---
name: axon
description: Intel Axon data lake SDK for retrieving and querying test execution records, failure analysis, and validation data
license: Intel Proprietary
---

# Axon Skill

This skill provides access to Intel's Axon data lake through the pyaxon SDK. Axon stores test execution records, failure analysis data, and validation logs from various Intel testing frameworks.

## Quick Start

### Basic Record Retrieval

```python
from pyaxon import Axon

# Initialize Axon client (Kerberos auth is automatic)
axon = Axon(host="https://axonsv.app.intel.com")

# Get a record by ID (extracted from URL)
record_id = "c425ebc4-aed6-4c6e-8eb1-a47726ffce47"
record = axon.failure.get(record_id)

print(f"Record metadata: {record['metadata']}")
print(f"Content types: {list(record['content'].keys())}")

# Close connection
axon.close()
```

### Context Manager Usage

```python
with Axon(host="https://axonsv.app.intel.com") as axon:
    record = axon.failure.get("c425ebc4-aed6-4c6e-8eb1-a47726ffce47")
    print(record)
```

## Understanding Axon Records

### Record ID Extraction from URL

Axon URLs follow this pattern:
```
https://axonsv.app.intel.com/apps/record-viewer/{RECORD_ID}/{CONTENT_TYPE}?tab=...
```

Example:
- URL: `https://axonsv.app.intel.com/apps/record-viewer/c425ebc4-aed6-4c6e-8eb1-a47726ffce47/intel-svtools-report-v1?tab=report`
- Record ID: `c425ebc4-aed6-4c6e-8eb1-a47726ffce47`
- Content Type: `intel-svtools-report-v1`

### Record Structure

A record contains:
- **metadata**: Top-level record information (created_at, updated_at, tags, etc.)
- **content**: Dictionary of content types (e.g., `intel-svtools-report-v1`, `logs`, `artifacts`)
- Each content type contains **objects** (individual data items)

## Failure Endpoint Operations

### Get Complete Record

```python
with Axon(host="https://axonsv.app.intel.com") as axon:
    record = axon.failure.get(failure_id="RECORD_ID_HERE")
    
    # Access metadata
    print(f"Created: {record['metadata']['created_at']}")
    print(f"Updated: {record['metadata']['updated_at']}")
    
    # Access content types
    for content_type in record['content']:
        print(f"Content type: {content_type}")
        objects = record['content'][content_type]['objects']
        print(f"  Objects: {len(objects)}")
```

### Get Record Metadata Only

```python
with Axon(host="https://axonsv.app.intel.com") as axon:
    metadata = axon.failure.metadata.get(failure_id="RECORD_ID_HERE")
    print(metadata)
```

### Update Record Metadata

```python
with Axon(host="https://axonsv.app.intel.com") as axon:
    updated = axon.failure.metadata.update(
        failure_id="RECORD_ID_HERE",
        metadata={"tags": ["analyzed", "debug"], "priority": "high"}
    )
```

### Get Content by Type

```python
with Axon(host="https://axonsv.app.intel.com") as axon:
    # Get specific content type
    content = axon.failure.content.get(
        failure_id="RECORD_ID_HERE",
        content_type="intel-svtools-report-v1"
    )
    
    # Access objects within the content
    for obj in content['objects']:
        print(f"Object ID: {obj['id']}")
        print(f"Object data: {obj['data']}")
```

### Get Specific Object from Content

```python
with Axon(host="https://axonsv.app.intel.com") as axon:
    obj = axon.failure.content.object.get(
        failure_id="RECORD_ID_HERE",
        content_type="intel-svtools-report-v1",
        object_id="OBJECT_ID_HERE"
    )
    print(obj)
```

### Stream Large Objects

For large objects, use streaming to avoid memory issues:

```python
with Axon(host="https://axonsv.app.intel.com") as axon:
    # Stream object in chunks
    stream = axon.failure.content.object.get(
        failure_id="RECORD_ID_HERE",
        content_type="logs",
        object_id="OBJECT_ID_HERE",
        stream=True,
        chunk_size=8192  # bytes per chunk
    )
    
    # Process chunks
    for chunk in stream:
        process_chunk(chunk)
```

### Create New Record

```python
with Axon(host="https://axonsv.app.intel.com") as axon:
    metadata = {
        "test_name": "Test123",
        "platform": "MTL",
        "tags": ["regression"]
    }
    
    object_map = {
        "intel-svtools-report-v1": [
            {"id": "report1", "data": {"status": "FAIL", "error": "Timeout"}}
        ]
    }
    
    record_id, results = axon.failure.create(
        metadata=metadata,
        object_map=object_map
    )
    print(f"Created record: {record_id}")
```

### Delete Record

```python
with Axon(host="https://axonsv.app.intel.com") as axon:
    axon.failure.delete(failure_id="RECORD_ID_HERE")
```

## Query Operations

### MongoDB Queries

Axon supports MongoDB-style queries for searching records:

```python
with Axon(host="https://axonsv.app.intel.com") as axon:
    # Query records by metadata
    query = {
        "metadata.tags": "regression",
        "metadata.platform": "MTL"
    }
    
    results = axon.query.mongodb.execute(
        database="failures",
        collection="records",
        query=query
    )
    
    for record in results:
        print(f"Record ID: {record['_id']}")
```

