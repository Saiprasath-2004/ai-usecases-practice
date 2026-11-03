"""Persistence layer for ATS domain models."""

from typing import List, Optional
from sqlmodel import Session, create_engine, select, func
from ats_agent.domain.models import (
    SQLModel,
    JobRequisition,
    Application,
    EvaluationRun,
    CandidateProfile,
    EvaluationResult,
    RecruiterAction,
    AuditEvent
)

class Database:
    def __init__(self, db_url: str = "sqlite:///ats_business.db"):
        self.engine = create_engine(db_url)
        SQLModel.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        return Session(self.engine)

    def create_job(self, job: JobRequisition) -> JobRequisition:
        with self.get_session() as session:
            session.add(job)
            session.commit()
            session.refresh(job)
            return job

    def create_application(self, app: Application) -> Application:
        with self.get_session() as session:
            session.add(app)
            session.commit()
            session.refresh(app)
            return app

    def create_evaluation_run(self, run: EvaluationRun) -> EvaluationRun:
        with self.get_session() as session:
            session.add(run)
            session.commit()
            session.refresh(run)
            return run

    def get_job(self, job_id: int) -> Optional[JobRequisition]:
        with self.get_session() as session:
            return session.get(JobRequisition, job_id)

    def get_application(self, app_id: str) -> Optional[Application]:
        with self.get_session() as session:
            return session.get(Application, app_id)

    def get_applicant_count(self, job_id: int) -> int:
        with self.get_session() as session:
            statement = select(func.count(Application.application_id)).where(Application.job_requisition_id == job_id)
            return session.exec(statement).one()

    def get_applications_for_job(self, job_id: int) -> List[Application]:
        with self.get_session() as session:
            statement = select(Application).where(Application.job_requisition_id == job_id)
            return session.exec(statement).all()
