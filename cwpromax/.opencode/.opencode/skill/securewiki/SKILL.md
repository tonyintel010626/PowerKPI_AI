---
name: securewiki
description: Intel Confluence Wiki access with secure keyring credential storage - read, create, update pages
license: MIT
---

# SecureWiki - Intel Confluence Wiki API Skill

Securely access, read, create, and update pages on Intel's Enterprise Confluence Wiki (`https://wiki.ith.intel.com`) using REST API with automatic credential management via Windows Keyring.

## Overview

This skill provides secure, one-time credential setup for accessing Intel's Confluence Wiki. Credentials are stored in Windows Credential Manager (keyring) so you only need to enter your password once per machine.

**Key Features:**
- GUI password popup on first use (tkinter)
- Secure credential storage in Windows Keyring
- Auto-detects current Windows username as default
- Full REST API support: read, create, update, delete pages
- SSL handling for Intel's internal certificates

## Prerequisites

- **Python 3.8+**
- **Required packages**: `pip install requests keyring`
- **Network**: Must be on Intel network or VPN
- **Credentials**: Your Intel IDSID (e.g., `aabdulmu`) and password

## Script Location

All scripts at: `<cwd>/.opencode/skill/securewiki/`

## Available Scripts

| Script | Purpose | Command Format |
|--------|---------|----------------|
| `securewiki.py` | Main API wrapper - get, create, update pages | `python <cwd>/.opencode/skill/securewiki/securewiki.py <action> [args]` |
| `securewiki_auth.py` | Credential management - store, check, clear | `python <cwd>/.opencode/skill/securewiki/securewiki_auth.py [--status\|--refresh\|--clear]` |
| `securewiki_session.py` | Publish OpenCode sessions to Confluence wiki | `python <cwd>/.opencode/skill/securewiki/securewiki_session.py <session_file> [options]` |

## First-Time Setup (Automatic)

On first use, the script will:
1. Detect your Windows username (e.g., `aabdulmu`)
2. Show a GUI popup asking for your Intel password
3. Store credentials securely in Windows Credential Manager
4. Test the connection to verify credentials work

**After first use**: No password prompts - credentials are loaded from keyring automatically.

## Authentication Commands

```bash
# Check if credentials are stored
python <cwd>/.opencode/skill/securewiki/securewiki_auth.py --status

# Re-enter password (refresh credentials)
python <cwd>/.opencode/skill/securewiki/securewiki_auth.py --refresh

# Clear stored credentials
python <cwd>/.opencode/skill/securewiki/securewiki_auth.py --clear

# Use a different username
python <cwd>/.opencode/skill/securewiki/securewiki_auth.py --user jsmith --refresh
```

## Wiki Operations

### [GET] Read a Page

Fetch page content by page ID:

```bash
python <cwd>/.opencode/skill/securewiki/securewiki.py get <page_id>
```

**Example:**
```bash
python <cwd>/.opencode/skill/securewiki/securewiki.py get 2204060308
```

**Output:**
```json
{
  "id": "2204060308",
  "title": "FV Power Management Wiki Home",
  "space": "ITSfvpm",
  "version": 32,
  "body": "<p>Page content here...</p>"
}
```

### [CREATE] Create a New Page

Create a new page in a space:

```bash
python <cwd>/.opencode/skill/securewiki/securewiki.py create <space_key> "<title>" "<html_body>" [parent_id]
```

**Example - Create page under parent:**
```bash
python <cwd>/.opencode/skill/securewiki/securewiki.py create ITSfvpm "My New Page" "<p>Hello from API!</p>" 2204060308
```

**Example - Create top-level page in space:**
```bash
python <cwd>/.opencode/skill/securewiki/securewiki.py create ITSfvpm "Standalone Page" "<p>Content here</p>"
```

### [UPDATE] Update an Existing Page

Update page content (auto-increments version):

```bash
python <cwd>/.opencode/skill/securewiki/securewiki.py update <page_id> "<new_html_body>"
```

**Example:**
```bash
python <cwd>/.opencode/skill/securewiki/securewiki.py update 2204060308 "<p>Updated content via API</p>"
```

