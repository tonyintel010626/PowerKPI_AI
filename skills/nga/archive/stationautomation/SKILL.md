---
name: stationautomation
description: NGA Station Automation Service for managing stations, pools, recipes, activities, and configurations
license: MIT
---

# NGA Station Automation Service Skill

This skill provides access to the NGA Station Automation Service API for managing station infrastructure, pools, recipes, activities, and configurations.

## Key Capabilities

The Station Automation Service manages test infrastructure:
- **Stations** - View station information and status
- **Pools** - Access station pool configurations
- **Recipes** - Retrieve station recipes
- **Activities** - Get station activities
- **Configurations** - View station configurations
- **Systems** - Access system information

## Common GET Endpoints

### Stations
```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get station list
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Station/List',
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
```

### Recipes
```python
# Get all recipes
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Recipe/List',
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
```

### Configurations
```python
# Get all configs
status, data = NgaAPIUtils.NgaGet(
    '/StationAutomation/<nga_project>/api/Config/List',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

See `swagger.json` for complete API specification.
