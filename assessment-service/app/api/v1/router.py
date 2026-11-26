from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.assessments import router as assessments_router
from app.api.v1.endpoints.admin_questions import router as admin_questions_router
from app.simulation.api.router import router as simulation_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(assessments_router)
api_v1_router.include_router(admin_questions_router)
api_v1_router.include_router(simulation_router)

# Health router is mounted at root as well as /api/v1 for convenience
root_router = APIRouter()
root_router.include_router(health_router)
root_router.include_router(api_v1_router)
