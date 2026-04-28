#!/usr/bin/env python3
"""
HSDES Query Tool for TCD/TC Creation Skill
===========================================

Queries HSDES for existing TCD/TC records to use as reference material
when creating new or amending existing test cases.

Supports any HSDES tenant — user selects or provides tenant at runtime.

Usage:
  # Query by HSDES article ID (auto-detects tenant)
  python hsdes_query.py --id 15019042073

  # Query by HSDES article ID with explicit tenant
  python hsdes_query.py --id 15019042073 --tenant sighting_central.test_case_definition

  # Query by EQL search within a specific tenant
  python hsdes_query.py --tenant sighting_central.test_case_definition --eql "title LIKE '%ISH%'"

  # Query with custom fields
  python hsdes_query.py --id 15019042073 --fields id,title,description,owner

  # Discover available fields for a record (returns all fields + field list)
  python hsdes_query.py --id 15019042073 --discover-fields

  # List known tenants
  python hsdes_query.py --list-tenants

Output: JSON to stdout
"""

import sys
import json
import argparse


# ============================================================================
# KNOWN TENANTS REGISTRY
# Users can pick from these or supply any custom tenant string.
# ============================================================================
KNOWN_TENANTS = {
    "sighting_central.test_case_definition": {
        "description": "Test Case Definitions (TCD) in Sighting Central",
        "typical_use": "TCD/TC creation and reference lookup",
        "common_fields": "id,title,description,owner,status,system,category,family,family_affected,priority,product_segment,parent_id,val_teams,owner_team"
    },
    "sighting_central": {
        "description": "Sighting Central (cross-domain sightings)",
        "typical_use": "Known issue cross-reference, sighting lookup",
        "common_fields": "id,title,description,owner,status,priority,family_affected"
    },
    "heia_soc.test_case": {
        "description": "Test cases in HEIA SoC tenant (PVIM)",
        "typical_use": "PVIM test case reference lookup",
        "common_fields": "id,title,description,owner,status,forum,sub_forum,project_release,test_case.val_teams,priority"
    },
    "heia_soc.sighting": {
        "description": "Domain sightings in HEIA SoC tenant",
        "typical_use": "Known issue lookup for negative test cases",
        "common_fields": "id,title,description,owner,status,priority,family_affected,release_affected"
    },
    "heia_soc.bug": {
        "description": "Bug tracking in HEIA SoC tenant",
        "typical_use": "Bug-related test case generation",
        "common_fields": "id,title,description,owner,status,priority"
    },
    "heia_soc.feature": {
        "description": "Feature tracking in HEIA SoC tenant",
        "typical_use": "Feature-to-TCD mapping",
        "common_fields": "id,title,description,owner,status"
    },
    "heia_soc.test_result": {
        "description": "Test results in HEIA SoC tenant",
        "typical_use": "Historical test result lookup",
        "common_fields": "id,title,description,owner,status"
    }
}


def list_tenants():
    """Print all known tenants with descriptions."""
    output = {
        "status": "ok",
        "action": "list_tenants",
        "known_tenants": {},
        "note": "You can also use any custom tenant string not listed here."
    }
    for name, info in KNOWN_TENANTS.items():
        output["known_tenants"][name] = {
            "description": info["description"],
            "typical_use": info["typical_use"]
        }
    print(json.dumps(output, indent=2))


def get_default_fields(tenant):
    """Get the default field list for a known tenant, or a generic default."""
    if tenant and tenant in KNOWN_TENANTS:
        return KNOWN_TENANTS[tenant]["common_fields"]
    # Generic fallback
    return "id,title,description,owner,status"


def get_hsdes_client():
    """Initialize HSDES client."""
    try:
        from pysvtools import hsdes
        return hsdes.HSDES()
    except ImportError:
        print(json.dumps({
            "status": "error",
            "error": "pysvtools.hsdes not available. Install pysvtools or use a PythonSV environment.",
            "alternative": "Use browser-based access: navigate to https://hsdes.intel.com/appstore/article/#/<HSDES_ID>"
        }))
        sys.exit(1)


def query_by_id(hsd_id, tenant=None, fields=None, discover=False):
    """
    Fetch a specific HSDES article by ID.

    Args:
        hsd_id: HSDES article ID (integer)
        tenant: Optional tenant string. If None, uses config_by_id() for auto-detection.
        fields: Optional comma-separated field list.
        discover: If True and fields=None, return all available fields.
    """
    hsd = get_hsdes_client()

    # Configure tenant
    if tenant:
        hsd.config(tenant)
    else:
        hsd.config_by_id(hsd_id)

    # Build field list
    if fields:
        show_fields = fields
    elif discover:
        show_fields = None  # Fetch all fields
    else:
        show_fields = get_default_fields(tenant)

    try:
        if show_fields:
            result = hsd.search_id(hsd_id, showFields=show_fields)
        else:
            result = hsd.search_id(hsd_id)

        if result and len(result) > 0:
            record = result[0] if isinstance(result, list) else result
            output = {
                "status": "ok",
                "query_type": "by_id",
                "hsd_id": hsd_id,
                "tenant": tenant or "(auto-detected)",
                "record": record
            }

            # If discovering fields, list all keys found
            if discover and isinstance(record, dict):
                output["available_fields"] = sorted(record.keys())
                output["field_count"] = len(record.keys())

            print(json.dumps(output, indent=2, default=str))
        else:
            print(json.dumps({
                "status": "not_found",
                "query_type": "by_id",
                "hsd_id": hsd_id,
                "tenant": tenant or "(auto-detected)",
                "message": f"No record found for HSDES ID {hsd_id}"
            }))
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "query_type": "by_id",
            "hsd_id": hsd_id,
            "error": str(e)
        }))


