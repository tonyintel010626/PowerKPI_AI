#!/usr/bin/env python3
"""
Batch-create Test Results (TRs) for all leaf Test Cases under an HSDES MTP hierarchy.

Usage:
    # Dry-run: show what would be created (no writes) — replace <ROOT_ID> with your MTP root
    python hsdes_mtp_create_trs.py --root <ROOT_ID> --dry-run

    # Create TRs for all leaf TCs
    python hsdes_mtp_create_trs.py --root <ROOT_ID>

    # Cleanup test TRs by marking them rejected
    python hsdes_mtp_create_trs.py --cleanup <TR_ID_1> <TR_ID_2>

    # Create TRs only for TCs that don't already have one
    python hsdes_mtp_create_trs.py --root <ROOT_ID> --skip-existing

Auth: Kerberos (NOT pysvtools.hsdes — proven broken for /links endpoint).
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import requests
from requests_kerberos import HTTPKerberosAuth, OPTIONAL

HSDES_API_BASE = "https://hsdes-api.intel.com/rest"
TENANT = "sighting_central"

# Rate limiting: HSDES can be sensitive to burst traffic
BATCH_DELAY_SEC = 0.5  # delay between TR creations
MAX_RETRIES = 3
RETRY_DELAY_SEC = 2.0

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


@dataclass
class CreateResult:
    """Result of a single TR creation attempt."""

    tc_id: str
    tc_title: str
    tr_id: Optional[str] = None
    tr_title: Optional[str] = None
    status: str = "pending"  # pending, created, skipped, failed
    error: Optional[str] = None


def make_session() -> requests.Session:
    """Create a Kerberos-authenticated session."""
    session = requests.Session()
    session.auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)
    session.headers.update(
        {"Content-Type": "application/json", "Accept": "application/json"}
    )
    return session


def get_article(
    session: requests.Session, article_id: str, base_url: str = HSDES_API_BASE
) -> Optional[Dict]:
    """Fetch a single HSDES article."""
    url = f"{base_url}/article/{article_id}"
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [{}])[0] if data.get("data") else None
    except Exception as e:
        log.error(f"Failed to fetch article {article_id}: {e}")
        return None


def get_children(
    session: requests.Session, article_id: str, base_url: str = HSDES_API_BASE
) -> List[Dict]:
    """Get child articles via /links endpoint.

    The HSDES /links endpoint returns:
      {"responses": [{"id": ..., "title": ..., "relationship": "parent-child", ...}, ...]}
    NOT {"data": [{"link_type": ..., "from_id": ..., "to_id": ...}]}.
    """
    url = f"{base_url}/article/{article_id}/links"
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        children = []
        for item in data.get("responses", []):
            if item.get("relationship") == "parent-child":
                children.append(
                    {
                        "id": str(item.get("id", "")),
                        "title": item.get("title", ""),
                        "subject": item.get("subject", ""),
                        "status": item.get("status", ""),
                    }
                )
        return children
    except Exception as e:
        log.error(f"Failed to get children for {article_id}: {e}")
        return []


def get_test_results_for_tc(
    session: requests.Session, tc_id: str, base_url: str = HSDES_API_BASE
) -> List[Dict]:
    """Get existing TRs for a specific TC via /children endpoint."""
    url = f"{base_url}/article/{tc_id}/children"
    params = {"child_subject": "test_result", "tenant": TENANT}
    try:
        resp = session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("data", []):
            results.append(
                {
                    "id": str(item.get("id", "")),
                    "title": item.get("title", ""),
                    "status": item.get("status", ""),
                }
            )
        return results
    except Exception as e:
        log.debug(f"Failed to get TRs for TC {tc_id} via /children: {e}")
        # Fallback: try /links
        children = get_children(session, tc_id, base_url)
        return [c for c in children if c.get("subject") == "test_result"]


def collect_leaf_tcs(
    session: requests.Session, root_id: str, base_url: str = HSDES_API_BASE
) -> List[Dict]:
    """Walk the MTP tree and collect all leaf Test Cases (subject=test_case)."""
    log.info(f"Walking tree from root {root_id} to collect leaf TCs...")
    leaf_tcs = []

    def _walk(article_id: str, depth: int = 0):
        children = get_children(session, article_id, base_url)
        if not children:
            return
        for child in children:
            subj = child.get("subject", "")
            status = child.get("status", "")
            if status == "rejected":
                continue
            if subj == "test_case":
                leaf_tcs.append(child)
            elif subj in ("test_plan", "test_case_definition"):
                _walk(child["id"], depth + 1)
            # Skip test_result — those are below TCs

    _walk(root_id)
    log.info(f"Found {len(leaf_tcs)} leaf Test Cases")
    return leaf_tcs


def create_tr(
    session: requests.Session, tc_id: str, tr_title: str, base_url: str = HSDES_API_BASE
) -> Optional[str]:
    """Create a single Test Result under a Test Case. Returns the new TR ID or None."""
    url = f"{base_url}/article"
    payload = {
        "tenant": TENANT,
        "subject": "test_result",
        "fieldValues": [{"title": tr_title}, {"parent_id": tc_id}],
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.post(url, json=payload, timeout=30)
            if resp.status_code in (200, 201):
                data = resp.json()
                new_id = (
                    data.get("new_id")
                    or data.get("id")
                    or data.get("data", {}).get("id")
                )
                if new_id:
                    return str(new_id)
                # Try to extract from response text
                log.warning(
                    f"TR created but ID not in expected field. Response: {resp.text[:200]}"
                )
                return None
            elif resp.status_code == 429:
                wait = RETRY_DELAY_SEC * attempt
                log.warning(
                    f"Rate limited (429). Waiting {wait}s before retry {attempt}/{MAX_RETRIES}"
                )
                time.sleep(wait)
                continue
            else:
                log.error(
                    f"Create TR failed (attempt {attempt}): HTTP {resp.status_code} - {resp.text[:200]}"
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_SEC)
                    continue
                return None
        except Exception as e:
            log.error(f"Create TR exception (attempt {attempt}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SEC)
                continue
            return None
    return None


def update_article_status(
    session: requests.Session,
    article_id: str,
    new_status: str,
    base_url: str = HSDES_API_BASE,
) -> bool:
    """Update an article's status (e.g., mark as 'rejected' for cleanup)."""
    url = f"{base_url}/article/{article_id}"
    payload = {
        "tenant": TENANT,
        "subject": "test_result",
        "fieldValues": [{"status": new_status}],
    }
    try:
        resp = session.put(url, json=payload, timeout=30)
        if resp.status_code in (200, 204):
            log.info(f"Updated article {article_id} status to '{new_status}'")
            return True
        else:
            log.error(
                f"Failed to update {article_id}: HTTP {resp.status_code} - {resp.text[:200]}"
            )
            return False
    except Exception as e:
        log.error(f"Failed to update {article_id}: {e}")
        return False


