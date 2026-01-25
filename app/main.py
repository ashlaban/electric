"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

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


@asynccontextmanager
async def lifespan(app: FastAPI):
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


# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api")
app.include_router(properties.router, prefix="/api")
app.include_router(meters.router, prefix="/api")
app.include_router(readings.router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Welcome to Electric API",
        "version": settings.VERSION,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
