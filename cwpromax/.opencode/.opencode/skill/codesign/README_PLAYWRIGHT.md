# Co-De Sign Playwright Automation

Standalone Playwright-based automation tool for querying Intel's Co-De Sign knowledge base using your existing Chrome profile. Runs headless in background for reliable, predictable queries without browserMCP timing issues.

## Features

✅ **Auto-Detects Chrome Profile** - Automatically uses your default Chrome profile  
✅ **Uses Existing Authentication** - No API keys needed, leverages Intel SSO  
✅ **Headless Background Execution** - Runs invisibly by default  
✅ **Structured JSON Output** - Easy to parse programmatically  
✅ **Clean Answer Extraction** - Filters out UI noise automatically  
✅ **Verbose Mode** - Progress tracking with `--verbose`  
✅ **Custom Timeout** - Configure response wait time  
✅ **Reliable** - More predictable than browserMCP  

## Prerequisites

```bash
# Install Playwright (if not already installed)
pip install playwright

# Install browser drivers
playwright install chromium
```

## Usage

### Basic Query (Auto-Detected Profile)

```bash
# Chrome profile is automatically detected - no -profile flag needed!
python codesign_playwright.py \
  -q "What is PMC in Intel SoC architecture?" \
  -output_file ./result.json
```

### Custom Chrome Profile

```bash
# Specify custom profile if needed
python codesign_playwright.py \
  -q "What is PMC?" \
  -output_file ./result.json \
  -profile "C:\Users\username\AppData\Local\Google\Chrome\User Data\Profile 1"
```

### 2. Install Playwright Browsers

```bash
playwright install chromium
```

## 🚀 Quick Start

### Find Your Chrome Profile Path

**Windows:**
```
C:\Users\<username>\AppData\Local\Google\Chrome\User Data\Default
```

**Linux:**
```
~/.config/google-chrome/Default
```

**macOS:**
```
~/Library/Application Support/Google/Chrome/Default
```

**Tip:** If you use a different Chrome profile, replace "Default" with your profile name (e.g., "Profile 1", "Profile 2").

### Basic Usage

```bash
python codesign_playwright.py \
  -q "What is PMC in Intel SoC?" \
  -output_file ./result.json \
  -profile "C:/Users/aabdulmu/AppData/Local/Google/Chrome/User Data/Default" \
  -v
```

## 📖 Command-Line Options

| Option | Required | Description | Default |
|--------|----------|-------------|---------|
| `-q`, `--question` | ✅ | Question to ask | - |
| `-output_file` | ✅ | Output JSON file path | - |
| `-profile`, `--chrome_profile` | ✅ | Chrome profile directory path | - |
| `--timeout` | ❌ | Response timeout (seconds) | 60 |
| `--no-headless` | ❌ | Show browser window (debugging) | False |
| `-v`, `--verbose` | ❌ | Progress output to stderr | False |

## 💡 Usage Examples

### Example 1: Basic Query

```bash
python codesign_playwright.py \
  -q "What are eSPI BootPrep and ResetPrep registers?" \
  -output_file ./espi_regs.json \
  -profile "./chrome_profile"
```

### Example 2: Verbose Mode with Custom Timeout

```bash
python codesign_playwright.py \
  -q "Explain PMC crash scenarios" \
  -output_file ./pmc_crashes.json \
  -profile "C:/Users/aabdulmu/AppData/Local/Google/Chrome/User Data/Default" \
  -v \
  --timeout 120
```

### Example 3: Debug Mode (Visible Browser)

```bash
python codesign_playwright.py \
  -q "What is the PCIe enumeration process?" \
  -output_file ./pcie.json \
  -profile "./chrome_profile" \
  --no-headless \
  -v
```

### Example 4: FV Debug Workflow - Architecture Lookup

```bash
# Query register information
python codesign_playwright.py \
  -q "What are the THC interrupt registers and their offsets?" \
  -output_file ./thc_interrupts.json \
  -profile "$CHROME_PROFILE" \
  -v

# Parse the result
jq -r '.answer' ./thc_interrupts.json
```

## 📊 Output Format

### Success Response

```json
{
  "status": "success",
  "question": "What is PMC?",
  "timestamp": "2026-03-05T15:30:45.123456",
  "answer": "PMC (Power Management Controller) is a critical component in Intel SoCs responsible for...",
  "references": [
    "MTL Platform Design Guide - Section 4.2",
    "PMC Programming Manual v1.3"
  ],
  "error": null
}
```

### Error Response

```json
{
  "status": "error",
  "question": "What is PMC?",
  "timestamp": "2026-03-05T15:30:45.123456",
  "answer": null,
  "references": [],
  "error": "Timeout after 60s waiting for response"
}
```

## 🔧 Integration Examples

### Bash Script Integration

