"""State contract shared by ATS graph nodes."""

from typing import Any, TypedDict, Annotated
import operator

class ATSState(TypedDict, total=False):
    resume_path: str
    jd_path: str

    resume_text: str
    jd_text: str

    jd_requirements: dict[str, Any]
    resume_profile: dict[str, Any]

    matches: dict[str, Any]

    result: dict[str, Any]

    jd_extraction_error: str | None
    resume_extraction_error: str | None

    verdict: str | None
    escalation_reason: str | None
    evidence: dict[str, Any] | None
    narrative: str | None

    followup_questions: list[str] | None
    followup_used: bool | None
    # DEV-ONLY: Manual field for exercising the graph without a real webhook.
    # File 07 will add the production path.
    candidate_reply: str | None


    human_decision: str | None
    human_comments: str | None

    action_status: str | None
    action_id: str | None
    action_type: str | None
    audit_trail: Annotated[list[dict[str, Any]], operator.add]
