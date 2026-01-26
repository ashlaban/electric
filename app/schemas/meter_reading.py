"""MeterReading Pydantic schemas for request/response validation."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


class MeterReadingBase(BaseModel):
    """Base meter reading schema."""

    reading_timestamp: datetime
    value: Decimal


class MeterReadingCreate(MeterReadingBase):
    """Schema for creating a single meter reading."""

    meter_id: int


class MeterReadingBulkCreate(BaseModel):
    """Schema for submitting multiple readings for a property at once."""

    property_id: int
    reading_timestamp: datetime
    main_meter_value: Decimal
    submeter_readings: dict[str, Decimal]  # {"gg": 100.5, "sg": 50.2}

    @field_validator("submeter_readings")
    @classmethod
    def validate_submeter_names(cls, v: dict[str, Decimal]) -> dict[str, Decimal]:
        """Validate submeter reading names are not empty."""
        for name in v:
            if not name or not name.strip():
                raise ValueError("Submeter names cannot be empty")
        return v


class MeterReadingResponse(MeterReadingBase):
    """Schema for meter reading response."""

    id: int
    meter_id: int
    created_at: datetime
    recorded_by_user_id: int | None

    model_config = {"from_attributes": True}


class SubMeterReading(BaseModel):
    """Schema for a submeter reading in summaries."""

    name: str
    location: str | None
    value: Decimal


class PropertyReadingSummary(BaseModel):
    """Complete reading summary for a property including computed values."""

    property_id: int
    reading_timestamp: datetime
    main_meter: Decimal | None
    submeters: list[SubMeterReading]
    unmetered: Decimal | None  # Computed: main_meter - sum(submeters)


class MeterReadingHistory(BaseModel):
    """Schema for paginated meter reading history."""

    meter_id: int
    readings: list[MeterReadingResponse]
    total: int
    limit: int
    offset: int


# Consumption calculation schemas


class SubMeterConsumption(BaseModel):
    """Schema for a submeter's consumption in a period."""

    name: str
    meter_id: int
    location: str | None
    start_value: Decimal
    end_value: Decimal
    consumption: Decimal  # end_value - start_value


class PropertyConsumptionSummary(BaseModel):
    """Consumption summary for a property over a period."""

    property_id: int
    start_timestamp: datetime
    end_timestamp: datetime
    main_meter_consumption: Decimal | None  # Total property consumption
    submeters: list[SubMeterConsumption]
    total_submetered_consumption: Decimal  # Sum of all submeter consumption
    unmetered_consumption: Decimal | None  # main_meter - sum(submeters)


# Cost distribution schemas


class SubMeterCostShare(BaseModel):
    """Schema for a submeter's share of costs."""

    name: str
    meter_id: int
    location: str | None
    consumption: Decimal
    consumption_share: Decimal  # Percentage of total submetered consumption (0-1)
    unmetered_share: Decimal  # Share of unmetered consumption
    total_consumption: Decimal  # consumption + unmetered_share
    cost: Decimal  # Allocated cost


class CostDistributionResult(BaseModel):
    """Result of distributing costs across submeters for a property."""

    property_id: int
    start_timestamp: datetime
    end_timestamp: datetime
    total_cost: Decimal  # Input: total cost to distribute
    main_meter_consumption: Decimal | None
    unmetered_consumption: Decimal | None
    submeters: list[SubMeterCostShare]
