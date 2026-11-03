"""Human-in-the-loop review for ATS recruiter decisions."""

from typing import Any

from langgraph.types import interrupt

from ats_agent.graph.state import ATSState


# These are recruiter decisions, not AI decisions.
#
# The agent produces a recommendation such as SELECT, ESCALATE,
# or REJECT. The recruiter then chooses the actual next action.
ALLOWED_DECISIONS = {
    "Schedule Interview",
    "Get More Details",
    "Hold",
    "Reject",
    "Move to Review",
    "Confirm Rejection",
}


def _build_review_context(state: ATSState) -> dict[str, Any]:
    """
    Build the information presented to the recruiter.

    The recruiter should receive enough information to understand
    why the agent reached its recommendation before choosing an action.

    This function only prepares review data. It does not make or
    execute the recruiter's decision.
    """

    result = state.get("result") or {}
    evidence = state.get("evidence") or {}

    return {
        "recommendation": state.get("verdict"),
        "overall_score": result.get("overall_score"),
        "score_breakdown": {
            "skill_score": result.get("skill_score"),
            "experience_score": result.get("experience_score"),
            "keyword_score": result.get("keyword_score"),
            "responsibility_score": result.get(
                "responsibility_score"
            ),
        },
        "evidence": evidence,
        "narrative": state.get("narrative"),
        "missing_skills": (
            state.get("matches", {}).get("missing_skills", [])
        ),
        "matched_skills": (
            state.get("matches", {}).get("matched_skills", [])
        ),
        "missing_keywords": (
            state.get("matches", {}).get("missing_keywords", [])
        ),
        "matched_keywords": (
            state.get("matches", {}).get("matched_keywords", [])
        ),
        "missing_responsibilities": (
            state.get("matches", {}).get(
                "missing_responsibilities",
                [],
            )
        ),
        "matched_responsibilities": (
            state.get("matches", {}).get(
                "matched_responsibilities",
                [],
            )
        ),
        "escalation_reason": state.get("escalation_reason"),
        "followup_questions": (
            state.get("followup_questions") or []
        ),
        "errors": {
            "jd_error": state.get("jd_extraction_error"),
            "resume_error": state.get(
                "resume_extraction_error"
            ),
        },
    }


def human_review_node(state: ATSState) -> dict[str, Any]:
    """
    Pause the ATS workflow and request a recruiter decision.

    The agent has already:
        1. Extracted the JD and resume.
        2. Matched requirements.
        3. Calculated the ATS score.
        4. Produced evidence.
        5. Produced an AI recommendation.

    The recruiter now decides what should happen next.

    LangGraph interrupt() pauses the workflow and checkpoints its state.
    The API can later resume the same thread using Command(resume=...).

    Expected resume payload:

        {
            "decision": "Schedule Interview",
            "comments": "Strong candidate. Proceed with interview."
        }

    This node NEVER:
        - sends email
        - schedules an interview
        - rejects a candidate
        - changes the database
        - calls an external service

    It only captures and validates the recruiter's decision.
    """

    review_context = _build_review_context(state)

    human_input = interrupt(
        {
            "message": (
                "The ATS evaluation is complete. "
                "Please review the candidate evidence and "
                "choose the next action."
            ),
            "review_context": review_context,
            "allowed_decisions": sorted(ALLOWED_DECISIONS),
        }
    )

    # ---------------------------------------------------------
    # Validate resume payload
    # ---------------------------------------------------------

    if not isinstance(human_input, dict):
        return {
            "human_decision": None,
            "human_comments": None,
            "escalation_reason": (
                "Recruiter review response must be a JSON object."
            ),
        }

    # ---------------------------------------------------------
    # Extract decision and comments
    # ---------------------------------------------------------

    decision = human_input.get("decision")
    comments = human_input.get("comments")

    if not isinstance(decision, str):
        return {
            "human_decision": None,
            "human_comments": None,
            "escalation_reason": (
                "Recruiter review decision was not provided."
            ),
        }

    decision = decision.strip()

    # ---------------------------------------------------------
    # Validate decision
    # ---------------------------------------------------------

    if decision not in ALLOWED_DECISIONS:
        return {
            "human_decision": None,
            "human_comments": comments,
            "escalation_reason": (
                f"Invalid recruiter decision: {decision}. "
                f"Allowed decisions: "
                f"{', '.join(sorted(ALLOWED_DECISIONS))}."
            ),
        }

    # ---------------------------------------------------------
    # Validate comments
    # ---------------------------------------------------------

    if comments is not None and not isinstance(comments, str):
        comments = str(comments)

    comments = comments.strip() if comments else None

    return {
        "human_decision": decision,
        "human_comments": comments,
        "escalation_reason": None,
    }