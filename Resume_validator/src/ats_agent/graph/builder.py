"""Build the ATS evaluation LangGraph workflow."""

from langgraph.graph import END, START, StateGraph

from ats_agent.graph.nodes import (
    calculate_ats_score_node,
    extract_job_description_requirements,
    extract_resume_profile,
    load_inputs_node,
    match_requirements_node,
)
from ats_agent.graph.state import ATSState


def build_graph():
    """Compile the single-JD, single-resume evaluation workflow."""

    builder = StateGraph(ATSState)

    builder.add_node("load_inputs", load_inputs_node)
    builder.add_node(
        "extract_job_description_requirements",
        extract_job_description_requirements,
    )
    builder.add_node("extract_resume_profile", extract_resume_profile)
    builder.add_node("match_requirements", match_requirements_node)
    builder.add_node("calculate_ats_score", calculate_ats_score_node)

    builder.add_edge(START, "load_inputs")
    builder.add_edge("load_inputs", "extract_job_description_requirements")
    builder.add_edge("load_inputs", "extract_resume_profile")
    builder.add_edge("extract_job_description_requirements", "match_requirements")
    builder.add_edge("extract_resume_profile", "match_requirements")
    builder.add_edge("match_requirements", "calculate_ats_score")
    builder.add_edge("calculate_ats_score", END)

    return builder.compile()
