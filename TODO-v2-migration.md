# V2 API Migration — Remaining Work

## Checklist

- [ ] Add web UI for managing cost formulas (CRUD)
- [ ] Add reading type selector (absolute / relative) to reading forms
- [ ] Surface per-meter consumption detail in cost breakdown
- [ ] Differentiate "no formulas" vs "no readings" in cost breakdown empty state
- [ ] Show unmetered consumption in trends view
- [ ] Restore location context in cost breakdown cards

---

## 1. Add web UI for managing cost formulas (CRUD)

V2 cost distribution requires active `CostFormula` records to exist before
costs can be distributed. The API endpoints are implemented
(`app/api/v2/routes/billing.py`), but there are no corresponding web routes
or templates for the mobile UI.

**What is needed:**

- New web routes in `app/web/routes/` for formula CRUD (create, list, edit,
  delete/deactivate).
- New templates in `app/templates/` (e.g. `formulas/list.html`,
  `formulas/create.html`, `formulas/edit.html`).
- Navigation entry so users can reach the formula management pages (e.g. from
  the property detail page or the costs page).

Without this, the cost breakdown page will always show "No cost data available"
because `distribute_costs` raises an error when no active formulas exist.

**Relevant code:**

- Service: `app/services/v2/billing.py` — `create_formula`, `get_formulas_for_property`, `update_formula`, `delete_formula`
- Schema: `app/schemas/v2/billing.py` — `CostFormulaCreate`, `CostFormulaUpdate`, `CostFormulaResponse`
- Model: `app/models/cost_formula.py`

---

## 2. Add reading type selector (absolute / relative) to reading forms

V2 introduces `ReadingType` (ABSOLUTE or RELATIVE). All three reading entry
points in the mobile UI currently default to ABSOLUTE with no way for users to
choose RELATIVE.

**Affected templates:**

- `app/templates/home/index.html` — quick-reading form
- `app/templates/readings/create.html` — single reading form
- `app/templates/readings/bulk_create.html` — bulk reading form

**What is needed:**

- A toggle or select element for `reading_type` in each form.
- Pass the selected value through to the V2 schema (`ReadingCreateV2` /
  `BulkReadingCreateV2`) in the corresponding web route handlers
  (`app/web/routes/home.py`, `app/web/routes/readings.py`).

**Relevant code:**

- Enum: `app/models/enums.py` — `ReadingType`
- Schemas: `app/schemas/v2/readings.py` — `ReadingCreateV2.reading_type`, `BulkReadingCreateV2.reading_type`

---

## 3. Surface per-meter consumption detail in cost breakdown

V2's `CostDistributionResultV2` includes a `meter_consumptions` dict that maps
meter names to their individual consumption values. The breakdown template
currently only shows the formula-level `weighted_consumption`, which is a
computed weighted sum — not raw per-meter consumption.

**What is needed:**

- Render the `meter_consumptions` data somewhere on the cost breakdown page
  (e.g. as a supplementary table or expandable detail section per formula card).
- This restores the per-submeter consumption visibility that V1's
  `SubMeterCostShare.consumption` provided.

**Relevant code:**

- Schema: `app/schemas/v2/billing.py` — `CostDistributionResultV2.meter_consumptions`
- Template: `app/templates/costs/breakdown.html`

---

## 4. Differentiate "no formulas" vs "no readings" in cost breakdown empty state

When `distribute_costs` fails, the template shows a single generic message:
"No cost data available for this month." In V2, failure can stem from two
distinct causes:

1. **No active cost formulas** — the user needs to create formulas first.
2. **No readings for the period** — the user needs to record meter readings at
   period boundaries.

**What is needed:**

- Catch the specific exception from `distribute_costs` in
  `app/web/routes/costs.py` and inspect the error detail.
- Pass a distinct error reason to the template so it can show an actionable
  message (e.g. "No cost formulas configured — create one" with a link, vs
  "No meter readings found for this period").

**Relevant code:**

- Web route: `app/web/routes/costs.py` — `cost_breakdown()`, lines 91-96
- Service: `app/services/v2/billing.py` — `distribute_costs()` raises
  `HTTPException` with detail `"No active cost formulas found for this property"`
  or `"Main meter consumption is zero or unavailable for this period"`

---

## 5. Show unmetered consumption in trends view

V2's `get_property_consumption` returns `_unmetered` as a virtual submeter
(with `is_virtual=True`). The trends web route currently filters these out to
avoid displaying a misleading bar alongside real submeters. However, unmetered
consumption trends are not shown anywhere.

**What is needed:**

- Track unmetered consumption per month alongside the real submeter data.
- Add a dedicated section or annotation in `app/templates/costs/trends.html`
  showing unmetered consumption over time (e.g. a separate bar, a line overlay,
  or a summary row in the month-over-month table).

**Relevant code:**

- Web route: `app/web/routes/costs.py` — `trends_overview()`, virtual submeter
  filtering at line ~160
- Schema: `app/schemas/v2/readings.py` — `SubMeterConsumptionV2.is_virtual`
- Template: `app/templates/costs/trends.html`

---

## 6. Restore location context in cost breakdown cards

V1's `SubMeterCostShare` included a `location` field displayed as a subtitle on
each cost card. V2's `FormulaShareResult` does not carry location — formulas
are named allocation rules that reference meters by name, not individual
submeters with physical locations.

**What is needed:**

- Either embed location info into formula names by convention, or
- Look up meter locations from `meter_consumptions` keys and pass them to the
  template, or
- Add a `description` or `location` field to the `CostFormula` model/schema.

**Relevant code:**

- Schema: `app/schemas/v2/billing.py` — `FormulaShareResult` (no location field)
- Template: `app/templates/costs/breakdown.html` — previously rendered `sub.location`
- Model: `app/models/cost_formula.py`