def make_tr_title(tc_title: str) -> str:
    """Generate a TR title from a TC title.

    Convention: "TR: <TC_title>"
    """
    return f"TR: {tc_title}"


def batch_create_trs(
    session: requests.Session,
    root_id: str,
    base_url: str = HSDES_API_BASE,
    dry_run: bool = False,
    skip_existing: bool = False,
) -> List[CreateResult]:
    """Create TRs for all leaf TCs under the MTP root."""
    leaf_tcs = collect_leaf_tcs(session, root_id, base_url)
    results: List[CreateResult] = []

    if not leaf_tcs:
        log.warning("No leaf TCs found. Nothing to create.")
        return results

    log.info(f"{'[DRY-RUN] ' if dry_run else ''}Processing {len(leaf_tcs)} leaf TCs...")

    for i, tc in enumerate(leaf_tcs, 1):
        tc_id = tc["id"]
        tc_title = tc.get("title", f"TC-{tc_id}")
        tr_title = make_tr_title(tc_title)
        result = CreateResult(tc_id=tc_id, tc_title=tc_title, tr_title=tr_title)

        # Check for existing TRs
        if skip_existing:
            existing_trs = get_test_results_for_tc(session, tc_id, base_url)
            if existing_trs:
                result.status = "skipped"
                result.error = f"Already has {len(existing_trs)} TR(s)"
                results.append(result)
                log.info(
                    f"  [{i}/{len(leaf_tcs)}] SKIP TC {tc_id} — already has {len(existing_trs)} TR(s)"
                )
                continue

        if dry_run:
            result.status = "dry-run"
            results.append(result)
            log.info(
                f"  [{i}/{len(leaf_tcs)}] DRY-RUN: Would create TR '{tr_title}' under TC {tc_id}"
            )
            continue

        # Create the TR
        log.info(f"  [{i}/{len(leaf_tcs)}] Creating TR under TC {tc_id}: '{tr_title}'")
        new_tr_id = create_tr(session, tc_id, tr_title, base_url)
        if new_tr_id:
            result.tr_id = new_tr_id
            result.status = "created"
            log.info(f"    -> Created TR {new_tr_id}")
        else:
            result.status = "failed"
            result.error = "API returned no ID"
            log.error(f"    -> FAILED to create TR for TC {tc_id}")

        results.append(result)

        # Rate limiting
        if i < len(leaf_tcs):
            time.sleep(BATCH_DELAY_SEC)

    return results


