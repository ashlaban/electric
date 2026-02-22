"""V2 MeterReading routes with support for absolute and relative readings."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.v2.readings import (
    BulkReadingCreateV2,
    ConsumptionSummaryV2,
    MeterReadingHistoryV2,
    PropertyReadingSummaryV2,
    ReadingCreateV2,
    ReadingResponseV2,
)
from app.services.v2 import readings as reading_service

router = APIRouter(prefix="/readings", tags=["v2-readings"])


@router.post(
    "/",
    response_model=ReadingResponseV2,
    status_code=status.HTTP_201_CREATED,
)
def create_reading(
    reading_data: ReadingCreateV2,
    db: Session = Depends(get_db),
) -> ReadingResponseV2:
    """Record a single meter reading.

    Supports both absolute (cumulative kWh) and relative (period consumption kWh) readings.
    """
    reading = reading_service.create_reading(db, reading_data, user_id=None)
    return ReadingResponseV2.model_validate(reading)


@router.post(
    "/bulk",
    response_model=list[ReadingResponseV2],
    status_code=status.HTTP_201_CREATED,
)
def create_bulk_readings(
    bulk_data: BulkReadingCreateV2,
    db: Session = Depends(get_db),
) -> list[ReadingResponseV2]:
    """Record multiple meter readings for a property at once.

    All readings in the batch share the same reading_type and timestamp.
    """
    readings = reading_service.create_bulk_readings(db, bulk_data, user_id=None)
    return [ReadingResponseV2.model_validate(r) for r in readings]


@router.get(
    "/property/{property_id}/summary",
    response_model=PropertyReadingSummaryV2,
)
def get_property_reading_summary(
    property_id: int,
    reading_timestamp: datetime = Query(..., description="Timestamp to get readings for"),
    db: Session = Depends(get_db),
) -> PropertyReadingSummaryV2:
    """Get all meter readings for a property at a specific timestamp.

    Includes computed unmetered value (virtual submeter).
    """
    return reading_service.get_property_reading_summary(db, property_id, reading_timestamp)


@router.get(
    "/property/{property_id}/latest",
    response_model=PropertyReadingSummaryV2 | None,
)
def get_latest_property_readings(
    property_id: int,
    db: Session = Depends(get_db),
) -> PropertyReadingSummaryV2 | None:
    """Get the most recent readings for a property including computed unmetered."""
    return reading_service.get_latest_readings_for_property(db, property_id)


@router.get(
    "/meter/{meter_id}/history",
    response_model=MeterReadingHistoryV2,
)
def get_meter_reading_history(
    meter_id: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> MeterReadingHistoryV2:
    """Get reading history for a specific meter with pagination."""
    readings, total = reading_service.get_readings_history(db, meter_id, limit, offset)
    return MeterReadingHistoryV2(
        meter_id=meter_id,
        readings=[ReadingResponseV2.model_validate(r) for r in readings],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/property/{property_id}/consumption",
    response_model=ConsumptionSummaryV2,
)
def get_property_consumption(
    property_id: int,
    start_timestamp: datetime = Query(..., description="Start of period"),
    end_timestamp: datetime = Query(..., description="End of period"),
    db: Session = Depends(get_db),
) -> ConsumptionSummaryV2:
    """Get consumption for a property over a period.

    Handles both absolute and relative reading types.
    Includes unmetered consumption as a virtual submeter.
    """
    return reading_service.get_property_consumption(db, property_id, start_timestamp, end_timestamp)
