# memory/_template

Copy this folder to memory/{username} when onboarding a new user.
Rename the folder to match the user's ID (e.g., their login or email prefix).

## Structure
- `profile.json`          — user preferences and settings
- `sessions/`             — one subfolder per conversation session
  - `{session_id}/`
    - `context.json`      — current session state and variables
    - `history.json`      — message history for this session
- `long_term/`            — persistent memory across sessions
  - `embeddings/`         — vector embeddings of past interactions
  - `notes.json`          — agent-written notes about this user
- `artifacts/`            — files generated for this user (reports, exports)
