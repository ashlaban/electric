"""Property API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.property import PropertyCreate, PropertyResponse, PropertyUpdate
from app.services import property_service

router = APIRouter(prefix="/properties", tags=["properties"])


@router.post("", response_model=PropertyResponse, status_code=201)
async def create_property(
    property_data: PropertyCreate,
    db: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """Create a new property with default meters (total, gg, sg, unmetered)."""
    property_obj = await property_service.create_property(db, property_data)
    return PropertyResponse.model_validate(property_obj)


@router.get("", response_model=list[PropertyResponse])
async def list_properties(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[PropertyResponse]:
    """List all properties."""
    properties = await property_service.get_properties(db, skip, limit)
    return [PropertyResponse.model_validate(p) for p in properties]


@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """Get a property by ID."""
    property_obj = await property_service.get_property(db, property_id)
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    return PropertyResponse.model_validate(property_obj)


@router.patch("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: UUID,
    property_data: PropertyUpdate,
    db: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """Update a property."""
    property_obj = await property_service.update_property(db, property_id, property_data)
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    return PropertyResponse.model_validate(property_obj)


@router.delete("/{property_id}", status_code=204)
async def delete_property(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a property."""
    success = await property_service.delete_property(db, property_id)
    if not success:
        raise HTTPException(status_code=404, detail="Property not found")
