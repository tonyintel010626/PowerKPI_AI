"""
Geni Authentication Manager

This module provides authentication services for Geni API, including:
- MSAL-based user authentication
- Axon token retrieval (for Axon Assistant focus mode)
- IBI token retrieval (for HSD Assistant focus mode)
- Secure credential storage using unified intel_credentials skill
- CLI interface for credential management
"""

import msal
import requests
from requests_kerberos import HTTPKerberosAuth, OPTIONAL
from typing import Optional, Dict, Any
import keyring
import argparse
import sys
import getpass
import tkinter as tk
from tkinter import ttk, messagebox
import os
import subprocess
from pathlib import Path

# --- Unified credentials import ---
_CRED_DIR = str(Path(__file__).resolve().parent.parent / "credentials")
if _CRED_DIR not in sys.path:
    sys.path.insert(0, _CRED_DIR)
try:
    from intel_credentials import get_credentials as _get_intel_creds
except ImportError:
    _get_intel_creds = None


class CredentialDialog:
    """GUI dialog for credential input."""
    
    def __init__(self, parent=None):
        """Initialize the credential dialog."""
        self.result = None
        self.root = tk.Tk() if parent is None else tk.Toplevel(parent)
        self.root.title("GENI Authentication")
        self.root.geometry("400x200")
        self.root.resizable(False, False)
        
        # Center the window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.root.winfo_screenheight() // 2) - (200 // 2)
        self.root.geometry(f"400x200+{x}+{y}")
        
        self._create_widgets()
        
        # Make dialog modal
        self.root.transient(parent)
        self.root.grab_set()
        
    def _create_widgets(self):
        """Create dialog widgets."""
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Enter Intel Credentials", 
                               font=('Segoe UI', 12, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Username
        ttk.Label(main_frame, text="Intel Email:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.username_entry = ttk.Entry(main_frame, width=30)
        self.username_entry.grid(row=1, column=1, pady=5, padx=(10, 0))
        self.username_entry.focus()
        
        # Password
        ttk.Label(main_frame, text="Password:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(main_frame, width=30, show="●")
        self.password_entry.grid(row=2, column=1, pady=5, padx=(10, 0))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(20, 0))
        
        # OK button
        ok_button = ttk.Button(button_frame, text="OK", command=self._on_ok, width=10)
        ok_button.grid(row=0, column=0, padx=5)
        
        # Cancel button
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self._on_cancel, width=10)
        cancel_button.grid(row=0, column=1, padx=5)
        
        # Bind Enter key to OK
        self.root.bind('<Return>', lambda e: self._on_ok())
        self.root.bind('<Escape>', lambda e: self._on_cancel())
        
    def _on_ok(self):
        """Handle OK button click."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username:
            messagebox.showerror("Error", "Username cannot be empty", parent=self.root)
            self.username_entry.focus()
            return
        
        if not password:
            messagebox.showerror("Error", "Password cannot be empty", parent=self.root)
            self.password_entry.focus()
            return
        
        self.result = (username, password)
        self.root.destroy()
        
    def _on_cancel(self):
        """Handle Cancel button click."""
        self.result = None
        self.root.destroy()
        
    def show(self):
        """Show the dialog and return the result."""
        self.root.wait_window()
        return self.result


class GeniAuthManager:
    """Manages authentication for Geni API and related services."""
    
    # Default configuration
    CLIENT_ID = "8a2ecaf5-fb85-4534-81aa-2df3e7f24907"
    TENANT_ID = "46c98d88-e344-4ed4-8496-4ed7712e255d"
    AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
    SCOPE = ['api://8a2ecaf5-fb85-4534-81aa-2df3e7f24907/API.Read']
    
    AXON_BEARER_URL = "https://axon.intel.com/api/v1/token"
    IBI_BEARER_URL = "https://ibi-daas-api.intel.com/login"
    
    # Keyring service name
    KEYRING_SERVICE = "geni_auth_manager"
    KEYRING_USERNAME_KEY = "username"
    KEYRING_PASSWORD_KEY = "password"
    
    # Environment variable names for token storage
    ENV_ACCESS_TOKEN = "GENI_ACCESS_TOKEN"
    ENV_AXON_TOKEN = "GENI_AXON_TOKEN"
    ENV_IBI_TOKEN = "GENI_IBI_TOKEN"
    
    def __init__(self, username: str = "", password: str = "", 
                 client_id: Optional[str] = None, 
                 tenant_id: Optional[str] = None,
                 use_stored_credentials: bool = True):
        """
        Initialize the Geni Authentication Manager.
        
        Args:
            username: Intel email address for authentication
            password: User password for authentication
            client_id: Optional custom client ID (uses default if not provided)
            tenant_id: Optional custom tenant ID (uses default if not provided)
            use_stored_credentials: If True, attempt to load credentials from keyring
        """
        self.client_id = client_id or self.CLIENT_ID
        self.tenant_id = tenant_id or self.TENANT_ID
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        
        # Load credentials from keyring if requested and not provided
        if use_stored_credentials and not username:
            username, password = self._load_credentials()
        
        self.username = username
        self.password = password
        
        # Cached tokens - load from environment if available
        self._access_token: Optional[str] = os.getenv(self.ENV_ACCESS_TOKEN)
        self._axon_token: Optional[str] = os.getenv(self.ENV_AXON_TOKEN)
        self._ibi_token: Optional[str] = os.getenv(self.ENV_IBI_TOKEN)
    
    def _set_env_var(self, var_name: str, value: str) -> bool:
        """
        Set environment variable persistently using setx command.
        
        Args:
            var_name: Name of the environment variable
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use setx for persistent storage
            result = subprocess.run(
                ['setx', var_name, value],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Also set in current process environment
            os.environ[var_name] = value
            
            return result.returncode == 0
        except Exception as e:
            print(f"Warning: Failed to set environment variable {var_name}: {e}")
            # Fallback to process-only environment variable
            os.environ[var_name] = value
            return False
    
    def _delete_env_var(self, var_name: str) -> bool:
        """
        Delete environment variable using reg command.
        
        Args:
            var_name: Name of the environment variable to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete from registry for persistent removal
            subprocess.run(
                ['reg', 'delete', 'HKCU\\Environment', '/F', '/V', var_name],
                capture_output=True,
                timeout=10
            )
            
            # Also remove from current process
            if var_name in os.environ:
                del os.environ[var_name]
            
            return True
        except Exception as e:
            print(f"Warning: Failed to delete environment variable {var_name}: {e}")
            if var_name in os.environ:
                del os.environ[var_name]
            return False
    
    def _load_credentials(self) -> tuple:
        """
        Load credentials from unified intel_credentials, then fall back to GENI keyring.
        
        Returns:
            Tuple of (username, password)
        """
        # Try unified credential manager first
        if _get_intel_creds is not None:
            try:
                username, password = _get_intel_creds()
                if username and password:
                    # GENI needs email format — append @intel.com if bare IDSID
                    if "@" not in username:
                        username = f"{username}@intel.com"
                    return username, password
            except Exception:
                pass

        # Fall back to GENI-specific keyring (legacy)
        try:
            username = keyring.get_password(self.KEYRING_SERVICE, self.KEYRING_USERNAME_KEY)
            password = keyring.get_password(self.KEYRING_SERVICE, self.KEYRING_PASSWORD_KEY) if username else None
            return username or "", password or ""
        except Exception as e:
            print(f"Warning: Failed to load credentials from keyring: {e}")
            return "", ""
    
    def _save_credentials(self) -> bool:
        """
        Save credentials to keyring.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.username:
                keyring.set_password(self.KEYRING_SERVICE, self.KEYRING_USERNAME_KEY, self.username)
            if self.password:
                keyring.set_password(self.KEYRING_SERVICE, self.KEYRING_PASSWORD_KEY, self.password)
            return True
        except Exception as e:
            print(f"Error: Failed to save credentials to keyring: {e}")
            return False
    
    def _delete_credentials(self) -> bool:
        """
        Delete credentials from keyring.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            try:
                keyring.delete_password(self.KEYRING_SERVICE, self.KEYRING_USERNAME_KEY)
            except keyring.errors.PasswordDeleteError:
                pass
            try:
                keyring.delete_password(self.KEYRING_SERVICE, self.KEYRING_PASSWORD_KEY)
            except keyring.errors.PasswordDeleteError:
                pass
            return True
        except Exception as e:
            print(f"Error: Failed to delete credentials from keyring: {e}")
            return False
    
    def prompt_for_credentials(self) -> bool:
        """
        Prompt user for credentials using GUI dialog and save to keyring.
        
        Returns:
            True if credentials were provided and saved, False otherwise
        """
        dialog = CredentialDialog()
        result = dialog.show()
        
        if result is None:
            print("Credential input cancelled")
            return False
        
        username, password = result
        self.username = username
        self.password = password
        
        if self._save_credentials():
            print("✓ Credentials saved securely")
            return True
        return False
    
    def check_credentials_status(self) -> Dict[str, Any]:
        """
        Check if credentials are stored and valid.
        
        Returns:
            Dictionary with status information
        """
        username, password = self._load_credentials()
        has_credentials = bool(username and password)
        
        status = {
            'has_stored_credentials': has_credentials,
            'username': username if has_credentials else None,
            'can_authenticate': has_credentials
        }
        
        return status
    
    def authenticate_user(self) -> Optional[str]:
        """
        Authenticate user using MSAL with username and password.
        
        Returns:
            Access token if authentication succeeds, None otherwise
        """
        if not self.username or not self.password:
            print("Error: Username and password are required for authentication")
            return None
        
        app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority=self.authority,
        )
        
        result = app.acquire_token_by_username_password(
            username=self.username,
            password=self.password,
            scopes=self.SCOPE
        )
        
        if "access_token" in result:
            self._access_token = result["access_token"]
            self._set_env_var(self.ENV_ACCESS_TOKEN, self._access_token)
            return self._access_token
        else:
            print("Failed to authenticate.")
            print(f"Error: {result.get('error')}")
            print(f"Error description: {result.get('error_description')}")
            return None
    
    def get_axon_token(self) -> Optional[str]:
        """
        Get Axon token using Kerberos authentication.
        Required for Axon Assistant focus mode.
        
        Returns:
            Axon token if successful, None otherwise
        """
        try:
            kerberos_auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)
            response = requests.get(self.AXON_BEARER_URL, auth=kerberos_auth)
            response.raise_for_status()
            
            axon_data = response.json()
            self._axon_token = axon_data.get('token')
            if self._axon_token:
                self._set_env_var(self.ENV_AXON_TOKEN, self._axon_token)
            return self._axon_token
        except requests.RequestException as e:
            print(f"Failed to get Axon token: {e}")
            return None
    
    def get_ibi_token(self) -> Optional[str]:
        """
        Get IBI token using Kerberos authentication.
        Required for HSD Assistant focus mode.
        
        Returns:
            IBI token if successful, None otherwise
        """
        try:
            kerberos_auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)
            response = requests.get(self.IBI_BEARER_URL, auth=kerberos_auth, verify=False)
            response.raise_for_status()
            
            ibi_data = response.json()
            self._ibi_token = ibi_data.get('accessToken')
            if self._ibi_token:
                self._set_env_var(self.ENV_IBI_TOKEN, self._ibi_token)
            return self._ibi_token
        except requests.RequestException as e:
            print(f"Failed to get IBI token: {e}")
            return None
    
    def get_all_tokens(self, clear_password: bool = True) -> Dict[str, Optional[str]]:
        """
        Retrieve all tokens (access, axon, and ibi).
        
        Args:
            clear_password: If True, clear password from memory after authentication
        
        Returns:
            Dictionary containing all tokens
        """
        tokens = {
            'access_token': self.authenticate_user(),
            'axon_token': self.get_axon_token(),
            'ibi_token': self.get_ibi_token()
        }
        
        # Clear password from memory after successful authentication
        if clear_password and tokens['access_token']:
            self.password = ""
        
        return tokens
    
    @property
    def access_token(self) -> Optional[str]:
        """Get cached access token or None if not authenticated."""
        return self._access_token
    
    @property
    def axon_token(self) -> Optional[str]:
        """Get cached Axon token or None if not retrieved."""
        return self._axon_token
    
    @property
    def ibi_token(self) -> Optional[str]:
        """Get cached IBI token or None if not retrieved."""
        return self._ibi_token
    
    def get_auth_headers(self, include_axon: bool = False, 
                        include_ibi: bool = False) -> Dict[str, str]:
        """
        Generate authentication headers for API requests.
        
        Args:
            include_axon: Include Axon token in headers
            include_ibi: Include IBI token in headers
            
        Returns:
            Dictionary of headers
        """
        headers = {}
        
        if self._access_token:
            headers['Authorization'] = f'Bearer {self._access_token}'
        
        if include_axon and self._axon_token:
            headers['Axon-Token'] = self._axon_token
        
        if include_ibi and self._ibi_token:
            headers['ibi-token'] = self._ibi_token
        
        return headers
    
    def clear_tokens_from_env(self):
        """
        Clear all tokens from environment variables (persistent).
        """
        for env_var in [self.ENV_ACCESS_TOKEN, self.ENV_AXON_TOKEN, self.ENV_IBI_TOKEN]:
            self._delete_env_var(env_var)
        
        self._access_token = None
        self._axon_token = None
        self._ibi_token = None


def cli_status():
    """Check authentication status."""
    auth = GeniAuthManager()
    status = auth.check_credentials_status()
    
    print("=" * 60)
    print("GENI Authentication Status")
    print("=" * 60)
    
    if status['has_stored_credentials']:
        print("✓ Credentials are stored")
        print(f"  Username: {status['username']}")
        print(f"  Ready to authenticate: {status['can_authenticate']}")
    else:
        print("✗ No credentials stored")
        print("  Run with --refresh to set up credentials")
    
    print("=" * 60)


def cli_refresh():
    """Refresh (re-prompt for) credentials and fetch all tokens."""
    auth = GeniAuthManager(use_stored_credentials=False)
    
    print("=" * 60)
    print("GENI Authentication - Credential Setup")
    print("=" * 60)
    
    if auth.prompt_for_credentials():
        print("\nFetching all tokens...")
        tokens = auth.get_all_tokens()
        
        print("\nAuthentication Results:")
        print(f"  Access Token: {'✓' if tokens['access_token'] else '✗'}")
        print(f"  Axon Token: {'✓' if tokens['axon_token'] else '✗'}")
        print(f"  IBI Token: {'✓' if tokens['ibi_token'] else '✗'}")
        
        if tokens['access_token']:
            print("\n✓ Tokens stored persistently in Windows environment")
            print("  (Available after restarting terminals/applications)")
        else:
            print("\n✗ Authentication failed. Please check your credentials.")
    else:
        print("✗ Failed to save credentials")
    
    print("=" * 60)


def cli_flush():
    """Clear all stored credentials and tokens."""
    auth = GeniAuthManager(use_stored_credentials=False)
    
    print("=" * 60)
    print("GENI Authentication - Clear Credentials")
    print("=" * 60)
    
    confirm = input("Are you sure you want to clear all stored credentials and tokens? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        creds_cleared = auth._delete_credentials()
        auth.clear_tokens_from_env()
        
        if creds_cleared:
            print("✓ All credentials have been cleared from keyring")
            print("✓ All tokens have been cleared from environment (persistent)")
        else:
            print("✗ Failed to clear credentials")
    else:
        print("Operation cancelled")
    
    print("=" * 60)


def main():
    """CLI entry point for authentication manager."""
    parser = argparse.ArgumentParser(
        description="GENI Authentication Manager - Secure credential storage and token management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check authentication status
  python geni_auth_manager.py --status
  
  # Set up or refresh credentials
  python geni_auth_manager.py --refresh
  
  # Clear all stored credentials
  python geni_auth_manager.py --flush
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--status', action='store_true', 
                      help='Check authentication status')
    group.add_argument('--refresh', action='store_true', 
                      help='Force refresh (re-prompt for credentials)')
    group.add_argument('--flush', action='store_true', 
                      help='Clear all stored credentials')
    
    args = parser.parse_args()
    
    if args.status:
        cli_status()
    elif args.refresh:
        cli_refresh()
    elif args.flush:
        cli_flush()


if __name__ == "__main__":
    main()
