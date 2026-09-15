"""Pydantic contracts exchanged by extraction and scoring workflows."""

from pydantic import BaseModel, Field


class SkillRequirement(BaseModel):
    name: str
    variants: list[str] = Field(default_factory=list)


class ResponsibilityRequirement(BaseModel):
    name: str
    keywords: list[str] = Field(default_factory=list)


class JDRequirements(BaseModel):
    skills: list[SkillRequirement] = Field(default_factory=list)

    keywords: list[str] = Field(default_factory=list)

    responsibilities: list[ResponsibilityRequirement] = Field(default_factory=list)

    experience_min: float | None = None
    experience_max: float | None = None


class CandidateSkill(BaseModel):
    name: str
    variants: list[str] = Field(default_factory=list)


class Responsibility(BaseModel):
    name: str
    keywords: list[str] = Field(default_factory=list)


class ResumeProfile(BaseModel):
    skills: list[CandidateSkill] = Field(default_factory=list)

    keywords: list[str] = Field(default_factory=list)

    responsibilities: list[Responsibility] = Field(default_factory=list)

    experience_years: float | None = None


class ResponsibilityMatch(BaseModel):
    responsibility: str = Field(description="The job responsibility being evaluated")
    supported: bool = Field(
        description="True if direct evidence exists in the resume, False otherwise"
    )
    evidence: str | None = Field(
        default=None,
        description=(
            "Exact quote or summary from the resume supporting the claim. "
            "Required when supported is true."
        ),
    )
