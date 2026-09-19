"""Services for the Household Chores integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_COMPLETION_LOG,
    ATTR_LAST_DONE,
    ATTR_LAST_DONE_BY,
    ATTR_NEXT_DUE,
    CONF_FREQUENCY_TYPE,
    CONF_FREQUENCY_UNIT,
    CONF_FREQUENCY_VALUE,
    CONF_NAME,
    CONF_SCHEDULE,
    DOMAIN,
    FIELD_CHORE_ID,
    FIELD_ENTITY_ID,
    FIELD_NOTES,
    FIELD_PERSON,
    SERVICE_MARK_DONE,
    SERVICE_RESET,
)
from .helpers import calculate_next_due
from .storage import ChoreStorage

_LOGGER = logging.getLogger(__name__)

MARK_DONE_SCHEMA = vol.Schema(
    {
        vol.Exclusive(FIELD_ENTITY_ID, "chore_identifier"): cv.entity_id,
        vol.Exclusive(FIELD_CHORE_ID, "chore_identifier"): str,
        vol.Optional(FIELD_PERSON): cv.entity_id,
        vol.Optional(FIELD_NOTES): str,
    }
)

RESET_SCHEMA = vol.Schema(
    {
        vol.Exclusive(FIELD_ENTITY_ID, "chore_identifier"): cv.entity_id,
        vol.Exclusive(FIELD_CHORE_ID, "chore_identifier"): str,
    }
)


def _find_chore_entry(
    hass: HomeAssistant, entity_id: str | None, chore_id: str | None
) -> tuple[str, dict[str, Any]]:
    """Find a chore config entry by entity_id or chore_id.

    Returns (chore_id, config_dict).
    """
    if entity_id is None and chore_id is None:
        raise HomeAssistantError(
            "Must provide either entity_id or chore_id"
        )

    entries = hass.config_entries.async_entries(DOMAIN)

    if chore_id is not None:
        for entry in entries:
            if entry.entry_id == chore_id:
                return entry.entry_id, dict(entry.data)
        raise HomeAssistantError(f"Chore not found with chore_id: {chore_id}")

    # entity_id provided — match against derived entity_id pattern.
    # Entity IDs are sensor.chores_<slug>.
    from .helpers import slugify_name

    target_slug = entity_id.replace("sensor.chores_", "")
    for entry in entries:
        name = entry.data.get(CONF_NAME, "")
        if slugify_name(name) == target_slug:
            return entry.entry_id, dict(entry.data)

    raise HomeAssistantError(f"Chore not found with entity_id: {entity_id}")


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register services for the Chores integration."""
    storage: ChoreStorage = hass.data[DOMAIN]["storage"]

    async def handle_mark_done(call: ServiceCall) -> ServiceResponse:
        """Mark a chore as done."""
        entity_id = call.data.get(FIELD_ENTITY_ID)
        chore_id = call.data.get(FIELD_CHORE_ID)
        person = call.data.get(FIELD_PERSON)
        notes = call.data.get(FIELD_NOTES, "")

        found_chore_id, config = _find_chore_entry(hass, entity_id, chore_id)

        now = dt_util.now()

        # Get current state.
        state = storage.get_chore_state(found_chore_id)
        log = state.get(ATTR_COMPLETION_LOG, [])

        log_entry: dict[str, Any] = {
            "timestamp": now.isoformat(),
            "person": person,
            "notes": notes,
        }
        log.append(log_entry)

        # Calculate next due.
        freq_type = config.get(CONF_FREQUENCY_TYPE)
        freq_value = config.get(CONF_FREQUENCY_VALUE)
        freq_unit = config.get(CONF_FREQUENCY_UNIT)
        schedule = config.get(CONF_SCHEDULE)

        next_due = calculate_next_due(
            freq_type, now, freq_value, freq_unit, schedule
        )

        await storage.async_update_chore_state(
            found_chore_id,
            {
                ATTR_LAST_DONE: now.isoformat(),
                ATTR_LAST_DONE_BY: person,
                ATTR_NEXT_DUE: next_due.isoformat(),
                ATTR_COMPLETION_LOG: log,
            },
        )

        # Trigger entity update.
        await _async_trigger_entity_update(hass, entity_id, chore_id, config)

        _LOGGER.info(
            "Chore '%s' marked as done by %s", config.get(CONF_NAME), person
        )
        return None

    async def handle_reset(call: ServiceCall) -> ServiceResponse:
        """Reset a chore's completion state."""
        entity_id = call.data.get(FIELD_ENTITY_ID)
        chore_id = call.data.get(FIELD_CHORE_ID)

        found_chore_id, config = _find_chore_entry(hass, entity_id, chore_id)

        freq_type = config.get(CONF_FREQUENCY_TYPE)
        freq_value = config.get(CONF_FREQUENCY_VALUE)
        freq_unit = config.get(CONF_FREQUENCY_UNIT)
        schedule = config.get(CONF_SCHEDULE)

        # Recompute from now so the chore gets a fresh, stable due date
        # (due today if today is a scheduled day) instead of a floating one.
        next_due = calculate_next_due(
            freq_type, None, freq_value, freq_unit, schedule
        )

        await storage.async_update_chore_state(
            found_chore_id,
            {
                ATTR_LAST_DONE: None,
                ATTR_LAST_DONE_BY: None,
                ATTR_NEXT_DUE: next_due.isoformat(),
                ATTR_COMPLETION_LOG: [],
            },
        )

        await _async_trigger_entity_update(hass, entity_id, chore_id, config)

        _LOGGER.info("Chore '%s' has been reset", config.get(CONF_NAME))
        return None

    hass.services.async_register(
        DOMAIN, SERVICE_MARK_DONE, handle_mark_done, schema=MARK_DONE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RESET, handle_reset, schema=RESET_SCHEMA
    )


async def _async_trigger_entity_update(
    hass: HomeAssistant,
    entity_id: str | None,
    chore_id: str | None,
    config: dict[str, Any],
) -> None:
    """Force an immediate state refresh on the chore entity."""
    from .helpers import slugify_name

    slug = slugify_name(config.get(CONF_NAME, ""))
    target_entity_id = f"sensor.chores_{slug}"

    # Look up the entity instance and call async_write_ha_state so it
    # re-evaluates native_value and extra_state_attributes from the
    # updated storage data and writes the fresh state immediately.
    entities = hass.data.get(DOMAIN, {}).get("entities", {})
    entity = entities.get(target_entity_id)
    if entity is not None:
        entity.async_write_ha_state()
