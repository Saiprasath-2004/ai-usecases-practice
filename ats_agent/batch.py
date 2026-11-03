"""Bulk evaluation of every pending application for a job, using the
evaluation-only ATS graph (see ats_agent.graph.builder). Since the graph no
longer interrupts or auto-emails, every invoke() call here is guaranteed to
either finish (score computed, or an extraction error captured) or raise, so
each application's status is always resolved to COMPLETED or FAILED.
"""

import asyncio
import uuid
import json
from datetime import datetime

from ats_agent.graph.builder import build_graph
from ats_agent.domain.models import (
    JobRequisition,
    Application,
    EvaluationRun,
    EvaluationResult,
    RunStatus,
    EvaluationStatus,
    PipelineStage,
)
from ats_agent.persistence.database import Database


class BulkEvaluator:
    def __init__(self, db: Database):
        self.db = db
        self.graph = build_graph()

    async def evaluate_application(self, application_id: str, jd_path: str):
        """Evaluates a single application and persists the results."""
        with self.db.get_session() as session:
            app = session.get(Application, application_id)
            if not app:
                print(f"Application {application_id} not found.")
                return
            resume_path = app.resume_path

        thread_id = f"eval_{uuid.uuid4().hex}"

        with self.db.get_session() as session:
            run = EvaluationRun(
                application_id=application_id,
                thread_id=thread_id,
                status=RunStatus.RUNNING,
                started_at=datetime.utcnow()
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            run_id = run.run_id

            app_db = session.get(Application, application_id)
            if app_db:
                app_db.evaluation_thread_id = thread_id
                app_db.evaluation_status = EvaluationStatus.RUNNING
                session.add(app_db)
                session.commit()

        try:
            final_state = await asyncio.to_thread(
                self.graph.invoke,
                {"resume_path": resume_path, "jd_path": jd_path},
                config={"configurable": {"thread_id": thread_id}}
            )

            extraction_error = final_state.get("jd_extraction_error") or final_state.get("resume_extraction_error")
            if extraction_error:
                raise RuntimeError(extraction_error)

            result_data = final_state.get("result", {})  # {overall_score, skill_score, experience_score, ...}
            evidence = final_state.get("evidence", {})    # {skills: {matched, missing}, responsibilities: {...}, ...}
            overall_score = result_data.get("overall_score")

            matched_skills = evidence.get("skills", {}).get("matched", [])
            missing_skills = evidence.get("skills", {}).get("missing", [])
            responsibilities_matched = evidence.get("responsibilities", {}).get("matched", [])
            responsibilities_missing = evidence.get("responsibilities", {}).get("missing", [])

            with self.db.get_session() as session:
                eval_res = EvaluationResult(
                    run_id=run_id,
                    application_id=application_id,
                    score=overall_score if overall_score is not None else 0.0,
                    breakdown=json.dumps(result_data),
                    evidence=json.dumps(evidence),
                    narrative=final_state.get("narrative", "")
                )
                session.add(eval_res)

                app_db = session.get(Application, application_id)
                if app_db:
                    app_db.overall_score = overall_score
                    app_db.score_breakdown = json.dumps(result_data)
                    app_db.matched_skills = json.dumps(matched_skills)
                    app_db.missing_skills = json.dumps(missing_skills)
                    app_db.strengths = json.dumps(matched_skills)
                    app_db.gaps = json.dumps(missing_skills)
                    app_db.responsibilities_matched = json.dumps(responsibilities_matched)
                    app_db.responsibilities_missing = json.dumps(responsibilities_missing)

                    # Only auto-move stage if a recruiter hasn't already moved it manually.
                    if app_db.pipeline_stage == PipelineStage.NEEDS_REVIEW:
                        verdict = final_state.get("verdict")
                        if verdict == "SELECT":
                            app_db.pipeline_stage = PipelineStage.SHORTLISTED
                        elif verdict == "REJECT":
                            app_db.pipeline_stage = PipelineStage.REJECTED
                        # ESCALATE / ERROR -> stays NEEDS_REVIEW ("Review" tab)

                    app_db.evaluation_status = EvaluationStatus.COMPLETED
                    session.add(app_db)

                run_db = session.get(EvaluationRun, run_id)
                if run_db:
                    run_db.status = RunStatus.COMPLETED
                    run_db.completed_at = datetime.utcnow()
                    session.add(run_db)

                session.commit()

        except Exception as e:
            print(f"Error evaluating {application_id}: {e}")
            with self.db.get_session() as session:
                run_db = session.get(EvaluationRun, run_id)
                if run_db:
                    run_db.status = RunStatus.FAILED
                    run_db.error = str(e)
                    session.add(run_db)

                app_db = session.get(Application, application_id)
                if app_db:
                    app_db.evaluation_status = EvaluationStatus.FAILED
                    session.add(app_db)
                session.commit()

    async def bulk_evaluate(self, job_id: int):
        """Evaluates all pending applications for a given job, concurrently."""
        job = self.db.get_job(job_id)
        if not job:
            raise ValueError(f"Job Requisition {job_id} not found.")

        jd_path = job.job_description_source

        with self.db.get_session() as session:
            from sqlmodel import select
            statement = select(Application).where(
                Application.job_requisition_id == job_id,
                Application.evaluation_status == EvaluationStatus.PENDING
            )
            applications = session.exec(statement).all()

        if not applications:
            print("No pending applications to evaluate.")
            return

        print(f"Starting bulk evaluation for Job {job_id}: {len(applications)} apps.")

        with self.db.get_session() as session:
            from sqlmodel import select, func
            stmt = select(func.count(EvaluationRun.run_id)).join(Application).where(
                Application.job_requisition_id == job_id,
                EvaluationRun.status == RunStatus.RUNNING
            )
            running_count = session.exec(stmt).one()
            if running_count > 0:
                print(f"Evaluation already in progress ({running_count} running). Please wait.")
                return

        tasks = [self.evaluate_application(app.application_id, jd_path) for app in applications]
        await asyncio.gather(*tasks)
        print("Bulk evaluation complete.")

    async def retry_application(self, application_id: str):
        """Retries evaluation for a single application."""
        with self.db.get_session() as session:
            app = session.get(Application, application_id)
            if not app:
                return
            job = session.get(JobRequisition, app.job_requisition_id)
            jd_path = job.job_description_source if job else "data/jd.txt"

        await self.evaluate_application(application_id, jd_path)


def run_bulk_eval(job_id: int):
    """Synchronous wrapper for bulk evaluation."""
    db = Database()
    evaluator = BulkEvaluator(db)
    asyncio.run(evaluator.bulk_evaluate(job_id))
