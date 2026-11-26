from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.persistence.models.profile import AssessmentProfileModel, ProfileQuestionAssociationModel

class AssessmentProfileRepository:
    """Repository handling persistence and queries for AssessmentProfile entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, profile_id: int) -> Optional[AssessmentProfileModel]:
        stmt = select(AssessmentProfileModel).where(AssessmentProfileModel.id == profile_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_code(self, code: str, version: Optional[int] = None) -> Optional[AssessmentProfileModel]:
        stmt = select(AssessmentProfileModel).where(AssessmentProfileModel.code == code)
        if version is not None:
            stmt = stmt.where(AssessmentProfileModel.version == version)
        else:
            stmt = stmt.order_by(AssessmentProfileModel.version.desc())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_active_profiles(self) -> List[AssessmentProfileModel]:
        stmt = select(AssessmentProfileModel).where(AssessmentProfileModel.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def query_profiles(
        self,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AssessmentProfileModel]:
        stmt = select(AssessmentProfileModel)
        if is_active is not None:
            stmt = stmt.where(AssessmentProfileModel.is_active == is_active)
        stmt = stmt.order_by(AssessmentProfileModel.id.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_profile(self, profile: AssessmentProfileModel) -> AssessmentProfileModel:
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def update_profile(
        self,
        profile_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        dimensions: Optional[List[str]] = None,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None
    ) -> Optional[AssessmentProfileModel]:
        profile = await self.get_by_id(profile_id)
        if not profile:
            return None

        if title is not None:
            profile.title = title
        if description is not None:
            profile.description = description
        if is_active is not None:
            profile.is_active = is_active
        if dimensions is not None:
            profile.dimensions = dimensions
        if min_age is not None:
            profile.min_age = min_age
        if max_age is not None:
            profile.max_age = max_age

        await self.session.flush()
        return profile

    async def associate_question(
        self,
        profile_id: int,
        question_id: int,
        is_active: bool = True
    ) -> ProfileQuestionAssociationModel:
        stmt = select(ProfileQuestionAssociationModel).where(
            and_(
                ProfileQuestionAssociationModel.profile_id == profile_id,
                ProfileQuestionAssociationModel.question_id == question_id
            )
        )
        result = await self.session.execute(stmt)
        existing = result.scalars().first()
        if existing:
            existing.is_active = is_active
            return existing

        assoc = ProfileQuestionAssociationModel(
            profile_id=profile_id,
            question_id=question_id,
            is_active=is_active
        )
        self.session.add(assoc)
        await self.session.flush()
        return assoc

    async def is_question_in_profile(self, profile_id: int, question_id: int) -> bool:
        stmt = select(ProfileQuestionAssociationModel).where(
            and_(
                ProfileQuestionAssociationModel.profile_id == profile_id,
                ProfileQuestionAssociationModel.question_id == question_id,
                ProfileQuestionAssociationModel.is_active == True
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first() is not None
