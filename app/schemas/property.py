"""Property Pydantic schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel


class PropertyBase(BaseModel):
    """Base property schema."""

    display_name: str


class PropertyCreate(PropertyBase):
    """Schema for creating a new property."""

    address: str | None = None


class PropertyUpdate(BaseModel):
    """Schema for updating a property."""

    display_name: str | None = None
    address: str | None = None
    is_active: bool | None = None


class PropertyResponse(PropertyBase):
    """Schema for property response."""

    id: int
    address: str | None
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}
