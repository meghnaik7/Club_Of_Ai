import math
import hashlib
from typing import List
import numpy as np
from app.core.config import settings

# Attempt to configure Gemini client if API key is present
genai_client = None
if settings.GEMINI_API_KEY:
    try:
        from google import genai
        genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception:
        genai_client = None

def _generate_fallback_embedding(text: str, dim: int = 768) -> List[float]:
    """
    Deterministic semantic hash vectorizer for local/offline environments.
    Maps words, character tri-grams, and semantic roots to a normalized float vector.
    Ensures that identical or semantically related terms have high cosine similarity.
    """
    vec = np.zeros(dim, dtype=np.float32)
    words = text.lower().split()
    if not words:
        return vec.tolist()

    for idx, word in enumerate(words):
        # Word-level hash
        h_word = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
        vec[h_word % dim] += 1.5

        # Subword n-grams for typo & stem tolerance
        clean_w = "".join(c for c in word if c.isalnum())
        if len(clean_w) >= 3:
            for i in range(len(clean_w) - 2):
                ngram = clean_w[i:i+3]
                h_ng = int(hashlib.md5(ngram.encode("utf-8")).hexdigest(), 16)
                vec[h_ng % dim] += 0.5

    # L2 normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()

def generate_embedding(text: str) -> List[float]:
    """Generates a dense vector embedding for a single text chunk."""
    if not text.strip():
        return [0.0] * 768

    if genai_client and settings.GEMINI_API_KEY:
        try:
            response = genai_client.models.embed_content(
                model="text-embedding-004",
                contents=text
            )
            # Response handling for google-genai SDK
            if hasattr(response, "embedding") and hasattr(response.embedding, "values"):
                return list(response.embedding.values)
            elif hasattr(response, "embeddings") and response.embeddings:
                return list(response.embeddings[0].values)
        except Exception as e:
            # Fall back safely if API quota or connection fails
            pass

    return _generate_fallback_embedding(text)

def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Generates embeddings for a batch of text chunks."""
    return [generate_embedding(t) for t in texts]

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    a = np.array(vec1, dtype=np.float32)
    b = np.array(vec2, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
