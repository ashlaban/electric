"""Property service for business logic."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meter import Meter, MeterType
from app.db.models.property import Property
from app.models.property import PropertyCreate, PropertyUpdate


async def create_property(db: AsyncSession, property_data: PropertyCreate) -> Property:
    """
    Create a new property with default meters.

    Args:
        db: Database session
        property_data: Property creation data

    Returns:
        Created property with meters

    """
    # Create property
    property_obj = Property(
        name=property_data.name,
        address=property_data.address,
    )
    db.add(property_obj)
    await db.flush()

    # Create default meters
    default_meters = [
        Meter(
            property_id=property_obj.id,
            meter_code="total",
            meter_type=MeterType.PHYSICAL_MAIN,
            description="Main meter - total consumption",
            unit="kWh",
        ),
        Meter(
            property_id=property_obj.id,
            meter_code="gg",
            meter_type=MeterType.PHYSICAL_SUBMETER,
            description="GG circuit submeter",
            unit="kWh",
        ),
        Meter(
            property_id=property_obj.id,
            meter_code="sg",
            meter_type=MeterType.PHYSICAL_SUBMETER,
            description="SG circuit submeter",
            unit="kWh",
        ),
        Meter(
            property_id=property_obj.id,
            meter_code="unmetered",
            meter_type=MeterType.VIRTUAL,
            description="Unmetered consumption (total - gg - sg)",
            unit="kWh",
        ),
    ]

    for meter in default_meters:
        db.add(meter)

    await db.commit()
    await db.refresh(property_obj)
    return property_obj


async def get_property(db: AsyncSession, property_id: UUID) -> Property | None:
    """
    Get a property by ID.

    Args:
        db: Database session
        property_id: Property UUID

    Returns:
        Property or None if not found

    """
    result = await db.execute(select(Property).where(Property.id == property_id))
    return result.scalar_one_or_none()


async def get_properties(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Property]:
    """
    Get all properties with pagination.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of properties

    """
    result = await db.execute(select(Property).offset(skip).limit(limit))
    return list(result.scalars().all())


async def update_property(
    db: AsyncSession, property_id: UUID, property_data: PropertyUpdate
) -> Property | None:
    """
    Update a property.

    Args:
        db: Database session
        property_id: Property UUID
        property_data: Property update data

    Returns:
        Updated property or None if not found

    """
    property_obj = await get_property(db, property_id)
    if not property_obj:
        return None

    update_data = property_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(property_obj, field, value)

    await db.commit()
    await db.refresh(property_obj)
    return property_obj


async def delete_property(db: AsyncSession, property_id: UUID) -> bool:
    """
    Delete a property.

    Args:
        db: Database session
        property_id: Property UUID

    Returns:
        True if deleted, False if not found

    """
    property_obj = await get_property(db, property_id)
    if not property_obj:
        return False

    await db.delete(property_obj)
    await db.commit()
    return True
