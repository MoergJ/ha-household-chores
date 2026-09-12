"""The Household Chores integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
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
        _LOGGER.info("Chores integration initialized")
    else:
        storage = hass.data[DOMAIN]["storage"]
        await storage.async_load()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload entities when options are updated.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


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
