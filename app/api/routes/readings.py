"""Meter reading API routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.meter_reading import (
    MeterReadingCreate,
    MeterReadingResponse,
    MeterReadingUpdate,
)
from app.services import meter_reading_service

router = APIRouter(tags=["readings"])


@router.post(
    "/meters/{meter_id}/readings", response_model=MeterReadingResponse, status_code=201
)
async def create_reading(
    meter_id: UUID,
    reading_data: MeterReadingCreate,
    db: AsyncSession = Depends(get_db),
) -> MeterReadingResponse:
    """Create a new meter reading (only for physical meters)."""
    reading = await meter_reading_service.create_reading(db, meter_id, reading_data)
    return MeterReadingResponse.model_validate(reading)


@router.get("/meters/{meter_id}/readings", response_model=list[MeterReadingResponse])
async def list_readings(
    meter_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[MeterReadingResponse]:
    """List readings for a meter with optional date filtering."""
    readings = await meter_reading_service.get_readings_by_meter(
        db, meter_id, start_date, end_date, skip, limit
    )
    return [MeterReadingResponse.model_validate(r) for r in readings]


@router.get("/meters/{meter_id}/calculated-readings")
async def get_calculated_readings(
    meter_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get calculated readings for a virtual meter."""
    # First get the meter to find its property
    from app.services.meter_service import get_meter

    meter = await get_meter(db, meter_id)
    if not meter:
        raise HTTPException(status_code=404, detail="Meter not found")

    virtual_readings = await meter_reading_service.calculate_virtual_readings(
        db, meter.property_id, start_date, end_date
    )
    return virtual_readings


@router.get("/readings/{reading_id}", response_model=MeterReadingResponse)
async def get_reading(
    reading_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> MeterReadingResponse:
    """Get a specific reading by ID."""
    reading = await meter_reading_service.get_reading(db, reading_id)
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
    return MeterReadingResponse.model_validate(reading)


@router.patch("/readings/{reading_id}", response_model=MeterReadingResponse)
async def update_reading(
    reading_id: UUID,
    reading_data: MeterReadingUpdate,
    db: AsyncSession = Depends(get_db),
) -> MeterReadingResponse:
    """Update a meter reading (for correcting errors)."""
    reading = await meter_reading_service.update_reading(db, reading_id, reading_data)
    if not reading:
        raise HTTPException(status_code=404, detail="Reading not found")
    return MeterReadingResponse.model_validate(reading)


@router.delete("/readings/{reading_id}", status_code=204)
async def delete_reading(
    reading_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a meter reading."""
    success = await meter_reading_service.delete_reading(db, reading_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reading not found")
