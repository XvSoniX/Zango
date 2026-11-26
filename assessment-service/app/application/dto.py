"""
Data Transfer Objects (DTOs) for Application Services.
Defines inputs and outputs for StartAssessment, NextQuestion, and SubmitAnswer.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


# ==========================================
# TASK-025: Start Assessment DTOs
# ==========================================

class StartAssessmentCommand(BaseModel):
    """Input payload for initiating a new assessment session."""
    student_id: str = Field(..., min_length=1, description="Authenticated student identifier")
    student_age: int = Field(..., ge=1, le=120, description="Student age in completed years")
    profile_code: str = Field(..., min_length=1, description="Target assessment profile code")
    algorithm_version: Optional[str] = Field(default=None, description="Optional algorithm version override")
    random_seed: Optional[int] = Field(default=None, description="Optional deterministic seed")


class StartAssessmentResultDTO(BaseModel):
    """Output summary returned when a session is successfully initiated."""
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    student_id: str
    student_age: int
    profile_id: int
    profile_code: str
    status: str
    started_at: datetime
    algorithm_version: str
    target_dimensions: List[str]
    initial_scores: Dict[str, float]
    initial_uncertainty: Dict[str, float]


# ==========================================
# TASK-026: Next Question DTOs
# ==========================================

class NextQuestionQuery(BaseModel):
    """Input query for requesting the next adaptive question."""
    session_id: str = Field(..., min_length=1, description="Unique session identifier")
    student_id: str = Field(..., min_length=1, description="Authenticated student identifier")


class PublicQuestionOptionDTO(BaseModel):
    """Sanitized option representation for student rendering (no correct answer leak)."""
    key: str
    text: str


class PublicQuestionDTO(BaseModel):
    """Sanitized question presentation for student (strict secrecy of psychometrics and answers)."""
    question_id: int
    question_version_id: int
    question_type: str
    content: str
    options: List[PublicQuestionOptionDTO]
    estimated_time: int
    sequence_number: int


class NextQuestionResultDTO(BaseModel):
    """Result of requesting the next question: either a question or a stopping decision."""
    session_id: str
    should_stop: bool
    stopping_reason: Optional[str] = None
    stopping_detail: Optional[str] = None
    question: Optional[PublicQuestionDTO] = None
    progress: Dict[str, Any] = Field(default_factory=dict)


# ==========================================
# TASK-027: Submit Answer DTOs
# ==========================================

class SubmitAnswerCommand(BaseModel):
    """Input command for submitting an answer to an active question version."""
    session_id: str = Field(..., min_length=1, description="Unique session identifier")
    student_id: str = Field(..., min_length=1, description="Authenticated student identifier")
    question_version_id: int = Field(..., ge=1, description="Question version being answered")
    answer: Dict[str, Any] = Field(..., description="Student response payload, e.g. {'selected_option': 'B'}")
    response_time_ms: int = Field(..., ge=0, description="Response time in milliseconds")
    idempotency_key: str = Field(..., min_length=1, max_length=64, description="Client idempotency key")


class SubmitAnswerResultDTO(BaseModel):
    """Result of evaluating and persisting a student's answer (never leaks correct answer)."""
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    response_id: str
    question_id: int
    question_version_id: int
    is_correct: bool
    score: float
    response_time_ms: int
    idempotency_key: str
    answered_at: datetime
    response_count: int
    session_status: str
    is_retry: bool = False


# ==========================================
# TASK-028 & TASK-029: Session Summary & Status DTOs
# ==========================================

class SessionSummaryDTO(BaseModel):
    """Detailed summary of session progress, status, and ability state."""
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    student_id: str
    student_age: int
    profile_id: int
    profile_code: str
    status: str
    started_at: datetime
    last_activity_at: datetime
    completed_at: Optional[datetime] = None
    response_count: int
    elapsed_seconds: float
    target_dimensions: List[str]
    current_scores: Dict[str, float]
    current_uncertainty: Dict[str, float]
    completion_reason: Optional[str] = None
    completion_detail: Optional[str] = None


# ==========================================
# TASK-032: Ability Snapshot & History DTOs
# ==========================================

class AbilitySnapshotDTO(BaseModel):
    """Immutable snapshot of estimated cognitive abilities and uncertainties."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    session_id: str
    snapshot_sequence: int
    ability_scores: Dict[str, float]
    uncertainty_scores: Dict[str, float]
    dimension_coverage: Dict[str, int]
    answered_question_count: int
    algorithm_version: str
    checkpoint_type: str
    created_at: datetime


class AbilityHistoryResponseDTO(BaseModel):
    """Paginated collection of ability snapshots."""
    items: List[AbilitySnapshotDTO]
    total: int
    limit: int
    offset: int


# ==========================================
# TASK-031: Assessment Report DTOs
# ==========================================

class DimensionOverviewDTO(BaseModel):
    """Evaluation metrics for a specific cognitive dimension."""
    dimension_code: str
    dimension_name: str
    ability_score: float
    uncertainty: float
    confidence_interval_low: float = -1.96
    confidence_interval_high: float = 1.96
    percentile_rank: int = 50
    evidence_count: int
    interpretation_level: str


class StrengthOrGrowthItemDTO(BaseModel):
    """Identified relative strength or growth opportunity with constructive framing."""
    dimension_code: str
    dimension_name: str
    ability_score: float
    uncertainty: float
    title: str
    description: str
    evidence_level: str


class ConfidenceAuditDTO(BaseModel):
    """Assessment measurement reliability and diagnostic limitations audit."""
    overall_confidence: str
    average_uncertainty: float
    coverage_summary: str
    limitations_notice: str


class AssessmentReportDTO(BaseModel):
    """Structured analytical assessment report suitable for parents and clinicians."""
    model_config = ConfigDict(from_attributes=True)

    report_id: str
    user_id: str
    assessment_session_id: str
    assessment_profile_id: int
    completed_at: datetime
    total_answered_questions: int
    total_duration_seconds: float
    algorithm_version: str
    report_version: str
    report_mode: str = "RULE_BASED_ANALYTICAL"
    clinician_review_status: str = "PENDING_REVIEW"
    quality_status: str = "INTERPRETABLE"
    quality_reasons: List[str] = Field(default_factory=list)
    ability_overview: List[DimensionOverviewDTO]
    strengths: List[StrengthOrGrowthItemDTO]
    growth_areas: List[StrengthOrGrowthItemDTO]
    confidence_audit: ConfidenceAuditDTO
    general_summary: str
    observed_highlights: List[str] = Field(default_factory=list)
    next_experiments: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    anomaly_flags: List[str] = Field(default_factory=list)
    generated_at: datetime


