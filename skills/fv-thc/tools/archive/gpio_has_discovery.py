# > **Owner**: Chin, William Willy (`willychi`)
"""
GPIO HAS Discovery: Find and extract vGPIO/wake content from GPIO IP HAS on docs.intel.com
Tries multiple URL patterns to find the GPIO IP HAS document.
"""
import requests
from requests_kerberos import HTTPKerberosAuth, OPTIONAL
import re
import sys
from html.parser import HTMLParser

class TextExtractor(HTMLParser):
    """Extract text from HTML, preserving structure."""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_script = False
        self.in_style = False
    
    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.in_script = True
        elif tag == 'style':
            self.in_style = True
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.text_parts.append(f'\n\n### ')
        elif tag in ('p', 'div', 'br', 'tr', 'li'):
            self.text_parts.append('\n')
        elif tag == 'td':
            self.text_parts.append(' | ')
    
    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_script = False
        elif tag == 'style':
            self.in_style = False
    
    def handle_data(self, data):
        if not self.in_script and not self.in_style:
            self.text_parts.append(data)
    
    def get_text(self):
        return ''.join(self.text_parts)

def try_url(url, auth, proxies):
    """Try to fetch a URL, return (status, content_length, content_type) or error."""
    try:
        r = requests.get(url, auth=auth, proxies=proxies, timeout=30, verify=True, allow_redirects=True)
        ct = r.headers.get('Content-Type', 'unknown')
        return (r.status_code, len(r.content), ct, r.text if r.status_code == 200 else None, r.url)
    except Exception as e:
        return (0, 0, str(e), None, url)

def html_to_text(html):
    """Convert HTML to text."""
    extractor = TextExtractor()
    extractor.feed(html)
    return extractor.get_text()

def search_text(text, keywords, context_lines=10):
    """Search text for keywords, return matches with context."""
    lines = text.split('\n')
    results = {}
    for keyword in keywords:
        pattern = re.compile(keyword, re.IGNORECASE)
        for i, line in enumerate(lines):
            if pattern.search(line):
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                if i not in results:
                    results[i] = {
                        'line': i + 1,
                        'match': line.strip()[:200],
                        'keywords': [keyword],
                        'context': '\n'.join(f"  {j+1}: {lines[j]}" for j in range(start, end))
                    }
                else:
                    results[i]['keywords'].append(keyword)
    return sorted(results.values(), key=lambda x: x['line'])

