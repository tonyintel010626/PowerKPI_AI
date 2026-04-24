# Custom Debug Skills — Example Branch

> **Branch:** `feature/debug-skills-example`  
> **Purpose:** Demonstrates how a feature/debug branch can import general skills from `main` and extend them for a specific debug scenario.

---

## Imports

The following general skills are imported from the `main` branch:

```
main::PKPI-SKL-001   # KPI Data Retrieval
main::PKPI-SKL-004   # Log Analysis
main::PKPI-SKL-005   # Performance Profiling
main::PKPI-SKL-008   # Root Cause Analysis
```

These skills are available to all steps defined in this file without re-defining them. The steps below extend or specialize those general skills for debug-specific workflows.

---

## `PKPI-DBG-001` — Deep-Dive Log Correlation

| Field | Value |
|-------|-------|
| **Skill ID** | `PKPI-DBG-001` |
| **Name** | Deep-Dive Log Correlation |
| **Category** | Debug |
| **Version** | 1.0 |
| **Branch** | `feature/debug-skills-example` |
| **Extends** | `main::PKPI-SKL-004` (Log Analysis) |

### Purpose

Extends the general Log Analysis skill (`PKPI-SKL-004`) with cross-component correlation: it collects logs from **multiple** PowerKPI components simultaneously and cross-references error signatures across component boundaries to identify cascading failures.

### Trigger

- User suspects a failure is propagating across multiple components
- Root Cause Analysis (`PKPI-SKL-008`) returns multiple probable causes with similar confidence scores
- On-call engineer initiates a deep-dive debug session

### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `components` | list[string] | ✅ | List of PowerKPI components to analyze (extends single-component input of `PKPI-SKL-004`) |
| `time_range` | object | ✅ | `{ start: ISO8601, end: ISO8601 }` |
| `correlation_window_seconds` | number | ❌ | Time window (seconds) for cross-component event correlation (default: `30`) |
| `error_signature_filter` | string | ❌ | Regex pattern to focus on specific error signatures |

### Outputs

| Field | Type | Description |
|-------|------|-------------|
| `per_component_logs` | object | Log summaries keyed by component name (output of `PKPI-SKL-004` per component) |
| `correlated_events` | list[object] | Cross-component event chains: `{ trigger_component, downstream_components, event_chain, first_seen }` |
| `cascade_root` | object | The most likely originating component and error, with evidence |

### Steps

1. For each component in `components`, invoke the general `PKPI-SKL-004` Log Analysis skill in parallel
2. Collect all resulting log entries and index them by timestamp
3. Apply a sliding correlation window (`correlation_window_seconds`) to identify error events that appear in one component and then propagate to others within the window
4. Build cross-component event chains by following error signatures across component log streams
5. Identify the component and error type that appears first in the chain — this is the `cascade_root`
6. Return per-component log summaries, correlated event chains, and the cascade root

### Integration

- `main::PKPI-SKL-004` (Log Analysis) — invoked once per component
- Log Aggregation Service
- PowerKPI Component Registry

---

## `PKPI-DBG-002` — KPI Regression Comparison

| Field | Value |
|-------|-------|
| **Skill ID** | `PKPI-DBG-002` |
| **Name** | KPI Regression Comparison |
| **Category** | Debug |
| **Version** | 1.0 |
| **Branch** | `feature/debug-skills-example` |
| **Extends** | `main::PKPI-SKL-001` (KPI Data Retrieval), `main::PKPI-SKL-003` (Anomaly Detection) |

### Purpose

Compares KPI metric values between a **baseline period** (known-good state) and an **incident period** to quantify regression and identify which KPIs degraded, by how much, and when the regression began.

### Trigger

- User asks "how much worse is this metric compared to last week?"
- Post-deployment health check detects KPI degradation
- Debug session needs to quantify the impact of a specific change

### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workload_id` | string | ✅ | Target workload |
| `kpi_ids` | list[string] | ✅ | KPIs to compare |
| `baseline_range` | object | ✅ | `{ start: ISO8601, end: ISO8601 }` — known-good period |
| `incident_range` | object | ✅ | `{ start: ISO8601, end: ISO8601 }` — period under investigation |
| `regression_threshold_pct` | number | ❌ | Minimum % change to flag as a regression (default: `10`) |

