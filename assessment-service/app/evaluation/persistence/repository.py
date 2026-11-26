"""
Repository layer for Assessment Engine Evaluation Framework (TASK-034 & TASK-035).
Handles async database operations for evaluation runs and results.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.evaluation.persistence.models import (
    EvaluationRunModel,
    QuestionSelectionEvaluationResultModel,
    AbilityEstimationEvaluationResultModel,
)


class EvaluationRepository:
    """
    Async repository for Evaluation entities.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_evaluation_run(self, run: EvaluationRunModel) -> EvaluationRunModel:
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_evaluation_run(self, run_id: str) -> Optional[EvaluationRunModel]:
        stmt = (
            select(EvaluationRunModel)
            .where(EvaluationRunModel.id == run_id)
            .options(
                selectinload(EvaluationRunModel.question_selection_result),
                selectinload(EvaluationRunModel.ability_estimation_result),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def update_run_status(
        self,
        run_id: str,
        status: str,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None,
    ) -> None:
        run = await self.get_evaluation_run(run_id)
        if run:
            run.status = status
            if error_message:
                run.error_message = error_message
            if completed_at:
                run.completed_at = completed_at
            elif status in ("COMPLETED", "FAILED", "PARTIALLY_COMPLETED"):
                run.completed_at = datetime.now(timezone.utc)
            await self.session.flush()

    async def create_question_selection_result(
        self, result: QuestionSelectionEvaluationResultModel
    ) -> QuestionSelectionEvaluationResultModel:
        self.session.add(result)
        await self.session.flush()
        return result

    async def create_ability_estimation_result(
        self, result: AbilityEstimationEvaluationResultModel
    ) -> AbilityEstimationEvaluationResultModel:
        self.session.add(result)
        await self.session.flush()
        return result

    async def get_question_selection_result_by_run_id(
        self, run_id: str
    ) -> Optional[QuestionSelectionEvaluationResultModel]:
        stmt = select(QuestionSelectionEvaluationResultModel).where(
            QuestionSelectionEvaluationResultModel.evaluation_run_id == run_id
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_ability_estimation_result_by_run_id(
        self, run_id: str
    ) -> Optional[AbilityEstimationEvaluationResultModel]:
        stmt = select(AbilityEstimationEvaluationResultModel).where(
            AbilityEstimationEvaluationResultModel.evaluation_run_id == run_id
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_evaluation_runs(self, limit: int = 50) -> List[EvaluationRunModel]:
        stmt = (
            select(EvaluationRunModel)
            .order_by(EvaluationRunModel.created_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
