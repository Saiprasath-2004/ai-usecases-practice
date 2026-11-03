"""Domain models for the ATS recruiter product."""

from datetime import date, datetime, time
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field as SQLField


# ============================================================
# Enums
# ============================================================


class PipelineStage(str, Enum):
    """Candidate pipeline stages."""

    SHORTLISTED = "Shortlisted"
    NEEDS_REVIEW = "Needs Review"
    REJECTED = "Rejected"
    ON_HOLD = "On Hold"


class EvaluationStatus(str, Enum):
    """Current status of an application's evaluation."""

    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"


class RunStatus(str, Enum):
    """Status of a specific evaluation run."""

    PENDING = "Pending"
    RUNNING = "Running"
    WAITING_REVIEW = "Waiting for Review"
    COMPLETED = "Completed"
    FAILED = "Failed"


class ActorType(str, Enum):
    """Who performed an action or caused an event."""

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


# ============================================================
# Job Requisition
# ============================================================


class JobRequisition(SQLModel, table=True):
    """A job opening that candidates can apply to."""

    __table_args__ = {"extend_existing": True}

    id: Optional[int] = SQLField(
        default=None,
        primary_key=True,
    )

    title: str

    department: str

    location: str

    employment_type: str

    job_description_text: str

    job_description_source: str
    """File path or external reference for the JD."""

    required_skills: str = SQLField(
        default="",
        sa_column_kwargs={
            "server_default": "''",
        },
    )
    """JSON-encoded required skills."""

    evaluation_status: str = "Active"


# ============================================================
# Candidate Profile
# ============================================================


class CandidateProfile(SQLModel, table=True):
    """Extracted candidate information."""

    __table_args__ = {"extend_existing": True}

    id: Optional[int] = SQLField(
        default=None,
        primary_key=True,
    )

    application_id: str = SQLField(
        foreign_key="application.application_id"
    )

    full_name: str

    email: str

    skills: str = ""
    """JSON-encoded skills."""

    keywords: str = ""
    """JSON-encoded keywords."""

    responsibilities: str = ""
    """JSON-encoded responsibilities."""

    experience_years: Optional[float] = None


# ============================================================
# Application
# ============================================================


class Application(SQLModel, table=True):
    """
    The primary record for a candidate's application.

    This stores the candidate's current ATS state and current
    evaluation snapshot. Historical evaluations are stored in
    EvaluationRun and EvaluationResult.
    """

    __table_args__ = {"extend_existing": True}

    application_id: str = SQLField(
        primary_key=True
    )

    job_requisition_id: Optional[int] = SQLField(
        default=None,
        foreign_key="jobrequisition.id",
    )

    candidate_id: Optional[int] = SQLField(
        default=None,
        foreign_key="candidateprofile.id",
    )

    candidate_name: str

    candidate_email: str

    resume_path: str

    submission_date: datetime = SQLField(
        default_factory=datetime.utcnow
    )

    # --------------------------------------------------------
    # Pipeline state
    # --------------------------------------------------------

    pipeline_stage: PipelineStage = SQLField(
        default=PipelineStage.NEEDS_REVIEW
    )

    # --------------------------------------------------------
    # Evaluation state
    # --------------------------------------------------------

    evaluation_status: EvaluationStatus = SQLField(
        default=EvaluationStatus.PENDING
    )

    # Persistent LangGraph thread for this application.
    #
    # This is intentionally stored on Application rather than
    # generating a new thread for every evaluation.
    thread_id: Optional[str] = None

    # Points to the latest evaluation run.
    current_evaluation_run_id: Optional[int] = SQLField(
        default=None,
        foreign_key="evaluationrun.run_id",
    )

    # --------------------------------------------------------
    # Current scoring snapshot
    # --------------------------------------------------------

    overall_score: Optional[float] = None

    score_breakdown: str = ""
    """JSON-encoded score breakdown."""

    matched_skills: str = ""
    """JSON-encoded matched skills."""

    missing_skills: str = ""
    """JSON-encoded missing skills."""

    strengths: str = ""
    """JSON-encoded candidate strengths."""

    gaps: str = ""
    """JSON-encoded candidate gaps."""

    responsibilities_matched: str = ""
    """JSON-encoded matched responsibilities."""

    responsibilities_missing: str = ""
    """JSON-encoded missing responsibilities."""

    experience_result: str = ""
    """JSON-encoded experience evaluation."""

    # --------------------------------------------------------
    # Recruiter / workflow state
    # --------------------------------------------------------

    recruiter_comments: Optional[str] = None

    follow_up_status: str = "None"

    interview_status: str = "None"


# ============================================================
# Evaluation Run
# ============================================================


class EvaluationRun(SQLModel, table=True):
    """
    One execution of the ATS evaluation workflow.

    Multiple EvaluationRun records can exist for the same
    application, preserving evaluation history.
    """

    __table_args__ = {"extend_existing": True}

    run_id: Optional[int] = SQLField(
        default=None,
        primary_key=True,
    )

    application_id: str = SQLField(
        foreign_key="application.application_id"
    )

    # LangGraph thread used by this evaluation.
    thread_id: str

    status: RunStatus = SQLField(
        default=RunStatus.PENDING
    )

    started_at: datetime = SQLField(
        default_factory=datetime.utcnow
    )

    completed_at: Optional[datetime] = None

    error: Optional[str] = None
    user_facing_error: Optional[str] = None


# ============================================================
# Evaluation Result
# ============================================================


