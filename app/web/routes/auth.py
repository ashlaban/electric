"""Authentication web routes."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import UserCreate
from app.services.auth import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_username,
)
from app.web.dependencies import add_flash_message, get_current_user_from_session
from app.web.template_config import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse, response_model=None)
async def login_page(
    request: Request,
    user: None = Depends(get_current_user_from_session),
) -> HTMLResponse | RedirectResponse:
    """Display login form."""
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {"next": request.query_params.get("next", "/")},
    )


@router.post("/login", response_class=HTMLResponse, response_model=None)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next_url: str = Form("/"),
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Process login form."""
    user = authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            request,
            "auth/login.html",
            {
                "error": "Invalid username or password",
                "next": next_url,
                "username": username,
            },
            status_code=400,
        )

    request.session["user_id"] = user.id
    add_flash_message(request, "Welcome back!", "success")
    return RedirectResponse(next_url, status_code=303)


@router.get("/register", response_class=HTMLResponse, response_model=None)
async def register_page(
    request: Request,
    user: None = Depends(get_current_user_from_session),
) -> HTMLResponse | RedirectResponse:
    """Display registration form."""
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "auth/register.html", {})


@router.post("/register", response_class=HTMLResponse, response_model=None)
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Process registration form."""
    errors = {}

    if password != password_confirm:
        errors["password_confirm"] = "Passwords do not match"

    if len(password) < 8:
        errors["password"] = "Password must be at least 8 characters"

    if get_user_by_username(db, username):
        errors["username"] = "Username already taken"

    if get_user_by_email(db, email):
        errors["email"] = "Email already registered"

    if errors:
        return templates.TemplateResponse(
            request,
            "auth/register.html",
            {
                "errors": errors,
                "username": username,
                "email": email,
            },
            status_code=400,
        )

    user_data = UserCreate(username=username, email=email, password=password)
    user = create_user(db, user_data)

    request.session["user_id"] = user.id
    add_flash_message(request, "Account created successfully!", "success")
    return RedirectResponse("/", status_code=303)


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    """Log out and clear session."""
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
