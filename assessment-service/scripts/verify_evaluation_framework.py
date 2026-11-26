"""
Verification script for Assessment Engine Evaluation Framework (TASK-034 & TASK-035).
Tests QuestionSelectionEvaluator, AbilityEstimationEvaluator, persistence, and API integration.
"""
import asyncio
import os
import sys

# Ensure assessment-service root is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.infrastructure.persistence.base import Base
from app.simulation.orchestration.orchestrator import SimulationOrchestrator
from app.simulation.domain.archetypes import ArchetypeType
from app.simulation.persistence.repository import SimulationRepository
from app.infrastructure.persistence.repositories.question_repo import QuestionRepository
from app.infrastructure.persistence.models.question import QuestionModel, QuestionVersionModel
from app.infrastructure.persistence.models.profile import AssessmentProfileModel, ProfileQuestionAssociationModel
from app.domain.enums import QuestionVersionStatus
from app.evaluation.persistence.repository import EvaluationRepository
from app.evaluation.services.question_selection_evaluator import QuestionSelectionEvaluator
from app.evaluation.services.ability_estimation_evaluator import AbilityEstimationEvaluator
from app.evaluation.domain.config import CANONICAL_DIMENSIONS, EvaluationSettings


async def run_verification():
    print("=" * 65)
    print("TASK-034 & TASK-035: Evaluation Framework Verification")
    print("=" * 65)

    # Use an in-memory SQLite database for isolated, reproducible testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as db:
        # 1. Populate test profile and question bank (50 questions across 5 dimensions)
        print("\n[1] Seeding test Profile and Question Bank with 50 items...")
        profile = AssessmentProfileModel(
            code="standard",
            title="Standard Assessment Profile",
            version=1,
            dimensions=CANONICAL_DIMENSIONS,
            min_age=10,
            max_age=18,
            is_active=True,
        )
        db.add(profile)
        await db.flush()

        dims_list = CANONICAL_DIMENSIONS
        for i in range(1, 51):
            main_dim = dims_list[(i - 1) % len(dims_list)]
            sec_dim = dims_list[i % len(dims_list)]
            diff = -2.0 + (i / 50.0) * 4.0  # Range -2.0 to +2.0

            q = QuestionModel(id=i, code=f"Q-{i:03d}", question_type="MULTIPLE_CHOICE", is_active=True)
            db.add(q)
            await db.flush()

            qv = QuestionVersionModel(
                question_id=q.id,
                version=1,
                status=QuestionVersionStatus.PUBLISHED.value,
                content=f"Question {i} test content",
                question_type="MULTIPLE_CHOICE",
                options=[
                    {"key": "A", "text": "Opt A"},
                    {"key": "B", "text": "Opt B"},
                    {"key": "C", "text": "Opt C"},
                    {"key": "D", "text": "Opt D"},
                ],
                correct_answer="B",
                difficulty=round(diff, 2),
                discrimination=1.2,
                guessing=0.25,
                min_age=10,
                max_age=18,
                estimated_time=45,
                dimensions={main_dim: 0.8, sec_dim: 0.2},
            )
            db.add(qv)
            await db.flush()

            assoc = ProfileQuestionAssociationModel(profile_id=profile.id, question_id=q.id, is_active=True)
            db.add(assoc)

        await db.commit()
        print("  Profile and Question bank populated successfully.")

        # 2. Run a batch simulation of 10 synthetic participants across various archetypes
        print("\n[2] Executing Simulation Run (10 participants)...")
        sim_orch = SimulationOrchestrator(db)
        sim_run = await sim_orch.execute_simulation_run(
            name="Verification Sim Run",
            profile_code="standard",
            participant_count=10,
            archetypes=[
                ArchetypeType.BALANCED,
                ArchetypeType.STRONG,
                ArchetypeType.DEVELOPING,
                ArchetypeType.SPECIALIZED,
                ArchetypeType.MIXED,
                ArchetypeType.BALANCED,
                ArchetypeType.STRONG,
                ArchetypeType.DEVELOPING,
                ArchetypeType.SPECIALIZED,
                ArchetypeType.MIXED,
            ],
            random_seed=12345,
        )
        assert sim_run.status == "COMPLETED"
        assert sim_run.completed_participant_count == 10
        print(f"  Simulation completed with ID: {sim_run.id}")

        # 3. Test TASK-034: Question Selection Evaluation
        print("\n[3] Testing QuestionSelectionEvaluator (TASK-034)...")
        eval_repo = EvaluationRepository(db)
        sim_repo = SimulationRepository(db)
        question_repo = QuestionRepository(db)

        qs_evaluator = QuestionSelectionEvaluator(
            eval_repo=eval_repo,
            sim_repo=sim_repo,
            question_repo=question_repo,
        )

        qs_result = await qs_evaluator.evaluate_simulation_runs([sim_run.id])
        assert qs_result["status"] == "COMPLETED"
        assert qs_result["eligible_sessions_count"] == 10
        assert qs_result["excluded_sessions_count"] == 0

        qs_summary = qs_result["summary_metrics"]
        print("  Question Selection Summary Metrics (Dashboard View):")
        print(f"    - Dimension Coverage:          {qs_summary['dimension_coverage_pct']}%")
        print(f"    - Average Questions:           {qs_summary['average_questions']}")
        print(f"    - Within-session Repetition:   {qs_summary['within_session_repetition_pct']}%")
        print(f"    - Exposure Distribution Index: {qs_summary['exposure_distribution_index']}")

        # Verify dimension coverage
        dim_cov = qs_result["dimension_coverage"]
        assert "per_dimension_metrics" in dim_cov
        for d in CANONICAL_DIMENSIONS:
            dm = dim_cov["per_dimension_metrics"][d]
            assert "total_question_exposures" in dm
            assert "sessions_covered_pct" in dm

        # Verify difficulty distribution
        diff_dist = qs_result["difficulty_distribution"]
        assert "mean_difficulty" in diff_dist
        assert "difficulty_buckets" in diff_dist
        assert len(diff_dist["difficulty_buckets"]) == 6

        # Verify sequence analysis
        seq = qs_result["selection_sequence"]
        assert "mean_difficulty_delta_after_correct" in seq
        assert "adaptive_responsiveness_status" in seq

        print("  TASK-034 Question Selection Evaluation passed all checks.")

        # 4. Test TASK-035: Ability Estimation Quality Evaluation
        print("\n[4] Testing AbilityEstimationEvaluator (TASK-035)...")
        ae_evaluator = AbilityEstimationEvaluator(
            eval_repo=eval_repo,
            sim_repo=sim_repo,
        )

        ae_result = await ae_evaluator.evaluate_simulation_runs([sim_run.id])
        assert ae_result["status"] == "COMPLETED"
        assert ae_result["eligible_sessions_count"] == 10
        assert ae_result["excluded_sessions_count"] == 0

        ae_summary = ae_result["summary_metrics"]
        print("  Ability Estimation Summary Metrics:")
        print(f"    - Overall MAE:  {ae_summary['overall_mae']}")
        print(f"    - Overall RMSE: {ae_summary['overall_rmse']}")
        print(f"    - Overall Bias: {ae_summary['overall_bias_formatted']}")

        print("\n  Dimensional Table (Matching User Mockup):")
        print("    " + "-" * 55)
        print(f"    {'Dimension':<18} | {'MAE':<6} | {'RMSE':<6} | {'Bias':<8}")
        print("    " + "-" * 55)
        for row in ae_summary["dimensional_table"]:
            print(f"    {row['dimension']:<18} | {row['mae']:<6} | {row['rmse']:<6} | {row['bias_formatted']:<8}")
            assert row["mae"] >= 0.0
            assert row["rmse"] >= 0.0
        print("    " + "-" * 55)

        # Verify uncertainty calibration
        unc_res = ae_result["uncertainty_analysis"]
        assert "calibration_buckets" in unc_res
        assert len(unc_res["calibration_buckets"]) == 3
        print(f"    Uncertainty-Error Correlation: {unc_res['uncertainty_error_correlation']} ({unc_res['correlation_interpretation']})")

        # Verify length vs quality
        len_q = ae_result["length_vs_quality"]
        assert "question_count_intervals" in len_q

        # Verify archetype breakdowns
        arch_bd = ae_result["archetype_breakdowns"]
        for arch_name in [ArchetypeType.BALANCED.value, ArchetypeType.STRONG.value]:
            if arch_name in arch_bd:
                assert "mae" in arch_bd[arch_name]
                assert "rmse" in arch_bd[arch_name]

        print("  TASK-035 Ability Estimation Quality Evaluation passed all checks.")

        # 5. Verify Persistence & Retrieval
        print("\n[5] Testing Database Persistence & Retrieval...")
        qs_run_id = qs_result["evaluation_run_id"]
        ae_run_id = ae_result["evaluation_run_id"]

        persisted_qs = await eval_repo.get_evaluation_run(qs_run_id)
        assert persisted_qs is not None
        assert persisted_qs.status == "COMPLETED"
        assert persisted_qs.question_selection_result is not None
        assert persisted_qs.question_selection_result.summary_metrics["dimension_coverage_pct"] == qs_summary["dimension_coverage_pct"]

        persisted_ae = await eval_repo.get_evaluation_run(ae_run_id)
        assert persisted_ae is not None
        assert persisted_ae.status == "COMPLETED"
        assert persisted_ae.ability_estimation_result is not None
        assert persisted_ae.ability_estimation_result.summary_metrics["overall_mae"] == ae_summary["overall_mae"]

        runs_list = await eval_repo.list_evaluation_runs()
        assert len(runs_list) >= 2
        print(f"  Successfully retrieved {len(runs_list)} persisted evaluation runs.")

        # 6. Verify Validation & Incompatible Runs Rejection
        print("\n[6] Testing Validation Guards...")
        # Empty simulation run IDs list
        try:
            await qs_evaluator.evaluate_simulation_runs([])
            assert False, "Should have raised ValueError for empty run IDs"
        except ValueError:
            print("  Empty run IDs rejected as expected.")

        # Non-existent simulation run ID
        try:
            await qs_evaluator.evaluate_simulation_runs(["non-existent-uuid"])
            assert False, "Should have raised ValueError for non-existent run ID"
        except ValueError:
            print("  Non-existent run ID rejected as expected.")

        # 7. Test REST API Endpoints Integration
        print("\n[7] Testing Evaluation REST API Endpoints...")
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        from app.infrastructure.persistence.database import get_db_session
        from app.infrastructure.security.jwt import get_current_user, AuthenticatedUser

        async def override_db():
            yield db

        def override_admin():
            return AuthenticatedUser(user_id="admin-verifier", roles=["ROLE_ADMIN"])

        app.dependency_overrides[get_db_session] = override_db
        app.dependency_overrides[get_current_user] = override_admin

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test POST /api/v1/internal/evaluations/question-selection
            resp_qs = await client.post(
                "/api/v1/internal/evaluations/question-selection",
                json={"simulation_run_ids": [sim_run.id]}
            )
            assert resp_qs.status_code == 201, f"Expected 201, got {resp_qs.status_code}: {resp_qs.text}"
            data_qs = resp_qs.json()
            assert "summary_metrics" in data_qs
            assert "dimension_coverage_pct" in data_qs["summary_metrics"]
            api_qs_run_id = data_qs["evaluation_run_id"]
            print(f"  API POST /question-selection succeeded (run_id: {api_qs_run_id})")

            # Test POST /api/v1/internal/evaluations/ability-estimation
            resp_ae = await client.post(
                "/api/v1/internal/evaluations/ability-estimation",
                json={"simulation_run_ids": [sim_run.id]}
            )
            assert resp_ae.status_code == 201, f"Expected 201, got {resp_ae.status_code}: {resp_ae.text}"
            data_ae = resp_ae.json()
            assert "summary_metrics" in data_ae
            assert "dimensional_table" in data_ae["summary_metrics"]
            api_ae_run_id = data_ae["evaluation_run_id"]
            print(f"  API POST /ability-estimation succeeded (run_id: {api_ae_run_id})")

            # Test GET /api/v1/internal/evaluations/{id}
            resp_get = await client.get(f"/api/v1/internal/evaluations/{api_qs_run_id}")
            assert resp_get.status_code == 200
            assert resp_get.json()["status"] == "COMPLETED"
            print(f"  API GET /evaluations/{api_qs_run_id} succeeded")

            # Test GET /api/v1/internal/evaluations/{id}/results
            resp_results = await client.get(f"/api/v1/internal/evaluations/{api_qs_run_id}/results")
            assert resp_results.status_code == 200
            assert "summary_metrics" in resp_results.json()
            print(f"  API GET /evaluations/{api_qs_run_id}/results succeeded")

            # Test Convenience Route /api/internal/evaluations/question-selection
            resp_root_route = await client.post(
                "/api/internal/evaluations/question-selection",
                json={"simulation_run_ids": [sim_run.id]}
            )
            assert resp_root_route.status_code == 201
            print("  Convenience route /api/internal/evaluations/question-selection succeeded")

        app.dependency_overrides.clear()
        print("  REST API integration verified successfully.")

    print("\n" + "=" * 65)
    print("ALL EVALUATION FRAMEWORK VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_verification())
