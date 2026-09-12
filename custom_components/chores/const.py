"""Constants for the Household Chores integration."""

DOMAIN = "chores"

# Config entry data keys
CONF_NAME = "name"
CONF_FREQUENCY_TYPE = "frequency_type"
CONF_FREQUENCY_VALUE = "frequency_value"
CONF_FREQUENCY_UNIT = "frequency_unit"
CONF_SCHEDULE = "schedule"
CONF_ASSIGNEES = "assignees"
CONF_ACTIVE = "active"
CONF_ICON = "icon"

# Attribute keys
ATTR_LAST_DONE = "last_done"
ATTR_LAST_DONE_BY = "last_done_by"
ATTR_NEXT_DUE = "next_due"
ATTR_ASSIGNEES = "assignees"
ATTR_FREQUENCY = "frequency"
ATTR_FREQUENCY_DAYS = "frequency_days"
ATTR_COMPLETION_LOG = "completion_log"
ATTR_DAYS_UNTIL_DUE = "days_until_due"

# Status values
STATUS_DEACTIVATED = "deactivated"
STATUS_PENDING = "pending"
STATUS_DUE = "due"

# Frequency types
FREQUENCY_TYPE_INTERVAL = "interval"
FREQUENCY_TYPE_SCHEDULE = "schedule"

# Frequency units
FREQUENCY_UNIT_DAYS = "days"
FREQUENCY_UNIT_WEEKS = "weeks"
FREQUENCY_UNIT_MONTHS = "months"

# Map frequency units to number of days
FREQUENCY_UNIT_TO_DAYS = {
    FREQUENCY_UNIT_DAYS: lambda v: v,
    FREQUENCY_UNIT_WEEKS: lambda v: v * 7,
    FREQUENCY_UNIT_MONTHS: lambda v: v * 30,
}

# Days of week
DAYS_OF_WEEK = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

# Services
SERVICE_MARK_DONE = "mark_done"
SERVICE_RESET = "reset"
SERVICE_SET_ACTIVE = "set_active"

# Service fields
FIELD_ENTITY_ID = "entity_id"
FIELD_CHORE_ID = "chore_id"
FIELD_PERSON = "person"
FIELD_NOTES = "notes"
FIELD_ACTIVE = "active"

# Storage
STORAGE_KEY = "chores"
STORAGE_VERSION = 1

# Platform
PLATFORM_SENSOR = "sensor"
PLATFORMS = [PLATFORM_SENSOR]
