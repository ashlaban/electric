"""MeterReading service for business logic."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.meter import MeterType
from app.db.models.meter_reading import MeterReading
from app.models.meter_reading import MeterReadingCreate, MeterReadingUpdate
from app.services.meter_service import get_meter, get_virtual_meter_sources


async def create_reading(
    db: AsyncSession,
    meter_id: UUID,
    reading_data: MeterReadingCreate,
    user_id: UUID | None = None,
) -> MeterReading:
    """
    Create a new meter reading.

    Args:
        db: Database session
        meter_id: Meter UUID
        reading_data: Reading creation data
        user_id: User who created the reading

    Returns:
        Created meter reading

    Raises:
        HTTPException: If validation fails

    """
    # Get meter and validate
    meter = await get_meter(db, meter_id)
    if not meter:
        raise HTTPException(status_code=404, detail="Meter not found")

    if not meter.is_active:
        raise HTTPException(status_code=400, detail="Cannot add readings to inactive meter")

    if meter.meter_type == MeterType.VIRTUAL:
        raise HTTPException(
            status_code=400, detail="Cannot add readings directly to virtual meters"
        )

    # Validate reading timestamp is not in the future
    if reading_data.reading_timestamp > datetime.now(reading_data.reading_timestamp.tzinfo):
        raise HTTPException(status_code=400, detail="Reading timestamp cannot be in the future")

    # Validate monotonically increasing (check latest reading)
    result = await db.execute(
        select(MeterReading)
        .where(MeterReading.meter_id == meter_id)
        .order_by(MeterReading.reading_timestamp.desc())
        .limit(1)
    )
    latest_reading = result.scalar_one_or_none()

    if latest_reading:
        if reading_data.reading_value < latest_reading.reading_value:
            raise HTTPException(
                status_code=400,
                detail=f"Reading value must be >= previous reading ({latest_reading.reading_value})",
            )

    # Create reading
    reading = MeterReading(
        meter_id=meter_id,
        reading_value=reading_data.reading_value,
        reading_timestamp=reading_data.reading_timestamp,
        notes=reading_data.notes,
        created_by_user_id=user_id,
    )
    db.add(reading)
    await db.commit()
    await db.refresh(reading)
    return reading


async def get_reading(db: AsyncSession, reading_id: UUID) -> MeterReading | None:
    """
    Get a reading by ID.

    Args:
        db: Database session
        reading_id: Reading UUID

    Returns:
        Reading or None if not found

    """
    result = await db.execute(select(MeterReading).where(MeterReading.id == reading_id))
    return result.scalar_one_or_none()


async def get_readings_by_meter(
    db: AsyncSession,
    meter_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[MeterReading]:
    """
    Get readings for a meter with optional date filtering.

    Args:
        db: Database session
        meter_id: Meter UUID
        start_date: Optional start date filter
        end_date: Optional end date filter
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of readings

    """
    query = select(MeterReading).where(MeterReading.meter_id == meter_id)

    if start_date:
        query = query.where(MeterReading.reading_timestamp >= start_date)
    if end_date:
        query = query.where(MeterReading.reading_timestamp <= end_date)

    query = query.order_by(MeterReading.reading_timestamp.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


async def update_reading(
    db: AsyncSession, reading_id: UUID, reading_data: MeterReadingUpdate
) -> MeterReading | None:
    """
    Update a meter reading.

    Args:
        db: Database session
        reading_id: Reading UUID
        reading_data: Reading update data

    Returns:
        Updated reading or None if not found

    Raises:
        HTTPException: If validation fails

    """
    reading = await get_reading(db, reading_id)
    if not reading:
        return None

    update_data = reading_data.model_dump(exclude_unset=True)

    # Validate timestamp if being updated
    if "reading_timestamp" in update_data:
        new_timestamp = update_data["reading_timestamp"]
        if new_timestamp > datetime.now(new_timestamp.tzinfo):
            raise HTTPException(
                status_code=400, detail="Reading timestamp cannot be in the future"
            )

    # Validate reading value if being updated
    if "reading_value" in update_data:
        # Check against other readings for the same meter
        result = await db.execute(
            select(MeterReading)
            .where(
                MeterReading.meter_id == reading.meter_id, MeterReading.id != reading_id
            )
            .order_by(MeterReading.reading_timestamp)
        )
        other_readings = result.scalars().all()

        new_value = update_data["reading_value"]
        new_timestamp = update_data.get("reading_timestamp", reading.reading_timestamp)

        for other in other_readings:
            if other.reading_timestamp < new_timestamp and other.reading_value > new_value:
                raise HTTPException(
                    status_code=400,
                    detail=f"Reading value conflicts with earlier reading on {other.reading_timestamp}",
                )
            if other.reading_timestamp > new_timestamp and other.reading_value < new_value:
                raise HTTPException(
                    status_code=400,
                    detail=f"Reading value conflicts with later reading on {other.reading_timestamp}",
                )

    for field, value in update_data.items():
        setattr(reading, field, value)

    await db.commit()
    await db.refresh(reading)
    return reading


async def delete_reading(db: AsyncSession, reading_id: UUID) -> bool:
    """
    Delete a meter reading.

    Args:
        db: Database session
        reading_id: Reading UUID

    Returns:
        True if deleted, False if not found

    """
    reading = await get_reading(db, reading_id)
    if not reading:
        return False

    await db.delete(reading)
    await db.commit()
    return True


async def calculate_virtual_readings(
    db: AsyncSession,
    property_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict]:
    """
    Calculate virtual meter readings (unmetered = total - gg - sg).

    Args:
        db: Database session
        property_id: Property UUID
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        List of virtual readings with calculated values

    """
    # Get source meters
    source_meters = await get_virtual_meter_sources(db, property_id)

    if len(source_meters) != 3:
        raise HTTPException(
            status_code=400,
            detail="Property must have total, gg, and sg meters for virtual calculation",
        )

    # Get readings for each meter
    total_readings = await get_readings_by_meter(
        db, source_meters["total"].id, start_date, end_date, limit=1000
    )
    gg_readings = await get_readings_by_meter(
        db, source_meters["gg"].id, start_date, end_date, limit=1000
    )
    sg_readings = await get_readings_by_meter(
        db, source_meters["sg"].id, start_date, end_date, limit=1000
    )

    # Create timestamp-indexed dictionaries
    total_dict = {r.reading_timestamp: r.reading_value for r in total_readings}
    gg_dict = {r.reading_timestamp: r.reading_value for r in gg_readings}
    sg_dict = {r.reading_timestamp: r.reading_value for r in sg_readings}

    # Find common timestamps
    common_timestamps = (
        set(total_dict.keys()) & set(gg_dict.keys()) & set(sg_dict.keys())
    )

    # Calculate virtual readings
    virtual_readings = []
    for timestamp in sorted(common_timestamps, reverse=True):
        unmetered_value = total_dict[timestamp] - gg_dict[timestamp] - sg_dict[timestamp]
        virtual_readings.append(
            {
                "reading_timestamp": timestamp,
                "reading_value": unmetered_value,
                "calculated": True,
            }
        )

    return virtual_readings
