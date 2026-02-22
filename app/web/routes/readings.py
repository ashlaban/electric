"""Readings CRUD web routes."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.v2.readings import BulkReadingCreateV2, ReadingCreateV2
from app.services.meter import get_meter, get_meters_for_property
from app.services.property import get_properties_for_user, get_property
from app.services.v2.readings import (
    create_bulk_readings,
    create_reading,
    get_readings_history,
)
from app.web.dependencies import add_flash_message, get_current_user_from_session
from app.web.template_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse, response_model=None)
async def list_readings(
    request: Request,
    meter_id: int | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """List readings, optionally filtered by meter."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login?next=/readings", status_code=303)

    properties = get_properties_for_user(db, user.id)

    readings_data = []
    total = 0

    if meter_id:
        meter = get_meter(db, meter_id)
        prop = get_property(db, meter.property_id)
        readings, total = get_readings_history(db, meter_id, limit=50)
        for reading in readings:
            readings_data.append(
                {
                    "reading": reading,
                    "meter": meter,
                    "property": prop,
                }
            )
    else:
        # Get recent readings across all meters
        for prop in properties:
            meters = get_meters_for_property(db, prop.id)
            for meter in meters:
                readings, _ = get_readings_history(db, meter.id, limit=10)
                for reading in readings:
                    readings_data.append(
                        {
                            "reading": reading,
                            "meter": meter,
                            "property": prop,
                        }
                    )

        # Sort by timestamp descending
        readings_data.sort(key=lambda x: x["reading"].reading_timestamp, reverse=True)
        readings_data = readings_data[:50]
        total = len(readings_data)

    # Build meters list for filtering
    all_meters = []
    for prop in properties:
        meters = get_meters_for_property(db, prop.id)
        for meter in meters:
            all_meters.append({"meter": meter, "property": prop})

    return templates.TemplateResponse(
        request,
        "readings/list.html",
        {
            "user": user,
            "readings": readings_data,
            "total": total,
            "meters": all_meters,
            "selected_meter_id": meter_id,
        },
    )


@router.get("/create", response_class=HTMLResponse, response_model=None)
async def create_reading_page(
    request: Request,
    meter_id: int | None = None,
    property_id: int | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display create reading form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login?next=/readings/create", status_code=303)

    properties = get_properties_for_user(db, user.id)

    # Build meters grouped by property
    meters_by_property = {}
    for prop in properties:
        meters = get_meters_for_property(db, prop.id)
        meters_by_property[prop.id] = meters

    return templates.TemplateResponse(
        request,
        "readings/create.html",
        {
            "user": user,
            "properties": properties,
            "meters_by_property": meters_by_property,
            "selected_property_id": property_id or user.default_property_id,
            "selected_meter_id": meter_id or user.default_meter_id,
        },
    )


@router.post("/create", response_class=HTMLResponse, response_model=None)
async def create_reading_submit(
    request: Request,
    meter_id: int = Form(...),
    value: Decimal = Form(...),
    reading_date: str = Form(None),
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Process create reading form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # Parse timestamp or use now
    if reading_date:
        timestamp = datetime.fromisoformat(reading_date).replace(tzinfo=UTC)
    else:
        timestamp = datetime.now(UTC)

    reading_data = ReadingCreateV2(
        meter_id=meter_id,
        value=value,
        reading_timestamp=timestamp,
    )

    create_reading(db, reading_data, user_id=user.id)
    add_flash_message(request, f"Reading of {value} recorded successfully!", "success")
    return RedirectResponse("/readings", status_code=303)


@router.get("/bulk", response_class=HTMLResponse, response_model=None)
async def bulk_reading_page(
    request: Request,
    property_id: int | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display bulk reading entry form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login?next=/readings/bulk", status_code=303)

    properties = get_properties_for_user(db, user.id)

    selected_property_id = property_id or user.default_property_id
    meters = []
    selected_property = None

    if selected_property_id:
        selected_property = get_property(db, selected_property_id)
        meters = get_meters_for_property(db, selected_property_id)

    return templates.TemplateResponse(
        request,
        "readings/bulk_create.html",
        {
            "user": user,
            "properties": properties,
            "selected_property": selected_property,
            "selected_property_id": selected_property_id,
            "meters": meters,
        },
    )


@router.post("/bulk", response_class=HTMLResponse, response_model=None)
async def bulk_reading_submit(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Process bulk reading form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    form_data = await request.form()

    property_id_str = form_data.get("property_id")
    main_meter_str = form_data.get("main_meter_value")
    reading_date_str = form_data.get("reading_date")

    # Ensure we have valid string values
    property_id = int(str(property_id_str))
    main_meter_value = Decimal(str(main_meter_str))

    # Parse timestamp
    if reading_date_str and str(reading_date_str).strip():
        timestamp = datetime.fromisoformat(str(reading_date_str)).replace(tzinfo=UTC)
    else:
        timestamp = datetime.now(UTC)

    # Collect submeter readings
    submeter_readings = {}
    for key, value in form_data.items():
        if key.startswith("submeter_") and value:
            name = key.replace("submeter_", "")
            submeter_readings[name] = Decimal(str(value))

    bulk_data = BulkReadingCreateV2(
        property_id=property_id,
        reading_timestamp=timestamp,
        main_meter_value=main_meter_value,
        submeter_readings=submeter_readings,
    )

    readings = create_bulk_readings(db, bulk_data, user_id=user.id)
    add_flash_message(
        request,
        f"Successfully recorded {len(readings)} readings!",
        "success",
    )
    return RedirectResponse(f"/properties/{property_id}", status_code=303)


@router.get("/meter/{meter_id}/history", response_class=HTMLResponse, response_model=None)
async def meter_history(
    request: Request,
    meter_id: int,
    page: int = 1,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display reading history for a specific meter."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(f"/login?next=/readings/meter/{meter_id}/history", status_code=303)

    meter = get_meter(db, meter_id)
    prop = get_property(db, meter.property_id)

    limit = 20
    offset = (page - 1) * limit
    readings, total = get_readings_history(db, meter_id, limit=limit, offset=offset)

    total_pages = (total + limit - 1) // limit

    return templates.TemplateResponse(
        request,
        "readings/history.html",
        {
            "user": user,
            "meter": meter,
            "property": prop,
            "readings": readings,
            "total": total,
            "page": page,
            "total_pages": total_pages,
        },
    )
