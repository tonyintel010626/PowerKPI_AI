# Co-De Sign Query Tool - Standalone Binary

A predictable, reliable command-line tool for querying Intel's Co-De Sign knowledge base without browserMCP dependencies.

## Overview

This tool provides a stable API-based interface to Co-De Sign, eliminating the timing issues and flakiness associated with browser automation. It's designed for programmatic access and automation workflows, particularly for FV debug scenarios.

## Installation

### Prerequisites

1. **Python 3.7+** with required packages:
```bash
pip install requests python-dotenv
```

2. **Environment Variables** in `.env` file:
```env
IDSID=your_idsid_without_domain
PASS=your_intel_password
API_KEY=your_apigee_api_key
API_SECRET=your_apigee_api_secret
```

3. **Network**: Must be on Intel network or VPN (uses Intel proxy)

## Usage

### Basic Query

```bash
python codesign.py -q "What is PMC?" -output_file ./result.json
```

### Query with Verbose Output

```bash
python codesign.py -q "What are eSPI registers?" -output_file ./result.json --verbose
```

### Limited Context (Faster Response)

```bash
python codesign.py -q "Explain PCIe enumeration" -output_file ./result.json --limit 5
```

### Query Uploaded Files

```bash
python codesign.py -q "Explain my code" -output_file ./result.json --source files
```

### Follow-up Questions (Conversational Context)

```bash
# First query - note the thread_id in output
python codesign.py -q "What is PMC?" -output_file ./result1.json -v

# Follow-up using the same thread_id
python codesign.py -q "Tell me more about PMC registers" -output_file ./result2.json --thread_id <uuid-from-result1>
```

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-q`, `--question` | **Required**. Question to ask CoDesign | - |
| `-output_file`, `--output-file` | **Required**. Output JSON file path | - |
| `--limit` | Number of projects to use as context | 3 |
| `--source` | Source type: `projects` or `files` | `projects` |
| `--thread_id`, `--thread-id` | Thread ID for follow-up questions | Auto-generated UUID |
| `--graph_id`, `--graph-id` | Agent type: `spec_agent` or `spec_rag` | `spec_agent` |
| `-v`, `--verbose` | Enable verbose output to stderr | False |

## Output Format

The tool writes a JSON file with the following structure:

```json
{
  "status": "success",
  "timestamp": "2026-03-05T10:30:45.123456",
  "query": {
    "question": "What is PMC?",
    "source_type": "projects",
    "limit": 3,
    "thread_id": "abc-123-def-456",
    "graph_id": "spec_agent"
  },
  "response": {
    "answer": "PMC (Power Management Controller) is...",
    "references": [
      "Project: MTL-BIOS, Document: PMC_Spec.pdf",
      "Project: LNL-Arch, Document: Architecture_Overview.pdf"
    ],
    "metadata": {}
  }
}
```

### Error Output

```json
{
  "status": "error",
  "timestamp": "2026-03-05T10:30:45.123456",
  "query": {
    "question": "What is PMC?",
    "source_type": "projects",
    "thread_id": "abc-123-def-456"
  },
  "response": {
    "error": "HTTP Error: 401 Unauthorized",
    "details": "Invalid credentials"
  }
}
```

## Reading Output in Scripts

### Python Example

```python
import json

with open('./result.json', 'r') as f:
    result = json.load(f)

if result['status'] == 'success':
    print(f"Answer: {result['response']['answer']}")
    print(f"References: {result['response']['references']}")
else:
    print(f"Error: {result['response']['error']}")
```

### Bash Example

```bash
# Check status
STATUS=$(jq -r '.status' ./result.json)

if [ "$STATUS" == "success" ]; then
    # Extract answer
    ANSWER=$(jq -r '.response.answer' ./result.json)
    echo "Answer: $ANSWER"
else
    # Extract error
    ERROR=$(jq -r '.response.error' ./result.json)
    echo "Error: $ERROR"
fi
```

## Common Use Cases for FV Debug

### 1. Register Specification Lookup

```bash
python codesign.py \
  -q "What are the eSPI BootPrep and ResetPrep register offsets and fields?" \
  -output_file ./espi_regs.json \
  --limit 5 \
  --verbose
