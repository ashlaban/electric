"""V2 MeterReading service with support for absolute and relative readings."""

from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.enums import MeterType, ReadingType
from app.models.meter import Meter
from app.models.meter_reading import MeterReading
from app.schemas.v2.readings import (
    BulkReadingCreateV2,
    ConsumptionSummaryV2,
    PropertyReadingSummaryV2,
    ReadingCreateV2,
    SubMeterConsumptionV2,
    SubMeterReadingV2,
)
from app.services.meter import (
    get_main_meter_for_property,
    get_meters_for_property,
    get_submeter_by_name,
    get_submeters_for_property,
)


def create_reading(
    db: Session,
    reading_data: ReadingCreateV2,
    user_id: int | None = None,
) -> MeterReading:
    """Create a single meter reading with explicit reading type."""
    meter = db.query(Meter).filter(Meter.id == reading_data.meter_id).first()
    if not meter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meter not found",
        )

    db_reading = MeterReading(
        meter_id=reading_data.meter_id,
        reading_timestamp=reading_data.reading_timestamp,
        value=reading_data.value,
        reading_type=reading_data.reading_type,
        recorded_by_user_id=user_id,
    )
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    return db_reading


def create_bulk_readings(
    db: Session,
    bulk_data: BulkReadingCreateV2,
    user_id: int | None = None,
) -> list[MeterReading]:
    """Create multiple readings for a property at once."""
    created_readings: list[MeterReading] = []

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
        reading_type=bulk_data.reading_type,
        recorded_by_user_id=user_id,
    )
    db.add(main_reading)
    created_readings.append(main_reading)

    for name, value in bulk_data.submeter_readings.items():
        submeter = get_submeter_by_name(db, bulk_data.property_id, name)
        if not submeter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Submeter '{name}' not found for property {bulk_data.property_id}",
            )

        reading = MeterReading(
            meter_id=submeter.id,
            reading_timestamp=bulk_data.reading_timestamp,
            value=value,
            reading_type=bulk_data.reading_type,
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
) -> PropertyReadingSummaryV2:
    """Get a complete reading summary for a property at a specific timestamp."""
    meters = get_meters_for_property(db, property_id)

    main_meter = next(
        (m for m in meters if m.meter_type == MeterType.MAIN_METER),
        None,
    )
    main_value = (
        get_reading_value_at_timestamp(db, main_meter.id, reading_timestamp) if main_meter else None
    )

    submeters = [m for m in meters if m.meter_type == MeterType.SUB_METER]
    submeter_readings: list[SubMeterReadingV2] = []
    submeter_values: list[Decimal] = []

    for submeter in submeters:
        value = get_reading_value_at_timestamp(db, submeter.id, reading_timestamp)
        if value is not None:
            submeter_values.append(value)
            submeter_readings.append(
                SubMeterReadingV2(
                    name=submeter.name or "",
                    meter_id=submeter.id,
                    location=submeter.location,
                    value=value,
                )
            )

    unmetered = _compute_unmetered(main_value, submeter_values)

    return PropertyReadingSummaryV2(
        property_id=property_id,
        reading_timestamp=reading_timestamp,
        main_meter=main_value,
        submeters=submeter_readings,
        unmetered=unmetered,
    )


def get_latest_readings_for_property(
    db: Session,
    property_id: int,
) -> PropertyReadingSummaryV2 | None:
    """Get the most recent readings for a property."""
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


def compute_meter_consumption(
    db: Session,
    meter_id: int,
    start_timestamp: datetime,
    end_timestamp: datetime,
) -> Decimal | None:
    """Compute consumption for a single meter over a period.

    Supports both absolute and relative reading types:
    - Absolute: consumption = end_reading - start_reading
    - Relative: consumption = sum of all relative readings in the period
    """
    # Try absolute readings first: look for readings at boundary timestamps
    start_reading = (
        db.query(MeterReading)
        .filter(
            and_(
                MeterReading.meter_id == meter_id,
                MeterReading.reading_timestamp == start_timestamp,
                MeterReading.reading_type == ReadingType.ABSOLUTE,
            )
        )
        .first()
    )
    end_reading = (
        db.query(MeterReading)
        .filter(
            and_(
                MeterReading.meter_id == meter_id,
                MeterReading.reading_timestamp == end_timestamp,
                MeterReading.reading_type == ReadingType.ABSOLUTE,
            )
        )
        .first()
    )

    if start_reading and end_reading:
        return end_reading.value - start_reading.value

    # Fall back to relative readings: sum all relative readings in the period
    relative_readings = (
        db.query(MeterReading)
        .filter(
            and_(
                MeterReading.meter_id == meter_id,
                MeterReading.reading_type == ReadingType.RELATIVE,
                MeterReading.reading_timestamp > start_timestamp,
                MeterReading.reading_timestamp <= end_timestamp,
            )
        )
        .all()
    )

    if relative_readings:
        return sum((r.value for r in relative_readings), Decimal("0"))

    return None


