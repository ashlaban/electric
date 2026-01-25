"""Meter service for business logic."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import MeterType, SubMeterKind
from app.models.meter import Meter
from app.schemas.meter import MainMeterCreate, MeterUpdate, SubMeterCreate


def create_main_meter(db: Session, meter_data: MainMeterCreate) -> Meter:
    """Create a main meter for a property."""
    # Check if property already has a main meter
    existing = (
        db.query(Meter)
        .filter(
            Meter.property_id == meter_data.property_id,
            Meter.meter_type == MeterType.MAIN_METER,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Property already has a main meter",
        )

    db_meter = Meter(
        property_id=meter_data.property_id,
        meter_type=MeterType.MAIN_METER,
    )
    db.add(db_meter)
    db.commit()
    db.refresh(db_meter)
    return db_meter


def create_submeter(db: Session, meter_data: SubMeterCreate) -> Meter:
    """Create a submeter for a property."""
    # Check for duplicate submeter name on same property
    existing = (
        db.query(Meter)
        .filter(
            Meter.property_id == meter_data.property_id,
            Meter.name == meter_data.name,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Submeter with name '{meter_data.name}' already exists for this property",
        )

    db_meter = Meter(
        property_id=meter_data.property_id,
        meter_type=MeterType.SUB_METER,
        sub_meter_kind=meter_data.sub_meter_kind,
        name=meter_data.name,
        location=meter_data.location,
    )
    db.add(db_meter)
    db.commit()
    db.refresh(db_meter)
    return db_meter


def get_meter(db: Session, meter_id: int) -> Meter:
    """Get a meter by ID."""
    meter = db.query(Meter).filter(Meter.id == meter_id).first()
    if not meter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meter not found",
        )
    return meter


def get_meters_for_property(db: Session, property_id: int) -> list[Meter]:
    """Get all meters for a property."""
    return db.query(Meter).filter(Meter.property_id == property_id).all()


def get_main_meter_for_property(db: Session, property_id: int) -> Meter | None:
    """Get the main meter for a property."""
    return (
        db.query(Meter)
        .filter(
            Meter.property_id == property_id,
            Meter.meter_type == MeterType.MAIN_METER,
        )
        .first()
    )


def get_physical_submeters_for_property(db: Session, property_id: int) -> list[Meter]:
    """Get all physical submeters for a property."""
    return (
        db.query(Meter)
        .filter(
            Meter.property_id == property_id,
            Meter.meter_type == MeterType.SUB_METER,
            Meter.sub_meter_kind == SubMeterKind.PHYSICAL,
        )
        .all()
    )


def get_submeter_by_name(
    db: Session,
    property_id: int,
    name: str,
) -> Meter | None:
    """Get a submeter by name for a property."""
    return (
        db.query(Meter)
        .filter(
            Meter.property_id == property_id,
            Meter.name == name,
        )
        .first()
    )


def update_meter(db: Session, meter_id: int, meter_data: MeterUpdate) -> Meter:
    """Update a meter."""
    meter = get_meter(db, meter_id)

    update_data = meter_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(meter, field, value)

    db.commit()
    db.refresh(meter)
    return meter
