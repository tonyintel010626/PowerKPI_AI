---
name: nga/planning
description: NGA Planning Service for test planning - manage test groups, suites, steps, actions, and configurations
---

# NGA Planning Service

Manages test planning including test groups, suites, steps, actions, and configurations.

## Quick Start

```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get all test groups
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestGroup/List?page=1&pageSize=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
print(json.dumps(data, indent=2))
```

---

## API Endpoints

### Test Groups

```python
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

# Get test group suites
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestGroup/<group_id>/Suites',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Test Suites

```python
# Get all test suites (with paging)
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestSuite/List?page=1&pageSize=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get test suite by ID
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestSuite/<suite_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get test lines for a suite
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestSuite/<suite_id>/TestLines',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get suite configuration
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestSuite/<suite_id>/Configuration',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Test Lines

```python
# Get test line by ID
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestLine/<line_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get test line steps
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestLine/<line_id>/Steps',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get test line actions
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestLine/<line_id>/Actions',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Test Steps

```python
# Get test step by ID
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestStep/<step_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all test steps (with paging)
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/TestStep/List?page=1&pageSize=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Actions

```python
# Get action by ID
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/Action/<action_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all actions (with paging)
status, data = NgaAPIUtils.NgaGet(
    '/Planning/<nga_project>/api/Action/List?page=1&pageSize=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Service Version

```python
# Get Planning service version
status, data = NgaAPIUtils.NgaGet(
    '/Planning/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

---

## Parameters

| Parameter | Description |
|-----------|-------------|
| `<nga_project>` | NGA project name (e.g., `ptl_pcd_validation`) |
| `<group_id>` | UUID of the test group |
| `<suite_id>` | UUID of the test suite |
| `<line_id>` | UUID of the test line |
| `<step_id>` | UUID of the test step |
| `<action_id>` | UUID of the action |

---

## Related Skills

- `nga/testrun` - Test run execution
- `nga/search` - OData search for planning entities
- `nga/suitereruns` - Suite rerun scheduling
