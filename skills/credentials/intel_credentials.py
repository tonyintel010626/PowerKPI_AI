#!/usr/bin/env python3
"""
Intel Unified Credential Manager
=================================
Single source of truth for Intel intranet credentials (IDSID + password).
Stored securely in Windows Credential Manager via the `keyring` library.

One-time setup:
    python intel_credentials.py --refresh      # GUI popup (default)
    python intel_credentials.py --refresh --console  # CLI prompt

After first setup, all skills retrieve credentials silently:

    from intel_credentials import get_credentials
    username, password = get_credentials()

API:
    get_credentials(username=None) -> (str, str)
        Returns (username, password).  Raises CredentialError if unavailable.

    get_domain() -> str
        Returns the Windows domain (e.g. "gar") in lowercase.

    get_idsid() -> str
        Returns "domain\\username" (e.g. "gar\\aabdulmu").

    ensure_credentials(username=None) -> (str, str)
        Like get_credentials, but silently prompts GUI if missing.

CLI:
    python intel_credentials.py --status       # check stored state
    python intel_credentials.py --refresh      # re-enter password (GUI)
    python intel_credentials.py --refresh --console  # re-enter via CLI
    python intel_credentials.py --clear        # delete stored creds
    python intel_credentials.py --test         # test against Confluence
    python intel_credentials.py --user <idsid> # use a specific username
"""

import argparse
import getpass
import json
import os
import sys
from typing import Optional, Tuple

try:
    import keyring
