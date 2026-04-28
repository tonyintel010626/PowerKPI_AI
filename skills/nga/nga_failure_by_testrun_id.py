"""
NGA Failure Query Script - Query failures by test run ID using NGA API

This script queries failure information for a test run ID using the NGA Failure API.

Usage:
    python nga_failure_by_testrun_id.py <project> <test_run_id> [nga_env]

Examples:
    # Query failures for a test run
    python nga_failure_by_testrun_id.py "ptl_pcd_validation" "c707b743-30bd-41a8-a941-05c5fe160f70"
"""

import json
import sys
import re
from pysvtools.execution.Lib import NgaAPIUtils
import logging
log = logging.getLogger(__name__)

def extract_test_run_id(input_str):
    """
    Extract test run ID from various input formats.
    
    Supports:
    - Plain UUID: c707b743-30bd-41a8-a941-05c5fe160f70
    - NGA URL: https://nga-prod.laas.intel.com/#/ptl_pcd_validation/Results/c707b743-...
    - API endpoint: /Results/ptl_pcd_validation/api/TestRun/c707b743-...
    
    Args:
        input_str: String containing test run ID
        
    Returns:
        str: Extracted test run ID (UUID)
    """
    # UUID pattern
    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    
    match = re.search(uuid_pattern, input_str, re.IGNORECASE)
    if match:
        return match.group(0)
    
    raise ValueError(f"No valid test run ID found in: {input_str}")

def nga_post(url: str = 'test', data: dict = {}):    
    response = nga_utils.NgaPut()
    return response
    pass

def query_failures_by_testrun_id(test_run_id, project, nga_env="https://nga-prod.laas.icloud.intel.com"):
    """
    Query failure information for a given test run ID.
    
    Args:
        test_run_id: Test run ID (UUID)
        project: NGA project name (required)
        nga_env: NGA environment URL (optional, defaults to production)
        
    Returns:
        dict: JSON response data containing failure information
    """
    # Construct the endpoint
    endpoint = f'/Failure/{project}/api/Failure/QueryByTestRunIds'
    log.debug(endpoint)    
    # Prepare the payload (list containing single test run ID)
    payload = [test_run_id]
    
    # Make the POST request
    
    data  = NgaAPIUtils.NgaPost(endpoint, payload, nga_env=nga_env)
    status_code = data.status_code
    json_data = data.json()    
    if status_code != 200:
        raise Exception(
            f"NGA API POST request failed with status {status_code}\n"
            f"Endpoint: {endpoint}\n"
            f"Environment: {nga_env}\n"
            f"Payload: {json.dumps(payload)}"
        )
    
    return json_data


def main():
    """Main function for command line execution."""
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    # Parse command line arguments
    project = sys.argv[1]
    test_run_id_input = sys.argv[2]    
    
    try:
        # Extract test run ID
        test_run_id = extract_test_run_id(test_run_id_input)
        print(project)
        # Query failures
        result = query_failures_by_testrun_id(test_run_id, project)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
