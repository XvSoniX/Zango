import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app, CORRELATION_ID_HEADER
from app.config import settings
from app.infrastructure.eureka.client import EurekaClient
from app.engine.protocols import (
    AbilityState,
    ItemParameterSnapshot,
    EvaluationResult,
    StoppingDecision,
    AssessmentContext,
)
from app.domain.enums import CognitiveDimension, SessionStatus

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UP"
        assert "version" in data

@pytest.mark.asyncio
async def test_ready_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")
        # Ready probe checks DB and Eureka; response is either 200 or 503 depending on local DB availability
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data
        assert "details" in data
        assert "database" in data["details"]
        assert "eureka" in data["details"]

@pytest.mark.asyncio
async def test_correlation_id_middleware_generated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert CORRELATION_ID_HEADER in response.headers
        corr_id = response.headers[CORRELATION_ID_HEADER]
        # Verify it is a valid UUID
        parsed_uuid = uuid.UUID(corr_id)
        assert str(parsed_uuid) == corr_id

@pytest.mark.asyncio
async def test_correlation_id_middleware_propagated():
    transport = ASGITransport(app=app)
    custom_cid = "12345678-1234-5678-1234-567812345678"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health", headers={CORRELATION_ID_HEADER: custom_cid})
        assert response.status_code == 200
        assert response.headers[CORRELATION_ID_HEADER] == custom_cid

@pytest.mark.asyncio
async def test_openapi_schema_accessible():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == settings.APP_NAME
        assert "/health" in schema["paths"]
        assert "/ready" in schema["paths"]
        assert "/api/v1/assessments/start" in schema["paths"]

@pytest.mark.asyncio
async def test_rfc7807_validation_error_format():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Send invalid payload to provisional admin questions endpoint to trigger 400 validation error
        response = await client.post("/api/v1/admin/questions", json={"code": 123, "options": "not-a-list"})
        assert response.status_code == 400
        assert response.headers["content-type"].startswith("application/problem+json")
        data = response.json()
        assert data["isSuccess"] is False
        assert data["errorCode"] == "BAD_REQUEST"
        assert "correlationId" in data
        assert "errors" in data
        assert len(data["errors"]) > 0

@pytest.mark.asyncio
async def test_provisional_endpoint_returns_501():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        valid_payload = {
            "code": "Q-PROV-001",
            "content": "Provisional question content",
            "options": [{"key": "A", "text": "Option A"}],
            "correct_answer": "A",
            "dimensions": {"logical_reasoning": 1.0},
            "difficulty": 0.0,
            "discrimination": 1.0
        }
        response = await client.post("/api/v1/admin/questions", json=valid_payload)
        assert response.status_code == 501
        data = response.json()
        assert data["errorCode"] == "NOT_IMPLEMENTED"
        assert data["isSuccess"] is False

def test_eureka_client_payload_construction():
    client = EurekaClient()
    payload = client._get_registration_payload()
    instance = payload["instance"]
    assert instance["app"] == "ASSESSMENT-SERVICE"
    assert instance["status"] == "UP"
    assert instance["port"]["$"] == settings.EUREKA_INSTANCE_PORT
    assert "leaseInfo" in instance
    assert instance["leaseInfo"]["renewalIntervalInSecs"] == 30

def test_engine_protocols_and_domain_enums():
    dim = CognitiveDimension.LOGICAL_REASONING
    assert dim.value == "logical_reasoning"
    
    state = AbilityState(
        dimension_scores={"logical_reasoning": 0.5},
        uncertainty={"logical_reasoning": 0.25},
        response_count=1,
        dimension_coverage={"logical_reasoning": 1}
    )
    assert state.dimension_scores["logical_reasoning"] == 0.5
    assert state.uncertainty["logical_reasoning"] == 0.25
