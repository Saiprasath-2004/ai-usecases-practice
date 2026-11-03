import pytest
from unittest.mock import MagicMock, patch
import sqlite3
import os
import json
from ats_agent.agent_layer.decision import decide, Verdict
from ats_agent.agent_layer.report import build_evidence, render_narrative
from ats_agent.agent_layer.followup import build_followup_questions, apply_followup_reply, extract_confirmed_skills
from ats_agent.agent_layer.human_review import human_review_node
from ats_agent.agent_layer.actions import send_interview_invite, send_rejection_notice, init_outbox
from ats_agent.agent_layer.audit import log_event

# --- Decision Tests ---
def test_decide_thresholds():
    thresholds = {"select_cutoff": 80.0, "reject_floor": 40.0}
    # Case 1: Select
    assert decide({"overall_score": 85.0}, thresholds) == Verdict.SELECT
    # Case 2: Escalate
    assert decide({"overall_score": 70.0}, thresholds) == Verdict.ESCALATE
    # Case 3: Reject
    assert decide({"overall_score": 30.0}, thresholds) == Verdict.REJECT

def test_decide_defaults():
    # Test without thresholds (uses config defaults)
    # Assuming defaults are e.g. 80 and 40
    res = decide({"overall_score": 90.0})
    assert res == Verdict.SELECT

# --- Report Tests ---
def test_build_evidence_structure():
    matches = {
        "matched_skills": ["React", "TypeScript"],
        "missing_skills": ["AWS"],
        "skill_coverage": 0.6,
        "matched_keywords": ["Agile"],
        "missing_keywords": ["Scrum"],
        "matched_responsibilities": ["Frontend Dev"],
        "missing_responsibilities": ["CI/CD"]
    }
    result = {"overall_score": 75.0, "skill_score": 45.0}
    evidence = build_evidence(matches, result)

    assert "skills" in evidence
    assert evidence["skills"]["matched"] == ["React", "TypeScript"]
    assert evidence["skills"]["missing"] == ["AWS"]
    assert evidence["score_breakdown"]["overall_score"] == 75.0

def test_render_narrative_deterministic():
    evidence = {
        "skills": {"matched": ["React"], "missing": ["AWS"]},
        "score_breakdown": {"overall_score": 75.0}
    }
    narrative = render_narrative(evidence)
    assert "overall score of 75.0" in narrative
    assert "Matched skills: React" in narrative
    assert "Missing skills: AWS" in narrative

def test_render_narrative_with_llm():
    evidence = {
        "skills": {"matched": ["React"], "missing": ["AWS"]},
        "score_breakdown": {"overall_score": 75.0}
    }
    mock_llm = MagicMock()
    mock_llm.return_value = "LLM Rephrased Narrative"

    narrative = render_narrative(evidence, llm_call=mock_llm)
    assert narrative == "LLM Rephrased Narrative"
    mock_llm.assert_called_once()

# --- Follow-up Tests ---
def test_build_followup_questions():
    missing = ["Docker", "Kubernetes", "Terraform"]
    # Test limit
    questions = build_followup_questions(missing, max_questions=2)
    assert len(questions) == 2
    assert "Docker" in questions[0]
    assert "Kubernetes" in questions[1]

def test_extract_confirmed_skills_fallback():
    # No LLM provided, uses basic keyword search
    questions = ["Do you have experience with Docker?", "Do you have experience with AWS?"]
    reply = "Yes, I have used Docker for 3 years."
    confirmed = extract_confirmed_skills(reply, questions, llm_call=None)
    assert "Docker" in confirmed
    assert "AWS" not in confirmed

def test_apply_followup_reply_scoring():
    result = {"overall_score": 50.0, "skill_score": 30.0}
    questions = ["..."]
    confirmed = ["Docker", "AWS"] # 2 skills * 5 = 10 points

    new_result = apply_followup_reply(result, questions, confirmed)
    assert new_result["skill_score"] == 40.0
    assert new_result["overall_score"] == 60.0
    assert new_result["followup_bonus"] == 10.0

def test_apply_followup_reply_ceiling():
    # Test skill score ceiling (60.0)
    result = {"overall_score": 70.0, "skill_score": 58.0}
    confirmed = ["S1", "S2", "S3"] # 15 points bonus

    new_result = apply_followup_reply(result, [], confirmed)
    assert new_result["skill_score"] == 60.0 # Capped
    assert new_result["overall_score"] == 72.0 # Only +2 bonus added
    assert new_result["followup_bonus"] == 2.0

# --- Human Review Tests ---
def test_human_review_node_mapping():
    # Mock interrupt
    with patch("ats_agent.agent_layer.human_review.interrupt") as mock_interrupt:
        mock_interrupt.return_value = {"decision": "Approve", "comments": "Strong candidate"}

        state = {"verdict": "ESCALATE", "result": {"overall_score": 75.0}}
        output = human_review_node(state)

        assert output["human_decision"] == "Approve"
        assert output["human_comments"] == "Strong candidate"

# --- Actions Tests ---
@pytest.fixture
def temp_actions_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_actions.db")
    monkeypatch.setattr("ats_agent.agent_layer.actions.ACTIONS_DB_PATH", db_path)
    return db_path

def test_actions_idempotency(temp_actions_db):
    thread_id = "test_thread_123"
    candidate_data = {"email": "test@example.com", "name": "Test User"}

    # First call
    id1, status1 = send_interview_invite(thread_id, candidate_data)
    assert status1 == "SENT"

    # Second call (should be idempotent)
    id2, status2 = send_interview_invite(thread_id, candidate_data)
    assert status2 == "SENT"
    assert id1 == id2 # Same action_id returned

def test_actions_different_types(temp_actions_db):
    thread_id = "test_thread_456"
    candidate_data = {"email": "test@example.com"}

    id1, _ = send_interview_invite(thread_id, candidate_data)
    id2, _ = send_rejection_notice(thread_id, candidate_data)

    assert id1 != id2 # Different action types should create different records

# --- Audit Tests ---
def test_log_event_append():
    state = {"audit_trail": [{"event": "START"}]}
    output = log_event(state, "node_1", "TRANSITION", "Moved to node 1")

    assert len(output["audit_trail"]) == 2
    assert output["audit_trail"][1]["node"] == "node_1"
    assert output["audit_trail"][1]["event"] == "TRANSITION"
    assert output["audit_trail"][1]["details"] == "Moved to node 1"

def test_log_event_init():
    state = {} # audit_trail not initialized
    output = log_event(state, "node_1", "START")

    assert len(output["audit_trail"]) == 1
    assert output["audit_trail"][0]["event"] == "START"
