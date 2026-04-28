---
name: self-improve
description: >
  Generic self-improvement framework for any skill tree — automated structural checks,
  content verification, coverage gap detection, and proposal-based improvement pipeline.
  Generalized from the battle-tested THC self-improvement framework.
disable: false
license: MIT
---

> **Owner**: Chin, William Willy (`willychi`)
> **Support**: For any issues, contact the owner above. Please collect the **complete session transcript** (AI log dump) before reporting — this enables faster root-cause analysis.

# Self-Improvement Framework Skill

## Purpose

This skill provides a **reusable, domain-agnostic self-improvement pipeline** for any skill tree in the OpenCode ecosystem. It automates:

1. **Structural checks** — verify file existence, frontmatter validity, cross-references, owner headers
2. **Content verification** — data-driven regex assertions against skill file content
3. **Coverage gap detection** — find important terms in skills not covered by any assertion
4. **Proposal generation** — convert findings into actionable improvement proposals
5. **Human-in-the-loop approval** — proposals require review before application

The framework was extracted from the THC self-improvement tools (`thc_self_check.py`, `thc_self_verify.py`, `thc_self_improve.py`) after 24+ audit iterations proved its effectiveness (64 structural checks, 129 content assertions, all passing).

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CONFIG (JSON)                         │
│  paths, skills[], docs[], owner, thresholds, rules      │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────┼─────────────────┐
         ▼             ▼                 ▼
   ┌──────────┐  ┌──────────┐    ┌──────────┐
   │  CHECK   │  │  VERIFY  │    │  IMPROVE  │
   │ structural│  │ content  │    │ orchestr. │
   │  checks  │  │ assertions│    │ pipeline  │
   └────┬─────┘  └────┬─────┘    └────┬─────┘
        │              │               │
        ▼              ▼               ▼
   ┌──────────────────────────────────────┐
   │          COMMON (shared lib)          │
   │  Finding, Report, path resolution,    │
   │  config loading, git utils, I/O       │
   └──────────────────────────────────────┘
```

## Getting Started

### Step 1: Create a Config File

Every skill tree needs a `self_improvement_config.json`. Use the template generator:

```bash
python .opencode/skill/self-improve/tools/self_improve_common.py init \
  --skill-base .opencode/skill/my-domain \
  --agent-def .opencode/agent/MY-DOMAIN/MY-DOMAIN.md \
  --skills "sub1,sub2,sub3" \
  --owner "Doe, John (johndoe)" \
  --output .opencode/skill/my-domain/tools/self_improvement_config.json
```

This creates a config with the correct structure:

```json
{
  "_comment": "Self-improvement config for my-domain skill tree",
  "_owner": "johndoe",
  "_version": "1.0.0",
  "paths": {
    "skill_base": ".opencode/skill/my-domain",
    "agent_def": ".opencode/agent/MY-DOMAIN/MY-DOMAIN.md",
    "docs_dir": ".opencode/skill/my-domain/docs",
    "eval_dir": ".opencode/skill/my-domain/eval",
    "tools_dir": ".opencode/skill/my-domain/tools",
    "reports_dir": ".opencode/skill/my-domain/reports"
  },
  "skills": ["sub1", "sub2", "sub3"],
  "docs": [],
  "owner": {
    "name": "Doe, John",
    "idsid": "johndoe",
    "tag": "> **Owner**: Doe, John (`johndoe`)"
  },
  "self_check": {
    "owner_tag": "johndoe",
    "expected_skill_count": 3,
    "cross_references": {}
  },
  "self_verify": {
    "eval_tests_file": ".opencode/skill/my-domain/eval/eval_tests.md",
    "pass_threshold_pct": 95,
    "results_dir": ".opencode/skill/my-domain/eval"
  },
  "self_improve": {
    "auto_apply": false,
    "require_human_approval": true,
    "max_proposals_per_run": 20,
    "proposals_file": ".opencode/skill/my-domain/tools/proposals.json",
    "changelog_file": ".opencode/skill/my-domain/tools/CHANGELOG.md"
  }
}
```

### Step 2: Define Structural Checks

Structural checks verify the **shape** of your skill tree — files exist, frontmatter is valid, cross-references are consistent. The generic checker provides these built-in checks:

| Check | What It Verifies |
|-------|-----------------|
| `skill_files_exist` | Every skill in config `skills[]` has a `SKILL.md` |
| `owner_headers` | Owner tag appears in first 10 lines of every skill/doc file |
| `subskill_count` | Agent definition's claimed count matches actual directories |
| `cross_references` | Bidirectional cross-references between skill pairs |
| `doc_files_exist` | Every file in config `docs[]` exists |
| `eval_files` | Eval test file exists and has expected structure |
| `frontmatter` | YAML frontmatter has `name` and `description`, name matches directory |
| `stale_references` | Custom regex patterns flagged as known-stale values |

Run checks:

```bash
python .opencode/skill/self-improve/tools/self_check.py \
  --config .opencode/skill/my-domain/tools/self_improvement_config.json
