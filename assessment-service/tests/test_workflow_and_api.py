import pytest
import pytest_asyncio
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.database import get_db_session
from app.infrastructure.security.jwt import get_current_user, AuthenticatedUser
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
from app.application.workflow import AssessmentWorkflowOrchestrator
from app.application.dto import (
    StartAssessmentCommand,
    NextQuestionQuery,
    SubmitAnswerCommand,
)
from app.application.exceptions import (
    SessionNotFoundError,
    SessionAccessForbiddenError,
    SessionNotActiveError,
    ProfileNotFoundError,
    QuestionNotOfferedError,
    DuplicateAnswerError,
    IdempotencyConflictError,
)


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session():
    """In-memory SQLite database session fixture."""
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
async def seeded_data(db_session: AsyncSession):
    """Creates a sample profile and 3 questions for testing."""
    profile = AssessmentProfileModel(
        code="TECHNICAL_TALENT_V1",
        title="Technical Talent Profile",
        version=1,
        dimensions=["logical_reasoning", "algorithmic_thinking", "spatial_reasoning"],
        min_age=10,
        max_age=18,
        is_active=True,
    )
    db_session.add(profile)
    await db_session.flush()

    questions = []
    for i in range(1, 4):
        dim = profile.dimensions[(i - 1) % len(profile.dimensions)]
        q = QuestionModel(code=f"Q-TEST-{i:03d}", question_type="MULTIPLE_CHOICE", is_active=True)
        db_session.add(q)
        await db_session.flush()

        v = QuestionVersionModel(
            question_id=q.id,
            version=1,
            status=QuestionVersionStatus.PUBLISHED.value,
            content=f"Sample question {i} content text",
            question_type="MULTIPLE_CHOICE",
            options=[
                {"key": "A", "text": "Alpha"},
                {"key": "B", "text": "Beta"},
                {"key": "C", "text": "Gamma"},
                {"key": "D", "text": "Delta"},
            ],
            correct_answer="B",
            difficulty=0.2 * i,
            discrimination=1.0,
            guessing=0.25,
            min_age=10,
            max_age=18,
            estimated_time=60,
            dimensions={dim: 1.0},
        )
        db_session.add(v)
        await db_session.flush()

        assoc = ProfileQuestionAssociationModel(
            profile_id=profile.id,
            question_id=q.id,
            is_active=True,
        )
        db_session.add(assoc)
        questions.append((q, v))

    await db_session.flush()
    return profile, questions


# ---------------------------------------------------------------------------
# TASK-028: WORKFLOW ORCHESTRATION TESTS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workflow_orchestrator_full_cycle_and_completion(
    db_session: AsyncSession,
    seeded_data,
):
    profile, questions = seeded_data
    orchestrator = AssessmentWorkflowOrchestrator(db_session)

    # 1. Start Assessment
    start_res = await orchestrator.start_assessment(StartAssessmentCommand(
        student_id="student-orch-01",
        student_age=14,
        profile_code=profile.code,
    ))
    session_id = start_res.session_id
    assert start_res.status == SessionStatus.IN_PROGRESS.value

    # 2. Get initial question
    q1 = await orchestrator.get_next_question(NextQuestionQuery(
        session_id=session_id,
        student_id="student-orch-01",
    ))
    assert not q1.should_stop
    assert q1.question is not None

    # 3. Submit Answer 1
    sub1 = await orchestrator.submit_answer(SubmitAnswerCommand(
        session_id=session_id,
        student_id="student-orch-01",
        question_version_id=q1.question.question_version_id,
        answer={"selected_option": "B"},
        response_time_ms=10000,
        idempotency_key="key-orch-01",
    ))
    assert sub1.is_correct is True

    # 4. Check session summary
    summary = await orchestrator.get_session_summary(session_id, "student-orch-01")
    assert summary.status == SessionStatus.IN_PROGRESS.value
    assert summary.response_count == 1
    assert summary.student_id == "student-orch-01"

    # 5. Answer remaining 2 questions
    q2 = await orchestrator.get_next_question(NextQuestionQuery(session_id=session_id, student_id="student-orch-01"))
    assert not q2.should_stop
    await orchestrator.submit_answer(SubmitAnswerCommand(
        session_id=session_id,
        student_id="student-orch-01",
        question_version_id=q2.question.question_version_id,
        answer={"selected_option": "B"},
        response_time_ms=10000,
        idempotency_key="key-orch-02",
    ))

    q3 = await orchestrator.get_next_question(NextQuestionQuery(session_id=session_id, student_id="student-orch-01"))
    assert not q3.should_stop
    await orchestrator.submit_answer(SubmitAnswerCommand(
        session_id=session_id,
        student_id="student-orch-01",
        question_version_id=q3.question.question_version_id,
        answer={"selected_option": "A"},
        response_time_ms=12000,
        idempotency_key="key-orch-03",
    ))

    # 6. Next question should trigger STOPPING due to question bank exhaustion
    stop_q = await orchestrator.get_next_question(NextQuestionQuery(session_id=session_id, student_id="student-orch-01"))
    assert stop_q.should_stop is True
    assert stop_q.question is None
    assert stop_q.stopping_reason is not None

    # Verify session automatically transitioned to COMPLETED
    completed_summary = await orchestrator.get_session_summary(session_id, "student-orch-01")
    assert completed_summary.status == SessionStatus.COMPLETED.value
    assert completed_summary.completed_at is not None
    assert completed_summary.completion_reason is not None

    # Subsequent attempt to submit on COMPLETED session raises SessionNotActiveError
    with pytest.raises(SessionNotActiveError):
        await orchestrator.submit_answer(SubmitAnswerCommand(
            session_id=session_id,
            student_id="student-orch-01",
            question_version_id=q1.question.question_version_id,
            answer={"selected_option": "B"},
            response_time_ms=5000,
            idempotency_key="key-orch-after-complete",
        ))


