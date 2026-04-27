"""
OneBKC Get Kits Script - Fetch kits from OneBKC API

This script allows you to query kits from OneBKC with various filters:
- Platform configurations (e.g., PTL-UPH-25H2-CONS, NVL-Hx-Cons)
- Promotion date (e.g., 12/24/2025)
- Quality colors (Created, Bronze, Silver, Gold, BKC)
- Build statuses (passed, failed)

Usage:
    python onebkc_get_kits.py [--platformconfigs <config>] [--promotiondate <date>] [--colors <color>] [--buildstatuses <status>]

Examples:
    # Get all kits
    python onebkc_get_kits.py
    
    # Get PTL Consumer kits promoted to BKC
    python onebkc_get_kits.py --platformconfigs "PTL-UPH-25H2-CONS" --colors "BKC"
    
    # Get kits promoted on specific date with passed build
    python onebkc_get_kits.py --platformconfigs "PTL-UPH-25H2-CONS" --promotiondate "12/24/2025" --colors "BKC" --buildstatuses "passed"
"""

import json
import sys
import os
import argparse
from pathlib import Path
from onebkc.client import OneBkcClient

# --- Unified credentials import ---
_CRED_DIR = str(Path(__file__).resolve().parent.parent / "credentials")
if _CRED_DIR not in sys.path:
    sys.path.insert(0, _CRED_DIR)
from intel_credentials import get_credentials  # noqa: E402


def get_kits(platformconfigs=None, promotiondate=None, colors=None, buildstatuses=None, api_url='https://onekitapi.intel.com/api/v1/'):
    """
    Fetch kits from OneBKC API with optional filters.
    
    Args:
        platformconfigs: Platform configuration filter (e.g., "PTL-UPH-25H2-CONS")
        promotiondate: Promotion date filter (e.g., "12/24/2025")
        colors: Quality color filter (Created, Bronze, Silver, Gold, BKC)
        buildstatuses: Build status filter (passed, failed)
        api_url: OneBKC API URL (defaults to production)
        
    Returns:
        dict: JSON response with kits data
    """
    # Get credentials from unified credential manager
    try:
        username, password = get_credentials()
    except Exception as e:
        raise Exception(
            f"Intel credentials not found: {e}\n"
            "Run: python .opencode/skill/credentials/intel_credentials.py --refresh"
        )
    
    # Create client
    client = OneBkcClient(api_url, username=username, password=password)
    
    # Build filter parameters
    filter_params = {}
    if platformconfigs:
        filter_params['platformconfigs'] = platformconfigs
    if promotiondate:
        filter_params['promotiondate'] = promotiondate
    if colors:
        filter_params['colors'] = colors
    if buildstatuses:
        filter_params['buildstatuses'] = buildstatuses
    
    # Fetch kits
    result = client.get_kits(**filter_params)
    
    if result.get('kits') is None:
        raise Exception("No kits returned from API")
    
    return result


def main():
    """Main function for command line execution."""
    parser = argparse.ArgumentParser(
        description='Fetch kits from OneBKC API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--platformconfigs', 
                       help='Platform configuration (e.g., PTL-UPH-25H2-CONS, NVL-Hx-Cons)')
    parser.add_argument('--promotiondate', 
                       help='Promotion date (e.g., 12/24/2025)')
    parser.add_argument('--colors', 
                       help='Quality color (Created, Bronze, Silver, Gold, BKC)')
    parser.add_argument('--buildstatuses', 
                       help='Build status (passed, failed)')
    parser.add_argument('--api-url', 
                       default='https://onekitapi.intel.com/api/v1/',
                       help='OneBKC API URL (default: production)')
    
    args = parser.parse_args()
    
    try:
        result = get_kits(
            platformconfigs=args.platformconfigs,
            promotiondate=args.promotiondate,
            colors=args.colors,
            buildstatuses=args.buildstatuses,
            api_url=args.api_url
        )
        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
