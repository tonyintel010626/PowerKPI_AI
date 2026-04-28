---
name: results
description: NGA Results Service for fetching test execution results and messages
license: MIT
---

# NGA Results Service Skill

This skill provides access to the NGA Results Service API for retrieving test execution results and execution messages.

## Key Capabilities

The Results Service manages test execution outcomes:
- **Test Run Results** - Get complete test run execution data
- **Test Suite Results** - Retrieve all test results for a suite
- **Execution Messages** - Access detailed execution messages and logs

## Common GET Endpoints

### Test Run Results
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

### Test Suite Results
```python
# Get all tests for a suite
status, data = NgaAPIUtils.NgaGet(
    '/Results/<nga_project>/api/TestSuite/<suite_id>/AllTests',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

## Example Usage

Given URL: `https://nga-prod.laas.intel.com/#/ptl_pcd_validation/planning/testResult/6406862c-b684-4d14-bc33-46002572141e`

Extract the test run ID (`6406862c-b684-4d14-bc33-46002572141e`) and fetch results:

```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

status, data = NgaAPIUtils.NgaGet(
    '/Results/<nga_project>/api/TestRun/6406862c-b684-4d14-bc33-46002572141e',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
print(json.dumps(data, indent=2))
```

See `swagger.json` for complete API specification.