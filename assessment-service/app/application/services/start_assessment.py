from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.domain.enums import SessionStatus
from app.domain.profile import check_compatibility
from app.infrastructure.persistence.models.session import AssessmentSessionModel
from app.infrastructure.persistence.repositories.session_repo import AssessmentSessionRepository
from app.infrastructure.persistence.repositories.profile_repo import AssessmentProfileRepository
from app.engine.estimator import create_initial_ability_state
from app.application.dto import StartAssessmentCommand, StartAssessmentResultDTO
from app.application.exceptions import (
    ProfileNotFoundError,
    ProfileInactiveError,
    AgeIncompatibleError,
    ApplicationError,
)


class StartAssessmentService:
    """
    Application Service implementing TASK-025: Start Assessment.
    Validates student eligibility and profile parameters, initializes multidimensional
    ability state and uncertainty, and persists a new AssessmentSession atomically.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        session_repo: Optional[AssessmentSessionRepository] = None,
        profile_repo: Optional[AssessmentProfileRepository] = None,
    ):
        self.db = db_session
        self.session_repo = session_repo or AssessmentSessionRepository(db_session)
        self.profile_repo = profile_repo or AssessmentProfileRepository(db_session)

    async def execute(self, command: StartAssessmentCommand) -> StartAssessmentResultDTO:
        """
        Executes the session startup sequence.

        Args:
            command: StartAssessmentCommand carrying authenticated student_id, student_age, profile_code.

        Returns:
            StartAssessmentResultDTO with session metadata and initial cognitive profile.

        Raises:
            ProfileNotFoundError: If the requested profile code does not exist.
            ProfileInactiveError: If the profile is marked inactive.
            AgeIncompatibleError: If the student's age is outside profile limits.
            ApplicationError: For general validation failures.
        """
        # 1. Validate student authentication
        if not command.student_id or not command.student_id.strip():
            raise ApplicationError("Student ID is required and must be authenticated.", code="UNAUTHENTICATED")

        if command.student_age < 1:
            raise ApplicationError("Student age must be at least 1 year.", code="INVALID_AGE")

        # 2. Retrieve Profile
        profile = await self.profile_repo.get_by_code(command.profile_code)
        if not profile:
            raise ProfileNotFoundError(command.profile_code)

        if not profile.is_active:
            raise ProfileInactiveError(command.profile_code)

        # 3. Validate Age Compatibility against Profile Bracket
        if not (profile.min_age <= command.student_age <= profile.max_age):
            raise AgeIncompatibleError(
                age=command.student_age,
                min_age=profile.min_age,
                max_age=profile.max_age,
                profile_code=profile.code
            )

        # 4. Initialize Multidimensional Ability State and Uncertainty (TASK-020 & TASK-021)
        initial_ability = create_initial_ability_state(
            target_dimensions=profile.dimensions,
            initial_score=settings.INITIAL_PRIOR_ABILITY,
            initial_uncertainty=settings.INITIAL_PRIOR_UNCERTAINTY
        )

        now_utc = datetime.now(timezone.utc)

        # Structure initial context metadata with history tracking (acting as AbilitySnapshot storage)
        context_metadata = {
            "ability_state": {
                "dimension_scores": initial_ability.dimension_scores,
                "uncertainty": initial_ability.uncertainty,
                "response_count": 0,
                "dimension_coverage": initial_ability.dimension_coverage,
                "metadata": initial_ability.metadata,
            },
            "ability_history": [
                {
                    "step": 0,
                    "dimension_scores": initial_ability.dimension_scores,
                    "uncertainty": initial_ability.uncertainty,
                    "response_count": 0,
                    "created_at": now_utc.isoformat(),
                }
            ],
            "presented_questions": [],
            "selection_logs": [],
        }

        # 5. Resolve Algorithm and Question Bank Versions
        algo_version = command.algorithm_version or settings.ALGORITHM_VERSION
        random_seed = command.random_seed if command.random_seed is not None else 42

        # 6. Create Persistent Assessment Session
        session_model = AssessmentSessionModel(
            student_id=command.student_id,
            student_age=command.student_age,
            profile_id=profile.id,
            status=SessionStatus.IN_PROGRESS.value,
            started_at=now_utc,
            last_activity_at=now_utc,
            algorithm_version=algo_version,
            question_bank_version=settings.QUESTION_BANK_VERSION,
            random_seed=random_seed,
            context_metadata=context_metadata,
        )

        # 7. Persist atomically
        await self.session_repo.create_session(session_model)
        await self.db.flush()

        # 8. Return Result DTO
        return StartAssessmentResultDTO(
            session_id=session_model.id,
            student_id=session_model.student_id,
            student_age=session_model.student_age,
            profile_id=profile.id,
            profile_code=profile.code,
            status=session_model.status,
            started_at=session_model.started_at,
            algorithm_version=session_model.algorithm_version,
            target_dimensions=profile.dimensions,
            initial_scores=initial_ability.dimension_scores,
            initial_uncertainty=initial_ability.uncertainty,
        )
