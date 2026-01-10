"""User service for business logic."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.models.user import UserCreate, UserUpdate
from app.services.meter_service import get_meter


async def create_user(db: AsyncSession, property_id: UUID, user_data: UserCreate) -> User:
    """
    Create a new user.

    Args:
        db: Database session
        property_id: Property UUID
        user_data: User creation data

    Returns:
        Created user

    Raises:
        HTTPException: If validation fails

    """
    # Validate default meter if provided
    if user_data.default_meter_id:
        meter = await get_meter(db, user_data.default_meter_id)
        if not meter or meter.property_id != property_id:
            raise HTTPException(
                status_code=400,
                detail="Default meter must belong to the same property as the user",
            )

    user = User(
        property_id=property_id,
        name=user_data.name,
        phone_number=user_data.phone_number,
        default_meter_id=user_data.default_meter_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user(db: AsyncSession, user_id: UUID) -> User | None:
    """
    Get a user by ID.

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        User or None if not found

    """
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_users_by_property(
    db: AsyncSession, property_id: UUID, skip: int = 0, limit: int = 100
) -> list[User]:
    """
    Get all users for a property.

    Args:
        db: Database session
        property_id: Property UUID
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of users

    """
    result = await db.execute(
        select(User).where(User.property_id == property_id).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def update_user(
    db: AsyncSession, user_id: UUID, user_data: UserUpdate
) -> User | None:
    """
    Update a user.

    Args:
        db: Database session
        user_id: User UUID
        user_data: User update data

    Returns:
        Updated user or None if not found

    Raises:
        HTTPException: If validation fails

    """
    user = await get_user(db, user_id)
    if not user:
        return None

    update_data = user_data.model_dump(exclude_unset=True)

    # Validate default meter if being updated
    if "default_meter_id" in update_data and update_data["default_meter_id"]:
        meter = await get_meter(db, update_data["default_meter_id"])
        if not meter or meter.property_id != user.property_id:
            raise HTTPException(
                status_code=400,
                detail="Default meter must belong to the same property as the user",
            )

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


async def deactivate_user(db: AsyncSession, user_id: UUID) -> bool:
    """
    Deactivate a user.

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        True if deactivated, False if not found

    """
    user = await get_user(db, user_id)
    if not user:
        return False

    user.is_active = False
    await db.commit()
    return True
