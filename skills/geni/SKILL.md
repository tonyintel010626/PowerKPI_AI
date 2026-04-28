---
name: geni
description: GENI AI-powered API for query 
---
# Script Location
All scripts are located at: `<cwd>/.opencode/skill/geni/`

# GENI API Integration
GENI is an AI that provide alternative interface to intel's infrastructure. 

## Supported Intel's Infrastructure
- JIRA
- HSD
- VE Wiki
- Axon
- PySV Registers - incomplete & need further search 
 
# How to Use

## Prerequisites

1. **Python Packages**: Install required packages: `pip install msal requests requests-kerberos keyring`
2. **Authentication Manager**: Use the new authentication manager for secure credential storage.


**Script**: `geni_auth_manager.py`

**Authentication**:
```bash
# Check authentication status
python <cwd>/.opencode/skill/geni/geni_auth_manager.py --status

# Force refresh (re-prompt for credentials)
python <cwd>/.opencode/skill/geni/geni_auth_manager.py --refresh

# Clear all stored credentials
python <cwd>/.opencode/skill/geni/geni_auth_manager.py --flush

# 3 TOKEN WILL BE AVAILABLE: 
    GENI_ACCESS_TOKE
    GENI_AXON_TOKEN
    GENI_IBI_TOKEN
```

***FOCUS ID***
|Name	| Description	|	API Focus ID| 
|---|---|---| 
|Jira Summarizer | Summarize JIRA tickets by inputting the JIRA ticket ID | 4|
|Debug Assistant	| Speed up debugging by allowing users to query product-related documents (Promark, Wikies, SharePoint). | 5|
|Bootstrapper	| HW\SW component classification for a sighting. Currently supported for PTL and GNR only | 6|
|ChatHSD	| HSD focus mode provides instant, detailed access to HSD ticket information and enables open-ended, semantic search across predefined HSD tenants for efficient query resolution. | 9|
|VE Wiki	| Discover our solutions and workflows by enabling users to ask questions using VE Wiki data. | 12|
|Registers Search	| Search PySV registers with natural language query (Available through API only) | 14|
|Axon Assistant	| Query Axon database in Natural language |  15|

**Example Usage - Axon Focus Mode**:
```python
import requests
import json

if __name__ == "__main__":
    url = "https://laas-aks-prod01.laas.icloud.intel.com/genichatservice/Chat/askQuestion?focusId=15"

	# authenticate_user and get_axon_token are defined in first example above
    token = authenticate_user()
    axon_token = get_axon_token()

    payload = json.dumps([
      {
        "content": "get the PTL failed records from the last 4 weeks that had a pcode_mca insight",
        "role": "user"
      }
    ])

    headers = {
      'Content-Type': 'application/json',
      'Authorization': f"Bearer {GENI_ACCESS_TOKE}",
      'Axon-Token': f"{GENI_AXON_TOKEN}"   # NOTE: axon_token is required for using the Axon Assistant focus more
      'ibi-token': f"{GENI_IBI_TOKEN}"  # NOTE: ibi_token is required only for using the HSD Assistant focus more
    }

    response = requests.request("POST", url, headers=headers, data=payload, verify=False)

    print(response.text)
```

***Using Geni with Workspace\Conversation history***
```python
import requests
import json

if __name__ == "__main__":

    url = "https://laas-aks-prod01.laas.icloud.intel.com/genichatservice/Chat/askQuestionHistoryNoStreaming"
    # Following are the Workspace and Conversation Ids you are using. workspace Id is mandatory. Conversation Id is optional. You can choose to omit it, in such a case Geni will create a new Conversation for you
    workspaceId = 4 # NOTE: you need to change this to your own existing Workspace Id
    conversationId = 65480 # NOTE: you need to change this to your own Conversation Id

    # authenticate_user and get_ibi_token are defined in first example above
    token = authenticate_user()
    ibi_token = get_ibi_token() # this is required only if you are calling the ChatHSD focus

    payload = json.dumps(
        {
            "workspaceId": workspaceId, 
            #"conversationId": conversationId, # You can use your own conversation id, for example if you uploaded files into it and want Geni to use it. In case you do not specify it Geni will create a new conversation for you
            # messages is a list of your conversation messages. You must add any message and reply if you want Geni to use them when asking follow-up questions.
            "messages": [
                {
                    "content": "Can you provide a short one sentence summary of what is Geni tool?",
                    "role": "User"
                },
                {
                    "content": "GENI is an AI-powered autonomous solution designed to accelerate validation, debugging, and triage for engineering teams by automating data analysis, generating insights from documents and tickets, and enhancing code and workflow efficiency. (document url: https://wiki.ith.intel.com/display/GENI/GENI+WIKI+Home)",
                    "role": "Assistant"
                },
                {
                    "content": "Provide a short explanation of when to use it",
                    "role": "User"
                }
            ],
            "includeFiles": False,  # True if you want to use files that were uploaded to the Conversation
            "product": "MyToolName",
            "focusIds": [
                12   # NOTE: change to the required focus id
            ]
        }
    )

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {token}",
        'ibi-token': f"{ibi_token}"  # NOTE: ibi_token is required only for using the HSD Assistant focus more
    }

    response = requests.request("POST", url, headers=headers, data=payload, verify=False)

    print(response.text)
```

## Focus Modes (Production API)

| Focus Mode | Description | Focus ID |
|------------|-------------|----------|
| **Jira Summarizer** | Summarize JIRA tickets by inputting the JIRA ticket ID | 4 |
| **Debug Assistant** | Speed up debugging by querying product-related documents (Promark, Wikies, SharePoint) | 5 |
| **Bootstrapper** | HW/SW component classification for a sighting (PTL and GNR only) | 6 |
| **ChatHSD** | Instant, detailed access to HSD ticket information with semantic search | 9 |
| **VE Wiki** | Ask questions using VE Wiki data | 12 |
| **Registers Search** | Search PySV registers with natural language query (API only) | 14 |
| **Axon Assistant** | Query Axon database in natural language | 15 |


## API Endpoints

- **Production Chat Service**: https://laas-aks-prod01.laas.icloud.intel.com/genichatservice/
- **Production Entity Service**: https://laas-aks-prod01.laas.icloud.intel.com/genientityservice/
- **Swagger Documentation**: 
  - Chat Service: https://laas-aks-prod01.laas.icloud.intel.com/genichatservice/swagger/index.html
  - Entity Service: https://laas-aks-prod01.laas.icloud.intel.com/genientityservice/swagger/index.html

## Authentication Details

**Azure Application Info**:
- CLIENT_ID: `8a2ecaf5-fb85-4534-81aa-2df3e7f24907`
- TENANT_ID: `46c98d88-e344-4ed4-8496-4ed7712e255d`
- SCOPE: `api://8a2ecaf5-fb85-4534-81aa-2df3e7f24907/API.Read`

## Special Requirements

- **HSD Assistant (Focus 9)**: Requires `ibi-token` in headers
- **Axon Assistant (Focus 15)**: Requires `Axon-Token` in headers
- **Workspace/History API**: Use `askQuestionHistoryNoStreaming` endpoint

## Support

For issues or questions, contact: geni_support@intel.com

## Additional Resources

- Wiki: https://wiki.ith.intel.com/display/GENI/GENI+WIKI+Home
- Register Search Details: https://wiki.ith.intel.com/spaces/GENI/pages/4386359053/Registers+Search
