# Household Chores

A custom Home Assistant integration for managing household chores with recurring schedules, person assignments, and completion tracking.

> **Disclaimer:** This is a work in progress. It is not production-ready and may contain bugs. Use at your own risk. No guarantees are made about data integrity or stability.

## Features

- Each chore is a separate config entry, added via the HA UI
- Two frequency types:
  - **Interval**: every X days, weeks, or months since last completed
  - **Schedule**: specific days of the week (e.g. every Monday, Thursday, Saturday)
- Assign one or multiple HA person entities to each chore
- Automatic status: `due` or `pending` based on the next due date
- Completion log: who completed it, when, and optional notes
- Custom Lovelace card that dynamically discovers all chore sensors
- English and German translations

## Installation

### 1. Copy the integration

Copy the `custom_components/chores/` directory into your Home Assistant config directory:

```
config/
└── custom_components/
    └── chores/
        ├── __init__.py
        ├── manifest.json
        ├── config_flow.py
        ├── const.py
        ├── entity.py
        ├── frontend.py
        ├── sensor.py
        ├── services.py
        ├── services.yaml
        ├── storage.py
        ├── helpers.py
        ├── www/
        │   └── chores-card.js
        └── translations/
            ├── en.json
            └── de.json
```

If you already have a `custom_components/` directory, just add the `chores/` subdirectory.

### 2. Restart Home Assistant

Restart HA so it picks up the new integration. The custom Lovelace card is bundled with the integration and registered automatically on startup -- no manual resource setup or file copying needed.

## Adding Chores

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for "Household Chores"
3. Follow the config flow:
   - **Step 1**: Enter the chore name and choose frequency type (interval or schedule)
   - **Step 2**: For interval -- enter a number and unit (days, weeks, months). For schedule -- select days of the week
   - **Step 3**: Optionally assign person entities and choose an icon
4. Repeat for each chore you want to track

Each chore creates a sensor entity with the ID `sensor.chores_<name>` (umlauts are transliterated, e.g. "Mull rausbringen" becomes `sensor.chores_muell_rausbringen`).

## Editing Chores

Go to **Settings > Devices & Services > Household Chores**, click **Configure** on any chore entry to edit its name, frequency, assignees, and icon.

To disable a chore, use HA's built-in entity disabling: **Settings > Devices & Services > Entities**, find the chore sensor, and disable it. Disabled entities are hidden from the dashboard.

## Services

### `chores.mark_done`

Mark a chore as completed. Automatically sets the next due date and adds an entry to the completion log.

| Field | Required | Description |
|-------|----------|-------------|
| `entity_id` | One of entity_id/chore_id | The chore sensor entity ID |
| `chore_id` | One of entity_id/chore_id | The config entry ID |
| `person` | No | The person entity who completed the chore |
| `notes` | No | Optional notes about this completion |

Example:

```yaml
service: chores.mark_done
data:
  entity_id: sensor.chores_take_out_trash
  person: person.marc
  notes: Done early this week
```

### `chores.reset`

Reset a chore's completion state. Clears last done, next due, and the completion log.

| Field | Required | Description |
|-------|----------|-------------|
| `entity_id` | One of entity_id/chore_id | The chore sensor entity ID |
| `chore_id` | One of entity_id/chore_id | The config entry ID |

## Using the Chores Card

The integration includes a custom Lovelace card (`custom:chores-card`) that automatically discovers all `sensor.chores_*` entities. Add it to any of your existing dashboards.

### Card configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `type` | string | -- | Must be `custom:chores-card` |
| `title` | string | none | Optional heading displayed above the chore list |
| `only_state` | string | none | Filter to a single state: `due` or `pending`. Omit to show all. |

### Examples

Show only due chores:

```yaml
type: custom:chores-card
title: Due now
only_state: due
```

Show only upcoming chores:

```yaml
type: custom:chores-card
title: Upcoming
only_state: pending
```

Show all chores:

```yaml
type: custom:chores-card
title: All chores
```

### What the card shows

Each chore row displays:
- Name and icon
- Due status (e.g. "Due today", "3 days overdue", "Due in 5 days")
- Assigned persons
- Last completed date and who did it

Tap **Done** to mark a chore as completed. The currently logged-in HA user is automatically recorded as the person who completed it (matched by name to a person entity).

## Entity Attributes

Each chore sensor exposes the following attributes:

| Attribute | Description |
|-----------|-------------|
| `assignees` | List of assigned person entity IDs |
| `frequency` | Human-readable frequency description (e.g. "Every 7 days", "Every Monday, Thursday") |
| `last_done` | ISO timestamp of last completion |
| `last_done_by` | Person entity ID of who last completed it |
| `next_due` | Date of next due date (e.g. "2026-09-12") |
| `days_until_due` | Days until due (0 = today, negative = overdue, null = never) |
| `completion_log` | List of all completion entries with timestamp, person, and notes |
