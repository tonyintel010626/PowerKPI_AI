---
name: agent-builder
description: "Comprehensive knowledge base for creating OpenCode agents and skills — guides the AGENT-BUILDER through interview, design, and generation of digital copy agents"
disable: false
license: MIT
---

# Agent Builder Knowledge Base

This skill contains everything needed to create OpenCode agents and skills within the `applications.ai.ocode.market.skills` project. It serves as the reference manual for the AGENT-BUILDER agent.

---

## 1. What is OpenCode?

OpenCode is an AI-powered coding assistant that runs in the terminal. It provides a conversational interface where users interact with AI models to perform software engineering tasks. OpenCode supports:

- **Agents** — Configurable AI personas with specific roles, expertise, and tool access
- **Skills** — Loadable knowledge documents that give agents domain-specific instructions
- **Tools** — Built-in capabilities (file read/write, bash, search, web fetch, etc.)
- **MCP Servers** — External tool integrations (browser automation, custom APIs)

Users select an agent as their active assistant. That agent has a system prompt (its personality/instructions), access to specific tools, and can load skills for domain knowledge. Agents can delegate tasks to sub-agents using the `@AGENT-NAME` syntax.

---

## 2. Project Structure

The `applications.ai.ocode.market.skills` project organizes agents and skills as follows:

```
.opencode/
  agent/                          # All agent definitions
    AGENT-NAME.md                 # Standalone agent
    GROUP-NAME/                   # Grouped agents (related agents in subdirectory)
      PRIMARY-AGENT.md
      SUB-AGENT-1.md
      SUB-AGENT-2.md
  skill/                          # All skill definitions
    skill-name/                   # Each skill gets its own directory
      SKILL.md                    # Main skill document (required)
      script.py                   # Optional supporting scripts
      templates/                  # Optional template files
      sub-skill-name/             # Optional sub-skills
        SKILL.md
      EVAL/                       # Optional evaluation tests
        opencode.json
  xplugin/                        # OpenCode plugins
opencode.json                     # Project-level configuration
```

### Naming Conventions

| Entity | Convention | Example |
|--------|-----------|---------|
| Agent name | UPPERCASE-HYPHENATED | `FV-TRIAGE`, `TTK3-BIOS`, `N8N` |
| Agent filename | Same as name + `.md` | `FV-TRIAGE.md`, `N8N.md` |
| Agent directory | Same as primary agent name | `FV/`, `TTK3/` |
| Skill name | lowercase-hyphenated | `agent-builder`, `github-copilot-token` |
| Skill directory | Same as skill name | `agent-builder/`, `n8n/` |
| Sub-skill directory | Under parent skill | `ttk3/spi/`, `nga/results/` |
| Skill reference in agent body | `skills_` prefix, underscores | `skills_n8n`, `skills_ttk3_spi` |

---

## 3. Agent Definition Reference

An agent is a Markdown file (`.md`) with YAML frontmatter and a markdown body. The frontmatter configures the agent's behavior; the body is the agent's system prompt.

### 3.1 Complete YAML Frontmatter Schema

```yaml
---
# REQUIRED FIELDS
name: "AGENT-NAME"              # Unique identifier. UPPERCASE-HYPHENATED.
                                 # Used for @AGENT-NAME delegation syntax.

description: "..."              # Human-readable description shown in agent selection UI.
                                 # Should clearly state what this agent does.

mode: "primary"                 # How the agent is accessible:
                                 #   "primary"  — User can select it directly as active agent
                                 #   "subagent" — Only accessible via delegation from another agent
                                 #   "all"      — Available both as primary and sub-agent

# RECOMMENDED FIELDS
disable: false                  # Set to true to hide/disable the agent without deleting it

model: "github-copilot/..."    # LLM model to use. Available models:
                                 #   github-copilot/claude-opus-4.5    — Best reasoning, most expensive
                                 #   github-copilot/claude-opus-4      — Strong reasoning
                                 #   github-copilot/claude-sonnet-4.5  — Balanced quality/cost
                                 #   github-copilot/claude-sonnet-4    — Good quality, lower cost
                                 #   github-copilot/gpt-5-mini         — Fast, cheapest
                                 #   github-copilot/gemini-3-flash-preview — Fast alternative

reasoningEffort: medium         # How much the model reasons before responding:
                                 #   low    — Quick responses, less deliberation
                                 #   medium — Balanced (default)
                                 #   high   — Deep reasoning, slower but more thorough

textVerbosity: medium           # Response length:
                                 #   low    — Concise, minimal output
                                 #   medium — Balanced (default)

temperature: 0.3                # Sampling temperature (0.0 - 1.0):
                                 #   0.0 — Deterministic, precise (good for code generation)
                                 #   0.3 — Slightly creative (good for conversation + generation)
                                 #   0.5 — Moderate creativity (good for orchestrators)
                                 #   0.7+ — High creativity (rarely needed for agents)

top_p: 1.0                      # Nucleus sampling (0.0 - 1.0). Usually leave at default.

# OPTIONAL FIELDS
response_format:                # Force structured output format
  type: "json_object"           # Only use when agent must output JSON

instructions:                   # Array of system-level instructions prepended to context
  - "instruction text 1"        # Can reference skill names or routing rules
  - "instruction text 2"

# TOOL TOGGLES — Enable/disable specific tools for this agent
tool:
  list: true                    # List directory contents
  write: true                   # Create/overwrite files
  edit: true                    # Edit existing files
  bash: true                    # Execute shell commands
  read: true                    # Read file contents
  grep: true                    # Search file contents with regex
  glob: true                    # Find files by pattern
  webfetch: true                # Fetch web page content
  todowrite: true               # Create/manage todo lists
  task: true                    # Delegate to sub-agents
  skill: true                   # Load skills
  multi_tool_use.parallel: true # Call multiple tools simultaneously
  multi_tool_use.sequential: true

# PERMISSION CONTROLS — Fine-grained access control
permission:
  write: "allow"                # "allow" or "deny"
  edit: "allow"
  read: "allow"
  grep: "allow"
  glob: "allow"
  webfetch: "allow"
  bash:
    global: "allow"             # Global bash permission
    python: "allow"             # Allow python commands
    pip: "allow"                # Allow pip commands
    rm: "deny"                  # Deny destructive commands
    del: "deny"
  "mcp-browsermcp": "allow"    # MCP server permissions
---
```

### 3.2 Mode Selection Guide

| Mode | When to Use | Example |
|------|------------|---------|
| `primary` | The agent is a top-level persona that users select directly. Use when the agent is a standalone entry point. | `AGENT-BUILDER`, `FV`, `EVAL-JSON`, `logs-keeper` |
| `subagent` | The agent is only called by other agents via `@NAME`. Use when the agent performs a specific sub-task within a larger workflow. | `TTK3-BIOS`, `EVAL-SKILL`, `minion`, `AGENT-BUILDER-WRITER` |
| `all` | The agent can be used both ways. Use when the agent is useful both standalone AND as a helper for other agents. | `N8N`, `FV-PM-SOUTH` |

### 3.3 Model Selection Guide

| Model | Best For | Cost | Speed |
|-------|---------|------|-------|
| `claude-opus-4.5` | Complex reasoning, multi-phase workflows, interviews, design decisions | Highest | Slowest |
| `claude-opus-4` | Strong reasoning, complex domain tasks | High | Slow |
| `claude-sonnet-4.5` | Balanced — good for most agents, code generation, file creation | Medium | Medium |
| `claude-sonnet-4` | Good quality at lower cost, routine tasks, well-defined workflows | Lower | Faster |
| `gpt-5-mini` | Fast responses, simple tasks, evaluation, high-volume operations | Lowest | Fastest |
| `gemini-3-flash-preview` | Fast alternative, good for orchestrators that only delegate | Low | Fast |

**Recommendations for digital copy agents:**
- If the person's role involves complex troubleshooting/analysis → `claude-opus-4.5` or `claude-opus-4`
- If the role is balanced (some analysis, some routine) → `claude-sonnet-4.5`
- If the role is mostly routine workflows with clear steps → `claude-sonnet-4`
- For orchestrator agents that only delegate → `gemini-3-flash-preview` or `gpt-5-mini`

