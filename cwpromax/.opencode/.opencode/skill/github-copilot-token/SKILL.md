---
name: github-copilot-token
description: Check GitHub Copilot token information and usage statistics
---
scripts is relative in folder.

# [GitHub Copilot Token Info] Get token owner and details
script location is at -> <cwd>/.opencode/skills/github-copilot-token/get_token_info.py
use get_token_info.py to fetch GitHub Copilot token owner information and usage statistics.
the command format is: python <cwd>/.opencode/skills/github-copilot-token/get_token_info.py [auth_file_path]

# [GitHub Copilot Token Usage] Get detailed usage percentages
script location is at -> <cwd>/.opencode/skills/github-copilot-token/get_token_usage.py
use get_token_usage.py to get detailed GitHub API usage statistics in percentage format.
the command format is: python <cwd>/.opencode/skills/github-copilot-token/get_token_usage.py [auth_file_path]

Default auth file path: C:\Users\aabdulmu\.local\share\opencode\auth.json
