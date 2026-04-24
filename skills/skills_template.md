# Skill Definition Template

> Copy this template to create a new skill definition.  
> Replace all placeholder values (`<...>`) with real content.  
> Remove this header block before committing.

---

## `<PKPI-SKL-XXX>` — `<Skill Name>`

| Field | Value |
|-------|-------|
| **Skill ID** | `PKPI-SKL-XXX` |
| **Name** | `<Skill Name>` |
| **Category** | `<Data \| Analysis \| Debug \| Performance \| Reporting \| Alerting \| UI \| Validation>` |
| **Version** | `1.0` |
| **Branch** | `<main \| feature/branch-name>` — set to `main` for general skills |

### Purpose

`<One or two sentences describing what this skill does and why it exists.>`

### Trigger

- `<Condition or event that causes this skill to activate>`
- `<Another trigger condition>`

### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `param_name` | string | ✅ | `<Description>` |
| `optional_param` | number | ❌ | `<Description>` (default: `<value>`) |

### Outputs

| Field | Type | Description |
|-------|------|-------------|
| `output_field` | object | `<Description>` |
| `status` | string | `<success \| partial \| failed>` |

### Steps

1. `<First action or reasoning step>`
2. `<Second action or reasoning step>`
3. `<Continue as needed>`

### Integration

- `<PowerKPI component or external service this skill calls>`
- `<Another integration point>`

### Notes / Edge Cases

- `<Any important caveats, limitations, or edge cases>`

---

## Importing General Skills (for branch-specific files)

If this is a **branch-specific** skill file, add an `## Imports` section before your skill definitions to declare which general skills from `main` you depend on:

```markdown
## Imports
- `main::PKPI-SKL-001`   # KPI Data Retrieval
- `main::PKPI-SKL-004`   # Log Analysis
```

These imports allow the agent to resolve and load general skill definitions at runtime and make them available to your custom skill steps.
