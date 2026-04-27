---
name: pvimintegration
description: NGA PVIM Integration Service for NGA-HSD mapping and PVIM test cycles
license: MIT
---

# NGA PVIM Integration Service Skill

This skill provides access to the NGA PVIM Integration Service API for managing NGA-HSD mapping and PVIM test cycle integration.

## Key Capabilities

The PVIM Integration Service manages HSD/PVIM integration:
- **NGA-HSD Mapping** - View NGA to HSD property mappings
- **PVIM Links** - Access PVIM test cycle links
- **Test Cycles** - Retrieve PVIM test cycle information

## Common GET Endpoints

### NGA-HSD Mapping
```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get NGA-HSD mapping by ID
status, data = NgaAPIUtils.NgaGet(
    '/PvimIntegration/<nga_project>/api/NgaHsdMapping/<mapping_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all NGA-HSD mappings
status, data = NgaAPIUtils.NgaGet(
    '/PvimIntegration/<nga_project>/api/NgaHsdMapping/GetAll',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get NGA properties available for HSD mapping
status, data = NgaAPIUtils.NgaGet(
    '/PvimIntegration/<nga_project>/api/NgaHsdMapping/GetNgaPropertiesForHsdMapping',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get HSD properties schema
status, data = NgaAPIUtils.NgaGet(
    '/PvimIntegration/<nga_project>/api/NgaHsdMapping/GetHsdPropertiesSchema/<tenant>/<subject>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### PVIM Links
```python
# Get PVIM link by test line ID
status, data = NgaAPIUtils.NgaGet(
    '/PvimIntegration/<nga_project>/api/Pvim/<test_line_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get PVIM links by operation ID
status, data = NgaAPIUtils.NgaGet(
    '/PvimIntegration/<nga_project>/api/Pvim/GetByOperationId?operationId=<operation_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all test cycles
status, data = NgaAPIUtils.NgaGet(
    '/PvimIntegration/<nga_project>/api/Pvim',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get test line IDs by test cycles
status, data = NgaAPIUtils.NgaGet(
    '/PvimIntegration/<nga_project>/api/Pvim/TestLineIds?testCycle=<cycle>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

See `swagger.json` for complete API specification.
