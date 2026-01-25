"""Enum definitions for meter types."""

from enum import Enum


class MeterType(str, Enum):
    """Main meter vs submeter classification."""

    MAIN_METER = "main_meter"
    SUB_METER = "sub_meter"


class SubMeterKind(str, Enum):
    """Physical vs virtual classification (submeters only)."""

    PHYSICAL = "physical"
    VIRTUAL = "virtual"
