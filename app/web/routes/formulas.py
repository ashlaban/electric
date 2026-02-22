"""Cost formula management web routes."""

from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.v2.billing import CostFormulaCreate, CostFormulaUpdate
from app.services.meter import get_meters_for_property
from app.services.property import get_property
from app.services.v2.billing import (
    create_formula,
    delete_formula,
    formula_to_response,
    get_formula,
    get_formulas_for_property,
    update_formula,
)
from app.web.dependencies import add_flash_message, get_current_user_from_session
from app.web.template_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse, response_model=None)
async def list_formulas(
    request: Request,
    property_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """List cost formulas for a property."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse(f"/login?next=/formulas?property_id={property_id}", status_code=303)

    prop = get_property(db, property_id)
    formulas = get_formulas_for_property(db, property_id, active_only=False)
    formula_responses = [formula_to_response(f) for f in formulas]

    return templates.TemplateResponse(
        request,
        "formulas/list.html",
        {
            "user": user,
            "property": prop,
            "property_id": property_id,
            "formulas": formula_responses,
        },
    )


@router.get("/create", response_class=HTMLResponse, response_model=None)
async def create_formula_page(
    request: Request,
    property_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display create formula form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    prop = get_property(db, property_id)
    meters = get_meters_for_property(db, property_id)

    return templates.TemplateResponse(
        request,
        "formulas/create.html",
        {
            "user": user,
            "property": prop,
            "property_id": property_id,
            "meters": meters,
        },
    )


@router.post("/create", response_class=HTMLResponse, response_model=None)
async def create_formula_submit(
    request: Request,
    property_id: int = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Process create formula form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    form_data = await request.form()

    # Collect terms from form fields named term_meter_* and term_coeff_*
    terms: dict[str, Decimal] = {}
    for key, value in form_data.items():
        if key.startswith("term_coeff_") and value:
            meter_key = key.replace("term_coeff_", "term_meter_")
            meter_name = str(form_data.get(meter_key, ""))
            if meter_name.strip():
                try:
                    terms[meter_name.strip()] = Decimal(str(value))
                except InvalidOperation:
                    add_flash_message(
                        request, f"Invalid coefficient value for {meter_name}.", "error"
                    )
                    return RedirectResponse(
                        f"/formulas/create?property_id={property_id}", status_code=303
                    )

    if not terms:
        add_flash_message(request, "At least one term is required.", "error")
        return RedirectResponse(f"/formulas/create?property_id={property_id}", status_code=303)

    try:
        formula_data = CostFormulaCreate(
            property_id=property_id,
            name=name.strip(),
            description=description.strip() or None,
            terms=terms,
        )
        create_formula(db, formula_data)
        add_flash_message(request, f"Formula '{name}' created successfully!", "success")
    except Exception as e:
        detail = getattr(e, "detail", str(e))
        add_flash_message(request, f"Error creating formula: {detail}", "error")

    return RedirectResponse(f"/formulas?property_id={property_id}", status_code=303)


@router.get("/{formula_id}/edit", response_class=HTMLResponse, response_model=None)
async def edit_formula_page(
    request: Request,
    formula_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display edit formula form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    formula = get_formula(db, formula_id)
    prop = get_property(db, formula.property_id)
    meters = get_meters_for_property(db, formula.property_id)
    formula_resp = formula_to_response(formula)

    return templates.TemplateResponse(
        request,
        "formulas/edit.html",
        {
            "user": user,
            "property": prop,
            "property_id": formula.property_id,
            "formula": formula_resp,
            "meters": meters,
        },
    )


@router.post("/{formula_id}/edit", response_class=HTMLResponse, response_model=None)
async def edit_formula_submit(
    request: Request,
    formula_id: int,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Process edit formula form."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    formula = get_formula(db, formula_id)
    form_data = await request.form()

    # Collect terms
    terms: dict[str, Decimal] = {}
    for key, value in form_data.items():
        if key.startswith("term_coeff_") and value:
            meter_key = key.replace("term_coeff_", "term_meter_")
            meter_name = str(form_data.get(meter_key, ""))
            if meter_name.strip():
                try:
                    terms[meter_name.strip()] = Decimal(str(value))
                except InvalidOperation:
                    add_flash_message(
                        request, f"Invalid coefficient value for {meter_name}.", "error"
                    )
                    return RedirectResponse(f"/formulas/{formula_id}/edit", status_code=303)

    if not terms:
        add_flash_message(request, "At least one term is required.", "error")
        return RedirectResponse(f"/formulas/{formula_id}/edit", status_code=303)

    try:
        update_data = CostFormulaUpdate(
            name=name.strip(),
            description=description.strip() or None,
            terms=terms,
        )
        update_formula(db, formula_id, update_data)
        add_flash_message(request, f"Formula '{name}' updated successfully!", "success")
    except Exception as e:
        detail = getattr(e, "detail", str(e))
        add_flash_message(request, f"Error updating formula: {detail}", "error")

    return RedirectResponse(f"/formulas?property_id={formula.property_id}", status_code=303)


@router.post("/{formula_id}/delete", response_class=HTMLResponse, response_model=None)
async def delete_formula_submit(
    request: Request,
    formula_id: int,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Soft-delete (deactivate) a cost formula."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    formula = get_formula(db, formula_id)
    property_id = formula.property_id

    delete_formula(db, formula_id)
    add_flash_message(request, f"Formula '{formula.name}' deactivated.", "success")
    return RedirectResponse(f"/formulas?property_id={property_id}", status_code=303)
