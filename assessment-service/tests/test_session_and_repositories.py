import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.domain.enums import SessionStatus, QuestionType, QuestionVersionStatus, CalibrationStatus
from app.domain.session import (
    validate_session_transition,
    validate_answer_payload,
    evaluate_answer_correctness,
    validate_response_time,
    validate_idempotency_key
)
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.question import QuestionModel, QuestionVersionModel
from app.infrastructure.persistence.models.profile import AssessmentProfileModel
from app.infrastructure.persistence.models.session import AssessmentSessionModel, AssessmentResponseModel
from app.infrastructure.persistence.repositories import (
    QuestionRepository,
    AssessmentProfileRepository,
    AssessmentSessionRepository,
    AssessmentResponseRepository
)

# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def async_db_session():
    """Isolated in-memory SQLite database for session and repository testing."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# ---------------------------------------------------------------------------
# TASK-015: DOMAIN SESSION & RESPONSE VALIDATION TESTS
# ---------------------------------------------------------------------------

def test_session_state_transitions():
    # Valid transitions
    validate_session_transition(SessionStatus.IN_PROGRESS, SessionStatus.COMPLETED)
    validate_session_transition(SessionStatus.IN_PROGRESS, SessionStatus.ABANDONED)
    validate_session_transition(SessionStatus.IN_PROGRESS, SessionStatus.EXPIRED)
    validate_session_transition(SessionStatus.IN_PROGRESS, SessionStatus.CANCELLED)

    # Illegal transitions: terminal back to IN_PROGRESS
    with pytest.raises(ValueError, match="Illegal session status transition"):
        validate_session_transition(SessionStatus.COMPLETED, SessionStatus.IN_PROGRESS)

    with pytest.raises(ValueError, match="Illegal session status transition"):
        validate_session_transition(SessionStatus.EXPIRED, SessionStatus.IN_PROGRESS)

    with pytest.raises(ValueError, match="Illegal session status transition"):
        validate_session_transition(SessionStatus.ABANDONED, SessionStatus.IN_PROGRESS)

    with pytest.raises(ValueError, match="Illegal session status transition"):
        validate_session_transition(SessionStatus.CANCELLED, SessionStatus.IN_PROGRESS)

def test_validate_answer_payload():
    assert validate_answer_payload({"selected_option": "B"}) == "B"
    assert validate_answer_payload({"selected_option": " c "}) == "C"

    with pytest.raises(ValueError, match="must be a JSON object"):
        validate_answer_payload("not-a-dict")

    with pytest.raises(ValueError, match="non-empty 'selected_option'"):
        validate_answer_payload({"selected_option": ""})

    with pytest.raises(ValueError, match="non-empty 'selected_option'"):
        validate_answer_payload({"wrong_key": "A"})

def test_evaluate_answer_correctness():
    is_correct, score = evaluate_answer_correctness("B", "b")
    assert is_correct is True
    assert score == 1.0

    is_correct, score = evaluate_answer_correctness("A", "C")
    assert is_correct is False
    assert score == 0.0

def test_validate_response_time():
    assert validate_response_time(1500) == 1500
    assert validate_response_time(0) == 0

    with pytest.raises(ValueError, match="cannot be negative"):
        validate_response_time(-10)

    with pytest.raises(ValueError, match="exceeds maximum"):
        validate_response_time(4_000_000)

    with pytest.raises(ValueError, match="must be an integer"):
        validate_response_time("invalid")

def test_validate_idempotency_key():
    key = "idem-key-12345"
    assert validate_idempotency_key(key) == key

    with pytest.raises(ValueError, match="cannot be empty"):
        validate_idempotency_key("")

    with pytest.raises(ValueError, match="cannot exceed 64"):
        validate_idempotency_key("x" * 65)


# ---------------------------------------------------------------------------
# TASK-015 & TASK-016: PERSISTENCE, CONSTRAINTS & REPOSITORY INTEGRATION TESTS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_session_lifecycle_and_constraints(async_db_session: AsyncSession):
    profile_repo = AssessmentProfileRepository(async_db_session)
    session_repo = AssessmentSessionRepository(async_db_session)

    # 1. Create Profile
    profile = AssessmentProfileModel(
        code="TECHNICAL_TALENT_V1",
        title="Technical & Cognitive Talent",
        version=1,
        dimensions=["logical_reasoning", "algorithmic_thinking"],
        min_age=10,
        max_age=18,
        is_active=True
    )
    await profile_repo.create_profile(profile)

    # 2. Create Session
    session_id = str(uuid.uuid4())
    session = AssessmentSessionModel(
        id=session_id,
        student_id="student-uuid-001",
        student_age=14,
        profile_id=profile.id,
        status=SessionStatus.IN_PROGRESS.value,
        algorithm_version="1.0.0-baseline",
        question_bank_version="1.0.0",
        random_seed=42,
        context_metadata={"locale": "fa"}
    )
    await session_repo.create_session(session)

    # 3. Retrieve Session
    retrieved = await session_repo.get_by_id(session_id)
    assert retrieved is not None
    assert retrieved.student_id == "student-uuid-001"
    assert retrieved.status == SessionStatus.IN_PROGRESS.value
    assert retrieved.profile.code == "TECHNICAL_TALENT_V1"

    # 4. Check active session retrieval
    active = await session_repo.get_active_session("student-uuid-001")
    assert active is not None
    assert active.id == session_id

    # 5. Update Status to COMPLETED
    updated = await session_repo.update_status(session_id, SessionStatus.COMPLETED)
    assert updated.status == SessionStatus.COMPLETED.value
    assert updated.completed_at is not None

    # After completion, active session query returns None
    active_after = await session_repo.get_active_session("student-uuid-001")
    assert active_after is None

    # Cannot revert terminal session
    with pytest.raises(ValueError, match="Illegal session status transition"):
        await session_repo.update_status(session_id, SessionStatus.IN_PROGRESS)


@pytest.mark.asyncio
async def test_session_completed_before_started_constraint(async_db_session: AsyncSession):
    profile = AssessmentProfileModel(
        code="TEST_PROFILE",
        title="Test Profile",
        version=1,
        dimensions=["logical_reasoning"],
        min_age=10,
        max_age=18,
        is_active=True
    )
    async_db_session.add(profile)
    await async_db_session.commit()

    now = datetime.now(timezone.utc)
    earlier = now - timedelta(hours=2)

    invalid_session = AssessmentSessionModel(
        id=str(uuid.uuid4()),
        student_id="student-test",
        student_age=12,
        profile_id=profile.id,
        status=SessionStatus.COMPLETED.value,
        started_at=now,
        completed_at=earlier
    )
    async_db_session.add(invalid_session)
    with pytest.raises(IntegrityError):
        await async_db_session.commit()
    await async_db_session.rollback()


@pytest.mark.asyncio
async def test_response_persistence_and_uniqueness_constraints(async_db_session: AsyncSession):
    profile_repo = AssessmentProfileRepository(async_db_session)
    session_repo = AssessmentSessionRepository(async_db_session)
    question_repo = QuestionRepository(async_db_session)
    response_repo = AssessmentResponseRepository(async_db_session)

    # Setup profile, question and session
    profile = await profile_repo.create_profile(
        AssessmentProfileModel(
            code="TECH_TALENT",
            title="Tech",
            version=1,
            dimensions=["logical_reasoning"],
            min_age=10,
            max_age=18,
            is_active=True
        )
    )
    q = await question_repo.create_question(QuestionModel(code="Q-TEST-01", is_active=True))
    v = await question_repo.create_version(
        QuestionVersionModel(
            question_id=q.id,
            version=1,
            content="Question text",
            options=[{"key": "A", "text": "Opt A", "order": 1}, {"key": "B", "text": "Opt B", "order": 2}],
            correct_answer="A",
            difficulty=0.0,
            discrimination=1.0,
            guessing=0.25,
            dimensions={"logical_reasoning": 1.0}
        )
    )
    session = await session_repo.create_session(
        AssessmentSessionModel(
            id=str(uuid.uuid4()),
            student_id="student-1",
            student_age=15,
            profile_id=profile.id,
            status=SessionStatus.IN_PROGRESS.value
        )
    )

    sess_id = session.id
    qid = q.id
    vid = v.id

    # 1. First Response: Successful insertion
    resp1 = AssessmentResponseModel(
        id=str(uuid.uuid4()),
        session_id=sess_id,
        question_id=qid,
        question_version_id=vid,
        answer={"selected_option": "A"},
        is_correct=True,
        score=1.0,
        response_time_ms=12000,
        idempotency_key="idempotency-key-001"
    )
    await response_repo.create_response(resp1)
    await async_db_session.commit()

    # Verify query by session and question
    fetched = await response_repo.get_by_session_and_question(sess_id, qid)
    assert fetched is not None
    assert fetched.is_correct is True
    assert fetched.score == 1.0

    # Verify query by idempotency key
    fetched_by_key = await response_repo.get_by_idempotency_key(sess_id, "idempotency-key-001")
    assert fetched_by_key is not None
    assert fetched_by_key.id == resp1.id

    # 2. Duplicate Idempotency Key in same session: DB MUST REJECT
    duplicate_idem_resp = AssessmentResponseModel(
        id=str(uuid.uuid4()),
        session_id=sess_id,
        question_id=qid,
        question_version_id=vid,
        answer={"selected_option": "B"},
        is_correct=False,
        score=0.0,
        response_time_ms=5000,
        idempotency_key="idempotency-key-001"  # Same key
    )
    async_db_session.add(duplicate_idem_resp)
    with pytest.raises(IntegrityError):
        await async_db_session.commit()
    await async_db_session.rollback()

    # 3. Duplicate Question in same session (different key): DB MUST REJECT
    duplicate_question_resp = AssessmentResponseModel(
        id=str(uuid.uuid4()),
        session_id=sess_id,
        question_id=qid,  # Same question
        question_version_id=vid,
        answer={"selected_option": "B"},
        is_correct=False,
        score=0.0,
        response_time_ms=5000,
        idempotency_key="different-idempotency-key-999"
    )
    async_db_session.add(duplicate_question_resp)
    with pytest.raises(IntegrityError):
        await async_db_session.commit()
    await async_db_session.rollback()


@pytest.mark.asyncio
async def test_question_repository_filters_and_queries(async_db_session: AsyncSession):
    repo = QuestionRepository(async_db_session)

    # Insert two questions with distinct properties
    q1 = await repo.create_question(QuestionModel(code="Q-FILTER-LOG", is_active=True))
    await repo.create_version(
        QuestionVersionModel(
            question_id=q1.id,
            version=1,
            content="Logic question",
            options=[{"key": "A", "text": "Opt A", "order": 1}, {"key": "B", "text": "Opt B", "order": 2}],
            correct_answer="A",
            difficulty=-0.5,
            dimensions={"logical_reasoning": 0.9, "spatial_reasoning": 0.0}
        )
    )

    q2 = await repo.create_question(QuestionModel(code="Q-FILTER-ALG", is_active=True))
    await repo.create_version(
        QuestionVersionModel(
            question_id=q2.id,
            version=1,
            content="Algorithmic question",
            options=[{"key": "A", "text": "Opt A", "order": 1}, {"key": "B", "text": "Opt B", "order": 2}],
            correct_answer="B",
            difficulty=1.5,
            dimensions={"algorithmic_thinking": 0.85, "problem_solving": 0.6}
        )
    )
    await async_db_session.commit()

    # Filter by dimension
    log_questions = await repo.get_questions_by_dimension("logical_reasoning")
    assert len(log_questions) == 1
    assert log_questions[0].code == "Q-FILTER-LOG"

    alg_questions = await repo.get_questions_by_dimension("algorithmic_thinking")
    assert len(alg_questions) == 1
    assert alg_questions[0].code == "Q-FILTER-ALG"

    # Filter by difficulty bounds
    easy_questions = await repo.get_questions_by_difficulty(-1.0, 0.0)
    assert len(easy_questions) == 1
    assert easy_questions[0].code == "Q-FILTER-LOG"

    hard_questions = await repo.get_questions_by_difficulty(1.0, 2.0)
    assert len(hard_questions) == 1
    assert hard_questions[0].code == "Q-FILTER-ALG"


@pytest.mark.asyncio
async def test_session_repository_queries(async_db_session: AsyncSession):
    profile_repo = AssessmentProfileRepository(async_db_session)
    session_repo = AssessmentSessionRepository(async_db_session)

    profile = await profile_repo.create_profile(
        AssessmentProfileModel(
            code="QUERY_TEST",
            title="Query Test",
            version=1,
            dimensions=["logical_reasoning"],
            min_age=10,
            max_age=18,
            is_active=True
        )
    )

    s1 = await session_repo.create_session(
        AssessmentSessionModel(
            id=str(uuid.uuid4()),
            student_id="student-A",
            student_age=14,
            profile_id=profile.id,
            status=SessionStatus.IN_PROGRESS.value
        )
    )
    s2 = await session_repo.create_session(
        AssessmentSessionModel(
            id=str(uuid.uuid4()),
            student_id="student-A",
            student_age=14,
            profile_id=profile.id,
            status=SessionStatus.COMPLETED.value
        )
    )
    s3 = await session_repo.create_session(
        AssessmentSessionModel(
            id=str(uuid.uuid4()),
            student_id="student-B",
            student_age=16,
            profile_id=profile.id,
            status=SessionStatus.IN_PROGRESS.value
        )
    )
    await async_db_session.commit()

    # Query active sessions
    active_all = await session_repo.get_active_sessions()
    assert len(active_all) == 2

    # Query by student
    student_a_sessions = await session_repo.get_by_student_id("student-A")
    assert len(student_a_sessions) == 2

    # Query with filters
    filtered = await session_repo.query_sessions(student_id="student-A", status=SessionStatus.COMPLETED.value)
    assert len(filtered) == 1
    assert filtered[0].id == s2.id
