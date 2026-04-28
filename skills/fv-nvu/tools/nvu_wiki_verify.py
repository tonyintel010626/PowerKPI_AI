#!/usr/bin/env python3
"""
NVU Wiki Verification Tool
============================
Deep wiki-to-skill content verification for NVU sub-skills.
Verifies Confluence wiki pages exist, contain expected content, and cross-reference
correctly against the local NVU skill files.

Ported from: fv-thc/tools/thc_wiki_verify.py (1347 lines)
Adapted for: NVU domain — 11 sub-skills, NVU-specific wiki pages

Modes:
  --offline  : Verify skill files have correct wiki-reference anchors (no network)
  --live     : Fetch actual wiki pages and cross-check (requires Intel network + keyring creds)
  --loop N   : Run N iterations for stability testing

Usage:
    python nvu_wiki_verify.py                # Offline mode (default)
    python nvu_wiki_verify.py --live         # Live wiki fetch + verification
    python nvu_wiki_verify.py --loop 10      # 10 offline iterations
    python nvu_wiki_verify.py --json         # JSON output for CI
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONFLUENCE_BASE = "https://wiki.ith.intel.com"
CONFLUENCE_REST = f"{CONFLUENCE_BASE}/rest/api/content"

# --- Unified credentials import ---
_CRED_DIR = str(Path(__file__).resolve().parent.parent.parent / "credentials")
if _CRED_DIR not in sys.path:
    sys.path.insert(0, _CRED_DIR)
try:
    from intel_credentials import get_credentials as _get_intel_creds
except ImportError:
    _get_intel_creds = None

# NVU Skill file mapping
SKILL_ROOT = Path(__file__).parent.parent
SKILL_FILES = {
    "registers": SKILL_ROOT / "registers" / "SKILL.md",
    "inference": SKILL_ROOT / "inference" / "SKILL.md",
    "dma": SKILL_ROOT / "dma" / "SKILL.md",
    "power": SKILL_ROOT / "power" / "SKILL.md",
    "driver": SKILL_ROOT / "driver" / "SKILL.md",
    "platform": SKILL_ROOT / "platform" / "SKILL.md",
    "debug": SKILL_ROOT / "debug" / "SKILL.md",
    "camera": SKILL_ROOT / "camera" / "SKILL.md",
    "firmware": SKILL_ROOT / "firmware" / "SKILL.md",
    "bios": SKILL_ROOT / "bios" / "SKILL.md",
    "simics": SKILL_ROOT / "simics" / "SKILL.md",
    "root": SKILL_ROOT / "SKILL.md",
    "agent": SKILL_ROOT.parent.parent / "agent" / "FV" / "FV-NVU.md",
}

# NVU Wiki Page Manifest
# These are the expected Confluence wiki pages for NVU validation.
# Format: {id, title, space, priority, skills[], assertions[]}
#
# NOTE: NVU wiki pages may not exist yet (NVU is new IP on TitanLake).
# This manifest serves as a scaffold — populate page IDs once wiki is set up.
WIKI_PAGES = [
    {
        "id": None,  # TBD — page not created yet
        "title": "NVU Functional Validation Overview",
        "space": "FVCommon",
        "priority": 1,
        "skills": ["root", "agent"],
        "assertions": [
            {"type": "contains", "text": "Neural Vision Unit", "skill": "root"},
            {"type": "contains", "text": "NVU", "skill": "agent"},
        ],
    },
    {
        "id": None,
        "title": "NVU Register Map Reference",
        "space": "FVCommon",
        "priority": 1,
        "skills": ["registers"],
        "assertions": [
            {"type": "contains", "text": "MMIO", "skill": "registers"},
            {"type": "contains", "text": "BAR0", "skill": "registers"},
        ],
    },
    {
        "id": None,
        "title": "NVU Inference Engine Debug",
        "space": "FVCommon",
        "priority": 2,
        "skills": ["inference"],
        "assertions": [
            {"type": "contains", "text": "NPX6", "skill": "inference"},
            {"type": "contains", "text": "VPX2", "skill": "inference"},
        ],
    },
    {
        "id": None,
        "title": "NVU DMA Architecture",
        "space": "FVCommon",
        "priority": 2,
        "skills": ["dma"],
        "assertions": [
            {"type": "contains", "text": "DesignWare", "skill": "dma"},
            {"type": "contains", "text": "AXI DMA", "skill": "dma"},
        ],
    },
    {
        "id": None,
        "title": "NVU Power Management Debug",
        "space": "FVCommon",
        "priority": 1,
        "skills": ["power"],
        "assertions": [
            {"type": "contains", "text": "D0i2", "skill": "power"},
            {"type": "contains", "text": "Lid", "skill": "power"},
            {
                "type": "regex",
                "pattern": r"(?i)RTD3|D3hot|power.gat",
                "skill": "power",
            },
        ],
    },
    {
        "id": None,
        "title": "NVU Driver Interface Reference",
        "space": "FVCommon",
        "priority": 2,
        "skills": ["driver"],
        "assertions": [
            {"type": "contains", "text": "IPC", "skill": "driver"},
            {"type": "contains", "text": "PCI", "skill": "driver"},
        ],
    },
    {
        "id": None,
        "title": "NVU Platform Integration (TitanLake)",
        "space": "FVCommon",
        "priority": 1,
        "skills": ["platform"],
        "assertions": [
            {"type": "contains", "text": "TitanLake", "skill": "platform"},
            {"type": "contains", "text": "strap", "skill": "platform"},
        ],
    },
    {
        "id": None,
        "title": "NVU Debug and Triage Guide",
        "space": "DebugEncyclopedia",
        "priority": 1,
        "skills": ["debug"],
        "assertions": [
            {"type": "contains", "text": "DTF", "skill": "debug"},
            {"type": "contains", "text": "VISA", "skill": "debug"},
        ],
    },
    {
        "id": None,
        "title": "NVU Camera Interface Architecture",
        "space": "FVCommon",
        "priority": 2,
        "skills": ["camera"],
        "assertions": [
            {"type": "contains", "text": "MIPI", "skill": "camera"},
            {"type": "contains", "text": "Altek", "skill": "camera"},
        ],
    },
    {
        "id": None,
        "title": "NVU Firmware Loading and Security",
        "space": "FVCommon",
        "priority": 1,
        "skills": ["firmware"],
        "assertions": [
            {"type": "contains", "text": "secure boot", "skill": "firmware"},
            {"type": "contains", "text": "ESE", "skill": "firmware"},
        ],
    },
    {
        "id": None,
        "title": "NVU BIOS Requirements",
        "space": "FVCommon",
        "priority": 1,
        "skills": ["bios"],
        "assertions": [
            {"type": "contains", "text": "BIOS", "skill": "bios"},
            {
                "type": "regex",
                "pattern": r"REQ-BIOS-\d+|NVU.*BIOS.*req",
                "skill": "bios",
            },
        ],
    },
    {
        "id": None,
        "title": "NVU Simics Model Reference",
        "space": "FVCommon",
        "priority": 3,
        "skills": ["simics"],
        "assertions": [
            {"type": "contains", "text": "Simics", "skill": "simics"},
        ],
    },
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("nvu_wiki_verify")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
        )
        logger.addHandler(handler)
    return logger


log = setup_logging()

# ---------------------------------------------------------------------------
# Skill File Reading
# ---------------------------------------------------------------------------

_skill_cache: Dict[str, str] = {}


def read_skill(name: str) -> str:
    """Read and cache a skill file's content."""
    if name not in _skill_cache:
        path = SKILL_FILES.get(name)
        if path and path.exists():
            _skill_cache[name] = path.read_text(encoding="utf-8", errors="replace")
        else:
            _skill_cache[name] = ""
    return _skill_cache[name]


