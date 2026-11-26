import uuid
import random
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.enums import SessionStatus
from app.infrastructure.persistence.repositories import (
    AssessmentSessionRepository,
    AssessmentProfileRepository,
    QuestionRepository,
    AssessmentResponseRepository,
    AbilitySnapshotRepository,
    AssessmentReportRepository,
)
from app.application.dto import (
    StartAssessmentCommand,
    NextQuestionQuery,
    SubmitAnswerCommand,
)
from app.simulation.domain.archetypes import ArchetypeType
from app.simulation.domain.synthetic_user import SyntheticUserProfile
from app.simulation.domain.user_generator import SyntheticUserGenerator
from app.simulation.domain.response_simulator import ResponseSimulator
from app.simulation.persistence.models import SimulationRunModel, SimulationParticipantResultModel
from app.simulation.persistence.repository import SimulationRepository

logger = logging.getLogger("simulation_lab")


class SimulationOrchestrator:
    """
    Simulation Lab Orchestrator implementing TASK-033.
    Executes controlled experiments where synthetic participants with known ground-truth abilities
    interact with the genuine production assessment workflow (Selector, Evaluator, Estimator, Stopping).
    """

    def __init__(
        self,
        db_session: AsyncSession,
        simulation_repo: Optional[SimulationRepository] = None,
        workflow_orchestrator: Optional[Any] = None,
        question_repo: Optional[QuestionRepository] = None,
        snapshot_repo: Optional[AbilitySnapshotRepository] = None,
        response_simulator: Optional[ResponseSimulator] = None,
    ):
        from app.application.workflow import AssessmentWorkflowOrchestrator

        self.db = db_session
        self.sim_repo = simulation_repo or SimulationRepository(db_session)
        self.workflow = workflow_orchestrator or AssessmentWorkflowOrchestrator(db_session)
        self.question_repo = question_repo or QuestionRepository(db_session)
        self.snapshot_repo = snapshot_repo or AbilitySnapshotRepository(db_session)
        self.simulator = response_simulator or ResponseSimulator()

    async def execute_simulation_run(
        self,
        name: str = "Synthetic Cohort Evaluation",
        profile_code: str = "TECHNICAL_TALENT_V1",
        participant_count: int = 10,
        archetypes: Optional[List[ArchetypeType]] = None,
        min_age: int = 12,
        max_age: int = 18,
        random_seed: int = 42,
        custom_ability: Optional[Dict[str, float]] = None,
    ) -> SimulationRunModel:
        """
        Executes a complete reproducible simulation batch.
        """
        run_id = str(uuid.uuid4())
        now_utc = datetime.now(timezone.utc)

        config_dict = {
            "profile_code": profile_code,
            "participant_count": participant_count,
            "archetypes": [a.value for a in archetypes] if archetypes else ["ALL"],
            "min_age": min_age,
            "max_age": max_age,
            "random_seed": random_seed,
            "custom_ability": custom_ability,
            "algorithm_version": settings.ALGORITHM_VERSION,
            "simulation_model_version": "1.0.0-mirt",
        }

        # 1. Create SimulationRun record in PENDING status
        run_model = SimulationRunModel(
            id=run_id,
            name=name,
            status="RUNNING",
            profile_code=profile_code,
            algorithm_version=settings.ALGORITHM_VERSION,
            random_seed=random_seed,
            participant_count=participant_count,
            completed_participant_count=0,
            failed_participant_count=0,
            configuration=config_dict,
            started_at=now_utc,
            created_at=now_utc,
        )
        await self.sim_repo.create_run(run_model)

        # 2. Generate Synthetic Participants with Ground-Truth Profiles
        participants = SyntheticUserGenerator.generate_users(
            simulation_run_id=run_id,
            count=participant_count,
            archetypes=archetypes,
            min_age=min_age,
            max_age=max_age,
            random_seed=random_seed,
            custom_ability=custom_ability,
        )

        completed_count = 0
        failed_count = 0
        step_rng = random.Random(random_seed)

        # 3. Simulate Each Participant through the Genuine Assessment Engine
        for idx, participant in enumerate(participants):
            try:
                res_record = await self._run_single_participant(
                    run_id=run_id,
                    participant=participant,
                    profile_code=profile_code,
                    step_rng=step_rng,
                )
                await self.sim_repo.create_participant_result(res_record)
                completed_count += 1

                # Resource Hardening: periodic flush to prevent unbounded ORM memory growth
                if (idx + 1) % settings.SIMULATION_BATCH_SIZE == 0:
                    await self.db.flush()
            except Exception as e:
                logger.error(f"Error simulating participant {participant.synthetic_user_id}: {e}", exc_info=True)
                failed_count += 1
                # Failure isolation: record failure entry
                failed_record = SimulationParticipantResultModel(
                    id=str(uuid.uuid4()),
                    run_id=run_id,
                    synthetic_user_id=participant.synthetic_user_id,
                    archetype=participant.archetype.value,
                    age=participant.age,
                    ground_truth_ability=participant.ground_truth_ability,
                    estimated_ability={},
                    uncertainty_vector={},
                    dimension_coverage={},
                    session_id="FAILED",
                    session_status="FAILED",
                    stopping_reason=None,
                    answered_question_count=0,
                    total_duration_seconds=0.0,
                    error_message=str(e),
                    created_at=datetime.now(timezone.utc),
                )
                await self.sim_repo.create_participant_result(failed_record)

        # 4. Finalize Run Status
        final_status = "COMPLETED" if failed_count == 0 else ("PARTIALLY_COMPLETED" if completed_count > 0 else "FAILED")
        now_completed = datetime.now(timezone.utc)
        await self.sim_repo.update_run_status(
            run_id=run_id,
            status=final_status,
            completed_count=completed_count,
            failed_count=failed_count,
            completed_at=now_completed,
        )
        await self.db.flush()

        return await self.sim_repo.get_run_by_id(run_id)

    async def _run_single_participant(
        self,
        run_id: str,
        participant: SyntheticUserProfile,
        profile_code: str,
        step_rng: random.Random,
    ) -> SimulationParticipantResultModel:
        """
        Executes a full adaptive session for one synthetic user using real engine services.
        """
        # A. Start Session
        start_cmd = StartAssessmentCommand(
            student_id=participant.synthetic_user_id,
            student_age=participant.age,
            profile_code=profile_code,
            algorithm_version=settings.ALGORITHM_VERSION,
            random_seed=participant.random_seed,
        )
        start_res = await self.workflow.start_assessment(start_cmd)
        session_id = start_res.session_id

        question_records: List[Dict[str, Any]] = []
        step_idx = 0

        # B. Adaptive Testing Loop
        while True:
            step_idx += 1
            query = NextQuestionQuery(session_id=session_id, student_id=participant.synthetic_user_id)
            next_res = await self.workflow.get_next_question(query)

            # Check for Stopping Strategy trigger
            if next_res.should_stop:
                break

            q_dto = next_res.question
            if not q_dto:
                break

            # Fetch complete question version specification for psychometric modeling
            q_version = await self.question_repo.get_version_by_id(q_dto.question_version_id)
            if not q_version:
                break

            # Simulate Response
            step_seed = step_rng.randint(1000, 9999999)
            sim_answer, is_correct, rt_ms, p_correct = self.simulator.simulate_response(
                user=participant,
                question_version=q_version,
                step_seed=step_seed,
            )

            # Submit Answer through real workflow
            sub_cmd = SubmitAnswerCommand(
                session_id=session_id,
                student_id=participant.synthetic_user_id,
                question_version_id=q_dto.question_version_id,
                answer=sim_answer,
                response_time_ms=rt_ms,
                idempotency_key=f"sim-run-{run_id[:8]}-u-{participant.synthetic_user_id}-step-{step_idx}",
            )
            sub_res = await self.workflow.submit_answer(sub_cmd)

            # Record step trace for evaluation tasks (TASK-034 & TASK-035)
            question_records.append({
                "step": step_idx,
                "question_id": q_dto.question_id,
                "question_version_id": q_dto.question_version_id,
                "dimensions": q_version.dimensions,
                "difficulty": q_version.difficulty,
                "discrimination": q_version.discrimination,
                "guessing": q_version.guessing,
                "p_correct": p_correct,
                "submitted_answer": sim_answer,
                "is_correct": sub_res.is_correct,
                "response_time_ms": rt_ms,
            })

        # C. Retrieve Final State from Session & Snapshot
        summary = await self.workflow.get_session_summary(session_id, participant.synthetic_user_id)
        final_snapshot = await self.snapshot_repo.get_latest_by_session_id(session_id)

        result_id = str(uuid.uuid4())
        return SimulationParticipantResultModel(
            id=result_id,
            run_id=run_id,
            synthetic_user_id=participant.synthetic_user_id,
            archetype=participant.archetype.value,
            age=participant.age,
            ground_truth_ability=participant.ground_truth_ability,
            estimated_ability=summary.current_scores,
            uncertainty_vector=summary.current_uncertainty,
            dimension_coverage=final_snapshot.dimension_coverage if final_snapshot else {},
            session_id=session_id,
            session_status=summary.status,
            stopping_reason=summary.completion_reason,
            answered_question_count=summary.response_count,
            total_duration_seconds=summary.elapsed_seconds,
            final_snapshot_id=final_snapshot.id if final_snapshot else None,
            question_records=question_records,
            created_at=datetime.now(timezone.utc),
        )
