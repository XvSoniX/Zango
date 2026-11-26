from typing import Optional, Dict, Any, List
from app.config import settings
from app.domain.dimensions import normalize_dimension_code
from app.domain.enums import StoppingReason
from app.engine.protocols import (
    AssessmentContext,
    AbilityState,
    StoppingDecision,
    StoppingStrategy,
)


class StandardStoppingStrategy:
    """
    Evaluates whether an adaptive assessment session should terminate.

    Evaluation Hierarchy (Strict Priority):
    1. Exhaustion Limit: If no eligible questions remain in the pool -> STOP (QUESTION_BANK_EXHAUSTED).
    2. Hard Ceiling: If response_count >= max_questions -> STOP (MAX_QUESTIONS_REACHED).
    3. Session Timeout: If elapsed_time >= max_duration -> STOP (TIME_EXPIRED).
    4. Floor Gate: If response_count < min_questions -> CANNOT STOP for convergence.
    5. Convergence Criteria: If response_count >= min_questions:
       - Every target dimension has reached minimum coverage (min_coverage_per_dim).
       - Every target dimension has reached target precision (uncertainty <= threshold).
       -> STOP (MIN_UNCERTAINTY_ACHIEVED).
    6. Default: CONTINUE (should_stop=False).
    """

    def __init__(
        self,
        min_uncertainty_threshold: Optional[float] = None,
        min_coverage_per_dimension: int = 2,
        version: str = "1.0.0-baseline",
    ):
        self.min_uncertainty_threshold = (
            min_uncertainty_threshold
            if min_uncertainty_threshold is not None
            else settings.MIN_UNCERTAINTY_THRESHOLD
        )
        self.min_coverage_per_dimension = min_coverage_per_dimension
        self.version = version

    def evaluate(
        self,
        context: AssessmentContext,
        ability_state: AbilityState,
        remaining_candidates_count: Optional[int] = None,
    ) -> StoppingDecision:
        """
        Determines whether the assessment session should terminate or continue.

        Args:
            context: Current session execution context.
            ability_state: Current estimated ability scores, uncertainties, and coverage.
            remaining_candidates_count: Number of remaining eligible candidates (if known).

        Returns:
            StoppingDecision containing boolean flag, stopping reason, and audit detail.
        """
        target_dims = [normalize_dimension_code(d) for d in context.target_dimensions]
        resp_count = ability_state.response_count
        elapsed_sec = context.elapsed_time_seconds
        max_duration = context.max_duration_seconds
        max_q = context.max_questions
        min_q = context.min_questions

        coverage_map = ability_state.dimension_coverage or {}
        uncertainty_map = ability_state.uncertainty or {}

        # -------------------------------------------------------------
        # Condition 1: Question Bank Exhausted (Priority 1)
        # -------------------------------------------------------------
        if remaining_candidates_count is not None and remaining_candidates_count <= 0:
            return StoppingDecision(
                should_stop=True,
                reason=StoppingReason.QUESTION_BANK_EXHAUSTED,
                detail="No eligible candidate questions remain in the question bank for this session.",
                stopping_version=self.version,
                metadata={
                    "response_count": resp_count,
                    "remaining_candidates": 0,
                    "elapsed_time_seconds": elapsed_sec,
                }
            )

        # -------------------------------------------------------------
        # Condition 2: Maximum Questions Ceilings (Priority 2)
        # -------------------------------------------------------------
        if resp_count >= max_q:
            return StoppingDecision(
                should_stop=True,
                reason=StoppingReason.MAX_QUESTIONS_REACHED,
                detail=f"Hard question ceiling reached: {resp_count}/{max_q} questions answered.",
                stopping_version=self.version,
                metadata={
                    "response_count": resp_count,
                    "max_questions": max_q,
                    "elapsed_time_seconds": elapsed_sec,
                }
            )

        # -------------------------------------------------------------
        # Condition 3: Maximum Session Duration Exceeded (Priority 3)
        # -------------------------------------------------------------
        if max_duration > 0 and elapsed_sec >= max_duration:
            return StoppingDecision(
                should_stop=True,
                reason=StoppingReason.TIME_EXPIRED,
                detail=f"Session duration exceeded limit: {elapsed_sec:.1f}s / {max_duration:.1f}s.",
                stopping_version=self.version,
                metadata={
                    "elapsed_time_seconds": elapsed_sec,
                    "max_duration_seconds": max_duration,
                    "response_count": resp_count,
                }
            )

        # -------------------------------------------------------------
        # Condition 4: Floor Gate (Must satisfy minimum questions)
        # -------------------------------------------------------------
        if resp_count < min_q:
            # Cannot stop for convergence before reaching minimum test length
            return StoppingDecision(
                should_stop=False,
                reason=None,
                detail=f"Session below minimum questions threshold: {resp_count}/{min_q}.",
                stopping_version=self.version,
                metadata={
                    "response_count": resp_count,
                    "min_questions": min_q,
                    "floor_gate_passed": False,
                }
            )

        # -------------------------------------------------------------
        # Condition 5: Measurement Convergence (Uncertainty & Coverage)
        # -------------------------------------------------------------
        # 5a. Check Dimension Coverage
        all_dims_covered = True
        unmet_coverage_dims: List[str] = []
        for d in target_dims:
            c = coverage_map.get(d, 0)
            if c < self.min_coverage_per_dimension:
                all_dims_covered = False
                unmet_coverage_dims.append(d)

        # 5b. Check Uncertainty Threshold
        all_dims_precise = True
        unmet_uncertainty_dims: List[str] = []
        for d in target_dims:
            u = uncertainty_map.get(d, 1.0)
            if u > self.min_uncertainty_threshold:
                all_dims_precise = False
                unmet_uncertainty_dims.append(d)

        if all_dims_covered and all_dims_precise:
            return StoppingDecision(
                should_stop=True,
                reason=StoppingReason.MIN_UNCERTAINTY_ACHIEVED,
                detail=(
                    f"Measurement uncertainty threshold ({self.min_uncertainty_threshold}) and "
                    f"minimum dimension coverage ({self.min_coverage_per_dimension}) satisfied "
                    f"across all {len(target_dims)} target dimensions."
                ),
                stopping_version=self.version,
                metadata={
                    "response_count": resp_count,
                    "min_questions": min_q,
                    "all_dimensions_covered": True,
                    "all_dimensions_precise": True,
                    "target_dimensions": target_dims,
                }
            )

        # -------------------------------------------------------------
        # Condition 6: Default (Continue Testing)
        # -------------------------------------------------------------
        return StoppingDecision(
            should_stop=False,
            reason=None,
            detail=(
                f"Testing continues ({resp_count} questions answered). "
                f"Unmet coverage dimensions: {unmet_coverage_dims}; "
                f"Unmet precision dimensions: {unmet_uncertainty_dims}."
            ),
            stopping_version=self.version,
            metadata={
                "response_count": resp_count,
                "floor_gate_passed": True,
                "unmet_coverage_dims": unmet_coverage_dims,
                "unmet_uncertainty_dims": unmet_uncertainty_dims,
            }
        )
