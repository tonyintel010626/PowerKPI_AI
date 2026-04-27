---
name: virtualstationfactoryservice
description: NGA Virtual Station Factory Service for managing virtual stations and project settings
license: MIT
---

# NGA Virtual Station Factory Service Skill

This skill provides access to the NGA Virtual Station Factory Service API for managing virtual station factory operations, project settings, and NFS configurations.

## Key Capabilities

The Virtual Station Factory Service manages virtual stations:
- **Virtual Stations** - Manage virtual station factory operations
- **Project Settings** - View project-specific settings
- **NFS Paths** - Access NFS path configurations
- **Target System Configs** - Retrieve target system configurations

## Common GET Endpoints

### NFS Paths
```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get all NFS paths
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/api/Nfs/GetAll',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get NFS path by base path
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/api/Nfs?basePath=<path>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Project Settings
```python
# Get project settings
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/<nga_project>/api/ProjectSettings',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Suite Overrides
```python
# Get suite overrides by ID
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/<nga_project>/api/SuiteOverrides/<override_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Target System Configurations
```python
# Get target system configs
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/api/TargetSystemConfig?setName=<set_name>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Tokens
```python
# Get token by project name
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/api/Token?projectName=<project_name>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Service Information
```python
# Get service version
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

See `swagger.json` for complete API specification.
