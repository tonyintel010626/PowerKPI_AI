# tools

Implementations of all tools that agents can call.
Tools are shared across all users and agents.

## Examples for PowerKPI
- `pbi_api.py`       — Power BI REST API wrapper
- `dax_executor.py`  — DAX query runner
- `sql_query.py`     — SQL data source connector
- `file_reader.py`   — Read CSV, Excel, JSON inputs

## Tool Contract
Each tool should expose:
- `name` — unique identifier
- `description` — what the tool does (used by agent for selection)
- `input_schema` — expected parameters
- `run(input)` — execution function
