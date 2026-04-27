#!/usr/bin/env python3
"""
MCP Forge Token Helper
Completes the AISG SSO flow for ContextForge (MCP Forge) and retrieves a JWT token.

Usage:
    python get_mcp_forge_token.py

This script:
1. Requests an SSO authorization URL from MCP Forge
2. Opens your browser for AISG SSO authentication
3. Captures the auth code via a local HTTP server
4. Exchanges the code at MCP Forge's callback endpoint
5. Extracts and prints the JWT token for use in opencode.json
"""

import hashlib
import http.server
import json
import os
import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser

import requests

MCP_FORGE_BASE = "https://mcp-forge-prod.aisg.iglb.intel.com"
SSO_PROVIDER = "aisg"
LOCAL_PORT = 19876
LOCAL_CALLBACK = f"http://localhost:{LOCAL_PORT}/callback"

# Token storage file
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".mcp_forge_token.json")


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler that captures the OAuth callback."""
    auth_code = None
    state = None
    error = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/callback":
            if "code" in params:
                CallbackHandler.auth_code = params["code"][0]
                CallbackHandler.state = params.get("state", [None])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                <html><body style="font-family: system-ui; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; background:#1a1a2e; color:#e0e0e0;">
                <div style="text-align:center; padding:40px; background:#16213e; border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.3);">
                <h1 style="color:#0f0;">&#10004; Authentication Successful</h1>
                <p>You can close this tab and return to your terminal.</p>
                </div></body></html>
                """)
            elif "error" in params:
                CallbackHandler.error = params.get("error_description", params["error"])[0]
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(f"<html><body><h1>Authentication Failed</h1><p>{CallbackHandler.error}</p></body></html>".encode())
            else:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress HTTP server logs


def get_sso_auth_url():
    """Step 1: Get the SSO authorization URL from MCP Forge."""
    url = f"{MCP_FORGE_BASE}/auth/sso/login/{SSO_PROVIDER}"
    # Use the MCP Forge callback as redirect_uri so ContextForge handles the code exchange
    callback_url = f"{MCP_FORGE_BASE}/auth/sso/callback/{SSO_PROVIDER}"
    params = {"redirect_uri": callback_url}

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["authorization_url"], data.get("state")


def exchange_code_via_forge(auth_code, state):
    """
    Step 3: Exchange the auth code by calling MCP Forge's SSO callback directly.
    This lets ContextForge do the PKCE exchange and issue its JWT.
    """
    callback_url = f"{MCP_FORGE_BASE}/auth/sso/callback/{SSO_PROVIDER}"
    params = {"code": auth_code, "state": state}

    # Create a session to capture cookies
    session = requests.Session()
    resp = session.get(callback_url, params=params, timeout=30, allow_redirects=False)

    # The callback should set a cookie and redirect to /admin
    cookies = session.cookies.get_dict()
    token = None

    # Check for JWT in cookies
    for name, value in cookies.items():
        if "token" in name.lower() or "jwt" in name.lower() or "session" in name.lower():
            token = value
            print(f"  Found cookie: {name} = {value[:50]}...")

    # Check for token in response headers
    if not token:
        auth_header = resp.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    # Check for token in redirect URL
    if not token and resp.is_redirect:
        location = resp.headers.get("Location", "")
        parsed = urllib.parse.urlparse(location)
        params = urllib.parse.parse_qs(parsed.query)
        if "token" in params:
            token = params["token"][0]
        elif "access_token" in params:
            token = params["access_token"][0]

        # Follow the redirect and check cookies again
        resp2 = session.get(f"{MCP_FORGE_BASE}{location}", timeout=30, allow_redirects=False)
        cookies2 = session.cookies.get_dict()
        for name, value in cookies2.items():
            if "token" in name.lower() or "jwt" in name.lower() or "session" in name.lower() or "auth" in name.lower():
                token = value
                print(f"  Found cookie after redirect: {name} = {value[:50]}...")

    return token, cookies, session


