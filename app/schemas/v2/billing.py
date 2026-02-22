"""V2 billing schemas for cost allocation formulas and distribution."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


class CostFormulaCreate(BaseModel):
    """Schema for creating a cost allocation formula.

    Terms map meter names to coefficients. The formula computes:
        cost = total_cost * sum(coeff * consumption[meter]) / main_meter_consumption

    Use the special key "_unmetered" to reference unmetered consumption.
    """

    property_id: int
    name: str
    terms: dict[str, Decimal]

    @field_validator("terms")
    @classmethod
    def validate_terms(cls, v: dict[str, Decimal]) -> dict[str, Decimal]:
        """Validate that terms are not empty and keys are non-empty."""
        if not v:
            raise ValueError("Terms must not be empty")
        for key in v:
            if not key or not key.strip():
                raise ValueError("Term keys must not be empty")
        return v


class CostFormulaUpdate(BaseModel):
    """Schema for updating a cost allocation formula."""

    name: str | None = None
    terms: dict[str, Decimal] | None = None
    is_active: bool | None = None

    @field_validator("terms")
    @classmethod
    def validate_terms(cls, v: dict[str, Decimal] | None) -> dict[str, Decimal] | None:
        """Validate terms if provided."""
        if v is not None:
            if not v:
                raise ValueError("Terms must not be empty")
            for key in v:
                if not key or not key.strip():
                    raise ValueError("Term keys must not be empty")
        return v


class CostFormulaResponse(BaseModel):
    """Schema for cost formula response."""

    id: int
    property_id: int
    name: str
    terms: dict[str, Decimal]
    created_at: datetime
    is_active: bool


class FormulaShareResult(BaseModel):
    """Result of evaluating a single formula for cost distribution."""

    formula_id: int
    name: str
    terms: dict[str, Decimal]
    weighted_consumption: Decimal
    cost: Decimal


class CostDistributionResultV2(BaseModel):
    """Result of distributing costs using user-defined formulas."""

    property_id: int
    start_timestamp: datetime
    end_timestamp: datetime
    total_cost: Decimal
    main_meter_consumption: Decimal | None
    unmetered_consumption: Decimal | None
    meter_consumptions: dict[str, Decimal]
    shares: list[FormulaShareResult]
