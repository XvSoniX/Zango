from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import (
    String,
    JSON,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.persistence.base import Base


class AssessmentReportModel(Base):
    """
    Persistent report entity for a completed assessment session.
    Tied deterministically to a specific final AbilitySnapshot.
    Guarantees idempotency and prevents inconsistent re-evaluations.
    """
    __tablename__ = "assessment_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assessment_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True
    )
    student_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    snapshot_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ability_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    report_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False)
    
    # Complete structured JSON report payload
    report_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # Relationships
    session = relationship("AssessmentSessionModel", lazy="selectin")
    snapshot = relationship("AbilitySnapshotModel", lazy="selectin")

    __table_args__ = (
        Index("ix_reports_student_generated", "student_id", "generated_at"),
    )
