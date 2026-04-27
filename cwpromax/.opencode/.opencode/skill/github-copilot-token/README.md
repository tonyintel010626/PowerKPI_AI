# github-copilot-token

![Status](https://img.shields.io/badge/status-active-brightgreen)

**Description:** Check GitHub Copilot token information and usage statistics

## Features

This skill provides tools to:
- Get GitHub Copilot token owner information
- Check API usage statistics and rate limits
- View detailed usage percentages
- Monitor Copilot token expiration and features

## Scripts

### 1. Get Token Info
Retrieves token owner information and basic usage statistics.

**Script:** `get_token_info.py`

**Usage:**
```bash
python get_token_info.py [auth_file_path]
```

**Default auth file:** `C:\Users\aabdulmu\.local\share\opencode\auth.json`

**Output:**
- Token owner username, email, profile URL
- Account type and company information
- Rate limit summary for Core, Search, and GraphQL APIs
- Account statistics (repos, followers, etc.)

### 2. Get Token Usage
Retrieves detailed API usage statistics in percentage format.

**Script:** `get_token_usage.py`

**Usage:**
```bash
python get_token_usage.py [auth_file_path]
```

**Output:**
- Overall API usage percentage
- Detailed usage breakdown for all API resources
- Copilot token metadata (type, expiration, features)
- Token feature flags (chat, agent mode, MCP, etc.)

## Examples

### Get token owner information
```bash
python .opencode/skills/github-copilot-token/get_token_info.py
```

### Get detailed usage statistics
```bash
python .opencode/skills/github-copilot-token/get_token_usage.py
```

### Use custom auth file path
```bash
python .opencode/skills/github-copilot-token/get_token_info.py "C:\custom\path\auth.json"
```

## Requirements

- Python 3.6+
- `requests` library

Install requirements:
```bash
pip install requests
```

## Token Information

The skill works with GitHub Copilot tokens stored in OpenCode's `auth.json` file. The token must:
- Start with `ghu_` prefix (GitHub user token)
- Be a valid GitHub Copilot token with API access
- Have appropriate permissions to access user and rate limit endpoints

## API Rate Limits

GitHub API rate limits monitored:
- **Core API:** 15,000 requests/hour (for business accounts)
- **Search API:** 30 requests/minute
- **GraphQL API:** 5,000 points/hour
- **Code Search:** 10 requests/minute

## Notes

- Usage statistics represent GitHub API rate limits, not Copilot-specific completion/chat metrics
- Copilot completion usage is only available through GitHub organization dashboard
- Token expiration is checked and displayed in the detailed usage output
