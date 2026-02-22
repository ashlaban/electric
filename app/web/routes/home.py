"""Home/landing page web routes."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.v2.readings import ReadingCreateV2
from app.services.meter import get_meter
from app.services.property import get_properties_for_user, get_property
from app.services.v2.readings import create_reading, get_latest_readings_for_property
from app.web.dependencies import add_flash_message, get_current_user_from_session
from app.web.template_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse, response_model=None)
async def home(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Landing page with quick entry or login."""
    user = get_current_user_from_session(request, db)

    if not user:
        return templates.TemplateResponse(
            request,
            "home/index.html",
            {"user": None},
        )

    # Check for default property and meter
    properties = get_properties_for_user(db, user.id)

    if not properties:
        add_flash_message(request, "Let's start by adding your first property.", "info")
        return RedirectResponse("/properties/create?onboarding=1", status_code=303)

    if not user.default_property_id:
        add_flash_message(request, "Please set your default property for quick readings.", "info")
        return RedirectResponse("/profile/edit?setup_defaults=1", status_code=303)

    if not user.default_meter_id:
        add_flash_message(request, "Please set your default meter for quick readings.", "info")
        return RedirectResponse("/profile/edit?setup_defaults=1", status_code=303)

    # Get default property and meter info
    default_property = get_property(db, user.default_property_id)
    default_meter = get_meter(db, user.default_meter_id)
    latest_reading = get_latest_readings_for_property(db, user.default_property_id)

    return templates.TemplateResponse(
        request,
        "home/index.html",
        {
            "user": user,
            "active_tab": "home",
            "property": default_property,
            "meter": default_meter,
            "latest_reading": latest_reading,
        },
    )


@router.post("/quick-reading", response_class=HTMLResponse, response_model=None)
async def quick_reading(
    request: Request,
    value: Decimal = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Submit a quick meter reading."""
    user = get_current_user_from_session(request, db)

    if not user or not user.default_meter_id:
        add_flash_message(request, "Please set up your default meter first.", "error")
        return RedirectResponse("/profile/edit", status_code=303)

    reading_data = ReadingCreateV2(
        meter_id=user.default_meter_id,
        value=value,
        reading_timestamp=datetime.now(UTC),
    )

    create_reading(db, reading_data, user_id=user.id)
    add_flash_message(request, f"Reading of {value} recorded successfully!", "success")
    return RedirectResponse("/", status_code=303)
