"""Web-specific dependencies for session authentication."""

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User


def get_current_user_from_session(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    """Get current user from session cookie."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


def require_auth(
    request: Request,
    db: Session = Depends(get_db),
) -> User | RedirectResponse:
    """Require authenticated user, redirect to login if not."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(
            f"/login?next={request.url.path}",
            status_code=303,
        )
    return user


def get_flash_messages(request: Request) -> list[dict]:
    """Get and clear flash messages from session."""
    messages = request.session.pop("flash_messages", [])
    return messages


def add_flash_message(request: Request, message: str, category: str = "info") -> None:
    """Add a flash message to the session."""
    if "flash_messages" not in request.session:
        request.session["flash_messages"] = []
    request.session["flash_messages"].append({"message": message, "category": category})
