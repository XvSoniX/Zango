"""
Ability Estimation Quality Evaluator Service (TASK-035).
Orchestrates validation, retrieval of simulation records, computation of
accuracy metrics (MAE, RMSE, Bias), uncertainty calibration, and persistence of results.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.evaluation.domain.config import EvaluationSettings, EvaluationType, EvaluationStatus
from app.evaluation.domain.estimation_metrics import EstimationMetricsCalculator
from app.evaluation.persistence.models import (
    EvaluationRunModel,
    AbilityEstimationEvaluationResultModel,
)
from app.evaluation.persistence.repository import EvaluationRepository
from app.simulation.persistence.repository import SimulationRepository
from app.config import settings

logger = logging.getLogger(__name__)


class AbilityEstimationEvaluator:
    """
    Service coordinating the evaluation of ability estimation accuracy against simulation runs.
    """

    def __init__(
        self,
        eval_repo: EvaluationRepository,
        sim_repo: SimulationRepository,
        eval_settings: Optional[EvaluationSettings] = None,
    ):
        self.eval_repo = eval_repo
        self.sim_repo = sim_repo
        self.eval_settings = eval_settings or EvaluationSettings()
        self.calculator = EstimationMetricsCalculator(settings=self.eval_settings)

    async def evaluate_simulation_runs(
        self,
        simulation_run_ids: List[str],
        configuration: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes Ability Estimation Quality Evaluation across one or more simulation runs.
        """
        if not simulation_run_ids:
            raise ValueError("At least one simulation_run_id must be provided for evaluation")

        eval_run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        configuration = configuration or {}

        # 1. Validate Simulation Runs & Compatibility
        all_participants = []
        algo_version = None

        for s_id in simulation_run_ids:
            sim_run = await self.sim_repo.get_run_by_id(s_id)
            if not sim_run:
                raise ValueError(f"Simulation run '{s_id}' not found")

            if sim_run.status not in ("COMPLETED", "PARTIALLY_COMPLETED"):
                raise ValueError(f"Simulation run '{s_id}' has invalid status '{sim_run.status}' (must be COMPLETED or PARTIALLY_COMPLETED)")

            if algo_version is None:
                algo_version = sim_run.algorithm_version
            elif algo_version != sim_run.algorithm_version:
                raise ValueError(
                    f"Incompatible algorithm versions in simulation runs: '{algo_version}' vs '{sim_run.algorithm_version}'. Cannot aggregate."
                )

            participants = await self.sim_repo.get_results_by_run_id(s_id, limit=5000)
            all_participants.extend(participants)

        # 2. Create Persistent Evaluation Run in RUNNING state
        eval_run = EvaluationRunModel(
            id=eval_run_id,
            evaluation_type=EvaluationType.ABILITY_ESTIMATION.value,
            status=EvaluationStatus.RUNNING.value,
            source_simulation_run_ids=simulation_run_ids,
            configuration=configuration,
            algorithm_version=algo_version or settings.ALGORITHM_VERSION,
            question_bank_version="v1.0",
            started_at=started_at,
        )
        await self.eval_repo.create_evaluation_run(eval_run)

        try:
            # 3. Compute Psychometric Estimation Metrics
            metrics = self.calculator.calculate(participant_results=all_participants)

            # 4. Persist Result Model
            result_model = AbilityEstimationEvaluationResultModel(
                id=str(uuid.uuid4()),
                evaluation_run_id=eval_run_id,
                summary_metrics=metrics["summary_metrics"],
                dimension_metrics=metrics["dimension_metrics"],
                uncertainty_analysis=metrics["uncertainty_analysis"],
                length_vs_quality=metrics["length_vs_quality"],
                archetype_breakdown=metrics["archetype_breakdowns"],
                anomalies=metrics["anomalies"],
                limitations=metrics["limitations"],
            )
            await self.eval_repo.create_ability_estimation_result(result_model)

            # 5. Finalize Run Status
            completed_at = datetime.now(timezone.utc)
            await self.eval_repo.update_run_status(
                run_id=eval_run_id,
                status=EvaluationStatus.COMPLETED.value,
                completed_at=completed_at,
            )

            metrics["evaluation_run_id"] = eval_run_id
            metrics["status"] = EvaluationStatus.COMPLETED.value
            metrics["algorithm_version"] = algo_version
            metrics["started_at"] = started_at.isoformat()
            metrics["completed_at"] = completed_at.isoformat()

            return metrics

        except Exception as e:
            logger.error(f"Error during Ability Estimation Evaluation: {e}", exc_info=True)
            await self.eval_repo.update_run_status(
                run_id=eval_run_id,
                status=EvaluationStatus.FAILED.value,
                error_message=str(e),
                completed_at=datetime.now(timezone.utc),
            )
            raise
