from typing import List, Tuple, Optional
from app.domain.dimensions import normalize_dimension_code, DimensionsVector

def validate_profile_code(code: str) -> str:
    """Validates that a profile code is uppercase alphanumeric with underscores."""
    if not code or not code.strip():
        raise ValueError("Profile code cannot be empty")
    cleaned = code.strip().upper()
    if not all(c.isalnum() or c in ("_", "-") for c in cleaned):
        raise ValueError(f"Profile code '{code}' contains invalid characters. Use alphanumeric and underscores.")
    return cleaned

def validate_profile_dimensions(dimensions: List[str]) -> List[str]:
    """Validates that all dimensions in profile exist in registry."""
    if not dimensions:
        raise ValueError("Assessment profile must target at least one cognitive dimension")
    
    validated: List[str] = []
    seen = set()
    for dim in dimensions:
        norm = normalize_dimension_code(str(dim))
        if norm not in seen:
            seen.add(norm)
            validated.append(norm)
    return validated

def check_compatibility(
    profile_dimensions: List[str],
    profile_min_age: int,
    profile_max_age: int,
    question_dimensions: DimensionsVector,
    question_min_age: int,
    question_max_age: int
) -> Tuple[bool, Optional[str]]:
    """
    Validates compatibility between an AssessmentProfile and a QuestionVersion:
    1. Dimension compatibility: question must have association (>0) with at least one profile dimension.
    2. Age range overlap: [profile_min, profile_max] must overlap with [question_min, question_max].
    """
    # 1. Check Age Overlap
    overlap_start = max(profile_min_age, question_min_age)
    overlap_end = min(profile_max_age, question_max_age)
    if overlap_start > overlap_end:
        return False, (
            f"Age range mismatch: Profile [{profile_min_age}, {profile_max_age}] does not overlap "
            f"with question age range [{question_min_age}, {question_max_age}]."
        )

    # 2. Check Dimension Compatibility
    if not question_dimensions.is_compatible_with_profile(profile_dimensions):
        return False, (
            f"Dimension mismatch: Question active dimensions {question_dimensions.get_active_dimensions()} "
            f"have no overlap with profile dimensions {profile_dimensions}."
        )

    return True, None
