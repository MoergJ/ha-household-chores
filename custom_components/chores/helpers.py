"""Utility functions for scheduling and status calculation."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.util import dt as dt_util

from .const import (
    FREQUENCY_TYPE_INTERVAL,
    FREQUENCY_TYPE_SCHEDULE,
    FREQUENCY_UNIT_TO_DAYS,
    STATUS_DEACTIVATED,
    STATUS_DUE,
    STATUS_PENDING,
)

# Mapping from day name to Python weekday integer (Monday=0 .. Sunday=6).
_DAY_NAME_TO_WEEKDAY = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def calculate_next_due(
    frequency_type: str,
    last_done: datetime | None,
    frequency_value: int | None = None,
    frequency_unit: str | None = None,
    schedule: list[str] | None = None,
) -> datetime:
    """Calculate the next due datetime for a chore.

    Args:
        frequency_type: "interval" or "schedule".
        last_done: When the chore was last completed, or None if never.
        frequency_value: Number of units (for interval type).
        frequency_unit: "days", "weeks", or "months" (for interval type).
        schedule: List of day names (for schedule type).

    Returns:
        The next due datetime in local timezone.
    """
    now = dt_util.now()

    if frequency_type == FREQUENCY_TYPE_INTERVAL:
        if frequency_unit not in FREQUENCY_UNIT_TO_DAYS:
            raise ValueError(f"Unknown frequency unit: {frequency_unit}")

        days = FREQUENCY_UNIT_TO_DAYS[frequency_unit](frequency_value)
        delta = timedelta(days=days)

        if last_done is None:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)

        next_due = last_done + delta
        return next_due.replace(hour=0, minute=0, second=0, microsecond=0)

    if frequency_type == FREQUENCY_TYPE_SCHEDULE:
        if not schedule:
            raise ValueError("Schedule frequency requires at least one day")

        weekday_numbers = sorted(
            _DAY_NAME_TO_WEEKDAY[day] for day in schedule if day in _DAY_NAME_TO_WEEKDAY
        )
        if not weekday_numbers:
            raise ValueError(f"Invalid schedule days: {schedule}")

        reference = last_done if last_done is not None else now

        # Find the next occurrence of any scheduled day after the reference date.
        for offset in range(1, 8):
            candidate = reference + timedelta(days=offset)
            if candidate.weekday() in weekday_numbers:
                # Normalize to midnight local time.
                return candidate.replace(hour=0, minute=0, second=0, microsecond=0)

        # Should never reach here since we check all 7 days.
        return now

    raise ValueError(f"Unknown frequency type: {frequency_type}")


def calculate_status(next_due: datetime | None) -> str:
    """Calculate the current status of a chore.

    Args:
        next_due: The next due datetime, or None if never computed.

    Returns:
        One of STATUS_DUE or STATUS_PENDING.
    """
    if next_due is None:
        return STATUS_DUE

    now = dt_util.now()
    if now >= next_due:
        return STATUS_DUE

    return STATUS_PENDING


def calculate_days_until_due(next_due: datetime | None) -> int | None:
    """Calculate the number of days until (or since) the due date.

    Returns 0 if due today, positive if pending, negative if overdue, None if never.
    """
    if next_due is None:
        return None

    now = dt_util.now()
    delta = next_due.date() - now.date()
    return delta.days


def format_frequency(
    frequency_type: str,
    frequency_value: int | None = None,
    frequency_unit: str | None = None,
    schedule: list[str] | None = None,
) -> str:
    """Produce a human-readable description of the frequency."""
    if frequency_type == FREQUENCY_TYPE_INTERVAL:
        unit_label = frequency_unit if frequency_unit else "days"
        if frequency_value == 1:
            unit_label = unit_label.rstrip("s")
        return f"Every {frequency_value} {unit_label}"

    if frequency_type == FREQUENCY_TYPE_SCHEDULE:
        if not schedule:
            return "Schedule not set"
        capitalized = [day.capitalize() for day in schedule]
        if len(capitalized) == 1:
            return f"Every {capitalized[0]}"
        return f"Every {', '.join(capitalized)}"

    return "Unknown frequency"


def slugify_name(name: str) -> str:
    """Convert a chore name into a slug suitable for entity IDs.

    Transliterates common umlauts and special characters before slugifying.
    """
    import re
    import unicodedata

    # Transliterate German umlauts and common special chars.
    umlaut_map = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "ae",
        "Ö": "oe",
        "Ü": "ue",
        "ß": "ss",
    }
    for char, replacement in umlaut_map.items():
        name = name.replace(char, replacement)

    # Normalize remaining unicode characters (e.g. accents).
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")

    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug
