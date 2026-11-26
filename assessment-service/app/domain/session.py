from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from app.domain.enums import SessionStatus

def validate_session_transition(current_status: SessionStatus, new_status: SessionStatus) -> None:
    """
    Validates legal state transitions for an assessment session.
    Terminal states (COMPLETED, EXPIRED, ABANDONED, CANCELLED) cannot revert to IN_PROGRESS.
    """
    terminal_statuses = {
        SessionStatus.COMPLETED,
        SessionStatus.EXPIRED,
        SessionStatus.ABANDONED,
        SessionStatus.CANCELLED
    }
    if current_status in terminal_statuses and new_status == SessionStatus.IN_PROGRESS:
        raise ValueError(
            f"Illegal session status transition: Cannot revert terminal session '{current_status.value}' to '{new_status.value}'."
        )

def validate_answer_payload(answer: Dict[str, Any]) -> str:
    """
    Validates submitted student answer payload.
    In Multiple Choice Questions, requires 'selected_option' key.
    """
    if not isinstance(answer, dict):
        raise ValueError(f"Answer payload must be a JSON object, got {type(answer).__name__}")

    selected = answer.get("selected_option")
    if not selected:
        raise ValueError("Answer payload must contain a non-empty 'selected_option' field")

    return str(selected).strip().upper()

def evaluate_answer_correctness(selected_option: str, canonical_correct_answer: str) -> Tuple[bool, float]:
    """
    Determines answer correctness by comparing against canonical question version correct answer.
    Returns (is_correct: bool, score: float).
    """
    norm_selected = str(selected_option).strip().upper()
    norm_correct = str(canonical_correct_answer).strip().upper()
    is_correct = (norm_selected == norm_correct)
    score = 1.0 if is_correct else 0.0
    return is_correct, score

def validate_response_time(response_time_ms: int) -> int:
    """Ensures response time in milliseconds is non-negative and realistic."""
    try:
        rt = int(response_time_ms)
    except (TypeError, ValueError):
        raise ValueError("response_time_ms must be an integer")

    if rt < 0:
        raise ValueError(f"response_time_ms cannot be negative, got {rt}")
    if rt > 3_600_000:  # 1 hour max single question
        raise ValueError(f"response_time_ms exceeds maximum realistic threshold of 1 hour, got {rt}")
    return rt

def validate_idempotency_key(key: str) -> str:
    """Validates client-supplied idempotency key."""
    if not key or not str(key).strip():
        raise ValueError("idempotency_key cannot be empty")
    cleaned = str(key).strip()
    if len(cleaned) > 64:
        raise ValueError(f"idempotency_key length cannot exceed 64 characters, got {len(cleaned)}")
    return cleaned
