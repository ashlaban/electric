"""Association tables for many-to-many relationships."""

from sqlalchemy import Column, ForeignKey, Table

from app.core.database import Base

# Many-to-many: User <-> Property
user_property_association = Table(
    "user_property_association",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("property_id", ForeignKey("properties.id"), primary_key=True),
)
