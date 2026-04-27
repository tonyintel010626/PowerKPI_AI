---
name: nga/virtualstationfactoryservice
description: NGA Virtual Station Factory Service for managing virtual stations and project settings
---

# NGA Virtual Station Factory Service

Manages virtual stations and project settings.

## Quick Start

```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get all NFS paths
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/api/Nfs/GetAll',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
print(json.dumps(data, indent=2))
```

---

## API Endpoints

### NFS Paths

```python
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

# Get NFS path by ID
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/api/Nfs/<nfs_id>',
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

# Get project settings by key
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/<nga_project>/api/ProjectSettings/<key>',
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

# Get all suite overrides
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/<nga_project>/api/SuiteOverrides/GetAll',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get suite overrides by suite ID
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/<nga_project>/api/SuiteOverrides/GetBySuiteId/<suite_id>',
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

# Get all target system configs
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/api/TargetSystemConfig/GetAll',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get target system config by ID
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/api/TargetSystemConfig/<config_id>',
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

# Get token by ID
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/api/Token/<token_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Virtual Stations

```python
# Get virtual station by ID
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/<nga_project>/api/VirtualStation/<vs_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all virtual stations
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/<nga_project>/api/VirtualStation/GetAll',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Service Version

```python
# Get VirtualStationFactoryService version
status, data = NgaAPIUtils.NgaGet(
    '/VirtualStationFactoryService/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

---

## Parameters

| Parameter | Description |
|-----------|-------------|
| `<nga_project>` | NGA project name (e.g., `ptl_pcd_validation`) |
| `<path>` | Base NFS path |
| `<nfs_id>` | UUID of the NFS path |
| `<key>` | Project settings key |
| `<override_id>` | UUID of the suite override |
| `<suite_id>` | UUID of the test suite |
| `<set_name>` | Target system config set name |
| `<config_id>` | UUID of the target system config |
| `<project_name>` | Project name for token |
| `<token_id>` | UUID of the token |
| `<vs_id>` | UUID of the virtual station |

---

## Related Skills

- `nga/stationautomation` - Station management
- `nga/projects` - Project management
