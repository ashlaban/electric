"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import auth, health, meters, properties, readings
from app.core.config import settings
from app.core.database import Base, engine

# Import models for Base.metadata.create_all - order matters for foreign keys
from app.models import (
    associations,  # noqa: F401
    meter,  # noqa: F401
    meter_reading,  # noqa: F401
    property,  # noqa: F401
    user,  # noqa: F401
)
from app.web.routes import web_router

# Static files directory
BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager."""
    # Startup: Create database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Electric FastAPI application",
    lifespan=lifespan,
)

# Session middleware for web authentication
app.add_middleware(
    SessionMiddleware,  # type: ignore[arg-type]
    secret_key=settings.SECRET_KEY,
    session_cookie="electric_session",
    max_age=86400 * 7,  # 7 days
    same_site="lax",
    https_only=not settings.DEBUG,
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Include API routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api")
app.include_router(properties.router, prefix="/api")
app.include_router(meters.router, prefix="/api")
app.include_router(readings.router, prefix="/api")

# Include web routes (Jinja2 frontend)
app.include_router(web_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
