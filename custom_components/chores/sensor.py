"""Sensor platform for the Household Chores integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import ChoreEntity
from .storage import ChoreStorage

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up chore sensor entities from a config entry."""
    storage: ChoreStorage = hass.data[DOMAIN]["storage"]
    await storage.async_load()

    config = dict(config_entry.data)
    chore_id = config_entry.entry_id

    entity = ChoreEntity(hass, config_entry.entry_id, chore_id, config, storage)

    # Store a reference so services can trigger immediate state updates.
    if "entities" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["entities"] = {}
    hass.data[DOMAIN]["entities"][entity.entity_id] = entity

    async_add_entities([entity], update_before_add=True)
