import os
import sys
import json
import asyncio
from typing import Dict, Any

# Ensure assessment-service root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from alembic.config import Config
from alembic import command

from app.config import settings
from app.infrastructure.persistence.database import engine, AsyncSessionLocal
from app.infrastructure.persistence.models.question import QuestionModel, QuestionVersionModel
from app.infrastructure.persistence.models.profile import AssessmentProfileModel
from app.infrastructure.persistence.repositories.profile_repo import AssessmentProfileRepository
from app.infrastructure.persistence.repositories.question_repo import QuestionRepository


def run_migrations():
    """Runs Alembic migrations to bring the database to the head revision."""
    print("Running Alembic migrations up to 'head'...")
    alembic_ini_path = os.path.join(BASE_DIR, "alembic.ini")
    alembic_cfg = Config(alembic_ini_path)
    # Ensure alembic script location is absolute
    alembic_cfg.set_main_option("script_location", os.path.join(BASE_DIR, "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    command.upgrade(alembic_cfg, "head")
    print("Alembic migrations completed successfully.")


async def seed_data():
    """Seeds baseline profile, dimensions, and question bank idempotently."""
    print(f"Connecting to database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")

    async with AsyncSessionLocal() as session:
        profile_repo = AssessmentProfileRepository(session)
        question_repo = QuestionRepository(session)

        # -------------------------------------------------------------
        # 1. Seed Assessment Profile: TECHNICAL_TALENT_V1
        # -------------------------------------------------------------
        profile_code = "TECHNICAL_TALENT_V1"
        profile = await profile_repo.get_by_code(profile_code, version=1)
        if not profile:
            print(f"Creating profile '{profile_code}' (v1)...")
            profile = AssessmentProfileModel(
                code=profile_code,
                title="Technical & Cognitive Talent Assessment",
                description=(
                    "MVP profile assessing 5 cognitive dimensions: Logical Reasoning, "
                    "Algorithmic Thinking, Problem Solving, Spatial Reasoning, and Computational Thinking. "
                    "Target: ages 8-18."
                ),
                version=1,
                dimensions=[
                    "logical_reasoning",
                    "algorithmic_thinking",
                    "problem_solving",
                    "spatial_reasoning",
                    "computational_thinking"
                ],
                min_age=8,
                max_age=18,
                is_active=True
            )
            await profile_repo.create_profile(profile)
            await session.commit()
            await session.refresh(profile)
            print(f"Profile '{profile_code}' created with ID {profile.id}.")
        else:
            print(f"Profile '{profile_code}' already exists with ID {profile.id}. Skipping creation.")

        # -------------------------------------------------------------
        # 2. Seed Question Bank (from data/sample_questions.json)
        # -------------------------------------------------------------
        questions_file = os.path.join(BASE_DIR, "data", "sample_questions.json")
        if not os.path.exists(questions_file):
            raise FileNotFoundError(f"Question bank file not found: {questions_file}")

        with open(questions_file, "r", encoding="utf-8") as f:
            bank_data = json.load(f)

        questions_list = bank_data.get("questions", [])
        print(f"Found {len(questions_list)} questions in {questions_file}.")

        created_questions = 0
        created_versions = 0
        associated_count = 0

        for item in questions_list:
            q_code = item["code"]
            q_model = await question_repo.get_by_code(q_code)

            if not q_model:
                q_model = QuestionModel(
                    code=q_code,
                    question_type=item.get("question_type", "MULTIPLE_CHOICE"),
                    is_active=True
                )
                await question_repo.create_question(q_model)
                await session.flush()
                created_questions += 1

            # Check if version 1 exists
            version_num = item.get("version", 1)
            v_model = await question_repo.get_version_by_question_and_num(q_model.id, version_num)

            if not v_model:
                v_model = QuestionVersionModel(
                    question_id=q_model.id,
                    version=version_num,
                    status=item.get("status", "PUBLISHED"),
                    content=item["content"],
                    question_type=item.get("question_type", "MULTIPLE_CHOICE"),
                    options=item["options"],
                    correct_answer=item["correct_answer"],
                    difficulty=item["difficulty"],
                    discrimination=item.get("discrimination", 1.0),
                    guessing=item.get("guessing", 0.25),
                    min_age=item.get("min_age", 10),
                    max_age=item.get("max_age", 18),
                    estimated_time=item.get("estimated_time", 60),
                    dimensions=item["dimensions"],
                    calibration_status=item.get("calibration_status", "UNCALIBRATED"),
                    exposure_limit=item.get("exposure_limit", 100)
                )
                await question_repo.create_version(v_model)
                await session.flush()
                created_versions += 1

            # Associate question with profile
            assoc = await profile_repo.associate_question(profile.id, q_model.id, is_active=True)
            if assoc:
                associated_count += 1

        await session.commit()
        print(f"Seed complete: {created_questions} questions created, {created_versions} versions created, {associated_count} profile associations verified.")

        # -------------------------------------------------------------
        # 3. Verification Report
        # -------------------------------------------------------------
        total_q = await question_repo.count_questions()
        total_v = await question_repo.count_versions()
        active_profiles = await profile_repo.get_active_profiles()

        print("\n" + "=" * 60)
        print("SEED VERIFICATION REPORT")
        print("=" * 60)
        print(f"Total Questions in DB:        {total_q}")
        print(f"Total Question Versions in DB: {total_v}")
        print(f"Active Profiles in DB:         {len(active_profiles)}")
        for p in active_profiles:
            print(f"  - Profile: {p.code} (v{p.version}) - {p.title} (MinAge: {p.min_age}, MaxAge: {p.max_age})")

        # Dimension breakdown
        print("\nQuestions by Dominant Dimension:")
        dim_counts: Dict[str, int] = {}
        all_active_q = await question_repo.get_active_questions(limit=200)
        for q in all_active_q:
            latest = q.get_latest_version()
            if latest and isinstance(latest.dimensions, dict):
                dominant = max(latest.dimensions.items(), key=lambda x: x[1])[0]
                dim_counts[dominant] = dim_counts.get(dominant, 0) + 1

        for dim, count in sorted(dim_counts.items()):
            print(f"  - {dim:<25}: {count} questions")

        print("=" * 60 + "\n")


def main():
    # Step 1: Run migrations
    run_migrations()

    # Step 2: Run async seed
    asyncio.run(seed_data())


if __name__ == "__main__":
    main()
