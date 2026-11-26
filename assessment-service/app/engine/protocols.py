from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Protocol, runtime_checkable, Sequence
from app.domain.enums import StoppingReason

@dataclass(frozen=True)
class AbilityState:
    """
    Multidimensional ability state.
    dimension_scores: map of dimension -> normalized score
    uncertainty: map of dimension -> measurement standard error
    """
    dimension_scores: Dict[str, float]
    uncertainty: Dict[str, float]
    response_count: int
    dimension_coverage: Dict[str, int]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class EvaluationResult:
    """Outcome of evaluating a submitted answer."""
    is_correct: bool
    score: float
    response_time_ms: int
    raw_answer: Dict[str, Any]
    evaluator_version: str
    question_version_id: Optional[int] = None
    evaluation_status: str = "VALID"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class SelectionResult:
    """Outcome of adaptive question selection."""
    selected_question_id: Optional[int]
    selected_version: Optional[int]
    candidate_scores: Dict[int, float]
    selection_reason: str
    selector_version: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class StoppingDecision:
    """Outcome of stopping strategy evaluation."""
    should_stop: bool
    reason: Optional[StoppingReason] = None
    detail: Optional[str] = None
    stopping_version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ItemParameterSnapshot:
    """Snapshot of question parameters used by the engine."""
    question_id: int
    version: int
    dimensions: Dict[str, float]
    difficulty: float
    discrimination: float
    guessing: float
    min_age: int
    max_age: int
    exposure_limit: int
    exposure_count: int
    is_active: bool
    correct_answer: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None
    question_type: str = "MULTIPLE_CHOICE"
    calibration_status: str = "UNCALIBRATED"

@dataclass(frozen=True)
class AssessmentContext:
    """Stateless context for engine computations."""
    session_id: str
    student_id: str
    student_age: int
    profile_code: str
    target_dimensions: List[str]
    current_ability: AbilityState
    answered_question_ids: List[int]
    response_history: List[EvaluationResult]
    elapsed_time_seconds: float
    max_duration_seconds: float
    min_questions: int
    max_questions: int
    random_seed: int

@runtime_checkable
class AnswerEvaluator(Protocol):
    """Protocol for scoring student answers."""
    def evaluate(
        self,
        question: ItemParameterSnapshot,
        submitted_answer: Dict[str, Any],
        response_time_ms: int,
    ) -> EvaluationResult: ...

@runtime_checkable
class AbilityEstimationStrategy(Protocol):
    """Protocol for multidimensional ability estimation."""
    def estimate(
        self,
        current_state: AbilityState,
        latest_evaluation: EvaluationResult,
        question: ItemParameterSnapshot,
        context: AssessmentContext,
    ) -> AbilityState: ...

@runtime_checkable
class QuestionSelectionStrategy(Protocol):
    """Protocol for adaptive question selection."""
    def select(
        self,
        candidate_pool: Sequence[ItemParameterSnapshot],
        context: AssessmentContext,
    ) -> SelectionResult: ...

@runtime_checkable
class StoppingStrategy(Protocol):
    """Protocol for determining when testing terminates."""
    def evaluate(
        self,
        context: AssessmentContext,
        ability_state: AbilityState,
    ) -> StoppingDecision: ...

@runtime_checkable
class ReportGenerator(Protocol):
    """Protocol for creating final multidimensional reports."""
    def generate_report(
        self,
        context: AssessmentContext,
        final_ability: AbilityState,
    ) -> Dict[str, Any]: ...
