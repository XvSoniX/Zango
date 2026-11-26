class EngineError(Exception):
    """Base class for Assessment Engine errors."""
    pass

class InvalidAnswerPayloadError(EngineError, ValueError):
    """Raised when the submitted answer payload is malformed or missing required fields."""
    pass

class InvalidOptionError(EngineError, ValueError):
    """Raised when the selected option key does not exist among the question options."""
    pass

class UnsupportedQuestionTypeError(EngineError, ValueError):
    """Raised when evaluating a question type not supported by the evaluator."""
    pass

class InvalidQuestionVersionError(EngineError, ValueError):
    """Raised when the question version specification is incomplete or invalid."""
    pass
