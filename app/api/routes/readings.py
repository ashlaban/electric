"""MeterReading routes for ledger operations."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.meter_reading import (
    MeterReadingBulkCreate,
    MeterReadingCreate,
    MeterReadingHistory,
    MeterReadingResponse,
    PropertyReadingSummary,
)
from app.services import meter_reading as reading_service

router = APIRouter(prefix="/readings", tags=["meter-readings"])


@router.post(
    "/",
    response_model=MeterReadingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reading(
    reading_data: MeterReadingCreate,
    db: Session = Depends(get_db),
):
    """Record a single meter reading."""
    return reading_service.create_reading(db, reading_data, user_id=None)


@router.post(
    "/bulk",
    response_model=list[MeterReadingResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_bulk_readings(
    bulk_data: MeterReadingBulkCreate,
    db: Session = Depends(get_db),
):
    """Record multiple meter readings for a property at once."""
    return reading_service.create_bulk_readings(db, bulk_data, user_id=None)


@router.get("/property/{property_id}/summary", response_model=PropertyReadingSummary)
def get_property_reading_summary(
    property_id: int,
    reading_timestamp: datetime = Query(..., description="Timestamp to get readings for"),
    db: Session = Depends(get_db),
):
    """
    Get all meter readings for a property at a specific timestamp.

    Includes computed unmetered value.
    """
    return reading_service.get_property_reading_summary(db, property_id, reading_timestamp)


@router.get("/property/{property_id}/latest", response_model=PropertyReadingSummary | None)
def get_latest_property_readings(
    property_id: int,
    db: Session = Depends(get_db),
):
    """Get the most recent readings for a property including computed unmetered."""
    return reading_service.get_latest_readings_for_property(db, property_id)


@router.get("/meter/{meter_id}/history", response_model=MeterReadingHistory)
def get_meter_reading_history(
    meter_id: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Get reading history for a specific meter with pagination."""
    readings, total = reading_service.get_readings_history(db, meter_id, limit, offset)
    return MeterReadingHistory(
        meter_id=meter_id,
        readings=[MeterReadingResponse.model_validate(r) for r in readings],
        total=total,
        limit=limit,
        offset=offset,
    )
