from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator

@dataclass(frozen=True)
class Option:
    """Represents a single answer choice in a Multiple Choice Question."""
    key: str
    text: str
    order: int

    def to_dict(self) -> Dict[str, Any]:
        return {"key": self.key, "text": self.text, "order": self.order}

def validate_options(raw_options: List[Dict[str, Any]]) -> List[Option]:
    """
    Validates MCQ options list.
    - Must contain at least 2 options.
    - Each option must have non-empty key and text.
    - Keys must be unique.
    """
    if not isinstance(raw_options, list):
        raise ValueError(f"Options must be a list, got {type(raw_options).__name__}")

    if len(raw_options) < 2:
        raise ValueError(f"A multiple choice question must have at least 2 options, found {len(raw_options)}")

    parsed_options: List[Option] = []
    seen_keys = set()
    seen_orders = set()

    for idx, opt in enumerate(raw_options):
        if not isinstance(opt, dict):
            raise ValueError(f"Option at index {idx} must be a dictionary")

        key = str(opt.get("key", "")).strip().upper()
        if not key:
            raise ValueError(f"Option at index {idx} has an empty 'key'")

        if key in seen_keys:
            raise ValueError(f"Duplicate option key '{key}' found in options list")
        seen_keys.add(key)

        text = str(opt.get("text", "")).strip()
        if not text:
            raise ValueError(f"Option with key '{key}' has empty 'text'")

        order = opt.get("order", idx + 1)
        try:
            order_int = int(order)
        except (TypeError, ValueError):
            raise ValueError(f"Option order must be integer, got '{order}'")

        if order_int in seen_orders:
            raise ValueError(f"Duplicate display order '{order_int}' in options list")
        seen_orders.add(order_int)

        parsed_options.append(Option(key=key, text=text, order=order_int))

    return sorted(parsed_options, key=lambda x: x.order)

def validate_correct_answer(correct_answer: str, options: List[Option]) -> str:
    """Ensures the correct answer matches one of the provided option keys."""
    if not correct_answer:
        raise ValueError("Correct answer cannot be empty")

    normalized = str(correct_answer).strip().upper()
    valid_keys = {opt.key for opt in options}
    if normalized not in valid_keys:
        raise ValueError(f"Correct answer '{normalized}' is not in valid option keys: {sorted(list(valid_keys))}")
    return normalized

def validate_psychometrics(
    difficulty: float,
    discrimination: float,
    guessing: float
) -> Dict[str, float]:
    """
    Validates IRT / CAT psychometric parameters:
    - difficulty (b): [-4.0, 4.0]
    - discrimination (a): (0.0, 4.0]
    - guessing (c): [0.0, 1.0)
    """
    try:
        b = float(difficulty)
        a = float(discrimination)
        c = float(guessing)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Psychometric parameters must be numeric: {e}")

    if not (-4.0 <= b <= 4.0):
        raise ValueError(f"Difficulty parameter 'b' must be in [-4.0, +4.0], got {b}")

    if not (0.0 < a <= 4.0):
        raise ValueError(f"Discrimination parameter 'a' must be in (0.0, 4.0], got {a}")

    if not (0.0 <= c < 1.0):
        raise ValueError(f"Guessing parameter 'c' must be in [0.0, 1.0), got {c}")

    return {"difficulty": round(b, 4), "discrimination": round(a, 4), "guessing": round(c, 4)}

def validate_age_range(min_age: int, max_age: int) -> Dict[str, int]:
    """Validates age range bounds."""
    try:
        min_a = int(min_age)
        max_a = int(max_age)
    except (TypeError, ValueError):
        raise ValueError("Age values must be integers")

    if min_a < 1:
        raise ValueError(f"min_age must be >= 1, got {min_a}")
    if max_a > 120:
        raise ValueError(f"max_age must be <= 120, got {max_a}")
    if min_a > max_a:
        raise ValueError(f"min_age ({min_a}) cannot be greater than max_age ({max_a})")

    return {"min_age": min_a, "max_age": max_a}

def validate_estimated_time(estimated_time: int) -> int:
    """Validates estimated response time in seconds."""
    try:
        t = int(estimated_time)
    except (TypeError, ValueError):
        raise ValueError("estimated_time must be an integer")

    if t <= 0:
        raise ValueError(f"estimated_time must be a positive integer, got {t}")
    return t

def validate_exposure_limit(exposure_limit: Optional[int]) -> Optional[int]:
    """Validates question exposure limit."""
    if exposure_limit is None:
        return None
    try:
        exp_lim = int(exposure_limit)
    except (TypeError, ValueError):
        raise ValueError("exposure_limit must be an integer or None")

    if exp_lim < 1:
        raise ValueError(f"exposure_limit must be >= 1, got {exp_lim}")
    return exp_lim
