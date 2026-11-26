import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.enums import SessionStatus
from app.infrastructure.persistence.models.snapshot import AbilitySnapshotModel
from app.infrastructure.persistence.repositories import (
    AssessmentSessionRepository,
    AssessmentProfileRepository,
    QuestionRepository,
    AssessmentResponseRepository,
    AbilitySnapshotRepository,
    AssessmentReportRepository,
)
from app.application.services.start_assessment import StartAssessmentService
from app.application.services.next_question import NextQuestionService
from app.application.services.submit_answer import SubmitAnswerService
from app.application.services.assessment_report import AssessmentReportService
from app.application.dto import (
    StartAssessmentCommand,
    StartAssessmentResultDTO,
    NextQuestionQuery,
    NextQuestionResultDTO,
    SubmitAnswerCommand,
    SubmitAnswerResultDTO,
    SessionSummaryDTO,
    AbilitySnapshotDTO,
    AbilityHistoryResponseDTO,
    AssessmentReportDTO,
)
from app.application.exceptions import (
    SessionNotFoundError,
    SessionAccessForbiddenError,
    SessionNotActiveError,
    ProfileNotFoundError,
)


class AssessmentWorkflowOrchestrator:
    """
    Application Workflow Orchestrator implementing TASK-028, TASK-031, and TASK-032.
    Coordinates the complete assessment session lifecycle:
    - Initiates sessions and records initial ability snapshot
    - Fetches next questions and records stopping decisions
    - Transitions session state to COMPLETED upon termination criteria
    - Captures immutable AbilitySnapshot upon non-retry answer submissions
    - Generates and retrieves final assessment diagnostic reports
    - Provides historical ability snapshot tracking
    """

    def __init__(
        self,
        db_session: AsyncSession,
        session_repo: Optional[AssessmentSessionRepository] = None,
        profile_repo: Optional[AssessmentProfileRepository] = None,
        question_repo: Optional[QuestionRepository] = None,
        response_repo: Optional[AssessmentResponseRepository] = None,
        snapshot_repo: Optional[AbilitySnapshotRepository] = None,
        report_repo: Optional[AssessmentReportRepository] = None,
        start_service: Optional[StartAssessmentService] = None,
        next_service: Optional[NextQuestionService] = None,
        submit_service: Optional[SubmitAnswerService] = None,
        report_service: Optional[AssessmentReportService] = None,
    ):
        self.db = db_session
        self.session_repo = session_repo or AssessmentSessionRepository(db_session)
        self.profile_repo = profile_repo or AssessmentProfileRepository(db_session)
        self.question_repo = question_repo or QuestionRepository(db_session)
        self.response_repo = response_repo or AssessmentResponseRepository(db_session)
        self.snapshot_repo = snapshot_repo or AbilitySnapshotRepository(db_session)
        self.report_repo = report_repo or AssessmentReportRepository(db_session)

        self.start_service = start_service or StartAssessmentService(
            db_session=db_session,
            session_repo=self.session_repo,
            profile_repo=self.profile_repo,
        )
        self.next_service = next_service or NextQuestionService(
            db_session=db_session,
            session_repo=self.session_repo,
            profile_repo=self.profile_repo,
            question_repo=self.question_repo,
        )
        self.submit_service = submit_service or SubmitAnswerService(
            db_session=db_session,
            session_repo=self.session_repo,
            response_repo=self.response_repo,
            question_repo=self.question_repo,
        )
        self.report_service = report_service or AssessmentReportService(
            db_session=db_session,
            session_repo=self.session_repo,
            profile_repo=self.profile_repo,
            snapshot_repo=self.snapshot_repo,
            report_repo=self.report_repo,
        )

    async def start_assessment(self, command: StartAssessmentCommand) -> StartAssessmentResultDTO:
        """
        Coordinates session initiation workflow and records baseline snapshot (sequence 0).
        """
        result = await self.start_service.execute(command)

        # Record Initial AbilitySnapshot (TASK-032)
        initial_snapshot = AbilitySnapshotModel(
            id=str(uuid.uuid4()),
            student_id=result.student_id,
            session_id=result.session_id,
            snapshot_sequence=0,
            ability_scores=result.initial_scores,
            uncertainty_scores=result.initial_uncertainty,
            dimension_coverage={dim: 0 for dim in result.target_dimensions},
            answered_question_count=0,
            algorithm_version=result.algorithm_version,
            checkpoint_type="INITIAL_STATE",
        )
        await self.snapshot_repo.create_snapshot(initial_snapshot)

        return result

    async def get_next_question(self, query: NextQuestionQuery) -> NextQuestionResultDTO:
        """
        Coordinates next question workflow.
        If stopping criteria are triggered, automatically transitions session to COMPLETED
        and records final completion snapshot.
        """
        result = await self.next_service.execute(query)

        # If the assessment reached a terminal stopping condition, complete the session
        if result.should_stop:
            session = await self.session_repo.get_by_id(query.session_id, for_update=True)
            if session and session.status == SessionStatus.IN_PROGRESS.value:
                now_utc = datetime.now(timezone.utc)
                session.status = SessionStatus.COMPLETED.value
                session.completed_at = now_utc
                session.last_activity_at = now_utc

                # Persist completion metadata
                meta = dict(session.context_metadata or {})
                meta["completion_reason"] = result.stopping_reason
                meta["completion_detail"] = result.stopping_detail
                meta["completed_at"] = now_utc.isoformat()
                session.context_metadata = meta

                # Record completion snapshot if not already present for this sequence
                raw_ability = meta.get("ability_state", {})
                existing_snapshots = await self.snapshot_repo.get_by_session_id(session.id)
                next_seq = (existing_snapshots[-1].snapshot_sequence + 1) if existing_snapshots else 1

                completion_snapshot = AbilitySnapshotModel(
                    id=str(uuid.uuid4()),
                    student_id=session.student_id,
                    session_id=session.id,
                    snapshot_sequence=next_seq,
                    ability_scores=raw_ability.get("dimension_scores", {}),
                    uncertainty_scores=raw_ability.get("uncertainty", {}),
                    dimension_coverage=raw_ability.get("dimension_coverage", {}),
                    answered_question_count=len(session.responses),
                    algorithm_version=session.algorithm_version,
                    checkpoint_type="SESSION_COMPLETED",
                )
                try:
                    await self.snapshot_repo.create_snapshot(completion_snapshot)
                    await self.db.flush()
                except IntegrityError:
                    # Concurrent finalization already inserted completion snapshot
                    pass

        return result

    async def submit_answer(self, command: SubmitAnswerCommand) -> SubmitAnswerResultDTO:
        """
        Coordinates answer submission workflow.
        Captures an immutable AbilitySnapshot ONLY on fresh submissions (never on idempotent retry).
        """
        result = await self.submit_service.execute(command)

        # IMPORTANT: Idempotency Protection - never capture snapshot on duplicate / retry request
        if not result.is_retry:
            session = await self.session_repo.get_by_id(command.session_id)
            if session:
                meta = session.context_metadata or {}
                raw_ability = meta.get("ability_state", {})
                snapshot = AbilitySnapshotModel(
                    id=str(uuid.uuid4()),
                    student_id=session.student_id,
                    session_id=session.id,
                    snapshot_sequence=result.response_count,
                    ability_scores=raw_ability.get("dimension_scores", {}),
                    uncertainty_scores=raw_ability.get("uncertainty", {}),
                    dimension_coverage=raw_ability.get("dimension_coverage", {}),
                    answered_question_count=result.response_count,
                    algorithm_version=session.algorithm_version,
                    checkpoint_type="RESPONSE_UPDATE",
                )
                try:
                    await self.snapshot_repo.create_snapshot(snapshot)
                except IntegrityError:
                    await self.db.rollback()

        return result

    async def get_session_summary(self, session_id: str, student_id: str) -> SessionSummaryDTO:
        """
        Retrieves complete session progress and cognitive estimation summary.
        Enforces session ownership authorization.
        """
        session = await self.session_repo.get_session_with_responses(session_id)
        if not session:
            raise SessionNotFoundError(session_id)

        if session.student_id != student_id:
            raise SessionAccessForbiddenError(session_id, student_id)

        profile = session.profile
        if not profile:
            profile = await self.profile_repo.get_by_id(session.profile_id)
        if not profile:
            raise ProfileNotFoundError(str(session.profile_id))

        now_utc = datetime.now(timezone.utc)
        started_at = session.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        elapsed_seconds = max(0.0, (now_utc - started_at).total_seconds())

        context_metadata = dict(session.context_metadata or {})
        raw_ability = context_metadata.get("ability_state", {})
        scores = raw_ability.get("dimension_scores", {})
        uncertainty = raw_ability.get("uncertainty", {})

        return SessionSummaryDTO(
            session_id=session.id,
            student_id=session.student_id,
            student_age=session.student_age,
            profile_id=profile.id,
            profile_code=profile.code,
            status=session.status,
            started_at=session.started_at,
            last_activity_at=session.last_activity_at,
            completed_at=session.completed_at,
            response_count=len(session.responses),
            elapsed_seconds=round(elapsed_seconds, 1),
            target_dimensions=list(profile.dimensions),
            current_scores=scores,
            current_uncertainty=uncertainty,
            completion_reason=context_metadata.get("completion_reason"),
            completion_detail=context_metadata.get("completion_detail"),
        )

    async def get_assessment_report(self, session_id: str, student_id: str) -> AssessmentReportDTO:
        """
        Generates or retrieves final diagnostic report anchored to the final snapshot (TASK-031).
        """
        return await self.report_service.get_or_generate_report(session_id, student_id)

    async def get_ability_history(
        self,
        student_id: str,
        session_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> AbilityHistoryResponseDTO:
        """
        Retrieves paginated history of immutable ability snapshots for the authenticated student (TASK-032).
        """
        snapshots = await self.snapshot_repo.get_by_student_id(
            student_id=student_id,
            session_id=session_id,
            limit=limit,
            offset=offset
        )
        total_count = await self.snapshot_repo.count_by_student_id(
            student_id=student_id,
            session_id=session_id
        )

        dtos = [AbilitySnapshotDTO.model_validate(s) for s in snapshots]
        return AbilityHistoryResponseDTO(
            items=dtos,
            total=total_count,
            limit=limit,
            offset=offset
        )

    async def abandon_assessment(self, session_id: str, student_id: str) -> SessionSummaryDTO:
        """
        Transitions an IN_PROGRESS session to ABANDONED.
        """
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise SessionNotFoundError(session_id)
        if session.student_id != student_id:
            raise SessionAccessForbiddenError(session_id, student_id)
        if session.status != SessionStatus.IN_PROGRESS.value:
            raise SessionNotActiveError(session_id, session.status)

        await self.session_repo.update_status(session_id, SessionStatus.ABANDONED)
        await self.db.flush()
        return await self.get_session_summary(session_id, student_id)
