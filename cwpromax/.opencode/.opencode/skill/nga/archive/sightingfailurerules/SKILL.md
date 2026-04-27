---
name: sightingfailurerules
description: NGA Sighting Failure Rules Service for managing sighting rules and failure rule management
license: MIT
---

# NGA Sighting Failure Rules Service Skill

This skill provides access to the NGA Sighting Failure Rules Service API for managing sighting rules, rule activations, and sighting operations.

## Key Capabilities

The Sighting Failure Rules Service manages sighting and failure rules:
- **Sighting Rules** - View and query sighting rules
- **Rule Activations** - Access rule activation history
- **Sightings** - Retrieve sighting information

## Common GET Endpoints

### Sighting Rules
```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

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
```

### Sightings
```python
# Get sighting by ID
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/<nga_project>/api/Sightings/<sighting_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Sighting Puller
```python
# Get sighting puller status
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/api/SightingPuller',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Service Information
```python
# Get service version
status, data = NgaAPIUtils.NgaGet(
    '/SightingFailureRules/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

See `swagger.json` for complete API specification.
