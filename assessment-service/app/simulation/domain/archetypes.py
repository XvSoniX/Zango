from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass


class ArchetypeType(str, Enum):
    BALANCED = "BALANCED"
    STRONG = "STRONG"
    DEVELOPING = "DEVELOPING"
    SPECIALIZED = "SPECIALIZED"
    MIXED = "MIXED"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True)
class ArchetypeTemplate:
    """Template specifying ability priors for a synthetic participant archetype."""
    archetype: ArchetypeType
    base_scores: Dict[str, float]
    score_variance: float = 0.15
    speed_factor: float = 1.0  # 1.0 = average, >1.0 = faster, <1.0 = deliberate


# Standard baseline archetypes scaled to IRT interval [-3.0, +3.0]
ARCHETYPE_TEMPLATES: Dict[ArchetypeType, ArchetypeTemplate] = {
    ArchetypeType.BALANCED: ArchetypeTemplate(
        archetype=ArchetypeType.BALANCED,
        base_scores={
            "logical_reasoning": 0.0,
            "algorithmic_thinking": 0.0,
            "problem_solving": 0.0,
            "spatial_reasoning": 0.0,
            "computational_thinking": 0.0,
        },
        score_variance=0.2,
        speed_factor=1.0,
    ),
    ArchetypeType.STRONG: ArchetypeTemplate(
        archetype=ArchetypeType.STRONG,
        base_scores={
            "logical_reasoning": 1.8,
            "algorithmic_thinking": 1.7,
            "problem_solving": 1.9,
            "spatial_reasoning": 1.6,
            "computational_thinking": 1.8,
        },
        score_variance=0.2,
        speed_factor=1.25,
    ),
    ArchetypeType.DEVELOPING: ArchetypeTemplate(
        archetype=ArchetypeType.DEVELOPING,
        base_scores={
            "logical_reasoning": -1.5,
            "algorithmic_thinking": -1.6,
            "problem_solving": -1.4,
            "spatial_reasoning": -1.5,
            "computational_thinking": -1.7,
        },
        score_variance=0.2,
        speed_factor=0.8,
    ),
    ArchetypeType.SPECIALIZED: ArchetypeTemplate(
        archetype=ArchetypeType.SPECIALIZED,
        base_scores={
            "logical_reasoning": 2.0,
            "algorithmic_thinking": 1.8,
            "problem_solving": 0.2,
            "spatial_reasoning": -0.5,
            "computational_thinking": 0.0,
        },
        score_variance=0.2,
        speed_factor=1.1,
    ),
    ArchetypeType.MIXED: ArchetypeTemplate(
        archetype=ArchetypeType.MIXED,
        base_scores={
            "logical_reasoning": 1.2,
            "algorithmic_thinking": -0.8,
            "problem_solving": 0.5,
            "spatial_reasoning": 1.5,
            "computational_thinking": -1.2,
        },
        score_variance=0.25,
        speed_factor=1.0,
    ),
}
