"""Config flow for the Household Chores integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ACTIVE,
    CONF_ASSIGNEES,
    CONF_FREQUENCY_TYPE,
    CONF_FREQUENCY_UNIT,
    CONF_FREQUENCY_VALUE,
    CONF_ICON,
    CONF_NAME,
    CONF_SCHEDULE,
    DAYS_OF_WEEK,
    DOMAIN,
    FREQUENCY_TYPE_INTERVAL,
    FREQUENCY_TYPE_SCHEDULE,
    FREQUENCY_UNIT_DAYS,
    FREQUENCY_UNIT_MONTHS,
    FREQUENCY_UNIT_WEEKS,
)
from .helpers import slugify_name

_LOGGER = logging.getLogger(__name__)


class ChoresConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Chores integration."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "ChoresOptionsFlow":
        """Get the options flow for this integration."""
        return ChoresOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """First step: choose name and frequency type."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Store the data from this step and move to the next step.
            self._name = user_input[CONF_NAME]
            self._frequency_type = user_input[CONF_FREQUENCY_TYPE]

            if self._frequency_type == FREQUENCY_TYPE_INTERVAL:
                return await self.async_step_interval()
            return await self.async_step_schedule()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_FREQUENCY_TYPE): selector.selector(
                    {"select": {
                        "options": [
                            {"label": "interval", "value": FREQUENCY_TYPE_INTERVAL},
                            {"label": "schedule", "value": FREQUENCY_TYPE_SCHEDULE},
                        ],
                        "translation_key": "frequency_type",
                    }}
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_interval(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step for interval-based frequency configuration."""
        if user_input is not None:
            self._frequency_value = user_input[CONF_FREQUENCY_VALUE]
            self._frequency_unit = user_input[CONF_FREQUENCY_UNIT]
            return await self.async_step_details()

        schema = vol.Schema(
            {
                vol.Required(CONF_FREQUENCY_VALUE, default=7): vol.All(
                    int, vol.Range(min=1, max=365)
                ),
                vol.Required(CONF_FREQUENCY_UNIT, default=FREQUENCY_UNIT_DAYS): selector.selector(
                    {"select": {
                        "options": [
                            {"label": "days", "value": FREQUENCY_UNIT_DAYS},
                            {"label": "weeks", "value": FREQUENCY_UNIT_WEEKS},
                            {"label": "months", "value": FREQUENCY_UNIT_MONTHS},
                        ],
                        "translation_key": "frequency_unit",
                    }}
                ),
            }
        )

        return self.async_show_form(step_id="interval", data_schema=schema)

    async def async_step_schedule(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step for schedule-based frequency configuration."""
        if user_input is not None:
            self._schedule = user_input[CONF_SCHEDULE]
            return await self.async_step_details()

        schema = vol.Schema(
            {
                vol.Required(CONF_SCHEDULE): selector.selector(
                    {"select": {
                        "options": [
                            {"label": day.capitalize(), "value": day}
                            for day in DAYS_OF_WEEK
                        ],
                        "multiple": True,
                    }}
                ),
            }
        )

        return self.async_show_form(step_id="schedule", data_schema=schema)

    async def async_step_details(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Final step: assignees and icon."""
        if user_input is not None:
            data = {
                CONF_NAME: self._name,
                CONF_FREQUENCY_TYPE: self._frequency_type,
            }

            if self._frequency_type == FREQUENCY_TYPE_INTERVAL:
                data[CONF_FREQUENCY_VALUE] = self._frequency_value
                data[CONF_FREQUENCY_UNIT] = self._frequency_unit
            else:
                data[CONF_SCHEDULE] = self._schedule

            if user_input.get(CONF_ASSIGNEES):
                data[CONF_ASSIGNEES] = user_input[CONF_ASSIGNEES]

            if user_input.get(CONF_ICON):
                data[CONF_ICON] = user_input[CONF_ICON]

            # Check for duplicate name.
            slug = slugify_name(self._name)
            for entry in self._async_current_entries():
                if slug == slugify_name(entry.data.get(CONF_NAME, "")):
                    return self.async_abort(reason="already_exists")

            title = f"Chore: {self._name}"
            return self.async_create_entry(title=title, data=data)

        schema = vol.Schema(
            {
                vol.Optional(CONF_ASSIGNEES): selector.selector(
                    {"entity": {
                        "domain": "person",
                        "multiple": True,
                    }}
                ),
                vol.Optional(CONF_ICON, default="mdi:clipboard-check"): selector.selector(
                    {"icon": {}}
                ),
            }
        )

        return self.async_show_form(step_id="details", data_schema=schema)


class ChoresOptionsFlow(config_entries.OptionsFlow):
    """Options flow for editing an existing chore."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the chore options."""
        if user_input is not None:
            # Merge new data with existing entry data.
            new_data = dict(self._config_entry.data)
            new_data.update(user_input)
            self.hass.config_entries.async_update_entry(
                self._config_entry, data=new_data
            )
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.data
        freq_type = current.get(CONF_FREQUENCY_TYPE)

        schema_dict: dict[Any, Any] = {
            vol.Required(CONF_NAME, default=current.get(CONF_NAME, "")): str,
        }

        if freq_type == FREQUENCY_TYPE_INTERVAL:
            schema_dict[
                vol.Required(
                    CONF_FREQUENCY_VALUE,
                    default=current.get(CONF_FREQUENCY_VALUE, 7),
                )
            ] = vol.All(int, vol.Range(min=1, max=365))
            schema_dict[
                vol.Required(
                    CONF_FREQUENCY_UNIT,
                    default=current.get(CONF_FREQUENCY_UNIT, FREQUENCY_UNIT_DAYS),
                )
            ] = selector.selector(
                {"select": {
                    "options": [
                        {"label": "days", "value": FREQUENCY_UNIT_DAYS},
                        {"label": "weeks", "value": FREQUENCY_UNIT_WEEKS},
                        {"label": "months", "value": FREQUENCY_UNIT_MONTHS},
                    ],
                    "translation_key": "frequency_unit",
                }}
            )
        else:
            schema_dict[
                vol.Required(
                    CONF_SCHEDULE,
                    default=current.get(CONF_SCHEDULE, []),
                )
            ] = selector.selector(
                {"select": {
                    "options": [
                        {"label": day.capitalize(), "value": day}
                        for day in DAYS_OF_WEEK
                    ],
                    "multiple": True,
                }}
            )

        schema_dict[
            vol.Optional(
                CONF_ASSIGNEES,
                default=current.get(CONF_ASSIGNEES, []),
            )
        ] = selector.selector({"entity": {"domain": "person", "multiple": True}})

        schema_dict[
            vol.Optional(
                CONF_ICON,
                default=current.get(CONF_ICON, "mdi:clipboard-check"),
            )
        ] = selector.selector({"icon": {}})

        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(schema_dict)
        )
