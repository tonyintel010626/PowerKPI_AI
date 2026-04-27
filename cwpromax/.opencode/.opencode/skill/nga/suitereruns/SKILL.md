---
name: nga/suitereruns
description: NGA Suite Reruns Service for managing suite rerun scheduling (immediate, automatic, recurrent)
---

# NGA Suite Reruns Service

Manages suite rerun scheduling including immediate, automatic, and recurrent reruns.

## Quick Start

```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get suite reruns by suite ID
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/SuiteReruns/<suite_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
print(json.dumps(data, indent=2))
```

---

## API Endpoints

### Suite Reruns

```python
# Get suite reruns by suite ID
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/SuiteReruns/<suite_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get suite rerun schedules
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/SuiteRerunSchedules/<suite_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get suite rerun by ID
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/<rerun_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Rerun Instances

```python
# Get suite rerun instance by ID
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/SuiteRerunInstance/<instance_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all instances for a suite
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/SuiteRerunInstances/<suite_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get instances by request ID
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/SuiteRerunInstancesByRequestId/<request_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get latest instances
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/LatestSuiteRerunInstances/<suite_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Rerun Requests

```python
# Get rerun request by ID
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/RerunRequest/<request_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all rerun requests for suite
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/RerunRequests/<suite_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Rerun Schedules

```python
# Get rerun schedule by ID
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/RerunSchedule/<schedule_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all rerun schedules
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/RerunSchedules',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Service Version

```python
# Get SuiteReruns service version
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

---

## Parameters

| Parameter | Description |
|-----------|-------------|
| `<nga_project>` | NGA project name (e.g., `ptl_pcd_validation`) |
| `<suite_id>` | UUID of the test suite |
| `<rerun_id>` | UUID of the suite rerun |
| `<instance_id>` | UUID of the rerun instance |
| `<request_id>` | UUID of the rerun request |
| `<schedule_id>` | UUID of the rerun schedule |

---

## Related Skills

- `nga/testrun` - Test run execution
- `nga/planning` - Test suite planning
