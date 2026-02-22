"""V2 billing routes for cost allocation formulas and distribution."""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.v2.billing import (
    CostDistributionResultV2,
    CostFormulaCreate,
    CostFormulaResponse,
    CostFormulaUpdate,
)
from app.services.v2 import billing as billing_service

router = APIRouter(prefix="/billing", tags=["v2-billing"])


@router.post(
    "/formulas/",
    response_model=CostFormulaResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_formula(
    data: CostFormulaCreate,
    db: Session = Depends(get_db),
) -> CostFormulaResponse:
    """Create a cost allocation formula for a property.

    The formula defines how to compute one share of the total cost.
    Terms map meter names to coefficients:

        cost = total_cost * sum(coeff * consumption[meter]) / main_meter_consumption

    Use "_unmetered" as a key to reference the unmetered (virtual submeter) consumption.
    """
    formula = billing_service.create_formula(db, data)
    return billing_service.formula_to_response(formula)


@router.get(
    "/formulas/property/{property_id}",
    response_model=list[CostFormulaResponse],
)
def list_formulas(
    property_id: int,
    active_only: bool = Query(True, description="Only return active formulas"),
    db: Session = Depends(get_db),
) -> list[CostFormulaResponse]:
    """List all cost allocation formulas for a property."""
    formulas = billing_service.get_formulas_for_property(db, property_id, active_only)
    return [billing_service.formula_to_response(f) for f in formulas]


@router.get(
    "/formulas/{formula_id}",
    response_model=CostFormulaResponse,
)
def get_formula(
    formula_id: int,
    db: Session = Depends(get_db),
) -> CostFormulaResponse:
    """Get a cost allocation formula by ID."""
    formula = billing_service.get_formula(db, formula_id)
    return billing_service.formula_to_response(formula)


@router.patch(
    "/formulas/{formula_id}",
    response_model=CostFormulaResponse,
)
def update_formula(
    formula_id: int,
    data: CostFormulaUpdate,
    db: Session = Depends(get_db),
) -> CostFormulaResponse:
    """Update a cost allocation formula."""
    formula = billing_service.update_formula(db, formula_id, data)
    return billing_service.formula_to_response(formula)


@router.delete(
    "/formulas/{formula_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_formula(
    formula_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Soft-delete a cost allocation formula (deactivates it)."""
    billing_service.delete_formula(db, formula_id)


@router.get(
    "/property/{property_id}/distribute",
    response_model=CostDistributionResultV2,
)
def distribute_costs(
    property_id: int,
    start_timestamp: datetime = Query(..., description="Start of billing period"),
    end_timestamp: datetime = Query(..., description="End of billing period"),
    total_cost: Decimal = Query(..., description="Total cost to distribute"),
    db: Session = Depends(get_db),
) -> CostDistributionResultV2:
    """Distribute costs across tenants using the property's cost formulas.

    Each formula computes:
        cost = total_cost * sum(coeff * consumption[meter]) / main_meter_consumption

    The formulas are independent - each one defines a tenant's cost share.
    """
    return billing_service.distribute_costs(
        db, property_id, start_timestamp, end_timestamp, total_cost
    )
