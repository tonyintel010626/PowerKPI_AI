#!/usr/bin/env python3
"""
Helper script to detect Chrome profile paths on Windows
"""

import os
import sys
from pathlib import Path

def find_chrome_profiles():
    """Find all Chrome profile directories on Windows"""
    
    profiles = []
    
    # Windows locations
    if sys.platform == "win32":
        local_appdata = os.getenv('LOCALAPPDATA')
        if local_appdata:
            # Standard Chrome
            chrome_user_data = Path(local_appdata) / "Google" / "Chrome" / "User Data"
            if chrome_user_data.exists():
                for item in chrome_user_data.iterdir():
                    if item.is_dir() and (item.name == "Default" or item.name.startswith("Profile")):
                        profiles.append(str(item))
            
            # Chrome Canary
            canary_user_data = Path(local_appdata) / "Google" / "Chrome SxS" / "User Data"
            if canary_user_data.exists():
                for item in canary_user_data.iterdir():
                    if item.is_dir() and (item.name == "Default" or item.name.startswith("Profile")):
                        profiles.append(str(item))
        
        # Also check AppData\Roaming for Edge
        appdata = os.getenv('APPDATA')
        if appdata:
            edge_user_data = Path(appdata) / "Microsoft" / "Edge" / "User Data"
            if edge_user_data.exists():
                for item in edge_user_data.iterdir():
                    if item.is_dir() and (item.name == "Default" or item.name.startswith("Profile")):
                        profiles.append(str(item) + " [Edge]")
    
    # Linux locations
    elif sys.platform == "linux":
        home = Path.home()
        chrome_dir = home / ".config" / "google-chrome"
        if chrome_dir.exists():
            for item in chrome_dir.iterdir():
                if item.is_dir() and (item.name == "Default" or item.name.startswith("Profile")):
                    profiles.append(str(item))
    
    # macOS locations
    elif sys.platform == "darwin":
        home = Path.home()
        chrome_dir = home / "Library" / "Application Support" / "Google" / "Chrome"
        if chrome_dir.exists():
            for item in chrome_dir.iterdir():
                if item.is_dir() and (item.name == "Default" or item.name.startswith("Profile")):
                    profiles.append(str(item))
    
    return profiles

def main():
    print("Searching for Chrome profiles...\n")
    
    profiles = find_chrome_profiles()
    
    if not profiles:
        print("ERROR: No Chrome profiles found")
        print("\nPlease manually specify your Chrome profile path:")
        print("  Windows: C:\\Users\\<username>\\AppData\\Local\\Google\\Chrome\\User Data\\Default")
        print("  Linux:   ~/.config/google-chrome/Default")
        print("  macOS:   ~/Library/Application Support/Google/Chrome/Default")
        sys.exit(1)
    
    print(f"Found {len(profiles)} Chrome profile(s):\n")
    
    for i, profile in enumerate(profiles, 1):
        # Check if profile has cookies (indication it's been used)
        profile_path = profile.replace(" [Edge]", "")
        cookies_file = Path(profile_path) / "Cookies"
        network_file = Path(profile_path) / "Network" / "Cookies"
        
        has_cookies = cookies_file.exists() or network_file.exists()
        status = "[Active]" if has_cookies else "[Empty]"
        
        print(f"  {i}. {status}")
        print(f"     {profile}\n")
    
    # Export default profile path
    default_profile = profiles[0].replace(" [Edge]", "")
    print(f"Recommended (most recently used):")
    print(f"   {default_profile}\n")
    
    print(f"To use this profile:")
    print(f'   python codesign_playwright.py -q "Your question" -output_file ./result.json -profile "{default_profile}"')

if __name__ == "__main__":
    main()