### 3.4 Agent Body Structure

The markdown body below the YAML frontmatter is the agent's system prompt. Follow this structure:

```markdown
# Role Definition
You are [NAME], a [role description]. You [primary function].

## Identity
- Name: [Full name or role title]
- Expertise: [List of domain areas]
- Communication style: [How this agent communicates]

## Capabilities
[What this agent can do, organized by category]

### Category 1
- Capability A
- Capability B

### Category 2
- Capability C

## Available Skills
Load these skills as needed:
- `skills_name` — [description] (load with: `/skill name`)

## Workflow
[Step-by-step process this agent follows]

### Phase 1: [Name]
1. Step one
2. Step two

### Phase 2: [Name]
1. Step one

## Sub-Agent Delegation
[If this agent delegates to sub-agents]
- @SUB-AGENT-1 — Use for [task type]. Keywords: [routing keywords]
- @SUB-AGENT-2 — Use for [task type]. Keywords: [routing keywords]

## Task Routing
[Keyword-based routing table if applicable]

| Keywords | Route To |
|----------|----------|
| word1, word2 | @SUB-AGENT-1 |
| word3, word4 | @SUB-AGENT-2 |

## Boundaries
- DO NOT: [things this agent should never do]
- REDIRECT: [topics to redirect to other agents/humans]
- ESCALATE: [when to ask for human help]

## Output Format
[Expected output structure if applicable]
```

### 3.5 Agent Patterns

#### Pattern 1: Simple Standalone Agent
A single agent with one skill, no sub-agents. Good for domain experts with focused expertise.
- Mode: `all` or `primary`
- Tools: most enabled
- Body: role + capabilities + skill reference + workflow
- Example: N8N agent

#### Pattern 2: Orchestrator + Sub-agents
A primary agent that delegates to specialized sub-agents. Good for domain experts with multiple distinct sub-domains.
- Primary agent: mode `primary`, tools limited (mainly `task`, `todowrite`, `skill`)
- Sub-agents: mode `subagent`, tools enabled for their specific tasks
- Primary body: routing table, delegation rules, context-passing protocol
- Example: TTK3 (orchestrator) → TTK3-BIOS, TTK3-DIAG, TTK3-POWER, TTK3-COMM, TTK3-BOOT

#### Pattern 3: Supervisor/Worker
A supervisor that NEVER does direct work, only plans and delegates. Good for complex multi-step tasks.
- Supervisor: mode `primary`, ALL direct tools disabled except `todowrite` and `task`
- Worker: mode `subagent`, all tools enabled
- Supervisor body: strict hands-off policy, context passing protocol, atomic decomposition rules
- Example: logs-keeper (supervisor) → minion (worker)

---

## 4. Skill Definition Reference

A skill is a directory under `.opencode/skill/` containing at minimum a `SKILL.md` file.

### 4.1 SKILL.md Frontmatter

```yaml
---
name: skill-name              # lowercase-hyphenated, matches directory name
description: "..."             # Clear description of what this skill provides
disable: false                 # Set to true to hide the skill
license: MIT                   # License (optional)
---
```

### 4.2 Skill Body Patterns

#### Pattern A: Documentation-Only Skill
Pure markdown instructions. No scripts, no external dependencies. Good for capturing procedural knowledge, SOPs, decision trees.

```markdown
# Skill Name

## Overview
[What this skill provides]

## Domain Knowledge
[Detailed domain knowledge organized by topic]

### Topic 1
[Information, procedures, decision criteria]

### Topic 2
[Information, procedures, decision criteria]

## Common Scenarios
[Scenario-based guidance]

### Scenario: [Name]
**Trigger:** [When this applies]
**Process:**
1. Step one
2. Step two
**Expected Outcome:** [What should happen]

## Reference Tables
[Quick-reference data]

## Troubleshooting
[Common issues and solutions]
```

#### Pattern B: Script-Backed Skill
Includes Python scripts that the agent can execute. Scripts should output JSON to stdout.

