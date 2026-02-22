"""Enum definitions for meter types."""

from enum import Enum


class MeterType(str, Enum):
    """Main meter vs submeter classification."""

    MAIN_METER = "main_meter"
    SUB_METER = "sub_meter"


class SubMeterKind(str, Enum):
    """Classification of submeters."""

    PHYSICAL = "physical"
    VIRTUAL = "virtual"


class ReadingType(str, Enum):
    """Type of meter reading value."""

    ABSOLUTE = "absolute"  # Cumulative kWh since installation
    RELATIVE = "relative"  # kWh consumed during a period
