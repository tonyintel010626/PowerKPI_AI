---
name: nga/search
description: NGA Search Service - OData search across all NGA entities with powerful query capabilities
---

# NGA Search Service (OData)

Powerful OData search across all NGA entities with advanced query capabilities.

## Quick Start

```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Search test lines
status, data = NgaAPIUtils.NgaGet(
    '/Search/<nga_project>/odata/v1/TestLine?$top=10',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
print(json.dumps(data, indent=2))
```

---

## OData Query Parameters

| Parameter | Description | Limits |
|-----------|-------------|--------|
| `$select` | Limit properties returned | - |
| `$expand` | Include related entities | Max depth 4 |
| `$filter` | Filter results | Max 1000 expressions |
| `$orderby` | Sort results | Max 5 expressions |
| `$top` | Limit number of results | - |
| `$skip` | Skip results for pagination | - |
| `$count` | Get total count | - |

---

## API Endpoints

### Test Run Results

```python
# Search test run results with filter
status, data = NgaAPIUtils.NgaGet(
    '/Search/<nga_project>/odata/v1/TestRunResult?$filter=TestLineId eq <line_id>&$top=10',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get test run results with related data
status, data = NgaAPIUtils.NgaGet(
    '/Search/<nga_project>/odata/v1/TestRunResult?$expand=TestLine&$top=10',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get count of test run results
status, data = NgaAPIUtils.NgaGet(
    '/Search/<nga_project>/odata/v1/TestRunResult?$count=true&$top=0',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Test Lines

```python
# Search test lines by name
status, data = NgaAPIUtils.NgaGet(
    "/Search/<nga_project>/odata/v1/TestLine?$filter=contains(Name,'test')&$orderby=Name",
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Select specific properties
status, data = NgaAPIUtils.NgaGet(
    '/Search/<nga_project>/odata/v1/TestLine?$select=Id,Name,GoStatus&$top=20',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Filter by GoStatus
status, data = NgaAPIUtils.NgaGet(
    "/Search/<nga_project>/odata/v1/TestLine?$filter=GoStatus eq 'Go'",
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Test Suites

```python
# Search test suites
status, data = NgaAPIUtils.NgaGet(
    "/Search/<nga_project>/odata/v1/TestSuite?$filter=GoStatus eq 'Go'&$orderby=Name",
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get suite with test lines expanded
status, data = NgaAPIUtils.NgaGet(
    '/Search/<nga_project>/odata/v1/TestSuite?$expand=TestLines&$top=5',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Test Groups

```python
# Search test groups
status, data = NgaAPIUtils.NgaGet(
    '/Search/<nga_project>/odata/v1/TestGroup?$top=50&$skip=0',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Filter test groups by name
status, data = NgaAPIUtils.NgaGet(
    "/Search/<nga_project>/odata/v1/TestGroup?$filter=contains(Name,'validation')",
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Failures

```python
# Search failures with filter
status, data = NgaAPIUtils.NgaGet(
    '/Search/<nga_project>/odata/v1/Failure?$filter=BucketId eq <bucket_id>&$top=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get recent failures
status, data = NgaAPIUtils.NgaGet(
    '/Search/<nga_project>/odata/v1/Failure?$orderby=CreatedDate desc&$top=50',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Stations

```python
# Search active stations
status, data = NgaAPIUtils.NgaGet(
    '/Search/<nga_project>/odata/v1/Station?$filter=Active eq true',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get station details
status, data = NgaAPIUtils.NgaGet(
    '/Search/<nga_project>/odata/v1/Station?$select=Id,Name,Status&$orderby=Name',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Pools

```python
# Search pools
status, data = NgaAPIUtils.NgaGet(
    '/Search/<nga_project>/odata/v1/Pool?$select=Id,Name&$orderby=Name',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

---

## Complex Query Examples

### Multiple Conditions

```python
# AND conditions
status, data = NgaAPIUtils.NgaGet(
    "/Search/<nga_project>/odata/v1/TestLine?$filter=GoStatus eq 'Go' and Priority gt 5",
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# OR conditions
status, data = NgaAPIUtils.NgaGet(
    "/Search/<nga_project>/odata/v1/TestLine?$filter=GoStatus eq 'Go' or GoStatus eq 'NoGo'",
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Pagination

```python
# First page
status, data = NgaAPIUtils.NgaGet(
    '/Search/<nga_project>/odata/v1/TestLine?$count=true&$top=25&$skip=0',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Second page
status, data = NgaAPIUtils.NgaGet(
    '/Search/<nga_project>/odata/v1/TestLine?$count=true&$top=25&$skip=25',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Nested Expansion

```python
# Expand multiple levels
status, data = NgaAPIUtils.NgaGet(
    '/Search/<nga_project>/odata/v1/TestSuite?$expand=TestLines($expand=Steps)&$top=5',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

---

## Available Entities

- `TestRunResult` - Test run execution results
- `TestLine` - Test line definitions
- `TestSuite` - Test suite definitions
- `TestGroup` - Test group definitions
- `TestStep` - Test step definitions
- `Failure` - Failure records
- `Station` - Station information
- `Pool` - Pool definitions
- `Bucket` - Failure buckets

---

## Parameters

| Parameter | Description |
|-----------|-------------|
| `<nga_project>` | NGA project name (e.g., `ptl_pcd_validation`) |

---

## Related Skills

- `nga/results` - Direct results API access
- `nga/failure` - Failure tracking API
- `nga/planning` - Planning entities API
