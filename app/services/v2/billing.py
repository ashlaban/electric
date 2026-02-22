"""V2 billing service for cost formula management and cost distribution."""

from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.cost_formula import CostFormula
from app.schemas.v2.billing import (
    CostDistributionResultV2,
    CostFormulaCreate,
    CostFormulaResponse,
    CostFormulaUpdate,
    FormulaShareResult,
)
from app.services.v2.readings import compute_consumption_map


def create_formula(
    db: Session,
    data: CostFormulaCreate,
) -> CostFormula:
    """Create a new cost allocation formula for a property."""
    # Check for duplicate name within property
    existing = (
        db.query(CostFormula)
        .filter(
            and_(
                CostFormula.property_id == data.property_id,
                CostFormula.name == data.name,
                CostFormula.is_active.is_(True),
            )
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Active formula with name '{data.name}' already exists for this property",
        )

    formula = CostFormula(
        property_id=data.property_id,
        name=data.name,
        description=data.description,
    )
    formula.set_terms(data.terms)
    db.add(formula)
    db.commit()
    db.refresh(formula)
    return formula


def get_formula(db: Session, formula_id: int) -> CostFormula:
    """Get a formula by ID."""
    formula = db.query(CostFormula).filter(CostFormula.id == formula_id).first()
    if not formula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost formula not found",
        )
    return formula


def get_formulas_for_property(
    db: Session,
    property_id: int,
    active_only: bool = True,
) -> list[CostFormula]:
    """Get all cost formulas for a property."""
    query = db.query(CostFormula).filter(CostFormula.property_id == property_id)
    if active_only:
        query = query.filter(CostFormula.is_active.is_(True))
    return query.all()


def update_formula(
    db: Session,
    formula_id: int,
    data: CostFormulaUpdate,
) -> CostFormula:
    """Update a cost formula."""
    formula = get_formula(db, formula_id)

    if data.name is not None:
        # Check for duplicate name if renaming
        existing = (
            db.query(CostFormula)
            .filter(
                and_(
                    CostFormula.property_id == formula.property_id,
                    CostFormula.name == data.name,
                    CostFormula.is_active.is_(True),
                    CostFormula.id != formula_id,
                )
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Active formula with name '{data.name}' already exists for this property",
            )
        formula.name = data.name

    if data.description is not None:
        formula.description = data.description

    if data.terms is not None:
        formula.set_terms(data.terms)

    if data.is_active is not None:
        formula.is_active = data.is_active

    db.commit()
    db.refresh(formula)
    return formula


def delete_formula(db: Session, formula_id: int) -> None:
    """Soft-delete a cost formula by deactivating it."""
    formula = get_formula(db, formula_id)
    formula.is_active = False
    db.commit()


def formula_to_response(formula: CostFormula) -> CostFormulaResponse:
    """Convert a CostFormula model to a response schema."""
    return CostFormulaResponse(
        id=formula.id,
        property_id=formula.property_id,
        name=formula.name,
        description=formula.description,
        terms=formula.get_terms(),
        created_at=formula.created_at,
        is_active=formula.is_active,
    )


def evaluate_formula(
    terms: dict[str, Decimal],
    consumptions: dict[str, Decimal],
    total_cost: Decimal,
    main_consumption: Decimal,
) -> Decimal:
    """Evaluate a cost formula.

    Formula: cost = total_cost * sum(coeff * consumption[meter]) / main_consumption
    """
    weighted = sum(
        coeff * consumptions.get(meter_name, Decimal("0")) for meter_name, coeff in terms.items()
    )
    if main_consumption <= 0:
        return Decimal("0")
    return (total_cost * weighted / main_consumption).quantize(Decimal("0.01"))


def distribute_costs(
    db: Session,
    property_id: int,
    start_timestamp: datetime,
    end_timestamp: datetime,
    total_cost: Decimal,
) -> CostDistributionResultV2:
    """Distribute costs across formulas using user-defined allocation rules.

    For each active formula, evaluates:
        cost = total_cost * sum(coeff * consumption[meter]) / main_meter_consumption
    """
    formulas = get_formulas_for_property(db, property_id, active_only=True)
    if not formulas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active cost formulas found for this property",
        )

    consumptions, main_consumption, unmetered = compute_consumption_map(
        db, property_id, start_timestamp, end_timestamp
    )

    if main_consumption is None or main_consumption <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Main meter consumption is zero or unavailable for this period",
        )

    shares: list[FormulaShareResult] = []
    for formula in formulas:
        terms = formula.get_terms()
        weighted = sum(
            (
                coeff * consumptions.get(meter_name, Decimal("0"))
                for meter_name, coeff in terms.items()
            ),
            Decimal("0"),
        )
        cost = evaluate_formula(terms, consumptions, total_cost, main_consumption)
        shares.append(
            FormulaShareResult(
                formula_id=formula.id,
                name=formula.name,
                description=formula.description,
                terms=terms,
                weighted_consumption=weighted,
                cost=cost,
            )
        )

    return CostDistributionResultV2(
        property_id=property_id,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        total_cost=total_cost,
        main_meter_consumption=main_consumption,
        unmetered_consumption=unmetered,
        meter_consumptions=consumptions,
        shares=shares,
    )
