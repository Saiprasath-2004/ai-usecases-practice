"""Domain models for the ATS recruiter product."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from sqlmodel import SQLModel, Field as SQLField

# --- Enums ---

class PipelineStage(str, Enum):
    """Candidate pipeline stages."""
    SHORTLISTED = "Shortlisted"
    NEEDS_REVIEW = "Needs Review"
    REJECTED = "Rejected"
    ON_HOLD = "On Hold"

class EvaluationStatus(str, Enum):
    """Status of an evaluation run."""
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"

class RunStatus(str, Enum):
    """Status of a specific evaluation run."""
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"

class ActorType(str, Enum):
    """Who performed the action."""
    SYSTEM = "System"
    RECRUITER = "Recruiter"
    CANDIDATE = "Candidate"

class ActionType(str, Enum):
    """Types of recruiter actions."""
    SCHEDULE_INTERVIEW = "Schedule Interview"
    HOLD = "On Hold"
    REJECT = "Rejected"
    MOVE_TO_REVIEW = "Needs Review"
    APPROVE_FOLLOWUP = "Approve Followup"
    RETURN_TO_PIPELINE = "Return to Pipeline"

# --- Models ---

class JobRequisition(SQLModel, table=True):
    """A job opening that candidates apply to."""
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = SQLField(default=None, primary_key=True)

    title: str
    department: str
    location: str
    employment_type: str
    job_description_text: str
    job_description_source: str  # File path or reference
    required_skills: str = SQLField(default="", sa_column_kwargs={"server_default": "''"}) # JSON encoded
    evaluation_status: str = "Active"

class CandidateProfile(SQLModel, table=True):
    """Extracted candidate information."""
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = SQLField(default=None, primary_key=True)

    application_id: str = SQLField(foreign_key="application.application_id")
    full_name: str
    email: str
    skills: str = "" # JSON encoded
    keywords: str = "" # JSON encoded
    responsibilities: str = "" # JSON encoded
    experience_years: Optional[float] = None

class Application(SQLModel, table=True):
    """The primary record for a candidate's application to a job."""
    __table_args__ = {"extend_existing": True}
    application_id: str = SQLField(primary_key=True)

    job_requisition_id: Optional[int] = SQLField(default=None, foreign_key="jobrequisition.id")
    candidate_id: Optional[int] = SQLField(default=None, foreign_key="candidateprofile.id")
    candidate_name: str
    candidate_email: str
    resume_path: str
    submission_date: datetime = SQLField(default_factory=datetime.utcnow)
    pipeline_stage: PipelineStage = SQLField(default=PipelineStage.NEEDS_REVIEW)
    evaluation_status: EvaluationStatus = SQLField(default=EvaluationStatus.PENDING)
    evaluation_thread_id: Optional[str] = None  # The current run's thread, NOT application identity

    # Scoring results (updated by evaluation runs)
    overall_score: Optional[float] = None
    score_breakdown: str = "" # JSON
    matched_skills: str = "" # JSON
    missing_skills: str = "" # JSON
    strengths: str = "" # JSON
    gaps: str = "" # JSON
    responsibilities_matched: str = "" # JSON
    responsibilities_missing: str = "" # JSON
    experience_result: str = "" # JSON

    recruiter_comments: Optional[str] = None
    follow_up_status: str = "None"
    interview_status: str = "None"

class EvaluationRun(SQLModel, table=True):
    """An instance of evaluating an application."""
    __table_args__ = {"extend_existing": True}
    run_id: Optional[int] = SQLField(default=None, primary_key=True)

    application_id: str = SQLField(foreign_key="application.application_id")
    thread_id: str
    status: RunStatus = SQLField(default=RunStatus.PENDING)
    started_at: datetime = SQLField(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

class EvaluationResult(SQLModel, table=True):
    """The output of a completed evaluation run."""
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = SQLField(default=None, primary_key=True)

    run_id: int = SQLField(foreign_key="evaluationrun.run_id")
    application_id: str = SQLField(foreign_key="application.application_id")
    score: float
    breakdown: str = "" # JSON
    evidence: str = "" # JSON
    narrative: str = ""

class RecruiterAction(SQLModel, table=True):
    """An audit log of recruiter decisions."""
    __table_args__ = {"extend_existing": True}
    action_id: Optional[int] = SQLField(default=None, primary_key=True)

    application_id: str = SQLField(foreign_key="application.application_id")
    actor: str
    action_type: ActionType
    timestamp: datetime = SQLField(default_factory=datetime.utcnow)
    note: Optional[str] = None

class InterviewSlot(SQLModel, table=True):
    """Stub for interview scheduling."""
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = SQLField(default=None, primary_key=True)

    job_requisition_id: int = SQLField(foreign_key="jobrequisition.id")
    start_time: datetime
    end_time: datetime
    status: str = "Available"

class Interview(SQLModel, table=True):
    """Stub for interview records."""
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = SQLField(default=None, primary_key=True)

    application_id: str = SQLField(foreign_key="application.application_id")
    slot_id: int = SQLField(foreign_key="interviewslot.id")
    scheduled_at: datetime
    status: str = "Scheduled"

class FollowUpRequest(SQLModel, table=True):
    """Stub for follow-up requests."""
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = SQLField(default=None, primary_key=True)

    application_id: str = SQLField(foreign_key="application.application_id")
    request_text: str
    sent_at: datetime = SQLField(default_factory=datetime.utcnow)
    status: str = "Pending"

class CandidateReply(SQLModel, table=True):
    """Stub for candidate replies."""
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = SQLField(default=None, primary_key=True)

    follow_up_id: int = SQLField(foreign_key="followuprequest.id")
    reply_text: str
    received_at: datetime = SQLField(default_factory=datetime.utcnow)

class AuditEvent(SQLModel, table=True):
    """Universal audit trail for all state changes."""
    __table_args__ = {"extend_existing": True}
    event_id: Optional[int] = SQLField(default=None, primary_key=True)

    application_id: str = SQLField(foreign_key="application.application_id")
    event_type: str
    actor: ActorType
    payload: str # JSON
    timestamp: datetime = SQLField(default_factory=datetime.utcnow)
