from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from app.simulation.domain.archetypes import ArchetypeType


@dataclass(frozen=True)
class SyntheticUserProfile:
    """
    Representation of a synthetic assessment participant.
    Holds the ground-truth ability vector across all 5 dimensions.
    Must strictly remain separate from the engine's estimated AbilityState.
    """
    synthetic_user_id: str
    simulation_run_id: str
    archetype: ArchetypeType
    ground_truth_ability: Dict[str, float]
    age: int
    speed_factor: float = 1.0
    random_seed: int = 42
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Validate that all 5 dimensions exist in ground-truth vector
        required_dims = [
            "logical_reasoning",
            "algorithmic_thinking",
            "problem_solving",
            "spatial_reasoning",
            "computational_thinking",
        ]
        for dim in required_dims:
            if dim not in self.ground_truth_ability:
                raise ValueError(f"Missing required dimension '{dim}' in synthetic ground truth profile.")
            val = self.ground_truth_ability[dim]
            if not (-4.0 <= val <= 4.0):
                raise ValueError(f"Ground truth ability for '{dim}' out of bounds [-4.0, +4.0]: {val}")
