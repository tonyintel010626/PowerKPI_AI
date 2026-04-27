#!/usr/bin/env python3
"""
SecureWiki Authentication Manager
==================================
Thin wrapper around the unified ``credentials`` skill (intel_credentials.py).

Kept for backward-compatibility — existing scripts/docs that reference
``securewiki_auth.py --refresh`` continue to work.

Usage:
    python securewiki_auth.py --status     # Check if credentials are stored
    python securewiki_auth.py --refresh    # Re-enter password (GUI popup)
    python securewiki_auth.py --clear      # Remove stored credentials
    python securewiki_auth.py --console    # Enter password via console (no GUI)
    python securewiki_auth.py --user NAME  # Use specific username
"""

import os
import sys

# --- Unified credentials import ---
_CRED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "credentials")
if _CRED_DIR not in sys.path:
    sys.path.insert(0, _CRED_DIR)

import intel_credentials  # noqa: E402


def main():
    """Delegate all arguments to the unified credential manager CLI."""
    # Forward sys.argv to intel_credentials.main()
    return intel_credentials.main()


if __name__ == "__main__":
    sys.exit(main())
