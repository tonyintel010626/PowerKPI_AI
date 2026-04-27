---
name: lab-station-manager
description: "Script-backed skill for managing lab station inventory, reservations, and health monitoring via Python CLI tools"
disable: false
license: MIT
---

# Lab Station Manager

## Script Location

Scripts are located at `<cwd>/.opencode/skill/lab-station-manager/`

## Overview

This skill provides Python-based tools for managing lab test stations. It supports querying station inventory, making/releasing reservations, and monitoring station health status.

## Supported Operations

- **Query stations** — List all stations, filter by status/type/location
- **Reserve station** — Reserve a station for exclusive use
- **Release station** — Release a previously reserved station
- **Check health** — Run health diagnostics on a specific station
- **Get station details** — Retrieve full configuration and history for a station

## Prerequisites

Install required packages:

```bash
pip install requests tabulate
```

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `LAB_API_URL` | Lab management API base URL | Yes | — |
| `LAB_API_TOKEN` | Authentication token for the API | Yes | — |
| `LAB_DEFAULT_SITE` | Default lab site to query | No | `all` |

## How to Use

### CLI Usage

#### List all stations
```bash
python <cwd>/.opencode/skill/lab-station-manager/station_manager.py list --site folsom
```

#### Filter by status
```bash
python <cwd>/.opencode/skill/lab-station-manager/station_manager.py list --status available --type validation
```

#### Reserve a station
```bash
python <cwd>/.opencode/skill/lab-station-manager/station_manager.py reserve --station-id FSM-VAL-042 --duration 8h --reason "BKC validation"
```

#### Release a station
```bash
python <cwd>/.opencode/skill/lab-station-manager/station_manager.py release --station-id FSM-VAL-042
```

#### Check station health
```bash
python <cwd>/.opencode/skill/lab-station-manager/station_manager.py health --station-id FSM-VAL-042
```

#### Get station details
```bash
python <cwd>/.opencode/skill/lab-station-manager/station_manager.py details --station-id FSM-VAL-042
```

### Python API Usage

```python
import sys
sys.path.insert(0, "<cwd>/.opencode/skill/lab-station-manager")
from station_manager import StationManager

manager = StationManager()

# List available stations
stations = manager.list_stations(status="available", site="folsom")
print(f"Found {len(stations)} available stations")

# Reserve a station
result = manager.reserve("FSM-VAL-042", duration_hours=8, reason="BKC validation")
print(f"Reservation ID: {result['reservation_id']}")

# Check health
health = manager.check_health("FSM-VAL-042")
print(f"Health status: {health['status']}")  # "healthy", "degraded", "offline"

# Release when done
manager.release("FSM-VAL-042")
```

## API Response Format

All CLI commands output JSON to stdout:

### List Response
```json
{
  "stations": [
    {
      "station_id": "FSM-VAL-042",
      "type": "validation",
      "site": "folsom",
      "status": "available",
      "platform": "MTL-P",
      "last_health_check": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "filters_applied": {"status": "available"}
}
```

### Health Response
```json
{
  "station_id": "FSM-VAL-042",
  "status": "healthy",
  "checks": {
    "power": "ok",
    "network": "ok",
    "dut_connection": "ok",
    "storage": "ok",
    "ttk3_device": "ok"
  },
  "last_checked": "2025-01-15T10:30:00Z",
  "uptime_hours": 168
}
```

## Error Handling

| Error Code | Meaning | Recovery |
|-----------|---------|----------|
| `AUTH_FAILED` | Invalid or expired API token | Refresh LAB_API_TOKEN |
| `STATION_NOT_FOUND` | Station ID doesn't exist | Verify station ID with `list` command |
| `STATION_RESERVED` | Station already reserved by another user | Use `list --status available` to find alternatives |
| `RESERVATION_EXPIRED` | Your reservation has expired | Re-reserve the station if still needed |
| `HEALTH_CHECK_TIMEOUT` | Station didn't respond to health check | Station may be offline — contact lab admin |

## Limitations

- Reservations have a maximum duration of 72 hours
- Health checks may take up to 60 seconds for offline stations (timeout)
- Station inventory is cached for 5 minutes — recent changes may not appear immediately
- This tool manages reservations only — it does not power cycle or configure stations (use TTK3 skills for that)

## Security Notes

- API tokens are scoped to your user account — never share tokens
- All operations are logged with your user ID for audit purposes
- The `--force` flag on release requires team-lead permissions