# ---------------------------------------------------------------------------
# Assertion Checking (Offline)
# ---------------------------------------------------------------------------


def check_assertion(assertion: dict) -> dict:
    """
    Check a single assertion against local skill files.
    Returns dict with ok, label, details.
    """
    skill_name = assertion.get("skill", "root")
    content = read_skill(skill_name)
    a_type = assertion.get("type", "contains")

    if a_type == "contains":
        text = assertion["text"]
        found = text.lower() in content.lower()
        return {
            "type": a_type,
            "text": text,
            "skill": skill_name,
            "ok": found,
            "label": f"'{text}' in {skill_name}",
        }
    elif a_type == "regex":
        pattern = assertion["pattern"]
        found = bool(re.search(pattern, content))
        return {
            "type": a_type,
            "pattern": pattern,
            "skill": skill_name,
            "ok": found,
            "label": f"regex '{pattern[:40]}' in {skill_name}",
        }
    else:
        return {
            "type": a_type,
            "ok": False,
            "label": f"Unknown assertion type: {a_type}",
        }


# ---------------------------------------------------------------------------
# Offline Verification
# ---------------------------------------------------------------------------


def run_offline_checks() -> List[dict]:
    """Run offline verification: skill file existence + assertion checks."""
    results = []

    # Check 1: All skill files exist
    log.info("--- Skill File Existence ---")
    for name, path in SKILL_FILES.items():
        exists = path.exists()
        result = {
            "label": f"Skill file exists: {name}",
            "path": str(path),
            "ok": exists,
        }
        if not exists:
            result["error"] = f"Missing: {path}"
        status = "PASS" if exists else "FAIL"
        log.info(f"  [{status}] {name}: {path.name}")
        results.append(result)

    # Check 2: Wiki page manifest completeness
    log.info("\n--- Wiki Manifest Coverage ---")
    skills_covered = set()
    for page in WIKI_PAGES:
        for s in page.get("skills", []):
            skills_covered.add(s)
    skills_expected = set(SKILL_FILES.keys())
    uncovered = skills_expected - skills_covered
    result = {
        "label": "Wiki manifest covers all skills",
        "covered": sorted(skills_covered),
        "uncovered": sorted(uncovered),
        "ok": len(uncovered) == 0,
    }
    log.info(
        f"  [{'PASS' if result['ok'] else 'FAIL'}] Coverage: {len(skills_covered)}/{len(skills_expected)} skills"
    )
    if uncovered:
        log.warning(f"         Uncovered: {uncovered}")
    results.append(result)

    # Check 3: All assertions pass against local skill files
    log.info("\n--- Assertion Verification ---")
    for page in WIKI_PAGES:
        for assertion in page.get("assertions", []):
            a_result = check_assertion(assertion)
            a_result["page_title"] = page["title"]
            status = "PASS" if a_result["ok"] else "FAIL"
            log.info(f"  [{status}] {a_result['label']} (page: {page['title'][:40]})")
            results.append(a_result)

    # Check 4: Wiki page IDs populated
    log.info("\n--- Wiki Page IDs ---")
    pages_with_id = sum(1 for p in WIKI_PAGES if p.get("id") is not None)
    pages_total = len(WIKI_PAGES)
    result = {
        "label": f"Wiki page IDs populated: {pages_with_id}/{pages_total}",
        "ok": True,  # INFO only — IDs may not exist yet
        "severity": "info" if pages_with_id == 0 else "pass",
        "note": "NVU wiki pages not yet created — scaffold only"
        if pages_with_id == 0
        else None,
    }
    log.info(f"  [INFO] {pages_with_id}/{pages_total} pages have Confluence IDs")
    if pages_with_id == 0:
        log.info(f"         (expected — NVU wiki pages not yet created)")
    results.append(result)

    # Check 5: Cross-reference integrity
    log.info("\n--- Cross-Reference Integrity ---")
    root_content = read_skill("root")
    agent_content = read_skill("agent")
    for name in SKILL_FILES:
        if name in ("root", "agent"):
            continue
        # Check sub-skill is referenced in root SKILL.md
        in_root = name.lower() in root_content.lower()
        result = {
            "label": f"Root SKILL.md references '{name}'",
            "ok": in_root,
        }
        if not in_root:
            result["error"] = f"Sub-skill '{name}' not found in root SKILL.md"
        log.info(f"  [{'PASS' if in_root else 'FAIL'}] root -> {name}")
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Live Wiki Verification
# ---------------------------------------------------------------------------


