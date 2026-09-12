"""Base entity class for chore sensors."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant

from .const import (
    ATTR_ASSIGNEES,
    ATTR_COMPLETION_LOG,
    ATTR_DAYS_UNTIL_DUE,
    ATTR_FREQUENCY,
    ATTR_FREQUENCY_DAYS,
    ATTR_LAST_DONE,
    ATTR_LAST_DONE_BY,
    ATTR_NEXT_DUE,
    CONF_ASSIGNEES,
    CONF_FREQUENCY_TYPE,
    CONF_FREQUENCY_UNIT,
    CONF_FREQUENCY_VALUE,
    CONF_ICON,
    CONF_NAME,
    CONF_SCHEDULE,
    DOMAIN,
)
from .helpers import (
    calculate_days_until_due,
    calculate_next_due,
    calculate_status,
    format_frequency,
)
from .storage import ChoreStorage

_LOGGER = logging.getLogger(__name__)


class ChoreEntity(SensorEntity):
    """Representation of a single chore."""

    _attr_should_poll = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        chore_id: str,
        config: dict[str, Any],
        storage: ChoreStorage,
    ) -> None:
        """Initialize the chore entity."""
        self._hass = hass
        self._config_entry_id = config_entry_id
        self._chore_id = chore_id
        self._config = config
        self._storage = storage

        self._attr_unique_id = f"{chore_id}"
        self._attr_name = config[CONF_NAME]
        self._attr_icon = config.get(CONF_ICON, "mdi:clipboard-check")

        # Set entity_id with chores_ prefix so all chore sensors are grouped.
        from .helpers import slugify_name

        slug = slugify_name(config[CONF_NAME])
        self.entity_id = f"sensor.chores_{slug}"

    @property
    def chore_id(self) -> str:
        """Return the unique chore identifier."""
        return self._chore_id

    @property
    def config(self) -> dict[str, Any]:
        """Return the chore configuration."""
        return self._config

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        state = self._storage.get_chore_state(self._chore_id)
        next_due = self._get_next_due(state)
        return calculate_status(next_due)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        state = self._storage.get_chore_state(self._chore_id)
        next_due = self._get_next_due(state)

        freq_type = self._config.get(CONF_FREQUENCY_TYPE)
        freq_value = self._config.get(CONF_FREQUENCY_VALUE)
        freq_unit = self._config.get(CONF_FREQUENCY_UNIT)
        schedule = self._config.get(CONF_SCHEDULE)

        last_done = state.get(ATTR_LAST_DONE)
        last_done_by = state.get(ATTR_LAST_DONE_BY)

        return {
            ATTR_ASSIGNEES: self._config.get(CONF_ASSIGNEES, []),
            ATTR_FREQUENCY: format_frequency(
                freq_type, freq_value, freq_unit, schedule
            ),
            ATTR_FREQUENCY_DAYS: self._get_frequency_days(
                freq_type, freq_value, freq_unit
            ),
            ATTR_LAST_DONE: last_done,
            ATTR_LAST_DONE_BY: last_done_by,
            ATTR_NEXT_DUE: next_due.date().isoformat() if next_due else None,
            ATTR_DAYS_UNTIL_DUE: calculate_days_until_due(next_due),
            ATTR_COMPLETION_LOG: state.get(ATTR_COMPLETION_LOG, []),
        }

    def _get_next_due(self, state: dict[str, Any]) -> datetime | None:
        """Get the next due datetime, computing it if not stored."""
        next_due_str = state.get(ATTR_NEXT_DUE)
        if next_due_str:
            try:
                return datetime.fromisoformat(next_due_str)
            except (ValueError, TypeError):
                pass

        # Compute next_due if not stored yet.
        last_done_str = state.get(ATTR_LAST_DONE)
        last_done = None
        if last_done_str:
            try:
                last_done = datetime.fromisoformat(last_done_str)
            except (ValueError, TypeError):
                pass

        freq_type = self._config.get(CONF_FREQUENCY_TYPE)
        freq_value = self._config.get(CONF_FREQUENCY_VALUE)
        freq_unit = self._config.get(CONF_FREQUENCY_UNIT)
        schedule = self._config.get(CONF_SCHEDULE)

        try:
            next_due = calculate_next_due(
                freq_type, last_done, freq_value, freq_unit, schedule
            )
        except ValueError:
            _LOGGER.error(
                "Failed to calculate next_due for chore %s", self._chore_id
            )
            return None

        return next_due

    @staticmethod
    def _get_frequency_days(
        freq_type: str | None,
        freq_value: int | None,
        freq_unit: str | None,
    ) -> int | None:
        """Return the frequency interval in days, or None for schedule-based."""
        from .const import FREQUENCY_TYPE_INTERVAL, FREQUENCY_UNIT_TO_DAYS

        if freq_type != FREQUENCY_TYPE_INTERVAL:
            return None
        if freq_unit not in FREQUENCY_UNIT_TO_DAYS:
            return None
        return FREQUENCY_UNIT_TO_DAYS[freq_unit](freq_value)

    async def async_update(self) -> None:
        """Update the entity state.

        The state is computed from storage data, so polling mainly ensures
        the status transitions from pending to due at the right time.
        """
        # Nothing to fetch — state is computed from stored data.
        # This method exists so HA re-evaluates the state periodically.
