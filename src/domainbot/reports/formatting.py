from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

DEFAULT_DISPLAY_TIMEZONE = "Europe/Istanbul"


def format_datetime_tr(value: datetime | None, timezone: str = DEFAULT_DISPLAY_TIMEZONE) -> str:
    if value is None:
        return "-"
    local_value = value.astimezone(ZoneInfo(timezone))
    return local_value.strftime("%d.%m.%Y %H:%M:%S")


def format_date_tr(value: datetime | None, timezone: str = DEFAULT_DISPLAY_TIMEZONE) -> str:
    if value is None:
        return "-"
    local_value = value.astimezone(ZoneInfo(timezone))
    return local_value.strftime("%d.%m.%Y")
