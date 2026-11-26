from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.domain.enums import SessionStatus, StoppingReason, QuestionVersionStatus
from app.infrastructure.persistence.models.session import AssessmentSessionModel
from app.infrastructure.persistence.models.question import QuestionModel, QuestionVersionModel
from app.infrastructure.persistence.repositories.session_repo import AssessmentSessionRepository
from app.infrastructure.persistence.repositories.profile_repo import AssessmentProfileRepository
from app.infrastructure.persistence.repositories.question_repo import QuestionRepository
from app.engine.protocols import (
    AbilityState,
    AssessmentContext,
    ItemParameterSnapshot,
)
from app.engine.selector import CompositeHeuristicSelector
from app.engine.stopping import StandardStoppingStrategy
from app.application.dto import (
    NextQuestionQuery,
    NextQuestionResultDTO,
    PublicQuestionDTO,
    PublicQuestionOptionDTO,
)
from app.application.exceptions import (
    SessionNotFoundError,
    SessionAccessForbiddenError,
    SessionNotActiveError,
    SessionExpiredError,
    ProfileNotFoundError,
)


class NextQuestionService:
    """
    Application Service implementing TASK-026: Next Question.
    Coordinates session state verification, Stopping Strategy evaluation,
    Composite Heuristic question selection, and sanitization of the next question.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        session_repo: Optional[AssessmentSessionRepository] = None,
        profile_repo: Optional[AssessmentProfileRepository] = None,
        question_repo: Optional[QuestionRepository] = None,
        selector: Optional[CompositeHeuristicSelector] = None,
        stopping_strategy: Optional[StandardStoppingStrategy] = None,
    ):
        self.db = db_session
        self.session_repo = session_repo or AssessmentSessionRepository(db_session)
        self.profile_repo = profile_repo or AssessmentProfileRepository(db_session)
        self.question_repo = question_repo or QuestionRepository(db_session)
        self.selector = selector or CompositeHeuristicSelector()
        self.stopping_strategy = stopping_strategy or StandardStoppingStrategy()

    async def execute(self, query: NextQuestionQuery) -> NextQuestionResultDTO:
        """
        Retrieves the next adaptive question for the active session, or signals completion.

        Args:
            query: NextQuestionQuery with session_id and authenticated student_id.

        Returns:
            NextQuestionResultDTO indicating either the next sanitized question or stopping reason.

        Raises:
            SessionNotFoundError: If session does not exist.
            SessionAccessForbiddenError: If session belongs to a different student.
            SessionNotActiveError: If session is not currently IN_PROGRESS.
            SessionExpiredError: If session has exceeded its maximum lifetime.
        """
        # 1. Retrieve session with eager responses and profile
        session = await self.session_repo.get_session_with_responses(query.session_id)
        if not session:
            raise SessionNotFoundError(query.session_id)

        # 2. Enforce Session Ownership (Authorization)
        if session.student_id != query.student_id:
            raise SessionAccessForbiddenError(query.session_id, query.student_id)

        # 3. Validate Session Status
        if session.status != SessionStatus.IN_PROGRESS.value:
            raise SessionNotActiveError(query.session_id, session.status)

        # 4. Check Duration / Expiration
        now_utc = datetime.now(timezone.utc)
        started_at = session.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        elapsed_seconds = max(0.0, (now_utc - started_at).total_seconds())
        max_duration = float(settings.SESSION_TIMEOUT_SECONDS)

        # 5. Retrieve Profile & Reconstruct Current Ability State
        profile = session.profile
        if not profile:
            profile = await self.profile_repo.get_by_id(session.profile_id)
        if not profile:
            raise ProfileNotFoundError(str(session.profile_id))

        context_metadata = dict(session.context_metadata or {})
        raw_ability = context_metadata.get("ability_state", {})

        current_ability = AbilityState(
            dimension_scores=raw_ability.get("dimension_scores", {}),
            uncertainty=raw_ability.get("uncertainty", {}),
            response_count=len(session.responses),
            dimension_coverage=raw_ability.get("dimension_coverage", {}),
            metadata=raw_ability.get("metadata", {}),
        )

        answered_q_ids = [r.question_id for r in session.responses]

        # 6. Build Engine Assessment Context
        engine_context = AssessmentContext(
            session_id=session.id,
            student_id=session.student_id,
            student_age=session.student_age,
            profile_code=profile.code,
            target_dimensions=list(profile.dimensions),
            current_ability=current_ability,
            answered_question_ids=answered_q_ids,
            response_history=[],
            elapsed_time_seconds=elapsed_seconds,
            max_duration_seconds=max_duration,
            min_questions=settings.MIN_QUESTIONS,
            max_questions=settings.MAX_QUESTIONS,
            random_seed=session.random_seed,
        )

        # 7. Retrieve Candidate Questions from Question Bank
        active_questions = await self.question_repo.get_active_questions_for_profile(profile.id)
        remaining_candidates_count = len([q for q in active_questions if q.id not in answered_q_ids])

        # 8. Evaluate Stopping Strategy FIRST (TASK-024)
        stopping_decision = self.stopping_strategy.evaluate(
            context=engine_context,
            ability_state=current_ability,
            remaining_candidates_count=remaining_candidates_count,
        )

        if stopping_decision.should_stop:
            return NextQuestionResultDTO(
                session_id=session.id,
                should_stop=True,
                stopping_reason=stopping_decision.reason.value if stopping_decision.reason else "STOP",
                stopping_detail=stopping_decision.detail,
                question=None,
                progress={
                    "answered_count": len(answered_q_ids),
                    "elapsed_seconds": round(elapsed_seconds, 1),
                    "target_dimensions": list(profile.dimensions),
                }
            )

        # 9. Convert Candidates to Engine Snapshots
        snapshots: List[ItemParameterSnapshot] = []
        model_lookup: Dict[int, tuple[QuestionModel, QuestionVersionModel]] = {}

        for q in active_questions:
            version_model = q.get_active_version() or q.get_latest_version()
            if not version_model:
                continue

            snapshot = ItemParameterSnapshot(
                question_id=q.id,
                version=version_model.version,
                dimensions=dict(version_model.dimensions or {}),
                difficulty=version_model.difficulty,
                discrimination=version_model.discrimination,
                guessing=version_model.guessing,
                min_age=version_model.min_age,
                max_age=version_model.max_age,
                exposure_limit=version_model.exposure_limit or 1000,
                exposure_count=0,
                is_active=q.is_active and (version_model.status == QuestionVersionStatus.PUBLISHED.value),
                correct_answer=version_model.correct_answer,
                options=version_model.options,
                question_type=version_model.question_type,
                calibration_status=version_model.calibration_status,
            )
            snapshots.append(snapshot)
            model_lookup[q.id] = (q, version_model)

        # 10. Execute Composite Heuristic Question Selector (TASK-023)
        selection_result = self.selector.select(
            candidate_pool=snapshots,
            context=engine_context
        )

        if selection_result.selected_question_id is None:
            # Question pool exhausted or no eligible candidates remain
            return NextQuestionResultDTO(
                session_id=session.id,
                should_stop=True,
                stopping_reason=StoppingReason.QUESTION_BANK_EXHAUSTED.value,
                stopping_detail=selection_result.selection_reason,
                question=None,
                progress={
                    "answered_count": len(answered_q_ids),
                    "elapsed_seconds": round(elapsed_seconds, 1),
                }
            )

        selected_id = selection_result.selected_question_id
        selected_question_model, selected_version_model = model_lookup[selected_id]

        # 11. Record Selection Log and track Presented Question Version for validation
        selection_logs = list(context_metadata.get("selection_logs", []))
        selection_logs.append({
            "question_id": selected_id,
            "question_version_id": selected_version_model.id,
            "version": selected_version_model.version,
            "candidate_scores": selection_result.candidate_scores,
            "selection_reason": selection_result.selection_reason,
            "selected_at": now_utc.isoformat(),
        })
        context_metadata["selection_logs"] = selection_logs

        presented_versions = list(context_metadata.get("presented_questions", []))
        if selected_version_model.id not in presented_versions:
            presented_versions.append(selected_version_model.id)
        context_metadata["presented_questions"] = presented_versions

        session.context_metadata = context_metadata
        await self.db.flush()

        # 12. Sanitize and build Public Question Representation (Strict secrecy of answers)
        safe_options: List[PublicQuestionOptionDTO] = []
        for opt in (selected_version_model.options or []):
            safe_options.append(PublicQuestionOptionDTO(
                key=str(opt.get("key", "")),
                text=str(opt.get("text", "")),
            ))

        public_question = PublicQuestionDTO(
            question_id=selected_id,
            question_version_id=selected_version_model.id,
            question_type=selected_version_model.question_type,
            content=selected_version_model.content,
            options=safe_options,
            estimated_time=selected_version_model.estimated_time,
            sequence_number=len(answered_q_ids) + 1,
        )

        return NextQuestionResultDTO(
            session_id=session.id,
            should_stop=False,
            question=public_question,
            progress={
                "answered_count": len(answered_q_ids),
                "elapsed_seconds": round(elapsed_seconds, 1),
            }
        )
