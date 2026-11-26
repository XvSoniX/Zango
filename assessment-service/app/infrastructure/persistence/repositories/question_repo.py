from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.persistence.models.question import QuestionModel, QuestionVersionModel
from app.infrastructure.persistence.models.profile import ProfileQuestionAssociationModel
from app.domain.enums import QuestionVersionStatus

class QuestionRepository:
    """Repository handling persistence and queries for Question and QuestionVersion entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, question_id: int) -> Optional[QuestionModel]:
        stmt = select(QuestionModel).where(QuestionModel.id == question_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_code(self, code: str) -> Optional[QuestionModel]:
        stmt = select(QuestionModel).where(QuestionModel.code == code)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_version_by_id(self, version_id: int) -> Optional[QuestionVersionModel]:
        stmt = select(QuestionVersionModel).where(QuestionVersionModel.id == version_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_version_by_question_and_num(self, question_id: int, version: int) -> Optional[QuestionVersionModel]:
        stmt = select(QuestionVersionModel).where(
            QuestionVersionModel.question_id == question_id,
            QuestionVersionModel.version == version
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_versions_by_question_id(self, question_id: int) -> List[QuestionVersionModel]:
        stmt = (
            select(QuestionVersionModel)
            .where(QuestionVersionModel.question_id == question_id)
            .order_by(QuestionVersionModel.version.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_questions(self, limit: int = 100, offset: int = 0) -> List[QuestionModel]:
        stmt = (
            select(QuestionModel)
            .where(QuestionModel.is_active == True)
            .order_by(QuestionModel.id.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def query_questions(
        self,
        is_active: Optional[bool] = None,
        question_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[QuestionModel]:
        stmt = select(QuestionModel)
        if is_active is not None:
            stmt = stmt.where(QuestionModel.is_active == is_active)
        if question_type is not None:
            stmt = stmt.where(QuestionModel.question_type == question_type)
        stmt = stmt.order_by(QuestionModel.id.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_questions_by_dimension(
        self,
        dimension_code: str,
        min_weight: float = 0.0,
        active_only: bool = True
    ) -> List[QuestionModel]:
        """Filters questions having positive association with a specific cognitive dimension."""
        stmt = select(QuestionModel).join(QuestionVersionModel)
        if active_only:
            stmt = stmt.where(QuestionModel.is_active == True)
        result = await self.session.execute(stmt)
        questions = result.scalars().unique().all()
        matched: List[QuestionModel] = []
        for q in questions:
            latest = q.get_latest_version()
            if latest and isinstance(latest.dimensions, dict):
                norm_dim = dimension_code.strip().lower()
                weight = latest.dimensions.get(norm_dim, 0.0)
                if weight > min_weight:
                    matched.append(q)
        return matched

    async def get_questions_by_difficulty(
        self,
        min_difficulty: float,
        max_difficulty: float,
        active_only: bool = True
    ) -> List[QuestionModel]:
        """Filters questions whose versions fall within the specified IRT difficulty bounds."""
        stmt = (
            select(QuestionModel)
            .join(QuestionVersionModel)
            .where(
                QuestionVersionModel.difficulty >= min_difficulty,
                QuestionVersionModel.difficulty <= max_difficulty
            )
        )
        if active_only:
            stmt = stmt.where(QuestionModel.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_active_questions_for_profile(self, profile_id: int) -> List[QuestionModel]:
        stmt = (
            select(QuestionModel)
            .join(ProfileQuestionAssociationModel, QuestionModel.id == ProfileQuestionAssociationModel.question_id)
            .where(
                ProfileQuestionAssociationModel.profile_id == profile_id,
                ProfileQuestionAssociationModel.is_active == True,
                QuestionModel.is_active == True
            )
            .order_by(QuestionModel.id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_question(self, question: QuestionModel) -> QuestionModel:
        self.session.add(question)
        await self.session.flush()
        return question

    async def create_version(self, version: QuestionVersionModel) -> QuestionVersionModel:
        self.session.add(version)
        await self.session.flush()
        return version

    async def count_questions(self) -> int:
        stmt = select(func.count()).select_from(QuestionModel)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_versions(self) -> int:
        stmt = select(func.count()).select_from(QuestionVersionModel)
        result = await self.session.execute(stmt)
        return result.scalar_one()
