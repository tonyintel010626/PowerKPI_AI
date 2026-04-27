---
name: nga/pvimintegration
description: NGA PVIM Integration Service for NGA-HSD mapping and PVIM test cycles
---

# NGA PVIM Integration Service

Manages NGA-HSD mapping and PVIM test cycles.

## Quick Start

```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get all NGA-HSD mappings
status, data = NgaAPIUtils.NgaGet(
    '/PvimIntegration/<nga_project>/api/NgaHsdMapping/GetAll',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
print(json.dumps(data, indent=2))
```

---

## API Endpoints

### NGA-HSD Mapping

```python
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

# Get mapping by NGA property
status, data = NgaAPIUtils.NgaGet(
    '/PvimIntegration/<nga_project>/api/NgaHsdMapping/GetByNgaProperty/<property_name>',
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

### PVIM Test Cycles

```python
# Get PVIM test cycle by ID
status, data = NgaAPIUtils.NgaGet(
    '/PvimIntegration/<nga_project>/api/PvimTestCycle/<cycle_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get all PVIM test cycles
status, data = NgaAPIUtils.NgaGet(
    '/PvimIntegration/<nga_project>/api/PvimTestCycle/GetAll',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get test cycles by suite ID
status, data = NgaAPIUtils.NgaGet(
    '/PvimIntegration/<nga_project>/api/PvimTestCycle/GetBySuiteId/<suite_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Service Version

```python
# Get PvimIntegration service version
status, data = NgaAPIUtils.NgaGet(
    '/PvimIntegration/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

---

## Parameters

| Parameter | Description |
|-----------|-------------|
| `<nga_project>` | NGA project name (e.g., `ptl_pcd_validation`) |
| `<mapping_id>` | UUID of the NGA-HSD mapping |
| `<tenant>` | HSD tenant name |
| `<subject>` | HSD subject name |
| `<property_name>` | NGA property name |
| `<test_line_id>` | UUID of the test line |
| `<operation_id>` | Operation ID |
| `<cycle>` | Test cycle name |
| `<cycle_id>` | UUID of the PVIM test cycle |
| `<suite_id>` | UUID of the test suite |

---

## Related Skills

- `nga/planning` - Test planning
- `nga/results` - Test results
