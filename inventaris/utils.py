from __future__ import annotations

from datetime import date, timedelta
import calendar

from .models import MaintenanceSchedule


def add_period(base_date: date, period: str) -> date:
    if period == MaintenanceSchedule.PERIOD_HARIAN:
        return base_date + timedelta(days=1)
    if period == MaintenanceSchedule.PERIOD_MINGGUAN:
        return base_date + timedelta(days=7)
    if period == MaintenanceSchedule.PERIOD_BULANAN:
        year = base_date.year
        month = base_date.month + 1
        if month > 12:
            month = 1
            year += 1
        day = min(base_date.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    if period == MaintenanceSchedule.PERIOD_TAHUNAN:
        year = base_date.year + 1
        day = min(base_date.day, calendar.monthrange(year, base_date.month)[1])
        return date(year, base_date.month, day)
    return base_date


def schedule_status(next_due_date: date | None, today: date | None = None) -> str:
    if next_due_date is None:
        return MaintenanceSchedule.STATUS_TEPAT
    today = today or date.today()
    if today > next_due_date:
        return MaintenanceSchedule.STATUS_TERLAMBAT
    return MaintenanceSchedule.STATUS_TEPAT
