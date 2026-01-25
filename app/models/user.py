"""User database model."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.meter import Meter
    from app.models.property import Property


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    is_active: Mapped[bool] = mapped_column(default=True)

    # Meter ledger extensions
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    default_property_id: Mapped[int | None] = mapped_column(
        ForeignKey("properties.id"),
        nullable=True,
    )
    default_meter_id: Mapped[int | None] = mapped_column(
        ForeignKey("meters.id"),
        nullable=True,
    )

    # Relationships
    default_property: Mapped["Property | None"] = relationship(
        foreign_keys=[default_property_id],
    )
    default_meter: Mapped["Meter | None"] = relationship(
        foreign_keys=[default_meter_id],
    )
    properties: Mapped[list["Property"]] = relationship(
        secondary="user_property_association",
        back_populates="users",
    )
