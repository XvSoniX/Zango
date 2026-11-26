from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.database import get_db_session
from app.infrastructure.security.jwt import require_role, AuthenticatedUser
from app.simulation.orchestration.orchestrator import SimulationOrchestrator
from app.simulation.persistence.repository import SimulationRepository
from app.simulation.api.schemas import (
    StartSimulationRequest,
    SimulationRunSummaryResponse,
    SimulationParticipantResultResponse,
)

router = APIRouter(prefix="/internal/simulations", tags=["Simulation Lab (Engineering Only)"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SimulationRunSummaryResponse,
    summary="Execute Simulation Run",
    description="Executes a batch simulation of synthetic users against the production assessment engine. Restricted to administrators."
)
async def start_simulation_run(
    request: StartSimulationRequest,
    user: AuthenticatedUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db_session),
) -> SimulationRunSummaryResponse:
    orchestrator = SimulationOrchestrator(db)
    try:
        run_record = await orchestrator.execute_simulation_run(
            name=request.name,
            profile_code=request.profile_code,
            participant_count=request.participant_count,
            archetypes=request.archetypes,
            min_age=request.min_age,
            max_age=request.max_age,
            random_seed=request.random_seed,
            custom_ability=request.custom_ability,
        )
        return SimulationRunSummaryResponse.model_validate(run_record)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation run failed: {str(e)}"
        )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=List[SimulationRunSummaryResponse],
    summary="List Simulation Runs",
    description="Lists past and current simulation runs. Restricted to administrators."
)
async def list_simulation_runs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db_session),
) -> List[SimulationRunSummaryResponse]:
    repo = SimulationRepository(db)
    runs = await repo.list_runs(limit=limit, offset=offset)
    return [SimulationRunSummaryResponse.model_validate(r) for r in runs]


@router.get(
    "/{run_id}",
    status_code=status.HTTP_200_OK,
    response_model=SimulationRunSummaryResponse,
    summary="Get Simulation Run Status",
    description="Retrieves status and summary metrics for a specific simulation run."
)
async def get_simulation_run(
    run_id: str,
    user: AuthenticatedUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db_session),
) -> SimulationRunSummaryResponse:
    repo = SimulationRepository(db)
    run = await repo.get_run_by_id(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Simulation run '{run_id}' not found.")
    return SimulationRunSummaryResponse.model_validate(run)


@router.get(
    "/{run_id}/results",
    status_code=status.HTTP_200_OK,
    response_model=List[SimulationParticipantResultResponse],
    summary="Get Simulation Participant Results",
    description="Retrieves full participant results (ground-truth vs estimated abilities) for a simulation run."
)
async def get_simulation_results(
    run_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db_session),
) -> List[SimulationParticipantResultResponse]:
    repo = SimulationRepository(db)
    results = await repo.get_results_by_run_id(run_id, limit=limit, offset=offset)
    return [SimulationParticipantResultResponse.model_validate(r) for r in results]


@router.get(
    "/{run_id}/participants/{participant_id}",
    status_code=status.HTTP_200_OK,
    response_model=SimulationParticipantResultResponse,
    summary="Get Single Participant Simulation Trace",
    description="Retrieves question-by-question trace and evaluation records for a single synthetic participant."
)
async def get_participant_detail(
    run_id: str,
    participant_id: str,
    user: AuthenticatedUser = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db_session),
) -> SimulationParticipantResultResponse:
    repo = SimulationRepository(db)
    result = await repo.get_result_by_participant(run_id, participant_id)
    if not result:
        # Check by primary key ID if synthetic_user_id didn't match
        result = await repo.get_result_by_id(participant_id)

    if not result or result.run_id != run_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant '{participant_id}' in run '{run_id}' not found."
        )
    return SimulationParticipantResultResponse.model_validate(result)


from pydantic import BaseModel, Field
from typing import Dict, Any
import random
from app.config import settings
from app.domain.dimensions import DIMENSION_REGISTRY
from app.engine.protocols import AssessmentContext, ItemParameterSnapshot, EvaluationResult
from app.engine.estimator import create_initial_ability_state, BaselineMultidimensionalEstimator
from app.engine.selector import CompositeHeuristicSelector
from app.engine.stopping import StandardStoppingStrategy
from app.infrastructure.persistence.repositories.question_repo import QuestionRepository
from app.infrastructure.persistence.repositories.profile_repo import AssessmentProfileRepository


class SelectionTraceRequest(BaseModel):
    """Input for stateless step-by-step question selection logic audit."""
    seed: int = Field(default=42, description="Deterministic seed for virtual examinee responses")
    student_age: int = Field(default=12, ge=8, le=18, description="Virtual examinee age (8-18)")
    max_questions: int = Field(default=10, ge=1, le=20, description="Max steps to simulate")
    true_ability: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional true ability vector; if omitted, generated deterministically from seed"
    )


class SelectionTraceStep(BaseModel):
    step: int
    selected_question_id: int
    question_version: int
    difficulty: float
    simulated_correct: bool
    selection_reason: str
    chosen_details: Dict[str, Any]
    theta_after: Dict[str, float]
    uncertainty_after: Dict[str, float]
    stopping_should_stop: bool
    stopping_reason: Optional[str] = None


