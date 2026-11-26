from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.simulation.domain.archetypes import ArchetypeType


class StartSimulationRequest(BaseModel):
    """Payload to initiate a synthetic assessment simulation run."""
    name: str = Field(
        default="Synthetic Cohort Experiment",
        description="Descriptive run title",
        json_schema_extra={"example": "Batch Evaluation Run #1"}
    )
    profile_code: str = Field(
        default="TECHNICAL_TALENT_V1",
        description="Target profile for assessment sessions",
        json_schema_extra={"example": "TECHNICAL_TALENT_V1"}
    )
    participant_count: int = Field(
        default=10,
        ge=1,
        le=500,
        description="Number of synthetic participants",
        json_schema_extra={"example": 10}
    )
    archetypes: Optional[List[ArchetypeType]] = Field(
        default=None,
        description="Specific archetypes to include (default: all archetypes)",
        json_schema_extra={"example": ["BALANCED", "STRONG", "DEVELOPING"]}
    )
    min_age: int = Field(default=12, ge=6, le=99, description="Minimum participant age")
    max_age: int = Field(default=18, ge=6, le=99, description="Maximum participant age")
    random_seed: int = Field(default=42, description="Deterministic master seed")
    custom_ability: Optional[Dict[str, float]] = Field(
        default=None,
        description="Custom 5-dimensional ground-truth ability vector override"
    )


class SimulationRunSummaryResponse(BaseModel):
    """Execution status and summary metrics for a simulation run."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: str
    profile_code: str
    algorithm_version: str
    random_seed: int
    participant_count: int
    completed_participant_count: int
    failed_participant_count: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class SimulationParticipantResultResponse(BaseModel):
    """Detailed result comparison between ground-truth and estimated ability for one synthetic user."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    synthetic_user_id: str
    archetype: str
    age: int
    ground_truth_ability: Dict[str, float]
    estimated_ability: Dict[str, float]
    uncertainty_vector: Dict[str, float]
    dimension_coverage: Dict[str, int]
    session_id: str
    session_status: str
    stopping_reason: Optional[str] = None
    answered_question_count: int
    total_duration_seconds: float
    final_snapshot_id: Optional[str] = None
    question_records: List[Dict[str, Any]] = Field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime
