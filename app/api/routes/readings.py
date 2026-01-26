"""MeterReading routes for ledger operations."""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.meter_reading import (
    CostDistributionResult,
    MeterReadingBulkCreate,
    MeterReadingCreate,
    MeterReadingHistory,
    MeterReadingResponse,
    PropertyConsumptionSummary,
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


@router.get("/property/{property_id}/consumption", response_model=PropertyConsumptionSummary)
def get_property_consumption(
    property_id: int,
    start_timestamp: datetime = Query(..., description="Start of period"),
    end_timestamp: datetime = Query(..., description="End of period"),
    db: Session = Depends(get_db),
):
    """
    Get consumption for a property over a period.

    Consumption is calculated as: end_reading - start_reading for each meter.
    Returns consumption for main meter, each submeter, and computed unmetered consumption.
    """
    return reading_service.get_property_consumption(db, property_id, start_timestamp, end_timestamp)


@router.get("/property/{property_id}/cost-distribution", response_model=CostDistributionResult)
def get_cost_distribution(
    property_id: int,
    start_timestamp: datetime = Query(..., description="Start of period"),
    end_timestamp: datetime = Query(..., description="End of period"),
    total_cost: Decimal = Query(..., description="Total cost to distribute"),
    db: Session = Depends(get_db),
):
    """
    Distribute costs across submeters based on consumption.

    The cost distribution works as follows:
    1. Calculate each submeter's consumption for the period
    2. Calculate each submeter's share of the total submetered consumption
    3. Distribute the unmetered consumption proportionally among submeters
    4. Allocate the total cost based on each submeter's share of total consumption
    """
    return reading_service.distribute_costs(
        db, property_id, start_timestamp, end_timestamp, total_cost
    )
