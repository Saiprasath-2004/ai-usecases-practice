"""Build the ATS evaluation LangGraph workflow."""

from langgraph.graph import END, START, StateGraph

from ats_agent.graph.nodes import (
    analyze_resume,
    calculate_ats,
    load_resume_node,
    retrieve_job_description,
)
from ats_agent.graph.state import ATSState


def build_graph():
    """Compile the ordered resume evaluation workflow."""

    builder = StateGraph(ATSState)

    builder.add_node("load_resume", load_resume_node)
    builder.add_node("retrieve_job_description", retrieve_job_description)
    builder.add_node("analyze_resume", analyze_resume)
    builder.add_node("calculate_ats", calculate_ats)

    builder.add_edge(START, "load_resume")
    builder.add_edge("load_resume", "retrieve_job_description")
    builder.add_edge("retrieve_job_description", "analyze_resume")
    builder.add_edge("analyze_resume", "calculate_ats")
    builder.add_edge("calculate_ats", END)

    return builder.compile()