def get_property_consumption(
    db: Session,
    property_id: int,
    start_timestamp: datetime,
    end_timestamp: datetime,
) -> ConsumptionSummaryV2:
    """Calculate consumption for a property over a period.

    Handles both absolute and relative reading types per meter.
    Includes unmetered consumption as a virtual submeter.
    """
    main_meter = get_main_meter_for_property(db, property_id)
    main_consumption: Decimal | None = None

    if main_meter:
        main_consumption = compute_meter_consumption(
            db, main_meter.id, start_timestamp, end_timestamp
        )

    submeters = get_submeters_for_property(db, property_id)
    submeter_consumptions: list[SubMeterConsumptionV2] = []
    total_submetered = Decimal("0")

    for submeter in submeters:
        consumption = compute_meter_consumption(db, submeter.id, start_timestamp, end_timestamp)
        if consumption is not None:
            total_submetered += consumption
            submeter_consumptions.append(
                SubMeterConsumptionV2(
                    name=submeter.name or "",
                    meter_id=submeter.id,
                    location=submeter.location,
                    consumption=consumption,
                    is_virtual=False,
                )
            )

    unmetered_consumption = _compute_unmetered(main_consumption, [total_submetered])

    # Add the unmetered virtual submeter to the list
    if unmetered_consumption is not None and unmetered_consumption > 0:
        submeter_consumptions.append(
            SubMeterConsumptionV2(
                name="_unmetered",
                meter_id=-1,
                location=None,
                consumption=unmetered_consumption,
                is_virtual=True,
            )
        )

    return ConsumptionSummaryV2(
        property_id=property_id,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        main_meter_consumption=main_consumption,
        submeters=submeter_consumptions,
        total_submetered_consumption=total_submetered,
        unmetered_consumption=unmetered_consumption,
    )


def compute_consumption_map(
    db: Session,
    property_id: int,
    start_timestamp: datetime,
    end_timestamp: datetime,
) -> tuple[dict[str, Decimal], Decimal | None, Decimal | None]:
    """Compute a name-to-consumption mapping for all meters in a property.

    Returns:
        (consumptions, main_consumption, unmetered_consumption)
        where consumptions maps meter names (and "_unmetered") to Decimal values.
    """
    consumptions: dict[str, Decimal] = {}

    main_meter = get_main_meter_for_property(db, property_id)
    main_consumption: Decimal | None = None
    if main_meter:
        main_consumption = compute_meter_consumption(
            db, main_meter.id, start_timestamp, end_timestamp
        )

    submeters = get_submeters_for_property(db, property_id)
    total_submetered = Decimal("0")

    for submeter in submeters:
        consumption = compute_meter_consumption(db, submeter.id, start_timestamp, end_timestamp)
        if consumption is not None:
            name = submeter.name or str(submeter.id)
            consumptions[name] = consumption
            total_submetered += consumption

    unmetered = _compute_unmetered(main_consumption, [total_submetered])
    if unmetered is not None:
        consumptions["_unmetered"] = unmetered

    return consumptions, main_consumption, unmetered


def _compute_unmetered(
    main_value: Decimal | None,
    submeter_values: list[Decimal],
) -> Decimal | None:
    """Compute unmetered value: main - sum(submeters), clamped to 0."""
    if main_value is None:
        return None
    total_submetered = sum(submeter_values, Decimal("0"))
    return max(Decimal("0"), main_value - total_submetered)
