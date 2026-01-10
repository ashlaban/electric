"""Property Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PropertyBase(BaseModel):
    """Base property schema with common attributes."""

    name: str = Field(..., min_length=1, max_length=255, description="Property name")
    address: str | None = Field(None, max_length=500, description="Property address")


class PropertyCreate(PropertyBase):
    """Schema for creating a new property."""

    pass


class PropertyUpdate(BaseModel):
    """Schema for updating a property."""

    name: str | None = Field(None, min_length=1, max_length=255, description="Property name")
    address: str | None = Field(None, max_length=500, description="Property address")


class PropertyResponse(PropertyBase):
    """Schema for property responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
