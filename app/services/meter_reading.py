"""MeterReading service for business logic - the core ledger operations."""

from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.enums import MeterType, SubMeterKind
from app.models.meter import Meter
from app.models.meter_reading import MeterReading
from app.schemas.meter_reading import (
    MeterReadingBulkCreate,
    MeterReadingCreate,
    PropertyReadingSummary,
    SubMeterReading,
)
from app.services.meter import (
    get_main_meter_for_property,
    get_meters_for_property,
    get_submeter_by_name,
)


def compute_unmetered_value(
    main_meter_value: Decimal | None,
    physical_submeter_values: list[Decimal],
) -> Decimal | None:
    """
    Compute the unmetered (virtual) reading.

    Formula: unmetered = main_meter - sum(physical_submeters)

    Returns None if main meter value is missing.
    """
    if main_meter_value is None:
        return None

    total_submetered = sum(physical_submeter_values, Decimal("0"))
    unmetered = main_meter_value - total_submetered

    # Return 0 if negative (data quality indicator)
    return max(Decimal("0"), unmetered)


def create_reading(
    db: Session,
    reading_data: MeterReadingCreate,
    user_id: int | None = None,
) -> MeterReading:
    """Create a single meter reading."""
    # Verify meter exists
    meter = db.query(Meter).filter(Meter.id == reading_data.meter_id).first()
    if not meter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meter not found",
        )

    # Cannot record readings for virtual meters
    if meter.sub_meter_kind == SubMeterKind.VIRTUAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot directly record readings for virtual meters",
        )

    db_reading = MeterReading(
        meter_id=reading_data.meter_id,
        reading_timestamp=reading_data.reading_timestamp,
        value=reading_data.value,
        recorded_by_user_id=user_id,
    )
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    return db_reading


def create_bulk_readings(
    db: Session,
    bulk_data: MeterReadingBulkCreate,
    user_id: int | None = None,
) -> list[MeterReading]:
    """Create multiple readings for a property at once."""
    created_readings: list[MeterReading] = []

    # Get main meter and record its reading
    main_meter = get_main_meter_for_property(db, bulk_data.property_id)
    if not main_meter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Main meter not found for property {bulk_data.property_id}",
        )

    main_reading = MeterReading(
        meter_id=main_meter.id,
        reading_timestamp=bulk_data.reading_timestamp,
        value=bulk_data.main_meter_value,
        recorded_by_user_id=user_id,
    )
    db.add(main_reading)
    created_readings.append(main_reading)

    # Record submeter readings
    for name, value in bulk_data.submeter_readings.items():
        submeter = get_submeter_by_name(db, bulk_data.property_id, name)
        if not submeter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Submeter '{name}' not found for property {bulk_data.property_id}",
            )

        # Cannot record readings for virtual submeters
        if submeter.sub_meter_kind == SubMeterKind.VIRTUAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot directly record readings for virtual submeter '{name}'",
            )

        reading = MeterReading(
            meter_id=submeter.id,
            reading_timestamp=bulk_data.reading_timestamp,
            value=value,
            recorded_by_user_id=user_id,
        )
        db.add(reading)
        created_readings.append(reading)

    db.commit()
    for r in created_readings:
        db.refresh(r)

    return created_readings


def get_reading_value_at_timestamp(
    db: Session,
    meter_id: int,
    reading_timestamp: datetime,
) -> Decimal | None:
    """Get a meter reading value at a specific timestamp."""
    reading = (
        db.query(MeterReading)
        .filter(
            and_(
                MeterReading.meter_id == meter_id,
                MeterReading.reading_timestamp == reading_timestamp,
            )
        )
        .first()
    )
    return reading.value if reading else None


def get_property_reading_summary(
    db: Session,
    property_id: int,
    reading_timestamp: datetime,
) -> PropertyReadingSummary:
    """Get a complete reading summary for a property at a specific timestamp."""
    meters = get_meters_for_property(db, property_id)

    # Find main meter and get its reading
    main_meter = next(
        (m for m in meters if m.meter_type == MeterType.MAIN_METER),
        None,
    )
    main_value = (
        get_reading_value_at_timestamp(db, main_meter.id, reading_timestamp) if main_meter else None
    )

    # Get physical submeter readings
    physical_subs = [
        m
        for m in meters
        if m.meter_type == MeterType.SUB_METER and m.sub_meter_kind == SubMeterKind.PHYSICAL
    ]

    submeter_readings: list[SubMeterReading] = []
    physical_values: list[Decimal] = []

    for submeter in physical_subs:
        value = get_reading_value_at_timestamp(db, submeter.id, reading_timestamp)
        if value is not None:
            physical_values.append(value)
            submeter_readings.append(
                SubMeterReading(
                    name=submeter.name or "",
                    location=submeter.location,
                    value=value,
                    is_virtual=False,
                )
            )

    # Compute unmetered value
    unmetered = compute_unmetered_value(main_value, physical_values)

    return PropertyReadingSummary(
        property_id=property_id,
        reading_timestamp=reading_timestamp,
        main_meter=main_value,
        submeters=submeter_readings,
        unmetered=unmetered,
    )


def get_latest_readings_for_property(
    db: Session,
    property_id: int,
) -> PropertyReadingSummary | None:
    """Get the most recent readings for a property."""
    # Find the most recent reading timestamp for this property
    meters = get_meters_for_property(db, property_id)
    meter_ids = [m.id for m in meters]

    if not meter_ids:
        return None

    latest_reading = (
        db.query(MeterReading)
        .filter(MeterReading.meter_id.in_(meter_ids))
        .order_by(MeterReading.reading_timestamp.desc())
        .first()
    )

    if not latest_reading:
        return None

    return get_property_reading_summary(db, property_id, latest_reading.reading_timestamp)


def get_readings_history(
    db: Session,
    meter_id: int,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[MeterReading], int]:
    """Get reading history for a specific meter with pagination."""
    query = db.query(MeterReading).filter(MeterReading.meter_id == meter_id)

    total = query.count()
    readings = (
        query.order_by(MeterReading.reading_timestamp.desc()).offset(offset).limit(limit).all()
    )

    return readings, total
