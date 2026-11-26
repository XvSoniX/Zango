from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.persistence.models.report import AssessmentReportModel


class AssessmentReportRepository:
    """Repository handling persistence and queries for AssessmentReport entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_report(self, report: AssessmentReportModel) -> AssessmentReportModel:
        """Atomically persists and flushes a new final report."""
        self.session.add(report)
        await self.session.flush()
        return report

    async def get_by_id(self, report_id: str) -> Optional[AssessmentReportModel]:
        """Retrieves a report by its primary key ID."""
        stmt = select(AssessmentReportModel).where(AssessmentReportModel.id == report_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_session_id(self, session_id: str) -> Optional[AssessmentReportModel]:
        """Retrieves the unique report associated with an assessment session."""
        stmt = select(AssessmentReportModel).where(AssessmentReportModel.session_id == session_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_student_id(
        self,
        student_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[AssessmentReportModel]:
        """Retrieves all reports generated for a student."""
        stmt = (
            select(AssessmentReportModel)
            .where(AssessmentReportModel.student_id == student_id)
            .order_by(AssessmentReportModel.generated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
