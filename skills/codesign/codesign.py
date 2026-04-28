#!/usr/bin/env python3
"""
Co-De Sign Query Tool - Standalone Binary
Mimics browser access to CoDesign for predictable API-based queries.

Usage:
    python codesign.py -q "your question here" -output_file ./result.json
    python codesign.py -q "your question here" -output_file ./result.json --limit 5
    python codesign.py -q "your question here" -output_file ./result.json --source files
    python codesign.py -q "your question here" -output_file ./result.json --thread_id <uuid>
"""

import argparse
import json
import os
import sys
import uuid
from copy import deepcopy
from datetime import datetime
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
    'ask': f'{BASE_URL}/codesign/llm/runs/wait',
}


def get_apigee_token():
    """Get OAuth token from Apigee"""
    payload = {
        'grant_type': 'client_credentials',
        'client_id': API_KEY,
        'client_secret': API_SECRET
    }
    
    response = requests.post(ENDPOINTS['token'], data=payload, proxies=PROXIES)
    response.raise_for_status()
    return response.json()['access_token']


def get_codesign_token(auth_header):
    """Get Co-De Sign token using LDAP credentials"""
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
    """Get all accessible projects and files"""
    response = requests.get(
        ENDPOINTS['sources'],
        headers=auth_header,
        cookies={"token": codesign_token},
        proxies=PROXIES
    )
    response.raise_for_status()
    return response.json()


def ask_agent(auth_header, codesign_token, query, sources, graph_id="spec_agent", thread_id=None):
    """Ask AI agent a question"""
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
    parser = argparse.ArgumentParser(
        description='Co-De Sign Query Tool - Query Intel CoDesign knowledge base',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query projects (default)
  python codesign.py -q "What is PMC?" -output_file ./result.json
  
  # Query with limited context
  python codesign.py -q "What are eSPI registers?" -output_file ./result.json --limit 5
  
  # Query uploaded files
  python codesign.py -q "Explain my code" -output_file ./result.json --source files
  
  # Follow-up question
  python codesign.py -q "Tell me more" -output_file ./result.json --thread_id abc-123-def
        """
    )
    
    parser.add_argument('-q', '--question', required=True,
                        help='Question to ask CoDesign')
    parser.add_argument('-output_file', '--output-file', required=True,
                        help='Output JSON file path (e.g., ./result.json)')
    parser.add_argument('--limit', type=int, default=3,
                        help='Number of projects to use as context (default: 3)')
    parser.add_argument('--source', choices=['projects', 'files'], default='projects',
                        help='Source type: projects or files (default: projects)')
    parser.add_argument('--thread_id', '--thread-id', default=None,
                        help='Thread ID for follow-up questions (optional)')
    parser.add_argument('--graph_id', '--graph-id', default='spec_agent',
                        choices=['spec_agent', 'spec_rag'],
                        help='Agent type: spec_agent (conversational) or spec_rag (RAG only)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output to stderr')
    
    args = parser.parse_args()
    
    # Validate environment variables
    if not all([IDSID, PASSWD, API_KEY, API_SECRET]):
        print("❌ Error: Missing required environment variables", file=sys.stderr)
        print("Required: IDSID, PASS, API_KEY, API_SECRET", file=sys.stderr)
        sys.exit(1)
    
    # Generate or use provided thread_id
    thread_id = args.thread_id or str(uuid.uuid4())
    
    # Verbose logging
    def log(message):
        if args.verbose:
            print(message, file=sys.stderr)
    
    try:
        # Step 1: Authenticate
        log("🔐 Authenticating with Apigee...")
        apigee_token = get_apigee_token()
        auth_header = {'Authorization': f'Bearer {apigee_token}'}
        
        log("🔐 Authenticating with CoDesign...")
        codesign_token = get_codesign_token(auth_header)
        log("✅ Authentication successful\n")
        
        # Step 2: Get sources
        log(f"📂 Fetching {args.source}...")
        sources = get_sources(auth_header, codesign_token)
        
        # Filter source type
        if args.source == 'projects':
            source_data = [s for s in sources if s['type'] == 'projects'][0]
            # Limit projects if specified
            limited_source = deepcopy(source_data)
            limited_source['content'] = source_data['content'][:args.limit]
            log(f"📚 Using top {args.limit} projects out of {len(source_data['content'])} available")
        else:  # files
            source_data = [s for s in sources if s['type'] == 'my_files'][0]
            limited_source = source_data
            log(f"📄 Using {len(source_data['content'])} uploaded files")
        
        # Step 3: Ask question
        log(f"\n🤔 Question: {args.question}")
        log(f"🔗 Thread ID: {thread_id}")
        log("⏳ Querying CoDesign agent...\n")
        
        result = ask_agent(
            auth_header,
            codesign_token,
            args.question,
            [limited_source],
            graph_id=args.graph_id,
            thread_id=thread_id
        )
        
        # Step 4: Format output
        output = {
            "status": "success" if result.get('output') else "error",
            "timestamp": datetime.now().isoformat(),
            "query": {
                "question": args.question,
                "source_type": args.source,
                "limit": args.limit if args.source == 'projects' else None,
                "thread_id": thread_id,
                "graph_id": args.graph_id
            },
            "response": {}
        }
        
        if result.get('output'):
            output["response"]["answer"] = result['output'].get('answer', '')
            output["response"]["references"] = result['output'].get('references', [])
            output["response"]["metadata"] = result['output'].get('metadata', {})
            
            log("✅ Query successful!")
            if args.verbose and result['output'].get('answer'):
                log(f"\n💡 Answer Preview:\n{result['output']['answer'][:200]}...")
        else:
            output["status"] = "error"
            output["response"]["error"] = result.get('detail', 'Unknown error')
            log(f"❌ Query failed: {result.get('detail', 'Unknown error')}")
        
        # Step 5: Write output file
        output_path = os.path.abspath(args.output_file)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        log(f"\n📝 Output written to: {output_path}")
        
        # Exit with appropriate code
        sys.exit(0 if output["status"] == "success" else 1)
        
    except requests.exceptions.HTTPError as e:
        error_output = {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "query": {
                "question": args.question,
                "source_type": args.source,
                "thread_id": thread_id
            },
            "response": {
                "error": f"HTTP Error: {str(e)}",
                "details": e.response.text if hasattr(e, 'response') else None
            }
        }
        
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(error_output, f, indent=2, ensure_ascii=False)
        
        print(f"❌ HTTP Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
        
    except Exception as e:
        error_output = {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "query": {
                "question": args.question,
                "source_type": args.source,
                "thread_id": thread_id
            },
            "response": {
                "error": str(e),
                "type": type(e).__name__
            }
        }
        
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(error_output, f, indent=2, ensure_ascii=False)
        
        print(f"❌ Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
