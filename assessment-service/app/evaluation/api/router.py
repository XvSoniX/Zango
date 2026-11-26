"""
FastAPI Router for Assessment Engine Evaluation Framework (TASK-034 & TASK-035).
Internal engineering endpoints protected by admin authorization.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.database import get_db_session
from app.infrastructure.security.jwt import require_role, AuthenticatedUser
from app.infrastructure.persistence.repositories.question_repo import QuestionRepository
from app.simulation.persistence.repository import SimulationRepository
from app.evaluation.persistence.repository import EvaluationRepository
from app.evaluation.services.question_selection_evaluator import QuestionSelectionEvaluator
from app.evaluation.services.ability_estimation_evaluator import AbilityEstimationEvaluator
from app.evaluation.domain.config import EvaluationType
from app.evaluation.api.schemas import (
    StartEvaluationRequest,
    EvaluationRunResponse,
    QuestionSelectionEvaluationResponse,
    AbilityEstimationEvaluationResponse,
)

router = APIRouter(prefix="/internal/evaluations", tags=["Evaluation Framework (Engineering Only)"])


@router.post(
    "/question-selection",
    status_code=status.HTTP_201_CREATED,
    response_model=QuestionSelectionEvaluationResponse,
    summary="Evaluate Question Selection (TASK-034)",
    description="Analyzes dimension coverage, difficulty adaptation, exposure, and repetition across simulation runs."
)
async def evaluate_question_selection(
    request: StartEvaluationRequest,
    user: AuthenticatedUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db_session),
) -> QuestionSelectionEvaluationResponse:
    eval_repo = EvaluationRepository(db)
    sim_repo = SimulationRepository(db)
    question_repo = QuestionRepository(db)

    evaluator = QuestionSelectionEvaluator(
        eval_repo=eval_repo,
        sim_repo=sim_repo,
        question_repo=question_repo,
    )

    try:
        results = await evaluator.evaluate_simulation_runs(
            simulation_run_ids=request.simulation_run_ids,
            configuration=request.configuration,
        )
        return QuestionSelectionEvaluationResponse.model_validate(results)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Question selection evaluation failed: {str(e)}"
        )


@router.post(
    "/ability-estimation",
    status_code=status.HTTP_201_CREATED,
    response_model=AbilityEstimationEvaluationResponse,
    summary="Evaluate Ability Estimation Quality (TASK-035)",
    description="Analyzes MAE, RMSE, Bias, dimensional errors, and uncertainty calibration across simulation runs."
)
async def evaluate_ability_estimation(
    request: StartEvaluationRequest,
    user: AuthenticatedUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db_session),
) -> AbilityEstimationEvaluationResponse:
    eval_repo = EvaluationRepository(db)
    sim_repo = SimulationRepository(db)

    evaluator = AbilityEstimationEvaluator(
        eval_repo=eval_repo,
        sim_repo=sim_repo,
    )

    try:
        results = await evaluator.evaluate_simulation_runs(
            simulation_run_ids=request.simulation_run_ids,
            configuration=request.configuration,
        )
        return AbilityEstimationEvaluationResponse.model_validate(results)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ability estimation evaluation failed: {str(e)}"
        )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=List[EvaluationRunResponse],
    summary="List Evaluation Runs",
    description="Lists previous evaluation runs with status and metadata."
)
async def list_evaluation_runs(
    limit: int = Query(default=50, ge=1, le=100),
    user: AuthenticatedUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db_session),
) -> List[EvaluationRunResponse]:
    eval_repo = EvaluationRepository(db)
    runs = await eval_repo.list_evaluation_runs(limit=limit)
    return [
        EvaluationRunResponse(
            id=r.id,
            evaluation_type=r.evaluation_type,
            status=r.status,
            source_simulation_run_ids=r.source_simulation_run_ids,
            algorithm_version=r.algorithm_version,
            question_bank_version=r.question_bank_version,
            started_at=r.started_at,
            completed_at=r.completed_at,
            created_at=r.created_at,
            error_message=r.error_message,
        )
        for r in runs
    ]


@router.get(
    "/{evaluation_id}",
    status_code=status.HTTP_200_OK,
    response_model=EvaluationRunResponse,
    summary="Get Evaluation Run Status",
    description="Retrieves metadata and execution status for a specific evaluation run."
)
async def get_evaluation_run(
    evaluation_id: str,
    user: AuthenticatedUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db_session),
) -> EvaluationRunResponse:
    eval_repo = EvaluationRepository(db)
    run = await eval_repo.get_evaluation_run(evaluation_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run '{evaluation_id}' not found"
        )
    return EvaluationRunResponse(
        id=run.id,
        evaluation_type=run.evaluation_type,
        status=run.status,
        source_simulation_run_ids=run.source_simulation_run_ids,
        algorithm_version=run.algorithm_version,
        question_bank_version=run.question_bank_version,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        error_message=run.error_message,
    )


@router.get(
    "/{evaluation_id}/results",
    status_code=status.HTTP_200_OK,
    summary="Get Evaluation Run Results",
    description="Retrieves persisted evaluation results and structured metrics for an evaluation run."
)
async def get_evaluation_results(
    evaluation_id: str,
    user: AuthenticatedUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    eval_repo = EvaluationRepository(db)
    run = await eval_repo.get_evaluation_run(evaluation_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run '{evaluation_id}' not found"
        )

    if run.evaluation_type == EvaluationType.QUESTION_SELECTION.value:
        res = await eval_repo.get_question_selection_result_by_run_id(evaluation_id)
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question selection results not found for run '{evaluation_id}'"
            )
        return {
            "evaluation_run_id": run.id,
            "evaluation_type": run.evaluation_type,
            "status": run.status,
            "summary_metrics": res.summary_metrics,
            "dimension_coverage": res.dimension_coverage,
            "difficulty_distribution": res.difficulty_distribution,
            "exposure_and_repetition": res.exposure_metrics,
            "assessment_length": res.assessment_length,
            "selection_sequence": res.sequence_analysis,
            "archetype_breakdowns": res.archetype_breakdown,
            "anomalies": res.anomalies,
        }

    elif run.evaluation_type == EvaluationType.ABILITY_ESTIMATION.value:
        res = await eval_repo.get_ability_estimation_result_by_run_id(evaluation_id)
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ability estimation results not found for run '{evaluation_id}'"
            )
        return {
            "evaluation_run_id": run.id,
            "evaluation_type": run.evaluation_type,
            "status": run.status,
            "summary_metrics": res.summary_metrics,
            "dimension_metrics": res.dimension_metrics,
            "uncertainty_analysis": res.uncertainty_analysis,
            "length_vs_quality": res.length_vs_quality,
            "archetype_breakdowns": res.archetype_breakdown,
            "anomalies": res.anomalies,
            "limitations": res.limitations,
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported evaluation type '{run.evaluation_type}'"
        )