except ImportError:
    print("ERROR: 'keyring' package not installed. Run: pip install keyring", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KEYRING_SERVICE = "intel_credentials"
"""Canonical keyring service name.  All skills must use this single name."""

# Legacy service names — checked during migration only
_LEGACY_SERVICES = [
    "intel_confluence_wiki",   # securewiki
    "codesign_mcp",            # codesign MCP server
    "securewiki",              # thc_wiki_verify alternate
    "confluence",              # nvu_wiki_verify
    "wiki.ith.intel.com",      # thc_wiki_verify alternate
    "onebkc",                  # OneBKC (stores username as value, non-standard)
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CredentialError(RuntimeError):
    """Raised when credentials cannot be obtained."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _log(msg: str) -> None:
    print(f"[intel-creds] {msg}", file=sys.stderr, flush=True)


def _default_username() -> str:
    """Return current OS username (IDSID without domain)."""
    try:
        return os.getlogin()
    except OSError:
        return os.environ.get("USERNAME", os.environ.get("USER", "unknown"))


def _default_domain() -> str:
    """Return Windows domain in lowercase (e.g. 'gar')."""
    return os.environ.get("USERDOMAIN", "gar").lower()


# ---------------------------------------------------------------------------
# Core keyring operations
# ---------------------------------------------------------------------------

def _get_stored_password(username: str) -> Optional[str]:
    """Read password from the canonical keyring service."""
    return keyring.get_password(KEYRING_SERVICE, username)


def _set_stored_password(username: str, password: str) -> None:
    """Write password to the canonical keyring service."""
    keyring.set_password(KEYRING_SERVICE, username, password)


def _delete_stored_password(username: str) -> bool:
    """Delete password from keyring.  Returns True if deleted."""
    try:
        keyring.delete_password(KEYRING_SERVICE, username)
        return True
    except keyring.errors.PasswordDeleteError:
        return False


def _migrate_legacy(username: str) -> Optional[str]:
    """Check legacy keyring services and migrate if found.

    If a password is found under a legacy service name, it is copied
    to the canonical service and the legacy entry is left intact
    (so existing scripts still work during transition).
    """
    for svc in _LEGACY_SERVICES:
        pw = keyring.get_password(svc, username)
        if pw:
            _log(f"Migrating credentials from legacy service '{svc}'")
            _set_stored_password(username, pw)
            return pw
    return None


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

def _prompt_gui(username: str) -> Optional[str]:
    """Pop a tkinter dialog for the password.  Returns password or None."""
    try:
        import tkinter as tk
        from tkinter import ttk

        result = {}
        root = tk.Tk()
        root.title("Intel Credentials")
        root.resizable(False, False)
        root.attributes("-topmost", True)

        w, h = 400, 220
        x = (root.winfo_screenwidth() - w) // 2
        y = (root.winfo_screenheight() - h) // 2
        root.geometry(f"{w}x{h}+{x}+{y}")

        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Intel Credential Manager",
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=(0, 4))

        ttk.Label(
            frame,
            text="Stored securely in Windows Credential Manager",
            foreground="gray",
        ).grid(row=1, column=0, columnspan=2, pady=(0, 12))

        ttk.Label(frame, text="IDSID:").grid(row=2, column=0, sticky="e", padx=(0, 8))
        user_var = tk.StringVar(value=username)
        user_entry = ttk.Entry(frame, textvariable=user_var, width=28)
        user_entry.grid(row=2, column=1, sticky="w")

        ttk.Label(frame, text="Password:").grid(row=3, column=0, sticky="e", padx=(0, 8), pady=6)
        pw_var = tk.StringVar()
        pw_entry = ttk.Entry(frame, textvariable=pw_var, show="*", width=28)
        pw_entry.grid(row=3, column=1, sticky="w", pady=6)
        pw_entry.focus_set()

        def on_ok(event=None):
            u = user_var.get().strip()
            p = pw_var.get()
            if u and p:
                result["username"] = u
                result["password"] = p
                root.destroy()

        def on_cancel(event=None):
            root.destroy()

        btn = ttk.Frame(frame)
        btn.grid(row=4, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(btn, text="Save", command=on_ok).pack(side="left", padx=4)
        ttk.Button(btn, text="Cancel", command=on_cancel).pack(side="left", padx=4)

        root.bind("<Return>", on_ok)
        root.bind("<Escape>", on_cancel)
        root.protocol("WM_DELETE_WINDOW", on_cancel)
        root.mainloop()

        if result:
            # Allow the user to override IDSID from the dialog
            if result["username"] != username:
                username = result["username"]
            _set_stored_password(username, result["password"])
            _log(f"Credentials stored for '{username}'")
            return result["password"]
        return None

    except Exception as exc:
        _log(f"GUI prompt failed: {exc}")
        return None


def _prompt_console(username: str) -> Optional[str]:
    """Prompt for password via CLI getpass."""
    try:
        override = input(f"  Username [{username}]: ").strip()
        if override:
            username = override
        pw = getpass.getpass(f"  Password for '{username}': ")
        if pw:
            _set_stored_password(username, pw)
            _log(f"Credentials stored for '{username}'")
            return pw
        return None
    except (EOFError, KeyboardInterrupt):
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_domain() -> str:
    """Return the Windows domain in lowercase (e.g. ``'gar'``)."""
    return _default_domain()


def get_idsid(username: Optional[str] = None) -> str:
    """Return ``domain\\username`` (e.g. ``'gar\\aabdulmu'``)."""
    u = username or _default_username()
    return f"{_default_domain()}\\{u}"


def get_credentials(username: Optional[str] = None) -> Tuple[str, str]:
    """Return ``(username, password)`` from keyring.

    Resolution order:
      1. Canonical service (``intel_credentials``)
      2. Legacy services (auto-migrate on first hit)

    Raises ``CredentialError`` if no credentials are found.
    """
    u = username or _default_username()

    # 1. Canonical
    pw = _get_stored_password(u)
    if pw:
        return u, pw

    # 2. Legacy migration
    pw = _migrate_legacy(u)
    if pw:
        return u, pw

    raise CredentialError(
        f"No Intel credentials found for '{u}'.\n"
        f"Run:  python intel_credentials.py --refresh"
    )


def ensure_credentials(username: Optional[str] = None) -> Tuple[str, str]:
    """Like ``get_credentials`` but prompts (GUI) if missing."""
    try:
        return get_credentials(username)
    except CredentialError:
        u = username or _default_username()
        _log(f"No stored credentials for '{u}' — prompting…")
        pw = _prompt_gui(u)
        if pw is None:
            pw = _prompt_console(u)
        if pw:
            return u, pw
        raise CredentialError("Credential prompt cancelled by user.")


def clear_credentials(username: Optional[str] = None) -> None:
    """Delete stored credentials for *username*."""
    u = username or _default_username()
    if _delete_stored_password(u):
        _log(f"Credentials cleared for '{u}'")
    else:
        _log(f"No credentials found for '{u}'")


def status(username: Optional[str] = None) -> dict:
    """Return a dict describing stored credential state."""
    u = username or _default_username()
    pw = _get_stored_password(u)

    info = {
        "service": KEYRING_SERVICE,
        "username": u,
        "domain": _default_domain(),
        "idsid": get_idsid(u),
        "stored": pw is not None,
        "password_length": len(pw) if pw else 0,
    }

    # Check legacy services
    legacy_found = []
    for svc in _LEGACY_SERVICES:
        if keyring.get_password(svc, u):
            legacy_found.append(svc)
    info["legacy_services"] = legacy_found

    return info


# ---------------------------------------------------------------------------
# Self-test: validate credentials against Intel Confluence
# ---------------------------------------------------------------------------

def _test_confluence(username: str, password: str) -> bool:
    """Quick connectivity test against wiki.ith.intel.com."""
    try:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        resp = requests.get(
            "https://wiki.ith.intel.com/rest/api/content",
            auth=(username, password),
            verify=False,
            timeout=10,
        )
        if resp.status_code == 200:
            _log("Connection test PASSED (Confluence 200 OK)")
            return True
        elif resp.status_code == 401:
            _log("Connection test FAILED (401 Unauthorized)")
            return False
        else:
            _log(f"Connection test returned HTTP {resp.status_code}")
            return False
    except ImportError:
        _log("'requests' not installed — cannot test connection")
        return False
    except Exception as exc:
        _log(f"Connection test error: {exc}")
        return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Intel Unified Credential Manager",
    )
    parser.add_argument("--status", action="store_true", help="Show stored credential status")
    parser.add_argument("--refresh", action="store_true", help="Re-enter password (GUI popup)")
    parser.add_argument("--clear", action="store_true", help="Delete stored credentials")
    parser.add_argument("--console", action="store_true", help="Use console input instead of GUI")
    parser.add_argument("--test", action="store_true", help="Test credentials against Confluence")
    parser.add_argument("--user", type=str, default=None, help="Override username")
    parser.add_argument("--json", action="store_true", help="Output status as JSON")

    args = parser.parse_args()
    username = args.user or _default_username()

    # --clear
    if args.clear:
        clear_credentials(username)
        return 0

    # --refresh
    if args.refresh:
        _log(f"Refreshing credentials for '{username}'…")
        if args.console:
            pw = _prompt_console(username)
        else:
            pw = _prompt_gui(username)
            if pw is None:
                pw = _prompt_console(username)
        if not pw:
            _log("No password entered.")
            return 1
        if args.test:
            _test_confluence(username, pw)
        return 0

    # --test (standalone)
    if args.test:
        try:
            u, pw = get_credentials(username)
            ok = _test_confluence(u, pw)
            return 0 if ok else 1
        except CredentialError as e:
            _log(str(e))
            return 1

    # default: --status
    info = status(username)
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print("=" * 60)
        print("INTEL CREDENTIAL STATUS")
        print("=" * 60)
        print(f"  Service:   {info['service']}")
        print(f"  Username:  {info['username']}")
        print(f"  Domain:    {info['domain']}")
        print(f"  IDSID:     {info['idsid']}")
        if info["stored"]:
            stars = "*" * min(info["password_length"], 8)
            print(f"  Status:    STORED ({stars}, {info['password_length']} chars)")
        else:
            print(f"  Status:    NOT FOUND")
            print(f"  Action:    Run with --refresh to enter password")
        if info["legacy_services"]:
            print(f"  Legacy:    {', '.join(info['legacy_services'])}")
        print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
