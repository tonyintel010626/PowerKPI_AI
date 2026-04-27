---
name: axonintegration
description: NGA Axon Integration Service for Axon analytics and validation log access
license: MIT
---

# NGA Axon Integration Service Skill

This skill provides access to the NGA Axon Integration Service API for Axon analytics, connectivity to Axon records, and validation log management.

## Key Capabilities

The Axon Integration Service manages Axon integration:
- **Validation Logs** - Access vallog file content and metadata
- **Axon Records** - Connect sightings/failures to Axon records
- **HSD Suggestions** - Get Axon HSD-ES article suggestions

## Common GET Endpoints

### Validation Logs
```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get vallog file content
status, data = NgaAPIUtils.NgaGet(
    '/AxonIntegration/<nga_project>/api/Vallog/GetFileContent/<axon_id>/<file_path>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Download single file from vallog
status, data = NgaAPIUtils.NgaGet(
    '/AxonIntegration/<nga_project>/api/Vallog/DownLoadSingle/<axon_id>/<file_path>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Download combined vallog files
status, data = NgaAPIUtils.NgaGet(
    '/AxonIntegration/<nga_project>/api/Vallog/DownLoadCombined/<axon_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Service Information
```python
# Get service version
status, data = NgaAPIUtils.NgaGet(
    '/AxonIntegration/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

See `swagger.json` for complete API specification.
