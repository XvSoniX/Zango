import random
import uuid
from typing import List, Dict, Optional
from app.simulation.domain.archetypes import ArchetypeType, ARCHETYPE_TEMPLATES
from app.simulation.domain.synthetic_user import SyntheticUserProfile


class SyntheticUserGenerator:
    """
    Generates synthetic participants with predefined ground-truth abilities.
    Guarantees deterministic, reproducible generation using a fixed seed.
    """

    @classmethod
    def generate_users(
        cls,
        simulation_run_id: str,
        count: int = 10,
        archetypes: Optional[List[ArchetypeType]] = None,
        min_age: int = 12,
        max_age: int = 18,
        random_seed: int = 42,
        custom_ability: Optional[Dict[str, float]] = None,
    ) -> List[SyntheticUserProfile]:
        """
        Generates synthetic profiles distributed across requested archetypes.
        """
        rng = random.Random(random_seed)
        selected_archetypes = archetypes or [
            ArchetypeType.BALANCED,
            ArchetypeType.STRONG,
            ArchetypeType.DEVELOPING,
            ArchetypeType.SPECIALIZED,
            ArchetypeType.MIXED,
        ]

        participants: List[SyntheticUserProfile] = []

        for idx in range(count):
            user_seed = rng.randint(1000, 999999)
            user_rng = random.Random(user_seed)

            # Assign archetype round-robin or randomly from the pool
            if custom_ability:
                archetype = ArchetypeType.CUSTOM
                ground_truth = {k: round(float(v), 3) for k, v in custom_ability.items()}
                speed = 1.0
            else:
                archetype = selected_archetypes[idx % len(selected_archetypes)]
                template = ARCHETYPE_TEMPLATES[archetype]

                ground_truth = {}
                for dim_code, base_val in template.base_scores.items():
                    # Apply controlled gaussian jitter
                    jitter = user_rng.gauss(0, template.score_variance)
                    val = max(-3.0, min(3.0, base_val + jitter))
                    ground_truth[dim_code] = round(val, 3)

                speed = round(template.speed_factor * user_rng.uniform(0.9, 1.1), 2)

            age = user_rng.randint(min_age, max_age)
            synthetic_id = f"sim-{simulation_run_id[:8]}-u{idx+1:04d}"

            profile = SyntheticUserProfile(
                synthetic_user_id=synthetic_id,
                simulation_run_id=simulation_run_id,
                archetype=archetype,
                ground_truth_ability=ground_truth,
                age=age,
                speed_factor=speed,
                random_seed=user_seed,
            )
            participants.append(profile)

        return participants
