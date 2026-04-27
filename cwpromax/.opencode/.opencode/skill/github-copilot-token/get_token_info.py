"""
GitHub Copilot Token Info Script - Get token owner and details

This script reads the GitHub Copilot token from OpenCode's auth.json file
and retrieves information about the token owner and basic usage statistics.

Usage:
    python get_token_info.py [auth_file_path]

Examples:
    # Using default auth file path
    python get_token_info.py
    
    # Using custom auth file path
    python get_token_info.py "C:\\Users\\username\\.local\\share\\opencode\\auth.json"
"""

import json
import sys
import os
from pathlib import Path
import requests
from datetime import datetime


def get_default_auth_path():
    """Get the default OpenCode auth.json path based on OS."""
    home = Path.home()
    if os.name == 'nt':  # Windows
        return home / '.local' / 'share' / 'opencode' / 'auth.json'
    else:  # Unix-like
        return home / '.local' / 'share' / 'opencode' / 'auth.json'


def read_token_from_auth(auth_file_path):
    """
    Read GitHub Copilot token from auth.json file.
    
    Args:
        auth_file_path: Path to auth.json file
        
    Returns:
        str: GitHub token (refresh token starting with 'ghu_')
    """
    try:
        with open(auth_file_path, 'r') as f:
            auth_data = json.load(f)
        
        if 'github-copilot' not in auth_data:
            raise ValueError("github-copilot section not found in auth.json")
        
        token = auth_data['github-copilot'].get('refresh')
        if not token:
            raise ValueError("refresh token not found in auth.json")
        
        if not token.startswith('ghu_'):
            raise ValueError("Invalid token format - expected token starting with 'ghu_'")
        
        return token
    except FileNotFoundError:
        raise FileNotFoundError(f"Auth file not found: {auth_file_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in auth file: {auth_file_path}")


def get_token_info(token):
    """
    Get information about the GitHub token owner.
    
    Args:
        token: GitHub token
        
    Returns:
        dict: User information from GitHub API
    """
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    response = requests.get('https://api.github.com/user', headers=headers)
    
    if response.status_code != 200:
        raise Exception(
            f"GitHub API request failed with status {response.status_code}\n"
            f"Response: {response.text}"
        )
    
    return response.json()


def get_rate_limit(token):
    """
    Get rate limit information for the token.
    
    Args:
        token: GitHub token
        
    Returns:
        dict: Rate limit information from GitHub API
    """
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    response = requests.get('https://api.github.com/rate_limit', headers=headers)
    
    if response.status_code != 200:
        raise Exception(
            f"GitHub API request failed with status {response.status_code}\n"
            f"Response: {response.text}"
        )
    
    return response.json()


def format_timestamp(timestamp):
    """Convert Unix timestamp to readable datetime string."""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def main():
    """Main function for command line execution."""
    # Get auth file path from argument or use default
    if len(sys.argv) > 1:
        auth_file_path = sys.argv[1]
    else:
        auth_file_path = get_default_auth_path()
    
    try:
        # Read token from auth file
        token = read_token_from_auth(auth_file_path)
        
        # Get user info and rate limit
        user_info = get_token_info(token)
        rate_limit = get_rate_limit(token)
        
        # Format output
        result = {
            "token_owner": {
                "username": user_info.get('login'),
                "name": user_info.get('name'),
                "email": user_info.get('email'),
                "user_id": user_info.get('id'),
                "profile_url": user_info.get('html_url'),
                "account_type": user_info.get('type'),
                "company": user_info.get('company'),
                "created_at": user_info.get('created_at'),
                "public_repos": user_info.get('public_repos'),
                "followers": user_info.get('followers'),
                "following": user_info.get('following')
            },
            "rate_limit_summary": {
                "core_api": {
                    "limit": rate_limit['resources']['core']['limit'],
                    "used": rate_limit['resources']['core']['used'],
                    "remaining": rate_limit['resources']['core']['remaining'],
                    "reset_time": format_timestamp(rate_limit['resources']['core']['reset'])
                },
                "search_api": {
                    "limit": rate_limit['resources']['search']['limit'],
                    "used": rate_limit['resources']['search']['used'],
                    "remaining": rate_limit['resources']['search']['remaining'],
                    "reset_time": format_timestamp(rate_limit['resources']['search']['reset'])
                },
                "graphql_api": {
                    "limit": rate_limit['resources']['graphql']['limit'],
                    "used": rate_limit['resources']['graphql']['used'],
                    "remaining": rate_limit['resources']['graphql']['remaining'],
                    "reset_time": format_timestamp(rate_limit['resources']['graphql']['reset'])
                }
            },
            "auth_file_path": str(auth_file_path)
        }
        
        print(json.dumps(result, indent=2))
        return 0
        
    except Exception as e:
        error_result = {
            "error": str(e),
            "auth_file_path": str(auth_file_path)
        }
        print(json.dumps(error_result, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
