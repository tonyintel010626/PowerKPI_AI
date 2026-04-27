---
name: planning
description: NGA Planning Service for test planning - manage test groups, suites, steps, actions, and configurations
license: MIT
---

# NGA Planning Service Skill

This skill provides access to the NGA Planning Service API for managing test planning elements including test groups, suites, steps, actions, software configurations, and setup flows.

## Key Capabilities

The Planning Service manages the structure and organization of validation tests:
- **Test Groups** - Organize related test suites
- **Test Suites** - Collections of test lines for specific validation scenarios
- **Test Steps** - Individual test execution steps
- **Test Lines** - Complete test configurations linking suites, groups, and steps
- **Actions** - Automated actions triggered by test events
- **Software Configs** - Software configuration definitions

## Common GET Endpoints

### Test Groups
```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get all test groups (with paging)
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestGroup/List?page=1&pageSize=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get test group by ID
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestGroup/<group_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Test Suites
```python
# Get all test suites
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestSuite/List?page=1&pageSize=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get test lines for a suite
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestSuite/<suite_id>/TestLines',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Test Steps & Lines
```python
# Get test step by ID
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestStep/<step_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get test line steps
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestLine/<line_id>/Steps',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

See `swagger.json` for complete API specification.