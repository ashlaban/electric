"""MeterReading database model - the central ledger."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.meter import Meter
    from app.models.user import User


class MeterReading(Base):
    """Meter reading ledger entry."""

    __tablename__ = "meter_readings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        index=True,
    )  # When added to database
    reading_timestamp: Mapped[datetime] = mapped_column(index=True)  # When reading was taken

    # The actual reading value (using Decimal for precision)
    value: Mapped[Decimal] = mapped_column(Numeric(precision=12, scale=3))

    # Foreign keys
    meter_id: Mapped[int] = mapped_column(ForeignKey("meters.id"), index=True)
    recorded_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )  # Optional: who recorded this reading

    # Relationships
    meter: Mapped["Meter"] = relationship(back_populates="readings")
    recorded_by: Mapped["User | None"] = relationship()
