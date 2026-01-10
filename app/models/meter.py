"""Meter Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.meter import MeterType


class MeterBase(BaseModel):
    """Base meter schema with common attributes."""

    meter_code: str = Field(
        ..., min_length=1, max_length=50, description="Meter code (e.g., 'gg', 'sg', 'total')"
    )
    meter_type: MeterType = Field(..., description="Type of meter")
    description: str | None = Field(None, max_length=255, description="Meter description")
    unit: str = Field(default="kWh", max_length=20, description="Unit of measurement")


class MeterCreate(MeterBase):
    """Schema for creating a new meter."""

    pass


class MeterUpdate(BaseModel):
    """Schema for updating a meter."""

    description: str | None = Field(None, max_length=255, description="Meter description")
    unit: str | None = Field(None, max_length=20, description="Unit of measurement")
    is_active: bool | None = Field(None, description="Whether the meter is active")


class MeterResponse(MeterBase):
    """Schema for meter responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    property_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
