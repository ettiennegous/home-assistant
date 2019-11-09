"""Enums used for United Energy API call context."""

from enum import Enum


class PeriodOffset(Enum):
    """Offset period valid options for reporting."""

    current = 0
    prior = 1
    timebeforelast = 2


class ReportPeriod(Enum):
    """Timespan options for reporting."""

    day = "day"
    week = "week"
    month = "month"
    year = "year"
