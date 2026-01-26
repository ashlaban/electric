"""Profile management web routes."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.auth import get_password_hash, verify_password
from app.services.meter import get_meters_for_property
from app.services.property import get_properties_for_user
from app.web.dependencies import add_flash_message, get_current_user_from_session
from app.web.template_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse, response_model=None)
async def view_profile(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display user profile."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login?next=/profile", status_code=303)

    return templates.TemplateResponse(
        request,
        "profile/view.html",
        {"user": user},
    )


@router.get("/edit", response_class=HTMLResponse, response_model=None)
async def edit_profile_page(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display edit profile form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login?next=/profile/edit", status_code=303)

    properties = get_properties_for_user(db, user.id)

    # Build meters grouped by property
    meters_by_property = {}
    for prop in properties:
        meters = get_meters_for_property(db, prop.id)
        meters_by_property[prop.id] = meters

    setup_defaults = request.query_params.get("setup_defaults") == "1"

    return templates.TemplateResponse(
        request,
        "profile/edit.html",
        {
            "user": user,
            "properties": properties,
            "meters_by_property": meters_by_property,
            "setup_defaults": setup_defaults,
        },
    )


@router.post("/edit", response_class=HTMLResponse, response_model=None)
async def edit_profile_submit(
    request: Request,
    phone_number: str = Form(""),
    default_property_id: int = Form(None),
    default_meter_id: int = Form(None),
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Process edit profile form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    user.phone_number = phone_number or None
    user.default_property_id = default_property_id
    user.default_meter_id = default_meter_id

    db.commit()

    add_flash_message(request, "Profile updated successfully!", "success")
    return RedirectResponse("/", status_code=303)


@router.get("/change-password", response_class=HTMLResponse, response_model=None)
async def change_password_page(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display change password form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login?next=/profile/change-password", status_code=303)

    return templates.TemplateResponse(
        request,
        "profile/change_password.html",
        {"user": user},
    )


@router.post("/change-password", response_class=HTMLResponse, response_model=None)
async def change_password_submit(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Process change password form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    errors = {}

    if not verify_password(current_password, user.hashed_password):
        errors["current_password"] = "Current password is incorrect"

    if new_password != confirm_password:
        errors["confirm_password"] = "New passwords do not match"

    if len(new_password) < 8:
        errors["new_password"] = "Password must be at least 8 characters"

    if errors:
        return templates.TemplateResponse(
            request,
            "profile/change_password.html",
            {
                "user": user,
                "errors": errors,
            },
            status_code=400,
        )

    user.hashed_password = get_password_hash(new_password)
    db.commit()

    add_flash_message(request, "Password changed successfully!", "success")
    return RedirectResponse("/profile", status_code=303)
