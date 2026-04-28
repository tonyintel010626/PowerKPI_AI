---
name: nga/failure
description: NGA Failure Service for failure tracking, buckets, and sighting integration
---

# NGA Failure Service

Manages failure tracking, buckets, and sighting integration.

## Quick Start

```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get failures from last 7 days
status, data = NgaAPIUtils.NgaGet(
    '/Failure/<nga_project>/api/Failure/Failures/7',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
print(json.dumps(data, indent=2))
```

---

## API Endpoints

### Failures

```python
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

# Get failure by ID
status, data = NgaAPIUtils.NgaGet(
    '/Failure/<nga_project>/api/Failure/<failure_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get failures by test run ID
status, data = NgaAPIUtils.NgaGet(
    '/Failure/<nga_project>/api/Failure/GetByTestRunId/<test_run_id>',
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

# Get all buckets (with paging)
status, data = NgaAPIUtils.NgaGet(
    '/Failure/<nga_project>/api/Bucket/List?page=1&pageSize=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get bucket statistics
status, data = NgaAPIUtils.NgaGet(
    '/Failure/<nga_project>/api/Bucket/<bucket_id>/Statistics',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Sighting Links

```python
# Get sighting link for failure
status, data = NgaAPIUtils.NgaGet(
    '/Failure/<nga_project>/api/Failure/<failure_id>/SightingLink',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Service Version

```python
# Get Failure service version
status, data = NgaAPIUtils.NgaGet(
    '/Failure/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

---

## Parameters

| Parameter | Description |
|-----------|-------------|
| `<nga_project>` | NGA project name (e.g., `ptl_pcd_validation`) |
| `<failure_id>` | UUID of the failure |
| `<bucket_id>` | UUID of the failure bucket |
| `<test_run_id>` | UUID of the test run |
| `<days_ago>` | Number of days to look back |

---

## Related Skills

- `nga/sightingfailurerules` - Sighting rules management
- `nga/search` - OData search for failures
- `nga/results` - Test execution results
