# GENI Skill for OpenCode

This skill provides integration with GENI (AI-powered autonomous solution) for validation, debugging, and triage.

## Prerequisites

1. Install required Python packages:
```bash
pip install msal requests requests-kerberos keyring
```

2. Request AGS access to 'Geni_users_production' group

## Authentication System

All GENI scripts now use **secure keyring storage** with **GUI authentication prompts**:
- **First use**: GUI dialog prompts for Intel email and password
- **Credentials stored securely**: Stored in system keyring (Windows Credential Manager, macOS Keychain, or Linux Secret Service)
- **24-hour validity**: Credentials are cached for 24 hours
- **Automatic refresh**: Scripts automatically use stored credentials within the 24-hour window

### Authentication Management

Manage your stored credentials using `geni_auth_manager.py`:

```bash
# Check token status
python geni_auth_manager.py --status

# Force refresh token (re-prompt for credentials)
python geni_auth_manager.py --refresh

# Flush all stored credentials
python geni_auth_manager.py --flush
```

## Available Scripts

### Authentication
- `geni_auth.py` - Generate bearer token (valid for 30 minutes)

### Query Scripts
- `geni_ask.py` - Simple question to GENI with focus mode
- `geni_ask_with_history.py` - Query with conversation history/workspace context
- `geni_hsd_query.py` - Query HSD tickets
- `geni_bootstrapper.py` - HW/SW component classification (PTL/GNR only)
- `geni_axon_query.py` - Query Axon database in natural language
- `geni_register_search.py` - Search PySV registers

## Quick Start

### 1. Ask a simple question
```bash
python geni_ask.py "Summarize JIRA ticket PROJ-1234" 4
```

### 2. Query an HSD ticket
```bash
python geni_hsd_query.py "14016832929"
```

### 3. Search registers
```bash
python geni_register_search.py "PCIe multicast control" "socket0.imh0.hiop.hiop_0"
```

## Focus Modes

- **4** - Jira Summarizer
- **5** - Debug Assistant
- **6** - Bootstrapper (PTL/GNR only)
- **9** - ChatHSD (requires IBI token)
- **12** - VE Wiki
- **14** - Registers Search
- **15** - Axon Assistant (requires Axon token)

## Support

Contact: geni_support@intel.com

## Documentation

See SKILL.md for detailed documentation and all available options.
