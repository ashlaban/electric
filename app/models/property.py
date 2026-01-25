"""Property database model."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.meter import Meter
    from app.models.user import User


class Property(Base):
    """Property entity that meters are connected to."""

    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100), index=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    meters: Mapped[list["Meter"]] = relationship(back_populates="parent_property")
    users: Mapped[list["User"]] = relationship(
        secondary="user_property_association",
        back_populates="properties",
    )
