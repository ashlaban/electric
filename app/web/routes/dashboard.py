"""Dashboard web routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.meter_reading import MeterReading
from app.services.meter import get_meters_for_property
from app.services.property import get_properties_for_user
from app.services.v2.readings import get_latest_readings_for_property
from app.web.dependencies import get_current_user_from_session
from app.web.template_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse, response_model=None)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display dashboard summary."""
    user = get_current_user_from_session(request, db)

    if not user:
        return RedirectResponse("/login?next=/dashboard", status_code=303)

    properties = get_properties_for_user(db, user.id)

    # Aggregate stats
    stats = {
        "properties_count": len(properties),
        "meters_count": 0,
        "readings_this_month": 0,
    }

    # Count readings this month
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    property_summaries = []
    all_meter_ids = []

    for prop in properties:
        meters = get_meters_for_property(db, prop.id)
        stats["meters_count"] += len(meters)
        all_meter_ids.extend([m.id for m in meters])

        latest = get_latest_readings_for_property(db, prop.id)

        property_summaries.append(
            {
                "property": prop,
                "meters_count": len(meters),
                "latest_reading": latest,
            }
        )

    # Count readings this month
    if all_meter_ids:
        stats["readings_this_month"] = (
            db.query(MeterReading)
            .filter(
                MeterReading.meter_id.in_(all_meter_ids),
                MeterReading.reading_timestamp >= month_start,
            )
            .count()
        )

    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        {
            "user": user,
            "stats": stats,
            "property_summaries": property_summaries,
        },
    )
