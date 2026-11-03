"""Bulk evaluation of applications using the ATS LangGraph workflow."""

import asyncio
import json
import uuid
from datetime import datetime, timezone

from sqlmodel import func, select

from ats_agent.domain.models import (
    Application,
    EvaluationResult,
    EvaluationRun,
    EvaluationStatus,
    JobRequisition,
    RunStatus,
)
from ats_agent.graph.builder import build_graph
from ats_agent.persistence.database import Database


def utc_now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)

class EvaluationProcessingError(Exception):
    def __init__(
        self,
        technical_error: str,
        user_facing_error: str,
    ):
        super().__init__(technical_error)
        self.technical_error = technical_error
        self.user_facing_error = user_facing_error

class BulkEvaluator:
    """
    Run ATS evaluations for applications belonging to a job.

    Responsibilities:
    - create evaluation runs
    - maintain persistent application threads
    - execute the ATS graph
    - persist evaluation results
    - track waiting-for-review state
    - update the application's current evaluation snapshot

    This class does NOT:
    - make recruiter decisions
    - schedule interviews
    - reject candidates
    - send emails
    - perform external recruiter actions
    """

    def __init__(self, db: Database):
        self.db = db
        self.graph = build_graph()

    # ========================================================
    # Single Application Evaluation
    # ========================================================

    async def evaluate_application(
        self,
        application_id: str,
        jd_path: str,
    ) -> None:
        """
        Evaluate a single application.

        Each application has one persistent LangGraph thread.

        The thread survives:
            initial evaluation
                ↓
            human review interrupt
                ↓
            recruiter decision
                ↓
            follow-up / rescore
                ↓
            another human review

        EvaluationRun and EvaluationResult preserve the
        historical evaluation records.
        """

        # ----------------------------------------------------
        # 1. Load application
        # ----------------------------------------------------

        with self.db.get_session() as session:
            application = session.get(
                Application,
                application_id,
            )

            if not application:
                print(
                    f"Application {application_id} not found."
                )
                return

            resume_path = application.resume_path

            # ------------------------------------------------
            # Create persistent application thread once
            # ------------------------------------------------

            if not application.thread_id:
                application.thread_id = (
                    f"application_{uuid.uuid4().hex}"
                )

                session.add(application)
                session.commit()

            thread_id = application.thread_id

            # ------------------------------------------------
            # Prevent duplicate active evaluation
            # ------------------------------------------------

            running_run = session.exec(
                select(EvaluationRun).where(
                    EvaluationRun.application_id
                    == application_id,
                    EvaluationRun.status
                    == RunStatus.RUNNING,
                )
            ).first()

            if running_run:
                print(
                    f"Application {application_id} "
                    f"already has a running evaluation."
                )
                return

        # ----------------------------------------------------
        # 2. Create EvaluationRun
        # ----------------------------------------------------

        with self.db.get_session() as session:
            run = EvaluationRun(
                application_id=application_id,
                thread_id=thread_id,
                status=RunStatus.RUNNING,
                started_at=utc_now(),
            )

            session.add(run)
            session.commit()
            session.refresh(run)

            run_id = run.run_id

            # -----------------------------------------------
            # Update Application evaluation state
            # -----------------------------------------------

            application = session.get(
                Application,
                application_id,
            )

            if application:
                application.evaluation_status = (
                    EvaluationStatus.RUNNING
                )

                application.current_evaluation_run_id = run_id

                session.add(application)
                session.commit()

        # ----------------------------------------------------
        # 3. Execute LangGraph
        # ----------------------------------------------------

        try:
            final_state = await asyncio.to_thread(
                self.graph.invoke,
                {
                    "resume_path": resume_path,
                    "jd_path": jd_path,
                },
                config={
                    "configurable": {
                        "thread_id": thread_id,
                    }
                },
            )

            # ------------------------------------------------
            # 4. Determine whether graph is waiting for human
            # ------------------------------------------------

            state_snapshot = self.graph.get_state(
                {
                    "configurable": {
                        "thread_id": thread_id,
                    }
                }
            )

            waiting_for_review = bool(
                state_snapshot.next
            )

            # ------------------------------------------------
            # 5. Extract graph result
            # ------------------------------------------------

            result_data = final_state.get(
                "result",
                {},
            )

            matches = final_state.get(
                "matches",
                {},
            )

            evidence = final_state.get(
                "evidence",
                {},
            )

            narrative = final_state.get(
                "narrative",
                "",
            )

            overall_score = result_data.get(
                "overall_score"
            )

            # ------------------------------------------------
            # 5A. Detect early graph termination / failure
            # ------------------------------------------------

            if overall_score is None:

                technical_error = (
                    final_state.get("escalation_reason")
                    or final_state.get("jd_extraction_error")
                    or final_state.get("resume_extraction_error")
                    or "Evaluation did not produce an ATS score."
                )

                recruiter_message = (
                    "This resume could not be processed because it contains "
                    "instructions or content that cannot be safely interpreted "
                    "as candidate information. No ATS score was generated. "
                    "Please review the resume manually or upload a revised version."
                )

                raise EvaluationProcessingError(
                    technical_error=technical_error,
                    user_facing_error=recruiter_message,
                )

            # ------------------------------------------------
            # 6. Persist successful EvaluationResult
            # ------------------------------------------------

            with self.db.get_session() as session:

                evaluation_result = EvaluationResult(
                    run_id=run_id,
                    application_id=application_id,
                    score=float(overall_score),
                    breakdown=json.dumps(
                        result_data
                    ),
                    evidence=json.dumps(
                        evidence
                    ),
                    narrative=narrative,
                )

                session.add(evaluation_result)

                # --------------------------------------------
                # Update current Application snapshot
                # --------------------------------------------

                application = session.get(
                    Application,
                    application_id,
                )

                if application:

                    application.overall_score = (
                        overall_score
                    )

                    application.score_breakdown = json.dumps(
                        result_data
                    )

                    application.matched_skills = json.dumps(
                        matches.get(
                            "matched_skills",
                            [],
                        )
                    )

                    application.missing_skills = json.dumps(
                        matches.get(
                            "missing_skills",
                            [],
                        )
                    )

                    application.strengths = json.dumps({
                        "skills": matches.get(
                            "matched_skills",
                            [],
                        ),
                        "keywords": matches.get(
                            "matched_keywords",
                            [],
                        ),
                        "responsibilities": matches.get(
                            "matched_responsibilities",
                            [],
                        ),
                    })

                    application.gaps = json.dumps({
                        "skills": matches.get(
                            "missing_skills",
                            [],
                        ),
                        "keywords": matches.get(
                            "missing_keywords",
                            [],
                        ),
                        "responsibilities": matches.get(
                            "missing_responsibilities",
                            [],
                        ),
                    })

                    application.responsibilities_matched = (
                        json.dumps(
                            matches.get(
                                "matched_responsibilities",
                                [],
                            )
                        )
                    )

                    application.responsibilities_missing = (
                        json.dumps(
                            matches.get(
                                "missing_responsibilities",
                                [],
                            )
                        )
                    )

                    application.experience_result = json.dumps({
                        "candidate_years": matches.get(
                            "candidate_experience_years"
                        ),
                        "required_min_years": matches.get(
                            "required_experience_min"
                        ),
                        "required_max_years": matches.get(
                            "required_experience_max"
                        ),
                        "status": matches.get(
                            "experience_status"
                        ),
                        "matches_requirement": matches.get(
                            "experience_match"
                        ),
                    })

                    # ----------------------------------------
                    # IMPORTANT:
                    #
                    # Do NOT change pipeline_stage here.
                    #
                    # The graph's verdict is an AI
                    # recommendation.
                    #
                    # Recruiter action is handled later
                    # through the human-review/API layer.
                    # ----------------------------------------

                    application.evaluation_status = (
                        EvaluationStatus.COMPLETED
                    )

                    session.add(application)

                # --------------------------------------------
                # Update EvaluationRun
                # --------------------------------------------

                run_db = session.get(
                    EvaluationRun,
                    run_id,
                )

                if run_db:

                    if waiting_for_review:
                        run_db.status = (
                            RunStatus.WAITING_REVIEW
                        )
                    else:
                        run_db.status = (
                            RunStatus.COMPLETED
                        )

                    run_db.completed_at = utc_now()

                    session.add(run_db)

                session.commit()

            # ------------------------------------------------
            # 7. Logging
            # ------------------------------------------------

            if waiting_for_review:
                print(
                    f"Application {application_id} "
                    f"evaluation completed and is waiting "
                    f"for recruiter review."
                )
            else:
                print(
                    f"Application {application_id} "
                    f"evaluation completed."
                )

        # ----------------------------------------------------
        # 8. Evaluation failure
        # ----------------------------------------------------

        except EvaluationProcessingError as exc:

            print(
                f"Evaluation failed for {application_id}: "
                f"{exc.technical_error}"
            )

            with self.db.get_session() as session:

                run_db = session.get(
                    EvaluationRun,
                    run_id,
                )

                if run_db:
                    run_db.status = RunStatus.FAILED
                    run_db.error = exc.technical_error
                    run_db.user_facing_error = exc.user_facing_error
                    run_db.completed_at = utc_now()

                    session.add(run_db)

                application = session.get(
                    Application,
                    application_id,
                )

                if application:
                    application.evaluation_status = (
                        EvaluationStatus.FAILED
                    )

                    session.add(application)

                session.commit()


        except Exception as exc:

            print(
                f"Unexpected error evaluating "
                f"{application_id}: {exc}"
            )

            with self.db.get_session() as session:

                run_db = session.get(
                    EvaluationRun,
                    run_id,
                )

                if run_db:
                    run_db.status = RunStatus.FAILED
                    run_db.error = str(exc)
                    run_db.user_facing_error = (
                        "The ATS evaluation could not be completed. "
                        "Please try again or review the resume manually."
                    )
                    run_db.completed_at = utc_now()

                    session.add(run_db)

                application = session.get(
                    Application,
                    application_id,
                )

                if application:
                    application.evaluation_status = (
                        EvaluationStatus.FAILED
                    )

                    session.add(application)

                session.commit()

    # ========================================================
    # Bulk Evaluation
    # ========================================================

    async def bulk_evaluate(
        self,
        job_id: int,
    ) -> None:
        """
        Evaluate all pending applications for a job.

        Applications are evaluated concurrently.
        """

        # ----------------------------------------------------
        # 1. Get job
        # ----------------------------------------------------

        job = self.db.get_job(
            job_id
        )

        if not job:
            raise ValueError(
                f"Job Requisition {job_id} not found."
            )

        jd_path = job.job_description_source

        # ----------------------------------------------------
        # 2. Get pending applications
        # ----------------------------------------------------

        with self.db.get_session() as session:

            statement = select(Application).where(
                Application.job_requisition_id == job_id,
                Application.evaluation_status
                == EvaluationStatus.PENDING,
            )

            applications = session.exec(
                statement
            ).all()

        if not applications:
            print(
                f"No pending applications for "
                f"Job {job_id}."
            )
            return

        # ----------------------------------------------------
        # 3. Prevent overlapping job evaluation
        # ----------------------------------------------------

        with self.db.get_session() as session:

            statement = (
                select(
                    func.count(
                        EvaluationRun.run_id
                    )
                )
                .join(Application)
                .where(
                    Application.job_requisition_id
                    == job_id,
                    EvaluationRun.status
                    == RunStatus.RUNNING,
                )
            )

            running_count = session.exec(
                statement
            ).one()

        if running_count > 0:
            print(
                f"Evaluation already in progress "
                f"({running_count} running)."
            )
            return

        print(
            f"Starting bulk evaluation for Job "
            f"{job_id}: {len(applications)} applications."
        )

        # ----------------------------------------------------
        # 4. Run applications concurrently
        # ----------------------------------------------------

        tasks = [
            self.evaluate_application(
                application_id=application.application_id,
                jd_path=jd_path,
            )
            for application in applications
        ]

        await asyncio.gather(
            *tasks
        )

        print(
            f"Bulk evaluation completed for "
            f"Job {job_id}."
        )

    # ========================================================
    # Retry
    # ========================================================

    async def retry_application(
        self,
        application_id: str,
    ) -> None:
        """
        Retry evaluation for one application.
        """

        with self.db.get_session() as session:

            application = session.get(
                Application,
                application_id,
            )

            if not application:
                print(
                    f"Application {application_id} "
                    f"not found."
                )
                return

            job = session.get(
                JobRequisition,
                application.job_requisition_id,
            )

            if not job:
                raise ValueError(
                    f"Job for application "
                    f"{application_id} not found."
                )

            jd_path = job.job_description_source

        await self.evaluate_application(
            application_id=application_id,
            jd_path=jd_path,
        )


# ============================================================
# Synchronous Entry Point
# ============================================================


def run_bulk_eval(
    job_id: int,
) -> None:
    """
    Synchronous wrapper for bulk evaluation.

    Used by code that is not already running inside
    an async event loop.
    """

    db = Database()

    evaluator = BulkEvaluator(
        db
    )

    asyncio.run(
        evaluator.bulk_evaluate(
            job_id
        )
    )