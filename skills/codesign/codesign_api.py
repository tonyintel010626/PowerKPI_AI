#!/usr/bin/env python3
"""
Co-De Sign API - Simplified Script
Teaches AI how to interact with Intel's Co-De Sign API in simple snippets.
"""

import json
import os
import sys
import uuid
from copy import deepcopy
from pathlib import Path

import dotenv
import requests

# Load environment variables
dotenv.load_dotenv()

# --- Unified credentials import ---
_CRED_DIR = str(Path(__file__).resolve().parent.parent / "credentials")
if _CRED_DIR not in sys.path:
    sys.path.insert(0, _CRED_DIR)
try:
    from intel_credentials import get_credentials as _get_intel_creds, get_idsid
    _user, _pass = _get_intel_creds()
    IDSID = get_idsid(_user)
    PASSWD = _pass
except Exception:
    # Fallback to .env
    IDSID = f"{os.environ.get('USERDOMAIN', 'gar').lower()}\\{os.getenv('IDSID', '')}"
    PASSWD = os.getenv('PASS')

# Configuration from environment (Apigee keys still from .env)
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

# Intel proxy settings
PROXIES = {
    "http": "http://proxy-chain.intel.com:911",
    "https": "http://proxy-chain.intel.com:912"
}

# API endpoints
BASE_URL = 'https://apis-internal-sandbox.intel.com'
ENDPOINTS = {
    'token': f'{BASE_URL}/v1/auth/token',
    'login': f'{BASE_URL}/codesign/auth/login/ldap',
    'sources': f'{BASE_URL}/codesign/online/auth/sources/all',
    'upload': f'{BASE_URL}/codesign/online/upload_file',
    'delete': f'{BASE_URL}/codesign/online/delete_file',
    'ask': f'{BASE_URL}/codesign/llm/runs/wait',
}


def get_apigee_token():
    """Step 1: Get OAuth token from Apigee"""
    payload = {
        'grant_type': 'client_credentials',
        'client_id': API_KEY,
        'client_secret': API_SECRET
    }
    
    response = requests.post(ENDPOINTS['token'], data=payload, proxies=PROXIES)
    response.raise_for_status()
    return response.json()['access_token']


def get_codesign_token(auth_header):
    """Step 2: Get Co-De Sign token using LDAP credentials"""
    payload = {"idsid": IDSID, "passwd": PASSWD}
    
    response = requests.post(
        ENDPOINTS['login'],
        headers=auth_header,
        data=json.dumps(payload),
        proxies=PROXIES
    )
    response.raise_for_status()
    return response.json()


def get_sources(auth_header, codesign_token):
    """Step 3: Get all accessible projects and files"""
    response = requests.get(
        ENDPOINTS['sources'],
        headers=auth_header,
        cookies={"token": codesign_token},
        proxies=PROXIES
    )
    response.raise_for_status()
    return response.json()


def upload_file(auth_header, codesign_token, file_path):
    """Step 4: Upload a file to Co-De Sign"""
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(
            ENDPOINTS['upload'],
            headers=auth_header,
            files=files,
            cookies={"token": codesign_token},
            proxies=PROXIES
        )
    response.raise_for_status()
    return response.json()


def delete_file(auth_header, codesign_token, file_ids):
    """Step 5: Delete files by ID"""
    response = requests.post(
        ENDPOINTS['delete'],
        headers=auth_header,
        json=file_ids if isinstance(file_ids, list) else [file_ids],
        cookies={"token": codesign_token},
        proxies=PROXIES
    )
    response.raise_for_status()
    return response.json()


