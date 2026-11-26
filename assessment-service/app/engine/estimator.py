import math
from typing import Dict, Any, Optional, List, Union
from app.config import settings
from app.domain.dimensions import DIMENSION_REGISTRY, normalize_dimension_code
from app.engine.protocols import (
    AbilityState,
    EvaluationResult,
    ItemParameterSnapshot,
    AssessmentContext,
    AbilityEstimationStrategy
)
from app.engine.uncertainty import (
    UncertaintyEstimator,
    probability_3pl,
    fisher_information_3pl,
)


def create_initial_ability_state(
    target_dimensions: Optional[List[str]] = None,
    initial_score: Optional[float] = None,
    initial_uncertainty: Optional[float] = None,
) -> AbilityState:
    """
    Factory function for a fresh baseline AbilityState across all cognitive dimensions.

    Args:
        target_dimensions: Optional subset of dimensions; defaults to all 5 registry dimensions.
        initial_score: Prior mean ability (defaults to settings.INITIAL_PRIOR_ABILITY, 0.0).
        initial_uncertainty: Prior uncertainty (defaults to settings.INITIAL_PRIOR_UNCERTAINTY, 1.0).

    Returns:
        New immutable AbilityState.
    """
    score_val = initial_score if initial_score is not None else settings.INITIAL_PRIOR_ABILITY
    unc_val = initial_uncertainty if initial_uncertainty is not None else settings.INITIAL_PRIOR_UNCERTAINTY

    dims = target_dimensions or list(DIMENSION_REGISTRY.keys())
    normalized_dims = [normalize_dimension_code(d) for d in dims]

    dimension_scores = {d: round(score_val, 4) for d in normalized_dims}
    uncertainty = {d: round(unc_val, 4) for d in normalized_dims}
    coverage = {d: 0 for d in normalized_dims}
    accumulated_evidence = {d: 0.0 for d in normalized_dims}

    return AbilityState(
        dimension_scores=dimension_scores,
        uncertainty=uncertainty,
        response_count=0,
        dimension_coverage=coverage,
        metadata={
            "accumulated_evidence": accumulated_evidence,
            "estimator_version": settings.ALGORITHM_VERSION,
        }
    )


