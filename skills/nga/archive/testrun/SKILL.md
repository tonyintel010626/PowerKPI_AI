---
name: testrun
description: NGA Test Run Service for managing test run execution, reruns, and priority queues
license: MIT
---

# NGA Test Run Service Skill

This skill provides access to the NGA Test Run Service API for managing test run execution, reruns, priority queues, and fan out operations.

## Key Capabilities

The Test Run Service manages test execution lifecycle:
- **Test Runs** - Fetch test run details and status
- **Reruns** - Access rerun information and reasons
- **Priority Queues** - View test run priority queue information
- **Station Setup** - Retrieve station setup flow configurations

## Common GET Endpoints

### Test Run Information
```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

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
```

### Rerun Information
```python
# Get all rerun reasons
status, data = NgaAPIUtils.NgaGet(
    '/TestRun/<nga_project>/api/RerunReason/GetAll',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Station Setup
```python
# Get station setup flow by test line ID
status, data = NgaAPIUtils.NgaGet(
    '/TestRun/<nga_project>/api/StationSetupFlow/GetByTestLineId?testLineId=<line_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Service Information
```python
# Get service version
status, data = NgaAPIUtils.NgaGet(
    '/TestRun/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

See `swagger.json` for complete API specification.