def ask_agent(auth_header, codesign_token, query, sources, graph_id="spec_agent", thread_id=None):
    """Step 6: Ask AI agent a question"""
    headers = {
        "Content-Type": "application/json",
        "AgentAuth": f"Bearer {codesign_token}",
        "jwt-token": codesign_token
    }
    headers.update(auth_header)
    
    payload = {
        "input": {
            "query": query,
            "sources": sources,
        },
        "graph_id": graph_id,
    }
    
    if thread_id:
        payload["thread_id"] = thread_id
    
    response = requests.post(
        ENDPOINTS['ask'],
        headers=headers,
        json=payload,
        proxies=PROXIES
    )
    response.raise_for_status()
    return json.loads(response.json())


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  upload <file_path>              - Upload a file")
        print("  delete <file_id>                - Delete a file")
        print("  list-projects                   - List all projects")
        print("  list-files                      - List all uploaded files")
        print("  ask-files <question>            - Ask about uploaded files")
        print("  ask-projects <question> [--limit N] - Ask about projects")
        print("  ask-followup <thread_id> <question> - Ask follow-up question")
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Authenticate
    print("🔐 Authenticating...")
    apigee_token = get_apigee_token()
    auth_header = {'Authorization': f'Bearer {apigee_token}'}
    codesign_token = get_codesign_token(auth_header)
    print("✅ Authenticated\n")
    
    # Execute command
    if command == "upload":
        if len(sys.argv) < 3:
            print("Error: Please provide file path")
            sys.exit(1)
        
        file_path = sys.argv[2]
        print(f"📤 Uploading: {file_path}")
        result = upload_file(auth_header, codesign_token, file_path)
        print(f"✅ Status: {result['status']}")
        print(f"📄 File ID: {result['doc_id']}")
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Error: Please provide file ID")
            sys.exit(1)
        
        file_id = sys.argv[2]
        print(f"🗑️  Deleting file: {file_id}")
        result = delete_file(auth_header, codesign_token, file_id)
        print(f"✅ Status: {result.get('status_list', result.get('detail'))}")
    
    elif command == "list-projects":
        print("📂 Fetching projects...")
        sources = get_sources(auth_header, codesign_token)
        projects = [s for s in sources if s['type'] == 'projects'][0]
        
        print(f"\n📊 Found {len(projects['content'])} projects:\n")
        for i, proj in enumerate(projects['content'][:10], 1):
            print(f"  {i}. {proj.get('name', proj.get('id'))}")
        
        if len(projects['content']) > 10:
            print(f"\n  ... and {len(projects['content']) - 10} more")
    
    elif command == "list-files":
        print("📂 Fetching files...")
        sources = get_sources(auth_header, codesign_token)
        my_files = [s for s in sources if s['type'] == 'my_files'][0]
        
        print(f"\n📊 Found {len(my_files['content'])} files:\n")
        for i, file in enumerate(my_files['content'][:10], 1):
            print(f"  {i}. {file.get('name', file.get('id'))}")
        
        if len(my_files['content']) > 10:
            print(f"\n  ... and {len(my_files['content']) - 10} more")
    
    elif command == "ask-files":
        if len(sys.argv) < 3:
            print("Error: Please provide a question")
            sys.exit(1)
        
        question = sys.argv[2]
        print(f"🤔 Question: {question}\n")
        
        sources = get_sources(auth_header, codesign_token)
        my_files = [s for s in sources if s['type'] == 'my_files'][0]
        
        thread_id = str(uuid.uuid4())
        print(f"🔗 Thread ID: {thread_id}\n")
        
        result = ask_agent(auth_header, codesign_token, question, [my_files], thread_id=thread_id)
        
        if result.get('output'):
            print(f"💡 Answer:\n{result['output']['answer']}\n")
        else:
            print(f"❌ Error: {result.get('detail')}")
    
    elif command == "ask-projects":
        if len(sys.argv) < 3:
            print("Error: Please provide a question")
            sys.exit(1)
        
        question = sys.argv[2]
        limit = 3  # Default limit
        
        # Check for --limit flag
        if len(sys.argv) > 3 and sys.argv[3] == "--limit" and len(sys.argv) > 4:
            limit = int(sys.argv[4])
        
        print(f"🤔 Question: {question}")
        print(f"📚 Using top {limit} projects\n")
        
        sources = get_sources(auth_header, codesign_token)
        projects = [s for s in sources if s['type'] == 'projects'][0]
        
        # Limit projects
        limited_projects = deepcopy(projects)
        limited_projects['content'] = projects['content'][:limit]
        
        thread_id = str(uuid.uuid4())
        print(f"🔗 Thread ID: {thread_id}\n")
        
        result = ask_agent(auth_header, codesign_token, question, [limited_projects], thread_id=thread_id)
        
        if result.get('output'):
            print(f"💡 Answer:\n{result['output']['answer']}\n")
            
            if result['output'].get('references'):
                print(f"📚 References:")
                for ref in result['output']['references'][:5]:
                    print(f"  - {ref}")
        else:
            print(f"❌ Error: {result.get('detail')}")
    
    elif command == "ask-followup":
        if len(sys.argv) < 4:
            print("Error: Please provide thread_id and question")
            sys.exit(1)
        
        thread_id = sys.argv[2]
        question = sys.argv[3]
        
        print(f"🔗 Thread ID: {thread_id}")
        print(f"🤔 Question: {question}\n")
        
        sources = get_sources(auth_header, codesign_token)
        projects = [s for s in sources if s['type'] == 'projects'][0]
        
        result = ask_agent(auth_header, codesign_token, question, [projects], thread_id=thread_id)
        
        if result.get('output'):
            print(f"💡 Answer:\n{result['output']['answer']}\n")
        else:
            print(f"❌ Error: {result.get('detail')}")
    
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    # Validate environment variables
    if not all([IDSID, PASSWD, API_KEY, API_SECRET]):
        print("❌ Error: Missing required environment variables")
        print("Required: IDSID, PASS, API_KEY, API_SECRET")
        sys.exit(1)
    
    main()