```markdown
# Skill Name

## Script Location
Scripts are located at `<cwd>/.opencode/skill/skill-name/`

## Prerequisites
```bash
pip install required-package
```

## Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| `VAR_NAME` | Description | Yes |

## How to Use

### CLI Usage
```bash
python <cwd>/.opencode/skill/skill-name/script.py [args]
```

### Python API Usage
```python
from script import function_name
result = function_name(args)
```

## API Reference
[Endpoint/function documentation]

## Error Handling
[Error codes and recovery procedures]

## Limitations
[Known limitations]
```

#### Pattern C: Hierarchical Skill with Sub-Skills
A parent skill with sub-skills in subdirectories. Good for large domains with distinct sub-areas.

```
skill-name/
  SKILL.md              # Main overview, lists sub-skills
  sub-skill-1/
    SKILL.md            # Detailed instructions for sub-area 1
  sub-skill-2/
    SKILL.md            # Detailed instructions for sub-area 2
```

The parent SKILL.md should list all sub-skills:
```markdown
## Available Sub-Skills
- `skill-name/sub-skill-1` — [description] (load with: `/skill skill-name/sub-skill-1`)
- `skill-name/sub-skill-2` — [description] (load with: `/skill skill-name/sub-skill-2`)
```

Sub-skills are loaded independently using `/skill parent/child` syntax.

---

## 5. Sub-Agent Delegation

### 5.1 How Delegation Works

An agent delegates to a sub-agent by referencing it with `@AGENT-NAME` in its system prompt. When the agent encounters a task matching the sub-agent's domain, it uses the `task` tool to invoke the sub-agent.

### 5.2 Context Passing Protocol

Sub-agents start with a fresh context — they do NOT inherit the parent agent's conversation history. The parent must pass ALL relevant context in the delegation prompt. Follow this template:

```
GOAL: [What the sub-agent should accomplish]
TARGET: [Specific files, systems, or entities to work with]
CONSTRAINTS: [Rules, limitations, output format requirements]
CONTEXT: [All background information the sub-agent needs]
INSTRUCTIONS: [Step-by-step instructions]
OUTPUT: [What the sub-agent should return]
```

### 5.3 Keyword-Based Routing

For orchestrator agents, define a routing table that maps keywords to sub-agents:

```markdown
## Task Routing

| Keywords | Route To | Description |
|----------|----------|-------------|
| bios, flash, ifwi, spi | @TTK3-BIOS | BIOS/IFWI provisioning |
| power, cycle, reboot, pdu | @TTK3-POWER | Power management |
| i2c, uart, gpio, serial | @TTK3-COMM | Communication interfaces |
```

The orchestrator agent scans incoming requests for these keywords and delegates accordingly.

---

## 6. EVAL Test Reference

### 6.1 Purpose
EVAL tests verify that a skill provides correct information. They run automatically in CI when skills are modified.

### 6.2 File Location
```
.opencode/skill/skill-name/EVAL/opencode.json
```

### 6.3 Format

```json
{
  "$schema": "https://opencode.ai/config.json",
  "command": {
    "test_descriptive_name": {
      "template": "use skills_skill_name. [instruction to the agent]. EVAL STATEMENT: [assertion that must be true]",
      "description": "Human-readable test description",
      "agent": "EVAL-SKILL",
      "model": "github-copilot/gpt-5-mini"
    },
    "another_test_name": {
      "template": "use skills_skill_name. [another instruction]. EVAL STATEMENT: [another assertion]",
      "description": "Another test description",
      "agent": "EVAL-SKILL",
      "model": "github-copilot/gpt-5-mini"
    }
  }
}
```

### 6.4 Writing Good EVAL Tests

- **Template format:** `"use skills_SKILL_NAME. INSTRUCTION. EVAL STATEMENT: ASSERTION"`
- **Skill reference:** Use `skills_` prefix with underscores replacing hyphens (e.g., `skills_agent_builder`)
- **Instructions:** Ask the agent to do something using the skill's knowledge
- **Assertions:** State what should be true about the response — be specific and verifiable
- **Agent:** Always use `"EVAL-SKILL"` — this is the dedicated evaluation sub-agent
- **Model:** Use `"github-copilot/gpt-5-mini"` for cost efficiency

