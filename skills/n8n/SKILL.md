---
name: n8n
disable: false
description: N8N workflow automation API integration for Intel intranet community instance
license: MIT
---
# Script Location
All scripts are located at: `<cwd>/.opencode/skill/n8n/`

# N8N Workflow Automation Integration

N8N is a workflow automation platform that allows you to connect various services and automate tasks. This skill provides API integration with the Intel intranet N8N Community instance.

**IMPORTANT**: This skill only works with the N8N Community version deployed within Intel's intranet. External N8N instances are not supported.

## Supported Operations

- **Workflows**: List, get, create, update, delete, activate/deactivate workflows
- **Executions**: List, get, delete executions, trigger workflow executions
- **Credentials**: List available credentials (read-only for security)
- **Tags**: List, create, update, delete tags for workflow organization

## Prerequisites

1. **Python Packages**: Install required packages:
   ```bash
   pip install requests
   ```

2. **Environment Variable**: Set your N8N API key:
   ```bash
   # Windows
   set N8N_API_KEY=your_api_key_here
   
   # Linux/Mac
   export N8N_API_KEY=your_api_key_here
   ```

3. **Obtain API Key**: 
   - Log into your Intel N8N Community instance
   - Go to Settings > API > Create API Key
   - Copy the generated key and set it as the `N8N_API_KEY` environment variable

## Configuration

The N8N base URL is configured for Intel's intranet instance. If you need to use a different instance within Intel's network, set the `N8N_BASE_URL` environment variable:

```bash
# Default (if not set): https://n8n.intel.com/api/v1
set N8N_BASE_URL=https://your-n8n-instance.intel.com/api/v1
```

## How to Use

### Authentication Check

```bash
# Verify API connection and authentication
python <cwd>/.opencode/skill/n8n/n8n_api.py --check
```

### Workflow Operations

**Script**: `n8n_api.py`

```bash
# List all workflows
python <cwd>/.opencode/skill/n8n/n8n_api.py --list-workflows

# Get specific workflow by ID
python <cwd>/.opencode/skill/n8n/n8n_api.py --get-workflow <workflow_id>

# Activate a workflow
python <cwd>/.opencode/skill/n8n/n8n_api.py --activate-workflow <workflow_id>

# Deactivate a workflow
python <cwd>/.opencode/skill/n8n/n8n_api.py --deactivate-workflow <workflow_id>

# Delete a workflow
python <cwd>/.opencode/skill/n8n/n8n_api.py --delete-workflow <workflow_id>
```

### Execution Operations

```bash
# List all executions
python <cwd>/.opencode/skill/n8n/n8n_api.py --list-executions

# List executions for a specific workflow
python <cwd>/.opencode/skill/n8n/n8n_api.py --list-executions --workflow-id <workflow_id>

# Get specific execution details
python <cwd>/.opencode/skill/n8n/n8n_api.py --get-execution <execution_id>

# Trigger/execute a workflow
python <cwd>/.opencode/skill/n8n/n8n_api.py --execute-workflow <workflow_id>

# Trigger workflow with input data (JSON)
python <cwd>/.opencode/skill/n8n/n8n_api.py --execute-workflow <workflow_id> --data '{"key": "value"}'
```

### Tag Operations

```bash
# List all tags
python <cwd>/.opencode/skill/n8n/n8n_api.py --list-tags

# Create a new tag
python <cwd>/.opencode/skill/n8n/n8n_api.py --create-tag "my-new-tag"
```

### Credential Operations

```bash
# List available credentials (names only, not secrets)
python <cwd>/.opencode/skill/n8n/n8n_api.py --list-credentials
```

## Python API Usage

You can also use the N8N API directly in Python scripts:

```python
import os
import sys
sys.path.append('<cwd>/.opencode/skill/n8n')
from n8n_api import N8NClient

# Initialize client (uses N8N_API_KEY environment variable)
client = N8NClient()

# List all workflows
workflows = client.list_workflows()
for wf in workflows.get('data', []):
    print(f"Workflow: {wf['name']} (ID: {wf['id']}, Active: {wf['active']})")

# Get a specific workflow
workflow = client.get_workflow('workflow_id')

# Execute a workflow with data
result = client.execute_workflow('workflow_id', data={'input': 'value'})

# List executions
executions = client.list_executions(workflow_id='optional_workflow_id')

# Activate/deactivate workflow
client.activate_workflow('workflow_id')
client.deactivate_workflow('workflow_id')
```

## API Endpoints Reference

| Operation | Method | Endpoint |
|-----------|--------|----------|
| List Workflows | GET | `/workflows` |
| Get Workflow | GET | `/workflows/{id}` |
| Create Workflow | POST | `/workflows` |
| Update Workflow | PATCH | `/workflows/{id}` |
| Delete Workflow | DELETE | `/workflows/{id}` |
| Activate Workflow | POST | `/workflows/{id}/activate` |
| Deactivate Workflow | POST | `/workflows/{id}/deactivate` |
| List Executions | GET | `/executions` |
| Get Execution | GET | `/executions/{id}` |
| Delete Execution | DELETE | `/executions/{id}` |
| Execute Workflow | POST | `/workflows/{id}/execute` |
| List Credentials | GET | `/credentials` |
| List Tags | GET | `/tags` |
| Create Tag | POST | `/tags` |

## Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `N8N_API_KEY` | Yes | API key for authentication | None |
| `N8N_BASE_URL` | No | Base URL for N8N API | `https://n8n.intel.com/api/v1` |

## Error Handling

The API client handles common errors:
- **401 Unauthorized**: Invalid or missing API key
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Workflow/execution not found
- **500 Server Error**: N8N server issue

## Limitations

- **No Vision Capability**: This skill does not support image/screenshot analysis
- **Intel Intranet Only**: Only works with N8N instances within Intel's network
- **Read-Only Credentials**: Credential secrets cannot be retrieved for security reasons
- **Community Version**: Designed for N8N Community edition (not Enterprise)

## Security Notes

- Never commit your API key to version control
- Use environment variables for sensitive data
- API keys have the same permissions as the user who created them
- Rotate API keys periodically

## Troubleshooting

**Connection refused / Cannot connect**
- Verify you are on Intel's intranet (VPN if remote)
- Check `N8N_BASE_URL` is correct

**401 Unauthorized**
- Verify `N8N_API_KEY` is set correctly
- Check if API key has expired
- Regenerate API key in N8N settings

**Workflow not executing**
- Ensure workflow is activated
- Check workflow has a webhook or manual trigger node
- Verify input data format matches workflow expectations

## Support

For N8N-related issues within Intel:
- Intel N8N Community: Check your internal N8N instance documentation
- OpenCode Skill Issues: Report at https://github.com/sst/opencode
