"""Property service for business logic."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import MeterType
from app.models.meter import Meter
from app.models.property import Property
from app.models.user import User
from app.schemas.property import PropertyCreate, PropertyUpdate


def create_property(db: Session, property_data: PropertyCreate) -> Property:
    """Create a new property with its main meter."""
    db_property = Property(
        display_name=property_data.display_name,
        address=property_data.address,
    )
    db.add(db_property)
    db.flush()  # Get property.id

    # Auto-create main meter for the property
    main_meter = Meter(
        property_id=db_property.id,
        meter_type=MeterType.MAIN_METER,
    )
    db.add(main_meter)

    db.commit()
    db.refresh(db_property)
    return db_property


def get_property(db: Session, property_id: int) -> Property:
    """Get a property by ID."""
    db_property = db.query(Property).filter(Property.id == property_id).first()
    if not db_property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )
    return db_property


def get_properties(db: Session, skip: int = 0, limit: int = 100) -> list[Property]:
    """Get all properties with pagination."""
    return db.query(Property).offset(skip).limit(limit).all()


def update_property(
    db: Session,
    property_id: int,
    property_data: PropertyUpdate,
) -> Property:
    """Update a property."""
    db_property = get_property(db, property_id)

    update_data = property_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_property, field, value)

    db.commit()
    db.refresh(db_property)
    return db_property


def get_properties_for_user(db: Session, user_id: int) -> list[Property]:
    """Get all properties associated with a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return list(user.properties)


def associate_user_with_property(
    db: Session,
    user_id: int,
    property_id: int,
) -> None:
    """Associate a user with a property."""
    user = db.query(User).filter(User.id == user_id).first()
    db_property = db.query(Property).filter(Property.id == property_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if not db_property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    if db_property not in user.properties:
        user.properties.append(db_property)
        db.commit()


def disassociate_user_from_property(
    db: Session,
    user_id: int,
    property_id: int,
) -> None:
    """Remove a user's association with a property."""
    user = db.query(User).filter(User.id == user_id).first()
    db_property = db.query(Property).filter(Property.id == property_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if not db_property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    if db_property in user.properties:
        user.properties.remove(db_property)
        db.commit()
