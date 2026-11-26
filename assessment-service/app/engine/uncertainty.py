import math
from typing import Dict, Any, Optional
from app.config import settings
from app.domain.dimensions import DIMENSION_REGISTRY, normalize_dimension_code
from app.engine.protocols import AbilityState


def probability_3pl(
    theta: float,
    difficulty: float,
    discrimination: float = 1.0,
    guessing: float = 0.25,
) -> float:
    """
    3-Parameter Logistic (3PL) IRT probability of a correct response:
        P(Y = 1 | theta) = c + (1 - c) / (1 + exp(-a * (theta - b)))
    """
    a = max(0.05, float(discrimination))
    c = max(0.0, min(0.5, float(guessing)))
    logit = max(-20.0, min(20.0, a * (theta - difficulty)))
    return c + (1.0 - c) / (1.0 + math.exp(-logit))


def fisher_information_3pl(
    theta: float,
    difficulty: float,
    discrimination: float = 1.0,
    guessing: float = 0.25,
) -> float:
    """
    3PL IRT Fisher Information at ability theta:
        I(theta) = a^2 * ((P - c)^2 / (1 - c)^2) * ((1 - P) / P)
    Reduces cleanly to a^2 * P * (1 - P) when guessing c == 0.
    """
    a = max(0.05, float(discrimination))
    c = max(0.0, min(0.5, float(guessing)))
    p = probability_3pl(theta, difficulty, a, c)
    p_clamped = max(1e-6, min(1.0 - 1e-6, p))
    if c <= 0.0:
        return (a * a) * p_clamped * (1.0 - p_clamped)
    ratio = (p_clamped - c) / max(1e-6, 1.0 - c)
    if ratio <= 0.0:
        return 0.0
    return (a * a) * (ratio * ratio) * ((1.0 - p_clamped) / p_clamped)


class UncertaintyEstimator:
    """
    Stateless estimator for measurement uncertainty across cognitive dimensions.

    Core principles (Fisher Information Bayesian Posterior SE):
    1. Prior Precision: Starts at 1 / sigma_0^2 (sigma_0 = 1.0) before evidence is observed.
    2. Fisher Information Accumulation: Each valid response contributes w_d^2 * I_i(theta_d)
       to dimension d's total information.
    3. Posterior Standard Error:
           SE(theta_d) = max(sigma_min, 1 / sqrt(1 / sigma_0^2 + I_acc,d))
    4. Uncovered Dimensions: Dimensions lacking relevant evidence retain their high prior uncertainty.
    """

    def __init__(
        self,
        initial_uncertainty: float = 1.0,
        min_uncertainty: float = 0.32,
        evidence_scaling: float = 0.5,
    ):
        self.initial_uncertainty = initial_uncertainty
        self.min_uncertainty = min_uncertainty
        self.evidence_scaling = evidence_scaling

    def create_initial_uncertainty(self) -> Dict[str, float]:
        """Returns baseline prior uncertainty for all 5 cognitive dimensions."""
        return {dim_code: round(self.initial_uncertainty, 4) for dim_code in DIMENSION_REGISTRY}

    def compute_uncertainty(
        self,
        current_state: AbilityState,
        dimensions_vector: Dict[str, float],
        is_valid_response: bool = True,
        item_info_per_dim: Optional[Dict[str, float]] = None,
    ) -> tuple[Dict[str, float], Dict[str, float]]:
        """
        Calculates updated posterior SE and accumulated Fisher information for each dimension.
        """
        current_evidence: Dict[str, float] = dict(
            current_state.metadata.get("accumulated_evidence", {})
        )
        for dim_code in DIMENSION_REGISTRY:
            if dim_code not in current_evidence:
                current_evidence[dim_code] = 0.0

        updated_uncertainty: Dict[str, float] = {}
        updated_evidence: Dict[str, float] = dict(current_evidence)

        norm_weights: Dict[str, float] = {}
        for k, v in dimensions_vector.items():
            try:
                norm_key = normalize_dimension_code(k)
                norm_weights[norm_key] = max(0.0, min(1.0, float(v)))
            except ValueError:
                continue

        prior_precision = 1.0 / (self.initial_uncertainty ** 2)

        for dim_code in DIMENSION_REGISTRY:
            w_d = norm_weights.get(dim_code, 0.0)
            if not is_valid_response or w_d <= 0.0:
                added_info = 0.0
            elif item_info_per_dim is not None and dim_code in item_info_per_dim:
                added_info = (w_d ** 2) * max(0.0, float(item_info_per_dim[dim_code]))
            else:
                added_info = w_d

            new_ev = round(current_evidence.get(dim_code, 0.0) + added_info, 4)
            updated_evidence[dim_code] = new_ev

            total_precision = prior_precision + new_ev
            raw_uncertainty = 1.0 / math.sqrt(max(1e-6, total_precision))
            bounded_uncertainty = max(self.min_uncertainty, raw_uncertainty)
            updated_uncertainty[dim_code] = round(bounded_uncertainty, 4)

        return updated_uncertainty, updated_evidence
