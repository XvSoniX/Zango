from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.simulation.persistence.models import SimulationRunModel, SimulationParticipantResultModel


class SimulationRepository:
    """Repository handling persistence and queries for simulation runs and participant results."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_run(self, run: SimulationRunModel) -> SimulationRunModel:
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_run_by_id(self, run_id: str) -> Optional[SimulationRunModel]:
        stmt = select(SimulationRunModel).where(SimulationRunModel.id == run_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_runs(self, limit: int = 50, offset: int = 0) -> List[SimulationRunModel]:
        stmt = (
            select(SimulationRunModel)
            .order_by(SimulationRunModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_run_status(
        self,
        run_id: str,
        status: str,
        completed_count: Optional[int] = None,
        failed_count: Optional[int] = None,
        completed_at: Optional[datetime] = None,
    ) -> Optional[SimulationRunModel]:
        run = await self.get_run_by_id(run_id)
        if not run:
            return None

        run.status = status
        if completed_count is not None:
            run.completed_participant_count = completed_count
        if failed_count is not None:
            run.failed_participant_count = failed_count
        if completed_at is not None:
            run.completed_at = completed_at

        await self.session.flush()
        return run

    async def create_participant_result(
        self,
        result: SimulationParticipantResultModel
    ) -> SimulationParticipantResultModel:
        self.session.add(result)
        await self.session.flush()
        return result

    async def get_results_by_run_id(
        self,
        run_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[SimulationParticipantResultModel]:
        stmt = (
            select(SimulationParticipantResultModel)
            .where(SimulationParticipantResultModel.run_id == run_id)
            .order_by(SimulationParticipantResultModel.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_result_by_id(self, result_id: str) -> Optional[SimulationParticipantResultModel]:
        stmt = select(SimulationParticipantResultModel).where(SimulationParticipantResultModel.id == result_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_result_by_participant(
        self,
        run_id: str,
        synthetic_user_id: str
    ) -> Optional[SimulationParticipantResultModel]:
        stmt = select(SimulationParticipantResultModel).where(
            SimulationParticipantResultModel.run_id == run_id,
            SimulationParticipantResultModel.synthetic_user_id == synthetic_user_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