```bash
#!/bin/bash

CHROME_PROFILE="C:/Users/aabdulmu/AppData/Local/Google/Chrome/User Data/Default"
OUTPUT_FILE="./codesign_result.json"

# Run query
python codesign_playwright.py \
  -q "$1" \
  -output_file "$OUTPUT_FILE" \
  -profile "$CHROME_PROFILE"

# Check status
STATUS=$(jq -r '.status' "$OUTPUT_FILE")

if [ "$STATUS" == "success" ]; then
  echo "✅ Success:"
  jq -r '.answer' "$OUTPUT_FILE"
  exit 0
else
  echo "❌ Error:"
  jq -r '.error' "$OUTPUT_FILE"
  exit 1
fi
```

### Python Integration

```python
import json
import subprocess
import sys

def query_codesign(question: str, chrome_profile: str) -> dict:
    """Query Co-De Sign and return parsed result"""
    
    output_file = "./temp_codesign_result.json"
    
    result = subprocess.run([
        "python", "codesign_playwright.py",
        "-q", question,
        "-output_file", output_file,
        "-profile", chrome_profile
    ], capture_output=True, text=True)
    
    with open(output_file, 'r') as f:
        return json.load(f)

# Usage
chrome_profile = "C:/Users/aabdulmu/AppData/Local/Google/Chrome/User Data/Default"
result = query_codesign("What is PMC?", chrome_profile)

if result['status'] == 'success':
    print(f"Answer: {result['answer']}")
else:
    print(f"Error: {result['error']}")
```

## 🐛 Troubleshooting

### Issue: "Chrome profile path does not exist"

**Solution:** Verify your Chrome profile path:

```bash
# Windows
dir "C:\Users\<username>\AppData\Local\Google\Chrome\User Data\Default"

# Linux/macOS
ls -la ~/.config/google-chrome/Default
```

### Issue: "Timeout waiting for response"

**Solutions:**
1. Increase timeout: `--timeout 120`
2. Check if you're authenticated: Run with `--no-headless -v` to see the browser
3. Navigate to https://chat.co-design.intel.com manually first to verify access

### Issue: "Chat interface not ready"

**Solutions:**
1. Ensure you're logged into Intel SSO in your Chrome profile
2. Try opening https://chat.co-design.intel.com in Chrome manually first
3. Run with `--no-headless -v` to debug

### Issue: Playwright not installed

**Solution:**
```bash
pip install playwright
playwright install chromium
```

### Issue: Proxy errors

**Solution:** The script uses Intel proxy (`proxy-chain.intel.com:911`). If you're off-network:
- Connect to Intel VPN first
- Or remove proxy settings from the script (edit `codesign_playwright.py`)

## 🔐 Security Notes

- **Profile Access:** Script uses your existing Chrome profile (read-only for cookies/session)
- **No Credentials Stored:** Leverages existing browser authentication
- **Session Reuse:** Uses your active Intel SSO session

## 🆚 Comparison: API vs Playwright

| Feature | API Method (`codesign.py`) | Playwright Method (`codesign_playwright.py`) |
|---------|---------------------------|---------------------------------------------|
| **Authentication** | Requires API_KEY, API_SECRET | Uses existing Chrome session ✅ |
| **Setup Complexity** | Need to obtain API credentials | Just need Chrome profile path ✅ |
| **Reliability** | Direct API (very reliable) ✅ | Browser automation (good reliability) |
| **Speed** | Fast (~2-5s) ✅ | Slower (~5-15s) |
| **Maintenance** | Requires credential management | No credentials needed ✅ |

### When to Use Each

**Use API Method (`codesign.py`)** when:
- You have API credentials
- Speed is critical
- Running in automated pipelines

**Use Playwright Method (`codesign_playwright.py`)** when:
- You don't have API credentials ✅ **Most FV users**
- You want quick setup without credential requests
- You already have Chrome authenticated

## 📝 Advanced Usage

### Custom Selectors

If Co-De Sign UI changes, you can modify selectors in the script:

```python
# Edit these in codesign_playwright.py
textarea = self.page.locator("textarea").first  # Input field
chat_feed = self.page.locator(".chat-feed-container").first  # Response area
```

### Multiple Queries in Sequence

```bash
#!/bin/bash
PROFILE="./chrome_profile"

questions=(
  "What is PMC?"
  "What are eSPI registers?"
  "Explain PCIe enumeration"
)

for i in "${!questions[@]}"; do
  python codesign_playwright.py \
    -q "${questions[$i]}" \
    -output_file "./q${i}.json" \
    -profile "$PROFILE"
done
```

## 🎓 For FV Engineers

This tool is particularly useful for:

- **Register lookups** during debug sessions
- **Architecture queries** when writing test cases  
- **Spec clarification** without manual browsing
- **Automated documentation** generation

Example FV workflow:

```bash
# Debug THC interrupt issue
python codesign_playwright.py \
  -q "What are THC interrupt enable registers and default values?" \
  -output_file ./thc_int.json \
  -profile "$CHROME_PROFILE" \
  -v

# Parse and use in debug
REGISTERS=$(jq -r '.answer' ./thc_int.json)
echo "Checking registers: $REGISTERS"

# Use with PythonSV to check actual values
python check_registers.py --info "$REGISTERS"
```

## 📚 See Also

- `codesign.py` - API-based method (requires credentials)
- `codesign_api.py` - Original API script
- `SKILL.md` - Complete Co-De Sign skill documentation
