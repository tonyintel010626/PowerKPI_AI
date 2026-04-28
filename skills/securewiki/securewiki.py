#!/usr/bin/env python3
"""
SecureWiki - Intel Confluence Wiki REST API Client

Securely access, read, create, and update pages on Intel's Enterprise Confluence Wiki.
Credentials are stored in Windows Keyring - only enter password once per machine.

Usage:
    python securewiki.py get <page_id>                              # Read a page
    python securewiki.py create <space_key> "<title>" "<body>" [parent_id]  # Create page
    python securewiki.py update <page_id> "<new_body>"              # Update page
    python securewiki.py list <space_key> [limit]                   # List pages in space
    python securewiki.py space <space_key>                          # Get space info
    python securewiki.py delete <page_id>                           # Delete a page
"""

import os
import sys
import json
import argparse

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("ERROR: 'requests' package not installed. Run: pip install requests")
    sys.exit(1)

# --- Unified credentials import ---
_CRED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "credentials")
if _CRED_DIR not in sys.path:
    sys.path.insert(0, _CRED_DIR)
from intel_credentials import get_credentials, ensure_credentials  # noqa: E402

# Constants
BASE_URL = "https://wiki.ith.intel.com"
API_BASE = f"{BASE_URL}/rest/api"


def get_default_username():
    """Get the current Windows username as default."""
    try:
        return os.getlogin()
    except OSError:
        return os.environ.get('USERNAME', os.environ.get('USER', 'unknown'))


def get_credentials_for_wiki(username=None):
    """Get credentials from unified credential manager.

    Uses the central ``intel_credentials`` skill.
    If credentials are not stored, prompts the user (GUI then CLI fallback).
    """
    try:
        u, pw = get_credentials(username)
        print(f"[INFO] Using stored credentials for '{u}'")
        return u, pw
    except Exception:
        print("[INFO] No stored credentials found — prompting…")
        u, pw = ensure_credentials(username)
        return u, pw


class SecureWiki:
    """Intel Confluence Wiki REST API client with secure credential storage."""
    
    def __init__(self, username=None):
        self.username, self.password = get_credentials_for_wiki(username)
        self.auth = (self.username, self.password)
        self.headers = {"Content-Type": "application/json"}
    
    def _request(self, method, endpoint, **kwargs):
        """Make authenticated request to wiki API."""
        url = f"{API_BASE}/{endpoint}"
        kwargs.setdefault('auth', self.auth)
        kwargs.setdefault('verify', False)
        kwargs.setdefault('timeout', 30)
        
        if method.upper() in ('POST', 'PUT') and 'json' in kwargs:
            kwargs.setdefault('headers', self.headers)
        
        resp = requests.request(method, url, **kwargs)
        
        if resp.status_code == 401:
            print("[ERROR] Authentication failed (401 Unauthorized)")
            print("[TIP] Your password may have changed. Run: python securewiki_auth.py --refresh")
            sys.exit(1)
        
        resp.raise_for_status()
        return resp.json() if resp.content else None
    
    def get_page(self, page_id, expand="body.storage,version,space"):
        """Get a page by ID."""
        data = self._request('GET', f"content/{page_id}", params={"expand": expand})
        return {
            "id": data["id"],
            "title": data["title"],
            "space": data.get("space", {}).get("key", "unknown"),
            "version": data["version"]["number"],
            "body": data.get("body", {}).get("storage", {}).get("value", "")[:500] + "..."
        }
    
    def create_page(self, space_key, title, html_body, parent_id=None):
        """Create a new page in a space."""
        payload = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": html_body,
                    "representation": "storage"
                }
            }
        }
        if parent_id:
            payload["ancestors"] = [{"id": str(parent_id)}]
        
        data = self._request('POST', "content", json=payload)
        return {
            "id": data["id"],
            "title": data["title"],
            "space": space_key,
            "url": f"{BASE_URL}/pages/viewpage.action?pageId={data['id']}"
        }
    
    def update_page(self, page_id, new_html_body):
        """Update an existing page."""
        # Get current page to get version and title
        current = self._request('GET', f"content/{page_id}", params={"expand": "version,space"})
        
        payload = {
            "id": page_id,
            "type": "page",
            "title": current["title"],
            "space": {"key": current["space"]["key"]},
            "body": {
                "storage": {
                    "value": new_html_body,
                    "representation": "storage"
                }
            },
            "version": {
                "number": current["version"]["number"] + 1,
                "minorEdit": True
            }
        }
        
        data = self._request('PUT', f"content/{page_id}", json=payload)
        return {
            "id": data["id"],
            "title": data["title"],
            "version": data["version"]["number"],
            "url": f"{BASE_URL}/pages/viewpage.action?pageId={data['id']}"
        }
    
    def delete_page(self, page_id):
        """Delete a page by ID."""
        self._request('DELETE', f"content/{page_id}")
        return {"deleted": True, "page_id": page_id}
    
    def list_pages(self, space_key, limit=25):
        """List pages in a space."""
        data = self._request('GET', "content", params={
            "spaceKey": space_key,
            "type": "page",
            "limit": limit,
            "expand": "version"
        })
        return [{
            "id": p["id"],
            "title": p["title"],
            "version": p["version"]["number"]
        } for p in data.get("results", [])]
    
    def get_space(self, space_key):
        """Get space information."""
        data = self._request('GET', f"space/{space_key}")
        return {
            "key": data["key"],
            "name": data["name"],
            "type": data["type"],
            "url": f"{BASE_URL}/spaces/{space_key}"
        }

    def search_pages(self, query, spaces=None, limit=10):
        """Search for pages using CQL (Confluence Query Language).
        
        Args:
            query: Search text (will be wrapped in CQL text search)
            spaces: Comma-separated space keys to search in (e.g., "fvcommon,DebugEncyclopedia")
            limit: Max results to return (default 10)
        
        Returns:
            Dict with query, cql, total, returned, and list of matching pages
        """
        # Build CQL query
        cql_parts = ['type = "page"']
        
        if spaces:
            space_list = [s.strip() for s in spaces.split(',')]
            if len(space_list) == 1:
                cql_parts.append(f'space = "{space_list[0]}"')
            else:
                space_clause = ' OR '.join(f'space = "{s}"' for s in space_list)
                cql_parts.append(f'({space_clause})')
        
        cql_parts.append(f'text ~ "{query}"')
        cql = ' AND '.join(cql_parts)
        
        data = self._request('GET', 'content/search', params={
            'cql': cql,
            'limit': limit,
            'expand': 'space,version'
        })
        
        results = []
        for page in data.get('results', []):
            results.append({
                'id': page['id'],
                'title': page['title'],
                'space': page.get('space', {}).get('key', 'unknown'),
                'url': f"{BASE_URL}/pages/viewpage.action?pageId={page['id']}",
                'excerpt': page.get('excerpt', '').strip()[:300]
            })
        
        return {
            'query': query,
            'cql': cql,
            'total': data.get('totalSize', len(results)),
            'returned': len(results),
            'results': results
        }

    def read_page(self, page_id):
        """Read full page content (no truncation, unlike get_page).
        
        Returns page with complete body text for knowledge extraction.
        HTML tags are stripped to return clean plain text.
        """
        data = self._request('GET', f"content/{page_id}", params={
            "expand": "body.storage,version,space"
        })
        
        body_html = data.get("body", {}).get("storage", {}).get("value", "")
        
        # Strip HTML tags for cleaner text output
        import re
        body_text = re.sub(r'<[^>]+>', ' ', body_html)
        body_text = re.sub(r'\s+', ' ', body_text).strip()
        
        return {
            "id": data["id"],
            "title": data["title"],
            "space": data.get("space", {}).get("key", "unknown"),
            "version": data["version"]["number"],
            "url": f"{BASE_URL}/pages/viewpage.action?pageId={data['id']}",
            "body_text": body_text,
            "body_length": len(body_text)
        }