def main():
    auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL, delegate=True)
    proxies = {'https': 'http://proxy-chain.intel.com:912', 'http': 'http://proxy-chain.intel.com:911'}
    
    # ==========================================
    # Phase 1: Discover GPIO HAS URL
    # ==========================================
    print("=" * 80)
    print("Phase 1: GPIO HAS URL Discovery")
    print("=" * 80)
    
    # Try various URL patterns based on THC HAS URL structure:
    # THC: https://docs.intel.com/documents/iparch/thc/THC_IP/4.x/IP%20Specs/HAS/SIP_THC_4x_HAS/SIP_THC_4x_HAS.html
    # GPIO patterns to try:
    urls_to_try = [
        # Direct IP architecture path patterns (like THC)
        'https://docs.intel.com/documents/iparch/gpio/',
        'https://docs.intel.com/documents/iparch/gpio/GPIO_IP/',
        'https://docs.intel.com/documents/iparch/gpio/GPIO/',
        
        # With version patterns
        'https://docs.intel.com/documents/iparch/gpio/GPIO_IP/4.x/',
        'https://docs.intel.com/documents/iparch/gpio/GPIO_IP/3.x/',
        'https://docs.intel.com/documents/iparch/gpio/GPIO_IP/2.x/',
        'https://docs.intel.com/documents/iparch/gpio/GPIO_IP/1.x/',
        
        # HAS direct paths
        'https://docs.intel.com/documents/iparch/gpio/GPIO_IP/4.x/IP%20Specs/HAS/',
        'https://docs.intel.com/documents/iparch/gpio/GPIO_IP/3.x/IP%20Specs/HAS/',
        
        # Try "gpio_community" or "gpio_com" patterns
        'https://docs.intel.com/documents/iparch/gpio_community/',
        'https://docs.intel.com/documents/iparch/gpio_com/',
        
        # SIP_GPIO patterns (like SIP_THC)
        'https://docs.intel.com/documents/iparch/gpio/GPIO_IP/4.x/IP%20Specs/HAS/SIP_GPIO_4x_HAS/SIP_GPIO_4x_HAS.html',
        'https://docs.intel.com/documents/iparch/gpio/GPIO_IP/3.x/IP%20Specs/HAS/SIP_GPIO_3x_HAS/SIP_GPIO_3x_HAS.html',
        
        # vGPIO specific paths
        'https://docs.intel.com/documents/iparch/vgpio/',
        'https://docs.intel.com/documents/iparch/gpio/vGPIO/',
        
        # GPIO community controller patterns
        'https://docs.intel.com/documents/iparch/gpio_community/GPIO_Community/',
        
        # Try platform-specific GPIO paths
        'https://docs.intel.com/documents/iparch/gpio/PTL/',
        'https://docs.intel.com/documents/iparch/gpio/NVL/',
        'https://docs.intel.com/documents/iparch/gpio/LNL/',
        
        # Try the parent iparch directory to see what IPs are listed
        'https://docs.intel.com/documents/iparch/',
        
        # Try alternative naming conventions
        'https://docs.intel.com/documents/iparch/gpio_controller/',
        'https://docs.intel.com/documents/iparch/gpio_soc/',
        'https://docs.intel.com/documents/iparch/soc_gpio/',
        'https://docs.intel.com/documents/iparch/south_gpio/',
        
        # IOSF/Sideband patterns (GPIO often in south complex)
        'https://docs.intel.com/documents/iparch/pch/',
        'https://docs.intel.com/documents/iparch/south/',
    ]
    
    print(f"\nTrying {len(urls_to_try)} URL patterns...\n")
    
    found_urls = []
    for url in urls_to_try:
        status, size, ct, content, final_url = try_url(url, auth, proxies)
        indicator = "✓" if status == 200 else "✗"
        redirect = f" → {final_url}" if final_url != url else ""
        print(f"  {indicator} [{status}] {size:>8} bytes  {url[:80]}{redirect}")
        if status == 200 and size > 1000:
            found_urls.append((url, size, ct, content, final_url))
    
    print(f"\n{'=' * 80}")
    print(f"Found {len(found_urls)} accessible URLs")
    print(f"{'=' * 80}")
    
    if not found_urls:
        print("\nNo GPIO HAS found via direct URL patterns.")
        print("The GPIO HAS may be under a different path or require Co-De Sign access.")
        return
    
    # ==========================================
    # Phase 2: Extract vGPIO/wake content from found pages
    # ==========================================
    print(f"\n{'=' * 80}")
    print("Phase 2: Extract vGPIO/Wake Content")
    print(f"{'=' * 80}")
    
    gpio_keywords = [
        r'vGPIO',
        r'virtual\s*GPIO',
        r'SW\s*GPIO',
        r'SWGPIO',
        r'wake.*source',
        r'wake.*enable',
        r'wake.*pad',
        r'wake.*pin',
        r'wake.*config',
        r'THC.*wake',
        r'touch.*wake',
        r'WoT',
        r'Wake\s*on\s*Touch',
        r'interrupt.*routing',
        r'interrupt.*wake',
        r'GPE.*wake',
        r'SCI.*wake',
        r'PME.*wake',
        r'pad.*config',
        r'community.*pad',
        r'GPIO.*interrupt.*config',
        r'GPIO.*wake.*config',
        r'GPIO.*power',
        r'GPIO.*D3',
        r'GPIO.*S0ix',
        r'GPIO.*suspend',
        r'GPIO.*resume',
        r'GPIO.*controller.*wake',
    ]
    
    for url, size, ct, content, final_url in found_urls:
        print(f"\n--- {final_url} ({size} bytes) ---")
        
        if 'html' in ct.lower() or 'text' in ct.lower():
            text = html_to_text(content)
            matches = search_text(text, gpio_keywords)
            
            if matches:
                print(f"Found {len(matches)} vGPIO/wake matches:")
                for m in matches[:30]:  # Limit to first 30
                    print(f"\n  Match (Line {m['line']}): {', '.join(m['keywords'])}")
                    print(f"  Text: {m['match']}")
                    print(f"  Context:")
                    print(m['context'])
            else:
                # Still show the page structure so we can find sub-pages
                lines = text.split('\n')
                print(f"No keyword matches, but page has {len(lines)} lines.")
                print("Page structure (first 100 non-empty lines):")
                count = 0
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped and len(stripped) > 3:
                        print(f"  L{i+1}: {stripped[:150]}")
                        count += 1
                        if count >= 100:
                            break
        else:
            print(f"Non-text content type: {ct}")

    # ==========================================
    # Phase 3: If iparch root was found, parse for GPIO links
    # ==========================================
    for url, size, ct, content, final_url in found_urls:
        if 'iparch/' in url and url.endswith('iparch/'):
            print(f"\n{'=' * 80}")
            print("Phase 3: Parse iparch root for GPIO-related links")
            print(f"{'=' * 80}")
            
            # Find all links in the page
            link_pattern = re.compile(r'href=["\']([^"\']*gpio[^"\']*)["\']', re.IGNORECASE)
            gpio_links = link_pattern.findall(content)
            if gpio_links:
                print(f"\nFound {len(gpio_links)} GPIO-related links:")
                for link in gpio_links:
                    print(f"  {link}")
            else:
                print("\nNo GPIO-specific links found in iparch root.")
                # Try to find ALL links to understand the structure
                all_links = re.compile(r'href=["\']([^"\']+)["\']').findall(content)
                print(f"\nAll links on iparch page ({len(all_links)} total):")
                for link in all_links[:50]:
                    print(f"  {link}")

if __name__ == '__main__':
    main()
