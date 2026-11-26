from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import (
    String,
    Integer,
    JSON,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.persistence.base import Base


class AbilitySnapshotModel(Base):
    """
    Persistent snapshot of multidimensional ability and measurement uncertainty.
    Captured at significant lifecycle checkpoints (initialization, answer submission, session completion).
    Guarantees historical immutability and complete auditability.
    """
    __tablename__ = "ability_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    student_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assessment_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    snapshot_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Multidimensional metric vectors across all 5 cognitive dimensions
    ability_scores: Mapped[Dict[str, float]] = mapped_column(JSON, nullable=False)
    uncertainty_scores: Mapped[Dict[str, float]] = mapped_column(JSON, nullable=False)
    dimension_coverage: Mapped[Dict[str, int]] = mapped_column(JSON, nullable=False)

    answered_question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False)
    checkpoint_type: Mapped[str] = mapped_column(String(32), default="RESPONSE_UPDATE", nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # Relationship to session
    session = relationship("AssessmentSessionModel", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("session_id", "snapshot_sequence", name="uq_snapshot_session_sequence"),
        Index("ix_snapshots_student_created", "student_id", "created_at"),
    )
