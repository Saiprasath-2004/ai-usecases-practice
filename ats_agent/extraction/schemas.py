"""Pydantic schemas for ATS extraction workflows."""

from pydantic import BaseModel, Field


class Skill(BaseModel):
    """Canonical skill name and explicitly supported variants."""

    name: str
    variants: list[str] = Field(default_factory=list)


class JDResponsibility(BaseModel):
    """A responsibility extracted from a job description."""

    description: str
    type: str


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
    responsibilities: list[str] = Field(
        default_factory=list
    )
    experience_years: float | None = None


class ResponsibilityMatch(BaseModel):
    """Individual responsibility match result."""

    responsibility: str
    supported: bool
    evidence: str


class ResponsibilityMatchResult(BaseModel):
    """Collection of responsibility matches."""

    matches: list[ResponsibilityMatch]


class SkillConfirmation(BaseModel):
    """Confirmation of a specific skill from a candidate."""

    skill_name: str
    confirmed: bool
    evidence: str | None = None


class FollowupReply(BaseModel):
    """Structured reply from a candidate during follow-up."""

    confirmations: list[SkillConfirmation] = Field(default_factory=list)
    additional_comments: str | None = None
