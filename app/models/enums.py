"""Enum definitions for meter types."""

from enum import Enum


class MeterType(str, Enum):
    """Main meter vs submeter classification."""

    MAIN_METER = "main_meter"
    SUB_METER = "sub_meter"


class SubMeterKind(str, Enum):
    """Classification of submeters. Currently only physical submeters are supported."""

    PHYSICAL = "physical"
