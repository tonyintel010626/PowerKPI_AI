# > **Owner**: Chin, William Willy (`willychi`)
"""
THC HAS Deep Dive: Extract ALL vGPIO, WoT, WoG, wake, UGD content
Accesses docs.intel.com THC HAS via Kerberos auth
"""
import requests
from requests_kerberos import HTTPKerberosAuth, OPTIONAL
import re
import json
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

def fetch_has():
    """Fetch THC HAS via Kerberos auth."""
    url = 'https://docs.intel.com/documents/iparch/thc/THC_IP/4.x/IP%20Specs/HAS/SIP_THC_4x_HAS/SIP_THC_4x_HAS.html'
    proxies = {'https': 'http://proxy-chain.intel.com:912', 'http': 'http://proxy-chain.intel.com:911'}
    auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL, delegate=True)
    r = requests.get(url, auth=auth, proxies=proxies, timeout=60, verify=True)
    if r.status_code != 200:
        print(f"ERROR: HTTP {r.status_code}", file=sys.stderr)
        sys.exit(1)
    return r.text

def html_to_text(html):
    """Convert HTML to text preserving structure."""
    extractor = TextExtractor()
    extractor.feed(html)
    return extractor.get_text()

def extract_sections(text, keywords, context_lines=15):
    """Extract sections around keyword matches with context."""
    lines = text.split('\n')
    results = {}
    for keyword in keywords:
        pattern = re.compile(keyword, re.IGNORECASE)
        for i, line in enumerate(lines):
            if pattern.search(line):
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                section_key = f"L{i+1}:{keyword}"
                context = '\n'.join(f"  {j+1}: {lines[j]}" for j in range(start, end))
                results[section_key] = {
                    'line': i + 1,
                    'match': line.strip(),
                    'keyword': keyword,
                    'context': context
                }
    return results

def main():
    print("=== THC HAS Deep Dive: vGPIO / WoT / WoG / Wake / UGD ===", file=sys.stderr)
    print("Fetching THC HAS from docs.intel.com...", file=sys.stderr)
    
    html = fetch_has()
    print(f"Fetched {len(html)} bytes of HTML", file=sys.stderr)
    
    text = html_to_text(html)
    print(f"Converted to {len(text)} chars of text", file=sys.stderr)
    
    # Define search keywords
    keywords = [
        r'vGPIO',
        r'SWGPIO',
        r'SW\s*GPIO',
        r'Wake\s*on\s*Gesture',
        r'WoG',
        r'Wake\s*on\s*Touch',
        r'WoT',
        r'wake.*interrupt',
        r'wake.*signal',
        r'pmc.*wake',
        r'wake.*pmc',
        r'UGD',
        r'un.?gated',
        r'always.?on',
        r'power.?domain',
        r'EWOG',
        r'RWOGC',
        r'TSEQ_CNTRL',
        r'INT_EDG_DET',
        r'arm.*wake',
        r'wake.*arm',
        r'ISH',
        r'gesture.*match',
        r'touch.*wake',
        r'D3.*wake',
        r'S0ix.*wake',
        r'connected.*standby.*wake',
        r'device_may_wakeup',
        r'dedicated.*wake',
        r'WAKE_ON_GEST',
        r'THC_TSI_WAKE',
        r'THC_SPI_WAKE',
    ]
    
    print(f"Searching {len(keywords)} keyword patterns...", file=sys.stderr)
    results = extract_sections(text, keywords, context_lines=10)
    
    # Deduplicate by line number (same line may match multiple keywords)
    by_line = {}
    for key, result in results.items():
        line = result['line']
        if line not in by_line:
            by_line[line] = result
            by_line[line]['keywords'] = [result['keyword']]
        else:
            by_line[line]['keywords'].append(result['keyword'])
    
    # Sort by line number
    sorted_results = sorted(by_line.values(), key=lambda x: x['line'])
    
    print(f"\nFound {len(sorted_results)} unique locations with matches\n", file=sys.stderr)
    
    # Output detailed results
    print("=" * 80)
    print("THC HAS vGPIO/WoT/WoG/Wake/UGD Deep Dive")
    print(f"Source: docs.intel.com THC 4.x HAS ({len(html)} bytes)")
    print(f"Unique match locations: {len(sorted_results)}")
    print("=" * 80)
    
    for i, result in enumerate(sorted_results, 1):
        print(f"\n--- Match {i}/{len(sorted_results)} (Line {result['line']}) ---")
        print(f"Keywords: {', '.join(result['keywords'])}")
        print(f"Match: {result['match'][:200]}")
        print(f"Context:")
        print(result['context'])
    
    # Also do a broad section extraction for major topics
    print("\n\n" + "=" * 80)
    print("BROAD SECTION EXTRACTIONS")
    print("=" * 80)
    
    lines = text.split('\n')
    
    # Find section headers related to our topics
    section_headers = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.search(r'(wake|power|interrupt|vGPIO|WoG|WoT|gesture|UGD|ungated|domain)', stripped, re.IGNORECASE):
            if re.search(r'^#+\s|^[A-Z].*:$|^\d+\.\d+', stripped):
                section_headers.append((i, stripped))
    
    print(f"\nSection headers related to wake/power/interrupt:")
    for line_num, header in section_headers:
        print(f"  L{line_num+1}: {header[:120]}")

if __name__ == '__main__':
    main()
