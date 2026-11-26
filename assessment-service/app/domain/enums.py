from enum import Enum

class CognitiveDimension(str, Enum):
    """
    Standard cognitive dimension codes.
    Values are immutable lowercase string identifiers.
    """
    LOGICAL_REASONING = "logical_reasoning"
    ALGORITHMIC_THINKING = "algorithmic_thinking"
    PROBLEM_SOLVING = "problem_solving"
    SPATIAL_REASONING = "spatial_reasoning"
    COMPUTATIONAL_THINKING = "computational_thinking"

    @classmethod
    def from_string(cls, value: str) -> "CognitiveDimension":
        normalized = value.strip().lower()
        for item in cls:
            if item.value == normalized or item.name.lower() == normalized:
                return item
        raise ValueError(f"Invalid cognitive dimension code: '{value}'")

class QuestionType(str, Enum):
    """Supported question formats."""
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"

class QuestionVersionStatus(str, Enum):
    """Lifecycle status of a specific question version."""
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"
    DEPRECATED = "DEPRECATED"

class CalibrationStatus(str, Enum):
    """Psychometric calibration status of a question version."""
    UNCALIBRATED = "UNCALIBRATED"
    CALIBRATING = "CALIBRATING"
    CALIBRATED = "CALIBRATED"
    RETIRED = "RETIRED"

class SessionStatus(str, Enum):
    """Lifecycle status of an assessment session."""
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"

class ConfidenceLevel(str, Enum):
    """Qualitative confidence bands for ability estimation."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class StoppingReason(str, Enum):
    """Conditions under which testing terminates."""
    MAX_QUESTIONS_REACHED = "MAX_QUESTIONS_REACHED"
    MIN_UNCERTAINTY_ACHIEVED = "MIN_UNCERTAINTY_ACHIEVED"
    TIME_EXPIRED = "TIME_EXPIRED"
    MAX_DURATION_REACHED = "MAX_DURATION_REACHED"
    QUESTION_BANK_EXHAUSTED = "QUESTION_BANK_EXHAUSTED"
    NO_ELIGIBLE_CANDIDATES = "NO_ELIGIBLE_CANDIDATES"
    DIMENSIONS_SATISFIED = "DIMENSIONS_SATISFIED"
    SUFFICIENT_EVIDENCE = "SUFFICIENT_EVIDENCE"
    MANUALLY_TERMINATED = "MANUALLY_TERMINATED"
