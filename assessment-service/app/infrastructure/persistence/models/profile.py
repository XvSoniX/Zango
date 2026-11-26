from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    JSON,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.persistence.base import Base, TimestampMixin

class AssessmentProfileModel(Base, TimestampMixin):
    """
    Defines an assessment configuration, target cognitive dimensions,
    and eligible age range.
    """
    __tablename__ = "assessment_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # List of dimension codes evaluated by this profile
    dimensions: Mapped[List[str]] = mapped_column(JSON, nullable=False)

    min_age: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_age: Mapped[int] = mapped_column(Integer, default=18, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    question_associations: Mapped[List["ProfileQuestionAssociationModel"]] = relationship(
        "ProfileQuestionAssociationModel",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_profile_code_version"),
        CheckConstraint("min_age <= max_age", name="ck_profile_age_range"),
        CheckConstraint("min_age >= 1", name="ck_profile_min_age_positive"),
    )


class ProfileQuestionAssociationModel(Base):
    """
    Association table explicitly mapping curated questions to an assessment profile.
    Allows questions to belong to multiple profiles while maintaining independent lifecycles.
    """
    __tablename__ = "profile_questions"

    profile_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("assessment_profiles.id", ondelete="CASCADE"),
        primary_key=True
    )
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        primary_key=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    profile: Mapped["AssessmentProfileModel"] = relationship(
        "AssessmentProfileModel",
        back_populates="question_associations"
    )
    question: Mapped["QuestionModel"] = relationship(
        "QuestionModel",
        back_populates="profile_associations"
    )
