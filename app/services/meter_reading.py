"""MeterReading service for business logic - the core ledger operations."""

from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.enums import MeterType
from app.models.meter import Meter
from app.models.meter_reading import MeterReading
from app.schemas.meter_reading import (
    CostDistributionResult,
    MeterReadingBulkCreate,
    MeterReadingCreate,
    PropertyConsumptionSummary,
    PropertyReadingSummary,
    SubMeterConsumption,
    SubMeterCostShare,
    SubMeterReading,
)
from app.services.meter import (
    get_main_meter_for_property,
    get_meters_for_property,
    get_submeter_by_name,
    get_submeters_for_property,
)


def compute_unmetered_value(
    main_meter_value: Decimal | None,
    submeter_values: list[Decimal],
) -> Decimal | None:
    """
    Compute the unmetered (common area) consumption.

    Formula: unmetered = main_meter - sum(submeters)

    Returns None if main meter value is missing.
    """
    if main_meter_value is None:
        return None

    total_submetered = sum(submeter_values, Decimal("0"))
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

    # Get submeter readings
    submeters = [m for m in meters if m.meter_type == MeterType.SUB_METER]

    submeter_readings: list[SubMeterReading] = []
    submeter_values: list[Decimal] = []

    for submeter in submeters:
        value = get_reading_value_at_timestamp(db, submeter.id, reading_timestamp)
        if value is not None:
            submeter_values.append(value)
            submeter_readings.append(
                SubMeterReading(
                    name=submeter.name or "",
                    location=submeter.location,
                    value=value,
                )
            )

    # Compute unmetered value
    unmetered = compute_unmetered_value(main_value, submeter_values)

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


def get_property_consumption(
    db: Session,
    property_id: int,
    start_timestamp: datetime,
    end_timestamp: datetime,
) -> PropertyConsumptionSummary:
    """
    Calculate consumption for a property over a period.

    Consumption is calculated as: end_reading - start_reading for each meter.
    """
    # Get main meter
    main_meter = get_main_meter_for_property(db, property_id)
    main_consumption: Decimal | None = None

    if main_meter:
        start_value = get_reading_value_at_timestamp(db, main_meter.id, start_timestamp)
        end_value = get_reading_value_at_timestamp(db, main_meter.id, end_timestamp)
        if start_value is not None and end_value is not None:
            main_consumption = end_value - start_value

    # Get submeter consumptions
    submeters = get_submeters_for_property(db, property_id)
    submeter_consumptions: list[SubMeterConsumption] = []
    total_submetered = Decimal("0")

    for submeter in submeters:
        start_value = get_reading_value_at_timestamp(db, submeter.id, start_timestamp)
        end_value = get_reading_value_at_timestamp(db, submeter.id, end_timestamp)

        if start_value is not None and end_value is not None:
            consumption = end_value - start_value
            total_submetered += consumption
            submeter_consumptions.append(
                SubMeterConsumption(
                    name=submeter.name or "",
                    meter_id=submeter.id,
                    location=submeter.location,
                    start_value=start_value,
                    end_value=end_value,
                    consumption=consumption,
                )
            )

    # Calculate unmetered consumption
    unmetered_consumption: Decimal | None = None
    if main_consumption is not None:
        unmetered_consumption = max(Decimal("0"), main_consumption - total_submetered)

    return PropertyConsumptionSummary(
        property_id=property_id,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        main_meter_consumption=main_consumption,
        submeters=submeter_consumptions,
        total_submetered_consumption=total_submetered,
        unmetered_consumption=unmetered_consumption,
    )


def distribute_costs(
    db: Session,
    property_id: int,
    start_timestamp: datetime,
    end_timestamp: datetime,
    total_cost: Decimal,
) -> CostDistributionResult:
    """
    Distribute costs across submeters based on consumption.

    The cost distribution works as follows:
    1. Calculate each submeter's consumption
    2. Calculate each submeter's share of the total submetered consumption
    3. Distribute the unmetered consumption proportionally among submeters
    4. Calculate each submeter's total consumption (own + unmetered share)
    5. Distribute the total cost based on total consumption
    """
    # Get consumption data
    consumption = get_property_consumption(db, property_id, start_timestamp, end_timestamp)

    submeter_cost_shares: list[SubMeterCostShare] = []
    total_consumption_for_cost = Decimal("0")

    # Calculate total consumption including unmetered distribution
    for sub in consumption.submeters:
        # Calculate share of unmetered consumption
        if (
            consumption.total_submetered_consumption > 0
            and consumption.unmetered_consumption is not None
        ):
            consumption_share = sub.consumption / consumption.total_submetered_consumption
            unmetered_share = consumption_share * consumption.unmetered_consumption
        else:
            consumption_share = Decimal("0")
            unmetered_share = Decimal("0")

        total_consumption = sub.consumption + unmetered_share
        total_consumption_for_cost += total_consumption

        submeter_cost_shares.append(
            SubMeterCostShare(
                name=sub.name,
                meter_id=sub.meter_id,
                location=sub.location,
                consumption=sub.consumption,
                consumption_share=consumption_share,
                unmetered_share=unmetered_share,
                total_consumption=total_consumption,
                cost=Decimal("0"),  # Will be calculated below
            )
        )

    # Distribute costs based on total consumption
    if total_consumption_for_cost > 0:
        for share in submeter_cost_shares:
            cost_ratio = share.total_consumption / total_consumption_for_cost
            share.cost = (cost_ratio * total_cost).quantize(Decimal("0.01"))

    return CostDistributionResult(
        property_id=property_id,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        total_cost=total_cost,
        main_meter_consumption=consumption.main_meter_consumption,
        unmetered_consumption=consumption.unmetered_consumption,
        submeters=submeter_cost_shares,
    )