def main():
    parser = argparse.ArgumentParser(
        description="SecureWiki - Intel Confluence Wiki REST API Client"
    )
    parser.add_argument('action', choices=['get', 'create', 'update', 'delete', 'list', 'space', 'search', 'read'],
                        help='Action to perform')
    parser.add_argument('args', nargs='*', help='Action arguments')
    parser.add_argument('--user', type=str, default=None,
                        help=f'Username (default: {get_default_username()})')
    parser.add_argument('--json', action='store_true',
                        help='Output as JSON')
    parser.add_argument('--spaces', type=str, default=None,
                        help='Comma-separated space keys to search (e.g., fvcommon,DebugEncyclopedia)')
    parser.add_argument('--limit', type=int, default=10,
                        help='Max results for search (default: 10)')
    
    args = parser.parse_args()
    
    wiki = SecureWiki(args.user)
    result = None
    
    try:
        if args.action == 'get':
            if not args.args:
                print("Usage: securewiki.py get <page_id>")
                sys.exit(1)
            result = wiki.get_page(args.args[0])
            
        elif args.action == 'create':
            if len(args.args) < 3:
                print("Usage: securewiki.py create <space_key> <title> <html_body> [parent_id]")
                sys.exit(1)
            parent = args.args[3] if len(args.args) > 3 else None
            result = wiki.create_page(args.args[0], args.args[1], args.args[2], parent)
            
        elif args.action == 'update':
            if len(args.args) < 2:
                print("Usage: securewiki.py update <page_id> <new_html_body>")
                sys.exit(1)
            result = wiki.update_page(args.args[0], args.args[1])
            
        elif args.action == 'delete':
            if not args.args:
                print("Usage: securewiki.py delete <page_id>")
                sys.exit(1)
            result = wiki.delete_page(args.args[0])
            
        elif args.action == 'list':
            if not args.args:
                print("Usage: securewiki.py list <space_key> [limit]")
                sys.exit(1)
            limit = int(args.args[1]) if len(args.args) > 1 else 25
            result = wiki.list_pages(args.args[0], limit)
            
        elif args.action == 'space':
            if not args.args:
                print("Usage: securewiki.py space <space_key>")
                sys.exit(1)
            result = wiki.get_space(args.args[0])

        elif args.action == 'search':
            if not args.args:
                print("Usage: securewiki.py search <query> [--spaces fvcommon,DebugEncyclopedia] [--limit 10]")
                sys.exit(1)
            query = ' '.join(args.args)
            result = wiki.search_pages(query, spaces=args.spaces, limit=args.limit)

        elif args.action == 'read':
            if not args.args:
                print("Usage: securewiki.py read <page_id>")
                sys.exit(1)
            result = wiki.read_page(args.args[0])
        
        # Output result
        print(json.dumps(result, indent=2))
        
    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] HTTP {e.response.status_code}: {e.response.text[:200]}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
