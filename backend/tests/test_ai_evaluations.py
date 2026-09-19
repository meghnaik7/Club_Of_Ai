"""
Automated Test Suite for the 8 Core Agentic AI & RAG Evaluations.
Ensures high accuracy, safety, human confirmation compliance, and that valid user requests are never unnecessarily restricted.
"""
import unittest
from app.ai.evaluations.evaluator import AgenticEvaluator

class TestAgenticAIEvaluations(unittest.TestCase):
    # -------------------------------------------------------------------------
    # 1. Tool Selection Accuracy
    # -------------------------------------------------------------------------
    def test_01_tool_selection_accuracy(self):
        cases = [
            ("What tasks are currently overdue?", "get_overdue_tasks", "get_overdue_tasks"),
            ("Calculate critical path for hackathon", "calculate_critical_path", "calculate_critical_path"),
            ("Show me overloaded volunteers", "get_overloaded_volunteers", "get_overloaded_volunteers"),
            ("Detect risks in event schedule", "detect_event_risks", "detect_event_risks")
        ]
        for query, selected, expected in cases:
            res = AgenticEvaluator.evaluate_tool_selection(query, selected, expected)
            self.assertTrue(res.passed, f"Failed tool selection on: {query}")
            self.assertEqual(res.score, 1.0)

        # Mismatched tool fails
        mismatch_res = AgenticEvaluator.evaluate_tool_selection("Show tasks", "delete_event", "list_tasks")
        self.assertFalse(mismatch_res.passed)
        self.assertEqual(mismatch_res.score, 0.0)

    # -------------------------------------------------------------------------
    # 2. Tool Argument Accuracy
    # -------------------------------------------------------------------------
    def test_02_tool_argument_accuracy(self):
        actual_args = {"event_id": 1, "task_id": 42, "status": "IN_PROGRESS"}
        expected_args = {"event_id": 1, "task_id": 42}
        res = AgenticEvaluator.evaluate_tool_arguments(actual_args, expected_args)
        self.assertTrue(res.passed)
        self.assertEqual(res.score, 1.0)

        # Missing or wrong parameter fails
        wrong_args = {"event_id": 99}
        res_fail = AgenticEvaluator.evaluate_tool_arguments(wrong_args, expected_args)
        self.assertFalse(res_fail.passed)
        self.assertLess(res_fail.score, 1.0)

    # -------------------------------------------------------------------------
    # 3. Task / Goal Completion
    # -------------------------------------------------------------------------
    def test_03_task_goal_completion(self):
        successful_response = {
            "success": True,
            "summary": "Proposal #12 created for rescheduling Task 5 to next Friday.",
            "data": {"proposal_id": 12}
        }
        res = AgenticEvaluator.evaluate_task_completion(successful_response, ["proposal", "task 5"])
        self.assertTrue(res.passed)
        self.assertEqual(res.score, 1.0)

        # Incomplete goal fails
        failed_response = {"success": False, "summary": "Failed to connect to service."}
        res_fail = AgenticEvaluator.evaluate_task_completion(failed_response, ["proposal"])
        self.assertFalse(res_fail.passed)

    # -------------------------------------------------------------------------
    # 4. Plan / Workflow Accuracy
    # -------------------------------------------------------------------------
    def test_04_plan_workflow_accuracy(self):
        # Correct sequence: READ -> PROPOSE -> CONFIRM
        correct_sequence = ["READ_CONTEXT", "PROPOSAL_STAGED", "USER_CONFIRMATION"]
        res = AgenticEvaluator.evaluate_plan_workflow_accuracy(
            executed_steps=correct_sequence,
            valid_sequences=[["READ_CONTEXT", "PROPOSAL_STAGED", "USER_CONFIRMATION"]]
        )
        self.assertTrue(res.passed)

        # Invalid sequence: Direct write before proposal or read
        bad_sequence = ["DIRECT_WRITE", "USER_CONFIRMATION"]
        res_bad = AgenticEvaluator.evaluate_plan_workflow_accuracy(
            executed_steps=bad_sequence,
            valid_sequences=[["READ_CONTEXT", "PROPOSAL_STAGED", "USER_CONFIRMATION"]]
        )
        self.assertFalse(res_bad.passed)

    # -------------------------------------------------------------------------
    # 5. Guardrail & Safety Evaluation (No false friction on valid requests)
    # -------------------------------------------------------------------------
    def test_05_guardrail_safety_evaluation(self):
        # 1. Dangerous / Malicious request MUST be blocked
        res_blocked = AgenticEvaluator.evaluate_guardrail_safety(
            is_malicious_or_unauthorized=True,
            was_blocked=True,
            action_summary="Prompt injection attempt rejected"
        )
        self.assertTrue(res_blocked.passed)

        # 2. Legitimate, valid user request MUST NOT be blocked
        res_valid = AgenticEvaluator.evaluate_guardrail_safety(
            is_malicious_or_unauthorized=False,
            was_blocked=False,
            action_summary="Summarize upcoming schedule for Hackathon"
        )
        self.assertTrue(res_valid.passed)
        self.assertIn("without unnecessary restriction", res_valid.details)

        # 3. False Positive: Valid request mistakenly blocked is flagged as FAILURE
        res_false_positive = AgenticEvaluator.evaluate_guardrail_safety(
            is_malicious_or_unauthorized=False,
            was_blocked=True,
            action_summary="Valid request incorrectly rejected"
        )
        self.assertFalse(res_false_positive.passed)

    # -------------------------------------------------------------------------
    # 6. Human-Approval Compliance
    # -------------------------------------------------------------------------
    def test_06_human_approval_compliance(self):
        # WRITE actions must be staged as proposals
        write_eval = AgenticEvaluator.evaluate_human_approval_compliance(
            tool_classification="WRITE",
            staged_as_proposal=True,
            required_confirmation=True
        )
        self.assertTrue(write_eval.passed)

        # READ actions should execute immediately without blocking
        read_eval = AgenticEvaluator.evaluate_human_approval_compliance(
            tool_classification="READ",
            staged_as_proposal=False,
            required_confirmation=False
        )
        self.assertTrue(read_eval.passed)

    # -------------------------------------------------------------------------
    # 7. Retrieval Quality (Precision, Recall, Hit Rate)
    # -------------------------------------------------------------------------
    def test_07_retrieval_quality(self):
        retrieved_ids = ["chunk_venue_policy", "chunk_catering_quote", "chunk_other_doc"]
        ground_truth = {"chunk_venue_policy"}
        res = AgenticEvaluator.evaluate_retrieval_quality(
            retrieved_chunk_ids=retrieved_ids,
            ground_truth_relevant_ids=ground_truth,
            k=3
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.metrics["hit_rate"], 1.0)
        self.assertGreater(res.score, 0.6)

    # -------------------------------------------------------------------------
    # 8. Answer Faithfulness + Relevance
    # -------------------------------------------------------------------------
    def test_08_answer_faithfulness_and_relevance(self):
        query = "What is the maximum reimbursement for club meals?"
        context = "According to Section 4 of budget guidelines, the maximum meal allowance is $50 per volunteer."
        answer = "The maximum reimbursement for club meals is $50 per volunteer [Source: budget guidelines]."
        
        res = AgenticEvaluator.evaluate_answer_faithfulness_and_relevance(
            user_query=query,
            answer=answer,
            retrieved_context=context,
            required_factual_keywords=["$50", "meal"]
        )
        self.assertTrue(res.passed)
        self.assertGreaterEqual(res.score, 0.8)

    # -------------------------------------------------------------------------
    # 9. Simultaneous / Parallel Tool Calling
    # -------------------------------------------------------------------------
    def test_09_parallel_simultaneous_tool_calling(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.db.base_class import Base
        from app.models.user import User, UserRole
        from app.ai.agents.operational_agent import OperationalAgent
        from app.ai.tools.registry import init_tool_registry

        # Setup SQLite memory session
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()

        user = User(id=1, email="lead@club.org", hashed_password="h", full_name="Morgan", role=UserRole.ADMIN)
        db.add(user)
        db.commit()

        init_tool_registry()
        agent = OperationalAgent(user=user, club_id=1, event_id=1)

        tool_calls = [
            # 2 Read tools
            {"tool_name": "list_tasks", "arguments": {"event_id": 1}},
            {"tool_name": "get_overdue_tasks", "arguments": {"event_id": 1}},
            # 2 Write tools
            {"tool_name": "create_task", "arguments": {"event_id": 1, "title": "Buy Banners", "priority": "HIGH"}},
            {"tool_name": "create_task", "arguments": {"event_id": 1, "title": "Reserve Hall", "priority": "URGENT"}}
        ]

        batch_result = agent.run_tools_parallel(tool_calls=tool_calls, db=db)

        self.assertTrue(batch_result["success"])
        self.assertEqual(batch_result["total_calls"], 4)
        # Read tools executed concurrently
        self.assertIn("list_tasks", batch_result["read_results"])
        self.assertIn("get_overdue_tasks", batch_result["read_results"])
        # Write tools bundled into single atomic proposal
        self.assertTrue(batch_result["requires_confirmation"])
        self.assertIsNotNone(batch_result["proposal"])
        self.assertEqual(batch_result["proposal"]["changes_count"], 2)

        db.close()


if __name__ == "__main__":
    unittest.main()

