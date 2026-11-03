"""Pydantic schemas for application API endpoints."""

from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from ats_agent.domain.models import (
    EvaluationStatus,
    PipelineStage,
    RunStatus,
)


# ============================================================
# Application Create
# ============================================================


class ApplicationCreate(BaseModel):
    """Request schema for creating a new application."""

    job_requisition_id: int = Field(
        ...,
        description="ID of the job the candidate is applying for.",
    )

    candidate_name: str = Field(
        ...,
        min_length=1,
        description="Candidate's full name.",
    )

    candidate_email: str = Field(
        ...,
        min_length=1,
        description="Candidate's email address.",
    )

    resume_path: str = Field(
        ...,
        min_length=1,
        description="Path to the candidate's resume PDF.",
    )


# ============================================================
# Application Read
# ============================================================


class ApplicationRead(BaseModel):
    """Application data returned to the frontend."""

    application_id: str
    candidate_name: str
    candidate_email: str
    resume_path: str
    pipeline_stage: PipelineStage
    evaluation_status: EvaluationStatus
    overall_score: Optional[float] = None
    score_breakdown: Optional[str] = None
    matched_skills: Optional[str] = None
    missing_skills: Optional[str] = None
    strengths: Optional[str] = None
    gaps: Optional[str] = None
    responsibilities_matched: Optional[str] = None
    responsibilities_missing: Optional[str] = None
    experience_result: Optional[str] = None
    recruiter_comments: Optional[str] = None
    follow_up_status: Optional[str] = None
    interview_status: Optional[str] = None
    thread_id: Optional[str] = None
    current_evaluation_run_id: Optional[int] = None

    model_config = ConfigDict(
        from_attributes=True
    )


# ============================================================
# Application List
# ============================================================


class ApplicationListResponse(BaseModel):
    """Applications grouped by pipeline stage."""

    applications: Dict[
        PipelineStage,
        List[ApplicationRead],
    ]


# ============================================================
# Recruiter Action
# ============================================================


class ActionRequest(BaseModel):
    """
    Recruiter action request.

    Examples:
        HOLD
        REJECT
        MOVE_TO_REVIEW
        SHORTLIST
        SCHEDULE_INTERVIEW
    """

    action_type: str = Field(
        ...,
        min_length=1,
        description=(
            "Recruiter action to perform, for example "
            "HOLD, REJECT, MOVE_TO_REVIEW, "
            "SHORTLIST, or SCHEDULE_INTERVIEW."
        ),
    )

    note: Optional[str] = Field(
        default=None,
        description="Optional recruiter comment.",
    )


# ============================================================
# Human Review
# ============================================================


class ReviewRequest(BaseModel):
    """
    Recruiter decision submitted to the LangGraph
    human-review interrupt.
    """

    decision: str = Field(
        ...,
        min_length=1,
        description=(
            "Recruiter decision, for example "
            "Schedule Interview, Get More Details, "
            "Hold, Reject, Move to Review, "
            "or Confirm Rejection."
        ),
    )

    comments: Optional[str] = Field(
        default=None,
        description="Optional recruiter review comments.",
    )
   

class FollowupReplyRequest(BaseModel):
    candidate_reply: str = Field(
        ...,
        min_length=1,
        description="Candidate's response to the ATS follow-up questions.",
    )

# ============================================================
# Evaluation Response
# ============================================================


class EvaluationResponse(BaseModel):
    """Response returned after starting/completing evaluation."""
    application_id: str
    evaluation_status: EvaluationStatus
    pipeline_stage: PipelineStage
    overall_score: Optional[float] = None
    thread_id: Optional[str] = None
    run_id: Optional[int] = None
    run_status: Optional[RunStatus] = None

class InterviewResponseRequest(BaseModel):
    response: str
    
# ============================================================
# Application Update
# ============================================================


class ApplicationUpdate(BaseModel):
    """
    Generic application metadata update.

    Pipeline decisions should preferably go through the
    recruiter action/review endpoints rather than directly
    modifying pipeline_stage.
    """

    recruiter_comments: Optional[str] = None