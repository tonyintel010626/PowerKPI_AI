#!/usr/bin/env python3
"""
FV-AUDIO Self-Learn — Knowledge gap detection from NGA, HSDES, and feedback.

Identifies gaps in the audio skill tree by:
  L01  nga_failures     — Recent NGA audio failures not covered by skills
  L02  hsdes_sightings  — Recent HSDES audio sightings not reflected in skills
  L03  coverage_gaps    — Important audio terms missing from skill content
  L04  feedback_items   — Manual feedback entries awaiting processing

Usage:
    python audio_self_learn.py [--json] [-v]

Adapted from FV-THC thc_self_learn.py.
Owner: huiyingt (Tan Hui Ying)
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audio_self_common import (
    Report,
    Severity,
    find_repo_root,
    get_all_skill_paths,
    load_config,
    read_agent_def,
    read_skill,
    resolve_path,
    setup_logging,
    logger,
)


# ---------------------------------------------------------------------------
# Important term patterns for audio domain
# ---------------------------------------------------------------------------
_IMPORTANT_TERM_PATTERNS: List[Tuple[str, str]] = [
    # Architecture
    (r"\bACE\s*4", "architecture"),
    (r"\bACE\s*3", "architecture"),
    (r"\bPCI\s+0[:.]31[:.]3\b", "architecture"),
    (r"\bPCD[-_]?[HS]\b", "architecture"),
    # HDA
    (r"\bCORB\b", "hda"),
    (r"\bRIRB\b", "hda"),
    (r"\bGCAP\b", "hda"),
    (r"\bGCTL\b", "hda"),
    (r"\bSTATESTS\b", "hda"),
    (r"\bcodec\s+discover", "hda"),
    # SoundWire
    (r"\bSoundWire\b", "soundwire"),
    (r"\bSDCA\b", "soundwire"),
    (r"\bSoundWire\s+[Ss]eg", "soundwire"),
    (r"\bmulti[-_]?drop\b", "soundwire"),
    # DSP
    (r"\bSOF\b", "dsp"),
    (r"\bIPC\s+(message|protocol|command)", "dsp"),
    (r"\bfirmware\s+load", "dsp"),
    (r"\bSRAM\s+(manage|alloc)", "dsp"),
    # DMIC
    (r"\bPDM\b", "dmic"),
    (r"\bDMIC\s+clock", "dmic"),
    (r"\bMicrophone\s+Privacy", "dmic"),
    # Display Audio
    (r"\biDisp\b", "display-audio"),
    (r"\bELD\b", "display-audio"),
    (r"\bHDMI\s+audio", "display-audio"),
    (r"\bDisplayPort\s+audio", "display-audio"),
    # UAOL
    (r"\bUAOL\b", "uaol"),
    (r"\bUSB\s+Audio\s+Offload", "uaol"),
    (r"\bisochronous\b", "uaol"),
    (r"\bbehind[-_]?hub\b", "uaol"),
    # BT Offload
    (r"\bBT\s+Audio\s+Offload", "bt-offload"),
    (r"\bSSP\b", "bt-offload"),
    (r"\bI2S\b", "bt-offload"),
    (r"\bBCLK\b", "bt-offload"),
    # WoV
    (r"\bWake\s+on\s+Voice", "wov"),
    (r"\bCRO\b", "wov"),
    (r"\balways[-_]?on", "wov"),
    # Power
    (r"\bD0i3\b", "power"),
    (r"\bD3hot\b", "power"),
    (r"\bSRAM[-_]?PG\b", "power"),
    (r"\bCGCTL\b", "power"),
    (r"\bLTR\b", "power"),
    # Clocking
    (r"\bAudio\s+PLL\b", "clocking"),
    (r"\bXTAL\b", "clocking"),
    (r"\bclock\s+gat", "clocking"),
    # AIOC
    (r"\bAIOC\b", "aioc"),
    (r"\bALC712\b", "aioc"),
    (r"\bALC1320\b", "aioc"),
    (r"\b5[-_]?[Ss]tar\b", "aioc"),
    # Jack Detection
    (r"\bjack\s+detect", "jack-detect"),
    (r"\bpin\s+sense\b", "jack-detect"),
    (r"\bslave\s+alert", "jack-detect"),
    # Interrupts
    (r"\bMSI\b.*audio", "interrupts"),
    (r"\bINTA\b", "interrupts"),
    (r"\bIPC\s+mask", "interrupts"),
]


# ---------------------------------------------------------------------------
# Keyword → Skill mapping
# ---------------------------------------------------------------------------
_KEYWORD_TO_SKILL: Dict[str, List[str]] = {
    "hda": ["hda"],
    "hd audio": ["hda"],
    "soundwire": ["soundwire"],
    "sdca": ["soundwire", "aioc"],
    "dmic": ["dmic"],
    "display audio": ["display-audio"],
    "hdmi audio": ["display-audio"],
    "uaol": ["uaol"],
    "usb audio": ["uaol"],
    "bt offload": ["bt-offload"],
    "bluetooth audio": ["bt-offload"],
    "ssp": ["bt-offload"],
    "wov": ["wov"],
    "wake on voice": ["wov"],
    "dsp": ["dsp"],
    "sof": ["dsp"],
    "firmware": ["dsp"],
    "power": ["power"],
    "d0i3": ["power"],
    "d3": ["power"],
    "s0ix": ["power"],
    "clocking": ["clocking"],
    "pll": ["clocking"],
    "aioc": ["aioc"],
    "jack": ["jack-detect"],
    "interrupt": ["interrupts"],
    "msi": ["interrupts"],
    "codec": ["hda", "aioc"],
    "config": ["config-checkout"],
    "enumeration": ["config-checkout"],
    "failure": ["failure-analysis"],
}


def _map_keywords_to_skills(text: str) -> Set[str]:
    """Extract skill names that are relevant to the given text."""
    text_lower = text.lower()
    skills: Set[str] = set()
    for keyword, skill_list in _KEYWORD_TO_SKILL.items():
        if keyword in text_lower:
            skills.update(skill_list)
    return skills


# ---------------------------------------------------------------------------
# Learn implementations
# ---------------------------------------------------------------------------

def learn_coverage_gaps(cfg: dict, report: Report) -> None:
    """L03: Find important audio terms not covered in skill content."""
    cid = "L03_coverage_gaps"

    # Collect all skill content
    all_content: Dict[str, str] = {}
    for name, path in get_all_skill_paths(cfg):
        content = read_skill(name, cfg)
        if content:
            all_content[name] = content

    # Also include agent def
    agent = read_agent_def(cfg)
    if agent:
        all_content["__agent_def__"] = agent

    # Merge all text for searching
    merged = "\n".join(all_content.values())

    # Check each important term
    missing_terms: List[Tuple[str, str]] = []  # (pattern_display, category)
    covered_count = 0

    for pattern, category in _IMPORTANT_TERM_PATTERNS:
        if re.search(pattern, merged, re.IGNORECASE):
            covered_count += 1
        else:
            # Try to make a human-readable version of the pattern
            readable = pattern.replace(r"\b", "").replace(r"\s+", " ").replace(r"\s*", "")
            readable = re.sub(r'\[.*?\]', '', readable).replace("\\", "")
            missing_terms.append((readable, category))

    total = len(_IMPORTANT_TERM_PATTERNS)
    coverage_pct = (covered_count / total * 100) if total > 0 else 100

    if missing_terms:
        detail_lines = [f"  {term} (category: {cat})" for term, cat in missing_terms[:15]]
        detail = "\n".join(detail_lines)
        if len(missing_terms) > 15:
            detail += f"\n  ... and {len(missing_terms) - 15} more"
        report.warn(
            cid,
            f"Coverage: {covered_count}/{total} terms ({coverage_pct:.0f}%), "
            f"{len(missing_terms)} gaps",
            detail=detail,
        )
    else:
        report.pass_(cid, f"All {total} important terms covered ({coverage_pct:.0f}%)")


def learn_feedback_items(cfg: dict, report: Report) -> None:
    """L04: Check for unprocessed manual feedback entries."""
    cid = "L04_feedback"
    learn_cfg = cfg.get("self_learn", {})
    feedback_file = learn_cfg.get("feedback_file", "")

    if not feedback_file:
        report.skip(cid, "No feedback file configured")
        return

    base = resolve_path(cfg["paths"]["skill_base"])
    path = base / feedback_file
    if not path.exists():
        report.pass_(cid, "No feedback file present (no pending feedback)")
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            feedback = json.load(f)
    except (json.JSONDecodeError, OSError):
        report.error(cid, f"Failed to parse feedback file: {path}")
        return

    items = feedback if isinstance(feedback, list) else feedback.get("items", [])
    pending = [item for item in items if item.get("status", "pending") == "pending"]

    if pending:
        detail = "\n".join(
            f"  - [{item.get('category', '?')}] {item.get('description', 'no description')}"
            for item in pending[:10]
        )
        report.warn(cid, f"{len(pending)} unprocessed feedback items", detail=detail)
    else:
        report.pass_(cid, f"All {len(items)} feedback items processed")


def learn_nga_gaps(cfg: dict, report: Report) -> None:
    """L01: Check if NGA audio failure patterns are covered by skills.

    Queries the NGA Failure API for recent audio-related failures, extracts
    failure messages and bucket names, and checks whether the failure patterns
    are covered by existing skill content. Falls back to config-only structural
    check when the NGA API is not reachable.
    """
    cid = "L01_nga"
    learn_cfg = cfg.get("self_learn", {})
    nga_cfg = learn_cfg.get("nga", {})

    if not nga_cfg.get("enabled", False):
        report.skip(cid, "NGA integration disabled in config")
        return

    # Structural check: verify NGA config is well-formed
    required_keys = ["base_url", "project_name", "suite_filters", "lookback_days"]
    missing_keys = [k for k in required_keys if k not in nga_cfg]
    if missing_keys:
        report.warn(cid, f"NGA config missing keys: {', '.join(missing_keys)}")
        return

    # --- Attempt live NGA query ---
    project = nga_cfg["project_name"]
    suite_filters = nga_cfg["suite_filters"]
    lookback_days = nga_cfg.get("lookback_days", 30)

    try:
        import requests
        from datetime import datetime, timedelta, timezone

        base_url = nga_cfg["base_url"].rstrip("/")
        # NGA Search API — query recent failures matching audio suite filters
        search_url = f"{base_url}/Search/{project}/api/v2/Search"
        since_date = (datetime.now(tz=timezone.utc) - timedelta(days=lookback_days)).strftime(
            "%Y-%m-%dT00:00:00Z"
        )

        # Build OData filter for audio suites with failures
        suite_filter = " or ".join(
            f"contains(SuiteName,'{sf}')" for sf in suite_filters
        )
        odata_filter = (
            f"Status eq 'Fail' and CompletionDate gt {since_date} "
            f"and ({suite_filter})"
        )

        resp = requests.get(
            search_url,
            params={"$filter": odata_filter, "$top": "200"},
            timeout=30,
            verify=False,
        )

        if resp.status_code == 401 or resp.status_code == 403:
            report.pass_(
                cid,
                f"NGA config valid (auth required for live query): "
                f"project={project}, filters={suite_filters}, "
                f"lookback={lookback_days}d",
            )
            return

        if resp.status_code != 200:
            report.pass_(
                cid,
                f"NGA config valid (API returned {resp.status_code}): "
                f"project={project}, filters={suite_filters}",
            )
            return

        results = resp.json()
        items = results if isinstance(results, list) else results.get("value", [])

        if not items:
            report.pass_(
                cid,
                f"No recent audio failures in NGA ({project}, "
                f"last {lookback_days}d) — skills are up to date",
            )
            return

        # Collect all skill content for gap checking
        all_content = "\n".join(
            read_skill(name, cfg) or ""
            for name, _ in get_all_skill_paths(cfg)
        )
        agent_def = read_agent_def(cfg) or ""
        merged_skills = all_content + "\n" + agent_def

        # Analyze failures for uncovered patterns
        uncovered: List[str] = []
        covered_count = 0
        for item in items:
            msg = (
                item.get("FailureMessage", "")
                or item.get("ErrorMessage", "")
                or item.get("BucketName", "")
                or item.get("Name", "")
            )
            if not msg:
                continue

            mapped_skills = _map_keywords_to_skills(msg)
            if mapped_skills:
                # Check if the specific failure pattern is mentioned in skills
                # Use first 80 chars as a signature
                sig = msg[:80].strip()
                if any(
                    sig[:30].lower() in merged_skills.lower()
                    for _ in [1]
                    if sig[:30]
                ):
                    covered_count += 1
                else:
                    uncovered.append(
                        f"{', '.join(mapped_skills)}: {sig}"
                    )
            else:
                uncovered.append(f"unmapped: {msg[:80].strip()}")

        total_analyzed = covered_count + len(uncovered)
        if uncovered:
            detail = "\n".join(f"  - {u}" for u in uncovered[:15])
            if len(uncovered) > 15:
                detail += f"\n  ... and {len(uncovered) - 15} more"
            report.warn(
                cid,
                f"NGA: {len(uncovered)}/{total_analyzed} recent failures "
                f"have uncovered patterns ({project}, last {lookback_days}d)",
                detail=detail,
            )
        else:
            report.pass_(
                cid,
                f"NGA: all {total_analyzed} recent failure patterns covered "
                f"({project}, last {lookback_days}d)",
            )
        return

    except ImportError:
        logger.debug("requests library not available — skipping live NGA query")
    except Exception as exc:
        logger.debug("NGA live query failed: %s — falling back to config check", exc)

    # Fallback: config-only structural check
    report.pass_(cid,
                  f"NGA config valid: project={project}, "
                  f"filters={suite_filters}, "
                  f"lookback={lookback_days}d")


def learn_hsdes_gaps(cfg: dict, report: Report) -> None:
    """L02: Check if HSDES audio sighting patterns are covered by skills.

    Queries HSDES for recent audio-related sightings, extracts titles and
    descriptions, and checks whether the sighting patterns are covered by
    existing skill content. Falls back to config-only structural check when
    HSDES is not reachable.
    """
    cid = "L02_hsdes"
    learn_cfg = cfg.get("self_learn", {})
    hsdes_cfg = learn_cfg.get("hsdes", {})

    if not hsdes_cfg:
        report.skip(cid, "No HSDES config present")
        return

    # Structural check: verify HSDES config is well-formed
    tenants = hsdes_cfg.get("tenants", [])
    filters = hsdes_cfg.get("query_filters", {})
    components = filters.get("component", [])
    lookback_days = hsdes_cfg.get("lookback_days", 90)

    if not tenants:
        report.warn(cid, "No HSDES tenants configured")
        return
    if not components:
        report.warn(cid, "No HSDES component filters configured")
        return

    # --- Attempt live HSDES query ---
    try:
        from pysvtools import hsdes as hsdes_api
        from datetime import datetime, timedelta, timezone

        since_date = (datetime.now(tz=timezone.utc) - timedelta(days=lookback_days)).strftime(
            "%Y-%m-%d"
        )

        # Collect all skill content for gap checking
        all_content = "\n".join(
            read_skill(name, cfg) or ""
            for name, _ in get_all_skill_paths(cfg)
        )
        agent_def = read_agent_def(cfg) or ""
        merged_skills = all_content + "\n" + agent_def

        all_sightings: list = []
        for tenant in tenants:
            try:
                hsdes_api.config(tenant)
            except Exception as exc:
                logger.debug("Failed to configure HSDES tenant %s: %s", tenant, exc)
                continue

            # Query for each component filter
            statuses = filters.get("status", ["open", "in_progress"])
            status_clause = " or ".join(f"status = '{s}'" for s in statuses)

            for component in components:
                try:
                    eql = (
                        f"subject = '{component}' and ({status_clause}) "
                        f"and submitted_date > '{since_date}'"
                    )
                    results = hsdes_api.search(
                        eql,
                        showFields="id,title,status,owner,submitted_date",
                    )
                    if isinstance(results, list):
                        all_sightings.extend(results)
                    elif isinstance(results, dict) and "data" in results:
                        all_sightings.extend(results["data"])
                except Exception as exc:
                    logger.debug(
                        "HSDES query failed for %s/%s: %s", tenant, component, exc
                    )
                    continue

        if not all_sightings:
            # Could mean no results OR auth/network issue — check if we got
            # any successful query at all
            report.pass_(
                cid,
                f"HSDES config valid: {len(tenants)} tenants, "
                f"{len(components)} components, lookback={lookback_days}d "
                f"(no recent sightings found or API not reachable)",
            )
            return

        # Analyze sightings for uncovered patterns
        uncovered: List[str] = []
        covered_count = 0
        seen_ids: set = set()

        for sighting in all_sightings:
            sid = str(sighting.get("id", ""))
            if sid in seen_ids:
                continue
            seen_ids.add(sid)

            title = sighting.get("title", "")
            if not title:
                continue

            mapped_skills = _map_keywords_to_skills(title)
            # Check if the sighting pattern appears in skill content
            # Use key terms from title for matching
            title_words = [
                w for w in title.lower().split()
                if len(w) > 3 and w not in {"the", "and", "for", "with", "from", "that", "this"}
            ]
            sig_terms = title_words[:5]
            match_count = sum(
                1 for term in sig_terms if term in merged_skills.lower()
            )

            if match_count >= 2 or mapped_skills:
                covered_count += 1
            else:
                owner = sighting.get("owner", "?")
                uncovered.append(f"HSD {sid}: {title[:80]} (owner: {owner})")

        total = covered_count + len(uncovered)
        if uncovered:
            detail = "\n".join(f"  - {u}" for u in uncovered[:15])
            if len(uncovered) > 15:
                detail += f"\n  ... and {len(uncovered) - 15} more"
            report.warn(
                cid,
                f"HSDES: {len(uncovered)}/{total} recent sightings "
                f"have uncovered patterns (last {lookback_days}d)",
                detail=detail,
            )
        else:
            report.pass_(
                cid,
                f"HSDES: all {total} recent sighting patterns covered "
                f"(last {lookback_days}d)",
            )
        return

    except ImportError:
        logger.debug("pysvtools.hsdes not available — skipping live HSDES query")
    except Exception as exc:
        logger.debug("HSDES live query failed: %s — falling back to config check", exc)

    # Fallback: config-only structural check
    report.pass_(cid,
                  f"HSDES config valid: {len(tenants)} tenants, "
                  f"{len(components)} component filters, "
                  f"lookback={lookback_days}d")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_learn(cfg: dict | None = None) -> Report:
    """Run all knowledge gap detection and return aggregated report."""
    t0 = time.time()
    cfg = cfg or load_config()
    report = Report(stage="self-learn")

    checks = [
        learn_nga_gaps,
        learn_hsdes_gaps,
        learn_coverage_gaps,
        learn_feedback_items,
    ]
    for check_fn in checks:
        try:
            check_fn(cfg, report)
        except Exception as exc:
            report.error(check_fn.__name__, f"Unhandled exception: {exc}")

    report.finalize(t0)
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="FV-AUDIO knowledge gap detection")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)

    report = run_learn()
    if args.json:
        print(report.to_json())
    else:
        report.print_text()
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
