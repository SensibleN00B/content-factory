from fastapi import APIRouter

from app.presentation.http.routers.candidates import router as candidates_router
from app.presentation.http.routers.health import router as health_router
from app.presentation.http.routers.labels import router as labels_router
from app.presentation.http.routers.profile import router as profile_router
from app.presentation.http.routers.runs import router as runs_router
from app.presentation.http.routers.topic_labels import router as topic_labels_router

api_router = APIRouter()
api_router.include_router(candidates_router)
api_router.include_router(health_router)
api_router.include_router(labels_router)
api_router.include_router(profile_router)
api_router.include_router(runs_router)
api_router.include_router(topic_labels_router)
