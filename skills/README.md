# PowerKPI AI Skills — System Overview

This directory contains all **SKILL** definitions for the PowerKPI AI agent. Skills are structured, reusable capability definitions that describe what the agent can do, when it activates, and how it processes data.

---

## What Is a Skill?

A **Skill** is a self-contained unit of AI agent capability. It defines:

| Field | Description |
|-------|-------------|
| **Skill ID** | Unique identifier (e.g., `PKPI-SKL-001`) |
| **Name** | Human-readable skill name |
| **Category** | Type of skill (Data, Analysis, Reporting, Debug, etc.) |
| **Purpose** | What the skill accomplishes |
| **Trigger** | Conditions or events that activate the skill |
| **Inputs** | Data or parameters the skill requires |
| **Outputs** | Results the skill produces |
| **Steps** | Ordered reasoning or action steps |
| **Integration** | PowerKPI components this skill interacts with |

---

## Skill Index

### General Skills (`general_skills.md`)

| Skill ID | Name | Category |
|----------|------|----------|
| PKPI-SKL-001 | KPI Data Retrieval | Data |
| PKPI-SKL-002 | KPI Threshold Evaluation | Analysis |
| PKPI-SKL-003 | Anomaly Detection | Analysis |
| PKPI-SKL-004 | Log Analysis | Debug |
| PKPI-SKL-005 | Performance Profiling | Performance |
| PKPI-SKL-006 | Report Generation | Reporting |
| PKPI-SKL-007 | Alert & Notification | Alerting |
| PKPI-SKL-008 | Root Cause Analysis | Debug |
| PKPI-SKL-009 | Dashboard Interaction | UI |
| PKPI-SKL-010 | Data Pipeline Validation | Validation |

---

## Directory Layout

```
skills/
├── README.md               ← This file — skills system overview & index
├── general_skills.md       ← General PowerKPI workload skills (main branch)
├── skills_template.md      ← Blank template for new skill definitions
└── custom/
    └── debug_skills.md     ← Example branch-specific debug skill customizations
```

---

## How to Reference a Skill from Another Branch

When a feature/debug branch needs to use a general skill, reference it with the `main::` prefix:

```markdown
## Imports
- `main::PKPI-SKL-001`   # KPI Data Retrieval
- `main::PKPI-SKL-004`   # Log Analysis
- `main::PKPI-SKL-008`   # Root Cause Analysis
```

The agent resolves `main::` references at runtime by loading the skill definition from the `main` branch of this repository.

---

## Adding a New General Skill

1. Open `general_skills.md`
2. Copy the skill block template from `skills_template.md`
3. Assign the next available Skill ID
4. Fill in all required fields
5. Add the skill to the index table above
6. Commit to `main` via a Pull Request

## Adding a Branch-Specific Skill

1. Create (or open) your custom skills file in `skills/custom/`
2. Add an `## Imports` section listing any general skills you need
3. Define your customized/extended skills below
4. Keep branch-specific skills in their own branch — do **not** merge them into `main` unless they are general-purpose
