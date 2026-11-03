"""Build the ATS evaluation LangGraph workflow.

Design note (refactor):
This graph is intentionally *evaluation-only*: load -> extract -> match ->
score -> decide -> build_report -> END. It no longer auto-sends emails or
interrupts for human/candidate input. Those concerns moved to
``ats_agent.agent_layer.actions`` / ``ats_agent.agent_layer.followup_service``
and are triggered explicitly by the recruiter from the dashboard (see
``ats_agent/api/routes/applications.py``).

Why: this graph is invoked concurrently for every resume in a batch
(``ats_agent.batch.BulkEvaluator``). LangGraph interrupts pause a single
thread waiting for external input, which is incompatible with "evaluate 50
resumes at once and always finish". Keeping the graph itself deterministic
and side-effect-free (no emails, no pauses) makes bulk evaluation reliable;
all recruiter-in-the-loop behavior (schedule interview, request more info,
reject with reason, hold) lives one layer up, driven by button clicks against
the stored ``Application`` row.

The older interactive nodes (``skill_gap_followup``, ``rescore_with_reply``,
``human_review``) are kept as importable functions (agent_layer/*.py) for
reference / a possible future interactive single-eval mode, but are no
longer wired into the compiled graph.
"""

import sqlite3

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver

from ats_agent.graph.nodes import (
    calculate_ats_score_node,
    extract_job_description_requirements,
    extract_resume_profile,
    load_inputs_node,
    match_requirements_node,
)
from ats_agent.graph.state import ATSState
from ats_agent.agent_layer.decision import decide
from ats_agent.agent_layer.report import build_evidence, render_narrative
from ats_agent.agent_layer.audit import log_event
from ats_agent.config import CHECKPOINT_DB_PATH


def unrecoverable_error_node(state):
    """Terminal node for extraction failures that can't be scored."""
    state_update = log_event(state, "unrecoverable_error", "ERROR", "Extraction failed")

    if state.get("jd_extraction_error"):
        reason = f"JD Extraction Failed: {state['jd_extraction_error']}"
    elif state.get("resume_extraction_error"):
        reason = f"Resume Extraction Failed: {state['resume_extraction_error']}"
    else:
        reason = "An unknown unrecoverable error occurred during extraction."

    return {**state_update, "verdict": "ERROR", "escalation_reason": reason}


def decision_node(state):
    """Determine the verdict based on the score. Always proceeds to build_report."""
    state_update = log_event(state, "decision", "TRANSITION", "Calculating verdict")

    score_result = state["result"]
    verdict = decide(score_result)

    return {**state_update, "verdict": verdict.value}


def report_node(state):
    """Build the evidence report and render narrative."""
    state_update = log_event(state, "build_report", "TRANSITION", "Generating final report")

    evidence = build_evidence(state["matches"], state["result"])
    narrative = render_narrative(evidence)
    return {
        **state_update,
        "evidence": evidence,
        "narrative": narrative,
    }


def build_graph():
    """Compile the evaluation-only workflow (no auto-actions, no interrupts)."""

    builder = StateGraph(ATSState)

    builder.add_node("load_inputs", load_inputs_node)
    builder.add_node(
        "extract_job_description_requirements",
        extract_job_description_requirements,
    )
    builder.add_node("extract_resume_profile", extract_resume_profile)
    builder.add_node("match_requirements", match_requirements_node)
    builder.add_node("calculate_ats_score", calculate_ats_score_node)
    builder.add_node("decision", decision_node)
    builder.add_node("build_report", report_node)
    builder.add_node("unrecoverable_error", unrecoverable_error_node)

    builder.add_edge(START, "load_inputs")
    builder.add_edge("load_inputs", "extract_job_description_requirements")
    builder.add_edge("load_inputs", "extract_resume_profile")

    builder.add_conditional_edges(
        "extract_job_description_requirements",
        lambda state: "unrecoverable_error" if state.get("jd_extraction_error") else "match_requirements",
    )
    builder.add_conditional_edges(
        "extract_resume_profile",
        lambda state: "unrecoverable_error" if state.get("resume_extraction_error") else "match_requirements",
    )

    builder.add_edge("match_requirements", "calculate_ats_score")
    builder.add_edge("calculate_ats_score", "decision")
    builder.add_edge("decision", "build_report")
    builder.add_edge("build_report", END)
    builder.add_edge("unrecoverable_error", END)

    conn = sqlite3.connect(CHECKPOINT_DB_PATH, check_same_thread=False)
    memory = SqliteSaver(conn)
    return builder.compile(checkpointer=memory)