def print_summary(results: List[CreateResult]):
    """Print a summary of batch creation results."""
    created = sum(1 for r in results if r.status == "created")
    skipped = sum(1 for r in results if r.status == "skipped")
    failed = sum(1 for r in results if r.status == "failed")
    dry_run = sum(1 for r in results if r.status == "dry-run")
    total = len(results)

    print("\n" + "=" * 70)
    print("BATCH TR CREATION SUMMARY")
    print("=" * 70)
    print(f"  Total TCs processed: {total}")
    if dry_run:
        print(f"  Would create:        {dry_run}")
    else:
        print(f"  Created:             {created}")
    print(f"  Skipped (existing):  {skipped}")
    print(f"  Failed:              {failed}")
    print("=" * 70)

    if failed > 0:
        print("\nFAILED TCs:")
        for r in results:
            if r.status == "failed":
                print(f"  TC {r.tc_id}: {r.tc_title} — {r.error}")

    if created > 0:
        print("\nCREATED TRs:")
        for r in results:
            if r.status == "created":
                print(f"  TR {r.tr_id} <- TC {r.tc_id}: {r.tr_title}")


def save_results_json(results: List[CreateResult], output_path: str):
    """Save results to JSON for downstream use."""
    data = []
    for r in results:
        data.append(
            {
                "tc_id": r.tc_id,
                "tc_title": r.tc_title,
                "tr_id": r.tr_id,
                "tr_title": r.tr_title,
                "status": r.status,
                "error": r.error,
            }
        )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "results": data,
                "total": len(data),
                "created": sum(1 for r in results if r.status == "created"),
                "failed": sum(1 for r in results if r.status == "failed"),
                "skipped": sum(1 for r in results if r.status == "skipped"),
            },
            f,
            indent=2,
        )
    log.info(f"Results saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch-create HSDES Test Results for MTP leaf Test Cases"
    )
    parser.add_argument(
        "--root",
        required=True,
        help="MTP root article HSDES ID (get from your FV-agent definition)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without writing",
    )
    parser.add_argument(
        "--skip-existing", action="store_true", help="Skip TCs that already have TRs"
    )
    parser.add_argument(
        "--cleanup",
        nargs="+",
        metavar="ID",
        help="Mark specified TR IDs as rejected (cleanup)",
    )
    parser.add_argument("--output", "-o", help="Save results to JSON file")
    parser.add_argument("--base-url", default=HSDES_API_BASE, help="HSDES API base URL")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip interactive confirmation (use ONLY when user has explicitly approved)",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    session = make_session()

    # Cleanup mode
    if args.cleanup:
        if not args.dry_run and not args.yes:
            print(
                f"\n⚠️  WARNING: This will mark {len(args.cleanup)} articles as rejected in HSDES."
            )
            print("   HSDES changes are PERMANENT and cannot be reverted via REST API.")
            answer = input("\n   Type 'yes' to proceed, anything else to abort: ")
            if answer.strip().lower() != "yes":
                print("   Aborted by user.")
                return
        log.info(f"Cleanup mode: marking {len(args.cleanup)} articles as rejected")
        for article_id in args.cleanup:
            ok = update_article_status(session, article_id, "rejected", args.base_url)
            if ok:
                print(f"  ✓ {article_id} -> rejected")
            else:
                print(f"  ✗ {article_id} -> FAILED")
        return

    # Batch create mode — MANDATORY confirmation gate unless --dry-run or --yes
    if not args.dry_run and not args.yes:
        print("\n" + "=" * 70)
        print("⚠️  HSDES ARTICLE CREATION — REQUIRES EXPLICIT APPROVAL")
        print("=" * 70)
        print(f"  Root:          {args.root}")
        print(f"  Skip existing: {args.skip_existing}")
        print(f"  Action:        CREATE Test Result (TR) articles in HSDES")
        print()
        print("  HSDES articles are PERMANENT — they cannot be deleted or")
        print("  reverted via the REST API (PUT/PATCH returns 405).")
        print()
        print("  Recommendation: Run with --dry-run first to preview changes.")
        print("=" * 70)
        answer = input("\n  Type 'yes' to proceed, anything else to abort: ")
        if answer.strip().lower() != "yes":
            print("  Aborted by user.")
            return
        print()

    results = batch_create_trs(
        session,
        args.root,
        args.base_url,
        dry_run=args.dry_run,
        skip_existing=args.skip_existing,
    )
    print_summary(results)

    if args.output:
        save_results_json(results, args.output)


if __name__ == "__main__":
    main()
