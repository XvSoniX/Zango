import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    JSON,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.domain.enums import SessionStatus
from app.infrastructure.persistence.base import Base

class AssessmentSessionModel(Base):
    """
    Persistent entity representing an adaptive testing session for a student.
    Tracks state transitions, active configuration profile, and associated responses.
    """
    __tablename__ = "assessment_sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    student_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    student_age: Mapped[int] = mapped_column(Integer, nullable=False)
    profile_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("assessment_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=SessionStatus.IN_PROGRESS.value,
        nullable=False,
        index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    algorithm_version: Mapped[str] = mapped_column(
        String(32),
        default="1.0.0-baseline",
        nullable=False
    )
    question_bank_version: Mapped[str] = mapped_column(
        String(32),
        default="1.0.0",
        nullable=False
    )
    random_seed: Mapped[int] = mapped_column(Integer, default=42, nullable=False)
    context_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False
    )

    # Relationships
    profile: Mapped["AssessmentProfileModel"] = relationship(
        "AssessmentProfileModel",
        lazy="selectin"
    )
    responses: Mapped[List["AssessmentResponseModel"]] = relationship(
        "AssessmentResponseModel",
        back_populates="session",
        order_by="AssessmentResponseModel.answered_at",
        lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint("completed_at IS NULL OR completed_at >= started_at", name="ck_session_completed_after_started"),
        CheckConstraint("student_age >= 1", name="ck_session_student_age_positive"),
        Index("ix_assessment_sessions_student_status", "student_id", "status"),
    )


class AssessmentResponseModel(Base):
    """
    Persistent entity representing a student's answer to a specific question version.
    Guarantees atomic response logging, idempotency, and historical immutability.
    """
    __tablename__ = "assessment_responses"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assessment_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("questions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    question_version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("question_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    answer: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    session: Mapped["AssessmentSessionModel"] = relationship(
        "AssessmentSessionModel",
        back_populates="responses",
        lazy="selectin"
    )
    question: Mapped["QuestionModel"] = relationship("QuestionModel", lazy="selectin")
    question_version: Mapped["QuestionVersionModel"] = relationship("QuestionVersionModel", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("session_id", "question_id", name="uq_session_question"),
        UniqueConstraint("session_id", "idempotency_key", name="uq_session_idempotency_key"),
        CheckConstraint("response_time_ms >= 0", name="ck_response_time_positive"),
        CheckConstraint("score >= 0.0", name="ck_response_score_positive"),
        Index("ix_responses_session_version", "session_id", "question_version_id"),
        Index("ix_responses_idempotency", "session_id", "idempotency_key"),
    )
