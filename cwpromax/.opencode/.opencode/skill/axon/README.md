# Axon Skill

Intel Axon data lake SDK for retrieving and querying test execution records, failure analysis, and validation data.

## Installation

Install the required dependencies:

```bash
pip install --index-url https://intelpypi.intel.com/pythonsv/production pyaxon[kerberos]
```

## Usage

### Get Record by ID or URL

```bash
python get_record.py --record-id c425ebc4-aed6-4c6e-8eb1-a47726ffce47
```

Or use the full URL:

```bash
python get_record.py --record-id "https://axonsv.app.intel.com/apps/record-viewer/c425ebc4-aed6-4c6e-8eb1-a47726ffce47/intel-svtools-report-v1"
```

### Download Complete Record

Download all objects from a record:

```bash
python download_record.py --record-id c425ebc4-aed6-4c6e-8eb1-a47726ffce47 --output-dir ./axon_data
```

### Query Records

Search for records using MongoDB-style queries:

```bash
python query_records.py --query '{"metadata.platform": "MTL"}' --limit 10
```

## Authentication

The scripts use Kerberos authentication by default. Ensure you have valid Kerberos tickets on the Intel network.

## Documentation

See [SKILL.md](SKILL.md) for complete API documentation and examples.
