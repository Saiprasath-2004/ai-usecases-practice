from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from ats_agent.domain.models import PipelineStage, EvaluationStatus

class ApplicationRead(BaseModel):
    application_id: str
    candidate_name: str
    candidate_email: str
    pipeline_stage: PipelineStage
    overall_score: Optional[float] = None
    evaluation_status: EvaluationStatus
    evaluation_verdict: Optional[str] = None
    resume_path: str

    class Config:
        from_attributes = True

class ApplicationDetailRead(ApplicationRead):
    job_requisition_id: Optional[int] = None
    score_breakdown: str = ""
    matched_skills: str = ""
    missing_skills: str = ""
    strengths: str = ""
    gaps: str = ""
    responsibilities_matched: str = ""
    responsibilities_missing: str = ""
    experience_result: str = ""
    follow_up_status: str = "None"
    interview_status: str = "None"
    recruiter_comments: Optional[str] = None


class ApplicationListResponse(BaseModel):
    # Grouped by pipeline stage
    applications: Dict[PipelineStage, List[ApplicationRead]]

class ActionRequest(BaseModel):
    action_type: str = Field(..., description="Type of action to perform (e.g., HOLD, REJECT, MOVE_TO_REVIEW)")
    note: Optional[str] = None

class ApplicationUpdate(BaseModel):
    pipeline_stage: Optional[PipelineStage] = None
    recruiter_comments: Optional[str] = None


class RejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="Recruiter's reasoning for the rejection, included in the candidate email")


class HoldRequest(BaseModel):
    note: Optional[str] = None


class FollowupReplyRequest(BaseModel):
    reply_text: str = Field(..., description="The candidate's answer to the follow-up questions")
