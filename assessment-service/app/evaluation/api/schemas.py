"""
Pydantic API schemas for Assessment Engine Evaluation Framework (TASK-034 & TASK-035).
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class StartEvaluationRequest(BaseModel):
    """
    Request payload to trigger an evaluation on completed simulation runs.
    """
    simulation_run_ids: List[str] = Field(
        ...,
        min_length=1,
        description="List of completed simulation run IDs to evaluate"
    )
    configuration: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional overrides for evaluation thresholds, buckets, etc."
    )


class EvaluationRunResponse(BaseModel):
    """
    Metadata representation of an evaluation execution run.
    """
    id: str
    evaluation_type: str
    status: str
    source_simulation_run_ids: List[str]
    algorithm_version: str
    question_bank_version: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    error_message: Optional[str] = None


class QuestionSelectionEvaluationResponse(BaseModel):
    """
    Structured report for TASK-034 Question Selection Evaluation.
    """
    evaluation_run_id: str
    status: str
    algorithm_version: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    eligible_sessions_count: int
    excluded_sessions_count: int
    summary_metrics: Dict[str, Any]
    dimension_coverage: Dict[str, Any]
    difficulty_distribution: Dict[str, Any]
    exposure_and_repetition: Dict[str, Any]
    assessment_length: Dict[str, Any]
    selection_sequence: Dict[str, Any]
    archetype_breakdowns: Dict[str, Any]
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)


class AbilityEstimationEvaluationResponse(BaseModel):
    """
    Structured report for TASK-035 Ability Estimation Quality Evaluation.
    """
    evaluation_run_id: str
    status: str
    algorithm_version: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    eligible_sessions_count: int
    excluded_sessions_count: int
    summary_metrics: Dict[str, Any]
    dimension_metrics: Dict[str, Any]
    uncertainty_analysis: Dict[str, Any]
    length_vs_quality: Dict[str, Any]
    archetype_breakdowns: Dict[str, Any]
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