### [LIST] List Pages in a Space

Get all pages in a Confluence space:

```bash
python <cwd>/.opencode/skill/securewiki/securewiki.py list <space_key> [limit]
```

**Example:**
```bash
python <cwd>/.opencode/skill/securewiki/securewiki.py list ITSfvpm 10
```

### [SPACE] Get Space Information

Get metadata about a Confluence space:

```bash
python <cwd>/.opencode/skill/securewiki/securewiki.py space <space_key>
```

**Example:**
```bash
python <cwd>/.opencode/skill/securewiki/securewiki.py space ITSfvpm
```

### [DELETE] Delete a Page

Delete a page by ID:

```bash
python <cwd>/.opencode/skill/securewiki/securewiki.py delete <page_id>
```

**Example:**
```bash
python <cwd>/.opencode/skill/securewiki/securewiki.py delete 123456789
```

### [SEARCH] Search Pages with CQL

Search for pages across one or more Confluence spaces using text search (CQL - Confluence Query Language):

```bash
python <cwd>/.opencode/skill/securewiki/securewiki.py search "<query>" [--spaces <space_keys>] [--limit <n>] [--user <username>] [--json]
```

**Parameters:**
- `<query>` - Search text (required). Multiple words are supported.
- `--spaces` - Comma-separated space keys to restrict search (e.g., `fvcommon`, `DebugEncyclopedia`, `fvcommon,DebugEncyclopedia`). If omitted, searches all spaces.
- `--limit` - Max results to return (default: 10)
- `--user` - Username for authentication (default: current Windows user)
- `--json` - Output as formatted JSON

**Examples:**
```bash
# Search FVCommon for BSOD debug procedures
python <cwd>/.opencode/skill/securewiki/securewiki.py search "BSOD debug" --spaces fvcommon --user twai --json

# Search DebugEncyclopedia for MCA errors
python <cwd>/.opencode/skill/securewiki/securewiki.py search "MCA machine check" --spaces DebugEncyclopedia --user twai --json

# Search both spaces for S0ix power management
python <cwd>/.opencode/skill/securewiki/securewiki.py search "S0ix residency debug" --spaces fvcommon,DebugEncyclopedia --limit 15 --user twai --json

# Search all spaces (no --spaces filter)
python <cwd>/.opencode/skill/securewiki/securewiki.py search "thermal throttling" --user twai --json
```

**Output:**
```json
{
  "query": "BSOD debug",
  "cql": "type = \"page\" AND space = \"fvcommon\" AND text ~ \"BSOD debug\"",
  "total": 23,
  "returned": 10,
  "results": [
    {
      "id": "1234567890",
      "title": "BSOD Debug BKM for PTL",
      "space": "fvcommon",
      "url": "https://wiki.ith.intel.com/pages/viewpage.action?pageId=1234567890",
      "excerpt": "This page describes the BSOD debug procedure for Panther Lake..."
    }
  ]
}
```

### [READ] Read Full Page Content

Read the complete text content of a wiki page (no truncation, unlike `get` which truncates body to 500 chars). HTML tags are stripped to return clean plain text suitable for AI agent consumption.

```bash
python <cwd>/.opencode/skill/securewiki/securewiki.py read <page_id> [--user <username>] [--json]
```

**Parameters:**
- `<page_id>` - The Confluence page ID (required)
- `--user` - Username for authentication
- `--json` - Output as formatted JSON

**Example:**
```bash
python <cwd>/.opencode/skill/securewiki/securewiki.py read 1234567890 --user twai --json
```

**Output:**
```json
{
  "id": "1234567890",
  "title": "BSOD Debug BKM for PTL",
  "space": "fvcommon",
  "version": 5,
  "url": "https://wiki.ith.intel.com/pages/viewpage.action?pageId=1234567890",
  "body_text": "Full page content as plain text with HTML tags stripped...",
  "body_length": 4521
}
```

### Knowledge Retrieval Protocol

When using `search` and `read` for AI-assisted debug and knowledge retrieval:

1. **Search first** — Use `search` with specific terms (error codes, component names, "BKM", "debug")
2. **Read relevant pages** — Use `read` to fetch full content of the most relevant search results
3. **Cite sources** — Always include page title, ID, and URL when referencing wiki content
4. **Never fabricate** — If search returns no results, report "not found" honestly
5. **Target spaces for FV debug:**
   - `fvcommon` — 9,764 pages: debug BKMs, domain guides, project wikis, environment setup, training
   - `DebugEncyclopedia` — Debug procedures, error code references, hardware debug guides

## [PUBLISH-SESSION] Publish OpenCode Session to Wiki

Publish an OpenCode session markdown file (`session-*.md`) to Confluence as a themed wiki page. The page is styled with OpenCode's terminal-like appearance including color-coded user/assistant turns, tool call blocks, and code formatting.

**Default location**: Child page under [Ocode Session Use Cases Sharing](https://wiki.ith.intel.com/spaces/ITSfvpm/pages/4617023376/Ocode+Session+Use+Cases+Sharing) (page ID `4617023376` in space `ITSfvpm`).

### Basic Usage

```bash
# Publish session to default location
python <cwd>/.opencode/skill/securewiki/securewiki_session.py <session_file>
```

**Example:**
```bash
python <cwd>/.opencode/skill/securewiki/securewiki_session.py session-ses-2026W08.1127am.md
```

### Publish to Custom Location

```bash
# By parent page ID
python <cwd>/.opencode/skill/securewiki/securewiki_session.py session.md --parent 4617023376

# By parent page URL
python <cwd>/.opencode/skill/securewiki/securewiki_session.py session.md --parent "https://wiki.ith.intel.com/spaces/ITSfvpm/pages/4617023376/Ocode+Session+Use+Cases+Sharing"

# To a different space
python <cwd>/.opencode/skill/securewiki/securewiki_session.py session.md --space MYSPACE --parent 12345678
```

### Custom Title

By default, the title is auto-generated from the session's H1 heading with a date prefix (e.g., `2026-02-19 - Automating non-automated test cases analysis...`). Override with:

```bash
python <cwd>/.opencode/skill/securewiki/securewiki_session.py session.md --title "HSDES Test Case Automation Analysis"
```

### Preview and Dry Run

```bash
# Generate local HTML preview (writes .preview.html file)
python <cwd>/.opencode/skill/securewiki/securewiki_session.py session.md --preview

# Show what would be published without actually doing it
python <cwd>/.opencode/skill/securewiki/securewiki_session.py session.md --dry-run
```

### All Options

| Option | Description | Default |
|--------|-------------|---------|
| `<session_file>` | Path to session markdown file (required) | - |
| `--parent <id_or_url>` | Parent page ID or Confluence URL | `4617023376` (Ocode Session Use Cases Sharing) |
| `--space <key>` | Confluence space key | `ITSfvpm` |
| `--title "<text>"` | Override auto-generated page title | Date + session H1 heading |
| `--user <idsid>` | Intel IDSID username | Current Windows user |
| `--preview` | Write HTML preview locally instead of publishing | Off |
| `--dry-run` | Show what would be published | Off |
| `--json` | Output result as JSON | Off |

### OpenCode Theme

Published pages include:
- **Header**: Dark gradient banner with session title, ID, timestamps, and "OPENCODE SESSION" badge
- **User turns**: Blue-tinted background with user prompt text
- **Assistant turns**: White background with model info badge (e.g., `claude-opus-4.5 · 10.8s`)
- **Tool calls**: Terminal-style dark blocks showing tool name, input JSON, and output
- **Code blocks**: Dark-themed code with syntax-appropriate formatting
- **Footer**: OpenCode branding with GitHub link

## Finding Page IDs and Space Keys

**Page ID**: Found in the URL when viewing a page:
```
https://wiki.ith.intel.com/pages/viewpage.action?pageId=2204060308
                                                       ^^^^^^^^^^
                                                       This is the page ID
```

**Space Key**: Found in the space URL:
```
https://wiki.ith.intel.com/spaces/ITSfvpm/pages/...
                                  ^^^^^^^
                                  This is the space key
```

## Examples

### Example 1: Read your wiki home page
```
"Use securewiki skill to get page 2204060308"
```

### Example 2: Create a new documentation page
```
"Use securewiki to create a page titled 'API Documentation' in space ITSfvpm with content '<h1>API Docs</h1><p>Coming soon</p>'"
```

### Example 3: Update page with new content
```
"Use securewiki to update page 2204060308 with new HTML content"
```

### Example 4: List all pages in a space
```
"Use securewiki to list all pages in space ITSfvpm"
```

### Example 5: Check credential status
```
"Use securewiki auth to check if my credentials are stored"
```

### Example 6: Publish current OpenCode session to wiki
```
"Use securewiki to publish this session to the Ocode Session Use Cases Sharing page"
```

### Example 7: Publish session to custom location
```
"Use securewiki to publish session-ses-2026W08.1127am.md under page https://wiki.ith.intel.com/spaces/ITSfvpm/pages/1234567/My+Parent+Page"
```

### Example 8: Preview session before publishing
```
"Use securewiki to preview session-ses-2026W08.1127am.md locally"
```

## API Reference

### Base URL
```
https://wiki.ith.intel.com/rest/api
```

### Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/rest/api/content/{id}` | GET | Retrieve a page |
| `/rest/api/content/{id}?expand=body.storage,version` | GET | Get page with body |
| `/rest/api/content` | POST | Create a new page |
| `/rest/api/content/{id}` | PUT | Update a page |
| `/rest/api/content/{id}` | DELETE | Delete a page |
| `/rest/api/space/{key}` | GET | Get space info |
| `/rest/api/content?spaceKey={key}` | GET | List pages in space |
| `/rest/api/content/search?cql={cql}` | GET | Search pages with CQL |
| `/rest/api/content/{id}?expand=body.storage` | GET | Read full page content |

### Authentication

- **Method**: HTTP Basic Auth
- **Username**: Intel IDSID (e.g., `aabdulmu`)
- **Password**: Intel password
- **Storage**: Windows Credential Manager (keyring service: `intel_confluence_wiki`)

### SSL/TLS

Intel's wiki uses internal certificates. The scripts disable SSL verification (`verify=False`) to handle this. This is safe on Intel's internal network.

## Troubleshooting

### Password popup doesn't appear
- Check if another window is covering it (look in taskbar)
- Run script directly: `python securewiki_auth.py --refresh`
- Use console mode: `python securewiki_auth.py --console`

### "401 Unauthorized" error
- Password may have changed - refresh credentials: `python securewiki_auth.py --refresh`
- Verify username is correct: `python securewiki_auth.py --status`

### "SSL Certificate Error"
- This is handled automatically with `verify=False`
- Ensure you're on Intel network or VPN

### "Page not found" error
- Verify page ID exists and you have access
- Check if page was moved or deleted

### Credentials not saving
- Windows Credential Manager may be locked
- Try running as administrator
- Check keyring backend: `python -c "import keyring; print(keyring.get_keyring())"`

## Security Notes

1. **Credentials are stored securely** in Windows Credential Manager, not in plain text files
2. **Password is never logged** or printed to console
3. **SSL verification is disabled** only for Intel's internal certificates (safe on intranet)
4. **Keyring is machine-specific** - credentials don't roam between machines

## Default Behavior

| Setting | Default Value | Override |
|---------|---------------|----------|
| Username | Current Windows user (`os.getlogin()`) | `--user <username>` |
| Base URL | `https://wiki.ith.intel.com` | `--url <base_url>` |
| SSL Verify | `False` (for Intel certs) | `--verify` to enable |
| Keyring Service | `intel_confluence_wiki` | N/A |
| Session Parent Page | `4617023376` (Ocode Session Use Cases Sharing) | `--parent <id_or_url>` |
| Session Space | `ITSfvpm` | `--space <key>` |
| Session Title | Date prefix + session H1 heading | `--title "<text>"` |

## Support

- **Confluence Version**: 9.2.2 (Server/Data Center)
- **API Documentation**: https://wiki.ith.intel.com/rest/api/
- **Wiki Training**: Check "Wiki's Training site" link on wiki dashboard
