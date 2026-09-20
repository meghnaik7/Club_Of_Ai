import os
import sys
import unittest
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Ensure root and backend are on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base import Base
from app.models.document import Document, DocumentChunk, DocumentCategory
from app.models.event import Event, EventStatus
from app.models.user import User, UserRole
from app.core.security import create_access_token
from app.core.permissions import seed_permissions
from app.main import app

from ai.rag.embeddings import generate_embedding, cosine_similarity
from ai.rag.retrieval import retrieve_candidate_chunks
from ai.rag.reranker import rerank_chunks
from ai.rag.crag_grader import grade_retrieved_documents_crag
from ai.rag.self_rag import synthesize_grounded_answer_self_rag
from ai.rag.pipeline import execute_rag_pipeline, search_documents_rag
from ai.rag.club_memory import check_plan_against_club_memory

class TestAdvancedRAGPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sqlalchemy.pool import StaticPool
        from app.api import deps
        from ai.tools import document_tools

        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=cls.engine)
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        cls.orig_doc_tools_session = document_tools.SessionLocal
        document_tools.SessionLocal = cls.TestingSessionLocal

        seed_db = cls.TestingSessionLocal()
        seed_permissions(seed_db)
        seed_db.close()

        def override_get_db():
            db = cls.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[deps.get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        from app.api import deps
        from ai.tools import document_tools
        document_tools.SessionLocal = cls.orig_doc_tools_session
        app.dependency_overrides.pop(deps.get_db, None)
        Base.metadata.drop_all(bind=cls.engine)

    def setUp(self):
        self.db = self.TestingSessionLocal()

        # Seed sample documents and chunks
        self.doc1 = Document(
            id="doc-notes-01",
            event_id="hackathon-2025",
            name="MeetingNotes.docx",
            filename="MeetingNotes.docx",
            file_path="/mock/MeetingNotes.docx",
            file_type="DOCX",
            file_size=12000,
            category=DocumentCategory.MEETING_NOTES,
            raw_text="General Overview. Logistics meeting. Sponsor coordination had critical delays at the registration desk.",
            uploader="Arjun"
        )
        self.doc2 = Document(
            id="doc-postmortem-02",
            event_id="hackathon-2025",
            name="Post-mortem.txt",
            filename="Post-mortem.txt",
            file_path="/mock/Post-mortem.txt",
            file_type="TXT",
            file_size=8500,
            category=DocumentCategory.POST_MORTEM,
            raw_text="Venue Operations. Venue setup took 3 hours because audio-visual systems required custom HDMI distribution.",
            uploader="Priya"
        )
        self.doc3 = Document(
            id="doc-rules-03",
            event_id=None,
            name="AuditoriumRules.pdf",
            filename="AuditoriumRules.pdf",
            file_path="/mock/AuditoriumRules.pdf",
            file_type="PDF",
            file_size=5400,
            category=DocumentCategory.VENUE_RULES,
            raw_text="Campus Facility Guidelines. All events must conclude by 10 PM. Clean-up must be completed within 1 hour.",
            uploader="Campus Admin"
        )

        self.db.add_all([self.doc1, self.doc2, self.doc3])
        self.db.commit()

        # Chunks for doc1
        self.chunk1_1 = DocumentChunk(
            id="c1-1",
            document_id=self.doc1.id,
            chunk_index=0,
            page_number=1,
            section_name="General Overview",
            content="Total participants exceeded 350 students across 12 departments in the hackathon.",
            token_count=15,
            embedding=generate_embedding("Total participants exceeded 350 students across 12 departments in the hackathon.")
        )
        self.chunk1_2 = DocumentChunk(
            id="c1-2",
            document_id=self.doc1.id,
            chunk_index=1,
            page_number=2,
            section_name="Sponsor Logistics",
            content="Sponsor coordination had critical delays at the registration desk and booth assignments.",
            token_count=14,
            embedding=generate_embedding("Sponsor coordination had critical delays at the registration desk and booth assignments.")
        )

        # Chunks for doc2
        self.chunk2_1 = DocumentChunk(
            id="c2-1",
            document_id=self.doc2.id,
            chunk_index=0,
            page_number=1,
            section_name="Venue Setup Logistics",
            content="Venue setup took 3 hours during previous major events because audio-visual systems required custom HDMI distribution.",
            token_count=19,
            embedding=generate_embedding("Venue setup took 3 hours during previous major events because audio-visual systems required custom HDMI distribution.")
        )

        # Chunks for doc3
        self.chunk3_1 = DocumentChunk(
            id="c3-1",
            document_id=self.doc3.id,
            chunk_index=0,
            page_number=1,
            section_name="Curfew and Clean-up",
            content="Campus Facility Guidelines: All events must conclude by 10 PM. Clean-up must be completed within 1 hour after the event concludes.",
            token_count=22,
            embedding=generate_embedding("Campus Facility Guidelines: All events must conclude by 10 PM. Clean-up must be completed within 1 hour after the event concludes.")
        )

        self.db.add_all([self.chunk1_1, self.chunk1_2, self.chunk2_1, self.chunk3_1])
        self.db.commit()

    def tearDown(self):
        self.db.query(DocumentChunk).delete()
        self.db.query(Document).delete()
        self.db.commit()
        self.db.close()

    def test_embeddings_and_cosine_similarity(self):
        """Test dense vector embedding generation and cosine similarity properties."""
        v1 = generate_embedding("Venue setup took 3 hours")
        v2 = generate_embedding("Venue setup duration and logistics")
        v3 = generate_embedding("Pizza catering for lunch break")

        self.assertEqual(len(v1), 768)
        self.assertEqual(len(v2), 768)

        # Related texts should have positive similarity
        sim_related = cosine_similarity(v1, v2)
        sim_unrelated = cosine_similarity(v1, v3)

        self.assertGreater(sim_related, 0.0)
        self.assertGreaterEqual(cosine_similarity(v1, v1), 0.99)

    def test_hybrid_candidate_retrieval(self):
        """Test hybrid retrieval returns candidate chunks matching dense and keyword overlap."""
        candidates = retrieve_candidate_chunks(self.db, "venue setup hours", candidate_k=10)
        self.assertGreater(len(candidates), 0)

        # The venue setup chunk should be in candidates
        chunk_ids = [c[0].id for c in candidates]
        self.assertIn("c2-1", chunk_ids)

        # Scoped by category
        notes_candidates = retrieve_candidate_chunks(self.db, "registration", category=DocumentCategory.MEETING_NOTES)
        self.assertTrue(all(d.category == DocumentCategory.MEETING_NOTES for _, d, _ in notes_candidates))

    def test_reranker_prioritization(self):
        """Test lexical-semantic re-ranker accurately prioritizes high-density chunks."""
        candidates = retrieve_candidate_chunks(self.db, "HDMI audio-visual setup 3 hours", candidate_k=10)
        reranked = rerank_chunks("HDMI audio-visual setup 3 hours", candidates, top_k=5)

        self.assertGreater(len(reranked), 0)
        top_chunk = reranked[0][0]
        # c2-1 contains HDMI and 3 hours, so it must be ranked #1
        self.assertEqual(top_chunk.id, "c2-1")

    def test_crag_grader_filtering(self):
        """Test Corrective RAG grader retains relevant chunks and filters out noise."""
        candidates = retrieve_candidate_chunks(self.db, "custom HDMI distribution", candidate_k=10)
        relevant_chunks, crag_eval = grade_retrieved_documents_crag("custom HDMI distribution", candidates)

        self.assertTrue(crag_eval.is_grounded)
        self.assertGreater(crag_eval.relevant_count, 0)
        self.assertTrue(any(c[0].id == "c2-1" for c in relevant_chunks))

    def test_self_rag_synthesis_and_citations(self):
        """Test Self-RAG generates grounded answers with complete verifiable citations."""
        candidates = retrieve_candidate_chunks(self.db, "sponsor registration delays", candidate_k=5)
        answer, citations, confidence = synthesize_grounded_answer_self_rag("sponsor registration delays", candidates)

        self.assertIn("registration", answer.lower())
        self.assertGreater(len(citations), 0)
        self.assertGreater(confidence, 0.0)

        first_cit = citations[0]
        self.assertEqual(first_cit.document_id, "doc-notes-01")
        self.assertEqual(first_cit.filename, "MeetingNotes.docx")
        self.assertIsNotNone(first_cit.section_name)

    def test_end_to_end_execute_rag_pipeline(self):
        """Test complete execute_rag_pipeline returns structured RAGQueryResponse."""
        query = "What caused delays in venue setup?"
        response = execute_rag_pipeline(self.db, query, top_k=3)

        self.assertEqual(response.query, query)
        self.assertIsNotNone(response.answer)
        self.assertGreater(len(response.citations), 0)
        self.assertTrue(response.crag_eval.is_grounded)

        # Check citation contains Post-mortem.txt
        filenames = [c.filename for c in response.citations]
        self.assertIn("Post-mortem.txt", filenames)

    def test_proactive_club_memory_plan_check(self):
        """Test club memory audit detects risk when plan has inadequate setup time."""
        plan = "Our plan is: Venue setup starts 1 hour before the event."
        mem_resp = check_plan_against_club_memory(self.db, plan)

        self.assertGreater(mem_resp.surfaced_lessons_count, 0)
        self.assertTrue(any(r.risk_level == "HIGH" for r in mem_resp.recommendations))
        self.assertTrue(any("3 hours" in r.historical_context or "setup" in r.lesson.lower() for r in mem_resp.recommendations))

    def test_search_documents_rag(self):
        """Test search_documents_rag returns clean dictionary structure."""
        results = search_documents_rag(self.db, "350 students hackathon", limit=3)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["document_id"], "doc-notes-01")
        self.assertIn("350", results[0]["content"])

    def test_ai_tools_document_interfaces(self):
        """Test document_tools in ai/tools execute with RAG and return serializable responses."""
        from ai.tools.document_tools import ask_documents as tool_ask, search_documents as tool_search, check_plan_against_club_memory as tool_audit

        # Test search tool
        search_res = tool_search.invoke({"query": "HDMI venue setup"})
        self.assertIsInstance(search_res, list)

        # Test audit tool
        audit_res = tool_audit.invoke({"plan_text": "Setup starts 1 hour before event"})
        self.assertIsInstance(audit_res, dict)
        self.assertIn("surfaced_lessons_count", audit_res)

        # Test ask tool
        ask_res = tool_ask.invoke({"question": "What issues happened at registration?"})
        self.assertIsInstance(ask_res, dict)
        self.assertIn("answer", ask_res)
        self.assertIn("citations", ask_res)

    def test_fastapi_rag_and_memory_endpoints(self):
        """Test FastAPI /api/documents/rag/query and /api/documents/club-memory/check-plan."""
        # 1. RAG query endpoint
        resp = self.client.post(
            "/api/documents/rag/query",
            json={"query": "What problems happened during venue setup?", "top_k": 3}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("answer", data)
        self.assertIn("citations", data)
        self.assertIn("crag_eval", data)

        # 2. Club memory plan check endpoint
        resp_mem = self.client.post(
            "/api/documents/club-memory/check-plan",
            json={"plan_text": "Venue setup starts 1 hour prior to opening"}
        )
        self.assertEqual(resp_mem.status_code, 200)
        mem_data = resp_mem.json()
        self.assertIn("recommendations", mem_data)
        self.assertIn("overall_risk_assessment", mem_data)

    def test_rag_chat_history_persistence(self):
        """Test that asking RAG questions persists history and can be retrieved on open."""
        # 1. Query RAG
        resp = self.client.post(
            "/api/documents/rag/query",
            json={"query": "What went wrong with the projector?"}
        )
        self.assertEqual(resp.status_code, 200)

        # 2. Retrieve history (simulating user opening RAG / document brain)
        hist_resp = self.client.get("/api/documents/rag/history")
        self.assertEqual(hist_resp.status_code, 200)
        history = hist_resp.json()
        self.assertIn("items", history)
        items = history["items"]
        self.assertIsInstance(items, list)
        self.assertGreater(len(items), 0)
        # Find the question in items
        questions = [item["question"] for item in items]
        self.assertIn("What went wrong with the projector?", questions)
        matching = [item for item in items if item["question"] == "What went wrong with the projector?"][0]
        self.assertIsNotNone(matching["answer"])
        self.assertIn("citations", matching)

        # 3. Clear history
        del_resp = self.client.delete("/api/documents/rag/history")
        self.assertEqual(del_resp.status_code, 200)
        
        # 4. Verify history is cleared
        cleared_resp = self.client.get("/api/documents/rag/history")
        self.assertEqual(cleared_resp.status_code, 200)
        self.assertEqual(len(cleared_resp.json()["items"]), 0)

    def test_langgraph_checkpointer_persistence(self):
        """Test that LangGraph checkpointer is configured and retains thread state."""
        from ai.agents.graph import compiled_graph, memory_checkpointer, get_thread_config
        self.assertIsNotNone(memory_checkpointer)
        self.assertIsNotNone(compiled_graph.checkpointer)
        
        config = get_thread_config(thread_id="thread-test-123", user_id=42)
        self.assertIn("configurable", config)
        self.assertEqual(config["configurable"]["thread_id"], "thread-test-123")
        self.assertEqual(config["configurable"]["user_id"], "42")

    def test_rag_pipeline_knowledge_base_added_only_by_system_admin(self):
        """Verify that inside RAG pipeline, knowledge base documents can only be added by System Admin."""
        # 1. Seed users across hierarchy
        admin = User(email="sysadmin_rag@clubops.ai", full_name="Sys Admin", hashed_password="pw", role=UserRole.ADMIN, is_active=True)
        head = User(email="head_rag@clubops.ai", full_name="Club Head", hashed_password="pw", role=UserRole.CLUB_HEAD, is_active=True)
        lead = User(email="lead_rag@clubops.ai", full_name="Subteam Lead", hashed_password="pw", role=UserRole.SUBTEAM_LEAD, is_active=True)
        vol = User(email="vol_rag@clubops.ai", full_name="Volunteer", hashed_password="pw", role=UserRole.VOLUNTEER, is_active=True)
        self.db.add_all([admin, head, lead, vol])
        self.db.commit()

        admin_id = admin.id
        head_id = head.id
        lead_id = lead.id
        vol_id = vol.id

        admin_headers = {"Authorization": f"Bearer {create_access_token(str(admin_id))}"}
        head_headers = {"Authorization": f"Bearer {create_access_token(str(head_id))}"}
        lead_headers = {"Authorization": f"Bearer {create_access_token(str(lead_id))}"}
        vol_headers = {"Authorization": f"Bearer {create_access_token(str(vol_id))}"}

        doc_content = b"Official AI Lab Policy: The high-performance compute GPU server requires reservation 48 hours in advance through the cluster portal."
        file_payload = {
            "file": ("gpu_policy.txt", doc_content, "text/plain")
        }
        form_data = {
            "name": "GPU Server Policy",
            "category": "VENUE_RULES"
        }

        # 2. Unauthenticated upload -> 401 Unauthorized
        res_unauth = self.client.post("/api/documents/upload", files=file_payload, data=form_data)
        self.assertEqual(res_unauth.status_code, 401)

        # 3. Volunteer upload -> 403 Forbidden
        file_payload["file"] = ("gpu_policy.txt", doc_content, "text/plain")
        res_vol = self.client.post("/api/documents/upload", headers=vol_headers, files=file_payload, data=form_data)
        self.assertEqual(res_vol.status_code, 403)
        self.assertIn("Permission denied", res_vol.json()["detail"])

        # 4. Subteam Lead upload -> 403 Forbidden
        file_payload["file"] = ("gpu_policy.txt", doc_content, "text/plain")
        res_lead = self.client.post("/api/documents/upload", headers=lead_headers, files=file_payload, data=form_data)
        self.assertEqual(res_lead.status_code, 403)
        self.assertIn("Permission denied", res_lead.json()["detail"])

        # 5. Club Head upload -> 403 Forbidden (Strictly System Admin only)
        file_payload["file"] = ("gpu_policy.txt", doc_content, "text/plain")
        res_head = self.client.post("/api/documents/upload", headers=head_headers, files=file_payload, data=form_data)
        self.assertEqual(res_head.status_code, 403)
        self.assertIn("Permission denied", res_head.json()["detail"])

        # 6. System Admin upload -> 201 Created (Added into RAG knowledge base)
        file_payload["file"] = ("gpu_policy.txt", doc_content, "text/plain")
        res_admin = self.client.post("/api/documents/upload", headers=admin_headers, files=file_payload, data=form_data)
        self.assertEqual(res_admin.status_code, 201)
        doc_data = res_admin.json()
        self.assertIn("id", doc_data)
        self.assertEqual(doc_data["name"], "GPU Server Policy")
        self.assertGreater(doc_data["chunk_count"], 0)

        # 7. Query RAG pipeline against the newly added knowledge base
        rag_query_resp = self.client.post(
            "/api/documents/rag/query",
            json={"query": "How many hours in advance must the compute GPU server be reserved?", "top_k": 3}
        )
        self.assertEqual(rag_query_resp.status_code, 200)
        rag_data = rag_query_resp.json()
        self.assertIn("answer", rag_data)
        self.assertIn("citations", rag_data)
        self.assertIn("48 hours", rag_data["answer"])
        self.assertGreaterEqual(rag_data["confidence"], 0.4)
        self.assertTrue(any("gpu" in c.get("filename", "").lower() or "policy" in c.get("filename", "").lower() or "gpu" in str(c).lower() for c in rag_data["citations"]))


if __name__ == "__main__":
    unittest.main()
