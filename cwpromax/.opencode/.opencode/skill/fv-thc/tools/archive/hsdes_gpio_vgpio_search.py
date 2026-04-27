# > **Owner**: Chin, William Willy (`willychi`)
"""
HSDES Search: Find GPIO vGPIO/wake sightings relevant to THC
Searches multiple tenants for GPIO wake, vGPIO, THC wake sightings.
"""
import sys
import json
from collections import defaultdict

try:
    from pysvtools import hsdes
except ImportError:
    print("ERROR: pysvtools.hsdes not available. Install with: pip install pysvtools", file=sys.stderr)
    sys.exit(1)

def safe_search(tenant, query, fields, label=""):
    """Safely execute an HSDES search, handling errors."""
    try:
        hsdes.config(tenant)
        data = hsdes.search(query, showFields=fields)
        if data:
            print(f"  ✓ [{label}] Found {len(data)} results in {tenant}")
            return data
        else:
            print(f"  - [{label}] No results in {tenant}")
            return []
    except Exception as e:
        print(f"  ✗ [{label}] Error in {tenant}: {e}")
        return []

def safe_search_id(hsd_id, fields=None, label=""):
    """Safely search by ID with auto-tenant detection."""
    try:
        ts = hsdes.config_by_id(hsd_id)
        hsdes.config(ts)
        if fields:
            data = hsdes.search_id(hsd_id, showFields=fields)
        else:
            data = hsdes.search_id(hsd_id)
        if data:
            print(f"  ✓ [{label}] Found record {hsd_id} in {ts}")
            return data[0]
        else:
            print(f"  - [{label}] No record found for {hsd_id}")
            return {}
    except Exception as e:
        print(f"  ✗ [{label}] Error looking up {hsd_id}: {e}")
        return {}

