"""Meter API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.meter import MeterCreate, MeterResponse, MeterUpdate
from app.services import meter_service

router = APIRouter(tags=["meters"])


@router.post("/properties/{property_id}/meters", response_model=MeterResponse, status_code=201)
async def create_meter(
    property_id: UUID,
    meter_data: MeterCreate,
    db: AsyncSession = Depends(get_db),
) -> MeterResponse:
    """Create a new meter for a property."""
    meter = await meter_service.create_meter(db, property_id, meter_data)
    return MeterResponse.model_validate(meter)


@router.get("/properties/{property_id}/meters", response_model=list[MeterResponse])
async def list_meters(
    property_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[MeterResponse]:
    """List all meters for a property."""
    meters = await meter_service.get_meters_by_property(db, property_id, skip, limit)
    return [MeterResponse.model_validate(m) for m in meters]


@router.get("/meters/{meter_id}", response_model=MeterResponse)
async def get_meter(
    meter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> MeterResponse:
    """Get a meter by ID."""
    meter = await meter_service.get_meter(db, meter_id)
    if not meter:
        raise HTTPException(status_code=404, detail="Meter not found")
    return MeterResponse.model_validate(meter)


@router.patch("/meters/{meter_id}", response_model=MeterResponse)
async def update_meter(
    meter_id: UUID,
    meter_data: MeterUpdate,
    db: AsyncSession = Depends(get_db),
) -> MeterResponse:
    """Update a meter."""
    meter = await meter_service.update_meter(db, meter_id, meter_data)
    if not meter:
        raise HTTPException(status_code=404, detail="Meter not found")
    return MeterResponse.model_validate(meter)


@router.delete("/meters/{meter_id}", status_code=204)
async def deactivate_meter(
    meter_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deactivate a meter."""
    success = await meter_service.deactivate_meter(db, meter_id)
    if not success:
        raise HTTPException(status_code=404, detail="Meter not found")
