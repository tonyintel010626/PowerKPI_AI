---
name: nga/stationautomation
description: NGA Station Automation Service for managing stations, pools, recipes, activities, and configurations
---

# NGA Station Automation Service

Manages stations, pools, recipes, activities, and configurations.

## Quick Start

```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get all stations
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Station/List',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
print(json.dumps(data, indent=2))
```

---

## API Endpoints

### Stations

```python
# Get station list
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Station/List',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get station by ID
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Station/<station_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get station status
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Station/<station_id>/Status',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get station by name
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Station/GetByName/<station_name>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Pools

```python
# Get all pools
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Pool/List',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get pool by ID
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Pool/<pool_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get pool stations
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Pool/<pool_id>/Stations',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Recipes

```python
# Get all recipes
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Recipe/List',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get recipe by ID
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Recipe/<recipe_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get recipe by name
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Recipe/GetByName/<recipe_name>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Activities

```python
# Get all activities
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Activity/List',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get activity by ID
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Activity/<activity_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get activities by station
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Activity/GetByStation/<station_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Configurations

```python
# Get all configs
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Config/List',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get config by ID
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Config/<config_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get config by name
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Config/GetByName/<config_name>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Service Version

```python
# Get StationAutomation service version
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

---

## Parameters

| Parameter | Description |
|-----------|-------------|
| `<nga_project>` | NGA project name (e.g., `ptl_pcd_validation`) |
| `<station_id>` | UUID of the station |
| `<station_name>` | Name of the station |
| `<pool_id>` | UUID of the pool |
| `<recipe_id>` | UUID of the recipe |
| `<recipe_name>` | Name of the recipe |
| `<activity_id>` | UUID of the activity |
| `<config_id>` | UUID of the configuration |
| `<config_name>` | Name of the configuration |

---

## Related Skills

- `nga/virtualstationfactoryservice` - Virtual station management
- `nga/projects` - Project management
- `nga/search` - OData search for station data
