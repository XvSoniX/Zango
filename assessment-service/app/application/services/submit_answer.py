from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.domain.enums import SessionStatus
from app.infrastructure.persistence.models.session import (
    AssessmentSessionModel,
    AssessmentResponseModel,
)
from app.infrastructure.persistence.repositories.session_repo import AssessmentSessionRepository
from app.infrastructure.persistence.repositories.response_repo import AssessmentResponseRepository
from app.infrastructure.persistence.repositories.question_repo import QuestionRepository
from app.engine.protocols import AbilityState
from app.engine.evaluator import BaselineAnswerEvaluator
from app.engine.estimator import BaselineMultidimensionalEstimator
from app.application.dto import SubmitAnswerCommand, SubmitAnswerResultDTO
from app.application.exceptions import (
    SessionNotFoundError,
    SessionAccessForbiddenError,
    SessionNotActiveError,
    QuestionVersionNotFoundError,
    QuestionNotOfferedError,
    DuplicateAnswerError,
    IdempotencyConflictError,
    ApplicationError,
)


class SubmitAnswerService:
    """
    Application Service implementing TASK-027: Submit Answer.
    Guarantees:
    - Session ownership and active status validation.
    - True database-backed idempotency (safe retry vs conflict detection).
    - Prevention of duplicate question answering.
    - Pure scoring via AnswerEvaluator (TASK-019).
    - Multidimensional ability update via BaselineMultidimensionalEstimator (TASK-020).
    - Uncertainty update via UncertaintyEstimator (TASK-021).
    - AbilitySnapshot history tracking.
    - Atomic transaction boundary.
    - Zero disclosure of correct_answer in public responses.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        session_repo: Optional[AssessmentSessionRepository] = None,
        response_repo: Optional[AssessmentResponseRepository] = None,
        question_repo: Optional[QuestionRepository] = None,
        evaluator: Optional[BaselineAnswerEvaluator] = None,
        estimator: Optional[BaselineMultidimensionalEstimator] = None,
    ):
        self.db = db_session
        self.session_repo = session_repo or AssessmentSessionRepository(db_session)
        self.response_repo = response_repo or AssessmentResponseRepository(db_session)
        self.question_repo = question_repo or QuestionRepository(db_session)
        self.evaluator = evaluator or BaselineAnswerEvaluator()
        self.estimator = estimator or BaselineMultidimensionalEstimator()

    async def execute(self, command: SubmitAnswerCommand) -> SubmitAnswerResultDTO:
        """
        Processes and scores a student's answer submission within an atomic transaction.

        Args:
            command: SubmitAnswerCommand containing session_id, student_id, question_version_id,
                     answer payload, response_time_ms, and idempotency_key.

        Returns:
            SubmitAnswerResultDTO confirming evaluation outcome and response state.

        Raises:
            SessionNotFoundError: If session does not exist.
            SessionAccessForbiddenError: If session belongs to another student.
            SessionNotActiveError: If session status is not IN_PROGRESS.
            QuestionVersionNotFoundError: If question version does not exist.
            QuestionNotOfferedError: If question was not presented to this session.
            DuplicateAnswerError: If this question was already answered in this session.
            IdempotencyConflictError: If idempotency key is reused with mismatched payload.
        """
        # 1. Load Session with eager responses (and row-level lock on PostgreSQL)
        session = await self.session_repo.get_session_with_responses(command.session_id, for_update=True)
        if not session:
            raise SessionNotFoundError(command.session_id)

        # 2. Enforce Session Ownership
        if session.student_id != command.student_id:
            raise SessionAccessForbiddenError(command.session_id, command.student_id)

        # 3. Validate Session Status
        if session.status != SessionStatus.IN_PROGRESS.value:
            raise SessionNotActiveError(command.session_id, session.status)

        # 4. Retrieve Question Version from Database
        question_version = await self.question_repo.get_version_by_id(command.question_version_id)
        if not question_version:
            raise QuestionVersionNotFoundError(command.question_version_id)

        # 5. Validate that Question Version was offered to this session
        context_metadata = dict(session.context_metadata or {})
        presented_versions = context_metadata.get("presented_questions", [])
        if presented_versions and command.question_version_id not in presented_versions:
            raise QuestionNotOfferedError(session.id, command.question_version_id)

        # 6. Idempotency & Duplicate Checks
        # Scenario A: Check Idempotency Key
        existing_by_key = await self.response_repo.get_by_idempotency_key(
            session_id=session.id,
            idempotency_key=command.idempotency_key
        )
        if existing_by_key:
            # If payload and question match, this is a valid retry
            if (
                existing_by_key.question_version_id == command.question_version_id
                and existing_by_key.answer == command.answer
            ):
                return SubmitAnswerResultDTO(
                    session_id=session.id,
                    response_id=existing_by_key.id,
                    question_id=existing_by_key.question_id,
                    question_version_id=existing_by_key.question_version_id,
                    is_correct=existing_by_key.is_correct,
                    score=existing_by_key.score,
                    response_time_ms=existing_by_key.response_time_ms,
                    idempotency_key=existing_by_key.idempotency_key,
                    answered_at=existing_by_key.answered_at,
                    response_count=len(session.responses),
                    session_status=session.status,
                    is_retry=True,
                )
            else:
                # Same idempotency key with conflicting parameters
                raise IdempotencyConflictError(session.id, command.idempotency_key)

        # Scenario B: Check if Question was already answered in this session
        has_answered = await self.response_repo.has_answered_question(
            session_id=session.id,
            question_id=question_version.question_id
        )
        if has_answered:
            raise DuplicateAnswerError(session.id, question_version.question_id)

        # 7. Evaluate Answer via AnswerEvaluator (TASK-019)
        # Structural errors (invalid option, malformed payload) will raise engine exceptions
        eval_result = self.evaluator.evaluate(
            question=question_version,
            submitted_answer=command.answer,
            response_time_ms=command.response_time_ms,
        )

        now_utc = datetime.now(timezone.utc)

        # 8. Create Response Entity
        response_model = AssessmentResponseModel(
            session_id=session.id,
            question_id=question_version.question_id,
            question_version_id=question_version.id,
            answer=command.answer,
            is_correct=eval_result.is_correct,
            score=eval_result.score,
            response_time_ms=eval_result.response_time_ms,
            idempotency_key=command.idempotency_key,
            answered_at=now_utc,
        )

        try:
            await self.response_repo.create_response(response_model)
        except IntegrityError:
            # Race condition: duplicate submission in concurrent request
            await self.db.rollback()
            # Re-check idempotency key using command parameters directly (safe after rollback)
            dup_check = await self.response_repo.get_by_idempotency_key(command.session_id, command.idempotency_key)
            if dup_check and dup_check.answer == command.answer:
                return SubmitAnswerResultDTO(
                    session_id=command.session_id,
                    response_id=dup_check.id,
                    question_id=dup_check.question_id,
                    question_version_id=dup_check.question_version_id,
                    is_correct=dup_check.is_correct,
                    score=dup_check.score,
                    response_time_ms=dup_check.response_time_ms,
                    idempotency_key=dup_check.idempotency_key,
                    answered_at=dup_check.answered_at,
                    response_count=1,
                    session_status=SessionStatus.IN_PROGRESS.value,
                    is_retry=True,
                )
            raise DuplicateAnswerError(command.session_id, question_version.question_id)

        # 9. Update Ability State and Uncertainty (TASK-020 & TASK-021)
        raw_ability = context_metadata.get("ability_state", {})
        current_ability = AbilityState(
            dimension_scores=raw_ability.get("dimension_scores", {}),
            uncertainty=raw_ability.get("uncertainty", {}),
            response_count=len(session.responses),
            dimension_coverage=raw_ability.get("dimension_coverage", {}),
            metadata=raw_ability.get("metadata", {}),
        )

        new_ability = self.estimator.estimate(
            current_state=current_ability,
            latest_evaluation=eval_result,
            question=question_version,
        )

        # 10. Persist Updated Ability State and Append History Snapshot (TASK-020 / AbilitySnapshot)
        context_metadata["ability_state"] = {
            "dimension_scores": new_ability.dimension_scores,
            "uncertainty": new_ability.uncertainty,
            "response_count": new_ability.response_count,
            "dimension_coverage": new_ability.dimension_coverage,
            "metadata": new_ability.metadata,
        }

        history = list(context_metadata.get("ability_history", []))
        history.append({
            "step": new_ability.response_count,
            "response_id": response_model.id,
            "question_id": question_version.question_id,
            "question_version_id": question_version.id,
            "is_correct": eval_result.is_correct,
            "dimension_scores": new_ability.dimension_scores,
            "uncertainty": new_ability.uncertainty,
            "created_at": now_utc.isoformat(),
        })
        context_metadata["ability_history"] = history

        # 11. Update Session Timestamps and Context Metadata
        session.context_metadata = context_metadata
        session.last_activity_at = now_utc
        await self.db.flush()

        # 12. Return Result DTO (zero disclosure of correct_answer)
        return SubmitAnswerResultDTO(
            session_id=session.id,
            response_id=response_model.id,
            question_id=response_model.question_id,
            question_version_id=response_model.question_version_id,
            is_correct=response_model.is_correct,
            score=response_model.score,
            response_time_ms=response_model.response_time_ms,
            idempotency_key=response_model.idempotency_key,
            answered_at=response_model.answered_at,
            response_count=new_ability.response_count,
            session_status=session.status,
            is_retry=False,
        )
