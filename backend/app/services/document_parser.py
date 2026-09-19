import os
import io
import logging
from typing import List, Dict, Any
try:
    import pypdf
except ImportError:
    pypdf = None
try:
    import docx
except ImportError:
    docx = None

logger = logging.getLogger(__name__)

def extract_text(file_path: str, file_type: str) -> str:
    """Extract text from PDF, DOCX, or TXT."""
    try:
        if file_type == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif file_type == 'pdf':
            if not pypdf:
                return "PDF extraction requires pypdf. Extracted nothing."
            text = ""
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        elif file_type == 'docx':
            if not docx:
                return "DOCX extraction requires python-docx. Extracted nothing."
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        return ""
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return ""

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Simple character overlap chunking."""
    if not text:
        return []
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunks.append(text[start:end])
        if end == text_len:
            break
        start += (chunk_size - overlap)
    return chunks
