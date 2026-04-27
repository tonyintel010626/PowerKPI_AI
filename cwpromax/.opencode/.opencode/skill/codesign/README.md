# Co-De Sign API Skill

## Overview

A simplified skill that teaches AI how to interact with Intel's Co-De Sign API in simple, manageable snippets.

## What Was Created

1. **SKILL.md** - Complete documentation with all commands and examples
2. **codesign_api.py** - Simplified Python script with 7 commands
3. **assets/Example.java** - Sample file for testing uploads

## Key Features

### Authentication (2-step)
- Step 1: Get Apigee OAuth token
- Step 2: Get Co-De Sign token via LDAP

### Core Functions (7 commands)

1. **upload** - Upload files to Co-De Sign
2. **delete** - Delete files by ID
3. **list-projects** - Show all accessible projects
4. **list-files** - Show all uploaded files
5. **ask-files** - Query AI about uploaded files
6. **ask-projects** - Query AI about project documents
7. **ask-followup** - Continue conversation with thread_id

## Simplifications from Original

### Original Script (~200 lines)
- Complex logging setup
- Multiple try-catch blocks
- Mixed responsibilities
- Hard to understand flow

### New Skill (~260 lines)
- ✅ Clear function separation (one function per API call)
- ✅ Simple command-line interface
- ✅ Self-documenting code with step numbers
- ✅ Easy-to-understand error handling
- ✅ Emoji indicators for better UX

## Teaching Approach

Each function is designed as a **teaching snippet**:

```python
def get_apigee_token():
    """Step 1: Get OAuth token from Apigee"""
    payload = {
        'grant_type': 'client_credentials',
        'client_id': API_KEY,
        'client_secret': API_SECRET
    }
    response = requests.post(ENDPOINTS['token'], data=payload, proxies=PROXIES)
    response.raise_for_status()
    return response.json()['access_token']
```

**Why this works for AI:**
- Clear step labeling (Step 1, Step 2, etc.)
- Minimal code per function
- Single responsibility principle
- Easy to copy and adapt

## Usage Examples

### Basic File Upload
```bash
python .opencode/skill/codesign/codesign_api.py upload assets/Example.java
```

### Query Projects
```bash
python .opencode/skill/codesign/codesign_api.py ask-projects "What is PMC?" --limit 5
```

### Conversational Follow-up
```bash
# First question (note the thread_id from output)
python .opencode/skill/codesign/codesign_api.py ask-projects "Explain SoC Config"

# Follow-up with same thread_id
python .opencode/skill/codesign/codesign_api.py ask-followup "abc-123-def" "Give examples"
```

## Environment Setup

Create `.env` file:
```
IDSID=your_idsid
PASS=your_password
API_KEY=your_apigee_key
API_SECRET=your_apigee_secret
```

## Files Structure

```
.opencode/skill/codesign/
├── SKILL.md              # Complete documentation
├── codesign_api.py       # Simplified script (7 commands)
├── assets/
│   └── Example.java      # Test file
└── README.md             # This file
```

## Next Steps

To enable evaluations, create:
```
.opencode/skill/codesign/EVAL/opencode.json
```

Example evaluation config:
```json
{
  "$schema": "https://opencode.ai/config.json",
  "command": {
    "test-upload": {
      "template": "Use codesign skill to upload Example.java. EVAL: Should return doc_id",
      "agent": "EVAL-SKILL",
      "model": "github-copilot/gpt-5-mini"
    },
    "test-list-projects": {
      "template": "Use codesign skill to list projects. EVAL: Should show at least 1 project",
      "agent": "EVAL-SKILL",
      "model": "github-copilot/gpt-5-mini"
    }
  }
}
```

## Benefits for AI Training

1. **Bite-sized learning** - Each function teaches one concept
2. **Clear patterns** - Authentication → Action → Response
3. **Reusable snippets** - Functions can be copied independently
4. **Progressive complexity** - From simple (upload) to complex (conversational AI)
5. **Real-world example** - Shows complete OAuth + API workflow

## Comparison to Original

| Aspect | Original | Skill Version |
|--------|----------|---------------|
| Lines of code | ~200 | ~260 (with CLI) |
| Functions | Mixed | 7 clear functions |
| Error handling | Complex try-catch | Simple raise_for_status |
| Documentation | Inline comments | Docstrings + SKILL.md |
| Usage | Script-only | CLI with 7 commands |
| Learning curve | Steep | Gentle |
