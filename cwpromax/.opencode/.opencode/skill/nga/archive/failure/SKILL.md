---
name: failure
description: NGA Failure Service for failure tracking, buckets, and sighting integration
license: MIT
---

# NGA Failure Service Skill

This skill provides access to the NGA Failure Service API for managing failure tracking, failure buckets, and sighting integration.

## Key Capabilities

The Failure Service manages test failure analysis:
- **Failures** - Retrieve failure records and history
- **Failure Buckets** - Access categorized failure buckets
- **Sightings** - View integrated sighting data

## Common GET Endpoints

### Failures
```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get failures from last N days
status, data = NgaAPIUtils.NgaGet(
    '/Failure/<nga_project>/api/Failure/Failures/<days_ago>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get failures by bucket ID
status, data = NgaAPIUtils.NgaGet(
    '/Failure/<nga_project>/api/Failure/GetByBucketId/<bucket_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Failure Buckets
```python
# Get failure bucket by ID
status, data = NgaAPIUtils.NgaGet(
    '/Failure/<nga_project>/api/Bucket/<bucket_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

See `swagger.json` for complete API specification.
