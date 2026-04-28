---
name: nga/notifications
description: NGA Notifications Service for managing notification publishing and subscriptions
---

# NGA Notifications Service

Manages notification publishing and subscriptions.

## Quick Start

```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get all my subscriptions
status, data = NgaAPIUtils.NgaGet(
    '/Notifications/<nga_project>/api/Subscription/GetAllMySubscriptions',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
print(json.dumps(data, indent=2))
```

---

## API Endpoints

### Subscriptions

```python
# Get subscriptions by event type
status, data = NgaAPIUtils.NgaGet(
    '/Notifications/<nga_project>/api/Subscription/GetSubscriptions/<event_type>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all my subscriptions
status, data = NgaAPIUtils.NgaGet(
    '/Notifications/<nga_project>/api/Subscription/GetAllMySubscriptions',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get subscription by ID
status, data = NgaAPIUtils.NgaGet(
    '/Notifications/<nga_project>/api/Subscription/<subscription_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get subscriptions by entity
status, data = NgaAPIUtils.NgaGet(
    '/Notifications/<nga_project>/api/Subscription/GetByEntity/<entity_type>/<entity_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Event Types

```python
# Get all available event types
status, data = NgaAPIUtils.NgaGet(
    '/Notifications/<nga_project>/api/EventType/GetAll',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get event type by name
status, data = NgaAPIUtils.NgaGet(
    '/Notifications/<nga_project>/api/EventType/<event_type_name>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Notification History

```python
# Get notification history
status, data = NgaAPIUtils.NgaGet(
    '/Notifications/<nga_project>/api/Notification/History?page=1&pageSize=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get notification by ID
status, data = NgaAPIUtils.NgaGet(
    '/Notifications/<nga_project>/api/Notification/<notification_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Service Version

```python
# Get Notifications service version
status, data = NgaAPIUtils.NgaGet(
    '/Notifications/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

---

## Parameters

| Parameter | Description |
|-----------|-------------|
| `<nga_project>` | NGA project name (e.g., `ptl_pcd_validation`) |
| `<event_type>` | Event type identifier |
| `<subscription_id>` | UUID of the subscription |
| `<entity_type>` | Entity type (e.g., TestSuite, TestLine) |
| `<entity_id>` | UUID of the entity |
| `<event_type_name>` | Name of the event type |
| `<notification_id>` | UUID of the notification |

---

## Related Skills

- `nga/projects` - Project management
- `nga/planning` - Test planning
