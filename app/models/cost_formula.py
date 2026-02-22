"""CostFormula database model for user-defined cost allocation formulas."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.property import Property


class CostFormula(Base):
    """Cost allocation formula for distributing electricity costs.

    Each formula defines how to compute one share of the total cost.
    The formula is expressed as a weighted sum of meter consumptions:

        cost = total_cost * sum(coefficient_i * consumption_i) / main_meter_consumption

    Terms are stored as JSON mapping meter names to coefficients.
    The special key "_unmetered" references the unmetered (virtual) consumption.

    Example: {"submeter_1": "1.0", "submeter_2": "0.4"} means
        cost = total_cost * (1.0 * submeter_1 + 0.4 * submeter_2) / main_meter
    """

    __tablename__ = "cost_formulas"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    terms_json: Mapped[str] = mapped_column(Text)  # JSON: {"meter_name": "coefficient"}
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    property: Mapped["Property"] = relationship()

    def get_terms(self) -> dict[str, Decimal]:
        """Parse the stored JSON terms into a dict of Decimal coefficients."""
        raw = json.loads(self.terms_json)
        return {k: Decimal(str(v)) for k, v in raw.items()}

    def set_terms(self, terms: dict[str, Decimal]) -> None:
        """Serialize a terms dict to JSON for storage."""
        self.terms_json = json.dumps({k: str(v) for k, v in terms.items()})
