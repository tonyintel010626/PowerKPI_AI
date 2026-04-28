---
name: suitereruns
description: NGA Suite Reruns Service for managing suite rerun scheduling (immediate, automatic, recurrent)
license: MIT
---

# NGA Suite Reruns Service Skill

This skill provides access to the NGA Suite Reruns Service API for managing suite rerun scheduling and instances.

## Key Capabilities

The Suite Reruns Service manages automated suite rerun scheduling:
- **Suite Reruns** - View suite rerun configurations
- **Rerun Schedules** - Access rerun schedule information
- **Rerun Instances** - Retrieve rerun instance details

## Common GET Endpoints

### Suite Reruns
```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get suite reruns by suite ID
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/SuiteReruns/<suite_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get suite rerun schedules
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/SuiteRerunSchedules/<suite_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Rerun Instances
```python
# Get suite rerun instance by ID
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/SuiteRerunInstance/<instance_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all instances for a suite
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/SuiteRerunInstances/<suite_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get instance names and IDs
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/SuiteRerunInstancesNameAndId/<suite_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get instances by request ID
status, data = NgaAPIUtils.NgaGet(
    '/SuiteReruns/<nga_project>/api/SuiteRerun/SuiteRerunInstancesByRequestId/<request_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

See `swagger.json` for complete API specification.