class SelectionTraceResponse(BaseModel):
    seed: int
    student_age: int
    true_ability: Dict[str, float]
    steps: List[SelectionTraceStep]
    final_theta: Dict[str, float]
    final_uncertainty: Dict[str, float]


@router.post(
    "/selection-trace",
    status_code=status.HTTP_200_OK,
    response_model=SelectionTraceResponse,
    summary="Test Question Selection Logic (Seeded Audit Trace)",
    description=(
        "Simulates a seeded virtual examinee step-by-step to inspect exact question selection "
        "reasons, Fisher Information scores, and ability updates. "
        "TODO Phase 2: Restrict access to ADMIN and CLINICIAN roles once those services are integrated."
    ),
)
async def test_selection_trace(
    request: SelectionTraceRequest,
    db: AsyncSession = Depends(get_db_session),
) -> SelectionTraceResponse:
    rng = random.Random(request.seed)
    dims = list(DIMENSION_REGISTRY.keys())
    true_theta = request.true_ability or {
        d: round(rng.uniform(-1.8, 1.8), 2) for d in dims
    }

    q_repo = QuestionRepository(db)
    p_repo = AssessmentProfileRepository(db)
    profile = await p_repo.get_by_code("TECHNICAL_TALENT_V1", version=1)
    if profile:
        active_qs = await q_repo.get_active_questions_for_profile(profile.id)
    else:
        active_qs = []

    snapshots: List[ItemParameterSnapshot] = []
    for q in active_qs:
        ver = q.get_active_version() or q.get_latest_version()
        if not ver:
            continue
        snapshots.append(
            ItemParameterSnapshot(
                question_id=q.id,
                version=ver.version,
                dimensions=ver.dimensions or {},
                difficulty=float(ver.difficulty),
                discrimination=float(getattr(ver, "discrimination", 1.1) or 1.1),
                guessing=float(getattr(ver, "guessing", 0.25) if getattr(ver, "guessing", None) is not None else 0.25),
                min_age=getattr(ver, "min_age", 8),
                max_age=getattr(ver, "max_age", 18),
                exposure_limit=getattr(ver, "exposure_limit", 100) or 100,
                exposure_count=getattr(ver, "exposure_count", 0) or 0,
                is_active=getattr(q, "is_active", True),
                correct_answer=ver.correct_answer,
                options=ver.options,
                calibration_status=ver.calibration_status,
            )
        )

    selector = CompositeHeuristicSelector()
    estimator = BaselineMultidimensionalEstimator()
    stopper = StandardStoppingStrategy()
    state = create_initial_ability_state(dims)
    answered_ids: List[int] = []
    steps: List[SelectionTraceStep] = []

    for step_idx in range(1, request.max_questions + 1):
        ctx = AssessmentContext(
            session_id=f"trace-{request.seed}",
            student_id=f"virtual-{request.seed}",
            student_age=request.student_age,
            profile_code="TECHNICAL_TALENT_V1",
            target_dimensions=dims,
            current_ability=state,
            answered_question_ids=answered_ids,
            response_history=[],
            elapsed_time_seconds=float(step_idx * 25),
            max_duration_seconds=float(settings.SESSION_TIMEOUT_SECONDS),
            min_questions=min(5, request.max_questions),
            max_questions=request.max_questions,
            random_seed=request.seed,
        )
        sel = selector.select(snapshots, ctx)
        if not sel.selected_question_id:
            break

        chosen = next(s for s in snapshots if s.question_id == sel.selected_question_id)
        answered_ids.append(chosen.question_id)

        # Simulate 3PL response probability from true_theta
        from app.engine.uncertainty import probability_3pl
        w_sum = sum(chosen.dimensions.values()) or 1.0
        eff_theta = sum(chosen.dimensions.get(d, 0.0) * true_theta.get(d, 0.0) for d in dims) / w_sum
        p_corr = probability_3pl(eff_theta, chosen.difficulty, chosen.discrimination, chosen.guessing)
        is_corr = rng.random() < p_corr

        eval_res = EvaluationResult(
            is_correct=is_corr,
            score=1.0 if is_corr else 0.0,
            response_time_ms=rng.randint(3500, 14000),
            raw_answer={"selected_option": "A"},
            evaluator_version="trace-sim",
            question_version_id=chosen.version,
            evaluation_status="VALID",
        )
        state = estimator.estimate(state, eval_res, chosen)
        stop_dec = stopper.evaluate(ctx, state, remaining_candidates_count=len(snapshots) - len(answered_ids))

        steps.append(
            SelectionTraceStep(
                step=step_idx,
                selected_question_id=chosen.question_id,
                question_version=chosen.version,
                difficulty=chosen.difficulty,
                simulated_correct=is_corr,
                selection_reason=sel.selection_reason,
                chosen_details=sel.metadata.get("chosen_details", {}),
                theta_after=dict(state.dimension_scores),
                uncertainty_after=dict(state.uncertainty),
                stopping_should_stop=stop_dec.should_stop,
                stopping_reason=stop_dec.reason.value if stop_dec.reason else None,
            )
        )
        if stop_dec.should_stop:
            break

    return SelectionTraceResponse(
        seed=request.seed,
        student_age=request.student_age,
        true_ability=true_theta,
        steps=steps,
        final_theta=dict(state.dimension_scores),
        final_uncertainty=dict(state.uncertainty),
    )
