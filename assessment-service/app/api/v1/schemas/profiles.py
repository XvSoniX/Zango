from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from app.domain.profile import validate_profile_code, validate_profile_dimensions
from app.domain.question import validate_age_range

class ProfileBaseSchema(BaseModel):
    code: str
    title: str
    description: Optional[str] = None
    version: int = 1
    dimensions: List[str]
    min_age: int = 10
    max_age: int = 18
    is_active: bool = True

    @model_validator(mode="after")
    def validate_profile_fields(self) -> "ProfileBaseSchema":
        self.code = validate_profile_code(self.code)
        self.dimensions = validate_profile_dimensions(self.dimensions)
        age = validate_age_range(self.min_age, self.max_age)
        self.min_age = age["min_age"]
        self.max_age = age["max_age"]
        return self

class ProfileCreateInput(ProfileBaseSchema):
    pass

class ProfilePublicSchema(ProfileBaseSchema):
    id: int
    created_at: datetime
    updated_at: datetime