@pytest.mark.asyncio
async def test_workflow_orchestrator_abandon(db_session: AsyncSession, seeded_data):
    profile, _ = seeded_data
    orchestrator = AssessmentWorkflowOrchestrator(db_session)

    start_res = await orchestrator.start_assessment(StartAssessmentCommand(
        student_id="student-abandon-01",
        student_age=14,
        profile_code=profile.code,
    ))
    session_id = start_res.session_id

    # Abandon
    abandoned = await orchestrator.abandon_assessment(session_id, "student-abandon-01")
    assert abandoned.status == SessionStatus.ABANDONED.value

    # Next question on abandoned session raises SessionNotActiveError
    with pytest.raises(SessionNotActiveError):
        await orchestrator.get_next_question(NextQuestionQuery(
            session_id=session_id,
            student_id="student-abandon-01",
        ))


# ---------------------------------------------------------------------------
# TASK-029: REST API INTEGRATION TESTS
# ---------------------------------------------------------------------------

@pytest.fixture
def test_client(db_session: AsyncSession):
    """Configures async test client with dependency overrides."""
    current_test_user = {"id": "student-api-01", "roles": ["ROLE_STUDENT"]}

    async def override_get_db():
        yield db_session

    def override_get_current_user():
        return AuthenticatedUser(user_id=current_test_user["id"], roles=current_test_user["roles"])

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    yield client, current_test_user

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_start_assessment(test_client, seeded_data):
    client, user = test_client
    profile, _ = seeded_data

    response = await client.post(
        "/api/v1/assessments/start",
        json={
            "age": 15,
            "profile_code": profile.code,
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert data["student_id"] == user["id"]
    assert data["status"] == "IN_PROGRESS"
    assert "initial_scores" in data


@pytest.mark.asyncio
async def test_api_get_status(test_client, seeded_data):
    client, user = test_client
    profile, _ = seeded_data

    # Start
    start_resp = await client.post("/api/v1/assessments/start", json={"age": 15, "profile_code": profile.code})
    session_id = start_resp.json()["session_id"]

    # Get Status
    status_resp = await client.get(f"/api/v1/assessments/{session_id}")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["session_id"] == session_id
    assert data["status"] == "IN_PROGRESS"
    assert data["response_count"] == 0


@pytest.mark.asyncio
async def test_api_get_next_question_and_answer(test_client, seeded_data):
    client, user = test_client
    profile, questions = seeded_data

    # 1. Start
    start_resp = await client.post("/api/v1/assessments/start", json={"age": 15, "profile_code": profile.code})
    session_id = start_resp.json()["session_id"]

    # 2. Get Next Question
    next_resp = await client.get(f"/api/v1/assessments/{session_id}/next-question")
    assert next_resp.status_code == 200
    next_data = next_resp.json()
    assert next_data["should_stop"] is False
    assert next_data["question"] is not None

    # CRITICAL: Verify correct_answer is NEVER disclosed in API output
    q = next_data["question"]
    assert "correct_answer" not in q
    for opt in q["options"]:
        assert "is_correct" not in opt
        assert "key" in opt
        assert "text" in opt

    q_ver_id = q["question_version_id"]

    # 3. Submit Answer
    ans_resp = await client.post(
        f"/api/v1/assessments/{session_id}/answers",
        json={
            "question_version_id": q_ver_id,
            "answer": {"selected_option": "B"},
            "response_time_ms": 11000,
            "idempotency_key": "api-idemp-001",
        }
    )
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()
    assert ans_data["is_correct"] is True
    assert ans_data["score"] == 1.0
    assert ans_data["is_retry"] is False
    assert "correct_answer" not in ans_data


@pytest.mark.asyncio
async def test_api_idempotency_retry(test_client, seeded_data):
    client, user = test_client
    profile, questions = seeded_data

    start_resp = await client.post("/api/v1/assessments/start", json={"age": 15, "profile_code": profile.code})
    session_id = start_resp.json()["session_id"]

    next_resp = await client.get(f"/api/v1/assessments/{session_id}/next-question")
    q_ver_id = next_resp.json()["question"]["question_version_id"]

    payload = {
        "question_version_id": q_ver_id,
        "answer": {"selected_option": "B"},
        "response_time_ms": 11000,
        "idempotency_key": "api-idemp-unique",
    }

    # Attempt 1
    resp1 = await client.post(f"/api/v1/assessments/{session_id}/answers", json=payload)
    assert resp1.status_code == 200
    assert resp1.json()["is_retry"] is False

    # Attempt 2 (Identical Retry)
    resp2 = await client.post(f"/api/v1/assessments/{session_id}/answers", json=payload)
    assert resp2.status_code == 200
    assert resp2.json()["is_retry"] is True
    assert resp2.json()["response_id"] == resp1.json()["response_id"]


@pytest.mark.asyncio
async def test_api_idempotency_conflict(test_client, seeded_data):
    client, user = test_client
    profile, questions = seeded_data

    start_resp = await client.post("/api/v1/assessments/start", json={"age": 15, "profile_code": profile.code})
    session_id = start_resp.json()["session_id"]

    next_resp = await client.get(f"/api/v1/assessments/{session_id}/next-question")
    q_ver_id = next_resp.json()["question"]["question_version_id"]

    # Attempt 1
    await client.post(
        f"/api/v1/assessments/{session_id}/answers",
        json={
            "question_version_id": q_ver_id,
            "answer": {"selected_option": "B"},
            "response_time_ms": 11000,
            "idempotency_key": "conflict-key",
        }
    )

    # Attempt 2 with conflicting answer
    resp_conflict = await client.post(
        f"/api/v1/assessments/{session_id}/answers",
        json={
            "question_version_id": q_ver_id,
            "answer": {"selected_option": "A"},
            "response_time_ms": 11000,
            "idempotency_key": "conflict-key",
        }
    )
    assert resp_conflict.status_code == 409


@pytest.mark.asyncio
async def test_api_forbidden_access(test_client, seeded_data):
    client, user = test_client
    profile, _ = seeded_data

    start_resp = await client.post("/api/v1/assessments/start", json={"age": 15, "profile_code": profile.code})
    session_id = start_resp.json()["session_id"]

    # Switch user
    user["id"] = "different-attacker"

    resp = await client.get(f"/api/v1/assessments/{session_id}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_api_report_endpoint_session_not_found(test_client):
    client, _ = test_client
    resp = await client.get("/api/v1/assessments/any-uuid/report")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# TASK-030: END-TO-END MULTI-STEP VERIFICATION
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_complete_flow_via_api(test_client, seeded_data):
    """
    Simulates a full end-to-end student assessment session through the REST API:
    1. Start session
    2. Repeatedly fetch next question & submit answer
    3. Detect test completion
    4. Verify session status is COMPLETED
    5. Verify subsequent questions/answers are rejected with 409
    """
    client, user = test_client
    profile, questions = seeded_data

    # Step 1: Start Assessment
    start_resp = await client.post("/api/v1/assessments/start", json={"age": 14, "profile_code": profile.code})
    assert start_resp.status_code == 201
    session_id = start_resp.json()["session_id"]

    answered_count = 0
    while True:
        # Step 2: Next Question
        next_resp = await client.get(f"/api/v1/assessments/{session_id}/next-question")
        assert next_resp.status_code == 200
        next_data = next_resp.json()

        if next_data["should_stop"]:
            assert next_data["stopping_reason"] is not None
            break

        q = next_data["question"]
        answered_count += 1

        # Step 3: Submit Answer
        ans_resp = await client.post(
            f"/api/v1/assessments/{session_id}/answers",
            json={
                "question_version_id": q["question_version_id"],
                "answer": {"selected_option": "B"},
                "response_time_ms": 10000,
                "idempotency_key": f"e2e-idemp-{answered_count}",
            }
        )
        assert ans_resp.status_code == 200

    assert answered_count == len(questions)

    # Step 4: Verify Session is COMPLETED
    status_resp = await client.get(f"/api/v1/assessments/{session_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "COMPLETED"
    assert status_data["completed_at"] is not None
    assert status_data["response_count"] == len(questions)

    # Step 5: Verify subsequent action rejected
    post_complete_resp = await client.get(f"/api/v1/assessments/{session_id}/next-question")
    # Next question on completed session returns 409 Conflict
    assert post_complete_resp.status_code == 409
