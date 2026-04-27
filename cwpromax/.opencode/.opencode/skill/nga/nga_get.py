"""
NGA GET Script - Fetch data from NGA API endpoints

This script allows you to make GET requests to NGA APIs by providing either:
- A full NGA web URL (extracts the endpoint automatically)
- A direct API endpoint path

Usage:
    python nga_get.py <url_or_endpoint> [nga_env]

Examples:
    # Using full NGA URL
    python nga_get.py "https://nga-prod.laas.intel.com/#/ptl_pcd_validation/Results/028c21b7-b661-4277-a6a3-b2784f6370bc"
    
    # Using API endpoint directly
    python nga_get.py "/Results/ptl_pcd_validation/api/TestRun/028c21b7-b661-4277-a6a3-b2784f6370bc"
    
    # Using custom environment
    python nga_get.py "/Planning/ptl_pcd_validation/api/TestLine/123" "https://nga-dev.laas.icloud.intel.com"
"""

import json
import sys
import re
from urllib.parse import urlparse
from pysvtools.execution.Lib import NgaAPIUtils


def parse_nga_url(url):
    """
    Parse an NGA URL and extract the API endpoint.
    
    Supports various NGA URL formats:
    - https://nga-prod.laas.intel.com/#/ptl_pcd_validation/Results/028c21b7-...
    - https://nga-prod.laas.intel.com/#/ptl_pcd_validation/planning/testResult/6406862c-...
    - /Results/ptl_pcd_validation/api/TestRun/028c21b7-...
    
    Args:
        url: String URL or endpoint path
        
    Returns:
        tuple: (endpoint_path, nga_environment_url)
    """
    # Default environment
    default_env = 'https://nga-prod.laas.icloud.intel.com'
    
    # If it's already an API endpoint path, return it
    if url.startswith('/'):
        return url, default_env
    
    # Parse the URL
    parsed = urlparse(url)
    
    # Extract environment from URL
    nga_env = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else default_env
    
    # Extract the fragment part (after #)
    fragment = parsed.fragment
    if not fragment:
        # Try path if no fragment
        fragment = parsed.path
    
    # Common NGA URL patterns
    # Pattern 1: #/project/Results/test-run-id
    # Pattern 2: #/project/planning/testResult/test-run-id
    # Pattern 3: #/project/Planning/TestLine/test-line-id
    
    parts = [p for p in fragment.split('/') if p]
    
    if len(parts) < 3:
        raise ValueError(f"Unable to parse NGA URL: {url}")
    
    project = parts[0]
    section = parts[1].lower()
    
    # Map common URL sections to API endpoints
    if section == 'results':
        # #/project/Results/test-run-id -> /Results/project/api/TestRun/test-run-id
        if len(parts) >= 3:
            test_run_id = parts[2]
            return f'/Results/{project}/api/TestRun/{test_run_id}', nga_env
            
    elif section == 'planning':
        # #/project/planning/testResult/test-run-id -> /Results/project/api/TestRun/test-run-id
        if len(parts) >= 4 and parts[2].lower() == 'testresult':
            test_run_id = parts[3]
            return f'/Results/{project}/api/TestRun/{test_run_id}', nga_env
        # #/project/Planning/TestLine/test-line-id -> /Planning/project/api/TestLine/test-line-id
        elif len(parts) >= 4 and parts[2].lower() == 'testline':
            test_line_id = parts[3]
            return f'/Planning/{project}/api/TestLine/{test_line_id}', nga_env
        # #/project/Planning/TestSuite/suite-id -> /Planning/project/api/TestSuite/suite-id
        elif len(parts) >= 4 and parts[2].lower() == 'testsuite':
            suite_id = parts[3]
            return f'/Planning/{project}/api/TestSuite/{suite_id}', nga_env
    
    # If we can't determine the pattern, raise an error with helpful message
    raise ValueError(
        f"Unable to determine API endpoint from URL: {url}\n"
        f"Please provide a direct API endpoint path instead, e.g.:\n"
        f"  /Results/{project}/api/TestRun/<test-run-id>\n"
        f"  /Planning/{project}/api/TestLine/<test-line-id>"
    )


def nga_get(url_or_endpoint, nga_env=None):
    """
    Fetch data from NGA API.
    
    Args:
        url_or_endpoint: NGA web URL or API endpoint path
        nga_env: NGA environment URL (optional, defaults to production)
        
    Returns:
        dict: JSON response data
    """
    # Parse the URL to get endpoint and environment
    endpoint, detected_env = parse_nga_url(url_or_endpoint)
    
    # Use provided environment or detected one
    final_env = nga_env if nga_env else detected_env
    
    # Make the API call
    status, data = NgaAPIUtils.NgaGet(endpoint, nga_env=final_env)
    
    if status != 200:
        raise Exception(
            f"NGA API request failed with status {status}\n"
            f"Endpoint: {endpoint}\n"
            f"Environment: {final_env}"
        )
    
    return data


def main():
    """Main function for command line execution."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    url_or_endpoint = sys.argv[1]
    nga_env = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        result = nga_get(url_or_endpoint, nga_env)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
