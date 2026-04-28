---
name: nga/testrun
description: NGA Test Run Service for managing test run execution, reruns, and priority queues
---

# NGA Test Run Service

Manages test run execution, reruns, and priority queues.

## Quick Start

```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get test run by ID
status, data = NgaAPIUtils.NgaGet(
    '/TestRun/<nga_project>/api/TestRun/<test_run_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
print(json.dumps(data, indent=2))
```

---

## API Endpoints

### Test Run Information

```python
# Get test run by ID
status, data = NgaAPIUtils.NgaGet(
    '/TestRun/<nga_project>/api/TestRun/<test_run_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get latest test run for a test line
status, data = NgaAPIUtils.NgaGet(
    '/TestRun/<nga_project>/api/TestRun/GetLatestTestRun/<test_line_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get test runs by suite (with paging)
status, data = NgaAPIUtils.NgaGet(
    '/TestRun/<nga_project>/api/TestRun/GetBySuite?suiteId=<suite_id>&page=1&pageSize=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get test runs by test line (with paging)
status, data = NgaAPIUtils.NgaGet(
    '/TestRun/<nga_project>/api/TestRun/GetByTestLine?testLineId=<test_line_id>&page=1&pageSize=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Rerun Information

```python
# Get all rerun reasons
status, data = NgaAPIUtils.NgaGet(
    '/TestRun/<nga_project>/api/RerunReason/GetAll',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get rerun reason by ID
status, data = NgaAPIUtils.NgaGet(
    '/TestRun/<nga_project>/api/RerunReason/<reason_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Station Setup

```python
# Get station setup flow by test line ID
status, data = NgaAPIUtils.NgaGet(
    '/TestRun/<nga_project>/api/StationSetupFlow/GetByTestLineId?testLineId=<test_line_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get station setup flow by ID
status, data = NgaAPIUtils.NgaGet(
    '/TestRun/<nga_project>/api/StationSetupFlow/<flow_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Priority Queue

```python
# Get priority queue status
status, data = NgaAPIUtils.NgaGet(
    '/TestRun/<nga_project>/api/PriorityQueue/Status',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Service Version

```python
# Get TestRun service version
status, data = NgaAPIUtils.NgaGet(
    '/TestRun/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

---

## Parameters

| Parameter | Description |
|-----------|-------------|
| `<nga_project>` | NGA project name (e.g., `ptl_pcd_validation`) |
| `<test_run_id>` | UUID of the test run |
| `<test_line_id>` | UUID of the test line |
| `<suite_id>` | UUID of the test suite |
| `<reason_id>` | UUID of the rerun reason |
| `<flow_id>` | UUID of the station setup flow |

---

## Related Skills

- `nga/results` - Test execution results
- `nga/suitereruns` - Suite rerun scheduling
- `nga/planning` - Test planning
