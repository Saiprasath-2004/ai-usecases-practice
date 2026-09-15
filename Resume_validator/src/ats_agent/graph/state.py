"""State contract shared by all ATS graph nodes."""

from typing import Any, TypedDict


class ATSState(TypedDict):
    resume_path: str
    resume_text: str
    jd_context: str
    analysis: str
    jd_requirements: dict[str, Any]
    resume_profile: dict[str, Any]
    matches: dict[str, Any]
    result: dict[str, Any]
