# PowerKPI AI — General Workload Skills

This file defines all **general-purpose SKILLS** for the PowerKPI AI agent. These skills are available to every branch and can be imported and extended by branch-specific skill sets.

> **Maintained on:** `main` branch  
> **Import prefix:** `main::`  
> **Template:** See `skills_template.md`

---

## Table of Contents

1. [PKPI-SKL-001 — KPI Data Retrieval](#pkpi-skl-001--kpi-data-retrieval)
2. [PKPI-SKL-002 — KPI Threshold Evaluation](#pkpi-skl-002--kpi-threshold-evaluation)
3. [PKPI-SKL-003 — Anomaly Detection](#pkpi-skl-003--anomaly-detection)
4. [PKPI-SKL-004 — Log Analysis](#pkpi-skl-004--log-analysis)
5. [PKPI-SKL-005 — Performance Profiling](#pkpi-skl-005--performance-profiling)
6. [PKPI-SKL-006 — Report Generation](#pkpi-skl-006--report-generation)
7. [PKPI-SKL-007 — Alert & Notification](#pkpi-skl-007--alert--notification)
8. [PKPI-SKL-008 — Root Cause Analysis](#pkpi-skl-008--root-cause-analysis)
9. [PKPI-SKL-009 — Dashboard Interaction](#pkpi-skl-009--dashboard-interaction)
10. [PKPI-SKL-010 — Data Pipeline Validation](#pkpi-skl-010--data-pipeline-validation)

---

## PKPI-SKL-001 — KPI Data Retrieval

| Field | Value |
|-------|-------|
| **Skill ID** | `PKPI-SKL-001` |
| **Name** | KPI Data Retrieval |
| **Category** | Data |
| **Version** | 1.0 |

### Purpose
Retrieve current and historical KPI metric values from the PowerKPI data store for a given workload, time range, and set of KPI identifiers.

### Trigger
- User or agent requests KPI data for analysis
- Scheduled data refresh event fires
- Another skill (e.g., Anomaly Detection) requests raw values

### Inputs
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workload_id` | string | ✅ | Identifier of the target workload |
| `kpi_ids` | list[string] | ✅ | One or more KPI identifiers to retrieve |
| `time_range` | object | ✅ | `{ start: ISO8601, end: ISO8601 }` |
| `aggregation` | string | ❌ | `raw`, `hourly`, `daily` (default: `raw`) |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `kpi_data` | list[object] | Array of `{ kpi_id, timestamp, value, unit }` |
| `metadata` | object | Query metadata (rows returned, source, latency) |

### Steps
1. Validate that `workload_id` and `kpi_ids` exist in the PowerKPI registry
2. Construct the data query with the provided time range and aggregation level
3. Execute the query against the PowerKPI data store
4. Return the results along with query metadata

### Integration
- PowerKPI Data Store API
- KPI Registry Service

---

## PKPI-SKL-002 — KPI Threshold Evaluation

| Field | Value |
|-------|-------|
| **Skill ID** | `PKPI-SKL-002` |
| **Name** | KPI Threshold Evaluation |
| **Category** | Analysis |
| **Version** | 1.0 |

### Purpose
Compare current KPI values against defined thresholds (warning and critical) and determine the health status of each KPI.

### Trigger
- KPI data is retrieved (follows `PKPI-SKL-001`)
- User requests a health check on a workload
- Scheduled evaluation job runs

### Inputs
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `kpi_data` | list[object] | ✅ | Output from `PKPI-SKL-001` |
| `threshold_config` | object | ✅ | Per-KPI threshold definitions |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `evaluation_results` | list[object] | `{ kpi_id, value, status: healthy/warning/critical, threshold_breached }` |
| `summary` | object | Overall workload health summary |

### Steps
1. Load the threshold configuration for the target workload
2. For each KPI data point, compare the value against warning and critical thresholds
3. Assign a status (`healthy`, `warning`, `critical`) to each KPI
4. Aggregate individual statuses into an overall workload health summary
5. Return evaluation results and summary

### Integration
- Threshold Configuration Service
- KPI Registry Service

---

## PKPI-SKL-003 — Anomaly Detection

| Field | Value |
|-------|-------|
| **Skill ID** | `PKPI-SKL-003` |
| **Name** | Anomaly Detection |
| **Category** | Analysis |
| **Version** | 1.0 |

### Purpose
Identify statistical anomalies (spikes, drops, trend deviations) in KPI time-series data using configurable detection algorithms.

### Trigger
- User requests anomaly analysis on a KPI
- KPI threshold evaluation returns a `warning` or `critical` status
- Scheduled anomaly scan runs

### Inputs
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `kpi_data` | list[object] | ✅ | Time-series KPI data |
| `algorithm` | string | ❌ | Detection algorithm: `zscore`, `iqr`, `ewma` (default: `zscore`) |
| `sensitivity` | number | ❌ | Detection sensitivity 0.0–1.0 (default: 0.8) |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `anomalies` | list[object] | `{ kpi_id, timestamp, value, anomaly_type, severity, score }` |
| `baseline` | object | Computed baseline statistics used for detection |

### Steps
1. Retrieve or compute baseline statistics (mean, stddev, percentiles) for the KPI
2. Apply the chosen detection algorithm to identify data points that deviate from the baseline
3. Score and classify each anomaly by type (`spike`, `drop`, `trend_shift`) and severity
4. Return the list of anomalies along with the computed baseline

### Integration
- PowerKPI Data Store API (for baseline computation)
- Anomaly Detection Engine

---

## PKPI-SKL-004 — Log Analysis

| Field | Value |
|-------|-------|
| **Skill ID** | `PKPI-SKL-004` |
| **Name** | Log Analysis |
| **Category** | Debug |
| **Version** | 1.0 |

### Purpose
Parse, filter, and summarize diagnostic logs from PowerKPI components to surface errors, warnings, and relevant events related to a workload.

### Trigger
- User asks to investigate a workload issue
- Root Cause Analysis skill (`PKPI-SKL-008`) requests log data
- KPI metric anomaly is detected

### Inputs
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `component` | string | ✅ | PowerKPI component name (e.g., `data-ingestion`, `scheduler`) |
| `time_range` | object | ✅ | `{ start: ISO8601, end: ISO8601 }` |
| `log_levels` | list[string] | ❌ | Filter by level: `ERROR`, `WARN`, `INFO` (default: all) |
| `keyword_filter` | string | ❌ | Optional keyword or regex filter |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `log_entries` | list[object] | Filtered log entries with timestamp, level, message, and source |
| `summary` | object | `{ total_entries, error_count, warn_count, top_errors }` |

### Steps
1. Connect to the PowerKPI log aggregation service for the specified component and time range
2. Apply level and keyword filters
3. Parse log entries into structured records
4. Identify and group repeated errors or warnings
5. Return filtered entries and a summary of key findings

### Integration
- Log Aggregation Service (e.g., Application Insights, Elasticsearch)
- PowerKPI Component Registry

---

## PKPI-SKL-005 — Performance Profiling

| Field | Value |
|-------|-------|
| **Skill ID** | `PKPI-SKL-005` |
| **Name** | Performance Profiling |
| **Category** | Performance |
| **Version** | 1.0 |

### Purpose
Collect and analyze performance metrics (CPU, memory, latency, throughput) for a PowerKPI workload or component to identify bottlenecks.

### Trigger
- User requests a performance review of a workload
- KPI data shows unexpected latency or throughput degradation
- Scheduled performance baseline collection runs

### Inputs
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workload_id` | string | ✅ | Target workload identifier |
| `metrics` | list[string] | ❌ | Metrics to collect: `cpu`, `memory`, `latency`, `throughput` (default: all) |
| `time_range` | object | ✅ | `{ start: ISO8601, end: ISO8601 }` |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `performance_data` | list[object] | Per-metric time-series data |
| `bottlenecks` | list[object] | Identified bottlenecks with severity and affected component |
| `recommendations` | list[string] | Actionable improvement suggestions |

### Steps
1. Collect the requested performance metrics for the workload over the given time range
2. Compare metrics against established baselines
3. Identify components or time windows with elevated resource usage or degraded throughput
4. Generate recommendations based on observed patterns
5. Return performance data, identified bottlenecks, and recommendations

### Integration
- PowerKPI Metrics Service
- Infrastructure Monitoring Platform

---

## PKPI-SKL-006 — Report Generation

| Field | Value |
|-------|-------|
| **Skill ID** | `PKPI-SKL-006` |
| **Name** | Report Generation |
| **Category** | Reporting |
| **Version** | 1.0 |

### Purpose
Compile KPI evaluation results, anomaly findings, and performance data into a structured report consumable by stakeholders.

### Trigger
- User requests a summary or report for a workload
- Scheduled reporting job runs (daily, weekly)
- Post-incident analysis is requested

### Inputs
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workload_id` | string | ✅ | Target workload identifier |
| `time_range` | object | ✅ | Reporting period |
| `include_sections` | list[string] | ❌ | `kpi_summary`, `anomalies`, `performance`, `recommendations` (default: all) |
| `format` | string | ❌ | Output format: `markdown`, `json`, `html` (default: `markdown`) |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `report` | string | Formatted report content |
| `report_metadata` | object | `{ generated_at, workload_id, period, format }` |

### Steps
1. Gather data from relevant skills: KPI retrieval, threshold evaluation, anomaly detection, performance profiling
2. Organize findings into the requested report sections
3. Format the report in the requested output format
4. Return the completed report and metadata

### Integration
- All data-producing skills (`PKPI-SKL-001` through `PKPI-SKL-005`)
- Report Storage / Distribution Service

---

## PKPI-SKL-007 — Alert & Notification

| Field | Value |
|-------|-------|
| **Skill ID** | `PKPI-SKL-007` |
| **Name** | Alert & Notification |
| **Category** | Alerting |
| **Version** | 1.0 |

### Purpose
Send notifications to configured channels (email, Teams, Slack, PagerDuty) when KPI thresholds are breached or anomalies are detected.

### Trigger
- KPI evaluation returns `warning` or `critical` status
- Anomaly detection identifies a high-severity anomaly
- User manually requests a notification

### Inputs
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `alert_type` | string | ✅ | `threshold_breach`, `anomaly`, `manual` |
| `severity` | string | ✅ | `warning`, `critical` |
| `workload_id` | string | ✅ | Affected workload |
| `details` | object | ✅ | Alert details (kpi_id, value, threshold, etc.) |
| `channels` | list[string] | ❌ | Override default notification channels |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `notification_results` | list[object] | Per-channel delivery status and message ID |

### Steps
1. Determine the appropriate notification channels based on severity and workload configuration
2. Format the alert message for each channel
3. Deliver the notification to each channel
4. Record delivery status and message IDs for audit purposes

### Integration
- Notification Gateway (email, Teams, Slack, PagerDuty)
- Alert Configuration Service

---

## PKPI-SKL-008 — Root Cause Analysis

| Field | Value |
|-------|-------|
| **Skill ID** | `PKPI-SKL-008` |
| **Name** | Root Cause Analysis |
| **Category** | Debug |
| **Version** | 1.0 |

### Purpose
Correlate KPI anomalies, log errors, and performance degradation signals to identify the probable root cause of a workload issue.

### Trigger
- User asks "why is this KPI degraded?" or similar question
- Critical anomaly detected in `PKPI-SKL-003`
- Post-incident investigation is initiated

### Inputs
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workload_id` | string | ✅ | Affected workload |
| `incident_time` | string | ✅ | ISO8601 timestamp at or near the incident |
| `kpi_ids` | list[string] | ❌ | KPIs involved in the incident |
| `lookback_minutes` | number | ❌ | How far back to analyze (default: 60) |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `probable_causes` | list[object] | Ranked list of `{ cause, confidence, evidence }` |
| `timeline` | list[object] | Chronological event timeline leading to the incident |
| `recommended_actions` | list[string] | Suggested remediation steps |

### Steps
1. Invoke `PKPI-SKL-001` to retrieve KPI data for the incident window
2. Invoke `PKPI-SKL-004` to collect and parse logs from relevant components
3. Invoke `PKPI-SKL-005` to gather performance metrics for the incident window
4. Correlate signals across KPI data, logs, and performance metrics
5. Build a chronological timeline of events
6. Rank probable causes by confidence based on corroborating evidence
7. Generate recommended remediation actions

### Integration
- `PKPI-SKL-001` (KPI Data Retrieval)
- `PKPI-SKL-004` (Log Analysis)
- `PKPI-SKL-005` (Performance Profiling)

---

## PKPI-SKL-009 — Dashboard Interaction

| Field | Value |
|-------|-------|
| **Skill ID** | `PKPI-SKL-009` |
| **Name** | Dashboard Interaction |
| **Category** | UI |
| **Version** | 1.0 |

### Purpose
Interact with the PowerKPI dashboard to navigate views, apply filters, export data, and surface relevant visualizations in response to user queries.

### Trigger
- User requests to view or explore a KPI dashboard
- Agent needs to capture a dashboard screenshot for a report
- User asks to change a time filter or drill down into a metric

### Inputs
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | string | ✅ | `navigate`, `filter`, `export`, `screenshot` |
| `dashboard_id` | string | ✅ | Target dashboard identifier |
| `parameters` | object | ❌ | Action-specific parameters (filter values, export format, etc.) |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `result` | object | Action outcome (screenshot path, exported data URL, applied filter confirmation) |
| `status` | string | `success`, `partial`, `failed` |

### Steps
1. Authenticate with the PowerKPI dashboard service
2. Navigate to the specified dashboard
3. Apply any provided filters or parameters
4. Execute the requested action (navigate, filter, export, or screenshot)
5. Return the result

### Integration
- PowerKPI Dashboard Service
- Authentication Service

---

## PKPI-SKL-010 — Data Pipeline Validation

| Field | Value |
|-------|-------|
| **Skill ID** | `PKPI-SKL-010` |
| **Name** | Data Pipeline Validation |
| **Category** | Validation |
| **Version** | 1.0 |

### Purpose
Validate the health and correctness of the data pipeline that feeds KPI metrics into PowerKPI, checking for data freshness, completeness, and schema conformance.

### Trigger
- User reports stale or missing KPI data
- Scheduled pipeline health check runs
- Data ingestion failure alert is received

### Inputs
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pipeline_id` | string | ✅ | Identifier of the data pipeline to validate |
| `validation_checks` | list[string] | ❌ | `freshness`, `completeness`, `schema` (default: all) |
| `expected_freshness_minutes` | number | ❌ | Maximum acceptable data age in minutes (default: 15) |

### Outputs
| Field | Type | Description |
|-------|------|-------------|
| `validation_results` | list[object] | Per-check results: `{ check, status, details }` |
| `overall_status` | string | `healthy`, `degraded`, `failed` |
| `remediation_hints` | list[string] | Suggestions for resolving detected issues |

### Steps
1. Connect to the pipeline monitoring service for the specified pipeline
2. Run each requested validation check:
   - **Freshness**: Compare the latest data timestamp against the expected freshness threshold
   - **Completeness**: Check for missing records or gaps in the expected data stream
   - **Schema**: Validate that incoming records conform to the expected schema
3. Aggregate individual check results into an overall pipeline status
4. Generate remediation hints for any failing checks
5. Return validation results, overall status, and remediation hints

### Integration
- Pipeline Monitoring Service
- Data Schema Registry
- PowerKPI Data Store API
