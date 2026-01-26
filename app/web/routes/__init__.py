"""Web routes package."""

from fastapi import APIRouter

from app.web.routes import auth, dashboard, home, meters, profile, properties, readings

web_router = APIRouter()

web_router.include_router(home.router, tags=["web-home"])
web_router.include_router(auth.router, tags=["web-auth"])
web_router.include_router(dashboard.router, prefix="/dashboard", tags=["web-dashboard"])
web_router.include_router(properties.router, prefix="/properties", tags=["web-properties"])
web_router.include_router(meters.router, prefix="/meters", tags=["web-meters"])
web_router.include_router(readings.router, prefix="/readings", tags=["web-readings"])
web_router.include_router(profile.router, prefix="/profile", tags=["web-profile"])