class BaselineMultidimensionalEstimator:
    """
    Pure, stateless estimator for multidimensional cognitive ability.

    Core principles:
    1. Independent Dimension Updates: Each of the 5 cognitive dimensions is updated independently.
    2. Separation of Dimensions Vector and Difficulty:
       - Dimensions Vector (w_d): Quantifies how much the question measures dimension d.
         If w_d is 0 (or below threshold), the dimension score does not change.
       - Difficulty (b): Represents item difficulty on IRT scale [-4.0, +4.0].
         Answering a hard item correctly yields larger increase; missing an easy item yields larger penalty.
    3. Innovation / Residual Update:
       - Expected probability of success: P_d = 1 / (1 + exp(-(theta_d - b)))
       - Innovation: e_d = y - P_d, where y in {0.0, 1.0}
       - Step: delta_theta_d = learning_rate * w_d * e_d * calibration_damping
    4. Boundedness & Stability:
       - Step size is inherently bounded by learning_rate * 1.0 * 1.0 <= learning_rate.
       - Scores are strictly clamped within [min_ability, max_ability] (default: [-3.0, +3.0]).
    5. Uncertainty Co-Estimation:
       - Uses UncertaintyEstimator to update measurement uncertainty and dimensional evidence.
    """

    def __init__(
        self,
        learning_rate: float = 0.5,
        min_ability: float = -3.0,
        max_ability: float = 3.0,
        min_weight_threshold: float = 0.05,
        uncertainty_estimator: Optional[UncertaintyEstimator] = None,
        version: str = "1.0.0-baseline"
    ):
        self.learning_rate = learning_rate
        self.min_ability = min_ability
        self.max_ability = max_ability
        self.min_weight_threshold = min_weight_threshold
        self.uncertainty_estimator = uncertainty_estimator or UncertaintyEstimator()
        self.version = version

    def estimate(
        self,
        current_state: AbilityState,
        latest_evaluation: EvaluationResult,
        question: Any,
        context: Optional[AssessmentContext] = None,
    ) -> AbilityState:
        """
        Computes updated ability state following an answer evaluation.

        Args:
            current_state: Pre-response AbilityState.
            latest_evaluation: Outcome of AnswerEvaluator.
            question: QuestionVersionModel, ItemParameterSnapshot, or dict containing
                      dimensions vector, difficulty, and optional calibration_status.
            context: Optional contextual parameters (target dimensions, bounds, etc.).

        Returns:
            New AbilityState with updated scores, coverage, uncertainty, and response count.
        """
        # 1. Extract item parameters (including 3PL discrimination a and guessing c)
        dimensions_vector, difficulty, discrimination, guessing, calib_status = (
            self._extract_parameters(question)
        )

        # 2. Extract outcome
        y = 1.0 if latest_evaluation.is_correct else 0.0
        is_valid = (latest_evaluation.evaluation_status == "VALID")

        # 3. Calibration damping: slight damping if question is uncalibrated
        damping = 0.85 if calib_status == "UNCALIBRATED" else 1.0

        updated_scores: Dict[str, float] = {}
        updated_coverage: Dict[str, int] = dict(current_state.dimension_coverage)
        item_info_per_dim: Dict[str, float] = {}

        # 4. Update each dimension independently using 3PL IRT + Fisher Information
        for dim_code, current_theta in current_state.dimension_scores.items():
            norm_code = normalize_dimension_code(dim_code)
            w_d = dimensions_vector.get(norm_code, 0.0)

            # If response is invalid (e.g. RAPID_GUESS) or dimension irrelevant, leave score untouched
            if not is_valid or w_d < self.min_weight_threshold:
                updated_scores[dim_code] = current_theta
                continue

            # 3PL expected probability and Fisher Information at current_theta
            p_expected = probability_3pl(current_theta, difficulty, discrimination, guessing)
            info_d = fisher_information_3pl(current_theta, difficulty, discrimination, guessing)
            item_info_per_dim[norm_code] = info_d

            # 3PL score function derivative: a * (P - c) / ((1 - c) * P) * (y - P)
            p_clamped = max(1e-6, min(1.0 - 1e-6, p_expected))
            if guessing > 0.0:
                guessing_factor = max(0.0, (p_clamped - guessing) / (max(1e-6, 1.0 - guessing) * p_clamped))
            else:
                guessing_factor = 1.0

            innovation = y - p_expected
            step = self.learning_rate * w_d * discrimination * guessing_factor * innovation * damping
            # Clamp single-item step for numerical stability
            step = max(-self.learning_rate, min(self.learning_rate, step))
            new_theta = current_theta + step

            # Clamp to allowed ability bounds [-3.0, +3.0]
            bounded_theta = max(self.min_ability, min(self.max_ability, new_theta))
            updated_scores[dim_code] = round(bounded_theta, 4)

            # Update dimension coverage count if dimension has meaningful association (>= 0.1)
            if w_d >= 0.1:
                updated_coverage[dim_code] = updated_coverage.get(dim_code, 0) + 1

        # 5. Co-estimate posterior uncertainty via Fisher Information
        new_uncertainty, new_evidence = self.uncertainty_estimator.compute_uncertainty(
            current_state=current_state,
            dimensions_vector=dimensions_vector,
            is_valid_response=is_valid,
            item_info_per_dim=item_info_per_dim if is_valid else None,
        )

        # 6. Increment total response count (including rapid guesses in response history, or valid count)
        new_response_count = current_state.response_count + (1 if is_valid else 0)

        # 7. Construct new AbilityState
        new_metadata = dict(current_state.metadata)
        new_metadata["accumulated_evidence"] = new_evidence
        new_metadata["estimator_version"] = self.version
        new_metadata["last_updated_dimensions"] = [
            d for d, w in dimensions_vector.items() if w >= self.min_weight_threshold
        ]
        if latest_evaluation.evaluation_status == "RAPID_GUESS":
            new_metadata["rapid_guess_count"] = int(new_metadata.get("rapid_guess_count", 0)) + 1

        return AbilityState(
            dimension_scores=updated_scores,
            uncertainty=new_uncertainty,
            response_count=new_response_count,
            dimension_coverage=updated_coverage,
            metadata=new_metadata
        )

    def _extract_parameters(self, question: Any) -> tuple[Dict[str, float], float, float, float, str]:
        """Extracts normalized dimensions vector, difficulty (b), discrimination (a), guessing (c), and calibration."""
        if question is None:
            return {}, 0.0, 1.0, 0.25, "UNCALIBRATED"

        if isinstance(question, dict):
            raw_dims = question.get("dimensions") or {}
            diff = float(question.get("difficulty", 0.0))
            disc = float(question.get("discrimination", 1.0) or 1.0)
            raw_guess = question.get("guessing", 0.25)
            guess = float(raw_guess) if raw_guess is not None else 0.25
            calib = str(question.get("calibration_status", "UNCALIBRATED")).upper()
        else:
            raw_dims = getattr(question, "dimensions", None) or {}
            diff = float(getattr(question, "difficulty", 0.0))
            disc = float(getattr(question, "discrimination", 1.0) or 1.0)
            raw_guess = getattr(question, "guessing", 0.25)
            guess = float(raw_guess) if raw_guess is not None else 0.25
            calib = str(getattr(question, "calibration_status", "UNCALIBRATED")).upper()

        disc = max(0.05, disc)
        guess = max(0.0, min(0.5, guess))

        # Normalize dimension codes in vector
        norm_vector: Dict[str, float] = {}
        if isinstance(raw_dims, dict):
            for k, v in raw_dims.items():
                try:
                    norm_k = normalize_dimension_code(str(k))
                    norm_vector[norm_k] = max(0.0, min(1.0, float(v)))
                except ValueError:
                    continue

        return norm_vector, diff, disc, guess, calib
