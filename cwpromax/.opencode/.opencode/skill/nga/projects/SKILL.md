---
name: nga/projects
description: NGA Projects Service for project management, authorization, queries, and collateral
---

# NGA Projects Service

Manages project information, authorization, queries, and collateral.

## Quick Start

```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get all projects
status, data = NgaAPIUtils.NgaGet(
    '/Projects/api/Project/List',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
print(json.dumps(data, indent=2))
```

---

## API Endpoints

### Projects

```python
# Get project by name
status, data = NgaAPIUtils.NgaGet(
    '/Projects/api/Project/<project_name>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all projects
status, data = NgaAPIUtils.NgaGet(
    '/Projects/api/Project/List',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get project stage type
status, data = NgaAPIUtils.NgaGet(
    '/Projects/api/Project/<project_name>/ProjectStageType',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get project settings
status, data = NgaAPIUtils.NgaGet(
    '/Projects/api/Project/<project_name>/Settings',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Authorization

```python
# Get project authorization data
status, data = NgaAPIUtils.NgaGet(
    '/Projects/api/Project/<project_name>/AuthorizationData',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all project authorizations
status, data = NgaAPIUtils.NgaGet(
    '/Projects/api/Project/Authorization/List',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get my authorization for project
status, data = NgaAPIUtils.NgaGet(
    '/Projects/api/Project/<project_name>/MyAuthorization',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Queries

```python
# Get all public and my private queries
status, data = NgaAPIUtils.NgaGet(
    '/Projects/<nga_project>/api/Query/AllPublicAndMyPrivate/<view>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get specific query by ID
status, data = NgaAPIUtils.NgaGet(
    '/Projects/<nga_project>/api/Query/<query_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get query results
status, data = NgaAPIUtils.NgaGet(
    '/Projects/<nga_project>/api/Query/<query_id>/Results',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Collateral

```python
# Get all collaterals
status, data = NgaAPIUtils.NgaGet(
    '/Projects/<nga_project>/api/Collateral/List',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get collateral by name
status, data = NgaAPIUtils.NgaGet(
    '/Projects/<nga_project>/api/Collateral/<collateral_name>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get collateral by ID
status, data = NgaAPIUtils.NgaGet(
    '/Projects/<nga_project>/api/Collateral/GetById/<collateral_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Validation Logs & Tokens

```python
# Get validation log by geo
status, data = NgaAPIUtils.NgaGet(
    '/Projects/api/ValidationLogLookup/<geo>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get HSD ES token
status, data = NgaAPIUtils.NgaGet(
    '/Projects/api/HsdEsToken/GetToken',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Service Version

```python
# Get Projects service version
status, data = NgaAPIUtils.NgaGet(
    '/Projects/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

---

## Parameters

| Parameter | Description |
|-----------|-------------|
| `<nga_project>` | NGA project name (e.g., `ptl_pcd_validation`) |
| `<project_name>` | Project name |
| `<query_id>` | UUID of the query |
| `<collateral_name>` | Name of the collateral |
| `<collateral_id>` | UUID of the collateral |
| `<view>` | View name for queries |
| `<geo>` | Geographic location code |

---

## Related Skills

- `nga/planning` - Test planning
- `nga/stationautomation` - Station management
