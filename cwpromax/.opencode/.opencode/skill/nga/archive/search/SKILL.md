---
name: search
description: NGA Search Service - OData search across all NGA entities with powerful query capabilities
license: MIT
---

# NGA Search Service Skill

This skill provides access to the NGA Search Service API using OData protocol for comprehensive searching across all NGA entities.

## Key Capabilities

The Search Service provides OData query capabilities across:
- **Actions** - Search plan actions
- **Activities** - Search station activities
- **Buckets** - Search failure buckets
- **Configs** - Search configurations
- **Failures** - Search failure records
- **Pools** - Search station pools
- **Test Groups** - Search test groups
- **Test Lines** - Search test lines
- **Test Suites** - Search test suites
- **Test Steps** - Search test steps
- **Test Run Results** - Search test execution results

## OData Query Parameters

The Search Service supports standard OData query options:
- `$select` - Limit properties returned
- `$expand` - Include related entities (max depth 4)
- `$filter` - Filter results (max 1000 expressions)
- `$orderby` - Sort results (max 5 expressions)
- `$top` - Limit number of results
- `$skip` - Skip results for pagination
- `$count` - Get total count

## Common GET Endpoints

### Test Run Results
```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Search test run results with filter
status, data = NgaAPIUtils.NgaGet(
    '/Search/ptl_pcd_validation/odata/v1/TestRunResult?$filter=TestLineId eq <line_id>&$top=10',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get test run results with related data
status, data = NgaAPIUtils.NgaGet(
    '/Search/ptl_pcd_validation/odata/v1/TestRunResult?$expand=TestLine&$top=10',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Test Lines
```python
# Search test lines by filter
status, data = NgaAPIUtils.NgaGet(
    '/Search/ptl_pcd_validation/odata/v1/TestLine?$filter=contains(Name,\'test\')&$orderby=Name',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Select specific properties
status, data = NgaAPIUtils.NgaGet(
    '/Search/ptl_pcd_validation/odata/v1/TestLine?$select=Id,Name,GoStatus&$top=20',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Test Suites
```python
# Search test suites
status, data = NgaAPIUtils.NgaGet(
    '/Search/ptl_pcd_validation/odata/v1/TestSuite?$filter=GoStatus eq \'Go\'&$orderby=Name',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Test Groups
```python
# Search test groups
status, data = NgaAPIUtils.NgaGet(
    '/Search/ptl_pcd_validation/odata/v1/TestGroup?$top=50&$skip=0',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Failures
```python
# Search failures with filter
status, data = NgaAPIUtils.NgaGet(
    '/Search/ptl_pcd_validation/odata/v1/Failure?$filter=BucketId eq <bucket_id>&$top=100',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Other Entities
```python
# Search stations
status, data = NgaAPIUtils.NgaGet(
    '/Search/ptl_pcd_validation/odata/v1/Station?$filter=Active eq true',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Search pools
status, data = NgaAPIUtils.NgaGet(
    '/Search/ptl_pcd_validation/odata/v1/Pool?$select=Id,Name&$orderby=Name',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Search configurations
status, data = NgaAPIUtils.NgaGet(
    '/Search/ptl_pcd_validation/odata/v1/Config?$top=20',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

## OData Query Examples

### Complex Filters
```python
# Multiple conditions
status, data = NgaAPIUtils.NgaGet(
    '/Search/ptl_pcd_validation/odata/v1/TestLine?$filter=GoStatus eq \'Go\' and Priority gt 5',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Contains search
status, data = NgaAPIUtils.NgaGet(
    '/Search/ptl_pcd_validation/odata/v1/TestSuite?$filter=contains(Name,\'validation\')',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Pagination with Count
```python
# Get total count with results
status, data = NgaAPIUtils.NgaGet(
    '/Search/ptl_pcd_validation/odata/v1/TestLine?$count=true&$top=25&$skip=0',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

See `swagger.json` for complete API specification and available entities.