```

### 2. Architecture Questions

```bash
python codesign.py \
  -q "Explain the boot flow for Nova Lake" \
  -output_file ./boot_flow.json \
  --limit 3
```

### 3. Debug Procedure Lookup

```bash
python codesign.py \
  -q "How do I debug PMC crashes?" \
  -output_file ./pmc_debug.json \
  --limit 5
```

### 4. Conversational Debug Session

```bash
# Initial question
python codesign.py \
  -q "What causes PCIe link training failures?" \
  -output_file ./q1.json \
  -v

# Extract thread_id from q1.json
THREAD_ID=$(jq -r '.query.thread_id' ./q1.json)

# Follow-up
python codesign.py \
  -q "What registers should I check?" \
  -output_file ./q2.json \
  --thread_id $THREAD_ID

# Another follow-up
python codesign.py \
  -q "Show me a debug checklist" \
  -output_file ./q3.json \
  --thread_id $THREAD_ID
```

## Performance Tips

1. **Use `--limit`**: Reducing the number of projects speeds up response time
   - Default: 3 projects
   - For quick queries: `--limit 1` or `--limit 2`
   - For comprehensive answers: `--limit 5` or `--limit 10`

2. **Use `--verbose`**: Monitor progress for long-running queries

3. **Reuse thread_id**: Follow-up questions in the same thread are faster

4. **Choose the right source**:
   - `--source projects`: For architecture/spec questions (default)
   - `--source files`: For questions about your uploaded documents

## Advantages Over BrowserMCP

| Issue | BrowserMCP | This Tool |
|-------|------------|-----------|
| Timing reliability | ❌ 15+ second waits, flaky | ✅ Predictable API calls |
| Session management | ❌ Requires fresh navigation | ✅ Stateless, no session issues |
| Text input | ❌ Fails silently | ✅ Direct API payload |
| Automation | ❌ Unreliable | ✅ Designed for automation |
| Output parsing | ❌ DOM scraping | ✅ Structured JSON |
| Error handling | ❌ Silent failures | ✅ Clear error messages |

## Troubleshooting

### Authentication Errors

```
❌ Error: Missing required environment variables
```

**Solution**: Ensure `.env` file contains `IDSID`, `PASS`, `API_KEY`, `API_SECRET`

### Network Errors

```
❌ HTTP Error: 407 Proxy Authentication Required
```

**Solution**: Verify you're on Intel network or VPN

### Empty Responses

```json
{
  "status": "success",
  "response": {
    "answer": "",
    "references": []
  }
}
```

**Solution**: Try increasing `--limit` or rephrasing the question

## Integration with FV Workflows

### Example: Autonomous Debug Agent

```python
import subprocess
import json

def query_codesign(question, limit=3):
    """Query CoDesign and return structured response"""
    output_file = f"./codesign_query_{uuid.uuid4()}.json"
    
    cmd = [
        "python", "codesign.py",
        "-q", question,
        "-output_file", output_file,
        "--limit", str(limit)
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    
    with open(output_file, 'r') as f:
        return json.load(f)

# Use in debug workflow
response = query_codesign("What are PMC crash indicators?")
if response['status'] == 'success':
    answer = response['response']['answer']
    # Parse answer and take action
    ...
```

## Exit Codes

- `0`: Success - Query completed successfully
- `1`: Error - Authentication, network, or query error

## API Agent Types

### `spec_agent` (Default - Conversational)

- Supports follow-up questions via `thread_id`
- Maintains conversational context
- Best for: Interactive debug sessions

### `spec_rag` (RAG Only)

- No conversational context
- Ignores `thread_id`
- Best for: Single-shot queries

```bash
python codesign.py -q "What is PMC?" -output_file ./result.json --graph_id spec_rag
```

## License

MIT License - Internal Intel tool

## Support

For issues or questions:
- Check `.env` configuration
- Verify Intel network/VPN connection
- Review output JSON for detailed error messages
- Use `--verbose` flag for debugging
