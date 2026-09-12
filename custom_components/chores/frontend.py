"""Frontend card registration for the Chores integration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.const import EVENT_COMPONENT_LOADED
from homeassistant.core import HomeAssistant, Event

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILE = "chores-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILE}"
RESOURCE_REGISTERED_KEY = f"{DOMAIN}_card_registered"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register the custom Lovelace card as a lovelace resource.

    This serves the card JS from the integration's www/ directory and
    registers it as a lovelace resource so users don't need to manually
    add it in the UI.
    """
    if hass.data.get(RESOURCE_REGISTERED_KEY):
        return

    www_dir = Path(__file__).parent / "www"
    card_path = www_dir / CARD_FILE

    if not card_path.is_file():
        _LOGGER.warning("Chores card file not found at %s", card_path)
        return

    # Register the static path so the JS file is served by HA.
    await _async_register_static_path(hass, f"/{DOMAIN}", str(www_dir))

    # Register as a lovelace resource.
    if hass.data.get("lovelace"):
        await _async_init_resource(hass)
    else:
        _LOGGER.debug("Lovelace not loaded yet; deferring resource registration")

        async def _on_lovelace_loaded(event: Event) -> None:
            if event.data.get("component") == "lovelace":
                _LOGGER.debug("Lovelace loaded; registering chores card resource")
                try:
                    await _async_init_resource(hass)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    _LOGGER.debug("Deferred resource registration failed: %s", exc)

        hass.bus.async_listen(EVENT_COMPONENT_LOADED, _on_lovelace_loaded)


async def _async_register_static_path(
    hass: HomeAssistant, url_path: str, path: str
) -> None:
    """Register a static path for serving the card JS."""
    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(url_path, path, False)]
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _LOGGER.debug("Failed to register static path %s: %s", url_path, exc)
        # Fall back to legacy sync API.
        try:
            hass.http.register_static_path(url_path, path, cache_headers=True)
        except Exception as exc2:  # pylint: disable=broad-exception-caught
            _LOGGER.warning(
                "Failed to register static path %s: %s / %s", url_path, exc, exc2
            )


async def _async_init_resource(hass: HomeAssistant) -> None:
    """Add or update the Lovelace resource for the chores card."""
    try:
        from homeassistant.components.frontend import add_extra_js_url
        from homeassistant.components.lovelace.resources import (
            ResourceStorageCollection,
        )
    except Exception:  # pylint: disable=broad-exception-caached
        _LOGGER.debug("Lovelace resource helpers unavailable")
        return

    lovelace = hass.data.get("lovelace")
    if not lovelace:
        _LOGGER.debug("Lovelace storage not available")
        return

    resources: Any = (
        lovelace.resources if hasattr(lovelace, "resources") else lovelace["resources"]
    )

    if not isinstance(resources, ResourceStorageCollection):
        # Non-storage mode (e.g. YAML dashboards).
        _LOGGER.debug("Adding extra JS module (non-storage): %s", CARD_URL)
        add_extra_js_url(hass, CARD_URL)
        hass.data[RESOURCE_REGISTERED_KEY] = True
        return

    await resources.async_get_info()

    # Check if resource already exists.
    for item in resources.async_items():
        if not isinstance(item, dict):
            continue
        item_url = item.get("url", "")
        if item_url.startswith(CARD_URL):
            _LOGGER.debug("Chores card resource already registered")
            hass.data[RESOURCE_REGISTERED_KEY] = True
            return

    # Create new resource.
    _LOGGER.debug("Adding new lovelace resource: %s", CARD_URL)
    await resources.async_create_item({"res_type": "module", "url": CARD_URL})
    hass.data[RESOURCE_REGISTERED_KEY] = True
    _LOGGER.info("Chores Lovelace card registered at %s", CARD_URL)
