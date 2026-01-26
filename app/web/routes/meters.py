"""Meters CRUD web routes."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import MeterType
from app.schemas.meter import MeterUpdate, SubMeterCreate
from app.services.meter import (
    create_submeter,
    get_meter,
    get_meters_for_property,
    update_meter,
)
from app.services.meter_reading import get_readings_history
from app.services.property import get_properties_for_user, get_property
from app.web.dependencies import add_flash_message, get_current_user_from_session
from app.web.template_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse, response_model=None)
async def list_meters(
    request: Request,
    property_id: int | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """List meters, optionally filtered by property."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login?next=/meters", status_code=303)

    properties = get_properties_for_user(db, user.id)

    meters_data = []
    if property_id:
        # Filter by specific property
        meters = get_meters_for_property(db, property_id)
        prop = get_property(db, property_id)
        for meter in meters:
            meters_data.append({"meter": meter, "property": prop})
    else:
        # Show all meters for all properties
        for prop in properties:
            meters = get_meters_for_property(db, prop.id)
            for meter in meters:
                meters_data.append({"meter": meter, "property": prop})

    return templates.TemplateResponse(
        request,
        "meters/list.html",
        {
            "user": user,
            "meters": meters_data,
            "properties": properties,
            "selected_property_id": property_id,
        },
    )


@router.get("/create", response_class=HTMLResponse, response_model=None)
async def create_meter_page(
    request: Request,
    property_id: int | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display create meter form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login?next=/meters/create", status_code=303)

    properties = get_properties_for_user(db, user.id)

    return templates.TemplateResponse(
        request,
        "meters/create.html",
        {
            "user": user,
            "properties": properties,
            "selected_property_id": property_id,
        },
    )


@router.post("/create", response_class=HTMLResponse, response_model=None)
async def create_meter_submit(
    request: Request,
    property_id: int = Form(...),
    name: str = Form(...),
    location: str = Form(""),
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Process create meter form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    meter_data = SubMeterCreate(
        property_id=property_id,
        name=name,
        location=location or None,
    )

    new_meter = create_submeter(db, meter_data)

    add_flash_message(request, f"Meter '{name}' created successfully!", "success")
    return RedirectResponse(f"/meters/{new_meter.id}", status_code=303)


@router.get("/{meter_id}", response_class=HTMLResponse, response_model=None)
async def meter_detail(
    request: Request,
    meter_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display meter detail with reading history."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(f"/login?next=/meters/{meter_id}", status_code=303)

    meter = get_meter(db, meter_id)
    prop = get_property(db, meter.property_id)
    readings, total = get_readings_history(db, meter_id, limit=10)

    return templates.TemplateResponse(
        request,
        "meters/detail.html",
        {
            "user": user,
            "meter": meter,
            "property": prop,
            "readings": readings,
            "total_readings": total,
        },
    )


@router.get("/{meter_id}/edit", response_class=HTMLResponse, response_model=None)
async def edit_meter_page(
    request: Request,
    meter_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display edit meter form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(f"/login?next=/meters/{meter_id}/edit", status_code=303)

    meter = get_meter(db, meter_id)
    prop = get_property(db, meter.property_id)

    return templates.TemplateResponse(
        request,
        "meters/edit.html",
        {
            "user": user,
            "meter": meter,
            "property": prop,
        },
    )


@router.post("/{meter_id}/edit", response_class=HTMLResponse, response_model=None)
async def edit_meter_submit(
    request: Request,
    meter_id: int,
    name: str = Form(None),
    location: str = Form(""),
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Process edit meter form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    meter = get_meter(db, meter_id)

    # Only allow editing name/location for submeters
    if meter.meter_type == MeterType.SUB_METER:
        meter_data = MeterUpdate(name=name, location=location or None)
        update_meter(db, meter_id, meter_data)

    add_flash_message(request, "Meter updated successfully!", "success")
    return RedirectResponse(f"/meters/{meter_id}", status_code=303)


@router.post("/{meter_id}/delete", response_class=HTMLResponse, response_model=None)
async def delete_meter(
    request: Request,
    meter_id: int,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Delete a meter (only submeters can be deleted)."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    meter = get_meter(db, meter_id)

    # Can't delete main meters
    if meter.meter_type == MeterType.MAIN_METER:
        add_flash_message(request, "Cannot delete main meter.", "error")
        return RedirectResponse(f"/meters/{meter_id}", status_code=303)

    property_id = meter.property_id

    # Clear default if this was the default meter
    if user.default_meter_id == meter_id:
        user.default_meter_id = None
        db.commit()

    db.delete(meter)
    db.commit()

    add_flash_message(request, "Meter deleted successfully!", "success")
    return RedirectResponse(f"/properties/{property_id}", status_code=303)