def main():
    common_fields = 'id,title,status,owner,description,submitted_date,updated_date,family_affected,release_affected'
    
    print("=" * 80)
    print("HSDES Search: GPIO vGPIO/Wake + THC Wake Sightings")
    print("=" * 80)
    
    # ==========================================
    # Section 1: Known THC/GPIO Wake HSD IDs
    # ==========================================
    print("\n" + "=" * 80)
    print("Section 1: Known HSD IDs from THC/WoT research")
    print("=" * 80)
    
    known_ids = {
        '22010872659': 'vGPIO FR - test VGPIO interrupt state in wake mode (from Confluence)',
        '16027810168': 'WCL WoT issue - POST code stuck at 0x9B0E (from Confluence)',
        '16014286225': 'THC not fully Chassis 2.2 compliant (from THC HAS)',
        '15010734105': 'PTL+ 16-bit SB port ID breaking change (from THC HAS)',
        '15014172472': 'PRD last entry 4KB alignment RTL bug (from THC HAS)',
    }
    
    for hsd_id, description in known_ids.items():
        print(f"\n--- HSD {hsd_id}: {description} ---")
        record = safe_search_id(hsd_id, fields=common_fields, label=hsd_id)
        if record:
            for key in ['id', 'title', 'status', 'owner', 'family_affected', 'release_affected']:
                if record.get(key):
                    print(f"    {key}: {record[key]}")
            desc = record.get('description', '')
            if desc:
                # Truncate long descriptions
                print(f"    description: {desc[:500]}...")
    
    # ==========================================
    # Section 2: Search sighting tenants for GPIO/vGPIO/THC wake
    # ==========================================
    print("\n" + "=" * 80)
    print("Section 2: Search for GPIO/vGPIO/THC Wake Sightings")
    print("=" * 80)
    
    # Tenants to search
    tenants_to_search = [
        'heia_soc.sighting',
        'sighting_central.sighting',
    ]
    
    # Queries to try - EQL doesn't support wildcards or regex, so use exact terms
    queries = [
        ("title = 'vGPIO'", "vGPIO in title"),
        ("title = 'vgpio'", "vgpio in title (lowercase)"),
        ("title = 'THC wake'", "THC wake in title"),
        ("title = 'THC WoT'", "THC WoT in title"),
        ("title = 'Wake on Touch'", "Wake on Touch in title"),
        ("title = 'SWGPIO'", "SWGPIO in title"),
        ("title = 'GPIO wake'", "GPIO wake in title"),
        ("title = 'touch wake'", "touch wake in title"),
    ]
    
    all_results = []
    for tenant in tenants_to_search:
        print(f"\n--- Searching tenant: {tenant} ---")
        for query, label in queries:
            results = safe_search(tenant, query, common_fields, label)
            for r in results:
                r['_tenant'] = tenant
                r['_query'] = label
            all_results.extend(results)
    
    # ==========================================
    # Section 3: Search client_soc_chipset tenant specifically
    # ==========================================
    print("\n" + "=" * 80)
    print("Section 3: Search client_soc_chipset Tenant")
    print("=" * 80)
    
    # The user specifically asked about client_soc_chipset
    chipset_tenants = [
        'client_soc_chipset.sighting',
        'client_soc_chipset.bug',
        'client_soc_chipset.feature',
    ]
    
    chipset_queries = [
        ("title = 'vGPIO'", "vGPIO"),
        ("title = 'GPIO wake'", "GPIO wake"),
        ("title = 'THC'", "THC"),
        ("title = 'touch'", "touch"),
        ("title = 'SWGPIO'", "SWGPIO"),
        ("title = 'Wake on Touch'", "Wake on Touch"),
        ("title = 'WoT'", "WoT"),
        ("title = 'virtual GPIO'", "virtual GPIO"),
    ]
    
    chipset_results = []
    for tenant in chipset_tenants:
        print(f"\n--- Searching tenant: {tenant} ---")
        for query, label in chipset_queries:
            results = safe_search(tenant, query, common_fields, label)
            for r in results:
                r['_tenant'] = tenant
                r['_query'] = label
            chipset_results.extend(results)
    
    # ==========================================
    # Section 4: Summary
    # ==========================================
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    # Deduplicate by ID
    all_unique = {}
    for r in all_results + chipset_results:
        rid = r.get('id', 'unknown')
        if rid not in all_unique:
            all_unique[rid] = r
    
    print(f"\nTotal unique sightings/records found: {len(all_unique)}")
    
    if all_unique:
        print("\nAll unique results:")
        for rid, r in sorted(all_unique.items()):
            print(f"\n  HSD {rid}:")
            print(f"    Title: {r.get('title', 'N/A')}")
            print(f"    Status: {r.get('status', 'N/A')}")
            print(f"    Owner: {r.get('owner', 'N/A')}")
            print(f"    Tenant: {r.get('_tenant', 'N/A')}")
            print(f"    Query: {r.get('_query', 'N/A')}")
            print(f"    Family: {r.get('family_affected', 'N/A')}")
            print(f"    Release: {r.get('release_affected', 'N/A')}")
    else:
        print("\nNo results found. Possible reasons:")
        print("  1. EQL syntax limitations - 'title = X' requires exact match")
        print("  2. Tenant names may be incorrect - try listing available tenants")
        print("  3. vGPIO/THC wake sightings may be filed under different terms")
        print("  4. Records may be in a different tenant namespace")
        
    # ==========================================
    # Section 5: Try known FR/sighting IDs from our research
    # ==========================================
    print("\n" + "=" * 80)
    print("Section 5: Cross-reference known IDs")
    print("=" * 80)
    
    # Try the vGPIO FR from Confluence
    print("\nLooking up vGPIO FR 22010872659 in detail...")
    record = safe_search_id('22010872659', label='vGPIO-FR')
    if record:
        print(f"\nFull record dump:")
        for key, val in sorted(record.items()):
            if val and not key.startswith('_'):
                val_str = str(val)[:300]
                print(f"  {key}: {val_str}")

if __name__ == '__main__':
    main()
