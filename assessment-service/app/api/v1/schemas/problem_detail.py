from typing import List, Optional
from pydantic import BaseModel, Field

class FieldValidationError(BaseModel):
    field: str
    message: str

class ProblemDetail(BaseModel):
    type: str = Field(default="about:blank", description="URI reference identifying the problem type")
    title: str = Field(description="Short human-readable summary of problem")
    status: int = Field(description="HTTP status code")
    detail: str = Field(description="Human-readable explanation specific to this occurrence")
    instance: str = Field(description="URI reference that identifies specific occurrence")
    isSuccess: bool = Field(default=False)
    errorCode: str = Field(description="Application error code matching Zango taxonomy")
    correlationId: Optional[str] = Field(default=None, description="Correlation tracking ID")
    errors: Optional[List[FieldValidationError]] = Field(default=None, description="Detailed field-level validation errors")
