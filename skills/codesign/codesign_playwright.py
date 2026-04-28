#!/usr/bin/env python3
"""
Co-De Sign Playwright Automation
Uses existing Chrome profile for authenticated access to chat.co-design.intel.com
Runs headless in background for reliable, predictable queries.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


class CoDesignAutomation:
    """Automated Co-Design chat interface using Playwright"""
    
    def __init__(self, chrome_profile_path: str, headless: bool = True, verbose: bool = False):
        self.chrome_profile_path = chrome_profile_path
        self.headless = headless
        self.verbose = verbose
        self.browser = None
        self.context = None
        self.page = None
        
    def log(self, message: str):
        """Log to stderr if verbose mode enabled"""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", file=sys.stderr)
    
    def start_browser(self):
        """Initialize browser with existing Chrome profile"""
        self.log("Starting Playwright browser...")
        
        playwright = sync_playwright().start()
        
        # Launch Chrome with existing profile
        self.browser = playwright.chromium.launch_persistent_context(
            user_data_dir=self.chrome_profile_path,
            headless=self.headless,
            channel="chrome",  # Use installed Chrome
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ],
            # Intel proxy settings
            proxy={
                "server": "http://proxy-chain.intel.com:911"
            }
        )
        
        self.page = self.browser.new_page() if len(self.browser.pages) == 0 else self.browser.pages[0]
        self.log("✅ Browser started with existing profile")
        
    def navigate_to_codesign(self):
        """Navigate to Co-Design chat interface"""
        self.log("Navigating to chat.co-design.intel.com...")
        
        self.page.goto("https://chat.co-design.intel.com/chat", wait_until="networkidle")
        self.page.wait_for_timeout(2000)  # Wait for dynamic content
        
        self.log("✅ Loaded Co-Design chat page")
        
    def wait_for_ready(self):
        """Wait for chat interface to be ready"""
        self.log("Waiting for chat interface to be ready...")
        
        try:
            # Wait for textarea to be available
            self.page.wait_for_selector("textarea", timeout=10000)
            self.log("✅ Chat interface ready")
            return True
        except PlaywrightTimeout:
            self.log("❌ Timeout waiting for chat interface")
            return False
    
    def ask_question(self, question: str, timeout: int = 60) -> dict:
        """
        Submit question and retrieve answer
        
        Returns:
            dict with keys: status, answer, timestamp, references (if available)
        """
        self.log(f"Submitting question: {question}")
        
        result = {
            "status": "error",
            "question": question,
            "timestamp": datetime.now().isoformat(),
            "answer": None,
            "references": [],
            "error": None
        }
        
        try:
            # Find textarea and clear any existing content
            textarea = self.page.locator("textarea").first
            textarea.click()
            textarea.fill("")  # Clear
            self.page.wait_for_timeout(500)
            
            # Type question
            textarea.type(question, delay=50)  # Slower typing for reliability
            self.page.wait_for_timeout(500)
            
            self.log("Question entered, submitting...")
            
            # Submit (press Enter or click submit button)
            textarea.press("Enter")
            
            # Wait for response - look for the chat feed container
            self.log("Waiting for response...")
            self.page.wait_for_timeout(2000)  # Initial wait
            
            # Wait for loading to complete (adjust selector based on actual page)
            # Common patterns: spinner disappears, "generating" text disappears, etc.
            max_wait = timeout
            waited = 0
            
            while waited < max_wait:
                # Check if there's new content in chat feed
                chat_feed = self.page.locator(".chat-feed-container, .message-container, .response-container").first
                
                if chat_feed.count() > 0:
                    content = chat_feed.inner_text()
                    
                    # Check if response is complete (no loading indicators)
                    if content and len(content) > 20:  # Has substantial content
                        # Check for loading indicators
                        loading_indicators = self.page.locator(".loading, .spinner, .generating").count()
                        
                        if loading_indicators == 0:
                            self.log("✅ Response received")
                            break
                
                self.page.wait_for_timeout(1000)
                waited += 1
                
                if waited % 5 == 0:
                    self.log(f"Still waiting... ({waited}s/{max_wait}s)")
            
            # Extract answer from chat feed - try multiple selectors
            answer_text = None
            
            # UI noise patterns to filter out
            ui_noise = [
                'Resources', 'Projects, Wikis', 'My Files', 'HSD', 'Code',
                'Global GPT', 'New!', 'Upload images', 'Image icon',
                'pasting from your clipboard', 'dragging them into',
                'AA\n'  # User avatar prefix
            ]
            
            def clean_text(text):
                """Remove UI noise from extracted text"""
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                filtered_lines = [
                    line for line in lines 
                    if not any(noise in line for noise in ui_noise)
                ]
                return '\n'.join(filtered_lines).strip()
            
            # Try specific message content selectors first
            selectors = [
                ".message-content",
                ".assistant-message",
                ".response-text",
                ".chat-message:last-child",
                "[role='article']:last-child",
                ".markdown-body",
            ]
            
            for selector in selectors:
                elements = self.page.locator(selector)
                if elements.count() > 0:
                    last_elem = elements.last
                    text = clean_text(last_elem.inner_text())
                    if text and len(text) > 10:  # Has meaningful content
                        answer_text = text
                        self.log(f"✅ Extracted answer using selector: {selector}")
                        break
            
            # Fallback to broader selectors
            if not answer_text:
                fallback_selectors = [
                    ".chat-feed-container",
                    ".message-container",
                    ".response-container"
                ]
                for selector in fallback_selectors:
                    elements = self.page.locator(selector)
                    if elements.count() > 0:
                        text = clean_text(elements.last.inner_text())
                        if text and len(text) > 10:
                            answer_text = text
                            self.log(f"✅ Extracted answer using fallback: {selector}")
                            break
            
            if answer_text:
                result["answer"] = answer_text
                result["status"] = "success"
                self.log(f"✅ Final answer length: {len(answer_text)} chars")
                
                # Try to extract references if available
                try:
                    reference_elements = self.page.locator(".reference, .citation, .source, [data-reference]").all()
                    result["references"] = [ref.inner_text().strip() for ref in reference_elements[:10] if ref.inner_text().strip()]
                except:
                    pass  # References are optional
            else:
                result["error"] = "No answer element found in page"
                self.log("❌ Could not find answer in page")
                
        except PlaywrightTimeout:
            result["error"] = f"Timeout after {timeout}s waiting for response"
            self.log(f"❌ Timeout after {timeout}s")
            
        except Exception as e:
            result["error"] = str(e)
            self.log(f"❌ Error: {e}")
        
        return result
    
    def close(self):
        """Clean up browser resources"""
        if self.browser:
            self.log("Closing browser...")
            self.browser.close()
            self.log("✅ Browser closed")


def get_default_chrome_profile():
    """Auto-detect default Chrome profile based on OS"""
    import os
    import platform
    
    system = platform.system()
    
    if system == "Windows":
        profile_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data" / "Default"
    elif system == "Linux":
        profile_path = Path.home() / ".config" / "google-chrome" / "Default"
    elif system == "Darwin":  # macOS
        profile_path = Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "Default"
    else:
        return None
    
    return profile_path if profile_path.exists() else None


def main():
    parser = argparse.ArgumentParser(
        description="Co-De Sign Playwright Automation - Query using existing Chrome profile",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic query (uses default Chrome profile automatically)
  python codesign_playwright.py -q "What is PMC?" -output_file ./result.json
  
  # With custom Chrome profile
  python codesign_playwright.py -q "What is PMC?" -output_file ./result.json -profile "C:/Users/username/AppData/Local/Google/Chrome/User Data/Default"
  
  # Verbose mode with custom timeout
  python codesign_playwright.py -q "Explain eSPI registers" -output_file ./espi.json -v --timeout 120
  
  # Run with visible browser (for debugging)
  python codesign_playwright.py -q "What is PCIe?" -output_file ./pcie.json --no-headless -v
        """
    )
    
    parser.add_argument("-q", "--question", required=True, help="Question to ask Co-De Sign")
    parser.add_argument("-output_file", required=True, help="Output JSON file path")
    parser.add_argument("-profile", "--chrome_profile", default=None, help="Path to Chrome profile directory (auto-detected if not provided)")
    parser.add_argument("--timeout", type=int, default=60, help="Response timeout in seconds (default: 60)")
    parser.add_argument("--no-headless", action="store_true", help="Run browser in visible mode (for debugging)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output to stderr")
    
    args = parser.parse_args()
    
    # Auto-detect or use provided Chrome profile
    if args.chrome_profile:
        profile_path = Path(args.chrome_profile)
    else:
        profile_path = get_default_chrome_profile()
        if profile_path is None:
            print(f"❌ Error: Could not auto-detect Chrome profile", file=sys.stderr)
            print(f"\nPlease specify Chrome profile path with -profile argument", file=sys.stderr)
            print(f"\nCommon Chrome profile locations:", file=sys.stderr)
            print(f"  Windows: C:\\Users\\<username>\\AppData\\Local\\Google\\Chrome\\User Data\\Default", file=sys.stderr)
            print(f"  Linux:   ~/.config/google-chrome/Default", file=sys.stderr)
            print(f"  macOS:   ~/Library/Application Support/Google/Chrome/Default", file=sys.stderr)
            sys.exit(1)
        
        if args.verbose:
            print(f"[AUTO] Using Chrome profile: {profile_path}", file=sys.stderr)
    
    # Validate Chrome profile path
    if not profile_path.exists():
        print(f"❌ Error: Chrome profile path does not exist: {profile_path}", file=sys.stderr)
        print(f"\nCommon Chrome profile locations:", file=sys.stderr)
        print(f"  Windows: C:\\Users\\<username>\\AppData\\Local\\Google\\Chrome\\User Data\\Default", file=sys.stderr)
        print(f"  Linux:   ~/.config/google-chrome/Default", file=sys.stderr)
        print(f"  macOS:   ~/Library/Application Support/Google/Chrome/Default", file=sys.stderr)
        sys.exit(1)
    
    # Initialize automation
    automation = CoDesignAutomation(
        chrome_profile_path=str(profile_path),
        headless=not args.no_headless,
        verbose=args.verbose
    )
    
    try:
        # Start browser and navigate
        automation.start_browser()
        automation.navigate_to_codesign()
        
        if not automation.wait_for_ready():
            result = {
                "status": "error",
                "error": "Chat interface not ready",
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Ask question
            result = automation.ask_question(args.question, timeout=args.timeout)
        
        # Write output
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        if args.verbose:
            print(f"\n✅ Output written to: {args.output_file}", file=sys.stderr)
        
        # Exit with appropriate code
        sys.exit(0 if result["status"] == "success" else 1)
        
    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(error_result, f, indent=2)
        
        print(f"❌ Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
        
    finally:
        automation.close()


if __name__ == "__main__":
    main()
