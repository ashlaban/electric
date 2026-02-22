"""Costs and trends web routes for mobile-first UI."""

import calendar
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.property import get_properties_for_user, get_property
from app.services.v2.billing import distribute_costs
from app.services.v2.readings import get_property_consumption
from app.web.dependencies import add_flash_message, get_current_user_from_session
from app.web.template_config import templates

# Submeter colors for trend charts
SUBMETER_COLORS = [
    "var(--primary)",
    "#e67e22",
    "#2ecc71",
    "#9b59b6",
    "#e74c3c",
    "#1abc9c",
]

router = APIRouter()


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    """Get first-of-month timestamps for a billing period."""
    start = datetime(year, month, 1, tzinfo=UTC)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=UTC)
    else:
        end = datetime(year, month + 1, 1, tzinfo=UTC)
    return start, end


def _prev_month(year: int, month: int) -> tuple[int, int]:
    """Return (year, month) for the previous month."""
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _next_month(year: int, month: int) -> tuple[int, int]:
    """Return (year, month) for the next month."""
    if month == 12:
        return year + 1, 1
    return year, month + 1


@router.get("/costs", response_class=HTMLResponse, response_model=None)
async def cost_breakdown(
    request: Request,
    property_id: int | None = None,
    total_cost: float = 0,
    year: int | None = None,
    month: int | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display monthly cost breakdown page."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login?next=/costs", status_code=303)

    # Resolve property
    if not property_id:
        property_id = user.default_property_id
    if not property_id:
        properties = get_properties_for_user(db, user.id)
        if properties:
            property_id = properties[0].id
        else:
            add_flash_message(request, "Create a property first.", "info")
            return RedirectResponse("/properties/create", status_code=303)

    prop = get_property(db, property_id)

    # Default to previous month if no date specified
    now = datetime.now(UTC)
    if not year or not month:
        prev_y, prev_m = _prev_month(now.year, now.month)
        year = prev_y
        month = prev_m

    start, end = _month_bounds(year, month)
    cost_decimal = Decimal(str(total_cost)) if total_cost else Decimal("0")

    cost_data = None
    error_reason = None
    if cost_decimal > 0:
        try:
            cost_data = distribute_costs(db, property_id, start, end, cost_decimal)
        except HTTPException as e:
            detail = e.detail if isinstance(e.detail, str) else str(e.detail)
            if "No active cost formulas" in detail:
                error_reason = "no_formulas"
            elif "zero or unavailable" in detail:
                error_reason = "no_readings"
            else:
                error_reason = "unknown"
        except Exception:
            error_reason = "unknown"

    prev_y, prev_m = _prev_month(year, month)
    next_y, next_m = _next_month(year, month)

    return templates.TemplateResponse(
        request,
        "costs/breakdown.html",
        {
            "user": user,
            "active_tab": "costs",
            "property_id": property_id,
            "property_name": prop.display_name if prop else "Unknown",
            "total_cost": float(cost_decimal),
            "year": year,
            "month": month,
            "month_name": calendar.month_name[month],
            "prev_year": prev_y,
            "prev_month": prev_m,
            "next_year": next_y,
            "next_month": next_m,
            "cost_data": cost_data,
            "error_reason": error_reason,
        },
    )


@router.get("/trends", response_class=HTMLResponse, response_model=None)
async def trends_overview(
    request: Request,
    property_id: int | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse | RedirectResponse:
    """Display consumption trend overview."""
    user = get_current_user_from_session(request, db)
    if not user:
        return RedirectResponse("/login?next=/trends", status_code=303)

    # Resolve property
    if not property_id:
        property_id = user.default_property_id
    if not property_id:
        properties = get_properties_for_user(db, user.id)
        if properties:
            property_id = properties[0].id
        else:
            add_flash_message(request, "Create a property first.", "info")
            return RedirectResponse("/properties/create", status_code=303)

    prop = get_property(db, property_id)

    # Collect last 6 months of consumption data
    now = datetime.now(UTC)
    months_data: list[dict] = []
    all_submeter_data: dict[str, list[dict]] = {}

    y, m = now.year, now.month
    for _ in range(6):
        y, m = _prev_month(y, m)
        start, end = _month_bounds(y, m)
        label = calendar.month_abbr[m]

        try:
            consumption = get_property_consumption(db, property_id, start, end)
            total = float(consumption.main_meter_consumption or 0)
            real_submeters = [s for s in consumption.submeters if not s.is_virtual]
            unmetered = float(consumption.unmetered_consumption or 0)
            months_data.append(
                {
                    "label": label,
                    "total": round(total, 1) if total else 0,
                    "year": y,
                    "month": m,
                    "submeters": real_submeters,
                    "unmetered": round(unmetered, 1),
                }
            )
            for sub in real_submeters:
                if sub.name not in all_submeter_data:
                    all_submeter_data[sub.name] = []
                all_submeter_data[sub.name].append(
                    {
                        "month": f"{y}-{m:02d}",
                        "consumption": float(sub.consumption),
                    }
                )
        except Exception:
            months_data.append(
                {
                    "label": label,
                    "total": 0,
                    "year": y,
                    "month": m,
                    "submeters": [],
                    "unmetered": 0,
                }
            )

    # Reverse so oldest is first (left to right)
    months_data.reverse()

    max_total = max((md["total"] for md in months_data), default=0)

    # Latest month submeter breakdown
    latest_submeters: list[dict] = []
    max_submeter = Decimal("0")
    latest_month_label = ""

    if months_data:
        latest = months_data[-1]
        latest_month_label = latest["label"]
        for i, sub in enumerate(latest["submeters"]):
            color = SUBMETER_COLORS[i % len(SUBMETER_COLORS)]
            latest_submeters.append(
                {
                    "name": sub.name,
                    "consumption": float(sub.consumption),
                    "color": color,
                }
            )
            if sub.consumption > max_submeter:
                max_submeter = sub.consumption

    # Month-over-month changes (compare last two months)
    mom_changes: list[dict] = []
    if len(months_data) >= 2:
        prev_month_data = months_data[-2]
        curr_month_data = months_data[-1]

        prev_subs = {s.name: float(s.consumption) for s in prev_month_data["submeters"]}
        curr_subs = {s.name: float(s.consumption) for s in curr_month_data["submeters"]}

        all_names = list(dict.fromkeys(list(prev_subs.keys()) + list(curr_subs.keys())))
        for name in all_names:
            prev_val = prev_subs.get(name, 0)
            curr_val = curr_subs.get(name, 0)
            pct = round((curr_val - prev_val) / prev_val * 100) if prev_val > 0 else 0
            mom_changes.append(
                {
                    "name": name,
                    "prev": round(prev_val, 1),
                    "curr": round(curr_val, 1),
                    "pct": pct,
                }
            )

    return templates.TemplateResponse(
        request,
        "costs/trends.html",
        {
            "user": user,
            "active_tab": "trends",
            "property_id": property_id,
            "property_name": prop.display_name if prop else "Unknown",
            "months": months_data,
            "max_total": max_total,
            "latest_submeters": latest_submeters,
            "max_submeter": float(max_submeter),
            "latest_month_label": latest_month_label,
            "mom_changes": mom_changes,
        },
    )
