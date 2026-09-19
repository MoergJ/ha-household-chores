"""Unit tests for the chore scheduling and status logic."""

import sys
import os
import importlib.util
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Mock the homeassistant.util.dt module before importing helpers.
# This lets us test the pure-logic functions without a full HA install.

mock_utcnow = datetime(2026, 9, 12, 10, 0, 0, tzinfo=ZoneInfo("UTC"))

# Create a mock for homeassistant.util.dt
ha_dt_mod = type(sys)("homeassistant.util.dt")
ha_dt_mod.now = lambda: mock_utcnow
sys.modules["homeassistant"] = type(sys)("homeassistant")
sys.modules["homeassistant.util"] = type(sys)("homeassistant.util")
sys.modules["homeassistant.util.dt"] = ha_dt_mod

# Set up the custom_components.chores package with a minimal __init__
# so relative imports in helpers.py work, without triggering the real
# __init__.py (which requires homeassistant).
pkg_cc = type(sys)("custom_components")
pkg_cc.__path__ = []
sys.modules["custom_components"] = pkg_cc

pkg_chores = type(sys)("custom_components.chores")
pkg_chores.__path__ = []
sys.modules["custom_components.chores"] = pkg_chores

_base = os.path.join(os.path.dirname(__file__), "..", "custom_components", "chores")


