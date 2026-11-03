"""Pydantic models for the ad-hoc ("Quick Evaluate") candidate API."""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class EvaluationRequest(BaseModel):
    jd_path: str = Field(..., description="Path to the job description file")
    resume_path: str = Field(..., description="Path to the resume PDF file")


class EvaluationStatus(BaseModel):
    id: str
    status: Literal["running", "completed"]
    verdict: Optional[str] = None
    narrative: Optional[str] = None
    error: Optional[str] = None
