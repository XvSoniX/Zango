from typing import Optional, List
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.persistence.models.session import AssessmentResponseModel

class AssessmentResponseRepository:
    """Repository handling persistence and queries for AssessmentResponse entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_response(self, response: AssessmentResponseModel) -> AssessmentResponseModel:
        self.session.add(response)
        await self.session.flush()
        return response

    async def get_by_id(self, response_id: str) -> Optional[AssessmentResponseModel]:
        stmt = select(AssessmentResponseModel).where(AssessmentResponseModel.id == response_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_session_id(self, session_id: str) -> List[AssessmentResponseModel]:
        stmt = (
            select(AssessmentResponseModel)
            .where(AssessmentResponseModel.session_id == session_id)
            .order_by(AssessmentResponseModel.answered_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_session_and_question(
        self,
        session_id: str,
        question_id: int
    ) -> Optional[AssessmentResponseModel]:
        stmt = select(AssessmentResponseModel).where(
            and_(
                AssessmentResponseModel.session_id == session_id,
                AssessmentResponseModel.question_id == question_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_session_and_version(
        self,
        session_id: str,
        question_version_id: int
    ) -> Optional[AssessmentResponseModel]:
        stmt = select(AssessmentResponseModel).where(
            and_(
                AssessmentResponseModel.session_id == session_id,
                AssessmentResponseModel.question_version_id == question_version_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_idempotency_key(
        self,
        session_id: str,
        idempotency_key: str
    ) -> Optional[AssessmentResponseModel]:
        stmt = select(AssessmentResponseModel).where(
            and_(
                AssessmentResponseModel.session_id == session_id,
                AssessmentResponseModel.idempotency_key == idempotency_key
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def has_answered_question(self, session_id: str, question_id: int) -> bool:
        resp = await self.get_by_session_and_question(session_id, question_id)
        return resp is not None

    async def has_answered_version(self, session_id: str, question_version_id: int) -> bool:
        resp = await self.get_by_session_and_version(session_id, question_version_id)
        return resp is not None

    async def count_by_session(self, session_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(AssessmentResponseModel)
            .where(AssessmentResponseModel.session_id == session_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def query_responses(
        self,
        session_id: str,
        is_correct: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AssessmentResponseModel]:
        stmt = select(AssessmentResponseModel).where(AssessmentResponseModel.session_id == session_id)
        if is_correct is not None:
            stmt = stmt.where(AssessmentResponseModel.is_correct == is_correct)
        stmt = stmt.order_by(AssessmentResponseModel.answered_at.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
