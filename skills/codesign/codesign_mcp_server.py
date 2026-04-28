#!/usr/bin/env python3
"""
Co-Design MCP Server for OpenCode
==================================
Local MCP server that wraps Intel's Co-Design plugin API.

Authentication: Uses the unified ``credentials`` skill (intel_credentials.py).
Credentials are read from Windows Keyring service ``intel_credentials``.
Run ``python intel_credentials.py --refresh`` once to set up.

Endpoints used:
  - Login:    https://plugin-api-prod.aisg-ossp.intel.com/login
  - Products: https://plugin-api-prod.aisg-ossp.intel.com/products
  - Ask:      https://plugin-api-prod.aisg-ossp.intel.com/completions_copilot_direct
"""
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

import requests
from mcp.server.fastmcp import FastMCP

# --- Unified credentials import ---
_CRED_DIR = str(Path(__file__).resolve().parent.parent / "credentials")
if _CRED_DIR not in sys.path:
    sys.path.insert(0, _CRED_DIR)
from intel_credentials import get_credentials, get_idsid  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = "https://plugin-api-prod.aisg-ossp.intel.com"
PROXIES = {
    "http": "http://proxy-chain.intel.com:911",
    "https": "http://proxy-chain.intel.com:912",
}
TOKEN_EXPIRY_BUFFER = 300   # refresh 5 min before expiry
LOGIN_EXP_MINUTES = 240     # 4 hours token lifetime

# Shared token file -- enables cross-MCP instance sharing
SHARED_TOKEN_PATH = Path.home() / ".codesign_mcp_token.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log(msg: str) -> None:
    """Write to stderr so it doesn't interfere with MCP stdio."""
    print(f"[codesign-mcp] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Shared token (cross-MCP instance sharing)
# ---------------------------------------------------------------------------

def _read_shared_token() -> Optional[str]:
    """Read a still-valid token from the shared file."""
    try:
        if not SHARED_TOKEN_PATH.exists():
            return None
        data = json.loads(SHARED_TOKEN_PATH.read_text(encoding="utf-8"))
        token = data.get("token")
        acquired = data.get("acquired_at", 0)
        lifetime = data.get("lifetime", 0)
        if not token:
            return None
        if time.time() - acquired >= lifetime - TOKEN_EXPIRY_BUFFER:
            _log("Shared token expired, will re-authenticate")
            return None
        _log("Reusing shared token from another MCP instance")
        return token
    except (json.JSONDecodeError, OSError, KeyError):
        return None


def _write_shared_token(token: str, lifetime: float) -> None:
    """Persist token for other MCP instances to reuse."""
    try:
        data = {
            "token": token,
            "acquired_at": time.time(),
            "lifetime": lifetime,
            "pid": os.getpid(),
        }
        SHARED_TOKEN_PATH.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )
        _log("Shared token saved for cross-MCP reuse")
    except OSError as exc:
        _log(f"Warning: could not write shared token: {exc}")


# ---------------------------------------------------------------------------
# Auth orchestration
# ---------------------------------------------------------------------------

_token: Optional[str] = None
_token_acquired_at: float = 0.0
_token_lifetime: float = LOGIN_EXP_MINUTES * 60
_credentials: Optional[tuple[str, str]] = None   # (idsid, passwd)


