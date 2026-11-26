import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.domain.enums import (
    CognitiveDimension,
    QuestionType,
    QuestionVersionStatus,
    CalibrationStatus
)
from app.domain.dimensions import (
    DimensionsVector,
    normalize_dimension_code,
    DIMENSION_REGISTRY
)
from app.domain.question import (
    validate_options,
    validate_correct_answer,
    validate_psychometrics,
    validate_age_range,
    validate_estimated_time,
    validate_exposure_limit,
    Option
)
from app.domain.profile import (
    validate_profile_code,
    validate_profile_dimensions,
    check_compatibility
)
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.question import QuestionModel, QuestionVersionModel
from app.infrastructure.persistence.models.profile import AssessmentProfileModel, ProfileQuestionAssociationModel
from app.api.v1.schemas.questions import (
    CreateQuestionVersionInput,
    QuestionVersionPublicSchema,
    QuestionVersionAdminSchema
)

# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def async_db_session():
    """Provides an isolated in-memory SQLite database for ORM integration testing."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()

# ---------------------------------------------------------------------------
# TASK-011: DIMENSIONS & DIMENSIONS VECTOR TESTS
# ---------------------------------------------------------------------------

def test_dimensions_registry_and_normalization():
    assert len(DIMENSION_REGISTRY) == 5
    assert normalize_dimension_code("logical_reasoning") == "logical_reasoning"
    assert normalize_dimension_code("LOGICAL_REASONING") == "logical_reasoning"
    assert normalize_dimension_code("Algorithmic_Thinking") == "algorithmic_thinking"

    with pytest.raises(ValueError, match="Unrecognized cognitive dimension code"):
        normalize_dimension_code("invalid_dimension_code")

def test_dimensions_vector_valid():
    raw = {
        "logical_reasoning": 0.85,
        "algorithmic_thinking": 0.6,
        "problem_solving": 0.4,
        "spatial_reasoning": 0.0,
        "computational_thinking": 0.1
    }
    vec = DimensionsVector(weights=raw)
    assert vec.get_weight("logical_reasoning") == 0.85
    assert vec.get_weight("spatial_reasoning") == 0.0
    assert vec.get_weight("non_existent") == 0.0
    assert vec.dominant_dimension() == "logical_reasoning"
    assert "spatial_reasoning" not in vec.get_active_dimensions()
    assert "logical_reasoning" in vec.get_active_dimensions()

def test_dimensions_vector_case_insensitivity():
    raw = {"LOGICAL_REASONING": 0.9, "PROBLEM_SOLVING": 0.5}
    vec = DimensionsVector(weights=raw)
    assert vec.get_weight("logical_reasoning") == 0.9
    assert vec.get_weight("problem_solving") == 0.5

def test_dimensions_vector_invalid_bounds():
    with pytest.raises(ValueError, match="must be in"):
        DimensionsVector(weights={"logical_reasoning": 1.5})

    with pytest.raises(ValueError, match="must be in"):
        DimensionsVector(weights={"logical_reasoning": -0.1})

def test_dimensions_vector_empty_fails():
    with pytest.raises(ValueError, match="cannot be empty"):
        DimensionsVector(weights={})

# ---------------------------------------------------------------------------
# TASK-012 & TASK-013: QUESTION & QUESTION VERSION VALIDATION TESTS
# ---------------------------------------------------------------------------

def test_options_validation():
    valid_opts = [
        {"key": "A", "text": "Choice A", "order": 1},
        {"key": "B", "text": "Choice B", "order": 2},
        {"key": "C", "text": "Choice C", "order": 3},
        {"key": "D", "text": "Choice D", "order": 4},
    ]
    parsed = validate_options(valid_opts)
    assert len(parsed) == 4
    assert parsed[0].key == "A"
    assert parsed[1].text == "Choice B"

    # Duplicate key
    with pytest.raises(ValueError, match="Duplicate option key"):
        validate_options([
            {"key": "A", "text": "Choice 1"},
            {"key": "A", "text": "Choice 2"}
        ])

    # Less than 2 options
    with pytest.raises(ValueError, match="at least 2 options"):
        validate_options([{"key": "A", "text": "Only one"}])

def test_correct_answer_validation():
    opts = [
        Option(key="A", text="Choice A", order=1),
        Option(key="B", text="Choice B", order=2)
    ]
    assert validate_correct_answer("a", opts) == "A"
    assert validate_correct_answer("B", opts) == "B"

    with pytest.raises(ValueError, match="is not in valid option keys"):
        validate_correct_answer("C", opts)

def test_psychometrics_validation():
    # Valid parameters
    res = validate_psychometrics(difficulty=1.2, discrimination=1.5, guessing=0.25)
    assert res["difficulty"] == 1.2
    assert res["discrimination"] == 1.5
    assert res["guessing"] == 0.25

    # Out of bounds
    with pytest.raises(ValueError, match="Difficulty"):
        validate_psychometrics(difficulty=5.0, discrimination=1.0, guessing=0.25)

    with pytest.raises(ValueError, match="Discrimination"):
        validate_psychometrics(difficulty=0.0, discrimination=-0.5, guessing=0.25)

    with pytest.raises(ValueError, match="Guessing"):
        validate_psychometrics(difficulty=0.0, discrimination=1.0, guessing=1.0)

def test_age_range_validation():
    res = validate_age_range(10, 18)
    assert res["min_age"] == 10
    assert res["max_age"] == 18

    with pytest.raises(ValueError, match="cannot be greater than"):
        validate_age_range(18, 10)

    with pytest.raises(ValueError, match="min_age must be >= 1"):
        validate_age_range(0, 10)

def test_security_schema_excludes_correct_answer():
    input_data = {
        "content": "What is 2+2?",
        "options": [
            {"key": "A", "text": "3", "order": 1},
            {"key": "B", "text": "4", "order": 2}
        ],
        "correct_answer": "B",
        "difficulty": 0.5,
        "discrimination": 1.2,
        "guessing": 0.5,
        "min_age": 8,
        "max_age": 14,
        "estimated_time": 45,
        "dimensions": {"logical_reasoning": 0.9}
    }
    validated = CreateQuestionVersionInput(**input_data)
    assert validated.correct_answer == "B"

    # Verify public schema serialization hides correct_answer
    public_dto = QuestionVersionPublicSchema(
        id=1,
        question_id=10,
        version=1,
        status=QuestionVersionStatus.PUBLISHED,
        content=validated.content,
        options=[{"key": opt["key"], "text": opt["text"], "order": opt["order"]} for opt in validated.options],
        min_age=validated.min_age,
        max_age=validated.max_age,
        estimated_time=validated.estimated_time,
        dimensions=validated.dimensions
    )
    public_dict = public_dto.model_dump()
    assert "correct_answer" not in public_dict
    assert "difficulty" not in public_dict

# ---------------------------------------------------------------------------
# TASK-014: ASSESSMENT PROFILE TESTS
# ---------------------------------------------------------------------------

def test_profile_validation():
    code = validate_profile_code("technical_talent_v1")
    assert code == "TECHNICAL_TALENT_V1"

    dims = validate_profile_dimensions(["LOGICAL_REASONING", "algorithmic_thinking"])
    assert dims == ["logical_reasoning", "algorithmic_thinking"]

def test_profile_question_compatibility():
    profile_dims = ["logical_reasoning", "problem_solving"]
    q_vec_compatible = DimensionsVector(weights={"logical_reasoning": 0.8, "spatial_reasoning": 0.2})
    q_vec_incompatible = DimensionsVector(weights={"spatial_reasoning": 0.9})

    # 1. Compatible
    ok, err = check_compatibility(
        profile_dimensions=profile_dims,
        profile_min_age=10,
        profile_max_age=16,
        question_dimensions=q_vec_compatible,
        question_min_age=12,
        question_max_age=15
    )
    assert ok is True
    assert err is None

    # 2. Dimension Mismatch
    ok, err = check_compatibility(
        profile_dimensions=profile_dims,
        profile_min_age=10,
        profile_max_age=16,
        question_dimensions=q_vec_incompatible,
        question_min_age=10,
        question_max_age=16
    )
    assert ok is False
    assert "Dimension mismatch" in err

    # 3. Age Range Mismatch
    ok, err = check_compatibility(
        profile_dimensions=profile_dims,
        profile_min_age=10,
        profile_max_age=14,
        question_dimensions=q_vec_compatible,
        question_min_age=15,
        question_max_age=18
    )
    assert ok is False
    assert "Age range mismatch" in err

# ---------------------------------------------------------------------------
# ORM & DATABASE PERSISTENCE TESTS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orm_question_and_versions_lifecycle(async_db_session: AsyncSession):
    # 1. Create Question
    q = QuestionModel(code="Q-LOG-001", is_active=True)
    async_db_session.add(q)
    await async_db_session.commit()
    await async_db_session.refresh(q)
    assert q.id is not None
    assert q.code == "Q-LOG-001"

    # 2. Add QuestionVersion 1
    v1 = QuestionVersionModel(
        question_id=q.id,
        version=1,
        status=QuestionVersionStatus.PUBLISHED.value,
        content="What is the next number: 2, 4, 8, ...?",
        options=[
            {"key": "A", "text": "10", "order": 1},
            {"key": "B", "text": "16", "order": 2}
        ],
        correct_answer="B",
        difficulty=0.2,
        discrimination=1.1,
        guessing=0.5,
        min_age=10,
        max_age=18,
        estimated_time=45,
        dimensions={"logical_reasoning": 0.8, "algorithmic_thinking": 0.4},
        calibration_status=CalibrationStatus.CALIBRATED.value
    )
    async_db_session.add(v1)
    await async_db_session.commit()

    # 3. Add QuestionVersion 2
    v2 = QuestionVersionModel(
        question_id=q.id,
        version=2,
        status=QuestionVersionStatus.PUBLISHED.value,
        content="What is the next number: 2, 4, 8, ... (revised text)?",
        options=[
            {"key": "A", "text": "12", "order": 1},
            {"key": "B", "text": "16", "order": 2}
        ],
        correct_answer="B",
        difficulty=0.3,
        discrimination=1.2,
        guessing=0.5,
        min_age=10,
        max_age=18,
        estimated_time=45,
        dimensions={"logical_reasoning": 0.85, "algorithmic_thinking": 0.45},
        calibration_status=CalibrationStatus.CALIBRATED.value
    )
    async_db_session.add(v2)
    await async_db_session.commit()

    # Refresh question and test version access
    await async_db_session.refresh(q)
    assert len(q.versions) == 2
    latest = q.get_latest_version()
    assert latest is not None
    assert latest.version == 2
    assert "revised" in latest.content

@pytest.mark.asyncio
async def test_orm_version_uniqueness_constraint(async_db_session: AsyncSession):
    q = QuestionModel(code="Q-ALG-002", is_active=True)
    async_db_session.add(q)
    await async_db_session.commit()
    await async_db_session.refresh(q)

    v1a = QuestionVersionModel(
        question_id=q.id,
        version=1,
        content="Version 1A",
        options=[{"key": "A", "text": "A", "order": 1}, {"key": "B", "text": "B", "order": 2}],
        correct_answer="A",
        dimensions={"algorithmic_thinking": 1.0}
    )
    async_db_session.add(v1a)
    await async_db_session.commit()

    # Try inserting another version 1 for the same question
    v1b = QuestionVersionModel(
        question_id=q.id,
        version=1,
        content="Version 1B Duplicate",
        options=[{"key": "A", "text": "A", "order": 1}, {"key": "B", "text": "B", "order": 2}],
        correct_answer="A",
        dimensions={"algorithmic_thinking": 1.0}
    )
    async_db_session.add(v1b)
    with pytest.raises(IntegrityError):
        await async_db_session.commit()
    await async_db_session.rollback()

@pytest.mark.asyncio
async def test_orm_profile_and_question_bank_association(async_db_session: AsyncSession):
    # 1. Create Profile
    profile = AssessmentProfileModel(
        code="TECHNICAL_TALENT_V1",
        title="Technical & Cognitive Talent",
        version=1,
        dimensions=["logical_reasoning", "algorithmic_thinking", "problem_solving"],
        min_age=10,
        max_age=18,
        is_active=True
    )
    async_db_session.add(profile)

    # 2. Create Question
    q = QuestionModel(code="Q-PRB-001", is_active=True)
    async_db_session.add(q)
    await async_db_session.commit()
    await async_db_session.refresh(profile)
    await async_db_session.refresh(q)

    # 3. Associate Question with Profile
    assoc = ProfileQuestionAssociationModel(
        profile_id=profile.id,
        question_id=q.id,
        is_active=True
    )
    async_db_session.add(assoc)
    await async_db_session.commit()

    # 4. Query questions for profile
    stmt = (
        select(QuestionModel)
        .join(ProfileQuestionAssociationModel)
        .where(ProfileQuestionAssociationModel.profile_id == profile.id)
    )
    result = await async_db_session.execute(stmt)
    questions_for_profile = result.scalars().all()
    assert len(questions_for_profile) == 1
    assert questions_for_profile[0].code == "Q-PRB-001"