def get_token_with_local_redirect():
    """
    Alternative approach: Use localhost redirect, then replay the code at MCP Forge.

    Flow:
    1. Get SSO URL from MCP Forge with MCP Forge's callback as redirect_uri
    2. Modify the authorization URL to redirect to localhost instead
    3. Capture the auth code locally
    4. Replay the code at MCP Forge's callback endpoint with the original state
    """
    print("Step 1: Getting SSO authorization URL...")
    # Get the auth URL with ContextForge's callback
    forge_callback = f"{MCP_FORGE_BASE}/auth/sso/callback/{SSO_PROVIDER}"
    resp = requests.get(
        f"{MCP_FORGE_BASE}/auth/sso/login/{SSO_PROVIDER}",
        params={"redirect_uri": forge_callback},
        timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    original_auth_url = data["authorization_url"]
    original_state = data.get("state")

    print(f"  State: {original_state}")

    # Now get ANOTHER auth URL with localhost redirect (different PKCE, different state)
    resp2 = requests.get(
        f"{MCP_FORGE_BASE}/auth/sso/login/{SSO_PROVIDER}",
        params={"redirect_uri": LOCAL_CALLBACK},
        timeout=30
    )
    resp2.raise_for_status()
    data2 = resp2.json()
    local_auth_url = data2["authorization_url"]
    local_state = data2.get("state")

    print(f"  Local callback auth URL ready")

    # Start local server
    print(f"\nStep 2: Starting local HTTP server on port {LOCAL_PORT}...")
    server = http.server.HTTPServer(("localhost", LOCAL_PORT), CallbackHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # Open browser with localhost redirect URL
    print(f"\nStep 3: Opening browser for AISG SSO authentication...")
    print(f"  If the browser doesn't open, visit this URL manually:")
    print(f"  {local_auth_url}\n")
    webbrowser.open(local_auth_url)

    # Wait for callback
    print("Waiting for authentication callback...")
    timeout = 120
    start = time.time()
    while CallbackHandler.auth_code is None and CallbackHandler.error is None:
        if time.time() - start > timeout:
            print("\nTimeout waiting for authentication callback.")
            server.shutdown()
            return None
        time.sleep(0.5)

    server.shutdown()

    if CallbackHandler.error:
        print(f"\nAuthentication error: {CallbackHandler.error}")
        return None

    auth_code = CallbackHandler.auth_code
    callback_state = CallbackHandler.state
    print(f"\nStep 4: Received auth code: {auth_code[:20]}...")

    # Now replay the code at MCP Forge's callback with the LOCAL state
    # MCP Forge stored the PKCE verifier associated with this state
    print("\nStep 5: Exchanging code at MCP Forge callback...")
    token, cookies, session = exchange_code_via_forge(auth_code, callback_state)

    if token:
        return token

    # If no token in cookies, try to access a protected endpoint with the session
    print("\nStep 6: Trying to access protected endpoints with session cookies...")
    all_cookies = session.cookies.get_dict()
    print(f"  Session cookies: {list(all_cookies.keys())}")

    # Try /servers with cookies
    resp3 = session.get(f"{MCP_FORGE_BASE}/servers", timeout=30)
    print(f"  /servers response: {resp3.status_code}")
    if resp3.status_code == 200:
        print("  Session is valid! Extracting token from cookies...")
        # The session works - extract all cookies as potential tokens
        for name, value in all_cookies.items():
            print(f"    Cookie {name}: {value[:80]}...")
        return all_cookies

    return None


def direct_sso_approach():
    """
    Direct approach: Open the MCP Forge login page, complete SSO,
    then extract the token from the resulting session.
    """
    print("=" * 60)
    print("MCP Forge Token Helper - Direct SSO Approach")
    print("=" * 60)

    # Get SSO URL with MCP Forge's callback
    forge_callback = f"{MCP_FORGE_BASE}/auth/sso/callback/{SSO_PROVIDER}"
    print(f"\nStep 1: Getting SSO URL...")
    resp = requests.get(
        f"{MCP_FORGE_BASE}/auth/sso/login/{SSO_PROVIDER}",
        params={"redirect_uri": forge_callback},
        timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    auth_url = data["authorization_url"]
    state = data.get("state")

    print(f"Step 2: Opening browser for authentication...")
    print(f"\n  URL: {auth_url}\n")
    webbrowser.open(auth_url)

    print("Step 3: After you complete SSO in the browser, the MCP Forge admin")
    print("  dashboard will open. You need to extract the auth token.")
    print()
    print("  Option A: Open browser DevTools (F12) > Application > Cookies")
    print("            Look for a cookie named 'token', 'jwt', 'session', or 'access_token'")
    print()
    print("  Option B: Open browser DevTools (F12) > Console, and run:")
    print("            document.cookie")
    print()
    print("  Option C: Open browser DevTools (F12) > Network tab,")
    print("            navigate to /servers, and check the Authorization header")
    print()

    token = input("Paste the token value here (or press Enter to skip): ").strip()
    if token:
        save_token(token)
        return token

    return None


def save_token(token):
    """Save token to file."""
    data = {
        "token": token,
        "timestamp": time.time(),
        "server": MCP_FORGE_BASE
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nToken saved to: {TOKEN_FILE}")


def load_token():
    """Load saved token."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            data = json.load(f)
        return data.get("token")
    return None


def test_token(token):
    """Test if a token works with the MCP Forge API."""
    print(f"\nTesting token against MCP Forge...")
    headers = {"Authorization": f"Bearer {token}"}

    # Test /servers endpoint
    resp = requests.get(f"{MCP_FORGE_BASE}/servers", headers=headers, timeout=30)
    print(f"  /servers: {resp.status_code}")
    if resp.status_code == 200:
        print(f"  Response: {resp.text[:200]}")
        return True

    # Test the MCP endpoint
    resp2 = requests.post(
        f"{MCP_FORGE_BASE}/servers/Co-Design-MCP/mcp",
        headers={**headers, "Content-Type": "application/json"},
        json={"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "opencode", "version": "1.3.17"}}, "id": 1},
        timeout=30
    )
    print(f"  /servers/Co-Design-MCP/mcp: {resp2.status_code}")
    if resp2.status_code == 200:
        print(f"  Response: {resp2.text[:200]}")
        return True

    print(f"  Response body: {resp2.text[:200]}")
    return False


def main():
    print("=" * 60)
    print("MCP Forge Token Helper for OpenCode")
    print("=" * 60)

    # Check for existing token
    existing_token = load_token()
    if existing_token:
        print(f"\nFound existing token. Testing...")
        if test_token(existing_token):
            print("\nExisting token is valid!")
            print(f"\nToken: {existing_token[:80]}...")
            print(f"\nAdd this to your opencode.json:")
            print(json.dumps({
                "codesign": {
                    "type": "remote",
                    "url": f"{MCP_FORGE_BASE}/servers/Co-Design-MCP/mcp",
                    "oauth": False,
                    "headers": {
                        "Authorization": f"Bearer {existing_token}"
                    },
                    "enabled": True
                }
            }, indent=2))
            return
        else:
            print("Existing token is expired or invalid. Getting a new one...")

    # Try the local redirect approach first
    print("\n--- Attempting automated SSO flow ---\n")
    result = get_token_with_local_redirect()

    if result and isinstance(result, str):
        print(f"\nGot token!")
        save_token(result)
        if test_token(result):
            print("\nToken verified successfully!")
        print(f"\nAdd this to your opencode.json:")
        print(json.dumps({
            "codesign": {
                "type": "remote",
                "url": f"{MCP_FORGE_BASE}/servers/Co-Design-MCP/mcp",
                "oauth": False,
                "headers": {
                    "Authorization": f"Bearer {result}"
                },
                "enabled": True
            }
        }, indent=2))
    elif result and isinstance(result, dict):
        print(f"\nGot session cookies: {list(result.keys())}")
        print("These might work as auth. Trying each...")
        for name, value in result.items():
            if test_token(value):
                print(f"\nCookie '{name}' works as bearer token!")
                save_token(value)
                return
        print("\nCookies didn't work as bearer tokens.")
        print("Falling back to manual approach...")
        direct_sso_approach()
    else:
        print("\nAutomated approach failed. Falling back to manual approach...")
        direct_sso_approach()


if __name__ == "__main__":
    main()
