"""State contract shared by ATS graph nodes."""

import operator

from typing import Annotated, Any, TypedDict


class ATSState(TypedDict, total=False):
    # ========================================================
    # Input
    # ========================================================

    resume_path: str
    jd_path: str

    resume_text: str
    jd_text: str

    # ========================================================
    # Extraction
    # ========================================================

    jd_requirements: dict[str, Any]
    resume_profile: dict[str, Any]

    jd_extraction_error: str | None
    resume_extraction_error: str | None

    # ========================================================
    # Matching and scoring
    # ========================================================

    matches: dict[str, Any]
    result: dict[str, Any]

    # ========================================================
    # Recommendation and report
    # ========================================================

    verdict: str | None
    escalation_reason: str | None

    evidence: dict[str, Any] | None
    narrative: str | None

    # ========================================================
    # Candidate follow-up
    # ========================================================

    followup_questions: list[str] | None
    followup_used: bool | None
    candidate_reply: str | None

    # ========================================================
    # Recruiter human-in-the-loop
    # ========================================================

    human_decision: str | None
    human_comments: str | None

    # ========================================================
    # External action result
    #
    # These remain in state because later workflows such as
    # interview scheduling/rejection can return action results.
    # The evaluation graph itself does not execute these actions.
    # ========================================================

    action_status: str | None
    action_id: str | None
    action_type: str | None

    # ========================================================
    # Audit
    # ========================================================

    audit_trail: Annotated[
        list[dict[str, Any]],
        operator.add,
    ]