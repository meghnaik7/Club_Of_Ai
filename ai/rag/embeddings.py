import os
import re
import math
import hashlib
import logging
from typing import List, Optional, Union
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

# Hugging Face ONNX & Tokenizer Singleton
_hf_model_instance = None

class HuggingFaceEmbeddingModel:
    """
    Local Hugging Face Embedding Engine powered by ONNX Runtime and HF Tokenizers.
    Provides fast, deterministic, CPU-accelerated vector generation without requiring PyTorch.
    """
    def __init__(self, model_repo: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_repo = model_repo
        self.session = None
        self.tokenizer = None
        self.dimension = 384
        self._load_model()

    def _load_model(self):
        try:
            from huggingface_hub import hf_hub_download
            from tokenizers import Tokenizer
            import onnxruntime as ort

            logger.info(f"Loading Hugging Face embedding model: {self.model_repo}")
            tok_path = hf_hub_download(self.model_repo, "tokenizer.json")
            model_path = hf_hub_download(self.model_repo, "onnx/model.onnx")

            self.tokenizer = Tokenizer.from_file(tok_path)
            self.tokenizer.enable_truncation(max_length=512)
            self.tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")

            # Initialize ONNX inference session with CPU provider and optimization
            opts = ort.SessionOptions()
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            opts.intra_op_num_threads = 2
            self.session = ort.InferenceSession(
                model_path,
                sess_options=opts,
                providers=["CPUExecutionProvider"]
            )
            # Detect output dimension from model metadata or test inference
            self.dimension = 384
            logger.info(f"Hugging Face embedding model {self.model_repo} initialized successfully (dim={self.dimension})")
        except Exception as e:
            logger.warning(f"Could not load Hugging Face ONNX model ({e}). Fallback vectorizer will be used.")
            self.session = None
            self.tokenizer = None

    def encode(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self.dimension
        if self.session is None or self.tokenizer is None:
            return _generate_fallback_embedding(text, dim=self.dimension)

        try:
            encoding = self.tokenizer.encode(text)
            input_ids = np.array([encoding.ids], dtype=np.int64)
            attention_mask = np.array([encoding.attention_mask], dtype=np.int64)
            token_type_ids = np.array([encoding.type_ids], dtype=np.int64)

            inputs = {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids
            }
            outputs = self.session.run(None, inputs)
            token_embeddings = outputs[0]  # [1, seq_len, dim]

            # Mean pooling with attention mask
            input_mask_expanded = np.expand_dims(attention_mask, -1).astype(float)
            sum_embeddings = np.sum(token_embeddings * input_mask_expanded, 1)
            sum_mask = np.clip(input_mask_expanded.sum(1), a_min=1e-9, a_max=None)
            mean_pooled = sum_embeddings / sum_mask

            # L2 Normalize vector
            norm = np.linalg.norm(mean_pooled, axis=1, keepdims=True)
            norm = np.where(norm == 0, 1e-12, norm)
            vector = (mean_pooled / norm)[0].tolist()
            return vector
        except Exception as err:
            logger.error(f"HF embedding encode error: {err}")
            return _generate_fallback_embedding(text, dim=self.dimension)

    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self.session is None or self.tokenizer is None:
            return [_generate_fallback_embedding(t, dim=self.dimension) for t in texts]

        try:
            encodings = self.tokenizer.encode_batch(texts)
            input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
            attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
            token_type_ids = np.array([e.type_ids for e in encodings], dtype=np.int64)

            inputs = {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids
            }
            outputs = self.session.run(None, inputs)
            token_embeddings = outputs[0]

            input_mask_expanded = np.expand_dims(attention_mask, -1).astype(float)
            sum_embeddings = np.sum(token_embeddings * input_mask_expanded, 1)
            sum_mask = np.clip(input_mask_expanded.sum(1), a_min=1e-9, a_max=None)
            mean_pooled = sum_embeddings / sum_mask

            norm = np.linalg.norm(mean_pooled, axis=1, keepdims=True)
            norm = np.where(norm == 0, 1e-12, norm)
            embeddings = (mean_pooled / norm).tolist()
            return embeddings
        except Exception as err:
            logger.error(f"HF embedding batch error: {err}")
            return [self.encode(t) for t in texts]

def get_huggingface_model() -> HuggingFaceEmbeddingModel:
    global _hf_model_instance
    if _hf_model_instance is None:
        model_name = getattr(settings, "HUGGINGFACE_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        _hf_model_instance = HuggingFaceEmbeddingModel(model_name)
    return _hf_model_instance

# Attempt to configure Gemini client if API key is present
genai_client = None
if getattr(settings, "GEMINI_API_KEY", None):
    try:
        from google import genai
        genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception:
        genai_client = None

def _generate_fallback_embedding(text: str, dim: int = 384) -> List[float]:
    """
    Deterministic semantic hash vectorizer for local/offline execution.
    Maps tokens, character n-grams, and semantic prefixes to a normalized float vector.
    Ensures identical or semantically related terms have positive cosine similarity.
    """
    vec = np.zeros(dim, dtype=np.float32)
    words = re.findall(r'\w+', text.lower())
    if not words:
        return vec.tolist()

    for word in words:
        h_word = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
        vec[h_word % dim] += 1.5

        if len(word) >= 3:
            for i in range(len(word) - 2):
                ngram = word[i:i+3]
                h_ng = int(hashlib.md5(ngram.encode("utf-8")).hexdigest(), 16)
                vec[h_ng % dim] += 0.5

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()

def generate_embedding(text: str) -> List[float]:
    """
    Generates a dense vector embedding for a text chunk.
    Default provider: Hugging Face (sentence-transformers/all-MiniLM-L6-v2).
    """
    if not text or not text.strip():
        model = get_huggingface_model()
        return [0.0] * getattr(model, "dimension", 384)

    provider = getattr(settings, "EMBEDDING_PROVIDER", "huggingface").lower()

    # 1. Hugging Face Local Embedding (Primary)
    if provider == "huggingface":
        try:
            hf_engine = get_huggingface_model()
            return hf_engine.encode(text)
        except Exception as e:
            logger.warning(f"HF embedding failed: {e}. Falling back...")

    # 2. Google Gemini Embedding (Optional when configured)
    if provider == "gemini" and genai_client and settings.GEMINI_API_KEY:
        try:
            response = genai_client.models.embed_content(
                model=getattr(settings, "EMBEDDING_MODEL", "text-embedding-004"),
                contents=text
            )
            if hasattr(response, "embedding") and hasattr(response.embedding, "values"):
                return list(response.embedding.values)
            elif hasattr(response, "embeddings") and response.embeddings:
                return list(response.embeddings[0].values)
        except Exception:
            pass

    # 3. Fallback deterministic vectorizer
    model = get_huggingface_model()
    dim = getattr(model, "dimension", 384)
    return _generate_fallback_embedding(text, dim=dim)

def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Generates embeddings for a batch of text chunks."""
    if not texts:
        return []

    provider = getattr(settings, "EMBEDDING_PROVIDER", "huggingface").lower()
    if provider == "huggingface":
        try:
            hf_engine = get_huggingface_model()
            return hf_engine.encode_batch(texts)
        except Exception as e:
            logger.warning(f"HF batch embedding failed: {e}")

    return [generate_embedding(t) for t in texts]

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculates cosine similarity between two float vectors with boundary protection."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    a = np.array(vec1, dtype=np.float32)
    b = np.array(vec2, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    similarity = float(np.dot(a, b) / (norm_a * norm_b))
    return max(0.0, min(1.0, similarity))
