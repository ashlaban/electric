"""Meter Pydantic schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, model_validator

from app.models.enums import MeterType, SubMeterKind


class MainMeterCreate(BaseModel):
    """Schema for creating a main meter."""

    property_id: int


class SubMeterCreate(BaseModel):
    """Schema for creating a submeter (all submeters are physical)."""

    property_id: int
    name: str
    location: str | None = None


class MeterResponse(BaseModel):
    """Schema for meter response."""

    id: int
    property_id: int
    meter_type: MeterType
    sub_meter_kind: SubMeterKind | None
    name: str | None
    location: str | None
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class MeterUpdate(BaseModel):
    """Schema for updating a meter."""

    name: str | None = None
    location: str | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "MeterUpdate":
        """Ensure at least one field is provided for update."""
        if all(v is None for v in [self.name, self.location, self.is_active]):
            raise ValueError("At least one field must be provided for update")
        return self
