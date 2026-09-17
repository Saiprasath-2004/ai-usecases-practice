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