import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Sequence, Tuple
from app.config import settings
from app.domain.dimensions import normalize_dimension_code
from app.domain.profile import check_compatibility
from app.domain.dimensions import DimensionsVector
from app.engine.uncertainty import fisher_information_3pl
from app.engine.protocols import (
    ItemParameterSnapshot,
    AssessmentContext,
    SelectionResult,
    QuestionSelectionStrategy,
)


@dataclass(frozen=True)
class SelectorWeights:
    """
    Configurable weights for the Composite Heuristic Question Selector.
    All weights must be non-negative and their sum should equal approximately 1.0.
    """
    weight_coverage: float = 0.30
    weight_uncertainty: float = 0.25
    weight_difficulty_fit: float = 0.20
    weight_ability: float = 0.15
    weight_relevance: float = 0.10
    weight_exposure_penalty: float = 0.05

    def __post_init__(self):
        for field_name, value in self.__dict__.items():
            if value < 0.0:
                raise ValueError(f"Weight '{field_name}' must be non-negative, got {value}")
        main_sum = (
            self.weight_coverage
            + self.weight_uncertainty
            + self.weight_difficulty_fit
            + self.weight_ability
            + self.weight_relevance
        )
        if main_sum <= 0.0:
            raise ValueError("Sum of primary selection weights must be strictly positive.")


class CandidateFilter:
    """
    Filters question candidates according to session eligibility rules.
    Guarantees:
    - Questions already answered in this session are excluded.
    - Inactive items are excluded.
    - Questions outside student age range are excluded.
    - Questions with no relevance to profile target dimensions are excluded.
    - Items with invalid psychometric or dimension parameters are excluded.
    - Over-exposed items exceeding exposure limits are excluded.
    """

    @staticmethod
    def filter_candidates(
        candidate_pool: Sequence[ItemParameterSnapshot],
        context: AssessmentContext,
    ) -> Tuple[List[ItemParameterSnapshot], Dict[str, int]]:
        """
        Filters candidates and returns (eligible_candidates, rejection_reasons_summary).
        """
        eligible: List[ItemParameterSnapshot] = []
        rejection_stats: Dict[str, int] = {
            "already_answered": 0,
            "inactive": 0,
            "age_mismatch": 0,
            "profile_incompatible": 0,
            "invalid_dimensions": 0,
            "invalid_difficulty": 0,
            "exposure_limit_reached": 0,
        }

        answered_set = set(context.answered_question_ids)
        target_dims_set = {normalize_dimension_code(d) for d in context.target_dimensions}

        for q in candidate_pool:
            # 1. Already answered check
            if q.question_id in answered_set:
                rejection_stats["already_answered"] += 1
                continue

            # 2. Active status check
            if not getattr(q, "is_active", True):
                rejection_stats["inactive"] += 1
                continue

            # 3. Age compatibility check
            if context.student_age > 0:
                if context.student_age < q.min_age or context.student_age > q.max_age:
                    rejection_stats["age_mismatch"] += 1
                    continue

            # 4. Exposure limit check
            exp_lim = getattr(q, "exposure_limit", None)
            exp_cnt = getattr(q, "exposure_count", 0)
            if exp_lim is not None and exp_lim > 0 and exp_cnt >= exp_lim:
                rejection_stats["exposure_limit_reached"] += 1
                continue

            # 5. Difficulty bounds check [-4.0, +4.0]
            if not (-4.0 <= q.difficulty <= 4.0):
                rejection_stats["invalid_difficulty"] += 1
                continue

            # 6. Dimensions vector validity & relevance
            q_dims = q.dimensions or {}
            if not isinstance(q_dims, dict) or not q_dims:
                rejection_stats["invalid_dimensions"] += 1
                continue

            # Verify at least one target dimension has positive association
            has_target_overlap = False
            total_weight = 0.0
            for dim_code, weight in q_dims.items():
                try:
                    norm_code = normalize_dimension_code(dim_code)
                    w = float(weight)
                    if 0.0 <= w <= 1.0:
                        total_weight += w
                        if norm_code in target_dims_set and w > 0.0:
                            has_target_overlap = True
                except (ValueError, TypeError):
                    continue

            if total_weight <= 0.0:
                rejection_stats["invalid_dimensions"] += 1
                continue

            if not has_target_overlap:
                rejection_stats["profile_incompatible"] += 1
                continue

            eligible.append(q)

        return eligible, rejection_stats