### Saved Queries

```python
with Axon(host="https://axonsv.app.intel.com") as axon:
    # List saved queries
    saved = axon.query.list_saved()
    
    # Execute saved query
    results = axon.query.execute_saved(query_name="my_saved_query")
    
    # Save a new query
    axon.query.save(
        name="platform_failures",
        query={"metadata.platform": "MTL"}
    )
```

### Snowflake Queries

For SQL-based analytics:

```python
with Axon(host="https://axonsv.app.intel.com") as axon:
    sql = "SELECT * FROM failures WHERE platform = 'MTL' LIMIT 10"
    results = axon.query.snowflake.execute(sql)
    
    for row in results:
        print(row)
```

## Common Use Cases

### Analyze Failure Record

```python
with Axon(host="https://axonsv.app.intel.com") as axon:
    record_id = "c425ebc4-aed6-4c6e-8eb1-a47726ffce47"
    record = axon.failure.get(record_id)
    
    # Extract key information
    metadata = record['metadata']
    content = record['content']
    
    # Check if intel-svtools-report is present
    if 'intel-svtools-report-v1' in content:
        report = content['intel-svtools-report-v1']
        print(f"Report objects: {len(report['objects'])}")
        
        for obj in report['objects']:
            print(f"Object: {obj['id']}")
            # Access object data
            if 'data' in obj:
                print(f"Data: {obj['data']}")
```

### Download All Objects from a Record

```python
import json
import os

with Axon(host="https://axonsv.app.intel.com") as axon:
    record_id = "c425ebc4-aed6-4c6e-8eb1-a47726ffce47"
    record = axon.failure.get(record_id)
    
    # Create output directory
    os.makedirs(f"axon_record_{record_id}", exist_ok=True)
    
    # Save metadata
    with open(f"axon_record_{record_id}/metadata.json", "w") as f:
        json.dump(record['metadata'], f, indent=2)
    
    # Save each content type
    for content_type, content_data in record['content'].items():
        content_dir = f"axon_record_{record_id}/{content_type}"
        os.makedirs(content_dir, exist_ok=True)
        
        for obj in content_data['objects']:
            obj_file = f"{content_dir}/{obj['id']}.json"
            with open(obj_file, "w") as f:
                json.dump(obj, f, indent=2)
```

### Search for Recent Failures

```python
from datetime import datetime, timedelta

with Axon(host="https://axonsv.app.intel.com") as axon:
    # Get failures from last 7 days
    week_ago = datetime.now() - timedelta(days=7)
    
    query = {
        "metadata.created_at": {"$gte": week_ago.isoformat()},
        "metadata.status": "FAIL"
    }
    
    results = axon.query.mongodb.execute(
        database="failures",
        collection="records",
        query=query
    )
    
    print(f"Found {len(results)} recent failures")
```

## Script Usage

### Get Record Script

Use the provided script to retrieve Axon records:

```bash
python <cwd>/.opencode/skill/axon/get_record.py --record-id c425ebc4-aed6-4c6e-8eb1-a47726ffce47
```

### Query Records Script

```bash
python <cwd>/.opencode/skill/axon/query_records.py --query '{"metadata.platform": "MTL"}'
```

### Download Record Script

```bash
python <cwd>/.opencode/skill/axon/download_record.py --record-id c425ebc4-aed6-4c6e-8eb1-a47726ffce47 --output-dir ./output
```

## Configuration

### Environment Variables

- `AXON_HOST`: Default Axon host URL (default: `https://axonsv.app.intel.com`)
- `AXON_TOKEN`: Optional API token (Kerberos auth is used by default)

### Authentication

The pyaxon SDK uses Kerberos authentication by default on Intel network. No additional configuration is required if you have valid Kerberos tickets.

For token-based authentication:

```python
axon = Axon(host="https://axonsv.app.intel.com", token="YOUR_TOKEN")
```

## Requirements

```
pyaxon[kerberos]
```

Install from Intel PyPI:
```bash
pip install --index-url https://intelpypi.intel.com/pythonsv/production pyaxon[kerberos]
```

## Error Handling

```python
from pyaxon import Axon, PyaxonError, ServerError, ClientError

try:
    with Axon(host="https://axonsv.app.intel.com") as axon:
        record = axon.failure.get("RECORD_ID")
except ClientError as e:
    print(f"Client error (4xx): {e}")
except ServerError as e:
    print(f"Server error (5xx): {e}")
except PyaxonError as e:
    print(f"General Axon error: {e}")
```

## Known Limitations

- Large objects should be streamed to avoid memory issues
- MongoDB queries are limited to the Axon query syntax (subset of MongoDB query language)
- Kerberos authentication requires valid Intel network access
- Record deletion is permanent and cannot be undone

## Related Skills

- `nga`: NGA test execution and results
- `hsdes`: HSDES sighting and bug tracking
- `securewiki`: Confluence wiki for documentation

## Additional Resources

- API Documentation: https://intelpypi.intel.com/pythonsv/production/pyaxon/latest/+doc/index.html
- Axon Portal: https://axonsv.app.intel.com
- GitHub Repository: https://github.com/intel-innersource/frameworks.analytics.axon.sdks.pyaxon
