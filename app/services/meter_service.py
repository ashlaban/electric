"""Meter service for business logic."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meter import Meter, MeterType
from app.models.meter import MeterCreate, MeterUpdate


async def create_meter(
    db: AsyncSession, property_id: UUID, meter_data: MeterCreate
) -> Meter:
    """
    Create a new meter.

    Args:
        db: Database session
        property_id: Property UUID
        meter_data: Meter creation data

    Returns:
        Created meter

    Raises:
        HTTPException: If meter code already exists for property

    """
    # Check for duplicate meter code
    result = await db.execute(
        select(Meter).where(
            Meter.property_id == property_id, Meter.meter_code == meter_data.meter_code
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Meter with code '{meter_data.meter_code}' already exists for this property",
        )

    meter = Meter(
        property_id=property_id,
        meter_code=meter_data.meter_code,
        meter_type=meter_data.meter_type,
        description=meter_data.description,
        unit=meter_data.unit,
    )
    db.add(meter)
    await db.commit()
    await db.refresh(meter)
    return meter


async def get_meter(db: AsyncSession, meter_id: UUID) -> Meter | None:
    """
    Get a meter by ID.

    Args:
        db: Database session
        meter_id: Meter UUID

    Returns:
        Meter or None if not found

    """
    result = await db.execute(select(Meter).where(Meter.id == meter_id))
    return result.scalar_one_or_none()


async def get_meters_by_property(
    db: AsyncSession, property_id: UUID, skip: int = 0, limit: int = 100
) -> list[Meter]:
    """
    Get all meters for a property.

    Args:
        db: Database session
        property_id: Property UUID
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of meters

    """
    result = await db.execute(
        select(Meter)
        .where(Meter.property_id == property_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_meter(
    db: AsyncSession, meter_id: UUID, meter_data: MeterUpdate
) -> Meter | None:
    """
    Update a meter.

    Args:
        db: Database session
        meter_id: Meter UUID
        meter_data: Meter update data

    Returns:
        Updated meter or None if not found

    """
    meter = await get_meter(db, meter_id)
    if not meter:
        return None

    update_data = meter_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(meter, field, value)

    await db.commit()
    await db.refresh(meter)
    return meter


async def deactivate_meter(db: AsyncSession, meter_id: UUID) -> bool:
    """
    Deactivate a meter.

    Args:
        db: Database session
        meter_id: Meter UUID

    Returns:
        True if deactivated, False if not found

    """
    meter = await get_meter(db, meter_id)
    if not meter:
        return False

    meter.is_active = False
    await db.commit()
    return True


async def get_virtual_meter_sources(
    db: AsyncSession, property_id: UUID
) -> dict[str, Meter]:
    """
    Get source meters for virtual meter calculation.

    Args:
        db: Database session
        property_id: Property UUID

    Returns:
        Dictionary of meter_code -> Meter for total, gg, sg

    """
    result = await db.execute(
        select(Meter).where(
            Meter.property_id == property_id,
            Meter.meter_code.in_(["total", "gg", "sg"]),
            Meter.meter_type != MeterType.VIRTUAL,
        )
    )
    meters = result.scalars().all()
    return {meter.meter_code: meter for meter in meters}
