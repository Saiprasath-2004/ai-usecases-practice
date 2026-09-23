"""Build and compile the ATS LangGraph workflow."""

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from ats_agent.agent_layer.human_review import human_review_node
from ats_agent.config import CHECKPOINT_DB_PATH
from ats_agent.graph.nodes import (
    calculate_ats_score_node,
    decision_node,
    extraction_complete_node,
    extract_job_description_requirements,
    extract_resume_profile,
    load_inputs_node,
    match_requirements_node,
    report_node,
    rescore_with_reply_node,
    skill_gap_followup_node,
)
from ats_agent.graph.state import ATSState


# ============================================================
# Extraction routing
# ============================================================


def route_after_extraction(state: ATSState) -> str:
    """
    Decide whether the graph can continue to matching.

    Both JD and resume extraction must complete successfully
    before matching starts.
    """

    if state.get("jd_extraction_error"):
        return "error"

    if state.get("resume_extraction_error"):
        return "error"

    if state.get("escalation_reason"):
        return "error"

    return "continue"


# ============================================================
# ATS decision routing
# ============================================================


def route_after_decision(state: ATSState) -> str:
    """
    Route the candidate based on the ATS recommendation.

    The ATS recommendation is not a final recruiter action.

    SELECT   -> Strong Match
    ESCALATE -> Review / Hold
    REJECT   -> Rejected

    All recommendations are sent to the recruiter review point.
    """

    verdict = state.get("verdict")

    if verdict == "SELECT":
        return "strong_match"

    if verdict == "ESCALATE":
        return "review"

    if verdict == "REJECT":
        return "reject"

    return "review"


# ============================================================
# Human review routing
# ============================================================


def route_after_human_review(state: ATSState) -> str:
    """
    Route the workflow according to the recruiter's decision.

    The recruiter is the final authority.

    The human-review node only captures the decision.
    External actions are handled by the application/service layer.
    """

    decision = state.get("human_decision")

    if decision == "Schedule Interview":
        return "schedule_interview"

    if decision == "Get More Details":
        return "followup"

    if decision == "Hold":
        return "hold"

    if decision == "Reject":
        return "reject"

    if decision == "Move to Review":
        return "review"

    if decision == "Confirm Rejection":
        return "confirm_rejection"

    return "invalid"


# ============================================================
# Build graph
# ============================================================


def build_graph():
    """Build and compile the ATS human-in-the-loop workflow."""

    builder = StateGraph(ATSState)

    # ========================================================
    # Nodes
    # ========================================================

    builder.add_node(
        "load_inputs",
        load_inputs_node,
    )

    builder.add_node(
        "extract_job_description_requirements",
        extract_job_description_requirements,
    )

    builder.add_node(
        "extract_resume_profile",
        extract_resume_profile,
    )

    builder.add_node(
        "extraction_complete",
        extraction_complete_node,
    )

    builder.add_node(
        "match_requirements",
        match_requirements_node,
    )

    builder.add_node(
        "calculate_ats_score",
        calculate_ats_score_node,
    )

    builder.add_node(
        "decision",
        decision_node,
    )

    builder.add_node(
        "build_report",
        report_node,
    )

    builder.add_node(
        "human_review",
        human_review_node,
    )

    builder.add_node(
        "skill_gap_followup",
        skill_gap_followup_node,
    )

    builder.add_node(
        "rescore_with_reply",
        rescore_with_reply_node,
    )

    # ========================================================
    # Initial evaluation
    # ========================================================

    builder.add_edge(
        START,
        "load_inputs",
    )

    builder.add_edge(
        "load_inputs",
        "extract_job_description_requirements",
    )

    builder.add_edge(
        "load_inputs",
        "extract_resume_profile",
    )

    # ========================================================
    # Extraction synchronization
    # ========================================================

    builder.add_edge(
        "extract_job_description_requirements",
        "extraction_complete",
    )

    builder.add_edge(
        "extract_resume_profile",
        "extraction_complete",
    )

    # ========================================================
    # Extraction result routing
    # ========================================================

    builder.add_conditional_edges(
        "extraction_complete",
        route_after_extraction,
        {
            "continue": "match_requirements",
            "error": "build_report",
        },
    )

    # ========================================================
    # Matching → scoring → decision
    # ========================================================

    builder.add_edge(
        "match_requirements",
        "calculate_ats_score",
    )

    builder.add_edge(
        "calculate_ats_score",
        "decision",
    )

    # ========================================================
    # AI recommendation → report
    # ========================================================

    builder.add_conditional_edges(
        "decision",
        route_after_decision,
        {
            "strong_match": "build_report",
            "review": "build_report",
            "reject": "build_report",
        },
    )

    # ========================================================
    # Report → Human Review
    # ========================================================

    # The ATS has completed its analysis.
    #
    # Now the workflow pauses and waits for the recruiter.
    builder.add_edge(
        "build_report",
        "human_review",
    )

    # ========================================================
    # Human decision routing
    # ========================================================

    builder.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            # The graph stops here. The API/service layer performs
            # the actual interview scheduling.
            "schedule_interview": END,

            # Generate questions and wait for candidate response.
            "followup": "skill_gap_followup",

            # Recruiter chose to keep the candidate on hold.
            "hold": END,

            # The API/service layer performs the rejection action.
            "reject": END,

            # Candidate remains in the review pipeline.
            "review": END,

            # Recruiter confirmed the rejection.
            "confirm_rejection": END,

            # Invalid recruiter input.
            "invalid": END,
        },
    )

    # ========================================================
    # Candidate follow-up
    # ========================================================

    builder.add_edge(
        "skill_gap_followup",
        "rescore_with_reply",
    )

    # ========================================================
    # Follow-up → new ATS decision
    # ========================================================

    builder.add_edge(
        "rescore_with_reply",
        "decision",
    )

    # ========================================================
    # Persistent checkpointing
    # ========================================================

    connection = sqlite3.connect(
        CHECKPOINT_DB_PATH,
        check_same_thread=False,
    )

    checkpointer = SqliteSaver(connection)

    return builder.compile(
        checkpointer=checkpointer,
    )