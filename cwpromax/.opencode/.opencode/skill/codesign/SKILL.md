---
name: codesign
description: Intel Co-De Sign API for document upload, project queries, and AI agent interactions
license: MIT
---

# Co-De Sign API Skill

This skill provides access to Intel's Co-De Sign for querying specifications, HAS documents, and interacting with AI agents.

## IMPORTANT: Preferred Access Method

**ALWAYS use the browser MCP to access Co-De Sign chat interface for the fastest and most efficient access.**

### Quick Access via Browser MCP (PREFERRED METHOD)

Use the browser MCP tools to navigate directly to the Co-De Sign chat interface:

```
URL: https://chat.co-design.intel.com/chat
Alternative: goto/codesign (redirects to the chat interface)
```

**Workflow:**
1. Use `browsermcp_browser_navigate` to open `https://chat.co-design.intel.com/chat`
2. Wait for the page to load (may need to wait 2-3 seconds)
3. Click on the chat textbox
4. Type your question and submit
5. Wait for the response (typically 5-10 seconds)

**Example Questions:**
- "How many I3C ports are there in LPSS for NVL project? Check the LPSS HAS"
- "What is the PMC architecture for PTL?"
- "Compare PRMRR_BASE register between PTL and NVL"

---

## Alternative: API Access (When Browser is Not Available)

If browser access is not available, you can use the Python API scripts below.

### Prerequisites

Required environment variables in `.env` file:
- `IDSID` - Your Intel IDSID (without domain prefix)
- `PASS` - Your Intel password
- `API_KEY` - Apigee API key
- `API_SECRET` - Apigee API secret

### Script Location

Script location: `<cwd>/.opencode/skill/codesign/codesign_api.py`

## API Usage

### 1. Upload a File

```bash
python <cwd>/.opencode/skill/codesign/codesign_api.py upload <file_path>
```

**Example:**
```bash
python .opencode/skill/codesign/codesign_api.py upload assets/Example.java
```

**Output:** File ID (doc_id) and upload status

---

### 2. Delete a File

```bash
python <cwd>/.opencode/skill/codesign/codesign_api.py delete <file_id>
```

**Example:**
```bash
python .opencode/skill/codesign/codesign_api.py delete abc123def456
```

---

### 3. List Projects

```bash
python <cwd>/.opencode/skill/codesign/codesign_api.py list-projects
```

**Output:** Lists all accessible projects with their IDs and names

---

### 4. List My Files

```bash
python <cwd>/.opencode/skill/codesign/codesign_api.py list-files
```

**Output:** Lists all uploaded files accessible to the user

---

### 5. Ask Agent a Question (My Files)

```bash
python <cwd>/.opencode/skill/codesign/codesign_api.py ask-files "<question>"
```

**Example:**
```bash
python .opencode/skill/codesign/codesign_api.py ask-files "Explain the Example.java file"
```

**Output:** AI agent's answer based on your uploaded files

---

### 6. Ask Agent a Question (Projects)

```bash
python <cwd>/.opencode/skill/codesign/codesign_api.py ask-projects "<question>" [--limit <N>]
```

**Example:**
```bash
python .opencode/skill/codesign/codesign_api.py ask-projects "What is the size of the hash in SoC Config Manifest?" --limit 3
```

**Output:** AI agent's answer with references to project documents

---

### 7. Ask Follow-up Question

```bash
python <cwd>/.opencode/skill/codesign/codesign_api.py ask-followup "<thread_id>" "<question>"
```

**Example:**
```bash
python .opencode/skill/codesign/codesign_api.py ask-followup "abc-123-def-456" "Can you provide more details?"
```

**Output:** AI agent's answer in the context of previous conversation

---

## API Details

### Endpoints

- **Auth Token**: `https://apis-internal-sandbox.intel.com/v1/auth/token`
- **LDAP Login**: `https://apis-internal-sandbox.intel.com/codesign/auth/login/ldap`
- **Upload File**: `https://apis-internal-sandbox.intel.com/codesign/online/upload_file`
- **Delete File**: `https://apis-internal-sandbox.intel.com/codesign/online/delete_file`
- **List Sources**: `https://apis-internal-sandbox.intel.com/codesign/online/auth/sources/all`
- **Ask Agent**: `https://apis-internal-sandbox.intel.com/codesign/llm/runs/wait`

### Agent Types

- **spec_agent**: Conversational agent with follow-up capability (supports thread_id)
- **spec_rag**: RAG agent without follow-up (ignores thread_id)

---

## Common Workflows

### Workflow 1: Upload and Query a File

```bash
# 1. Upload file
python .opencode/skill/codesign/codesign_api.py upload assets/mycode.java

# 2. Ask question about it
python .opencode/skill/codesign/codesign_api.py ask-files "What does this code do?"
```

### Workflow 2: Query Projects with Follow-up

```bash
# 1. Ask initial question
python .opencode/skill/codesign/codesign_api.py ask-projects "What is PMC?" --limit 5

# Note the thread_id from output, then:

# 2. Ask follow-up
python .opencode/skill/codesign/codesign_api.py ask-followup "<thread_id>" "Give me more examples"
```

---

## Notes

- All commands require authentication (handled automatically via .env)
- Intel proxy is configured automatically: `proxy-chain.intel.com:911/912`
- Thread IDs enable conversational context for follow-up questions
- The `--limit` flag restricts how many projects are used as context (default: 3)

---

## Known Limitations

### Browser-Based CoDesign Interaction
Using browsermcp to interact with `chat.co-design.intel.com` has known reliability issues:
- **Timing issues**: The chat textarea may not accept input reliably. Responses can take 15+ seconds.
- **Session management**: Need to navigate fresh each time (don't reuse stale browser tabs)
- **Flaky interactions**: Text input may fail silently or require multiple retry attempts

### Recommendation: Use API Script as Primary Method
For programmatic queries (especially register/architecture spec lookups common in FV debug workflows):
1. **Prefer** the `ask-projects` command via the API script over browser-based interaction
2. Use `--limit` to control context size and response speed
3. Browser-based CoDesign is best reserved for interactive exploration, not automated workflows

### Example: Register Spec Lookup Workflow
```bash
# Reliable approach (API-based)
python .opencode/skill/codesign/codesign_api.py ask-projects "What are the eSPI BootPrep and ResetPrep register offsets and fields?" --limit 5

# Less reliable (browser-based via browsermcp)
# Avoid for automation - timing issues and input failures
```
