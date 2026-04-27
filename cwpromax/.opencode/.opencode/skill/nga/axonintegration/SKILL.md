---
name: nga/axonintegration
description: NGA Axon Integration Service for Axon analytics and validation log access
---

# NGA Axon Integration Service

Provides Axon analytics and validation log access.

## Quick Start

```python
from pysvtools.execution.Lib import NgaAPIUtils
import json

# Get vallog file content
status, data = NgaAPIUtils.NgaGet(
    '/AxonIntegration/<nga_project>/api/Vallog/GetFileContent/<axon_id>/<file_path>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
print(json.dumps(data, indent=2))
```

---

## API Endpoints

### Validation Logs

```python
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

# Get vallog file list
status, data = NgaAPIUtils.NgaGet(
    '/AxonIntegration/<nga_project>/api/Vallog/GetFileList/<axon_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get vallog metadata
status, data = NgaAPIUtils.NgaGet(
    '/AxonIntegration/<nga_project>/api/Vallog/GetMetadata/<axon_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Axon Records

```python
# Get Axon record by ID
status, data = NgaAPIUtils.NgaGet(
    '/AxonIntegration/<nga_project>/api/Axon/<axon_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get Axon records by test run ID
status, data = NgaAPIUtils.NgaGet(
    '/AxonIntegration/<nga_project>/api/Axon/GetByTestRunId/<test_run_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Search Axon records
status, data = NgaAPIUtils.NgaGet(
    '/AxonIntegration/<nga_project>/api/Axon/Search?query=<search_query>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Analytics

```python
# Get analytics data
status, data = NgaAPIUtils.NgaGet(
    '/AxonIntegration/<nga_project>/api/Analytics/<axon_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)

# Get analytics summary
status, data = NgaAPIUtils.NgaGet(
    '/AxonIntegration/<nga_project>/api/Analytics/Summary/<axon_id>',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

### Service Version

```python
# Get AxonIntegration service version
status, data = NgaAPIUtils.NgaGet(
    '/AxonIntegration/api/Info/Version',
    nga_env='https://nga-prod.laas.icloud.intel.com'
)
```

---

## Parameters

| Parameter | Description |
|-----------|-------------|
| `<nga_project>` | NGA project name (e.g., `ptl_pcd_validation`) |
| `<axon_id>` | Axon record identifier |
| `<file_path>` | Path to file within vallog |
| `<test_run_id>` | UUID of the test run |
| `<search_query>` | Search query string |

---

## Related Skills

- `nga/results` - Test execution results
- `nga/testrun` - Test run management

---

## Known Limitations

### Axon Web UI Authentication
The Axon web interface at `https://axon.intel.com/` can experience silent session timeouts during extended debug sessions. For programmatic access, **prefer the NGA API routes** documented above via `NgaAPIUtils.NgaGet()` — these are more reliable than browser-based navigation.

### Status Scope Analyzers
The Axon web UI provides **Status Scope** analyzers that are extremely valuable for debug:
- Navigate to: Axon record → Status Scope → Select analyzer
- Displays scandump register values with **anomaly scores** (statistical outliers vs. reference population)
- High anomaly scores (>5.0) indicate registers with unusual values worth investigating
- **Limitation**: Status Scope data may not be programmatically accessible via API endpoints documented here

### Register Coverage Gap in Scandumps
Standard Status Scope scandumps do **not capture all registers**. Notable gaps:
- **SPBC PvtCR registers** (e.g., `PCERR_SLV0`, `VWERR_SLV0`, `OOB_GCNT_SLV0`, `ESPI_OOB_CRD_DBG`) are NOT included
- These registers require **SBI reads via PythonSV** on the live platform
- For eSPI/sideband debug workflows, consider enhancing scandump recipes to include SPBC registers

### Recommendation
For automated debug workflows:
1. Use API endpoints (above) for vallog file access and Axon record queries
2. Use Axon web UI Status Scope for interactive register analysis with anomaly detection
3. Use PythonSV for SPBC/sideband register reads not captured in scandumps
