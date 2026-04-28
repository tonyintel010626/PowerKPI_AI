---
name: nga/sightingfailurerules
description: NGA Sighting Failure Rules Service for managing sighting rules and failure rule management
---

# NGA Sighting Failure Rules Service

Manages sighting rules and failure rule management.

## Quick Start

```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get all sighting rules
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/<nga_project>/api/SightingRule/GetAll?page=1&pageSize=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
print(json.dumps(data, indent=2))
```

---

## API Endpoints

### Sighting Rules

```python
# Get sighting rule by ID
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/<nga_project>/api/SightingRule/<rule_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all sighting rules (with paging)
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/<nga_project>/api/SightingRule/GetAll?page=1&pageSize=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get active sighting rules
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/<nga_project>/api/SightingRule/GetActive',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get sighting rules by sighting ID
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/<nga_project>/api/SightingRule/GetBySightingId/<sighting_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Rule Activations

```python
# Get latest rule activations
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/<nga_project>/api/RuleActivation/GetLatest',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all rule activations (with paging)
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/<nga_project>/api/RuleActivation/GetAll?page=1&pageSize=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get rule activation by ID
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/<nga_project>/api/RuleActivation/<activation_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get activations by rule ID
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/<nga_project>/api/RuleActivation/GetByRuleId/<rule_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Sightings

```python
# Get sighting by ID
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/<nga_project>/api/Sightings/<sighting_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get sighting puller status
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/api/SightingPuller',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get sightings by project
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/<nga_project>/api/Sightings/GetAll?page=1&pageSize=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Failure Rules

```python
# Get failure rule by ID
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/<nga_project>/api/FailureRule/<rule_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all failure rules
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/<nga_project>/api/FailureRule/GetAll?page=1&pageSize=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Service Version

```python
# Get SightingFailureRules service version
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

---

## Parameters

| Parameter | Description |
|-----------|-------------|
| `<nga_project>` | NGA project name (e.g., `ptl_pcd_validation`) |
| `<rule_id>` | UUID of the sighting rule |
| `<sighting_id>` | UUID of the sighting |
| `<activation_id>` | UUID of the rule activation |

---

## Related Skills

- `nga/failure` - Failure tracking
- `nga/search` - OData search for sighting data
