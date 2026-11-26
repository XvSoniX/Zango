from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.persistence.models.session import AssessmentSessionModel
from app.domain.enums import SessionStatus
from app.domain.session import validate_session_transition

class AssessmentSessionRepository:
    """Repository handling persistence and queries for AssessmentSession entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(self, assessment_session: AssessmentSessionModel) -> AssessmentSessionModel:
        self.session.add(assessment_session)
        await self.session.flush()
        return assessment_session

    async def get_by_id(self, session_id: str, for_update: bool = False) -> Optional[AssessmentSessionModel]:
        stmt = select(AssessmentSessionModel).where(AssessmentSessionModel.id == session_id)
        if for_update and self.session.bind and "sqlite" not in str(self.session.bind.url):
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_session_with_responses(self, session_id: str, for_update: bool = False) -> Optional[AssessmentSessionModel]:
        """Loads session with eagerly-loaded responses and profile."""
        stmt = (
            select(AssessmentSessionModel)
            .where(AssessmentSessionModel.id == session_id)
            .options(
                selectinload(AssessmentSessionModel.profile),
                selectinload(AssessmentSessionModel.responses)
            )
        )
        if for_update and self.session.bind and "sqlite" not in str(self.session.bind.url):
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_student_id(
        self,
        student_id: str,
        status: Optional[str] = None
    ) -> List[AssessmentSessionModel]:
        stmt = select(AssessmentSessionModel).where(AssessmentSessionModel.student_id == student_id)
        if status:
            stmt = stmt.where(AssessmentSessionModel.status == status)
        stmt = stmt.order_by(AssessmentSessionModel.started_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_session(self, student_id: str) -> Optional[AssessmentSessionModel]:
        """Returns active in-progress session for a student if one exists."""
        stmt = select(AssessmentSessionModel).where(
            and_(
                AssessmentSessionModel.student_id == student_id,
                AssessmentSessionModel.status == SessionStatus.IN_PROGRESS.value
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_active_sessions(self, limit: int = 100, offset: int = 0) -> List[AssessmentSessionModel]:
        """Returns all currently IN_PROGRESS sessions across the system."""
        stmt = (
            select(AssessmentSessionModel)
            .where(AssessmentSessionModel.status == SessionStatus.IN_PROGRESS.value)
            .order_by(AssessmentSessionModel.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def query_sessions(
        self,
        student_id: Optional[str] = None,
        profile_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AssessmentSessionModel]:
        """Query sessions filtered by user, profile, and/or status."""
        stmt = select(AssessmentSessionModel)
        if student_id:
            stmt = stmt.where(AssessmentSessionModel.student_id == student_id)
        if profile_id:
            stmt = stmt.where(AssessmentSessionModel.profile_id == profile_id)
        if status:
            stmt = stmt.where(AssessmentSessionModel.status == status)
        stmt = stmt.order_by(AssessmentSessionModel.started_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_activity(self, session_id: str) -> Optional[AssessmentSessionModel]:
        """Updates last_activity_at timestamp to now."""
        sess = await self.get_by_id(session_id)
        if sess:
            sess.last_activity_at = datetime.now(timezone.utc)
            await self.session.flush()
        return sess

    async def update_status(
        self,
        session_id: str,
        new_status: SessionStatus,
        completed_at: Optional[datetime] = None
    ) -> Optional[AssessmentSessionModel]:
        sess = await self.get_by_id(session_id)
        if not sess:
            return None

        current = SessionStatus(sess.status)
        validate_session_transition(current, new_status)

        sess.status = new_status.value
        now = datetime.now(timezone.utc)
        sess.last_activity_at = now

        if completed_at:
            sess.completed_at = completed_at
        elif new_status in (SessionStatus.COMPLETED, SessionStatus.EXPIRED, SessionStatus.ABANDONED, SessionStatus.CANCELLED):
            sess.completed_at = now

        await self.session.flush()
        return sess
