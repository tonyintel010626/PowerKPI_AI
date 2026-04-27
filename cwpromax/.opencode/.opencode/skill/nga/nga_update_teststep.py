"""
NGA Update TestStep Script - Update a test step in NGA

Usage:
    python nga_update_teststep.py <project_name> <step_id> <field_name> <new_value>

Example:
    python nga_update_teststep.py nvl_fv_or 3e3180ba-a637-4239-8843-b65a56c4ae76 Command "new command value"
"""

import json
import sys
from pysvtools.execution.Lib import NgaAPIUtils


def update_test_step(project_name, step_id, updates_dict, nga_env='https://nga-prod.laas.icloud.intel.com'):
    """
    Update a test step in NGA.
    
    Args:
        project_name: NGA project name
        step_id: Test step ID (UUID)
        updates_dict: Dictionary of fields to update
        nga_env: NGA environment URL
        
    Returns:
        dict: Updated test step data
    """
    # First, get the current test step
    endpoint = f'/Planning/{project_name}/api/TestStep/{step_id}'
    status, current_data = NgaAPIUtils.NgaGet(endpoint, nga_env=nga_env)
    
    if status != 200:
        raise Exception(
            f"Failed to get current test step (status {status})\n"
            f"Endpoint: {endpoint}\n"
            f"Environment: {nga_env}"
        )
    
    print(f"Current test step retrieved successfully")
    print(f"Name: {current_data.get('Name')}")
    
    # Update the fields
    for field, value in updates_dict.items():
        old_value = current_data.get(field)
        current_data[field] = value
        print(f"Updating {field}:")
        print(f"  Old: {old_value}")
        print(f"  New: {value}")
    
    # Send the update
    status, result = NgaAPIUtils.NgaPost(endpoint, current_data, nga_env=nga_env)
    
    if status != 200:
        raise Exception(
            f"Failed to update test step (status {status})\n"
            f"Endpoint: {endpoint}\n"
            f"Environment: {nga_env}"
        )
    
    print(f"\nTest step updated successfully!")
    return result


def main():
    """Main function for command line execution."""
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    project_name = sys.argv[1]
    step_id = sys.argv[2]
    
    # Parse field updates from command line
    # Format: field1=value1 field2=value2
    updates = {}
    for arg in sys.argv[3:]:
        if '=' in arg:
            field, value = arg.split('=', 1)
            # Try to parse as JSON if it looks like JSON
            if value.startswith('{') or value.startswith('['):
                try:
                    value = json.loads(value)
                except:
                    pass
            updates[field] = value
    
    if not updates:
        print("Error: No updates specified")
        print("Usage: python nga_update_teststep.py <project> <step_id> field1=value1 field2=value2")
        sys.exit(1)
    
    try:
        result = update_test_step(project_name, step_id, updates)
        print("\nUpdated test step:")
        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
