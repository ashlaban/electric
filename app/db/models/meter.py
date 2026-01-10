"""Meter database model."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MeterType(str, enum.Enum):
    """Meter type enumeration."""

    PHYSICAL_MAIN = "physical_main"
    PHYSICAL_SUBMETER = "physical_submeter"
    VIRTUAL = "virtual"


class Meter(Base):
    """Electric meter - physical or virtual."""

    __tablename__ = "meters"
    __table_args__ = (
        UniqueConstraint("property_id", "meter_code", name="uq_property_meter_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, index=True
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    meter_code: Mapped[str] = mapped_column(String(50), nullable=False)
    meter_type: Mapped[MeterType] = mapped_column(
        Enum(MeterType), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="kWh")
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    property: Mapped["Property"] = relationship("Property", back_populates="meters")
    readings: Mapped[list["MeterReading"]] = relationship(
        "MeterReading", back_populates="meter", cascade="all, delete-orphan"
    )
    users_with_default: Mapped[list["User"]] = relationship(
        "User", back_populates="default_meter", foreign_keys="User.default_meter_id"
    )
