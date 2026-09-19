import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from pypdf import PdfReader
import docx

class ParsedChunk:
    def __init__(
        self,
        content: str,
        chunk_index: int,
        page_number: Optional[int] = None,
        section_name: Optional[str] = None,
        token_count: int = 0
    ):
        self.content = content
        self.chunk_index = chunk_index
        self.page_number = page_number
        self.section_name = section_name
        self.token_count = token_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "section_name": self.section_name,
            "token_count": self.token_count
        }

def clean_text(text: str) -> str:
    """Normalizes whitespace, removes control characters and cleans text."""
    if not text:
        return ""
    # Replace non-breaking spaces and excessive whitespace
    text = text.replace("\xa0", " ")
    # Replace multiple consecutive newlines with two
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Replace multiple spaces with a single space
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def extract_pdf(file_path: str) -> List[Dict[str, Any]]:
    """Extracts text per page from PDF, returning a list of page dicts."""
    reader = PdfReader(file_path)
    pages = []
    for page_idx, page in enumerate(reader.pages, start=1):
        try:
            raw_text = page.extract_text() or ""
            cleaned = clean_text(raw_text)
            if cleaned:
                pages.append({
                    "page_number": page_idx,
                    "section_name": f"Page {page_idx}",
                    "text": cleaned
                })
        except Exception as e:
            continue
    return pages

def extract_docx(file_path: str) -> List[Dict[str, Any]]:
    """Extracts text and heading hierarchies from DOCX files."""
    doc = docx.Document(file_path)
    sections = []
    current_section = "General"
    current_paragraphs = []
    current_page = 1 # Approximation for docx based on paragraph count

    for p in doc.paragraphs:
        text = clean_text(p.text)
        if not text:
            continue

        # Check if paragraph is a heading
        style_name = p.style.name if p.style else ""
        if "Heading" in style_name or style_name.startswith("Title"):
            if current_paragraphs:
                sections.append({
                    "page_number": current_page,
                    "section_name": current_section,
                    "text": "\n".join(current_paragraphs)
                })
                current_paragraphs = []
            current_section = text
        else:
            current_paragraphs.append(text)
            if len(current_paragraphs) >= 12: # Approximate page boundary
                current_page += 1

    if current_paragraphs:
        sections.append({
            "page_number": current_page,
            "section_name": current_section,
            "text": "\n".join(current_paragraphs)
        })

    # Also extract any tables in docx
    for t_idx, table in enumerate(doc.tables, start=1):
        table_rows = []
        for row in table.rows:
            row_text = " | ".join([clean_text(cell.text) for cell in row.cells])
            if row_text.strip():
                table_rows.append(row_text)
        if table_rows:
            sections.append({
                "page_number": current_page,
                "section_name": f"Table {t_idx}",
                "text": "\n".join(table_rows)
            })

    return sections

def extract_txt(file_path: str) -> List[Dict[str, Any]]:
    """Extracts text from plain text or markdown files."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        full_text = f.read()

    cleaned = clean_text(full_text)
    # Split by markdown headers or double newlines
    lines = cleaned.split("\n")
    sections = []
    current_section = "Section 1"
    current_paragraphs = []
    page_counter = 1

    for line in lines:
        line_clean = line.strip()
        if line_clean.startswith("#"):
            if current_paragraphs:
                sections.append({
                    "page_number": page_counter,
                    "section_name": current_section,
                    "text": "\n".join(current_paragraphs)
                })
                current_paragraphs = []
            current_section = line_clean.lstrip("#").strip() or current_section
        elif line_clean:
            current_paragraphs.append(line_clean)
            if len(current_paragraphs) >= 25:
                page_counter += 1

    if current_paragraphs:
        sections.append({
            "page_number": page_counter,
            "section_name": current_section,
            "text": "\n".join(current_paragraphs)
        })

    return sections

def chunk_text(
    sections: List[Dict[str, Any]],
    chunk_size: int = 500,
    chunk_overlap: int = 100
) -> List[ParsedChunk]:
    """
    Chunks extracted sections into overlapping token/character windows while
    preserving exact page_number and section_name metadata.
    """
    parsed_chunks = []
    global_chunk_idx = 0

    for sec in sections:
        text = sec["text"]
        page_no = sec.get("page_number")
        section_title = sec.get("section_name", "General")

        words = text.split()
        if not words:
            continue

        # If section is small, keep as single chunk
        if len(words) <= chunk_size:
            chunk_content = " ".join(words)
            parsed_chunks.append(ParsedChunk(
                content=chunk_content,
                chunk_index=global_chunk_idx,
                page_number=page_no,
                section_name=section_title,
                token_count=len(words)
            ))
            global_chunk_idx += 1
            continue

        # Sliding window over words
        start_idx = 0
        while start_idx < len(words):
            end_idx = min(start_idx + chunk_size, len(words))
            chunk_words = words[start_idx:end_idx]
            chunk_content = " ".join(chunk_words)

            parsed_chunks.append(ParsedChunk(
                content=chunk_content,
                chunk_index=global_chunk_idx,
                page_number=page_no,
                section_name=section_title,
                token_count=len(chunk_words)
            ))
            global_chunk_idx += 1

            if end_idx >= len(words):
                break
            start_idx += (chunk_size - chunk_overlap)

    return parsed_chunks

def parse_and_chunk_document(
    file_path: str,
    file_type: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100
) -> List[ParsedChunk]:
    """Unified entry point for parsing any supported document format."""
    ft = file_type.upper()
    if ft == "PDF":
        sections = extract_pdf(file_path)
    elif ft == "DOCX":
        sections = extract_docx(file_path)
    elif ft in ("TXT", "MD"):
        sections = extract_txt(file_path)
    else:
        # Fallback to plain text
        sections = extract_txt(file_path)

    return chunk_text(sections, chunk_size, chunk_overlap)
