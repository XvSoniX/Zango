from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Set
from pydantic import BaseModel, model_validator
from app.domain.enums import CognitiveDimension

@dataclass(frozen=True)
class DimensionDefinition:
    """Metadata specification for a cognitive dimension."""
    code: str
    display_name_en: str
    display_name_fa: str
    description: str

DIMENSION_REGISTRY: Dict[str, DimensionDefinition] = {
    CognitiveDimension.LOGICAL_REASONING.value: DimensionDefinition(
        code=CognitiveDimension.LOGICAL_REASONING.value,
        display_name_en="Logical Reasoning",
        display_name_fa="استدلال منطقی",
        description="Deductive and inductive logic, pattern identification, validity analysis, and rule inference."
    ),
    CognitiveDimension.ALGORITHMIC_THINKING.value: DimensionDefinition(
        code=CognitiveDimension.ALGORITHMIC_THINKING.value,
        display_name_en="Algorithmic Thinking",
        display_name_fa="تفکر الگوریتمی",
        description="Step-by-step procedure formulation, condition branching, loops, and optimization mindset."
    ),
    CognitiveDimension.PROBLEM_SOLVING.value: DimensionDefinition(
        code=CognitiveDimension.PROBLEM_SOLVING.value,
        display_name_en="Problem Solving",
        display_name_fa="حل مسئله",
        description="Decomposing complex scenarios, identifying root causes, and finding efficient solution paths."
    ),
    CognitiveDimension.SPATIAL_REASONING.value: DimensionDefinition(
        code=CognitiveDimension.SPATIAL_REASONING.value,
        display_name_en="Spatial Reasoning",
        display_name_fa="استدلال فضایی",
        description="Mental rotation, 2D/3D visual transformation, spatial pattern recognition, and geometric intuition."
    ),
    CognitiveDimension.COMPUTATIONAL_THINKING.value: DimensionDefinition(
        code=CognitiveDimension.COMPUTATIONAL_THINKING.value,
        display_name_en="Computational Thinking",
        display_name_fa="تفکر رایانشی",
        description="Abstraction, data organization, decomposition, and algorithmic modeling of real-world problems."
    ),
}

def normalize_dimension_code(code: str) -> str:
    """Normalizes and validates a dimension code."""
    normalized = code.strip().lower()
    if normalized in DIMENSION_REGISTRY:
        return normalized
    # Check if uppercase enum name matches
    upper = code.strip().upper()
    for dim_code in DIMENSION_REGISTRY:
        if dim_code.upper() == upper:
            return dim_code
    raise ValueError(f"Unrecognized cognitive dimension code: '{code}'. Valid codes: {list(DIMENSION_REGISTRY.keys())}")

def is_valid_dimension_code(code: str) -> bool:
    try:
        normalize_dimension_code(code)
        return True
    except (ValueError, AttributeError):
        return False

class DimensionsVector(BaseModel):
    """
    Value object representing a question's multidimensional association weights.
    Each weight is bounded in [0.0, 1.0].
    Note: This is an association vector, NOT a probability distribution (sum does not have to equal 1.0).
    """
    weights: Dict[str, float]

    @model_validator(mode="before")
    @classmethod
    def validate_weights(cls, data: Any) -> Any:
        if isinstance(data, DimensionsVector):
            return data
        
        raw_dict = data
        if isinstance(data, dict) and "weights" in data and len(data) == 1:
            raw_dict = data["weights"]

        if not isinstance(raw_dict, dict):
            raise ValueError(f"DimensionsVector must be initialized from a dictionary, got {type(raw_dict).__name__}")

        if not raw_dict:
            raise ValueError("DimensionsVector cannot be empty; at least one dimension weight is required.")

        normalized: Dict[str, float] = {}
        for key, value in raw_dict.items():
            norm_key = normalize_dimension_code(str(key))
            try:
                numeric_val = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"Weight for dimension '{norm_key}' must be a float, got '{value}'")

            if not (0.0 <= numeric_val <= 1.0):
                raise ValueError(f"Weight for dimension '{norm_key}' must be in [0.0, 1.0], got {numeric_val}")

            normalized[norm_key] = round(numeric_val, 4)

        return {"weights": normalized}

    def get_weight(self, dimension_code: str) -> float:
        """Returns weight for dimension (0.0 if not present)."""
        try:
            norm_code = normalize_dimension_code(dimension_code)
            return self.weights.get(norm_code, 0.0)
        except ValueError:
            return 0.0

    def get_active_dimensions(self, threshold: float = 0.0) -> List[str]:
        """Returns list of dimensions having weight strictly greater than threshold."""
        return [k for k, v in self.weights.items() if v > threshold]

    def dominant_dimension(self) -> Optional[str]:
        """Returns the dimension code with the highest weight."""
        if not self.weights:
            return None
        return max(self.weights.items(), key=lambda x: x[1])[0]

    def to_dict(self) -> Dict[str, float]:
        """Serializes vector to standard dictionary."""
        return dict(self.weights)

    def is_compatible_with_profile(self, profile_dimensions: List[str]) -> bool:
        """
        Validates whether this question's vector is compatible with a given profile.
        A vector is compatible if at least one active dimension (>0) is targeted by the profile.
        """
        profile_set = {normalize_dimension_code(d) for d in profile_dimensions}
        active_set = set(self.get_active_dimensions(threshold=0.0))
        return bool(profile_set.intersection(active_set))