```

Options:
- `--json` — JSON output
- `--save` — Save report to reports directory
- `--check <name>` — Run a specific check only
- `--pre-commit` — Run reduced subset suitable for git pre-commit hook

### Step 3: Define Content Assertions

Content assertions are **data-driven regex checks** against skill file content. Define them as a Python dictionary:

```python
# In your custom verify script or assertion file
EVAL_TESTS = {
    "MY-001": {
        "name": "Widget count is documented",
        "skill": "widgets",
        "assertions": [
            ("contains", "widgets", r"supports\s+\d+\s+widget types", "widget count stated"),
            ("not_contains", "widgets", r"deprecated.*widget", "no deprecated widgets"),
            ("value_match", "widgets", r"max_count", "256", "max count is 256"),
        ]
    },
}
```

Three assertion types:

| Type | Signature | Behavior |
|------|-----------|----------|
| `contains` | `(skill, regex, desc)` | PASS if regex matches skill content |
| `not_contains` | `(skill, regex, desc)` | PASS if regex does NOT match |
| `value_match` | `(skill, field_regex, expected, desc)` | Find field, check value within 300 chars |

Run verification:

```bash
python .opencode/skill/self-improve/tools/self_verify.py \
  --config .opencode/skill/my-domain/tools/self_improvement_config.json \
  --tests my_assertions.py
```

Options:
- `--json` — JSON output
- `--save` — Save report to eval directory
- `--category <cat>` — Run only a specific category
- `--test <id>` — Run a single test
- `--list` — List all available tests without running

### Step 4: Run the Improvement Pipeline

The orchestrator runs all stages and generates proposals:

```bash
python .opencode/skill/self-improve/tools/self_improve.py \
  --config .opencode/skill/my-domain/tools/self_improvement_config.json
```

Pipeline stages:
1. **CHECK** — Run structural checks
2. **VERIFY** — Run content assertions
3. **GAP** — Detect coverage gaps (important terms not covered by assertions)
4. **PROPOSE** — Generate improvement proposals from all findings

Options:
- `--stages check,verify,gap` — Run only specific stages
- `--skip-stages gap` — Skip specific stages
- `--dry-run` — Show what would be proposed without writing files
- `--auto-apply` — Apply proposals without human review (use with caution)
- `--json` — JSON output

### Step 5: Review and Apply Proposals

Proposals are written to `proposals.json`:

```json
[
  {
    "id": "P001",
    "priority": "high",
    "category": "MISSING",
    "target_file": ".opencode/skill/my-domain/widgets/SKILL.md",
    "action": "add_content",
    "description": "Add widget count documentation",
    "rationale": "Assertion MY-001 failed: widget count not found",
    "source_findings": ["MY-001"],
    "status": "pending"
  }
]
```

Review each proposal, then apply manually or with `--auto-apply` on next run.

## Core Data Model

### Finding

The universal unit of information across all stages:

```python
class Finding:
    check: str      # Which check/test produced this
    target: str     # File or component affected
    status: str     # PASS | FAIL | WARN | ERROR | SKIP | CHANGE
    message: str    # Human-readable description
    severity: str   # critical | high | medium | low | info
    details: dict   # Optional structured data
```

### Report

Aggregates findings with metadata:

```python
class Report:
    name: str           # "self_check", "self_verify", etc.
    version: str        # Config version
    timestamp: str      # ISO 8601
    findings: list      # List of Finding objects
    
    # Properties
    pass_count: int
    fail_count: int
    has_failures: bool
    has_warnings: bool
    
    # Methods
    compute_summary() -> dict
    to_json() -> str
    to_text() -> str
    save(directory_or_file, fmt="json")
```

### Proposal

Generated from findings, requires approval:

```python
class Proposal:
    id: str             # P001, P002, ...
    priority: str       # critical | high | medium | low
    category: str       # MISSING | WRONG | STALE | GAP
    target_file: str    # Path to file needing change
    action: str         # add_content | fix_content | remove_content
    description: str    # What to change
    rationale: str      # Why (linked to findings)
    source_findings: list  # Finding IDs that triggered this
    status: str         # pending | approved | applied | rejected
