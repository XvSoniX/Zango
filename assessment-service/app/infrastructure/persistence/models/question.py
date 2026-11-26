from typing import List, Optional, Dict, Any
from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    Boolean,
    JSON,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.domain.enums import QuestionType, QuestionVersionStatus, CalibrationStatus
from app.infrastructure.persistence.base import Base, TimestampMixin

class QuestionModel(Base, TimestampMixin):
    """
    Persistent entity representing a question's stable identity.
    Independent of mutable version content.
    """
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    question_type: Mapped[str] = mapped_column(
        String(32),
        default=QuestionType.MULTIPLE_CHOICE.value,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    versions: Mapped[List["QuestionVersionModel"]] = relationship(
        "QuestionVersionModel",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionVersionModel.version.desc()",
        lazy="selectin"
    )

    profile_associations: Mapped[List["ProfileQuestionAssociationModel"]] = relationship(
        "ProfileQuestionAssociationModel",
        back_populates="question",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def get_latest_version(self) -> Optional["QuestionVersionModel"]:
        """Returns the most recent version of this question."""
        if not self.versions:
            return None
        return max(self.versions, key=lambda v: v.version)

    def get_active_version(self) -> Optional["QuestionVersionModel"]:
        """Returns the latest PUBLISHED version of this question."""
        published = [v for v in self.versions if v.status == QuestionVersionStatus.PUBLISHED.value]
        if not published:
            return None
        return max(published, key=lambda v: v.version)


class QuestionVersionModel(Base, TimestampMixin):
    """
    Immutable or versioned snapshot of question content, options,
    psychometric parameters, and dimension weights.
    """
    __tablename__ = "question_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("questions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(32),
        default=QuestionVersionStatus.PUBLISHED.value,
        nullable=False,
        index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(
        String(32),
        default=QuestionType.MULTIPLE_CHOICE.value,
        nullable=False
    )
    options: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(32), nullable=False)

    # Psychometric parameters
    difficulty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    discrimination: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    guessing: Mapped[float] = mapped_column(Float, default=0.25, nullable=False)

    # Operational parameters
    min_age: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_age: Mapped[int] = mapped_column(Integer, default=18, nullable=False)
    estimated_time: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    # Dimensions vector (map of dimension_code -> weight in [0, 1])
    dimensions: Mapped[Dict[str, float]] = mapped_column(JSON, nullable=False)

    # Governance & Exposure
    calibration_status: Mapped[str] = mapped_column(
        String(32),
        default=CalibrationStatus.UNCALIBRATED.value,
        nullable=False,
        index=True
    )
    exposure_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    question: Mapped["QuestionModel"] = relationship("QuestionModel", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("question_id", "version", name="uq_question_version"),
        CheckConstraint("min_age <= max_age", name="ck_question_version_age_range"),
        CheckConstraint("min_age >= 1", name="ck_question_version_min_age_positive"),
        CheckConstraint("estimated_time > 0", name="ck_question_version_estimated_time"),
        CheckConstraint("guessing >= 0.0 AND guessing < 1.0", name="ck_question_version_guessing"),
        CheckConstraint("discrimination > 0.0 AND discrimination <= 4.0", name="ck_question_version_discrimination"),
        CheckConstraint("difficulty >= -4.0 AND difficulty <= 4.0", name="ck_question_version_difficulty"),
        Index("ix_question_versions_age", "min_age", "max_age"),
    )
