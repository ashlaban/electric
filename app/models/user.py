"""User Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    """Base user schema with common attributes."""

    name: str = Field(..., min_length=1, max_length=255, description="User name")
    phone_number: str | None = Field(None, max_length=20, description="Phone number")
    default_meter_id: UUID | None = Field(None, description="Default meter ID")


class UserCreate(UserBase):
    """Schema for creating a new user."""

    pass


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    name: str | None = Field(None, min_length=1, max_length=255, description="User name")
    phone_number: str | None = Field(None, max_length=20, description="Phone number")
    default_meter_id: UUID | None = Field(None, description="Default meter ID")
    is_active: bool | None = Field(None, description="Whether the user is active")


class UserResponse(UserBase):
    """Schema for user responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    property_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
