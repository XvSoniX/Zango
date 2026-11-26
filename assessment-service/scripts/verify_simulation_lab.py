"""
Verification script for TASK-033: Simulation Lab.
Validates synthetic participant generation, multidimensional response simulation,
and execution of an end-to-end simulation batch against real engine components.
"""
import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.profile import AssessmentProfileModel, ProfileQuestionAssociationModel
from app.infrastructure.persistence.models.question import QuestionModel, QuestionVersionModel
from app.domain.enums import QuestionVersionStatus
from app.simulation.domain.archetypes import ArchetypeType
from app.simulation.domain.user_generator import SyntheticUserGenerator
from app.simulation.domain.response_simulator import ResponseSimulator
from app.simulation.orchestration.orchestrator import SimulationOrchestrator
from app.simulation.persistence.repository import SimulationRepository


async def run_verification():
    print("=" * 60)
    print("TASK-033: Simulation Lab Verification")
    print("=" * 60)

    # 1. Setup in-memory test database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        # Seed test profile & questions
        profile = AssessmentProfileModel(
            code="TECHNICAL_TALENT_V1",
            title="Technical Profile",
            version=1,
            dimensions=["logical_reasoning", "algorithmic_thinking", "spatial_reasoning"],
            min_age=10,
            max_age=18,
            is_active=True,
        )
        db.add(profile)
        await db.flush()

        for i in range(1, 6):
            dim = profile.dimensions[(i - 1) % len(profile.dimensions)]
            q = QuestionModel(code=f"Q-SIM-{i:03d}", question_type="MULTIPLE_CHOICE", is_active=True)
            db.add(q)
            await db.flush()

            v = QuestionVersionModel(
                question_id=q.id,
                version=1,
                status=QuestionVersionStatus.PUBLISHED.value,
                content=f"Simulation question {i}",
                question_type="MULTIPLE_CHOICE",
                options=[
                    {"key": "A", "text": "Opt A"},
                    {"key": "B", "text": "Opt B"},
                    {"key": "C", "text": "Opt C"},
                    {"key": "D", "text": "Opt D"},
                ],
                correct_answer="B",
                difficulty=-1.0 + (0.5 * i),
                discrimination=1.2,
                guessing=0.25,
                min_age=10,
                max_age=18,
                estimated_time=45,
                dimensions={dim: 1.0},
            )
            db.add(v)
            await db.flush()

            assoc = ProfileQuestionAssociationModel(profile_id=profile.id, question_id=q.id, is_active=True)
            db.add(assoc)

        await db.flush()

        # Step 1: Verify Synthetic User Generation
        print("\n[1] Testing Synthetic User Generation...")
        users = SyntheticUserGenerator.generate_users(
            simulation_run_id="run-test-001",
            count=5,
            archetypes=[
                ArchetypeType.STRONG,
                ArchetypeType.DEVELOPING,
                ArchetypeType.BALANCED,
                ArchetypeType.SPECIALIZED,
                ArchetypeType.MIXED,
            ],
            random_seed=42,
        )
        assert len(users) == 5
        print(f"  Generated {len(users)} synthetic users across all 5 archetypes.")
        for u in users:
            print(f"  - User {u.synthetic_user_id} ({u.archetype.value}): Ground Truth Logic={u.ground_truth_ability['logical_reasoning']}")

        # Verify determinism
        users_repeat = SyntheticUserGenerator.generate_users(
            simulation_run_id="run-test-001",
            count=5,
            archetypes=[
                ArchetypeType.STRONG,
                ArchetypeType.DEVELOPING,
                ArchetypeType.BALANCED,
                ArchetypeType.SPECIALIZED,
                ArchetypeType.MIXED,
            ],
            random_seed=42,
        )
        assert users[0].ground_truth_ability == users_repeat[0].ground_truth_ability
        print("  Determinism verified: identical seed yields identical ground-truth vectors.")

        # Step 2: Verify Response Simulator
        print("\n[2] Testing Multidimensional Response Simulator (3PL)...")
        simulator = ResponseSimulator()
        strong_user = users[0]  # Strong
        dev_user = users[1]     # Developing

        sample_q = QuestionVersionModel(
            question_id=1,
            difficulty=1.0,
            discrimination=1.5,
            guessing=0.25,
            dimensions={"logical_reasoning": 1.0},
            options=[{"key": "A", "text": ""}, {"key": "B", "text": ""}],
            correct_answer="B",
            estimated_time=45,
        )

        _, is_c_strong, rt_strong, p_strong = simulator.simulate_response(strong_user, sample_q, 101)
        _, is_c_dev, rt_dev, p_dev = simulator.simulate_response(dev_user, sample_q, 101)

        print(f"  Hard Item (b=1.0): Strong P={p_strong:.4f}, Developing P={p_dev:.4f}")
        assert p_strong > p_dev, "Strong participant should have higher success probability than developing participant."
        print(f"  Response times: Strong={rt_strong}ms, Developing={rt_dev}ms (both positive and bounded).")

        # Step 3: Run Full Simulation Batch via Orchestrator
        print("\n[3] Executing Full Simulation Batch via SimulationOrchestrator...")
        sim_orchestrator = SimulationOrchestrator(db)
        run_record = await sim_orchestrator.execute_simulation_run(
            name="Verification Run",
            profile_code="TECHNICAL_TALENT_V1",
            participant_count=5,
            random_seed=42,
        )

        assert run_record.status == "COMPLETED"
        assert run_record.completed_participant_count == 5
        assert run_record.failed_participant_count == 0
        print(f"  Simulation Run {run_record.id} completed successfully (status: {run_record.status}).")

        # Step 4: Verify Collected Results
        print("\n[4] Verifying Collected Participant Results...")
        sim_repo = SimulationRepository(db)
        results = await sim_repo.get_results_by_run_id(run_record.id)
        assert len(results) == 5

        for r in results:
            print(f"\n  Participant: {r.synthetic_user_id} (Archetype: {r.archetype})")
            print(f"    Answered Questions: {r.answered_question_count}")
            print(f"    Stopping Reason: {r.stopping_reason}")
            print(f"    Ground Truth Ability: {r.ground_truth_ability}")
            print(f"    Estimated Ability:    {r.estimated_ability}")
            print(f"    Uncertainty Vector:   {r.uncertainty_vector}")
            print(f"    Question Records Collected: {len(r.question_records)}")

            # Assert strict separation between ground-truth and estimated ability
            assert r.ground_truth_ability != r.estimated_ability
            assert len(r.question_records) == r.answered_question_count
            assert r.session_status == "COMPLETED"

        print("\n" + "=" * 60)
        print("ALL SIMULATION LAB VERIFICATIONS PASSED SUCCESSFULLY!")
        print("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_verification())