### Outputs

| Field | Type | Description |
|-------|------|-------------|
| `regression_report` | list[object] | Per-KPI regression: `{ kpi_id, baseline_avg, incident_avg, change_pct, regressed, first_degraded_at }` |
| `most_degraded` | object | The KPI with the largest regression and its details |
| `regression_start_time` | string | Estimated ISO8601 timestamp when degradation began |

### Steps

1. Invoke `main::PKPI-SKL-001` twice — once for `baseline_range` and once for `incident_range` — for all requested KPIs
2. Compute baseline and incident aggregate statistics (mean, p50, p95) for each KPI
3. Calculate the percentage change between baseline and incident statistics
4. Flag KPIs where `change_pct` exceeds `regression_threshold_pct` as regressed
5. Invoke `main::PKPI-SKL-003` on the incident-period data to identify the earliest anomaly timestamp — this becomes the `regression_start_time`
6. Rank KPIs by severity of regression and identify the most degraded
7. Return the full regression report, the most degraded KPI, and the estimated regression start time

### Integration

- `main::PKPI-SKL-001` (KPI Data Retrieval)
- `main::PKPI-SKL-003` (Anomaly Detection)

---

## `PKPI-DBG-003` — Interactive Debug Session Orchestrator

| Field | Value |
|-------|-------|
| **Skill ID** | `PKPI-DBG-003` |
| **Name** | Interactive Debug Session Orchestrator |
| **Category** | Debug |
| **Version** | 1.0 |
| **Branch** | `feature/debug-skills-example` |
| **Extends** | `main::PKPI-SKL-008` (Root Cause Analysis) |

### Purpose

Orchestrates an interactive, multi-turn debug session that guides the on-call engineer through a structured investigation workflow. It builds on the general Root Cause Analysis skill (`PKPI-SKL-008`) and adds conversational checkpoints, evidence surfacing, and engineer-guided branching to handle ambiguous or complex incidents.

### Trigger

- On-call engineer opens a debug session with the agent
- Automated triage determines the incident requires human-in-the-loop investigation
- User explicitly invokes the debug orchestrator

### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `workload_id` | string | ✅ | Affected workload |
| `incident_id` | string | ✅ | Unique incident identifier for session tracking |
| `incident_time` | string | ✅ | ISO8601 timestamp of the incident |
| `initial_context` | string | ❌ | Optional engineer-provided context (symptoms, recent changes) |

### Outputs

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Unique debug session identifier |
| `investigation_log` | list[object] | Ordered list of investigation steps, findings, and engineer decisions |
| `final_diagnosis` | object | Agreed-upon root cause and confidence after engineer confirmation |
| `action_items` | list[string] | Remediation action items generated during the session |

### Steps

1. Initialize a new debug session and log the `incident_id`, `workload_id`, and `initial_context`
2. Invoke `main::PKPI-SKL-008` (Root Cause Analysis) with the provided incident details to generate initial hypotheses
3. Present the top 3 probable causes to the engineer with supporting evidence, and ask: *"Does any of these match what you're seeing?"*
4. If the engineer confirms a hypothesis → proceed to step 6
5. If the engineer rejects all hypotheses → invoke `PKPI-DBG-001` (Deep-Dive Log Correlation) and `PKPI-DBG-002` (KPI Regression Comparison) for additional signals, then loop back to step 3 with updated hypotheses
6. With the confirmed root cause, generate a list of remediation action items
7. Present action items to the engineer for review and confirmation
8. Log the final diagnosis, engineer decisions, and action items to the investigation log
9. Return the completed session log, final diagnosis, and action items

### Integration

- `main::PKPI-SKL-008` (Root Cause Analysis)
- `PKPI-DBG-001` (Deep-Dive Log Correlation)
- `PKPI-DBG-002` (KPI Regression Comparison)
- Incident Management System (for session tracking)
