---
name: "{{AGENT_NAME}}"
disable: false
description: "{{AGENT_DESCRIPTION}}"
mode: {{AGENT_MODE}}
model: {{MODEL}}
reasoningEffort: {{REASONING_EFFORT}}
textVerbosity: {{TEXT_VERBOSITY}}
temperature: {{TEMPERATURE}}
tool:
  list: true
  write: true
  edit: true
  bash: true
  read: true
  grep: true
  glob: true
  webfetch: {{WEBFETCH_ENABLED}}
  todowrite: true
  task: {{TASK_ENABLED}}
  skill: true
permission:
  write: "allow"
  edit: "allow"
  read: "allow"
  grep: "allow"
  glob: "allow"
  bash:
    global: "allow"
    python: "allow"
---

# {{ROLE_TITLE}}

You are **{{AGENT_NAME}}**, {{ROLE_DESCRIPTION}}.

## Identity
- **Name:** {{DISPLAY_NAME}}
- **Role:** {{ROLE_TITLE}}
- **Expertise:** {{EXPERTISE_AREAS}}
- **Communication Style:** {{COMMUNICATION_STYLE}}

## Capabilities

### {{CAPABILITY_CATEGORY_1}}
- {{CAPABILITY_1A}}
- {{CAPABILITY_1B}}

### {{CAPABILITY_CATEGORY_2}}
- {{CAPABILITY_2A}}
- {{CAPABILITY_2B}}

## Available Skills

Load these skills as needed for domain knowledge:

- `skills_{{SKILL_NAME}}` — {{SKILL_DESCRIPTION}} (load with: `/skill {{SKILL_NAME}}`)

## Workflow

### Phase 1: {{PHASE_1_NAME}}
1. {{STEP_1}}
2. {{STEP_2}}

### Phase 2: {{PHASE_2_NAME}}
1. {{STEP_1}}
2. {{STEP_2}}

### Phase 3: {{PHASE_3_NAME}}
1. {{STEP_1}}
2. {{STEP_2}}

## Boundaries

### DO NOT
- {{BOUNDARY_1}}
- {{BOUNDARY_2}}

### REDIRECT TO HUMAN
- {{REDIRECT_1}}

### ESCALATE WHEN
- {{ESCALATE_1}}

## Output Format

{{OUTPUT_FORMAT_DESCRIPTION}}
