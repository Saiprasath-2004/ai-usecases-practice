"""Human review node for manual intervention in ATS evaluation."""

from langgraph.types import interrupt
from ats_agent.graph.state import ATSState

def human_review_node(state: ATSState):
    """
    Pauses the graph execution to request a human decision.

    The graph will stop here. A human recruiter can then resume the graph
    via the API using Command(resume=...).
    """
    # The interrupt call pauses execution.
    # The value passed to interrupt() is sent to the client.
    # The value returned by interrupt() is the value provided in the resume call.
    human_input = interrupt({
        "message": "Human intervention required for ATS evaluation.",
        "current_verdict": state.get("verdict"),
        "errors": {
            "jd_error": state.get("jd_extraction_error"),
            "resume_error": state.get("resume_extraction_error"),
        },
        "overall_score": state.get("result", {}).get("overall_score") if state.get("result") else None
    })

    # Expecting human_input to be a dict: {"decision": "...", "comments": "..."}
    # possible decisions: "Approve", "Reject", "Request More Info"
    decision = human_input.get("decision") if isinstance(human_input, dict) else None
    comments = human_input.get("comments") if isinstance(human_input, dict) else None

    return {
        "human_decision": decision,
        "human_comments": comments
    }
