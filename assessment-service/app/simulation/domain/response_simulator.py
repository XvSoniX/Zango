import math
import random
from typing import Dict, Any, List, Tuple
from app.simulation.domain.synthetic_user import SyntheticUserProfile


class ResponseSimulator:
    """
    Simulates realistic responses of synthetic participants to adaptive questions.
    Uses compensatory Multidimensional Item Response Theory (MIRT / 3PL):
    - Calculates effective ability weighted by the question's dimensions vector.
    - Computes success probability P(correct) = c + (1 - c) / (1 + exp(-1.7 * a * (theta_eff - b))).
    - Deterministically samples option choice and realistic response time.
    """

    def __init__(self, scaling_constant: float = 1.702):
        self.scaling_constant = scaling_constant

    def calculate_effective_ability(
        self,
        ground_truth: Dict[str, float],
        question_dimensions: Dict[str, float]
    ) -> float:
        """
        Computes effective multidimensional ability for an item based on dimension loadings.
        """
        total_weight = 0.0
        weighted_sum = 0.0

        for dim_code, weight in question_dimensions.items():
            norm_code = dim_code.strip().lower()
            w = max(0.0, float(weight))
            if w > 0.0 and norm_code in ground_truth:
                weighted_sum += w * ground_truth[norm_code]
                total_weight += w

        if total_weight <= 0.0:
            # Fallback to mean ability across all ground truth dimensions
            return sum(ground_truth.values()) / max(1, len(ground_truth))

        return weighted_sum / total_weight

    def calculate_p_correct(
        self,
        effective_ability: float,
        difficulty: float,
        discrimination: float = 1.0,
        guessing: float = 0.25,
    ) -> float:
        """
        Calculates probability of correct response under 3PL IRT model.
        """
        a = max(0.1, min(4.0, float(discrimination)))
        b = max(-4.0, min(4.0, float(difficulty)))
        c = max(0.0, min(0.5, float(guessing)))

        logit = -self.scaling_constant * a * (effective_ability - b)
        # Numerical stability clamp
        logit = max(-35.0, min(35.0, logit))

        p_logistic = 1.0 / (1.0 + math.exp(logit))
        return c + (1.0 - c) * p_logistic

    def simulate_response(
        self,
        user: SyntheticUserProfile,
        question_version: Any,
        step_seed: int,
    ) -> Tuple[Dict[str, Any], bool, int, float]:
        """
        Simulates an answer payload, correctness flag, response time, and probability.

        Args:
            user: Synthetic participant with ground truth profile.
            question_version: QuestionVersionModel or ItemParameterSnapshot.
            step_seed: Deterministic random seed for this specific question event.

        Returns:
            Tuple of (answer_dict, is_correct, response_time_ms, p_correct).
        """
        rng = random.Random(step_seed)

        # 1. Extract item parameters
        q_dims = getattr(question_version, "dimensions", {}) or {}
        difficulty = getattr(question_version, "difficulty", 0.0)
        discrimination = getattr(question_version, "discrimination", 1.0)
        guessing = getattr(question_version, "guessing", 0.25)
        options = getattr(question_version, "options", []) or []
        correct_answer = str(getattr(question_version, "correct_answer", "A")).strip().upper()
        est_time_secs = getattr(question_version, "estimated_time", 45) or 45

        # 2. Psychometric calculation
        eff_ability = self.calculate_effective_ability(user.ground_truth_ability, q_dims)
        p_correct = self.calculate_p_correct(
            effective_ability=eff_ability,
            difficulty=difficulty,
            discrimination=discrimination,
            guessing=guessing,
        )

        # 3. Sample correctness
        u = rng.random()
        is_correct = (u <= p_correct)

        # 4. Select option
        all_option_keys = [str(opt.get("key", "")).strip().upper() for opt in options if opt.get("key")]
        if not all_option_keys:
            all_option_keys = ["A", "B", "C", "D"]

        if is_correct:
            chosen_key = correct_answer if correct_answer in all_option_keys else all_option_keys[0]
        else:
            # Pick a distractor (incorrect option)
            distractors = [k for k in all_option_keys if k != correct_answer]
            chosen_key = rng.choice(distractors) if distractors else all_option_keys[0]

        # 5. Simulate realistic response time
        # Closer match between ability and difficulty requires more deliberation
        gap = abs(eff_ability - difficulty)
        deliberation_factor = max(0.7, 1.3 - (gap * 0.15))

        base_ms = est_time_secs * 1000
        speed_mod = 1.0 / max(0.5, user.speed_factor)
        noise = rng.uniform(0.85, 1.15)

        rt_ms = int(base_ms * speed_mod * deliberation_factor * noise)
        # Clamp within realistic bounds [3s, 180s]
        rt_ms = max(3000, min(180000, rt_ms))

        return {"selected_option": chosen_key}, is_correct, rt_ms, round(p_correct, 4)
