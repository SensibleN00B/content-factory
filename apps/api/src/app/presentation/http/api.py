from fastapi import APIRouter

from app.presentation.http.routers.health import router as health_router
from app.presentation.http.routers.profile import router as profile_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(profile_router)
