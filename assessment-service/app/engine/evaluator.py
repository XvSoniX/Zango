from typing import Dict, Any, Optional, Set, List, Union
from app.engine.protocols import EvaluationResult, ItemParameterSnapshot, AnswerEvaluator
from app.engine.exceptions import (
    InvalidAnswerPayloadError,
    InvalidOptionError,
    UnsupportedQuestionTypeError,
    InvalidQuestionVersionError,
)
from app.config import settings
from app.domain.enums import QuestionType
from app.domain.session import validate_response_time


class BaselineAnswerEvaluator:
    """
    Pure, stateless evaluator for scoring student answers against a specific QuestionVersion.
    Guarantees:
    - Zero database dependencies.
    - Strict validation of answer payload structure.
    - Separation of structural invalidity (exceptions) from incorrect answers (score=0.0).
    - Rapid-guessing anomaly detection (response_time_ms < threshold).
    - Complete protection of canonical correct answer (never disclosed in outputs).
    """

    def __init__(
        self,
        version: str = "2.0.0-irt-mfi",
        rapid_guess_threshold_ms: Optional[int] = None,
    ):
        self.version = version
        self.rapid_guess_threshold_ms = (
            rapid_guess_threshold_ms
            if rapid_guess_threshold_ms is not None
            else settings.RAPID_GUESS_THRESHOLD_MS
        )

    def evaluate(
        self,
        question: Any,
        submitted_answer: Dict[str, Any],
        response_time_ms: int,
    ) -> EvaluationResult:
        """
        Evaluates a submitted answer against the question version specification.

        Args:
            question: QuestionVersionModel, ItemParameterSnapshot, or equivalent object
                      carrying correct_answer, options, and question_type.
            submitted_answer: Student payload, expected as {'selected_option': 'A', ...}
            response_time_ms: Response time in milliseconds (must be >= 0).

        Returns:
            EvaluationResult with correctness, score, and operational metadata.

        Raises:
            InvalidAnswerPayloadError: If the payload is not a dict or lacks selected_option.
            InvalidOptionError: If selected_option is not in the question's defined options.
            UnsupportedQuestionTypeError: If question format is not supported (e.g. not MCQ).
            InvalidQuestionVersionError: If the question specification lacks correct_answer or options.
            ValueError: If response_time_ms is negative or unrealistic.
        """
        # 1. Validate response time
        valid_response_time = validate_response_time(response_time_ms)

        # 2. Extract and validate question version details
        version_id, q_type, correct_answer, valid_keys = self._extract_question_details(question)

        # Ensure question type is supported
        normalized_q_type = str(q_type).upper()
        if "MULTIPLE_CHOICE" not in normalized_q_type:
            raise UnsupportedQuestionTypeError(
                f"Evaluator currently only supports MULTIPLE_CHOICE questions, got '{q_type}'"
            )

        # 3. Validate answer payload structure
        if not isinstance(submitted_answer, dict):
            raise InvalidAnswerPayloadError(
                f"Answer payload must be a JSON dictionary, got {type(submitted_answer).__name__}"
            )

        raw_selected = submitted_answer.get("selected_option")
        if raw_selected is None or not str(raw_selected).strip():
            raise InvalidAnswerPayloadError(
                "Answer payload must contain a non-empty 'selected_option' field."
            )

        selected_key = str(raw_selected).strip().upper()

        # 4. Validate selected option belongs to question options
        if valid_keys and selected_key not in valid_keys:
            raise InvalidOptionError(
                f"Selected option '{selected_key}' is not a valid choice for this question. "
                f"Valid options: {sorted(list(valid_keys))}"
            )

        # 5. Evaluate correctness (Pure deterministic comparison)
        norm_correct = str(correct_answer).strip().upper()
        is_correct = (selected_key == norm_correct)
        score = 1.0 if is_correct else 0.0

        # 6. Rapid-guessing anomaly detection (per clinical psychometrics spec)
        is_rapid_guess = (
            self.rapid_guess_threshold_ms > 0
            and valid_response_time < self.rapid_guess_threshold_ms
        )
        eval_status = "RAPID_GUESS" if is_rapid_guess else "VALID"

        # 7. Return standard evaluation result (never includes correct_answer)
        return EvaluationResult(
            is_correct=is_correct,
            score=score,
            response_time_ms=valid_response_time,
            raw_answer=submitted_answer,
            evaluator_version=self.version,
            question_version_id=version_id,
            evaluation_status=eval_status,
            metadata={
                "selected_option": selected_key,
                "question_type": QuestionType.MULTIPLE_CHOICE.value,
                "is_rapid_guess": is_rapid_guess,
            }
        )

    def _extract_question_details(self, question: Any) -> tuple[Optional[int], str, str, Set[str]]:
        """Extracts version ID, question type, correct answer, and valid option keys."""
        if question is None:
            raise InvalidQuestionVersionError("Question version cannot be None.")

        # Support dictionary access or attribute access
        if isinstance(question, dict):
            version_id = question.get("id") or question.get("version_id") or question.get("version")
            q_type = question.get("question_type", QuestionType.MULTIPLE_CHOICE.value)
            correct_answer = question.get("correct_answer")
            options = question.get("options") or []
        else:
            version_id = getattr(question, "id", None) or getattr(question, "version_id", None) or getattr(question, "version", None)
            q_type = getattr(question, "question_type", QuestionType.MULTIPLE_CHOICE.value)
            correct_answer = getattr(question, "correct_answer", None)
            options = getattr(question, "options", None) or []

        if not correct_answer:
            raise InvalidQuestionVersionError(
                "Question version must define a non-empty 'correct_answer'."
            )

        # Extract option keys
        valid_keys: Set[str] = set()
        for opt in options:
            if isinstance(opt, dict):
                k = opt.get("key")
            else:
                k = getattr(opt, "key", None)
            if k:
                valid_keys.add(str(k).strip().upper())

        if not valid_keys:
            raise InvalidQuestionVersionError(
                "Question version must define at least one valid choice in 'options'."
            )

        return version_id, str(q_type), str(correct_answer), valid_keys
