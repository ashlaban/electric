"""MeterReading Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MeterReadingBase(BaseModel):
    """Base meter reading schema with common attributes."""

    reading_value: Decimal = Field(..., gt=0, decimal_places=2, description="Meter reading value")
    reading_timestamp: datetime = Field(..., description="When the reading was taken")
    notes: str | None = Field(None, max_length=500, description="Optional notes")


class MeterReadingCreate(MeterReadingBase):
    """Schema for creating a new meter reading."""

    pass


class MeterReadingUpdate(BaseModel):
    """Schema for updating a meter reading."""

    reading_value: Decimal | None = Field(
        None, gt=0, decimal_places=2, description="Meter reading value"
    )
    reading_timestamp: datetime | None = Field(None, description="When the reading was taken")
    notes: str | None = Field(None, max_length=500, description="Optional notes")


class MeterReadingResponse(MeterReadingBase):
    """Schema for meter reading responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    meter_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by_user_id: UUID | None
