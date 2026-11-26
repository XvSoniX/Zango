from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator
from app.domain.enums import QuestionType, QuestionVersionStatus, CalibrationStatus
from app.domain.dimensions import DimensionsVector
from app.domain.question import (
    validate_options,
    validate_correct_answer,
    validate_psychometrics,
    validate_age_range,
    validate_estimated_time,
    validate_exposure_limit,
)

class OptionSchema(BaseModel):
    key: str
    text: str
    order: int

class QuestionVersionBaseSchema(BaseModel):
    content: str
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE
    options: List[OptionSchema]
    min_age: int = 10
    max_age: int = 18
    estimated_time: int = 60
    dimensions: Dict[str, float]

class QuestionVersionPublicSchema(QuestionVersionBaseSchema):
    """
    Public representation of question version served to students.
    SECURITY NOTICE: Excludes correct_answer and internal psychometrics.
    """
    id: int
    question_id: int
    version: int
    status: QuestionVersionStatus

class QuestionVersionAdminSchema(QuestionVersionPublicSchema):
    """Admin representation containing evaluation and calibration parameters."""
    correct_answer: str
    difficulty: float
    discrimination: float
    guessing: float
    calibration_status: CalibrationStatus
    exposure_limit: Optional[int] = None

class CreateQuestionVersionInput(BaseModel):
    content: str
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE
    options: List[Dict[str, Any]]
    correct_answer: str
    difficulty: float = 0.0
    discrimination: float = 1.0
    guessing: float = 0.25
    min_age: int = 10
    max_age: int = 18
    estimated_time: int = 60
    dimensions: Dict[str, float]
    status: QuestionVersionStatus = QuestionVersionStatus.PUBLISHED
    calibration_status: CalibrationStatus = CalibrationStatus.UNCALIBRATED
    exposure_limit: Optional[int] = None

    @model_validator(mode="after")
    def validate_all_fields(self) -> "CreateQuestionVersionInput":
        parsed_opts = validate_options(self.options)
        self.correct_answer = validate_correct_answer(self.correct_answer, parsed_opts)
        psych = validate_psychometrics(self.difficulty, self.discrimination, self.guessing)
        self.difficulty = psych["difficulty"]
        self.discrimination = psych["discrimination"]
        self.guessing = psych["guessing"]
        age = validate_age_range(self.min_age, self.max_age)
        self.min_age = age["min_age"]
        self.max_age = age["max_age"]
        self.estimated_time = validate_estimated_time(self.estimated_time)
        self.exposure_limit = validate_exposure_limit(self.exposure_limit)
        dim_vec = DimensionsVector(weights=self.dimensions)
        self.dimensions = dim_vec.to_dict()
        return self

class CreateQuestionInput(BaseModel):
    code: str
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE
    is_active: bool = True
    initial_version: CreateQuestionVersionInput