```

## Adapting to Your Domain

### What You Must Customize

1. **Config file** — Paths, skill names, owner, docs list
2. **Content assertions** — Domain-specific regex patterns and expected values
3. **Stale reference patterns** — Known-bad values to flag (optional)
4. **Cross-reference rules** — Which skills should reference each other (optional)

### What You Get for Free

1. **Structural checks** — All 8 built-in checks work out of the box
2. **Report infrastructure** — Finding, Report, Proposal classes
3. **CLI interface** — `--json`, `--save`, `--pre-commit` flags
4. **Pipeline orchestration** — Stage sequencing, proposal generation, changelog
5. **Coverage gap detection** — Finds important terms not covered by assertions
6. **Git utilities** — Log parsing, diff stats, timestamp tracking

## Quality Gates

| Gate | Condition | Action on Failure |
|------|-----------|-------------------|
| G1-Structure | All structural checks PASS | Fix before proceeding |
| G2-Content | ≥95% of assertions PASS (configurable) | Review failures, fix or update assertions |
| G3-Coverage | No HIGH-priority coverage gaps | Add assertions for uncovered terms |
| G4-Proposals | All proposals reviewed | Approve, apply, or reject each |

## Common Pitfalls

| Pitfall | Lesson |
|---------|--------|
| Generic assertions | Make assertions specific — `r"supports\s+\d+"` not `r"supports"` |
| Over-testing | Focus assertions on facts that could go wrong, not obvious structure |
| Ignoring coverage gaps | If an important term isn't tested, it WILL drift silently |
| Auto-apply without review | Always review proposals first; automation can make wrong fixes |
| Stale config | Update config when skills are added/removed/renamed |
| Monolithic assertions file | Group by category (e.g., `REG-*`, `PWR-*`) for maintainability |

## Tools

### `self_improve_common.py`

Shared utilities — Finding, Report, Proposal, config loading, path resolution, git utilities.

```bash
# Initialize a new config
python .opencode/skill/self-improve/tools/self_improve_common.py init --help

# Validate an existing config
python .opencode/skill/self-improve/tools/self_improve_common.py validate \
  --config path/to/config.json
```

### `self_check.py`

Generic structural checker — works with any config.

```bash
python .opencode/skill/self-improve/tools/self_check.py \
  --config path/to/config.json [--json] [--save] [--check NAME] [--pre-commit]
```

### `self_verify.py`

Generic content verifier — loads assertion definitions from a Python module.

```bash
python .opencode/skill/self-improve/tools/self_verify.py \
  --config path/to/config.json --tests path/to/assertions.py \
  [--json] [--save] [--category CAT] [--test ID] [--list]
```

### `self_improve.py`

Pipeline orchestrator — runs check → verify → gap → propose.

```bash
python .opencode/skill/self-improve/tools/self_improve.py \
  --config path/to/config.json \
  [--stages check,verify,gap] [--skip-stages gap] \
  [--dry-run] [--auto-apply] [--json]
```

## Example: Adapting for a New Domain

```bash
# 1. Initialize config
python .opencode/skill/self-improve/tools/self_improve_common.py init \
  --skill-base .opencode/skill/fv-pcie \
  --agent-def .opencode/agent/FV/FV-PCIE.md \
  --skills "phy,ltssm,config-space,dpc,aer,ptm" \
  --owner "Smith, Jane (jsmith)" \
  --output .opencode/skill/fv-pcie/tools/self_improvement_config.json

# 2. Create assertions (pcie_assertions.py)
# EVAL_TESTS = { "PHY-001": { ... }, "LTSSM-001": { ... } }

# 3. Run structural checks
python .opencode/skill/self-improve/tools/self_check.py \
  --config .opencode/skill/fv-pcie/tools/self_improvement_config.json

# 4. Run content verification
python .opencode/skill/self-improve/tools/self_verify.py \
  --config .opencode/skill/fv-pcie/tools/self_improvement_config.json \
  --tests .opencode/skill/fv-pcie/tools/pcie_assertions.py

# 5. Run full improvement pipeline
python .opencode/skill/self-improve/tools/self_improve.py \
  --config .opencode/skill/fv-pcie/tools/self_improvement_config.json
```

## Relationship to Other Skills

| Skill | Relationship |
|-------|-------------|
| `doc-study` | Provides the document extraction/verification pipeline that feeds into cross-check audits |
| `skill-audit` | Orchestrates multi-document audits; self-improve validates the *results* of audits |
| `driver-diff` | Produces findings that become input to self-improve proposals |
| Domain skills (e.g., `fv-thc`) | The *targets* that self-improve checks and improves |