class CompositeHeuristicSelector:
    """
    Adaptive Question Selector implementing the Composite Heuristic Strategy.
    Combines:
    1. Dimension Coverage: Prioritizes dimensions that have fewer responses so far.
    2. Uncertainty Reduction: Prioritizes dimensions with high measurement uncertainty.
    3. Difficulty Matching: Matches item difficulty to student's estimated ability (CAT info yield).
    4. Ability Challenge: Evaluates expected information curve at current student ability.
    5. Profile Relevance: Rewards questions highly aligned with profile target dimensions.
    6. Exposure Penalty: Penalizes over-exposed items to ensure balanced bank utilization.
    7. Deterministic Tie-breaking: Guarantees reproducible question sequences.
    """

    def __init__(
        self,
        weights: Optional[SelectorWeights] = None,
        difficulty_match_width: float = 1.2,
        version: str = "1.0.0-baseline"
    ):
        self.weights = weights or SelectorWeights(
            weight_coverage=settings.SELECTOR_WEIGHT_COVERAGE,
            weight_uncertainty=getattr(settings, "SELECTOR_WEIGHT_UNCERTAINTY", 0.25),
            weight_difficulty_fit=settings.SELECTOR_WEIGHT_DIFFICULTY_FIT,
            weight_ability=getattr(settings, "SELECTOR_WEIGHT_ABILITY", 0.15),
            weight_relevance=getattr(settings, "SELECTOR_WEIGHT_RELEVANCE", 0.10),
            weight_exposure_penalty=settings.SELECTOR_WEIGHT_EXPOSURE_PENALTY,
        )
        self.weights.__post_init__()
        self.difficulty_match_width = difficulty_match_width
        self.version = version

    def select(
        self,
        candidate_pool: Sequence[ItemParameterSnapshot],
        context: AssessmentContext,
    ) -> SelectionResult:
        """
        Selects the optimal next question from candidate_pool.

        Args:
            candidate_pool: All candidate questions available in repository.
            context: Full assessment session state.

        Returns:
            SelectionResult with selected ID, version, scores breakdown, and explanation.
        """
        # Step 1: Filter candidates for eligibility
        eligible_candidates, rejection_stats = CandidateFilter.filter_candidates(
            candidate_pool=candidate_pool,
            context=context
        )

        if not eligible_candidates:
            reason = "NO_ELIGIBLE_QUESTIONS"
            if rejection_stats["already_answered"] == len(candidate_pool) and len(candidate_pool) > 0:
                reason = "ALL_QUESTIONS_ANSWERED"
            elif rejection_stats["age_mismatch"] == len(candidate_pool) and len(candidate_pool) > 0:
                reason = "NO_AGE_COMPATIBLE_QUESTIONS"
            elif rejection_stats["profile_incompatible"] == len(candidate_pool) and len(candidate_pool) > 0:
                reason = "NO_PROFILE_COMPATIBLE_QUESTIONS"

            return SelectionResult(
                selected_question_id=None,
                selected_version=None,
                candidate_scores={},
                selection_reason=reason,
                selector_version=self.version,
                metadata={
                    "total_candidates": len(candidate_pool),
                    "eligible_candidates": 0,
                    "rejection_summary": rejection_stats,
                }
            )

        # Step 2: Calculate composite heuristic score for each eligible candidate
        target_dims = [normalize_dimension_code(d) for d in context.target_dimensions]
        candidate_scores: Dict[int, float] = {}
        candidate_details: Dict[int, Dict[str, Any]] = {}

        # Precompute coverage deficits across target dimensions
        # Deficit is higher for dimensions with fewer responses so far
        coverage_map = context.current_ability.dimension_coverage or {}
        cov_counts = [coverage_map.get(d, 0) for d in target_dims]
        max_cov = max(cov_counts) if cov_counts else 0
        dimension_deficits = {
            d: (max_cov - coverage_map.get(d, 0) + 1.0) / (max_cov + 1.0)
            for d in target_dims
        }

        # Precompute normalized uncertainty across target dimensions
        uncertainty_map = context.current_ability.uncertainty or {}
        sigma_0 = settings.INITIAL_PRIOR_UNCERTAINTY
        sigma_min = settings.MIN_UNCERTAINTY_THRESHOLD
        denom_unc = max(1e-4, sigma_0 - sigma_min)
        norm_uncertainties = {
            d: max(0.0, min(1.0, (uncertainty_map.get(d, sigma_0) - sigma_min) / denom_unc))
            for d in target_dims
        }

        for q in eligible_candidates:
            # 1. Normalize item weights on target dimensions
            q_dims = q.dimensions or {}
            norm_q_dims = {
                normalize_dimension_code(k): max(0.0, min(1.0, float(v)))
                for k, v in q_dims.items()
            }

            weight_target_sum = sum(norm_q_dims.get(d, 0.0) for d in target_dims)
            total_item_weight = sum(norm_q_dims.values())
            if weight_target_sum <= 0.0 or total_item_weight <= 0.0:
                continue

            # Component 1: Coverage Score (Prioritize under-tested dimensions)
            s_coverage = sum(
                norm_q_dims.get(d, 0.0) * dimension_deficits[d] for d in target_dims
            ) / weight_target_sum

            # Component 2: Uncertainty Reduction Score (Prioritize uncertain dimensions)
            s_uncertainty = sum(
                norm_q_dims.get(d, 0.0) * norm_uncertainties[d] for d in target_dims
            ) / weight_target_sum

            # Component 3: Weighted target ability for this item
            weighted_ability = sum(
                norm_q_dims.get(d, 0.0) * context.current_ability.dimension_scores.get(d, 0.0)
                for d in target_dims
            ) / weight_target_sum

            # Component 4 & 5: Maximum Fisher Information (MFI) under 3PL IRT
            a_param = max(0.05, float(getattr(q, "discrimination", 1.0) or 1.0))
            c_param = max(0.0, min(0.5, float(getattr(q, "guessing", 0.25) if getattr(q, "guessing", None) is not None else 0.25)))
            fisher_info = fisher_information_3pl(
                theta=weighted_ability,
                difficulty=q.difficulty,
                discrimination=a_param,
                guessing=c_param,
            )
            # Normalize Fisher info smoothly to [0, 1) for composite ranking
            s_difficulty = fisher_info / (fisher_info + 0.25)
            s_ability = min(1.0, fisher_info / max(0.25, a_param * a_param * 0.25))

            # Component 6: Profile Relevance Score (Concentration of weights in target dimensions)
            s_relevance = weight_target_sum / total_item_weight

            # Component 7: Exposure Penalty
            exp_lim = getattr(q, "exposure_limit", None)
            exp_cnt = getattr(q, "exposure_count", 0)
            if exp_lim and exp_lim > 0:
                s_exposure = min(1.0, exp_cnt / exp_lim)
            else:
                s_exposure = 0.0

            # Composite Heuristic Formula
            composite_score = (
                (self.weights.weight_coverage * s_coverage)
                + (self.weights.weight_uncertainty * s_uncertainty)
                + (self.weights.weight_difficulty_fit * s_difficulty)
                + (self.weights.weight_ability * s_ability)
                + (self.weights.weight_relevance * s_relevance)
                - (self.weights.weight_exposure_penalty * s_exposure)
            )

            # Clamp final score
            composite_score = round(max(0.0, composite_score), 4)

            candidate_scores[q.question_id] = composite_score
            candidate_details[q.question_id] = {
                "question_id": q.question_id,
                "version": q.version,
                "composite_score": composite_score,
                "coverage_score": round(s_coverage, 4),
                "uncertainty_score": round(s_uncertainty, 4),
                "difficulty_score": round(s_difficulty, 4),
                "ability_score": round(s_ability, 4),
                "relevance_score": round(s_relevance, 4),
                "exposure_score": round(s_exposure, 4),
                "difficulty": q.difficulty,
                "weighted_ability": round(weighted_ability, 4),
                "dominant_dimension": max(norm_q_dims.items(), key=lambda x: x[1])[0],
                "calibration_status": getattr(q, "calibration_status", "UNCALIBRATED"),
            }

        if not candidate_scores:
            return SelectionResult(
                selected_question_id=None,
                selected_version=None,
                candidate_scores={},
                selection_reason="NO_VALID_SCORABLE_CANDIDATES",
                selector_version=self.version,
                metadata={"total_candidates": len(candidate_pool), "eligible_candidates": 0}
            )

        # Step 3: Deterministic Ranking
        # Primary: Highest composite score
        # Tie-breaker: Smallest question_id, then smallest version (Strictly deterministic)
        ranked = sorted(
            eligible_candidates,
            key=lambda item: (-candidate_scores[item.question_id], item.question_id, item.version)
        )

        chosen = ranked[0]
        chosen_details = candidate_details[chosen.question_id]

        explanation = (
            f"Question {chosen.question_id} selected with score {chosen_details['composite_score']}. "
            f"Target dimension: '{chosen_details['dominant_dimension']}'. "
            f"Coverage weight: {chosen_details['coverage_score']}, "
            f"Uncertainty weight: {chosen_details['uncertainty_score']}, "
            f"Difficulty match: {chosen_details['difficulty_score']} "
            f"(diff: {chosen.difficulty}, ability: {chosen_details['weighted_ability']})."
        )

        return SelectionResult(
            selected_question_id=chosen.question_id,
            selected_version=chosen.version,
            candidate_scores=candidate_scores,
            selection_reason=explanation,
            selector_version=self.version,
            metadata={
                "chosen_details": chosen_details,
                "total_candidates": len(candidate_pool),
                "eligible_candidates": len(eligible_candidates),
                "weights_used": self.weights.__dict__,
            }
        )
