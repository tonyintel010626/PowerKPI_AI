---
name: credentials
description: Unified Intel credential manager — single keyring entry for all Intel intranet services
license: MIT
---

# Credentials — Unified Intel Credential Manager

Single source of truth for Intel intranet credentials (IDSID + password). Run once, used by every skill that needs authentication.

## Overview

All Intel skills that require authentication (Confluence wiki, Co-Design, OneBKC, GENI, etc.) share **one** keyring entry instead of each managing their own. This eliminates:

- 6+ different keyring service names across the codebase
- Duplicate GUI/CLI password prompts per skill
- Hardcoded usernames and domain prefixes
- Fragile fallback chains trying multiple service names

## Setup (One Time)

```bash
# GUI popup (recommended)
python <cwd>/.opencode/skill/credentials/intel_credentials.py --refresh

# Console fallback (no GUI)
python <cwd>/.opencode/skill/credentials/intel_credentials.py --refresh --console

# Verify stored credentials
python <cwd>/.opencode/skill/credentials/intel_credentials.py --status

# Test against Confluence wiki
python <cwd>/.opencode/skill/credentials/intel_credentials.py --test
```

After first setup, **no further prompts** — all skills silently retrieve credentials from keyring.

## Script Location

```
<cwd>/.opencode/skill/credentials/intel_credentials.py
```

## Python API (For Skill Authors)

```python
import sys, os
sys.path.insert(0, os.path.join(os.environ.get("CWD", "."), ".opencode/skill/credentials"))
from intel_credentials import get_credentials, get_idsid, get_domain

# Get username + password (raises CredentialError if not set up)
username, password = get_credentials()

# Get domain\username string (e.g. "gar\aabdulmu")
idsid = get_idsid()

# Get just the domain (e.g. "gar")
domain = get_domain()

# Auto-prompt if missing (GUI popup, then CLI fallback)
username, password = ensure_credentials()
```

### Functions

| Function | Returns | Description |
|----------|---------|-------------|
| `get_credentials(username=None)` | `(str, str)` | Returns `(username, password)`. Raises `CredentialError` if unavailable. |
| `get_idsid(username=None)` | `str` | Returns `"domain\\username"` (e.g. `"gar\\aabdulmu"`) |
| `get_domain()` | `str` | Returns Windows domain in lowercase (e.g. `"gar"`) |
| `ensure_credentials(username=None)` | `(str, str)` | Like `get_credentials` but auto-prompts GUI if missing |
| `clear_credentials(username=None)` | `None` | Delete stored credentials |
| `status(username=None)` | `dict` | Returns credential status info |

## CLI Commands

| Command | Description |
|---------|-------------|
| `--status` | Check if credentials are stored (default action) |
| `--refresh` | Re-enter password (GUI popup, falls back to console) |
| `--refresh --console` | Re-enter password via console only |
| `--clear` | Delete stored credentials |
| `--test` | Test credentials against Confluence wiki |
| `--user <idsid>` | Override the default username |
| `--json` | Output status as JSON |

## Keyring Details

| Setting | Value |
|---------|-------|
| Service name | `intel_credentials` |
| Username | Current Windows user (e.g. `aabdulmu`) |
| Backend | Windows Credential Manager |
| Domain | Auto-detected from `%USERDOMAIN%` |

## Legacy Migration

On first use, if no credentials exist under `intel_credentials`, the system automatically checks these legacy service names and migrates:

| Legacy Service | Used By |
|----------------|---------|
| `intel_confluence_wiki` | securewiki |
| `codesign_mcp` | Co-Design MCP |
| `securewiki` | thc_wiki_verify |
| `confluence` | nvu_wiki_verify |
| `wiki.ith.intel.com` | thc_wiki_verify |
| `onebkc` | OneBKC |

Migration copies the password to `intel_credentials` and leaves the legacy entry intact.

## Skills That Use This

| Skill | What It Authenticates |
|-------|----------------------|
| securewiki | Intel Confluence Wiki REST API (HTTP Basic Auth) |
| codesign | Co-Design plugin API (JWT login) |
| onebkc | OneBKC API |
| geni | GENI / Axon / IBI APIs (MSAL + Kerberos) |
| fv-thc (wiki verify) | Confluence wiki page reads |
| fv-nvu (wiki verify) | Confluence wiki page reads |

## Troubleshooting

### "No Intel credentials found"
```bash
python <cwd>/.opencode/skill/credentials/intel_credentials.py --refresh
```

### "401 Unauthorized" from any skill
Password likely changed. Refresh:
```bash
python <cwd>/.opencode/skill/credentials/intel_credentials.py --refresh --test
```

### GUI popup doesn't appear
Use console mode:
```bash
python <cwd>/.opencode/skill/credentials/intel_credentials.py --refresh --console
```

### Check keyring backend
```bash
python -c "import keyring; print(keyring.get_keyring())"
```
