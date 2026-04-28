# > **Owner**: Chin, William Willy (`willychi`)
# Support: For any issues, contact the owner above. Please collect the complete
#          session transcript (AI log dump) before reporting for faster root-cause analysis.
"""Co-De Sign access connectivity test.

Tests multiple authentication methods (direct, proxy, Kerberos) against
Intel's Co-De Sign chat service (chat.co-design.intel.com) to determine
which access path works from the current host. One-off investigation script.
"""
# Co-De Sign access script - tries multiple auth methods
import requests
import json
import sys
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://chat.co-design.intel.com"
PROXIES = {
    "https": "http://proxy-chain.intel.com:912",
    "http": "http://proxy-chain.intel.com:911"
}
NO_PROXY = {"https": None, "http": None}

def try_access(label, url, proxies, verify=False, auth=None, headers=None):
    """Try accessing a URL with given config"""
    print(f"\n--- {label} ---")
    try:
        r = requests.get(url, proxies=proxies, verify=verify, auth=auth, 
                        headers=headers, timeout=30, allow_redirects=True)
        print(f"Status: {r.status_code}")
        print(f"URL: {r.url}")
        print(f"Headers: {dict(list(r.headers.items())[:5])}")
        if r.status_code == 200:
            content = r.text[:500]
            print(f"Content: {content}")
        return r
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return None

# Test 1: Direct access (no proxy) - Co-De Sign may be intranet
print("=" * 60)
print("TEST 1: Direct access (no proxy)")
try_access("Direct /api/health", f"{BASE_URL}/api/health", NO_PROXY)

# Test 2: With proxy
print("\n" + "=" * 60)
print("TEST 2: With proxy")
try_access("Proxy /api/health", f"{BASE_URL}/api/health", PROXIES)

# Test 3: Try Kerberos auth (if requests_kerberos available)
print("\n" + "=" * 60)
print("TEST 3: Kerberos auth")
try:
    from requests_kerberos import HTTPKerberosAuth, OPTIONAL
    kerberos_auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)
    try_access("Kerberos direct", f"{BASE_URL}/api/health", NO_PROXY, auth=kerberos_auth)
    try_access("Kerberos proxy", f"{BASE_URL}/api/health", PROXIES, auth=kerberos_auth)
except ImportError:
    print("requests_kerberos not installed")
    # Try requests_negotiate_sspi (Windows SSPI)
    try:
        from requests_negotiate_sspi import HttpNegotiateAuth
        sspi_auth = HttpNegotiateAuth()
        try_access("SSPI direct", f"{BASE_URL}/api/health", NO_PROXY, auth=sspi_auth)
        try_access("SSPI proxy", f"{BASE_URL}/api/health", PROXIES, auth=sspi_auth)
    except ImportError:
        print("requests_negotiate_sspi not installed either")

# Test 4: Try NTLM auth
print("\n" + "=" * 60)
print("TEST 4: NTLM auth")
try:
    from requests_ntlm import HttpNtlmAuth
    # Use machine account
    import getpass
    user = os.environ.get('USERNAME', getpass.getuser())
    ntlm_auth = HttpNtlmAuth(f'INTEL\\{user}', '')
    try_access("NTLM direct", f"{BASE_URL}/chat", NO_PROXY, auth=ntlm_auth)
except ImportError:
    print("requests_ntlm not installed")

# Test 5: Check what auth libraries are available
print("\n" + "=" * 60)
print("TEST 5: Available auth libraries")
for lib in ['requests_kerberos', 'requests_negotiate_sspi', 'requests_ntlm', 
            'requests_gssapi', 'sspilib', 'winkerberos', 'pyspnego']:
    try:
        __import__(lib)
        print(f"  {lib}: AVAILABLE")
    except ImportError:
        print(f"  {lib}: not installed")

# Test 6: Try the Co-De Sign Swagger docs endpoint
print("\n" + "=" * 60)
print("TEST 6: Swagger docs")
try_access("Swagger direct", f"{BASE_URL}/docs", NO_PROXY)
try_access("Swagger proxy", f"{BASE_URL}/docs", PROXIES)

# Test 7: Try docs.intel.com THC HAS
print("\n" + "=" * 60)
print("TEST 7: docs.intel.com THC HAS")
HAS_URL = "https://docs.intel.com/documents/iparch/thc/THC_IP/4.x/IP%20Specs/HAS/SIP_THC_4x_HAS/SIP_THC_4x_HAS.html"
try_access("THC HAS direct", HAS_URL, NO_PROXY)
try_access("THC HAS proxy", HAS_URL, PROXIES)
