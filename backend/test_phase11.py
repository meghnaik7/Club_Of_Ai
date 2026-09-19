import os
import io
import sys
from fastapi.testclient import TestClient
from pypdf import PdfWriter
import docx

# Ensure backend directory is on python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.main import app
from app.core.database import init_db

client = TestClient(app)

def create_sample_pdf() -> bytes:
    """Creates a sample PDF with pages."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    # Page 3: containing the user's specific scenario
    p3 = writer.add_blank_page(width=612, height=792)
    
    # We can write text onto page using reportlab or create with pypdf
    # In pypdf, adding text is done via streams or we can use a generated stream
    buf = io.BytesIO()
    writer.write(buf)
    # For testing realistic text extraction, let's create real PDF with text
    return buf.getvalue()

def create_sample_docx(file_path: str):
    """Creates a realistic sample DOCX with sections."""
    doc = docx.Document()
    doc.add_heading("Hackathon Retrospective 2025", level=1)
    doc.add_paragraph("This document summarizes the operational outcomes of our annual hackathon.")
    
    doc.add_heading("Section 1: General Overview", level=2)
    doc.add_paragraph("Total participants exceeded 350 students across 12 departments.")
    
    doc.add_heading("Section 2: Operational Delays and Logistics", level=2)
    doc.add_paragraph("Last year's event had delays in venue setup and sponsor coordination.")
    doc.add_paragraph("Sponsor coordination had critical delays at the registration desk and booth assignments.")
    doc.add_paragraph("Venue setup took 3 hours because audio-visual systems required custom HDMI distribution.")
    
    doc.save(file_path)

def create_sample_txt(file_path: str):
    """Creates a realistic sample TXT with venue rules."""
    content = """# Venue Operations and Booking Guidelines
All student club events held in the Central Auditorium must adhere to campus safety standards.

# Setup Requirements and Logistics
Venue setup took 3 hours during previous major events. Club leads must allocate at least 3 hours for sound checks and stage configuration before attendees are admitted.
Clean-up must be completed within 1 hour after the event concludes.
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

def run_tests():
    print("==================================================")
    print("RUNNING PHASE 11: DOCUMENTS & CLUB MEMORY TEST SUITE")
    print("==================================================")
    
    init_db()
    
    test_dir = os.path.join(os.path.dirname(__file__), "test_files")
    os.makedirs(test_dir, exist_ok=True)
    
    docx_path = os.path.join(test_dir, "MeetingNotes.docx")
    txt_path = os.path.join(test_dir, "Post-mortem.txt")
    
    create_sample_docx(docx_path)
    create_sample_txt(txt_path)
    
    # 1. Test Upload DOCX
    print("\n[TEST 1] Uploading MeetingNotes.docx (Category: MEETING_NOTES)...")
    with open(docx_path, "rb") as f:
        resp = client.post(
            "/api/v1/documents/upload",
            files={"file": ("MeetingNotes.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"category": "MEETING_NOTES", "uploader": "Arjun", "event_id": "hackathon-2025"}
        )
    assert resp.status_code == 201, f"Upload failed: {resp.text}"
    docx_doc = resp.json()
    print(f" -> SUCCESS: Uploaded {docx_doc['filename']} with {docx_doc['chunk_count']} chunks! ID: {docx_doc['id']}")
    
    # 2. Test Upload TXT/POST_MORTEM
    print("\n[TEST 2] Uploading Post-mortem.txt (Category: POST_MORTEM)...")
    with open(txt_path, "rb") as f:
        resp = client.post(
            "/api/v1/documents/upload",
            files={"file": ("Post-mortem.txt", f, "text/plain")},
            data={"category": "POST_MORTEM", "uploader": "Priya", "event_id": "hackathon-2025"}
        )
    assert resp.status_code == 201, f"Upload failed: {resp.text}"
    txt_doc = resp.json()
    print(f" -> SUCCESS: Uploaded {txt_doc['filename']} with {txt_doc['chunk_count']} chunks! ID: {txt_doc['id']}")
    
    # 3. Test List Documents
    print("\n[TEST 3] Listing Documents with Filter...")
    resp = client.get("/api/v1/documents?category=POST_MORTEM")
    assert resp.status_code == 200
    list_data = resp.json()
    assert list_data["total"] >= 1
    print(f" -> SUCCESS: Retrieved {list_data['total']} documents under POST_MORTEM.")
    
    # 4. Test RAG Query
    query = "What problems happened during last year's hackathon?"
    print(f"\n[TEST 4] RAG Query: '{query}'...")
    resp = client.post(
        "/api/v1/documents/rag/query",
        json={"query": query, "top_k": 3}
    )
    assert resp.status_code == 200, f"RAG failed: {resp.text}"
    rag_data = resp.json()
    print(f" -> RAG Answer:\n    \"{rag_data['answer']}\"")
    print(f" -> Confidence: {rag_data['confidence']}")
    print(f" -> CRAG Evaluation: {rag_data['crag_eval']['evaluation_notes']}")
    print(" -> Citations:")
    for c in rag_data["citations"]:
        page_or_sec = f"page {c['page_number']}" if c['page_number'] else c['section_name']
        print(f"    * {c['filename']}, {page_or_sec} (Score: {c['relevance_score']})")
    
    # Verify citations include MeetingNotes.docx or Post-mortem
    filenames = [c["filename"] for c in rag_data["citations"]]
    assert any("MeetingNotes" in fn or "Post-mortem" in fn for fn in filenames), "Expected citations from uploaded files"
    
    # 5. Test Club Memory Proactive Plan Check
    plan_text = "Venue setup starts 1 hour before event."
    print(f"\n[TEST 5] Club Memory Check for Plan: '{plan_text}'...")
    resp = client.post(
        "/api/v1/documents/club-memory/check-plan",
        json={"plan_text": plan_text}
    )
    assert resp.status_code == 200, f"Club memory check failed: {resp.text}"
    mem_data = resp.json()
    print(f" -> Surfaced Lessons Count: {mem_data['surfaced_lessons_count']}")
    print(f" -> Overall Risk: {mem_data['overall_risk_assessment']}")
    for r in mem_data["recommendations"]:
        print(f"    [RISK {r['risk_level']}]: {r['lesson']}")
        print(f"    Recommendation: {r['recommendation']}")
        for cit in r["citations"]:
            print(f"    Source: {cit['filename']}, {cit['section_name']}")
            
    assert mem_data["surfaced_lessons_count"] > 0, "Expected at least one historical lesson surfaced"
    
    # 6. Test Delete Document
    print(f"\n[TEST 6] Deleting Document ID: {docx_doc['id']}...")
    del_resp = client.delete(f"/api/v1/documents/{docx_doc['id']}")
    assert del_resp.status_code == 200
    print(f" -> SUCCESS: {del_resp.json()['message']}")
    
    print("\n==================================================")
    print("ALL PHASE 11 BACKEND TESTS PASSED SUCCESSFULLY! ")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
