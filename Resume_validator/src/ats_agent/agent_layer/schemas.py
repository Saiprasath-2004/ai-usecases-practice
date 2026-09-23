"""Pydantic schemas used by the ATS agent."""

from pydantic import BaseModel, Field


class Skill(BaseModel):
    """Normalized skill with known variants."""

    name: str
    variants: list[str] = Field(default_factory=list)


class JDResponsibility(BaseModel):
    """Responsibility extracted from a job description."""

    description: str
    type: str = ""


class JDRequirements(BaseModel):
    """Structured requirements extracted from a job description."""

    skills: list[Skill] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    responsibilities: list[JDResponsibility] = Field(
        default_factory=list
    )
    experience_min: float | None = None
    experience_max: float | None = None


class ResumeProfile(BaseModel):
    """Structured candidate information extracted from a resume."""

    skills: list[Skill] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    experience_years: float | None = None


class ResponsibilityMatch(BaseModel):
    """Match result for one job responsibility."""

    responsibility: str
    supported: bool
    evidence: str = ""


class ResponsibilityMatchResult(BaseModel):
    """Results of matching job responsibilities against a resume."""

    matches: list[ResponsibilityMatch] = Field(
        default_factory=list
    )


class SkillConfirmation(BaseModel):
    """Confirmation of a skill from candidate follow-up."""

    skill_name: str
    confirmed: bool
    evidence: str | None = None


class FollowupReply(BaseModel):
    """Structured candidate response to follow-up questions."""

    confirmations: list[SkillConfirmation] = Field(
        default_factory=list
    )
    additional_comments: str | None = None