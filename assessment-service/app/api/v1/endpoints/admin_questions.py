from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.infrastructure.security.jwt import require_role, AuthenticatedUser

router = APIRouter(prefix="/admin/questions", tags=["Question Administration (Provisional)"])

class CreateQuestionRequest(BaseModel):
    code: str
    content: str
    options: List[Dict[str, Any]]
    correct_answer: str
    dimensions: Dict[str, float]
    difficulty: float
    discrimination: float
    guessing: float = 0.25
    min_age: int = 10
    max_age: int = 18

@router.post("", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_question(
    request: CreateQuestionRequest,
    # user: AuthenticatedUser = Depends(require_role("ADMIN"))
):
    """Provisional endpoint: creates a new question in the bank (Day 2 implementation)."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Question administration will be implemented in Day 2."
    )

@router.post("/{question_id}/activate", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def activate_question(
    question_id: int,
    # user: AuthenticatedUser = Depends(require_role("ADMIN"))
):
    """Provisional endpoint: toggles active status of a question (Day 2 implementation)."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Question activation will be implemented in Day 2."
    )
