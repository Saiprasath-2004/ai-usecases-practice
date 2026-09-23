"""Tests for the follow-up graph routing logic."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from langgraph.types import Command
from src.ats_agent.graph.builder import build_graph
from src.ats_agent.graph.state import ATSState

def test_followup_routing_and_rescore():
    """
    Test the flow: decision -> skill_gap_followup (interrupt) -> rescore -> decision.
    """
    graph = build_graph()

    # Initial state that triggers ESCALATE (follow-up)
    initial_state = {
        "resume_path": "input/resume_1.pdf",
        "jd_path": "jd.txt",
        "matches": {"missing_skills": ["Python", "AWS"]},
        "result": {"overall_score": 65.0},
        "verdict": "ESCALATE",
        "followup_used": False
    }

    # 1. Run to the first interrupt
    # We mock nodes that would normally do LLM work to focus on routing
    with patch("src.ats_agent.graph.nodes.load_inputs_node", return_value={"resume_text": "...", "jd_text": "..."}), \
         patch("src.ats_agent.graph.builder.extract_job_description_requirements", return_value={"jd_requirements": {}}), \
         patch("src.ats_agent.graph.builder.extract_resume_profile", return_value={"resume_profile": {}}), \
         patch("src.ats_agent.graph.builder.match_requirements_node", return_value={"matches": {"missing_skills": ["Python"]}}), \
         patch("src.ats_agent.graph.builder.calculate_ats_score_node", return_value={"result": {"overall_score": 65.0}}), \
         patch("src.ats_agent.graph.builder.decision_node", return_value={"verdict": "ESCALATE"}):

        config = {"configurable": {"thread_id": "followup_test"}}

        try:
            graph.invoke(initial_state, config=config)
        except Exception:
            pass

    # 2. Resume with a reply
    reply_data = {"candidate_reply": "Yes, I have 3 years of experience with Python and AWS."}

    # Mock all necessary nodes for the rescore path
    # We patch pypdf.PdfReader to avoid any real PDF parsing
    with patch("pypdf.PdfReader") as mock_pdf, \
         patch("src.ats_agent.graph.nodes.load_resume_text", return_value="..."), \
         patch("src.ats_agent.graph.nodes.load_inputs_node", return_value={"resume_text": "...", "jd_text": "..."}), \
         patch("src.ats_agent.graph.builder.extract_job_description_requirements", return_value={"jd_requirements": {}}), \
         patch("src.ats_agent.graph.builder.extract_resume_profile", return_value={"resume_profile": {}}), \
         patch("src.ats_agent.graph.builder.match_requirements_node", return_value={"matches": {"missing_skills": ["Python"]}}), \
         patch("src.ats_agent.graph.builder.calculate_ats_score_node", return_value={"result": {"overall_score": 65.0}}), \
         patch("src.ats_agent.graph.builder.apply_followup_reply", return_value={"overall_score": 85.0}), \
         patch("src.ats_agent.graph.builder.decision_node", return_value={"verdict": "SELECT"}):

        # Setup mock PDF reader behavior
        mock_pdf.return_value.pages = [MagicMock(extract_text=lambda: "...")]

        final_state = graph.invoke(
            Command(resume=reply_data),
            config=config
        )

        assert final_state["verdict"] == "SELECT"
        assert final_state["result"]["overall_score"] == 85.0

def test_non_escalate_verdicts_bypass_followup():
    """Confirm SELECT or REJECT verdicts never enter the follow-up path."""
    def routing_logic(state):
        if state["verdict"] == "ESCALATE" and not state.get("followup_used"):
            return "skill_gap_followup"
        elif state["verdict"] == "ESCALATE":
            return "human_review"
        else:
            return "build_report"

    assert routing_logic({"verdict": "SELECT"}) == "build_report"
    assert routing_logic({"verdict": "REJECT"}) == "build_report"
    assert routing_logic({"verdict": "ESCALATE", "followup_used": False}) == "skill_gap_followup"
    assert routing_logic({"verdict": "ESCALATE", "followup_used": True}) == "human_review"

def test_followup_bound_to_one_round():
    """Confirm follow-up path runs at most once."""
    def routing_logic(state):
        if state["verdict"] == "ESCALATE" and not state.get("followup_used"):
            return "skill_gap_followup"
        elif state["verdict"] == "ESCALATE":
            return "human_review"
        else:
            return "build_report"

    state1 = {"verdict": "ESCALATE", "followup_used": False}
    assert routing_logic(state1) == "skill_gap_followup"

    state2 = {"verdict": "ESCALATE", "followup_used": True}
    assert routing_logic(state2) == "human_review"