def _load_module(full_name, path):
    spec = importlib.util.spec_from_file_location(full_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod


_load_module("custom_components.chores.const", os.path.join(_base, "const.py"))
_load_module("custom_components.chores.helpers", os.path.join(_base, "helpers.py"))

from custom_components.chores.helpers import (  # noqa: E402
    calculate_next_due,
    calculate_status,
    calculate_days_until_due,
    format_frequency,
    slugify_name,
)
from custom_components.chores.const import (  # noqa: E402
    FREQUENCY_TYPE_INTERVAL,
    FREQUENCY_TYPE_SCHEDULE,
    FREQUENCY_UNIT_DAYS,
    FREQUENCY_UNIT_WEEKS,
    FREQUENCY_UNIT_MONTHS,
    STATUS_DUE,
    STATUS_PENDING,
)


def test_calculate_next_due_interval_days_never_done():
    """A chore never done with interval should be due today (date only)."""
    result = calculate_next_due(
        FREQUENCY_TYPE_INTERVAL, None,
        frequency_value=7, frequency_unit=FREQUENCY_UNIT_DAYS,
    )
    assert result.date() == mock_utcnow.date()
    assert result.hour == 0 and result.minute == 0


def test_calculate_next_due_interval_days():
    """7-day interval from last_done should be last_done date + 7 days, at midnight."""
    last_done = datetime(2026, 9, 5, 14, 30, 0, tzinfo=ZoneInfo("UTC"))
    result = calculate_next_due(
        FREQUENCY_TYPE_INTERVAL, last_done,
        frequency_value=7, frequency_unit=FREQUENCY_UNIT_DAYS,
    )
    expected = (last_done + timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    assert result == expected
    assert result.hour == 0 and result.minute == 0


def test_calculate_next_due_interval_weeks():
    """2-week interval should be last_done date + 14 days, at midnight."""
    last_done = datetime(2026, 9, 1, 8, 0, 0, tzinfo=ZoneInfo("UTC"))
    result = calculate_next_due(
        FREQUENCY_TYPE_INTERVAL, last_done,
        frequency_value=2, frequency_unit=FREQUENCY_UNIT_WEEKS,
    )
    expected = (last_done + timedelta(days=14)).replace(hour=0, minute=0, second=0, microsecond=0)
    assert result == expected
    assert result.hour == 0 and result.minute == 0


def test_calculate_next_due_interval_months():
    """1-month interval should be last_done date + 30 days, at midnight."""
    last_done = datetime(2026, 9, 1, 0, 0, 0, tzinfo=ZoneInfo("UTC"))
    result = calculate_next_due(
        FREQUENCY_TYPE_INTERVAL, last_done,
        frequency_value=1, frequency_unit=FREQUENCY_UNIT_MONTHS,
    )
    expected = (last_done + timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
    assert result == expected


def test_calculate_next_due_schedule_never_done():
    """Schedule-based chore never done: next occurrence of a scheduled day."""
    # mock_utcnow is 2026-09-12 (Saturday).
    # Next Monday is 2026-09-14.
    result = calculate_next_due(
        FREQUENCY_TYPE_SCHEDULE, None,
        schedule=["monday", "thursday"],
    )
    assert result.weekday() == 0  # Monday
    assert result.hour == 0 and result.minute == 0


def test_calculate_next_due_schedule_never_done_today():
    """Never-done chore should be due today when today is a scheduled day."""
    # mock_utcnow is 2026-09-12 (Saturday).
    result = calculate_next_due(
        FREQUENCY_TYPE_SCHEDULE, None,
        schedule=["saturday"],
    )
    assert result.date() == mock_utcnow.date()
    assert result.hour == 0 and result.minute == 0


def test_calculate_next_due_schedule_same_day_as_last_done():
    """Chore completed on a scheduled day rolls to the next occurrence."""
    # last_done is 2026-09-12 (Saturday), schedule is Saturday only.
    # Next due should be 2026-09-19, not the same day.
    last_done = datetime(2026, 9, 12, 14, 0, 0, tzinfo=ZoneInfo("UTC"))
    result = calculate_next_due(
        FREQUENCY_TYPE_SCHEDULE, last_done,
        schedule=["saturday"],
    )
    assert result.date() == datetime(2026, 9, 19).date()
    assert result.hour == 0 and result.minute == 0


def test_calculate_next_due_schedule_after_last_done():
    """Schedule-based chore: next scheduled day after last_done."""
    # last_done is 2026-09-07 (Monday), schedule is Monday+Thursday.
    # Next should be 2026-09-10 (Thursday).
    last_done = datetime(2026, 9, 7, 15, 0, 0, tzinfo=ZoneInfo("UTC"))
    result = calculate_next_due(
        FREQUENCY_TYPE_SCHEDULE, last_done,
        schedule=["monday", "thursday"],
    )
    assert result.weekday() == 3  # Thursday
    assert result.hour == 0 and result.minute == 0


def test_calculate_status_due():
    """Chore with next_due in the past should be due."""
    past = mock_utcnow - timedelta(days=1)
    result = calculate_status(past)
    assert result == STATUS_DUE


def test_calculate_status_pending():
    """Chore with next_due in the future should be pending."""
    future = mock_utcnow + timedelta(days=3)
    result = calculate_status(future)
    assert result == STATUS_PENDING


def test_calculate_status_due_none():
    """Chore with no next_due should be due."""
    result = calculate_status(None)
    assert result == STATUS_DUE


def test_calculate_days_until_due_future():
    """Days until due should be positive for future dates."""
    future = mock_utcnow + timedelta(days=5)
    result = calculate_days_until_due(future)
    assert result == 5


def test_calculate_days_until_due_past():
    """Days until due should be negative for overdue dates."""
    past = mock_utcnow - timedelta(days=2)
    result = calculate_days_until_due(past)
    assert result == -2


def test_calculate_days_until_due_none():
    """None next_due should return None."""
    result = calculate_days_until_due(None)
    assert result is None


def test_format_frequency_interval():
    """Interval frequency formatting."""
    result = format_frequency(
        FREQUENCY_TYPE_INTERVAL, 7, FREQUENCY_UNIT_DAYS
    )
    assert result == "Every 7 days"


def test_format_frequency_interval_singular():
    """Singular unit should drop the 's'."""
    result = format_frequency(
        FREQUENCY_TYPE_INTERVAL, 1, FREQUENCY_UNIT_DAYS
    )
    assert result == "Every 1 day"


def test_format_frequency_interval_weeks():
    """Weeks formatting."""
    result = format_frequency(
        FREQUENCY_TYPE_INTERVAL, 2, FREQUENCY_UNIT_WEEKS
    )
    assert result == "Every 2 weeks"


def test_format_frequency_schedule_single():
    """Single day schedule formatting."""
    result = format_frequency(
        FREQUENCY_TYPE_SCHEDULE, schedule=["monday"]
    )
    assert result == "Every Monday"


def test_format_frequency_schedule_multiple():
    """Multiple day schedule formatting."""
    result = format_frequency(
        FREQUENCY_TYPE_SCHEDULE, schedule=["monday", "thursday", "saturday"]
    )
    assert result == "Every Monday, Thursday, Saturday"


def test_slugify_name():
    """Slugify should produce valid entity ID slugs."""
    assert slugify_name("Take out trash") == "take_out_trash"
    assert slugify_name("Clean the kitchen!") == "clean_the_kitchen"
    assert slugify_name("Vacuum  2x/week") == "vacuum_2x_week"
    assert slugify_name("  Laundry  ") == "laundry"


def test_slugify_name_umlauts():
    """Umlauts should be transliterated correctly."""
    assert slugify_name("Müll rausbringen") == "muell_rausbringen"
    assert slugify_name("Grün fegen") == "gruen_fegen"
    assert slugify_name("Öl wechseln") == "oel_wechseln"
    assert slugify_name("Fußboden wischen") == "fussboden_wischen"
    assert slugify_name("Wäsche waschen") == "waesche_waschen"


if __name__ == "__main__":
    test_calculate_next_due_interval_days_never_done()
    test_calculate_next_due_interval_days()
    test_calculate_next_due_interval_weeks()
    test_calculate_next_due_interval_months()
    test_calculate_next_due_schedule_never_done()
    test_calculate_next_due_schedule_never_done_today()
    test_calculate_next_due_schedule_same_day_as_last_done()
    test_calculate_next_due_schedule_after_last_done()
    test_calculate_status_due()
    test_calculate_status_pending()
    test_calculate_status_due_none()
    test_calculate_days_until_due_future()
    test_calculate_days_until_due_past()
    test_calculate_days_until_due_none()
    test_format_frequency_interval()
    test_format_frequency_interval_singular()
    test_format_frequency_interval_weeks()
    test_format_frequency_schedule_single()
    test_format_frequency_schedule_multiple()
    test_slugify_name()
    test_slugify_name_umlauts()
    print("All tests passed!")
