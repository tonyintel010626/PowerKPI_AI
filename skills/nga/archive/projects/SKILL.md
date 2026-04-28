---
name: projects
description: NGA Projects Service for project management, authorization, queries, and collateral
license: MIT
---

# NGA Projects Service Skill

This skill provides access to the NGA Projects Service API for managing projects, authorization, queries, and collateral.

## Key Capabilities

The Projects Service manages project-level operations:
- **Projects** - View project information and settings
- **Authorization** - Check project authorization and permissions
- **Queries** - Access saved queries (public and private)
- **Collateral** - View project collateral and documentation
- **Validation Logs** - Look up validation log configurations

## Common GET Endpoints

### Projects
```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

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
```

### Queries
```python
# Get all public and my private queries
status, data = NgaAPIUtils.NgaGet(
    '/Projects/<nga_project>/api/Query/AllPublicAndMyPrivate/<view>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all query paths for a view
status, data = NgaAPIUtils.NgaGet(
    '/Projects/<nga_project>/api/Query/AllPaths/<view>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get specific query by ID
status, data = NgaAPIUtils.NgaGet(
    '/Projects/<nga_project>/api/Query/<query_id>',
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
```

### Validation Logs
```python
# Get validation log by geo
status, data = NgaAPIUtils.NgaGet(
    '/Projects/api/ValidationLogLookup/<geo>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get validation log lookup table
status, data = NgaAPIUtils.NgaGet(
    '/Projects/api/ValidationLogLookup/List',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Tokens
```python
# Get HSD ES token
status, data = NgaAPIUtils.NgaGet(
    '/Projects/api/HsdEsToken/GetToken',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

See `swagger.json` for complete API specification.
