"""State contract shared by ATS graph nodes."""

from typing import Any, TypedDict


class ATSState(TypedDict, total=False):
    resume_path: str
    jd_path: str

    resume_text: str
    jd_text: str

    jd_requirements: dict[str, Any]
    resume_profile: dict[str, Any]

    matches: dict[str, Any]

    result: dict[str, Any]
