# PowerKPI_AI

AI agent workspace for PowerKPI — multi-user, session-isolated.

## Architecture

```
PowerKPI_AI/
│
├── agents/                  # SHARED — agent definitions
│   ├── core/                # Base agent logic, prompt templates
│   └── specialized/         # Domain-specific agents (KPI analyst, report builder, etc.)
│
├── tools/                   # SHARED — tool implementations agents can call
├── skills/                  # SHARED — composable, higher-level skill definitions
├── knowledge/               # SHARED — organization-wide facts, KPI definitions, business rules
├── pipelines/               # SHARED — multi-agent orchestration workflows
├── config/                  # SHARED — workspace config (no secrets)
├── data/                    # SHARED — raw and processed data
│
├── memory/                  # USER-ISOLATED — one folder per user
│   ├── _template/           # Copy this when onboarding a new user
│   └── {username}/
│       ├── profile.json     # User preferences and settings
│       ├── sessions/        # Session isolation — one folder per conversation
│       │   └── {session_id}/
│       │       ├── context.json   # Current session state
│       │       └── history.json   # Message history
│       ├── long_term/       # Persistent memory across sessions
│       │   ├── embeddings/  # Vector embeddings of past interactions
│       │   └── notes.json   # Agent-written notes about this user
│       └── artifacts/       # Files generated for this user (reports, exports)
│
└── logs/                    # Audit and execution logs
    ├── system/              # System-wide pipeline and error logs
    └── {username}/          # Per-user agent interaction logs
```

## Multi-User Design Principle

- **Shared resources** (agents, tools, skills, knowledge, pipelines, config, data)
  are defined once and used by everyone.
- **User isolation** lives entirely inside `memory/{username}/`.
  Each user has their own profile, session history, long-term memory, and artifacts.
- **Sessions** are subfolders under `memory/{username}/sessions/{session_id}/`.
  A new session folder is created for each conversation.

## Onboarding a New User

1. Copy `memory/_template/` to `memory/{new_username}/`
2. Update `profile.json` with the user's ID and preferences
3. Create a log folder: `logs/{new_username}/`

## Current Users

| Username  | Memory Path              |
|-----------|--------------------------|
| weikangt  | memory/weikangt/         |
