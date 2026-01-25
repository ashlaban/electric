"""Meter database model."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import MeterType, SubMeterKind

if TYPE_CHECKING:
    from app.models.meter_reading import MeterReading
    from app.models.property import Property


class Meter(Base):
    """Meter entity - physical or virtual device for measuring usage."""

    __tablename__ = "meters"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    meter_type: Mapped[MeterType] = mapped_column(String(20), index=True)
    sub_meter_kind: Mapped[SubMeterKind | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Foreign keys
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    parent_property: Mapped["Property"] = relationship(back_populates="meters")
    readings: Mapped[list["MeterReading"]] = relationship(back_populates="meter")

    def get_is_virtual(self) -> bool:
        """Check if this is a virtual (computed) meter."""
        return self.sub_meter_kind == SubMeterKind.VIRTUAL

    def get_is_main_meter(self) -> bool:
        """Check if this is the main meter."""
        return self.meter_type == MeterType.MAIN_METER
