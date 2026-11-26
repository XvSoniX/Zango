"""
SQLAlchemy models for Assessment Engine Evaluation Framework (TASK-034 & TASK-035).
Stores immutable historical evaluation runs and structured result payloads.
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy import (
    String,
    JSON,
    DateTime,
    ForeignKey,
    Index,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.persistence.base import Base


class EvaluationRunModel(Base):
    """
    Persistent entity representing an evaluation experiment execution run.
    Evaluates one or more completed simulation runs.
    """
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    evaluation_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False, index=True)

    source_simulation_run_ids: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    configuration: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False)
    question_bank_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1.0")

    error_message: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # Relationships
    question_selection_result: Mapped[Optional["QuestionSelectionEvaluationResultModel"]] = relationship(
        "QuestionSelectionEvaluationResultModel",
        back_populates="evaluation_run",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    ability_estimation_result: Mapped[Optional["AbilityEstimationEvaluationResultModel"]] = relationship(
        "AbilityEstimationEvaluationResultModel",
        back_populates="evaluation_run",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    __table_args__ = (
        Index("ix_evaluation_runs_type_status", "evaluation_type", "status"),
    )


class QuestionSelectionEvaluationResultModel(Base):
    """
    Persistent structured metrics and analysis output for TASK-034.
    """
    __tablename__ = "question_selection_evaluation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    evaluation_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    summary_metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    dimension_coverage: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    difficulty_distribution: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    exposure_metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    assessment_length: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    sequence_analysis: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    archetype_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    anomalies: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    evaluation_run: Mapped["EvaluationRunModel"] = relationship(
        "EvaluationRunModel",
        back_populates="question_selection_result"
    )


class AbilityEstimationEvaluationResultModel(Base):
    """
    Persistent structured metrics and analysis output for TASK-035.
    """
    __tablename__ = "ability_estimation_evaluation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    evaluation_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    summary_metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    dimension_metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    uncertainty_analysis: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    length_vs_quality: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    archetype_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    anomalies: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    limitations: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    evaluation_run: Mapped["EvaluationRunModel"] = relationship(
        "EvaluationRunModel",
        back_populates="ability_estimation_result"
    )