def query_by_eql(tenant, eql, fields=None):
    """
    Search HSDES using EQL (Entity Query Language).

    Args:
        tenant: HSDES tenant string (REQUIRED for EQL search).
        eql: EQL query string.
             Supported: =, !=, <, >, AND, OR, NOT, LIKE '%term%', IN ('a','b')
             NOT supported: ~ (tilde), contains(), wildcards (*, ?)
        fields: Optional comma-separated field list.
    """
    hsd = get_hsdes_client()
    hsd.config(tenant)

    show_fields = fields if fields else get_default_fields(tenant)

    try:
        results = hsd.search(eql, showFields=show_fields)

        if results:
            records = results if isinstance(results, list) else [results]
            print(json.dumps({
                "status": "ok",
                "query_type": "eql_search",
                "tenant": tenant,
                "eql": eql,
                "result_count": len(records),
                "records": records
            }, indent=2, default=str))
        else:
            print(json.dumps({
                "status": "no_results",
                "query_type": "eql_search",
                "tenant": tenant,
                "eql": eql,
                "message": "No records matched the query"
            }))
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "query_type": "eql_search",
            "tenant": tenant,
            "eql": eql,
            "error": str(e)
        }))


def main():
    parser = argparse.ArgumentParser(
        description="HSDES Query Tool — Generic, tenant-configurable",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch by ID (auto-detect tenant)
  python hsdes_query.py --id 15019042073

  # Fetch by ID from specific tenant
  python hsdes_query.py --id 15019042073 --tenant sighting_central.test_case_definition

  # Discover all available fields for a record
  python hsdes_query.py --id 15019042073 --discover-fields

  # EQL search in a tenant
  python hsdes_query.py --tenant sighting_central.test_case_definition \\
    --eql "title LIKE '%ISH%' AND status = 'open'"

  # EQL search with custom fields
  python hsdes_query.py --tenant heia_soc.test_case \\
    --eql "title LIKE '%sensor%'" \\
    --fields "id,title,description,owner,status,priority"

  # List known tenants
  python hsdes_query.py --list-tenants

Known tenants (use --list-tenants for details):
  sighting_central.test_case_definition   TCD/TC definitions
  sighting_central                        Cross-domain sightings
  heia_soc.test_case                      PVIM test cases
  heia_soc.sighting                       Domain sightings
  heia_soc.bug                            Bug tracking
  heia_soc.feature                        Feature tracking
  heia_soc.test_result                    Test results
  <custom>                                Any tenant string you provide
        """
    )

    parser.add_argument("--id", type=int,
                        help="HSDES article ID to fetch")
    parser.add_argument("--tenant", type=str, default=None,
                        help="HSDES tenant string. Required for --eql. "
                             "Optional for --id (auto-detected if omitted). "
                             "Use --list-tenants to see known options.")
    parser.add_argument("--eql", type=str,
                        help="EQL query string (requires --tenant). "
                             "Use LIKE '%%term%%' for partial matching.")
    parser.add_argument("--fields", type=str, default=None,
                        help="Comma-separated field list. If omitted, uses "
                             "tenant-specific defaults.")
    parser.add_argument("--discover-fields", action="store_true",
                        help="With --id: fetch all fields to discover schema")
    parser.add_argument("--list-tenants", action="store_true",
                        help="List all known HSDES tenants with descriptions")

    args = parser.parse_args()

    # List tenants mode
    if args.list_tenants:
        list_tenants()
        return

    # Validation
    if not args.id and not args.eql:
        parser.error("Must provide --id, --eql, or --list-tenants")

    if args.eql and not args.tenant:
        parser.error("--eql requires --tenant (use --list-tenants to see options)")

    if args.discover_fields and not args.id:
        parser.error("--discover-fields requires --id")

    # Execute query
    if args.id:
        query_by_id(
            hsd_id=args.id,
            tenant=args.tenant,
            fields=args.fields,
            discover=args.discover_fields
        )
    elif args.eql:
        query_by_eql(
            tenant=args.tenant,
            eql=args.eql,
            fields=args.fields
        )


if __name__ == "__main__":
    main()
