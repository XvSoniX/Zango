"""
Application-level domain exceptions.
Used by Application Services to signal business rule violations and operational constraints.
"""

class ApplicationError(Exception):
    """Base class for all application service exceptions."""
    def __init__(self, message: str, code: str = "APPLICATION_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class SessionNotFoundError(ApplicationError):
    """Raised when the requested assessment session cannot be found."""
    def __init__(self, session_id: str):
        super().__init__(f"Assessment session '{session_id}' not found.", code="SESSION_NOT_FOUND")
        self.session_id = session_id


class SessionAccessForbiddenError(ApplicationError):
    """Raised when an authenticated user attempts to access a session belonging to another user."""
    def __init__(self, session_id: str, student_id: str):
        super().__init__(
            f"User '{student_id}' is not authorized to access session '{session_id}'.",
            code="SESSION_ACCESS_FORBIDDEN"
        )
        self.session_id = session_id
        self.student_id = student_id


class SessionNotActiveError(ApplicationError):
    """Raised when an operation requires an IN_PROGRESS session but current status differs."""
    def __init__(self, session_id: str, status: str):
        super().__init__(
            f"Session '{session_id}' is not in progress (current status: '{status}').",
            code="SESSION_NOT_ACTIVE"
        )
        self.session_id = session_id
        self.status = status


class SessionExpiredError(ApplicationError):
    """Raised when an assessment session has exceeded its maximum allocated duration."""
    def __init__(self, session_id: str, elapsed_seconds: float, max_seconds: float):
        super().__init__(
            f"Session '{session_id}' has expired ({elapsed_seconds:.0f}s elapsed, limit {max_seconds:.0f}s).",
            code="SESSION_EXPIRED"
        )
        self.session_id = session_id
        self.elapsed_seconds = elapsed_seconds
        self.max_seconds = max_seconds


class ProfileNotFoundError(ApplicationError):
    """Raised when the requested assessment profile does not exist."""
    def __init__(self, identifier: str):
        super().__init__(f"Assessment profile '{identifier}' not found.", code="PROFILE_NOT_FOUND")
        self.identifier = identifier


class ProfileInactiveError(ApplicationError):
    """Raised when an assessment profile exists but is marked inactive."""
    def __init__(self, identifier: str):
        super().__init__(f"Assessment profile '{identifier}' is not active.", code="PROFILE_INACTIVE")
        self.identifier = identifier


class AgeIncompatibleError(ApplicationError):
    """Raised when student age falls outside the profile's allowed age bracket."""
    def __init__(self, age: int, min_age: int, max_age: int, profile_code: str):
        super().__init__(
            f"Student age {age} is outside the allowed age range [{min_age}, {max_age}] for profile '{profile_code}'.",
            code="AGE_INCOMPATIBLE"
        )
        self.age = age
        self.min_age = min_age
        self.max_age = max_age
        self.profile_code = profile_code


class QuestionVersionNotFoundError(ApplicationError):
    """Raised when the specified QuestionVersion cannot be found."""
    def __init__(self, version_id: int):
        super().__init__(f"Question version {version_id} not found.", code="QUESTION_VERSION_NOT_FOUND")
        self.version_id = version_id


class QuestionNotOfferedError(ApplicationError):
    """Raised when an answer is submitted for a question that was not offered/presented to this session."""
    def __init__(self, session_id: str, question_version_id: int):
        super().__init__(
            f"Question version {question_version_id} was not offered to session '{session_id}'.",
            code="QUESTION_NOT_OFFERED"
        )
        self.session_id = session_id
        self.question_version_id = question_version_id


class DuplicateAnswerError(ApplicationError):
    """Raised when attempting to submit another answer for a question already answered in this session."""
    def __init__(self, session_id: str, question_id: int):
        super().__init__(
            f"Question {question_id} has already been answered in session '{session_id}'.",
            code="DUPLICATE_ANSWER"
        )
        self.session_id = session_id
        self.question_id = question_id


class IdempotencyConflictError(ApplicationError):
    """Raised when the same idempotency key is submitted with a different payload or question."""
    def __init__(self, session_id: str, idempotency_key: str):
        super().__init__(
            f"Idempotency key '{idempotency_key}' in session '{session_id}' was already used with different parameters.",
            code="IDEMPOTENCY_CONFLICT"
        )
        self.session_id = session_id
        self.idempotency_key = idempotency_key


class NoEligibleQuestionsError(ApplicationError):
    """Raised when the question selector cannot find any eligible question in the bank."""
    def __init__(self, session_id: str, reason: str = "QUESTION_BANK_EXHAUSTED"):
        super().__init__(
            f"No eligible questions available for session '{session_id}' (reason: {reason}).",
            code="NO_ELIGIBLE_QUESTIONS"
        )
        self.session_id = session_id
        self.reason = reason


class SessionNotCompletedError(ApplicationError):
    """Raised when an operation requires a COMPLETED session but current status differs."""
    def __init__(self, session_id: str, status: str):
        super().__init__(
            f"Assessment session '{session_id}' is not completed (current status: '{status}'). Final report cannot be generated.",
            code="SESSION_NOT_COMPLETED"
        )
        self.session_id = session_id
        self.status = status


class ReportNotFoundError(ApplicationError):
    """Raised when an assessment report cannot be found."""
    def __init__(self, identifier: str):
        super().__init__(f"Assessment report '{identifier}' not found.", code="REPORT_NOT_FOUND")
        self.identifier = identifier


class SnapshotNotFoundError(ApplicationError):
    """Raised when a required ability snapshot cannot be found."""
    def __init__(self, session_id: str):
        super().__init__(f"No ability snapshot found for session '{session_id}'.", code="SNAPSHOT_NOT_FOUND")
        self.session_id = session_id

