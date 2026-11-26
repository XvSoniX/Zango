"""
Evaluation Framework Configuration and Settings.
Centralized thresholds, constants, and policies for TASK-034 & TASK-035.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Dict


class EvaluationType(str, Enum):
    QUESTION_SELECTION = "QUESTION_SELECTION"
    ABILITY_ESTIMATION = "ABILITY_ESTIMATION"
    COMPREHENSIVE = "COMPREHENSIVE"


class EvaluationStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"


# Canonical list of the 5 cognitive dimensions evaluated by the engine
CANONICAL_DIMENSIONS: List[str] = [
    "logical_reasoning",
    "algorithmic_thinking",
    "problem_solving",
    "spatial_reasoning",
    "computational_thinking",
]

DIMENSION_LABELS: Dict[str, str] = {
    "logical_reasoning": "Logical",
    "algorithmic_thinking": "Algorithmic",
    "problem_solving": "Problem Solving",
    "spatial_reasoning": "Spatial",
    "computational_thinking": "Computational",
}


@dataclass
class EvaluationSettings:
    """
    Centralized configurable evaluation thresholds and binning rules.
    Avoids hardcoding arbitrary values throughout evaluation logic.
    """
    # Dimension coverage parameters
    dimension_contribution_threshold: float = 0.10  # min weight in dimension vector to consider contributing
    sufficient_dimension_evidence_threshold: int = 2  # min question exposures to consider evidence sufficient

    # Difficulty bins: tuples of (lower_inclusive, upper_exclusive)
    difficulty_buckets: List[Tuple[float, float]] = field(
        default_factory=lambda: [
            (-4.0, -2.0),
            (-2.0, -1.0),
            (-1.0, 0.0),
            (0.0, 1.0),
            (1.0, 2.0),
            (2.0, 4.0),
        ]
    )

    # Question count bins for assessment length analysis
    question_count_buckets: List[Tuple[int, int]] = field(
        default_factory=lambda: [
            (1, 5),
            (6, 10),
            (11, 15),
            (16, 20),
            (21, 50),
        ]
    )

    # Uncertainty bins (for standard deviation uncertainty in (0, 1.0])
    uncertainty_buckets: List[Tuple[float, float]] = field(
        default_factory=lambda: [
            (0.0, 0.40),
            (0.40, 0.70),
            (0.70, 1.01),
        ]
    )

    # Minimum sample size required to report subgroup metrics safely
    min_subgroup_sample_size: int = 3

    # Exposure warning threshold: fraction of total questions where exposure is considered high
    high_exposure_threshold: float = 0.20
