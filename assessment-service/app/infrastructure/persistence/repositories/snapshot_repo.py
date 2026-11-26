from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.persistence.models.snapshot import AbilitySnapshotModel


class AbilitySnapshotRepository:
    """Repository handling persistence and queries for AbilitySnapshot entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_snapshot(self, snapshot: AbilitySnapshotModel) -> AbilitySnapshotModel:
        """Atomically adds and flushes a new immutable snapshot."""
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def get_by_id(self, snapshot_id: str) -> Optional[AbilitySnapshotModel]:
        """Retrieves a single snapshot by its primary key ID."""
        stmt = select(AbilitySnapshotModel).where(AbilitySnapshotModel.id == snapshot_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_session_id(self, session_id: str) -> List[AbilitySnapshotModel]:
        """Retrieves all snapshots for a session ordered by sequence ascending."""
        stmt = (
            select(AbilitySnapshotModel)
            .where(AbilitySnapshotModel.session_id == session_id)
            .order_by(AbilitySnapshotModel.snapshot_sequence.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_by_session_id(self, session_id: str) -> Optional[AbilitySnapshotModel]:
        """Retrieves the most recent snapshot for a session."""
        stmt = (
            select(AbilitySnapshotModel)
            .where(AbilitySnapshotModel.session_id == session_id)
            .order_by(AbilitySnapshotModel.snapshot_sequence.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_student_id(
        self,
        student_id: str,
        session_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AbilitySnapshotModel]:
        """Retrieves ability history for a student across sessions, ordered chronologically."""
        stmt = select(AbilitySnapshotModel).where(AbilitySnapshotModel.student_id == student_id)
        if session_id:
            stmt = stmt.where(AbilitySnapshotModel.session_id == session_id)
        stmt = stmt.order_by(AbilitySnapshotModel.created_at.desc(), AbilitySnapshotModel.snapshot_sequence.desc())
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_student_id(self, student_id: str, session_id: Optional[str] = None) -> int:
        """Counts total snapshot records for a student."""
        stmt = select(func.count()).select_from(AbilitySnapshotModel).where(AbilitySnapshotModel.student_id == student_id)
        if session_id:
            stmt = stmt.where(AbilitySnapshotModel.session_id == session_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()