### 6.5 Test Examples

```json
{
  "knows_api_key_docs": {
    "template": "use skills_n8n. How do I configure the N8N API key? EVAL STATEMENT: The response should mention environment variable N8N_API_KEY",
    "description": "Verify skill documents API key configuration",
    "agent": "EVAL-SKILL",
    "model": "github-copilot/gpt-5-mini"
  }
}
```

---

## 7. Digital Copy Design Patterns

This section guides the translation of human expertise into agent structure.

### 7.1 Mapping Human Traits to Agent Configuration

| Human Trait | Agent Configuration |
|-------------|-------------------|
| "I'm an expert in X, Y, Z" | → Capabilities list + skill with detailed knowledge |
| "People come to me for A" | → Agent description + role definition |
| "I troubleshoot by doing 1, 2, 3" | → Workflow section with numbered phases |
| "I'm concise and direct" | → `textVerbosity: low`, `temperature: 0.1-0.3` |
| "I explain things in detail" | → `textVerbosity: medium`, detailed skill documentation |
| "I use tools X, Y daily" | → Skill references to existing skills (NGA, HSDES, etc.) or new skill |
| "Don't ask me about Z" | → Boundaries section with redirects |
| "I handle 3 different areas" | → Consider sub-agent hierarchy |
| "I follow strict SOPs" | → Workflow section with exact step sequences |
| "I make judgment calls based on experience" | → Decision trees in skill, higher temperature |

### 7.2 When to Use Sub-Agents

Create sub-agents when the person's expertise spans **3 or more distinct sub-domains** that:
- Have different tooling needs
- Have different workflows
- Could operate independently
- Would benefit from separate system prompts

Example: An engineer who handles BIOS flashing, power cycling, AND I2C debugging → 3 sub-agents.

If the person's expertise is focused on 1-2 related areas, a single agent with a comprehensive skill is sufficient.

### 7.3 Skill Depth Guidelines

| Expertise Depth | Skill Pattern | Content Volume |
|----------------|--------------|----------------|
| Shallow / general knowledge | Documentation-only, brief | 50-150 lines |
| Moderate / procedural knowledge | Documentation-only, detailed | 150-400 lines |
| Deep / includes tools and scripts | Script-backed | 200-500 lines + scripts |
| Very deep / multiple sub-domains | Hierarchical with sub-skills | Parent: 100-200 lines, each sub-skill: 100-300 lines |

### 7.4 Connecting to Existing Skills

This project already has skills for many Intel tools. Before creating new skills, check if the user's domain overlaps with existing ones:

| Existing Skill | Domain | Load Command |
|---------------|--------|--------------|
| `nga` | NGA test automation (test runs, results, failures, planning) | `/skill nga` |
| `hsdes` | HSDES sighting/bug queries | `/skill hsdes` |
| `ttk3` | TTK3 hardware validation (SPI, power, I2C, GPIO, UART, etc.) | `/skill ttk3` |
| `pysv` | PythonSV silicon validation (register access, named nodes) | `/skill pysv` |
| `onebkc` | OneBKC release management | `/skill onebkc` |
| `n8n` | N8N workflow automation | `/skill n8n` |
| `codesign` | Intel Co-De Sign API | `/skill codesign` |
| `geni` | GENI AI API | `/skill geni` |
| `caas` | Container as a Service | `/skill caas` |
| `github-copilot-token` | GitHub Copilot token info | `/skill github-copilot-token` |

If the user's digital copy needs knowledge from these domains, reference existing skills rather than recreating them.

---

## 8. Validation Reference

### 8.1 Validation Script

The validation script is at `<cwd>/.opencode/skill/agent-builder/validate_agent.py`.

Usage:
```bash
python <cwd>/.opencode/skill/agent-builder/validate_agent.py <path-to-agent.md>
```

