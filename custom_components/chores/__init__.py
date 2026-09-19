"""The Household Chores integration."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    ATTR_LAST_DONE,
    ATTR_NEXT_DUE,
    CONF_FREQUENCY_TYPE,
    CONF_FREQUENCY_UNIT,
    CONF_FREQUENCY_VALUE,
    CONF_SCHEDULE,
    DOMAIN,
    PLATFORMS,
)
from .frontend import async_register_frontend
from .helpers import calculate_next_due
from .services import async_setup_services
from .storage import ChoreStorage

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Chores integration via YAML (not supported, use UI)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a chore from a config entry."""
    # Initialize shared storage if this is the first entry.
    if DOMAIN not in hass.data:
        storage = ChoreStorage(hass)
        await storage.async_load()
        hass.data[DOMAIN] = {"storage": storage}
        async_setup_services(hass)
        await async_register_frontend(hass)
        _LOGGER.info("Chores integration initialized")
    else:
        storage = hass.data[DOMAIN]["storage"]
        await storage.async_load()

    await _async_ensure_next_due(storage, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload entities when options are updated.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO datetime string, returning None for missing values."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


async def _async_ensure_next_due(
    storage: ChoreStorage, entry: ConfigEntry
) -> None:
    """Persist a stable next_due date for a chore that has none stored.

    Without a stored value the due date is recomputed from now on every
    state read, drifting past scheduled days before the first completion.
    """
    state = storage.get_chore_state(entry.entry_id)
    if state.get(ATTR_NEXT_DUE):
        return

    last_done = _parse_datetime(state.get(ATTR_LAST_DONE))

    try:
        next_due = calculate_next_due(
            entry.data.get(CONF_FREQUENCY_TYPE),
            last_done,
            entry.data.get(CONF_FREQUENCY_VALUE),
            entry.data.get(CONF_FREQUENCY_UNIT),
            entry.data.get(CONF_SCHEDULE),
        )
    except ValueError:
        _LOGGER.error(
            "Failed to calculate next_due for chore %s", entry.entry_id
        )
        return

    await storage.async_update_chore_state(
        entry.entry_id, {ATTR_NEXT_DUE: next_due.isoformat()}
    )


async def _async_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options update by reloading the config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Clean up storage and entity reference for this chore.
    if DOMAIN in hass.data:
        storage: ChoreStorage = hass.data[DOMAIN]["storage"]
        await storage.async_remove_chore(entry.entry_id)

        entities = hass.data[DOMAIN].get("entities", {})
        slug = None
        name = entry.data.get("name", "")
        from .helpers import slugify_name

        slug = slugify_name(name)
        target_entity_id = f"sensor.chores_{slug}"
        entities.pop(target_entity_id, None)

    # If no more entries, remove services and data.
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        services_to_remove = ["mark_done", "reset"]
        for service in services_to_remove:
            if hass.services.has_service(DOMAIN, service):
                hass.services.async_remove(DOMAIN, service)
        hass.data.pop(DOMAIN, None)

    return unload_ok
