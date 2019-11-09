"""Enums used for United Energy API call context."""

from enum import Enum

class PeriodOffset(Enum):
    current = 0
    prior = 1
    timebeforelast = 2

class ReportPeriod(Enum):
    live = "live"
    day = "day"
    week = "week"
    month = "month"
    year = "year"
