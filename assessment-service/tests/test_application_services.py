import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models.profile import (
    AssessmentProfileModel,
    ProfileQuestionAssociationModel,
)
from app.infrastructure.persistence.models.question import (
    QuestionModel,
    QuestionVersionModel,
)
from app.infrastructure.persistence.models.session import (
    AssessmentSessionModel,
    AssessmentResponseModel,
)
from app.infrastructure.persistence.repositories import (
    AssessmentSessionRepository,
    AssessmentProfileRepository,
    QuestionRepository,
    AssessmentResponseRepository,
)
from app.domain.enums import SessionStatus, QuestionVersionStatus
from app.application.dto import (
    StartAssessmentCommand,
    NextQuestionQuery,
    SubmitAnswerCommand,
)
from app.application.services import (
    StartAssessmentService,
    NextQuestionService,
    SubmitAnswerService,
)
from app.application.exceptions import (
    SessionNotFoundError,
    SessionAccessForbiddenError,
    SessionNotActiveError,
    ProfileNotFoundError,
    ProfileInactiveError,
    AgeIncompatibleError,
    QuestionVersionNotFoundError,
    QuestionNotOfferedError,
    DuplicateAnswerError,
    IdempotencyConflictError,
    ApplicationError,
)
from app.engine.exceptions import InvalidAnswerPayloadError, InvalidOptionError


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session():
    """Isolated in-memory SQLite database for application service testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_profile(db_session: AsyncSession):
    """Creates a standard active test profile with target dimensions."""
    profile = AssessmentProfileModel(
        code="TECHNICAL_TALENT_V1",
        title="Technical Talent Diagnostic Profile",
        version=1,
        dimensions=["logical_reasoning", "algorithmic_thinking", "spatial_reasoning"],
        min_age=12,
        max_age=18,
        is_active=True,
    )
    db_session.add(profile)
    await db_session.flush()
    return profile


@pytest_asyncio.fixture
async def seeded_questions(db_session: AsyncSession, seeded_profile: AssessmentProfileModel):
    """Seeds 5 sample questions associated with the test profile."""
    questions = []
    for i in range(1, 6):
        dim = seeded_profile.dimensions[(i - 1) % len(seeded_profile.dimensions)]
        q = QuestionModel(code=f"Q-TEST-{i:03d}", question_type="MULTIPLE_CHOICE", is_active=True)
        db_session.add(q)
        await db_session.flush()

        v = QuestionVersionModel(
            question_id=q.id,
            version=1,
            status=QuestionVersionStatus.PUBLISHED.value,
            content=f"What is the answer to question {i}?",
            question_type="MULTIPLE_CHOICE",
            options=[
                {"key": "A", "text": "Option A"},
                {"key": "B", "text": "Option B"},
                {"key": "C", "text": "Option C"},
                {"key": "D", "text": "Option D"},
            ],
            correct_answer="B",
            difficulty=0.1 * i,
            discrimination=1.0,
            guessing=0.25,
            min_age=12,
            max_age=18,
            estimated_time=45,
            dimensions={dim: 1.0},
        )
        db_session.add(v)
        await db_session.flush()

        assoc = ProfileQuestionAssociationModel(
            profile_id=seeded_profile.id,
            question_id=q.id,
            is_active=True,
        )
        db_session.add(assoc)
        questions.append((q, v))

    await db_session.flush()
    return questions


# ---------------------------------------------------------------------------
# TASK-025: START ASSESSMENT SERVICE TESTS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_assessment_success(db_session: AsyncSession, seeded_profile: AssessmentProfileModel):
    service = StartAssessmentService(db_session)
    cmd = StartAssessmentCommand(
        student_id="student-100",
        student_age=15,
        profile_code=seeded_profile.code,
    )
    result = await service.execute(cmd)

    assert result.session_id is not None
    assert result.student_id == "student-100"
    assert result.student_age == 15
    assert result.profile_code == seeded_profile.code
    assert result.status == SessionStatus.IN_PROGRESS.value
    assert len(result.initial_scores) == len(seeded_profile.dimensions)
    for dim in seeded_profile.dimensions:
        assert dim in result.initial_scores
        assert dim in result.initial_uncertainty
        assert result.initial_uncertainty[dim] == 1.0


@pytest.mark.asyncio
async def test_start_assessment_unauthenticated(db_session: AsyncSession, seeded_profile: AssessmentProfileModel):
    service = StartAssessmentService(db_session)
    cmd = StartAssessmentCommand(
        student_id="   ",  # blank
        student_age=15,
        profile_code=seeded_profile.code,
    )
    with pytest.raises(ApplicationError, match="authenticated"):
        await service.execute(cmd)


@pytest.mark.asyncio
async def test_start_assessment_profile_not_found(db_session: AsyncSession):
    service = StartAssessmentService(db_session)
    cmd = StartAssessmentCommand(
        student_id="student-100",
        student_age=15,
        profile_code="NON_EXISTENT_PROFILE",
    )
    with pytest.raises(ProfileNotFoundError):
        await service.execute(cmd)


@pytest.mark.asyncio
async def test_start_assessment_profile_inactive(db_session: AsyncSession):
    inactive = AssessmentProfileModel(
        code="INACTIVE_PROF",
        title="Inactive Profile",
        version=1,
        dimensions=["logical_reasoning"],
        min_age=10,
        max_age=18,
        is_active=False,
    )
    db_session.add(inactive)
    await db_session.flush()

    service = StartAssessmentService(db_session)
    cmd = StartAssessmentCommand(
        student_id="student-100",
        student_age=14,
        profile_code="INACTIVE_PROF",
    )
    with pytest.raises(ProfileInactiveError):
        await service.execute(cmd)


@pytest.mark.asyncio
async def test_start_assessment_age_incompatible(db_session: AsyncSession, seeded_profile: AssessmentProfileModel):
    service = StartAssessmentService(db_session)
    # Profile min_age is 12, max_age is 18
    cmd_too_young = StartAssessmentCommand(
        student_id="student-100",
        student_age=9,
        profile_code=seeded_profile.code,
    )
    with pytest.raises(AgeIncompatibleError, match="outside the allowed age range"):
        await service.execute(cmd_too_young)

    cmd_too_old = StartAssessmentCommand(
        student_id="student-100",
        student_age=25,
        profile_code=seeded_profile.code,
    )
    with pytest.raises(AgeIncompatibleError):
        await service.execute(cmd_too_old)


# ---------------------------------------------------------------------------
# TASK-026: NEXT QUESTION SERVICE TESTS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_next_question_success_and_sanitization(
    db_session: AsyncSession,
    seeded_profile: AssessmentProfileModel,
    seeded_questions,
):
    # 1. Start assessment
    start_service = StartAssessmentService(db_session)
    start_res = await start_service.execute(
        StartAssessmentCommand(
            student_id="student-100",
            student_age=15,
            profile_code=seeded_profile.code,
        )
    )

    # 2. Query next question
    next_service = NextQuestionService(db_session)
    res = await next_service.execute(NextQuestionQuery(
        session_id=start_res.session_id,
        student_id="student-100",
    ))

    assert not res.should_stop
    assert res.question is not None
    assert res.question.question_id in [q.id for q, _ in seeded_questions]
    assert len(res.question.options) == 4
    # Ensure correct_answer is strictly NOT exposed in public question representation
    assert not hasattr(res.question, "correct_answer")
    assert not hasattr(res.question.options[0], "is_correct")
    assert res.question.sequence_number == 1


@pytest.mark.asyncio
async def test_next_question_forbidden_for_other_student(
    db_session: AsyncSession,
    seeded_profile: AssessmentProfileModel,
    seeded_questions,
):
    start_service = StartAssessmentService(db_session)
    start_res = await start_service.execute(
        StartAssessmentCommand(
            student_id="student-100",
            student_age=15,
            profile_code=seeded_profile.code,
        )
    )

    next_service = NextQuestionService(db_session)
    with pytest.raises(SessionAccessForbiddenError):
        await next_service.execute(NextQuestionQuery(
            session_id=start_res.session_id,
            student_id="intruder-999",
        ))


@pytest.mark.asyncio
async def test_next_question_session_not_found(db_session: AsyncSession):
    next_service = NextQuestionService(db_session)
    with pytest.raises(SessionNotFoundError):
        await next_service.execute(NextQuestionQuery(
            session_id="non-existent-uuid",
            student_id="student-100",
        ))


@pytest.mark.asyncio
async def test_next_question_session_not_active(
    db_session: AsyncSession,
    seeded_profile: AssessmentProfileModel,
    seeded_questions,
):
    start_service = StartAssessmentService(db_session)
    start_res = await start_service.execute(
        StartAssessmentCommand(
            student_id="student-100",
            student_age=15,
            profile_code=seeded_profile.code,
        )
    )

    # Transition session to COMPLETED
    session_repo = AssessmentSessionRepository(db_session)
    await session_repo.update_status(start_res.session_id, SessionStatus.COMPLETED)

    next_service = NextQuestionService(db_session)
    with pytest.raises(SessionNotActiveError, match="not in progress"):
        await next_service.execute(NextQuestionQuery(
            session_id=start_res.session_id,
            student_id="student-100",
        ))


# ---------------------------------------------------------------------------
# TASK-027: SUBMIT ANSWER SERVICE TESTS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_answer_correct_and_incorrect(
    db_session: AsyncSession,
    seeded_profile: AssessmentProfileModel,
    seeded_questions,
):
    start_service = StartAssessmentService(db_session)
    start_res = await start_service.execute(
        StartAssessmentCommand(
            student_id="student-100",
            student_age=15,
            profile_code=seeded_profile.code,
        )
    )

    next_service = NextQuestionService(db_session)
    q1 = await next_service.execute(NextQuestionQuery(
        session_id=start_res.session_id,
        student_id="student-100",
    ))

    submit_service = SubmitAnswerService(db_session)

    # 1. Submit Correct Answer ("B" is correct)
    sub1 = await submit_service.execute(SubmitAnswerCommand(
        session_id=start_res.session_id,
        student_id="student-100",
        question_version_id=q1.question.question_version_id,
        answer={"selected_option": "B"},
        response_time_ms=12000,
        idempotency_key="idemp-key-001",
    ))

    assert sub1.is_correct is True
    assert sub1.score == 1.0
    assert sub1.is_retry is False
    assert sub1.response_count == 1
    # Ensure correct answer is not leaked in output DTO
    assert not hasattr(sub1, "correct_answer")

    # 2. Get Next Question
    q2 = await next_service.execute(NextQuestionQuery(
        session_id=start_res.session_id,
        student_id="student-100",
    ))
    assert q2.question.question_id != q1.question.question_id

    # 3. Submit Incorrect Answer ("C" is wrong)
    sub2 = await submit_service.execute(SubmitAnswerCommand(
        session_id=start_res.session_id,
        student_id="student-100",
        question_version_id=q2.question.question_version_id,
        answer={"selected_option": "C"},
        response_time_ms=8500,
        idempotency_key="idemp-key-002",
    ))

    assert sub2.is_correct is False
    assert sub2.score == 0.0
    assert sub2.response_count == 2


@pytest.mark.asyncio
async def test_submit_answer_idempotent_retry(
    db_session: AsyncSession,
    seeded_profile: AssessmentProfileModel,
    seeded_questions,
):
    start_service = StartAssessmentService(db_session)
    start_res = await start_service.execute(
        StartAssessmentCommand(
            student_id="student-100",
            student_age=15,
            profile_code=seeded_profile.code,
        )
    )

    next_service = NextQuestionService(db_session)
    q1 = await next_service.execute(NextQuestionQuery(
        session_id=start_res.session_id,
        student_id="student-100",
    ))

    submit_service = SubmitAnswerService(db_session)

    cmd = SubmitAnswerCommand(
        session_id=start_res.session_id,
        student_id="student-100",
        question_version_id=q1.question.question_version_id,
        answer={"selected_option": "B"},
        response_time_ms=12000,
        idempotency_key="idemp-unique-123",
    )

    # First attempt
    res1 = await submit_service.execute(cmd)
    assert res1.is_retry is False

    # Second identical attempt (Retry)
    res2 = await submit_service.execute(cmd)
    assert res2.is_retry is True
    assert res2.response_id == res1.response_id
    assert res2.is_correct == res1.is_correct

    # Verify only ONE response is saved in database
    resp_repo = AssessmentResponseRepository(db_session)
    count = await resp_repo.count_by_session(start_res.session_id)
    assert count == 1


@pytest.mark.asyncio
async def test_submit_answer_idempotency_conflict(
    db_session: AsyncSession,
    seeded_profile: AssessmentProfileModel,
    seeded_questions,
):
    start_service = StartAssessmentService(db_session)
    start_res = await start_service.execute(
        StartAssessmentCommand(
            student_id="student-100",
            student_age=15,
            profile_code=seeded_profile.code,
        )
    )

    next_service = NextQuestionService(db_session)
    q1 = await next_service.execute(NextQuestionQuery(
        session_id=start_res.session_id,
        student_id="student-100",
    ))

    submit_service = SubmitAnswerService(db_session)

    # First attempt with Option B
    await submit_service.execute(SubmitAnswerCommand(
        session_id=start_res.session_id,
        student_id="student-100",
        question_version_id=q1.question.question_version_id,
        answer={"selected_option": "B"},
        response_time_ms=12000,
        idempotency_key="idemp-conflict-test",
    ))

    # Second attempt with same key but DIFFERENT answer (Option A)
    with pytest.raises(IdempotencyConflictError):
        await submit_service.execute(SubmitAnswerCommand(
            session_id=start_res.session_id,
            student_id="student-100",
            question_version_id=q1.question.question_version_id,
            answer={"selected_option": "A"},
            response_time_ms=12000,
            idempotency_key="idemp-conflict-test",
        ))


@pytest.mark.asyncio
async def test_submit_answer_duplicate_question(
    db_session: AsyncSession,
    seeded_profile: AssessmentProfileModel,
    seeded_questions,
):
    start_service = StartAssessmentService(db_session)
    start_res = await start_service.execute(
        StartAssessmentCommand(
            student_id="student-100",
            student_age=15,
            profile_code=seeded_profile.code,
        )
    )

    next_service = NextQuestionService(db_session)
    q1 = await next_service.execute(NextQuestionQuery(
        session_id=start_res.session_id,
        student_id="student-100",
    ))

    submit_service = SubmitAnswerService(db_session)

    # Answer question with key 1
    await submit_service.execute(SubmitAnswerCommand(
        session_id=start_res.session_id,
        student_id="student-100",
        question_version_id=q1.question.question_version_id,
        answer={"selected_option": "B"},
        response_time_ms=10000,
        idempotency_key="key-001",
    ))

    # Try answering the SAME question again with key 2
    with pytest.raises(DuplicateAnswerError):
        await submit_service.execute(SubmitAnswerCommand(
            session_id=start_res.session_id,
            student_id="student-100",
            question_version_id=q1.question.question_version_id,
            answer={"selected_option": "C"},
            response_time_ms=10000,
            idempotency_key="key-002",
        ))


@pytest.mark.asyncio
async def test_submit_answer_question_not_offered(
    db_session: AsyncSession,
    seeded_profile: AssessmentProfileModel,
    seeded_questions,
):
    start_service = StartAssessmentService(db_session)
    start_res = await start_service.execute(
        StartAssessmentCommand(
            student_id="student-100",
            student_age=15,
            profile_code=seeded_profile.code,
        )
    )

    # Get Q1 presented
    next_service = NextQuestionService(db_session)
    q1 = await next_service.execute(NextQuestionQuery(
        session_id=start_res.session_id,
        student_id="student-100",
    ))

    # Pick an arbitrary un-presented question version from seeded questions
    all_version_ids = [v.id for _, v in seeded_questions]
    unpresented_version_id = next(vid for vid in all_version_ids if vid != q1.question.question_version_id)

    submit_service = SubmitAnswerService(db_session)
    with pytest.raises(QuestionNotOfferedError):
        await submit_service.execute(SubmitAnswerCommand(
            session_id=start_res.session_id,
            student_id="student-100",
            question_version_id=unpresented_version_id,
            answer={"selected_option": "B"},
            response_time_ms=5000,
            idempotency_key="key-unoffered",
        ))


# ---------------------------------------------------------------------------
# TASK-025 - TASK-027: INTEGRATION LIFECYCLE LOOP
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_assessment_lifecycle_flow(
    db_session: AsyncSession,
    seeded_profile: AssessmentProfileModel,
    seeded_questions,
):
    """
    End-to-End integration test covering Start -> Next -> Answer -> Ability Update -> Next -> Termination.
    """
    start_service = StartAssessmentService(db_session)
    next_service = NextQuestionService(db_session)
    submit_service = SubmitAnswerService(db_session)

    # 1. Start Assessment
    start = await start_service.execute(StartAssessmentCommand(
        student_id="student-lifecycle",
        student_age=14,
        profile_code=seeded_profile.code,
    ))
    session_id = start.session_id

    seen_question_ids = set()

    # 2. Iterate through 3 questions
    for step in range(1, 4):
        # Fetch next question
        next_q = await next_service.execute(NextQuestionQuery(
            session_id=session_id,
            student_id="student-lifecycle",
        ))
        assert not next_q.should_stop
        assert next_q.question is not None
        assert next_q.question.question_id not in seen_question_ids
        seen_question_ids.add(next_q.question.question_id)

        # Submit answer
        ans = await submit_service.execute(SubmitAnswerCommand(
            session_id=session_id,
            student_id="student-lifecycle",
            question_version_id=next_q.question.question_version_id,
            answer={"selected_option": "B"},
            response_time_ms=10000,
            idempotency_key=f"lifecycle-key-{step}",
        ))
        assert ans.is_correct is True
        assert ans.response_count == step

    # 3. Verify Session Context and History Snapshot
    session_repo = AssessmentSessionRepository(db_session)
    session = await session_repo.get_session_with_responses(session_id)
    assert len(session.responses) == 3

    meta = session.context_metadata
    history = meta.get("ability_history", [])
    assert len(history) == 4  # step 0 (initial) + 3 responses
    assert history[0]["step"] == 0
    assert history[3]["step"] == 3

    # Check uncertainty decreased as evidence accumulated
    init_unc = history[0]["uncertainty"]["logical_reasoning"]
    step3_unc = history[3]["uncertainty"]["logical_reasoning"]
    assert step3_unc <= init_unc
