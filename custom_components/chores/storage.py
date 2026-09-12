"""Persistent storage for chore states."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class ChoreStorage:
    """Manages persistent state for all chores in .storage/chores.json."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the storage."""
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY
        )
        self._data: dict[str, dict[str, Any]] | None = None

    async def async_load(self) -> dict[str, dict[str, Any]]:
        """Load chore states from storage."""
        if self._data is not None:
            return self._data

        data = await self._store.async_load()
        if data is None:
            self._data = {}
        else:
            self._data = data

        return self._data

    async def async_save(self) -> None:
        """Persist chore states to storage."""
        if self._data is None:
            _LOGGER.warning("Cannot save: chore storage not loaded yet")
            return
        await self._store.async_save(self._data)

    def get_chore_state(self, chore_id: str) -> dict[str, Any]:
        """Get the runtime state for a single chore."""
        if self._data is None:
            return {}
        return self._data.get(chore_id, {})

    def set_chore_state(self, chore_id: str, state: dict[str, Any]) -> None:
        """Set the runtime state for a single chore."""
        if self._data is None:
            self._data = {}
        self._data[chore_id] = state

    async def async_update_chore_state(
        self, chore_id: str, updates: dict[str, Any]
    ) -> dict[str, Any]:
        """Update specific fields of a chore's state and persist."""
        if self._data is None:
            await self.async_load()

        current = self._data.get(chore_id, {})
        current.update(updates)
        self._data[chore_id] = current
        await self.async_save()
        return current

    async def async_remove_chore(self, chore_id: str) -> None:
        """Remove a chore's state from storage."""
        if self._data is None:
            await self.async_load()
        if chore_id in self._data:
            del self._data[chore_id]
            await self.async_save()
