from fastapi import APIRouter, status, Response
from pydantic import BaseModel
from typing import Dict, Any
from app.config import settings
from app.infrastructure.persistence.database import check_db_health
from app.infrastructure.eureka.client import eureka_client

router = APIRouter(tags=["Health & Readiness"])

class HealthResponse(BaseModel):
    status: str
    version: str

class ReadinessResponse(BaseModel):
    status: str
    details: Dict[str, Any]

@router.get("/health", response_model=HealthResponse, summary="Liveness Probe")
async def health():
    """Returns 200 OK if the process is responsive."""
    return HealthResponse(
        status="UP",
        version=settings.APP_VERSION
    )

@router.get("/ready", response_model=ReadinessResponse, summary="Readiness Probe")
async def readiness(response: Response):
    """
    Checks availability of critical dependencies (Database, Eureka).
    Returns 200 when ready to receive traffic, 503 if critical dependencies are unavailable.
    """
    db_ok = await check_db_health()
    eureka_ok = eureka_client.is_registered if settings.EUREKA_ENABLED else True

    details = {
        "database": "UP" if db_ok else "DOWN",
        "eureka": "UP" if eureka_ok else "UNAVAILABLE",
        "eureka_enabled": settings.EUREKA_ENABLED
    }

    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="DOWN", details=details)

    return ReadinessResponse(status="UP", details=details)
