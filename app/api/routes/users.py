"""User API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import UserCreate, UserResponse, UserUpdate
from app.services import user_service

router = APIRouter(tags=["users"])


@router.post("/properties/{property_id}/users", response_model=UserResponse, status_code=201)
async def create_user(
    property_id: UUID,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a new user for a property."""
    user = await user_service.create_user(db, property_id, user_data)
    return UserResponse.model_validate(user)


@router.get("/properties/{property_id}/users", response_model=list[UserResponse])
async def list_users(
    property_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """List all users for a property."""
    users = await user_service.get_users_by_property(db, property_id, skip, limit)
    return [UserResponse.model_validate(u) for u in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get a user by ID."""
    user = await user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update a user."""
    user = await user_service.update_user(db, user_id, user_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}", status_code=204)
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deactivate a user."""
    success = await user_service.deactivate_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
