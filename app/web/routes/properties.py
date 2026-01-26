"""Properties CRUD web routes."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.property import PropertyCreate, PropertyUpdate
from app.services.meter import get_meters_for_property
from app.services.meter_reading import get_latest_readings_for_property
from app.services.property import (
    associate_user_with_property,
    create_property,
    get_properties_for_user,
    get_property,
    update_property,
)
from app.web.dependencies import add_flash_message, get_current_user_from_session
from app.web.template_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse, response_model=None)
async def list_properties(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """List all user's properties."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login?next=/properties", status_code=303)

    properties = get_properties_for_user(db, user.id)

    # Enrich with meter counts
    property_data = []
    for prop in properties:
        meters = get_meters_for_property(db, prop.id)
        property_data.append(
            {
                "property": prop,
                "meters_count": len(meters),
            }
        )

    return templates.TemplateResponse(
        request,
        "properties/list.html",
        {
            "user": user,
            "properties": property_data,
        },
    )


@router.get("/create", response_class=HTMLResponse, response_model=None)
async def create_property_page(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display create property form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login?next=/properties/create", status_code=303)

    onboarding = request.query_params.get("onboarding") == "1"

    return templates.TemplateResponse(
        request,
        "properties/create.html",
        {
            "user": user,
            "onboarding": onboarding,
        },
    )


@router.post("/create", response_class=HTMLResponse, response_model=None)
async def create_property_submit(
    request: Request,
    display_name: str = Form(...),
    address: str = Form(""),
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Process create property form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    property_data = PropertyCreate(display_name=display_name, address=address or None)
    new_property = create_property(db, property_data)

    # Associate user with property
    associate_user_with_property(db, user.id, new_property.id)

    # If this is the user's first property, set it as default
    if not user.default_property_id:
        user.default_property_id = new_property.id
        # Set default meter to the main meter
        meters = get_meters_for_property(db, new_property.id)
        if meters:
            user.default_meter_id = meters[0].id
        db.commit()

    add_flash_message(request, f"Property '{display_name}' created successfully!", "success")
    return RedirectResponse(f"/properties/{new_property.id}", status_code=303)


@router.get("/{property_id}", response_class=HTMLResponse, response_model=None)
async def property_detail(
    request: Request,
    property_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display property detail."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(f"/login?next=/properties/{property_id}", status_code=303)

    prop = get_property(db, property_id)
    meters = get_meters_for_property(db, property_id)
    latest_reading = get_latest_readings_for_property(db, property_id)

    return templates.TemplateResponse(
        request,
        "properties/detail.html",
        {
            "user": user,
            "property": prop,
            "meters": meters,
            "latest_reading": latest_reading,
        },
    )


@router.get("/{property_id}/edit", response_class=HTMLResponse, response_model=None)
async def edit_property_page(
    request: Request,
    property_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display edit property form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(f"/login?next=/properties/{property_id}/edit", status_code=303)

    prop = get_property(db, property_id)

    return templates.TemplateResponse(
        request,
        "properties/edit.html",
        {
            "user": user,
            "property": prop,
        },
    )


@router.post("/{property_id}/edit", response_class=HTMLResponse, response_model=None)
async def edit_property_submit(
    request: Request,
    property_id: int,
    display_name: str = Form(...),
    address: str = Form(""),
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Process edit property form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    property_data = PropertyUpdate(display_name=display_name, address=address or None)
    update_property(db, property_id, property_data)

    add_flash_message(request, "Property updated successfully!", "success")
    return RedirectResponse(f"/properties/{property_id}", status_code=303)


@router.post("/{property_id}/delete", response_class=HTMLResponse, response_model=None)
async def delete_property(
    request: Request,
    property_id: int,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Delete a property."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    prop = get_property(db, property_id)

    # Clear default if this was the default property
    if user.default_property_id == property_id:
        user.default_property_id = None
        user.default_meter_id = None
        db.commit()

    # Delete property (cascade will handle meters and readings)
    db.delete(prop)
    db.commit()

    add_flash_message(request, "Property deleted successfully!", "success")
    return RedirectResponse("/properties", status_code=303)