def _get_wiki_session():
    """Create authenticated session for Confluence using unified credentials."""
    try:
        import requests
    except ImportError as e:
        log.error(f"Missing dependency: {e}")
        return None

    session = requests.Session()
    session.verify = False

    # Use unified credential manager
    if _get_intel_creds is not None:
        try:
            username, password = _get_intel_creds()
            session.auth = (username, password)
            log.info(f"  Using unified credentials for user: {username}")
            return session
        except Exception as e:
            log.warning(f"  Unified credentials failed: {e}")

    # Fallback: environment variables
    username = os.environ.get("CONFLUENCE_USER")
    password = os.environ.get("CONFLUENCE_PASS")
    if username and password:
        session.auth = (username, password)
        log.info(f"  Using environment variable credentials for user: {username}")
        return session

    log.error(
        "  No credentials available — run: python intel_credentials.py --refresh"
    )
    return None


def read_wiki_page(session, page_id: str, retries: int = 2) -> Optional[str]:
    """Fetch wiki page content by ID."""
    url = f"{CONFLUENCE_REST}/{page_id}?expand=body.storage"
    for attempt in range(retries + 1):
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("body", {}).get("storage", {}).get("value", "")
            elif resp.status_code == 404:
                log.warning(f"  Page {page_id} not found (404)")
                return None
            else:
                log.warning(
                    f"  Page {page_id}: HTTP {resp.status_code} (attempt {attempt + 1})"
                )
        except Exception as e:
            log.warning(f"  Page {page_id}: {e} (attempt {attempt + 1})")
        if attempt < retries:
            time.sleep(1)
    return None


