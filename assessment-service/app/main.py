import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.infrastructure.logging.logger import logger, set_correlation_id, get_correlation_id
from app.infrastructure.persistence.database import engine
from app.infrastructure.eureka.client import eureka_client
from app.api.v1.router import root_router

CORRELATION_ID_HEADER = "X-Correlation-ID"

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Ensures every request has a correlation ID, either from the client/gateway
    or freshly generated as a UUID4, and sets it in contextvars and response headers.
    """
    async def dispatch(self, request: Request, call_next):
        corr_id = request.headers.get(CORRELATION_ID_HEADER)
        if not corr_id:
            corr_id = str(uuid.uuid4())

        set_correlation_id(corr_id)
        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = corr_id
        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs incoming requests with their execution duration."""
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        
        # Don't clutter logs with periodic health check polling
        if not request.url.path.endswith("/health"):
            logger.info(
                f"{request.method} {request.url.path} returned {response.status_code} in {duration_ms}ms"
            )
        return response

class PayloadSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects request payloads exceeding MAX_PAYLOAD_SIZE_BYTES to prevent memory exhaustion."""
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > settings.MAX_PAYLOAD_SIZE_BYTES:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "type": "https://api.zango.ir/problems/payload-too-large",
                            "title": "Payload Too Large",
                            "status": 413,
                            "detail": f"Request body exceeds maximum allowed size of {settings.MAX_PAYLOAD_SIZE_BYTES} bytes.",
                            "instance": request.url.path,
                            "isSuccess": False,
                            "errorCode": "PAYLOAD_TOO_LARGE",
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": "Request payload size limit exceeded.",
                            },
                        }
                    )
            except ValueError:
                pass
        return await call_next(request)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and graceful shutdown."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} (env: {settings.APP_ENV})")
    
    # 1. Start Eureka client if enabled
    try:
        await eureka_client.start()
    except Exception as e:
        logger.warning(f"Error initializing Eureka client: {e}")

    yield

    # 2. Graceful Shutdown
    logger.info("Initiating graceful shutdown...")
    try:
        await eureka_client.stop()
    except Exception as e:
        logger.error(f"Error stopping Eureka client: {e}")

    try:
        await engine.dispose()
        logger.info("Database engine connections disposed.")
    except Exception as e:
        logger.error(f"Error disposing database engine: {e}")

    logger.info("Shutdown complete.")

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Smart Adaptive Assessment Engine Microservice for Zango",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # Middleware registration
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(PayloadSizeLimitMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    # Register Routers
    app.include_router(root_router)

    # RFC 7807 Global Exception Handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        corr_id = get_correlation_id() or str(uuid.uuid4())
        status_code = exc.status_code

        # Map HTTP status to Zango ErrorCode taxonomy
        error_code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            422: "VALIDATION_FAILED",
            500: "INTERNAL_SERVER_ERROR",
            501: "NOT_IMPLEMENTED",
            503: "SERVICE_UNAVAILABLE"
        }
        error_code = error_code_map.get(status_code, "ERROR")

        problem = {
            "type": f"https://api.zango.ir/problems/{error_code.lower().replace('_', '-')}",
            "title": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
            "status": status_code,
            "detail": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            "instance": request.url.path,
            "isSuccess": False,
            "errorCode": error_code,
            "correlationId": corr_id
        }
        return JSONResponse(
            status_code=status_code,
            content=problem,
            media_type="application/problem+json",
            headers={CORRELATION_ID_HEADER: corr_id}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        corr_id = get_correlation_id() or str(uuid.uuid4())
        field_errors = []
        for error in exc.errors():
            loc = " -> ".join([str(x) for x in error.get("loc", []) if x != "body"])
            msg = error.get("msg", "Invalid value")
            field_errors.append({"field": loc or "request", "message": msg})

        problem = {
            "type": "https://api.zango.ir/problems/bad-request",
            "title": "Validation Failed",
            "status": status.HTTP_400_BAD_REQUEST,
            "detail": "The request contains invalid or missing parameters.",
            "instance": request.url.path,
            "isSuccess": False,
            "errorCode": "BAD_REQUEST",
            "correlationId": corr_id,
            "errors": field_errors
        }
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=problem,
            media_type="application/problem+json",
            headers={CORRELATION_ID_HEADER: corr_id}
        )

    @app.exception_handler(Exception)
    async def global_uncaught_exception_handler(request: Request, exc: Exception):
        corr_id = get_correlation_id() or str(uuid.uuid4())
        logger.error(f"Uncaught exception on {request.method} {request.url.path}: {exc}", exc_info=True)
        
        problem = {
            "type": "https://api.zango.ir/problems/internal-server-error",
            "title": "Internal Server Error",
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "detail": "An unexpected internal server error occurred.",
            "instance": request.url.path,
            "isSuccess": False,
            "errorCode": "INTERNAL_SERVER_ERROR",
            "correlationId": corr_id
        }
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=problem,
            media_type="application/problem+json",
            headers={CORRELATION_ID_HEADER: corr_id}
        )

    return app

app = create_app()