def _login(idsid: str, passwd: str) -> str:
    """Call the Co-Design login endpoint and return a JWT token."""
    resp = requests.post(
        f"{BASE_URL}/login",
        json={"idsid": idsid, "passwd": passwd, "exp": LOGIN_EXP_MINUTES},
        proxies=PROXIES,
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed ({resp.status_code}): {resp.text[:300]}")

    data = resp.json()
    token = data.get("token")
    if not token:
        raise RuntimeError(f"No token in response: {json.dumps(data)[:300]}")
    return token


def _authenticate_on_startup() -> None:
    """Run once at startup to obtain credentials and initial token.

    Priority:
      1. Shared token file (another MCP instance already logged in)
      2. Unified credentials skill (intel_credentials keyring)
    """
    global _token, _token_acquired_at, _credentials

    # --- 1. Shared token from another instance ---
    shared = _read_shared_token()
    if shared:
        _token = shared
        _token_acquired_at = time.time()
        return

    # --- 2. Unified credential manager ---
    try:
        username, password = get_credentials()
    except Exception as exc:
        _log(f"ERROR: {exc}")
        _log("Run:  python .opencode/skill/credentials/intel_credentials.py --refresh")
        sys.exit(1)

    idsid = get_idsid(username)
    _credentials = (idsid, password)

    # Perform initial login
    _log(f"Logging in as {idsid}...")
    _token = _login(idsid, password)
    _token_acquired_at = time.time()
    _write_shared_token(_token, _token_lifetime)
    _log("Authenticated successfully")


def _ensure_token() -> str:
    """Return a valid token, refreshing if expired."""
    global _token, _token_acquired_at

    now = time.time()
    if _token and (now - _token_acquired_at) < (_token_lifetime - TOKEN_EXPIRY_BUFFER):
        return _token

    # Try shared token first (another instance may have refreshed)
    shared = _read_shared_token()
    if shared:
        _token = shared
        _token_acquired_at = now
        return _token

    # Re-login with stored credentials
    if not _credentials:
        raise RuntimeError(
            "Token expired and no stored credentials. Restart the MCP server."
        )

    _log("Token expired, refreshing...")
    _token = _login(*_credentials)
    _token_acquired_at = now
    _write_shared_token(_token, _token_lifetime)
    return _token


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _api_get(endpoint: str) -> dict:
    token = _ensure_token()
    resp = requests.get(
        f"{BASE_URL}{endpoint}",
        headers={"api-key": token},
        proxies=PROXIES,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _api_ask(question: str, project_ids: list[str], project_texts: list[str],
             session_id: Optional[str] = None) -> str:
    token = _ensure_token()
    sid = session_id or str(uuid.uuid4())

    payload = {
        "messages": [{
            "role": "user",
            "content": question,
            "runId": str(uuid.uuid4()),
            "structuredContent": {
                "userQuestion": question,
                "command": "/ask_spec",
                "context": {},
            },
        }],
        "model": "gpt-3.5-turbo",
        "max_tokens": 4096,
        "stream": True,
        "sessionId": sid,
        "sourceSelected": {
            "projects_id": project_ids,
            "projects_text": project_texts,
        },
    }

    resp = requests.post(
        f"{BASE_URL}/completions_copilot_direct",
        json=payload,
        headers={
            "api-key": token,
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        proxies=PROXIES,
        timeout=180,
        stream=True,
    )
    resp.raise_for_status()

    answer_parts = []
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        json_str = line[6:].strip()
        if json_str == "[DONE]":
            break
        try:
            chunk = json.loads(json_str)
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            content = delta.get("content", "")
            if content:
                answer_parts.append(content)
        except (json.JSONDecodeError, IndexError, KeyError):
            continue

    return "".join(answer_parts)


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "codesign",
    instructions=(
        "Co-Design MCP server for querying Intel specifications, "
        "HAS/MAS/FAS documents, tools & methodologies via the Co-Design API. "
        "Use codesign_list_projects to see available projects, then "
        "codesign_ask to query specs."
    ),
)


@mcp.tool()
def codesign_list_projects() -> str:
    """List all Co-Design projects and tools available to the user.

    Returns a JSON object with 'Specs' and 'Tools & Methodology' arrays,
    each containing {project_id, project_text} entries.
    """
    products = _api_get("/products")
    return json.dumps(products, indent=2)


@mcp.tool()
def codesign_ask(question: str, project_ids: str = "", session_id: str = "") -> str:
    """Ask Co-Design a question about Intel specs, HAS/MAS/FAS documents.

    Args:
        question: The question to ask (e.g. "How many USB ports are in NVL?")
        project_ids: Comma-separated project IDs to search (e.g. "NVL,PTL").
                     If empty, searches all available projects.
        session_id: Optional session ID for follow-up questions in same thread.

    Returns:
        The Co-Design AI agent's answer based on Intel specification documents.
    """
    products = _api_get("/products")
    specs = products.get("Specs", [])
    tools = products.get("Tools & Methodology", [])
    all_projects = specs + tools

    if project_ids.strip():
        requested = [p.strip().upper() for p in project_ids.split(",")]
        selected = [p for p in all_projects if p["project_id"].upper() in requested]
        if not selected:
            available = [p["project_id"] for p in all_projects]
            return (
                f"No matching projects found for: {project_ids}\n"
                f"Available projects: {', '.join(available)}"
            )
    else:
        selected = specs

    ids = [p["project_id"] for p in selected]
    texts = [p["project_text"] for p in selected]

    sid = session_id.strip() if session_id.strip() else None
    return _api_ask(question, ids, texts, sid)


@mcp.tool()
def codesign_ask_followup(question: str, session_id: str) -> str:
    """Ask a follow-up question in an existing Co-Design conversation.

    Args:
        question: The follow-up question.
        session_id: The session ID from a previous codesign_ask call.

    Returns:
        The Co-Design AI agent's answer with conversation context.
    """
    products = _api_get("/products")
    specs = products.get("Specs", [])
    ids = [p["project_id"] for p in specs]
    texts = [p["project_text"] for p in specs]
    return _api_ask(question, ids, texts, session_id)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    _authenticate_on_startup()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