def run_live_checks() -> List[dict]:
    """Run live wiki verification — fetches actual pages and cross-checks."""
    results = []
    session = _get_wiki_session()

    if session is None:
        results.append(
            {
                "label": "Wiki session",
                "ok": False,
                "error": "Could not create authenticated session",
            }
        )
        return results

    pages_with_id = [p for p in WIKI_PAGES if p.get("id") is not None]
    if not pages_with_id:
        results.append(
            {
                "label": "Live verification",
                "ok": True,
                "severity": "info",
                "note": "No wiki pages have IDs yet — nothing to fetch",
            }
        )
        log.info("  [INFO] No wiki page IDs available — live mode has nothing to fetch")
        return results

    # Fetch pages in parallel
    def fetch_page(page):
        content = read_wiki_page(session, page["id"])
        return page, content

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_page, p): p for p in pages_with_id}
        for future in as_completed(futures):
            page, content = future.result()
            if content is None:
                results.append(
                    {
                        "label": f"Fetch: {page['title']}",
                        "ok": False,
                        "error": f"Could not fetch page {page['id']}",
                    }
                )
                continue

            results.append(
                {
                    "label": f"Fetch: {page['title']}",
                    "ok": True,
                    "content_length": len(content),
                }
            )

            # Run assertions against wiki content
            for assertion in page.get("assertions", []):
                a_type = assertion.get("type", "contains")
                if a_type == "contains":
                    found = assertion["text"].lower() in content.lower()
                elif a_type == "regex":
                    found = bool(re.search(assertion["pattern"], content))
                else:
                    found = False

                results.append(
                    {
                        "label": f"Wiki assertion: {assertion.get('text', assertion.get('pattern', '?'))[:40]}",
                        "page": page["title"],
                        "ok": found,
                    }
                )

    return results


# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------


def run_all(live: bool = False, loop: int = 1) -> dict:
    """Run all wiki verification and return structured results."""
    start = time.time()
    all_iterations = []

    for i in range(loop):
        if loop > 1:
            log.info(f"\n{'=' * 60}")
            log.info(f"Iteration {i + 1}/{loop}")
            log.info(f"{'=' * 60}")

        iter_results = []

        # Offline checks (always run)
        log.info("\n=== Offline Verification ===")
        offline = run_offline_checks()
        iter_results.extend(offline)

        # Live checks (if requested)
        if live:
            log.info("\n=== Live Wiki Verification ===")
            live_results = run_live_checks()
            iter_results.extend(live_results)

        all_iterations.append(iter_results)

    # Aggregate results from last iteration
    last = all_iterations[-1]
    total_pass = sum(1 for r in last if r.get("ok"))
    total_fail = sum(1 for r in last if not r.get("ok") and r.get("severity") != "info")
    total_info = sum(1 for r in last if not r.get("ok") and r.get("severity") == "info")
    total_checks = len(last)

    # Stability across iterations
    stability = None
    if loop > 1:
        iter_pass_counts = [sum(1 for r in it if r.get("ok")) for it in all_iterations]
        stability = {
            "iterations": loop,
            "min_pass": min(iter_pass_counts),
            "max_pass": max(iter_pass_counts),
            "stable": len(set(iter_pass_counts)) == 1,
        }

    elapsed = time.time() - start
    summary = {
        "total_pass": total_pass,
        "total_fail": total_fail,
        "total_info": total_info,
        "total_checks": total_checks,
        "elapsed_seconds": round(elapsed, 2),
        "exit_code": 0 if total_fail == 0 else 1,
        "mode": "live" if live else "offline",
    }
    if stability:
        summary["stability"] = stability

    log.info(f"\n{'=' * 60}")
    log.info(
        f"Wiki Verify: {total_pass} PASS / {total_fail} FAIL / {total_info} INFO in {elapsed:.1f}s"
    )
    if stability:
        log.info(
            f"Stability: {'STABLE' if stability['stable'] else 'UNSTABLE'} across {loop} iterations"
        )
    log.info(f"{'=' * 60}")

    return {
        "results": [r for r in last],
        "summary": summary,
    }


def main():
    parser = argparse.ArgumentParser(description="NVU Wiki Verification Tool")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Fetch actual wiki pages (requires Intel network)",
    )
    parser.add_argument(
        "--offline", action="store_true", help="Offline checks only (default)"
    )
    parser.add_argument("--loop", type=int, default=1, help="Number of iterations")
    parser.add_argument("--json", action="store_true", help="JSON output for CI")
    parser.add_argument("--verbose", action="store_true", help="Detailed output")
    args = parser.parse_args()

    if args.json:
        log.setLevel(logging.WARNING)
    if args.verbose:
        log.setLevel(logging.DEBUG)

    results = run_all(live=args.live, loop=args.loop)

    if args.json:
        print(json.dumps(results, indent=2, default=str))

    sys.exit(results["summary"]["exit_code"])


if __name__ == "__main__":
    main()
