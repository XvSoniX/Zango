from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.database import get_db_session
from app.infrastructure.security.jwt import get_current_user, AuthenticatedUser
from app.application.workflow import AssessmentWorkflowOrchestrator
from app.application.dto import (
    StartAssessmentCommand,
    StartAssessmentResultDTO,
    NextQuestionQuery,
    NextQuestionResultDTO,
    SubmitAnswerCommand,
    SubmitAnswerResultDTO,
    SessionSummaryDTO,
    AbilityHistoryResponseDTO,
    AssessmentReportDTO,
)
from app.application.exceptions import (
    ApplicationError,
    SessionNotFoundError,
    SessionAccessForbiddenError,
    SessionNotActiveError,
    SessionExpiredError,
    SessionNotCompletedError,
    ProfileNotFoundError,
    ProfileInactiveError,
    AgeIncompatibleError,
    QuestionVersionNotFoundError,
    QuestionNotOfferedError,
    DuplicateAnswerError,
    IdempotencyConflictError,
    NoEligibleQuestionsError,
    ReportNotFoundError,
    SnapshotNotFoundError,
)
from app.engine.exceptions import (
    EngineError,
    InvalidAnswerPayloadError,
    InvalidOptionError,
    UnsupportedQuestionTypeError,
)

router = APIRouter(prefix="/assessments", tags=["Adaptive Assessments"])


# ==========================================
# Request Schemas
# ==========================================

class StartAssessmentApiRequest(BaseModel):
    """Payload to initiate a new adaptive assessment session."""
    age: int = Field(..., ge=1, le=120, description="Student age in completed years", json_schema_extra={"example": 15})
    profile_code: str = Field(
        default="TECHNICAL_TALENT_V1",
        description="Target profile code",
        json_schema_extra={"example": "TECHNICAL_TALENT_V1"}
    )
    language: Optional[str] = Field(default="fa", description="Language code")
    student_id: Optional[str] = Field(default=None, description="Optional student identifier override")


class SubmitAnswerApiRequest(BaseModel):
    """Payload to submit student's selected answer."""
    question_version_id: Optional[int] = Field(default=None, description="Question version primary key ID")
    question_id: Optional[int] = Field(default=None, description="Question identifier")
    question_version: Optional[int] = Field(default=None, description="Alternative version number key")
    answer: Dict[str, Any] = Field(
        ...,
        description="Student response payload",
        json_schema_extra={"example": {"selected_option": "B"}}
    )
    response_time_ms: int = Field(
        ...,
        ge=0,
        description="Time spent on the item in milliseconds",
        json_schema_extra={"example": 12500}
    )
    idempotency_key: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Client idempotency key for safe retries",
        json_schema_extra={"example": "idemp-8f92b-001"}
    )


# ==========================================
# Exception Translator
# ==========================================