class EvaluationResult(SQLModel, table=True):
    """
    Immutable result produced by an evaluation run.

    Historical results should not be overwritten when a new
    evaluation is performed.
    """

    __table_args__ = {"extend_existing": True}

    id: Optional[int] = SQLField(
        default=None,
        primary_key=True,
    )

    run_id: int = SQLField(
        foreign_key="evaluationrun.run_id"
    )

    application_id: str = SQLField(
        foreign_key="application.application_id"
    )

    score: float

    breakdown: str = ""
    """JSON-encoded score breakdown."""

    evidence: str = ""
    """JSON-encoded evidence."""

    narrative: str = ""


# ============================================================
# Recruiter Action
# ============================================================


class RecruiterAction(SQLModel, table=True):
    """Audit log of recruiter decisions/actions."""

    __table_args__ = {"extend_existing": True}

    action_id: Optional[int] = SQLField(
        default=None,
        primary_key=True,
    )

    application_id: str = SQLField(
        foreign_key="application.application_id"
    )

    actor: str

    action_type: ActionType

    timestamp: datetime = SQLField(
        default_factory=datetime.utcnow
    )

    note: Optional[str] = None

# ============================================================
# Recruiter Availability
# ============================================================


class RecruiterAvailability(SQLModel, table=True):
    """
    Recurring weekly availability for a recruiter.

    Example:
        Monday    10:00 - 17:00
        Tuesday   10:00 - 17:00
        Wednesday 10:00 - 17:00

    day_of_week:
        Monday = 0
        Tuesday = 1
        ...
        Sunday = 6
    """

    __table_args__ = {"extend_existing": True}

    id: Optional[int] = SQLField(
        default=None,
        primary_key=True,
    )

    recruiter_id: str

    day_of_week: int

    start_time: time

    end_time: time

    active: bool = True

# ============================================================
# Calendar Block
# ============================================================


class CalendarBlock(SQLModel, table=True):
    """
    A temporary period during which the recruiter is unavailable.

    Supports both:
        - partial-day blocking
        - full-day blocking

    Examples:
        2026-09-25 13:00 -> 15:00
        2026-09-26 00:00 -> 23:59 (all_day=True)
    """

    __table_args__ = {"extend_existing": True}

    id: Optional[int] = SQLField(
        default=None,
        primary_key=True,
    )

    recruiter_id: str

    start_at: datetime

    end_at: datetime

    all_day: bool = False

    reason: Optional[str] = None

# ============================================================
# Interview Slot
# ============================================================


class InterviewSlot(SQLModel, table=True):
    """Available interview slot."""

    __table_args__ = {"extend_existing": True}

    id: Optional[int] = SQLField(
        default=None,
        primary_key=True,
    )

    job_requisition_id: int = SQLField(
        foreign_key="jobrequisition.id"
    )

    start_time: datetime

    end_time: datetime

    status: str = "Available"

# ============================================================
# Interview
# ============================================================


class Interview(SQLModel, table=True):
    """Interview scheduled for an application."""

    __table_args__ = {"extend_existing": True}

    id: Optional[int] = SQLField(
        default=None,
        primary_key=True,
    )

    application_id: str = SQLField(
        foreign_key="application.application_id"
    )

    recruiter_id: str

    scheduled_at: datetime

    duration_minutes: int = 60

    # --------------------------------------------------------
    # Interview lifecycle
    # --------------------------------------------------------

    status: str = "PendingInvitation"

    # --------------------------------------------------------
    # Candidate invitation lifecycle
    # --------------------------------------------------------

    invitation_status: str = "PENDING"

    invitation_action_id: Optional[str] = None

    # --------------------------------------------------------
    # Candidate response lifecycle
    # --------------------------------------------------------

    candidate_response: str = "AWAITING_RESPONSE"

    candidate_responded_at: Optional[datetime] = None

    # --------------------------------------------------------
    # Calendar provider information
    # --------------------------------------------------------

    provider: Optional[str] = None

    external_event_id: Optional[str] = None

    meeting_url: Optional[str] = None

    candidate_email: str

    notes: Optional[str] = None

# ============================================================
# Follow-Up Request
# ============================================================


class FollowUpRequest(SQLModel, table=True):
    """Request sent to a candidate for additional information."""

    __table_args__ = {"extend_existing": True}

    id: Optional[int] = SQLField(
        default=None,
        primary_key=True,
    )

    application_id: str = SQLField(
        foreign_key="application.application_id"
    )

    request_text: str

    sent_at: Optional[datetime] = None

    status: str = "Pending"


# ============================================================
# Candidate Reply
# ============================================================


class CandidateReply(SQLModel, table=True):
    """Candidate response to a follow-up request."""

    __table_args__ = {"extend_existing": True}

    id: Optional[int] = SQLField(
        default=None,
        primary_key=True,
    )

    follow_up_id: int = SQLField(
        foreign_key="followuprequest.id"
    )

    reply_text: str

    received_at: datetime = SQLField(
        default_factory=datetime.utcnow
    )


class PublicHoliday(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = SQLField(default=None, primary_key=True)
    holiday_date: date
    name: str
    active: bool = True


# ============================================================
# Audit Event
# ============================================================


class AuditEvent(SQLModel, table=True):
    """Universal audit trail for application state changes."""

    __table_args__ = {"extend_existing": True}

    event_id: Optional[int] = SQLField(
        default=None,
        primary_key=True,
    )

    application_id: str = SQLField(
        foreign_key="application.application_id"
    )

    event_type: str

    actor: ActorType

    payload: str
    """JSON-encoded event payload."""

    timestamp: datetime = SQLField(
        default_factory=datetime.utcnow
    )