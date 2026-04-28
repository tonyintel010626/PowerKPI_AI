#!/usr/bin/env python3
"""
N8N API Client for Intel Intranet Community Instance

This module provides a Python client for interacting with N8N workflow automation
platform via its REST API. Designed for use within Intel's intranet only.

Environment Variables:
    N8N_API_KEY: Required. API key for authentication.
    N8N_BASE_URL: Optional. Base URL for N8N API (default: https://n8n.intel.com/api/v1)

Usage:
    # As a module
    from n8n_api import N8NClient
    client = N8NClient()
    workflows = client.list_workflows()

    # As a CLI
    python n8n_api.py --list-workflows
    python n8n_api.py --execute-workflow <workflow_id> --data '{"key": "value"}'
"""

import os
import sys
import json
import argparse
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    print("Error: 'requests' package is required. Install with: pip install requests")
    sys.exit(1)


class N8NClientError(Exception):
    """Custom exception for N8N API errors."""
    pass


class N8NClient:
    """
    N8N API Client for workflow automation.
    
    This client provides methods to interact with N8N's REST API for managing
    workflows, executions, credentials, and tags.
    
    Attributes:
        base_url: The base URL for the N8N API
        api_key: The API key for authentication
    """
    
    # Default base URL for Intel's N8N Community instance
    DEFAULT_BASE_URL = "https://n8n.intel.com/api/v1"
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the N8N client.
        
        Args:
            api_key: API key for authentication. If not provided, reads from N8N_API_KEY env var.
            base_url: Base URL for the N8N API. If not provided, reads from N8N_BASE_URL env var
                     or uses the default Intel intranet URL.
        
        Raises:
            N8NClientError: If API key is not provided or found in environment.
        """
        self.api_key = api_key or os.environ.get("N8N_API_KEY")
        if not self.api_key:
            raise N8NClientError(
                "N8N API key is required. Set the N8N_API_KEY environment variable "
                "or pass api_key to the constructor."
            )
        
        self.base_url = base_url or os.environ.get("N8N_BASE_URL", self.DEFAULT_BASE_URL)
        # Ensure base_url doesn't end with a slash
        self.base_url = self.base_url.rstrip("/")
        
        self.session = requests.Session()
        self.session.headers.update({
            "X-N8N-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the N8N API.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (e.g., "/workflows")
            data: Request body data (for POST/PATCH)
            params: Query parameters
        
        Returns:
            JSON response as a dictionary
        
        Raises:
            N8NClientError: If the request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            # Disable SSL verification for localhost/127.0.0.1
            verify_ssl = "localhost" not in url and "127.0.0.1" not in url
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=30,
                verify=verify_ssl  # Verify SSL certificates except for localhost
            )
            
            # Handle specific error codes
            if response.status_code == 401:
                raise N8NClientError("Authentication failed. Check your API key.")
            elif response.status_code == 403:
                raise N8NClientError("Permission denied. Your API key lacks required permissions.")
            elif response.status_code == 404:
                raise N8NClientError(f"Resource not found: {endpoint}")
            elif response.status_code >= 500:
                raise N8NClientError(f"N8N server error: {response.status_code}")
            
            response.raise_for_status()
            
            # Return empty dict for 204 No Content
            if response.status_code == 204:
                return {"success": True}
            
            return response.json()
            
        except requests.exceptions.ConnectionError:
            raise N8NClientError(
                f"Failed to connect to N8N at {self.base_url}. "
                "Ensure you are on Intel's intranet and the URL is correct."
            )
        except requests.exceptions.Timeout:
            raise N8NClientError("Request timed out. N8N server may be overloaded.")
        except requests.exceptions.RequestException as e:
            raise N8NClientError(f"Request failed: {str(e)}")
    
    # ========================
    # Workflow Operations
    # ========================
    
    def list_workflows(self, active: Optional[bool] = None, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        List all workflows.
        
        Args:
            active: Filter by active status (True/False/None for all)
            tags: Filter by tag names
        
        Returns:
            Dictionary containing workflow list
        """
        params = {}
        if active is not None:
            params["active"] = str(active).lower()
        if tags:
            params["tags"] = ",".join(tags)
        
        return self._request("GET", "/workflows", params=params)
    
    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get a specific workflow by ID.
        
        Args:
            workflow_id: The workflow ID
        
        Returns:
            Workflow details
        """
        return self._request("GET", f"/workflows/{workflow_id}")
    
    def create_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new workflow.
        
        Args:
            workflow_data: Workflow definition including name, nodes, connections
        
        Returns:
            Created workflow details
        """
        return self._request("POST", "/workflows", data=workflow_data)
    
    def update_workflow(self, workflow_id: str, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing workflow.
        
        Args:
            workflow_id: The workflow ID
            workflow_data: Updated workflow data
        
        Returns:
            Updated workflow details
        """
        return self._request("PUT", f"/workflows/{workflow_id}", data=workflow_data)
    
    def delete_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Delete a workflow.
        
        Args:
            workflow_id: The workflow ID
        
        Returns:
            Success status
        """
        return self._request("DELETE", f"/workflows/{workflow_id}")
    
    def activate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Activate a workflow.
        
        Args:
            workflow_id: The workflow ID
        
        Returns:
            Updated workflow details
        """
        return self._request("POST", f"/workflows/{workflow_id}/activate")
    
    def deactivate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Deactivate a workflow.
        
        Args:
            workflow_id: The workflow ID
        
        Returns:
            Updated workflow details
        """
        return self._request("POST", f"/workflows/{workflow_id}/deactivate")
    
    # ========================
    # Execution Operations
    # ========================
    
    def execute_workflow(
        self,
        workflow_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute/trigger a workflow.
        
        Args:
            workflow_id: The workflow ID to execute
            data: Input data to pass to the workflow
        
        Returns:
            Execution result
        """
        payload = data or {}
        return self._request("POST", f"/workflows/{workflow_id}/execute", data=payload)
    
    def list_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        List workflow executions.
        
        Args:
            workflow_id: Filter by workflow ID
            status: Filter by status (success, error, waiting)
            limit: Maximum number of results
        
        Returns:
            Dictionary containing execution list
        """
        params: Dict[str, Any] = {"limit": limit}
        if workflow_id:
            params["workflowId"] = workflow_id
        if status:
            params["status"] = status
        
        return self._request("GET", "/executions", params=params)
    
    def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """
        Get a specific execution by ID.
        
        Args:
            execution_id: The execution ID
        
        Returns:
            Execution details
        """
        return self._request("GET", f"/executions/{execution_id}")
    
    def delete_execution(self, execution_id: str) -> Dict[str, Any]:
        """
        Delete an execution.
        
        Args:
            execution_id: The execution ID
        
        Returns:
            Success status
        """
        return self._request("DELETE", f"/executions/{execution_id}")
    
    # ========================
    # Credential Operations
    # ========================
    
    def list_credentials(self) -> Dict[str, Any]:
        """
        List all credentials (names/types only, not secrets).
        
        Returns:
            Dictionary containing credential list
        """
        return self._request("GET", "/credentials")
    
    # ========================
    # Tag Operations
    # ========================
    
    def list_tags(self) -> Dict[str, Any]:
        """
        List all tags.
        
        Returns:
            Dictionary containing tag list
        """
        return self._request("GET", "/tags")
    
    def create_tag(self, name: str) -> Dict[str, Any]:
        """
        Create a new tag.
        
        Args:
            name: Tag name
        
        Returns:
            Created tag details
        """
        return self._request("POST", "/tags", data={"name": name})
    
    def update_tag(self, tag_id: str, name: str) -> Dict[str, Any]:
        """
        Update a tag.
        
        Args:
            tag_id: The tag ID
            name: New tag name
        
        Returns:
            Updated tag details
        """
        return self._request("PATCH", f"/tags/{tag_id}", data={"name": name})
    
    def delete_tag(self, tag_id: str) -> Dict[str, Any]:
        """
        Delete a tag.
        
        Args:
            tag_id: The tag ID
        
        Returns:
            Success status
        """
        return self._request("DELETE", f"/tags/{tag_id}")
    
    # ========================
    # Utility Methods
    # ========================
    
    def check_connection(self) -> Dict[str, Any]:
        """
        Check API connection and authentication.
        
        Returns:
            Connection status with basic info
        """
        try:
            # Try to list workflows as a connection test
            result = self.list_workflows()
            return {
                "connected": True,
                "base_url": self.base_url,
                "workflow_count": len(result.get("data", []))
            }
        except N8NClientError as e:
            return {
                "connected": False,
                "base_url": self.base_url,
                "error": str(e)
            }


def main():
    """CLI entry point for N8N API client."""
    parser = argparse.ArgumentParser(
        description="N8N API Client for Intel Intranet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --check
  %(prog)s --list-workflows
  %(prog)s --get-workflow abc123
  %(prog)s --execute-workflow abc123 --data '{"input": "value"}'
  %(prog)s --list-executions --workflow-id abc123
        """
    )
    
    # Connection
    parser.add_argument("--check", action="store_true", help="Check API connection")
    
    # Workflow operations
    parser.add_argument("--list-workflows", action="store_true", help="List all workflows")
    parser.add_argument("--get-workflow", metavar="ID", help="Get workflow by ID")
    parser.add_argument("--activate-workflow", metavar="ID", help="Activate workflow by ID")
    parser.add_argument("--deactivate-workflow", metavar="ID", help="Deactivate workflow by ID")
    parser.add_argument("--delete-workflow", metavar="ID", help="Delete workflow by ID")
    parser.add_argument("--execute-workflow", metavar="ID", help="Execute workflow by ID")
    
    # Execution operations
    parser.add_argument("--list-executions", action="store_true", help="List executions")
    parser.add_argument("--get-execution", metavar="ID", help="Get execution by ID")
    parser.add_argument("--workflow-id", metavar="ID", help="Filter by workflow ID")
    
    # Credential operations
    parser.add_argument("--list-credentials", action="store_true", help="List credentials")
    
    # Tag operations
    parser.add_argument("--list-tags", action="store_true", help="List tags")
    parser.add_argument("--create-tag", metavar="NAME", help="Create a tag")
    
    # Common options
    parser.add_argument("--data", metavar="JSON", help="JSON data for workflow execution")
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON output")
    
    args = parser.parse_args()
    
    # Check if any action was specified
    actions = [
        args.check, args.list_workflows, args.get_workflow,
        args.activate_workflow, args.deactivate_workflow, args.delete_workflow,
        args.execute_workflow, args.list_executions, args.get_execution,
        args.list_credentials, args.list_tags, args.create_tag
    ]
    
    if not any(actions):
        parser.print_help()
        sys.exit(0)
    
    try:
        client = N8NClient()
    except N8NClientError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    result = None
    
    try:
        if args.check:
            result = client.check_connection()
        
        elif args.list_workflows:
            result = client.list_workflows()
        
        elif args.get_workflow:
            result = client.get_workflow(args.get_workflow)
        
        elif args.activate_workflow:
            result = client.activate_workflow(args.activate_workflow)
            print(f"Workflow {args.activate_workflow} activated successfully.")
        
        elif args.deactivate_workflow:
            result = client.deactivate_workflow(args.deactivate_workflow)
            print(f"Workflow {args.deactivate_workflow} deactivated successfully.")
        
        elif args.delete_workflow:
            result = client.delete_workflow(args.delete_workflow)
            print(f"Workflow {args.delete_workflow} deleted successfully.")
        
        elif args.execute_workflow:
            data = json.loads(args.data) if args.data else None
            result = client.execute_workflow(args.execute_workflow, data=data)
        
        elif args.list_executions:
            result = client.list_executions(workflow_id=args.workflow_id)
        
        elif args.get_execution:
            result = client.get_execution(args.get_execution)
        
        elif args.list_credentials:
            result = client.list_credentials()
        
        elif args.list_tags:
            result = client.list_tags()
        
        elif args.create_tag:
            result = client.create_tag(args.create_tag)
            print(f"Tag '{args.create_tag}' created successfully.")
        
        # Print result if we have one
        if result:
            if args.pretty:
                print(json.dumps(result, indent=2))
            else:
                print(json.dumps(result))
    
    except N8NClientError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON data: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
