---
name: notifications
description: NGA Notifications Service for managing notification publishing and subscriptions
license: MIT
---

# NGA Notifications Service Skill

This skill provides access to the NGA Notifications Service API for managing notification subscriptions.

## Key Capabilities

The Notifications Service manages event notifications:
- **Subscriptions** - View notification subscriptions
- **Event Types** - Access subscription by event type

## Common GET Endpoints

### Subscriptions
```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

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
```

### Service Information
```python
# Get service version
status, data = NgaAPIUtils.NgaGet(
    '/Notifications/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

See `swagger.json` for complete API specification.
