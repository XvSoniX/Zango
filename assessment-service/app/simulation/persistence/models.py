from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy import (
    String,
    Integer,
    Float,
    JSON,
    DateTime,
    ForeignKey,
    Index,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.persistence.base import Base


class SimulationRunModel(Base):
    """
    Persistent entity representing a batch simulation experiment run.
    Contains overall configuration, participant counts, seed, and execution status.
    """
    __tablename__ = "simulation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False, index=True)
    profile_code: Mapped[str] = mapped_column(String(64), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False)
    random_seed: Mapped[int] = mapped_column(Integer, nullable=False, default=42)

    participant_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_participant_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_participant_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    configuration: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # Relationships
    participant_results: Mapped[List["SimulationParticipantResultModel"]] = relationship(
        "SimulationParticipantResultModel",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    __table_args__ = (
        Index("ix_simulation_runs_status_created", "status", "created_at"),
    )


class SimulationParticipantResultModel(Base):
    """
    Captures complete end-to-end evaluation data for a single synthetic participant.
    Preserves ground-truth ability separately from the engine's estimated ability.
    Holds full step-by-step question records to power TASK-034 and TASK-035.
    """
    __tablename__ = "simulation_participant_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    synthetic_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    archetype: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    age: Mapped[int] = mapped_column(Integer, nullable=False)

    # Strict separation of Ground Truth vs Estimated Ability
    ground_truth_ability: Mapped[Dict[str, float]] = mapped_column(JSON, nullable=False)
    estimated_ability: Mapped[Dict[str, float]] = mapped_column(JSON, nullable=False)
    uncertainty_vector: Mapped[Dict[str, float]] = mapped_column(JSON, nullable=False)
    dimension_coverage: Mapped[Dict[str, int]] = mapped_column(JSON, nullable=False)

    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    session_status: Mapped[str] = mapped_column(String(32), nullable=False)
    stopping_reason: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    answered_question_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    final_snapshot_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Question-level step records: question_id, version_id, difficulty, correctness, response_time, etc.
    question_records: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    error_message: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    run: Mapped["SimulationRunModel"] = relationship("SimulationRunModel", back_populates="participant_results")

    __table_args__ = (
        Index("ix_sim_results_run_archetype", "run_id", "archetype"),
    )
