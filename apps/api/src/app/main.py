from fastapi import FastAPI

from app.core.config import settings
from app.presentation.http.api import api_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(api_router)
    return app


app = create_app()