It checks:
- YAML frontmatter can be parsed
- Required fields present: `name`, `description`, `mode`
- `mode` is one of: `primary`, `subagent`, `all`
- `name` follows UPPERCASE-HYPHENATED convention
- `model` follows `github-copilot/` prefix pattern (if present)
- `temperature` is between 0.0 and 1.0 (if present)
- Body (system prompt) is non-empty
- Referenced sub-agents (`@AGENT-NAME`) have corresponding files in `.opencode/agent/`
- Referenced skills (`skills_xxx`) have corresponding directories in `.opencode/skill/`

Output is JSON:
```json
{"valid": true, "warnings": [], "errors": []}
```

### 8.2 Manual Validation Checklist

Before finalizing a generated agent, verify:

- [ ] Agent name is unique (no existing agent with same name)
- [ ] Skill directory name matches skill `name` field
- [ ] Agent mode matches its intended usage
- [ ] Model is appropriate for the agent's complexity
- [ ] All referenced skills exist or will be created
- [ ] All referenced sub-agents exist or will be created
- [ ] Boundaries section prevents the agent from overstepping
- [ ] Workflow section matches the user's actual process
- [ ] Tool permissions are not overly broad

---

## 9. Templates

Templates are located at `<cwd>/.opencode/skill/agent-builder/templates/`:

| Template | Purpose |
|----------|---------|
| `agent-template.md` | Skeleton for agent `.md` files |
| `skill-template.md` | Skeleton for skill `SKILL.md` files |
| `eval-template.json` | Skeleton for `EVAL/opencode.json` files |

Use these as starting points. Replace all `{{PLACEHOLDER}}` values with actual content.

---

## 10. Examples

Working examples are at `<cwd>/.opencode/skill/agent-builder/examples/`:

| Example | Pattern Shown |
|---------|--------------|
| `simple-agent.md` | Minimal standalone agent (mode: all, single skill) |
| `complex-agent.md` | Complex hierarchical agent (orchestrator + sub-agents, multi-phase workflow) |
| `simple-skill.md` | Documentation-only skill |
| `script-skill.md` | Script-backed skill with Python |

Study these examples to understand the conventions used in this project.

---

## 11. File Generation Checklist

When generating a complete digital copy agent package, create these files in order:

1. **Skill SKILL.md** — The agent's knowledge base
   - Path: `.opencode/skill/{skill-name}/SKILL.md`
   - Contains: all domain knowledge, procedures, reference data

2. **Supporting scripts** (if needed)
   - Path: `.opencode/skill/{skill-name}/script.py`
   - Must output JSON to stdout
   - Must handle errors gracefully

3. **Sub-skills** (if hierarchical)
   - Path: `.opencode/skill/{skill-name}/{sub-skill}/SKILL.md`
   - Each sub-skill is independently loadable

4. **Sub-agent files** (if hierarchical)
   - Path: `.opencode/agent/{AGENT-GROUP}/{SUB-AGENT-NAME}.md`
   - Each sub-agent has its own frontmatter and body

5. **Primary agent file**
   - Path: `.opencode/agent/{AGENT-NAME}.md` or `.opencode/agent/{AGENT-GROUP}/{AGENT-NAME}.md`
   - References skills and sub-agents created above

6. **EVAL tests**
   - Path: `.opencode/skill/{skill-name}/EVAL/opencode.json`
   - At least 3-5 test cases verifying skill knowledge

---

## 12. Common Pitfalls

| Pitfall | Prevention |
|---------|------------|
| Agent body too vague | Include specific workflows with numbered steps, not just general capabilities |
| Missing context passing | Sub-agents are stateless — always pass full context in delegation prompt |
| Over-broad permissions | Only enable tools the agent actually needs |
| Skill too shallow | A digital copy needs deep knowledge — include decision criteria, edge cases, not just procedures |
| No boundaries | Always define what the agent should NOT do and when to redirect |
| Wrong model choice | Match model to complexity — don't use opus for simple routing, don't use gpt-5-mini for complex analysis |
| Duplicate skills | Check existing skills before creating new ones — reference existing ones when possible |
| Missing EVAL tests | Always create at least basic tests to verify the skill loads and provides correct info |
