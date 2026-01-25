"""Property routes for property management."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.meter import MeterResponse
from app.schemas.property import PropertyCreate, PropertyResponse, PropertyUpdate
from app.services import meter as meter_service
from app.services import property as property_service

router = APIRouter(prefix="/properties", tags=["properties"])


@router.post("/", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
def create_property(
    property_data: PropertyCreate,
    db: Session = Depends(get_db),
):
    """Create a new property with its main meter."""
    return property_service.create_property(db, property_data)


@router.get("/", response_model=list[PropertyResponse])
def list_properties(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List all properties with pagination."""
    return property_service.get_properties(db, skip=skip, limit=limit)


@router.get("/{property_id}", response_model=PropertyResponse)
def get_property(
    property_id: int,
    db: Session = Depends(get_db),
):
    """Get a property by ID."""
    return property_service.get_property(db, property_id)


@router.patch("/{property_id}", response_model=PropertyResponse)
def update_property(
    property_id: int,
    property_data: PropertyUpdate,
    db: Session = Depends(get_db),
):
    """Update a property."""
    return property_service.update_property(db, property_id, property_data)


@router.get("/{property_id}/meters", response_model=list[MeterResponse])
def get_property_meters(
    property_id: int,
    db: Session = Depends(get_db),
):
    """Get all meters for a property."""
    # Verify property exists
    property_service.get_property(db, property_id)
    return meter_service.get_meters_for_property(db, property_id)


@router.post(
    "/{property_id}/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def associate_user_with_property(
    property_id: int,
    user_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Associate a user with a property."""
    property_service.associate_user_with_property(db, user_id, property_id)


@router.delete(
    "/{property_id}/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def disassociate_user_from_property(
    property_id: int,
    user_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Remove a user's association with a property."""
    property_service.disassociate_user_from_property(db, user_id, property_id)
