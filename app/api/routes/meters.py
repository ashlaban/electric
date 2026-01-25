"""Meter routes for meter management."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.meter import (
    MainMeterCreate,
    MeterResponse,
    MeterUpdate,
    SubMeterCreate,
)
from app.services import meter as meter_service

router = APIRouter(prefix="/meters", tags=["meters"])


@router.post(
    "/main",
    response_model=MeterResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_main_meter(
    meter_data: MainMeterCreate,
    db: Session = Depends(get_db),
):
    """Create a main meter for a property."""
    return meter_service.create_main_meter(db, meter_data)


@router.post(
    "/submeter",
    response_model=MeterResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_submeter(
    meter_data: SubMeterCreate,
    db: Session = Depends(get_db),
):
    """Create a submeter for a property."""
    return meter_service.create_submeter(db, meter_data)


@router.get("/{meter_id}", response_model=MeterResponse)
def get_meter(
    meter_id: int,
    db: Session = Depends(get_db),
):
    """Get a meter by ID."""
    return meter_service.get_meter(db, meter_id)


@router.patch("/{meter_id}", response_model=MeterResponse)
def update_meter(
    meter_id: int,
    meter_data: MeterUpdate,
    db: Session = Depends(get_db),
):
    """Update a meter."""
    return meter_service.update_meter(db, meter_id, meter_data)
