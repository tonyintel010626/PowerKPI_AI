---
name: nga/results
description: NGA Results Service for fetching test execution results and messages
---

# NGA Results Service

Retrieves test execution results and execution messages from NGA.

## Quick Start

```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get test run result by ID
status, data = NgaAPIUtils.NgaGet(
    '/Results/<nga_project>/api/TestRun/<test_run_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
print(json.dumps(data, indent=2))
```

---

## API Endpoints

### Test Run Results

```python
# Get test run result by ID
status, data = NgaAPIUtils.NgaGet(
    '/Results/<nga_project>/api/TestRun/<test_run_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all tests for a suite
status, data = NgaAPIUtils.NgaGet(
    '/Results/<nga_project>/api/TestSuite/<suite_id>/AllTests',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get test suite results
status, data = NgaAPIUtils.NgaGet(
    '/Results/<nga_project>/api/TestSuite/<suite_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Execution Messages

```python
# Get execution messages for a test run
status, data = NgaAPIUtils.NgaGet(
    '/Results/<nga_project>/api/ExecutionMessage/<test_run_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Service Version

```python
# Get Results service version
status, data = NgaAPIUtils.NgaGet(
    '/Results/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

---

## Parameters

| Parameter | Description |
|-----------|-------------|
| `<nga_project>` | NGA project name (e.g., `ptl_pcd_validation`) |
| `<test_run_id>` | UUID of the test run |
| `<suite_id>` | UUID of the test suite |

---

## Related Skills

- `nga/testrun` - Test run execution management
- `nga/search` - OData search for test results
- `nga/failure` - Failure tracking
