"""
GitHub Copilot Token Usage Script - Get detailed usage percentages

This script reads the GitHub Copilot token from OpenCode's auth.json file
and retrieves detailed API usage statistics in percentage format.

Usage:
    python get_token_usage.py [auth_file_path]

Examples:
    # Using default auth file path
    python get_token_usage.py
    
    # Using custom auth file path
    python get_token_usage.py "C:\\Users\\username\\.local\\share\\opencode\\auth.json"
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
        
        # Also get token metadata
        access_token = auth_data['github-copilot'].get('access', '')
        expires = auth_data['github-copilot'].get('expires', 0)
        
        return token, access_token, expires
    except FileNotFoundError:
        raise FileNotFoundError(f"Auth file not found: {auth_file_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in auth file: {auth_file_path}")


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


def calculate_usage_percentage(used, limit):
    """Calculate usage percentage."""
    if limit == 0:
        return 0.0
    return (used / limit) * 100


def format_timestamp(timestamp):
    """Convert Unix timestamp to readable datetime string."""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def parse_access_token_metadata(access_token):
    """Parse metadata from the access token string."""
    metadata = {}
    if not access_token:
        return metadata
    
    parts = access_token.split(';')
    for part in parts:
        if '=' in part:
            key, value = part.split('=', 1)
            metadata[key] = value
    
    return metadata


def main():
    """Main function for command line execution."""
    # Get auth file path from argument or use default
    if len(sys.argv) > 1:
        auth_file_path = sys.argv[1]
    else:
        auth_file_path = get_default_auth_path()
    
    try:
        # Read token from auth file
        token, access_token, expires = read_token_from_auth(auth_file_path)
        
        # Parse access token metadata
        metadata = parse_access_token_metadata(access_token)
        
        # Get rate limit
        rate_limit = get_rate_limit(token)
        
        # Calculate usage percentages
        resources = rate_limit['resources']
        
        usage_data = {}
        for resource_name, resource_info in resources.items():
            usage_percentage = calculate_usage_percentage(
                resource_info['used'], 
                resource_info['limit']
            )
            usage_data[resource_name] = {
                "used": resource_info['used'],
                "limit": resource_info['limit'],
                "remaining": resource_info['remaining'],
                "usage_percentage": round(usage_percentage, 2),
                "reset_time": format_timestamp(resource_info['reset'])
            }
        
        # Overall rate limit
        overall = rate_limit['rate']
        overall_percentage = calculate_usage_percentage(overall['used'], overall['limit'])
        
        # Format output
        result = {
            "overall_usage": {
                "used": overall['used'],
                "limit": overall['limit'],
                "remaining": overall['remaining'],
                "usage_percentage": round(overall_percentage, 2),
                "reset_time": format_timestamp(overall['reset'])
            },
            "detailed_usage": usage_data,
            "copilot_token_info": {
                "token_type": metadata.get('sku', 'unknown'),
                "expires_at": format_timestamp(expires / 1000) if expires else 'unknown',
                "is_expired": expires < (datetime.now().timestamp() * 1000) if expires else False,
                "features": {
                    "chat": metadata.get('chat') == '1',
                    "snippets": metadata.get('sn') == '1',
                    "agent_mode": metadata.get('agent_mode') == '1',
                    "agent_auto_approval": metadata.get('agent_mode_auto_approval') == '1',
                    "mcp": metadata.get('mcp') == '1'
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
