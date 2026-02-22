"""V2 MeterReading schemas with support for absolute and relative readings."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.models.enums import ReadingType


class ReadingCreateV2(BaseModel):
    """Schema for creating a single meter reading in v2."""

    meter_id: int
    reading_timestamp: datetime
    value: Decimal
    reading_type: ReadingType = ReadingType.ABSOLUTE


class BulkReadingCreateV2(BaseModel):
    """Schema for submitting multiple readings for a property at once in v2."""

    property_id: int
    reading_timestamp: datetime
    reading_type: ReadingType = ReadingType.ABSOLUTE
    main_meter_value: Decimal
    submeter_readings: dict[str, Decimal]

    @field_validator("submeter_readings")
    @classmethod
    def validate_submeter_names(cls, v: dict[str, Decimal]) -> dict[str, Decimal]:
        """Validate submeter reading names are not empty."""
        for name in v:
            if not name or not name.strip():
                raise ValueError("Submeter names cannot be empty")
        return v


class ReadingResponseV2(BaseModel):
    """Schema for meter reading response in v2."""

    id: int
    meter_id: int
    reading_timestamp: datetime
    value: Decimal
    reading_type: str
    created_at: datetime
    recorded_by_user_id: int | None

    model_config = {"from_attributes": True}


class SubMeterReadingV2(BaseModel):
    """Schema for a submeter reading in summaries."""

    name: str
    meter_id: int
    location: str | None
    value: Decimal


class PropertyReadingSummaryV2(BaseModel):
    """Complete reading summary for a property including computed values."""

    property_id: int
    reading_timestamp: datetime
    main_meter: Decimal | None
    submeters: list[SubMeterReadingV2]
    unmetered: Decimal | None


class SubMeterConsumptionV2(BaseModel):
    """Schema for a submeter's consumption in a period."""

    name: str
    meter_id: int
    location: str | None
    consumption: Decimal
    is_virtual: bool = False


class ConsumptionSummaryV2(BaseModel):
    """Consumption summary for a property over a period."""

    property_id: int
    start_timestamp: datetime
    end_timestamp: datetime
    main_meter_consumption: Decimal | None
    submeters: list[SubMeterConsumptionV2]
    total_submetered_consumption: Decimal
    unmetered_consumption: Decimal | None


class MeterReadingHistoryV2(BaseModel):
    """Schema for paginated meter reading history."""

    meter_id: int
    readings: list[ReadingResponseV2]
    total: int
    limit: int
    offset: int
