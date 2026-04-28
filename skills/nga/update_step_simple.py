"""
Simple NGA TestStep Update Script
"""

import json
import sys
from pysvtools.execution.Lib import NgaAPIUtils


def update_test_step_command(project_name, step_id, new_command):
    """Update the Command field of a test step."""
    
    nga_env = 'https://nga-prod.laas.icloud.intel.com'
    endpoint = f'/Planning/{project_name}/api/TestStep/{step_id}'
    
    # Get current test step
    print(f"Getting test step {step_id}...")
    status, current_data = NgaAPIUtils.NgaGet(endpoint, nga_env=nga_env)
    
    if status != 200:
        print(f"ERROR: Failed to get test step (status {status})")
        return False
    
    print(f"Current step name: {current_data.get('Name')}")
    print(f"\nOld command:\n{current_data.get('Command')}\n")
    
    # Update the command
    current_data['Command'] = new_command
    
    print(f"New command:\n{new_command}\n")
    
    # Post the update
    print(f"Updating test step...")
    response = NgaAPIUtils.NgaPost(endpoint, current_data, nga_env=nga_env)
    
    if response.status_code == 200:
        print(f"SUCCESS: Test step updated!")
        return True
    else:
        print(f"ERROR: Failed to update (status {response.status_code})")
        print(f"Reason: {response.reason}")
        try:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response text: {response.text}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python update_step_simple.py <project> <step_id> <new_command>")
        sys.exit(1)
    
    project = sys.argv[1]
    step_id = sys.argv[2]
    command = sys.argv[3]
    
    success = update_test_step_command(project, step_id, command)
    sys.exit(0 if success else 1)
