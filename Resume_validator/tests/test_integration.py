import pytest
from unittest.mock import MagicMock, patch
from ats_agent.graph.builder import build_graph
from ats_agent.graph.state import ATSState
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
import os

# Mock nodes for path verification
def mock_node(state):
    return {"node_visited": True}

@pytest.fixture
def mock_graph():
    # We need to mock the nodes because build_graph uses real LLM/embedding calls
    with patch("ats_agent.graph.builder.load_inputs_node", side_effect=lambda s: {"resume_text": "res", "jd_text": "jd"}), \
         patch("ats_agent.graph.builder.extract_job_description_requirements", side_effect=lambda s: {"jd_requirements": {}}), \
         patch("ats_agent.graph.builder.extract_resume_profile", side_effect=lambda s: {"resume_profile": {}}), \
         patch("ats_agent.graph.builder.match_requirements_node", side_effect=lambda s: {"matches": {}}), \
         patch("ats_agent.graph.builder.calculate_ats_score_node", side_effect=lambda s: {"result": {"overall_score": 70.0}}), \
         patch("ats_agent.graph.builder.decision_node", side_effect=lambda s: {"verdict": "ESCALATE"}), \
         patch("ats_agent.graph.builder.report_node", side_effect=lambda s: {"narrative": "fixed"}), \
         patch("ats_agent.graph.builder.skill_gap_followup_node", side_effect=lambda s: {"followup_used": True, "followup_questions": ["Q1"]}), \
         patch("ats_agent.graph.builder.rescore_with_reply_node", side_effect=lambda s: {"result": {"overall_score": 85.0}}), \
         patch("ats_agent.graph.builder.unrecoverable_error_node", side_effect=lambda s: {"escalation_reason": "error"}), \
         patch("ats_agent.graph.builder.human_review_node", side_effect=lambda s: {"human_decision": "Approve"}), \
         patch("ats_agent.graph.builder.take_action_node", side_effect=lambda s: {"action_status": "SENT"}):

        graph = build_graph()
        return graph

def test_resilience_path(mock_graph):
    """Verify: Extraction Error -> Unrecoverable Error -> Human Review"""
    config = {"configurable": {"thread_id": "resilience_test"}}

    # We can't easily mock the logic inside the lambda in build_graph without modifying builder.py
    # but we can simulate the state
    initial_state = {
        "resume_path": "res.pdf",
        "jd_path": "jd.txt",
        "jd_extraction_error": "LLM Timeout"
    }

    # Instead of running the whole graph (which has lambdas), we test the nodes individually
    # or use a custom graph for the integration test.
    # Given the current build_graph, we'll verify the logic by injecting state.

    from ats_agent.graph.builder import unrecoverable_error_node, human_review_node

    # 1. Test unrecoverable_error_node
    state = {"jd_extraction_error": "Timeout", "audit_trail": []}
    res = unrecoverable_error_node(state)
    assert "escalation_reason" in res
    assert "JD Extraction Failed" in res["escalation_reason"]

    # 2. Test human_review_node
    with patch("ats_agent.agent_layer.human_review.interrupt", return_value={"decision": "Approve"}):
        res_human = human_review_node(state)
        assert res_human["human_decision"] == "Approve"

def test_followup_loop_logic():
    """Verify: Decision(ESCALATE) -> Followup -> Rescore -> Decision"""
    from ats_agent.graph.builder import decision_node, skill_gap_followup_node, rescore_with_reply_node
    from ats_agent.agent_layer.decision import Verdict

    # State: Score 70 (ESCALATE), followup not used
    state = {
        "result": {"overall_score": 70.0},
        "matches": {"missing_skills": ["React"]},
        "followup_used": False,
        "audit_trail": []
    }

    # Decision
    res_dec = decision_node(state)
    assert res_dec["verdict"] == "ESCALATE"

    # Followup
    res_fol = skill_gap_followup_node(state)
    assert res_fol["followup_used"] is True
    assert len(res_fol["followup_questions"]) > 0

    # Rescore
    state.update(res_fol)
    state["candidate_reply"] = "Yes, I know React"

    # We mock the LLM inside rescore_with_reply_node by patching extract_confirmed_skills
    with patch("ats_agent.graph.builder.extract_confirmed_skills", return_value=["React"]):
        res_rescore = rescore_with_reply_node(state)
        assert res_rescore["result"]["overall_score"] > 70.0

def test_human_review_path():
    """Verify: Decision(ESCALATE + followup_used) -> Human Review"""
    from ats_agent.graph.builder import decision_node

    state = {
        "result": {"overall_score": 70.0},
        "followup_used": True,
        "audit_trail": []
    }

    # Decision logic in builder.py:
    # lambda state: (
    #     "skill_gap_followup" if state["verdict"] == "ESCALATE" and not state.get("followup_used")
    #     else "human_review" if state["verdict"] == "ESCALATE"
    #     else "build_report"
    # )

    verdict = decision_node(state)["verdict"]
    # simulate the lambda
    next_node = "human_review" if verdict == "ESCALATE" and state.get("followup_used") else "skill_gap_followup"
    assert next_node == "human_review"