def translate_service_exception(e: Exception) -> HTTPException:
    """Translates domain/application exceptions into standard HTTP exceptions."""
    if isinstance(e, (SessionNotFoundError, ProfileNotFoundError, QuestionVersionNotFoundError, ReportNotFoundError, SnapshotNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    elif isinstance(e, SessionAccessForbiddenError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    elif isinstance(e, (
        ProfileInactiveError,
        AgeIncompatibleError,
        InvalidAnswerPayloadError,
        InvalidOptionError,
        UnsupportedQuestionTypeError
    )):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    elif isinstance(e, (
        SessionNotActiveError,
        SessionExpiredError,
        SessionNotCompletedError,
        QuestionNotOfferedError,
        DuplicateAnswerError,
        IdempotencyConflictError,
        NoEligibleQuestionsError,
    )):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    elif isinstance(e, ApplicationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    elif isinstance(e, HTTPException):
        return e
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# ==========================================
# API Endpoints (TASK-029, TASK-031, TASK-032)
# ==========================================

@router.post(
    "/start",
    status_code=status.HTTP_201_CREATED,
    response_model=StartAssessmentResultDTO,
    summary="Start Assessment Session",
    description="Initiates an adaptive testing session for the authenticated student."
)
async def start_assessment(
    request: StartAssessmentApiRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> StartAssessmentResultDTO:
    orchestrator = AssessmentWorkflowOrchestrator(db)
    student_id = user.user_id

    command = StartAssessmentCommand(
        student_id=student_id,
        student_age=request.age,
        profile_code=request.profile_code,
    )
    try:
        return await orchestrator.start_assessment(command)
    except Exception as e:
        raise translate_service_exception(e)


@router.get(
    "/ability-history",
    status_code=status.HTTP_200_OK,
    response_model=AbilityHistoryResponseDTO,
    summary="Get Ability History",
    description="Retrieves the chronological history of immutable ability snapshots for the authenticated student."
)
async def get_ability_history(
    session_id: Optional[str] = Query(default=None, description="Optional session filter"),
    limit: int = Query(default=50, ge=1, le=100, description="Page limit"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AbilityHistoryResponseDTO:
    orchestrator = AssessmentWorkflowOrchestrator(db)
    try:
        return await orchestrator.get_ability_history(
            student_id=user.user_id,
            session_id=session_id,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise translate_service_exception(e)


@router.get(
    "/{assessment_id}",
    status_code=status.HTTP_200_OK,
    response_model=SessionSummaryDTO,
    summary="Get Assessment Session Status",
    description="Retrieves the current status, progress, and cognitive estimation summary."
)
async def get_assessment_status(
    assessment_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SessionSummaryDTO:
    orchestrator = AssessmentWorkflowOrchestrator(db)
    try:
        return await orchestrator.get_session_summary(
            session_id=assessment_id,
            student_id=user.user_id
        )
    except Exception as e:
        raise translate_service_exception(e)


@router.get(
    "/{assessment_id}/next-question",
    status_code=status.HTTP_200_OK,
    response_model=NextQuestionResultDTO,
    summary="Get Next Adaptive Question",
    description="Retrieves the next adaptive question or signals test completion."
)
async def get_next_question(
    assessment_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> NextQuestionResultDTO:
    orchestrator = AssessmentWorkflowOrchestrator(db)
    query = NextQuestionQuery(
        session_id=assessment_id,
        student_id=user.user_id,
    )
    try:
        return await orchestrator.get_next_question(query)
    except Exception as e:
        raise translate_service_exception(e)


@router.post(
    "/{assessment_id}/answers",
    status_code=status.HTTP_200_OK,
    response_model=SubmitAnswerResultDTO,
    summary="Submit Question Answer",
    description="Evaluates student response, updates multidimensional ability, and persists answer."
)
async def submit_answer(
    assessment_id: str,
    request: SubmitAnswerApiRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SubmitAnswerResultDTO:
    orchestrator = AssessmentWorkflowOrchestrator(db)

    q_ver_id = request.question_version_id or request.question_version
    if not q_ver_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either 'question_version_id' or 'question_version' must be provided."
        )

    command = SubmitAnswerCommand(
        session_id=assessment_id,
        student_id=user.user_id,
        question_version_id=q_ver_id,
        answer=request.answer,
        response_time_ms=request.response_time_ms,
        idempotency_key=request.idempotency_key,
    )
    try:
        return await orchestrator.submit_answer(command)
    except Exception as e:
        from app.infrastructure.logging.logger import logger
        logger.error(f"Error in submit_answer endpoint: {e}", exc_info=True)
        raise translate_service_exception(e)


@router.get(
    "/{assessment_id}/report",
    status_code=status.HTTP_200_OK,
    response_model=AssessmentReportDTO,
    summary="Get Assessment Report (TASK-031)",
    description="Generates or retrieves final diagnostic report anchored to the final snapshot."
)
async def get_assessment_report(
    assessment_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AssessmentReportDTO:
    orchestrator = AssessmentWorkflowOrchestrator(db)
    try:
        return await orchestrator.get_assessment_report(
            session_id=assessment_id,
            student_id=user.user_id
        )
    except Exception as e:
        from app.infrastructure.logging.logger import logger
        logger.error(f"Error in get_assessment_report: {e}", exc_info=True)
        raise translate_service_exception(e)
