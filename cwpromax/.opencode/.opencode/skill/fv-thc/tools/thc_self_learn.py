#!/usr/bin/env python3
# > **Owner**: Chin, William Willy (`willychi`)
# Support: For any issues, contact the owner above. Please collect the complete
#          session transcript (AI log dump) before reporting for faster root-cause analysis.
"""THC Self-Learn: Knowledge gap detection from NGA results, HSDES sightings,
and manual feedback.

Ingests external signals (test failures, sightings, user feedback) and
correlates them with skill file coverage to identify knowledge gaps.

Sources:
  1. NGA test results  -- recent THC test failures via NGA REST API
  2. HSDES sightings   -- open THC sightings via pysvtools.hsdes
  3. Manual feedback    -- feedback_inbox.json dropped by engineers

Output: Knowledge gap report mapping external signals → skill coverage gaps.

Usage:
    python thc_self_learn.py                     # all sources
    python thc_self_learn.py --source nga        # NGA only
    python thc_self_learn.py --source hsdes      # HSDES only
    python thc_self_learn.py --source feedback   # feedback only
    python thc_self_learn.py --json              # JSON output
    python thc_self_learn.py --save              # save report to file
    python thc_self_learn.py --since 2026-03-01  # custom lookback start
"""
import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Bootstrap: ensure tools/ is on sys.path for sibling imports
# ---------------------------------------------------------------------------
_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from thc_self_common import (  # noqa: E402
    Finding,
    Report,
    find_repo_root,
    load_config,
    read_skill,
    read_agent_def,
    get_all_skill_paths,
    setup_logging,
    load_last_run_timestamp,
    save_last_run_timestamp,
)

logger = logging.getLogger("thc_self_learn")

# ---------------------------------------------------------------------------
# Keyword → Skill mapping (used to correlate external signals to skills)
# ---------------------------------------------------------------------------
KEYWORD_SKILL_MAP: Dict[str, List[str]] = {
    # Protocol keywords
    "hidspi": ["hidspi"],
    "hid over spi": ["hidspi"],
    "spi": ["hidspi", "registers"],
    "quickspi": ["hidspi"],
    "hidi2c": ["hidi2c"],
    "hid over i2c": ["hidi2c"],
    "i2c": ["hidi2c", "registers"],
    "quicki2c": ["hidi2c"],
    # DMA keywords
    "dma": ["dma"],
    "rxdma": ["dma"],
    "txdma": ["dma"],
    "swdma": ["dma"],
    "prd": ["dma"],
    "descriptor": ["dma"],
    "ring": ["dma"],
    "buffer overrun": ["dma", "debug"],
    # Power keywords
    "power": ["power"],
    "d0i2": ["power"],
    "d3": ["power"],
    "d3hot": ["power"],
    "d3cold": ["power"],
    "cgpg": ["power"],
    "ltr": ["power"],
    "s0ix": ["power"],
    "s3": ["power"],
    "s4": ["power"],
    "rtd3": ["power"],
    "pmclite": ["power"],
    "power gate": ["power"],
    "clock gate": ["power"],
    # WoT keywords
    "wot": ["wot"],
    "wake on touch": ["wot"],
    "wake-on-touch": ["wot"],
    "touch wake": ["wot"],
    # Register / HW keywords
    "register": ["registers"],
    "pio": ["registers"],
    "mmio": ["registers"],
    "bar0": ["registers"],
    "pci": ["registers", "platform"],
    "bdf": ["platform"],
    # Platform keywords
    "lnl": ["platform"],
    "ptl": ["platform"],
    "wcl": ["platform"],
    "nvl": ["platform"],
    "rzl": ["platform"],
    "ttl": ["platform"],
    "arl": ["platform"],
    "mtl": ["platform"],
    "bom": ["platform"],
    # Driver keywords
    "driver": ["driver"],
    "bios": ["driver", "platform"],
    "acpi": ["driver", "hidspi", "hidi2c"],
    "dsm": ["driver", "hidspi", "hidi2c"],
    "ipts": ["driver"],
    "probe": ["driver"],
    "enumerat": ["driver", "platform"],
    # Debug keywords
    "debug": ["debug"],
    "triage": ["debug"],
    "bsod": ["debug"],
    "crash": ["debug"],
    "hang": ["debug"],
    "timeout": ["debug"],
    "error": ["debug"],
    "failure": ["debug"],
    "sighting": ["debug"],
}

# ---------------------------------------------------------------------------
# NGA Ingestion
# ---------------------------------------------------------------------------

def _ingest_nga(config: Dict[str, Any], since: Optional[str] = None) -> List[Finding]:
    """Ingest recent THC test failures from NGA REST API.

    Falls back to offline/mock mode if NGA API is unreachable.
    Skips entirely if nga.enabled is false in config.
    """
    findings: List[Finding] = []
    nga_cfg = config.get("self_learn", {}).get("nga", {})

    # Respect enabled flag — THC domain may not use NGA
    if not nga_cfg.get("enabled", True):
        findings.append(Finding(
            severity="INFO",
            check="nga_api",
            target="nga_connection",
            status="SKIP",
            message="NGA ingestion disabled in config (nga.enabled=false)",
        ))
        return findings

    base_url = nga_cfg.get("base_url", "https://nga.intel.com")
    project = nga_cfg.get("project_name", "THC")
    suite_filters = nga_cfg.get("suite_filters", ["THC_*", "thc_*"])
    lookback = nga_cfg.get("lookback_days", 7)

    if since:
        start_date = since
    else:
        start_date = (datetime.now() - timedelta(days=lookback)).strftime("%Y-%m-%d")

    # --- Try NGA REST API ---
    try:
        import requests  # noqa: F811
        # NGA Results API: GET /api/results with OData filters
        # This is a best-effort call; NGA may require specific auth tokens
        headers = {"Accept": "application/json"}
        params = {
            "$filter": (
                f"ProjectName eq '{project}' and "
                f"Status eq 'Failed' and "
                f"StartTime ge {start_date}T00:00:00Z"
            ),
            "$top": 200,
            "$orderby": "StartTime desc",
        }
        url = f"{base_url}/api/results"
        resp = requests.get(url, headers=headers, params=params, timeout=30,
                            verify=False)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("value", data) if isinstance(data, dict) else data
            if isinstance(results, list) and results:
                findings.append(Finding(
                    check="nga_api",
                    target="nga_results",
                    status="INFO",
                    message=f"Retrieved {len(results)} failed results since {start_date}",
                ))
                for r in results:
                    test_name = r.get("TestName", r.get("Name", "unknown"))
                    suite_name = r.get("SuiteName", r.get("Suite", "unknown"))
                    fail_msg = r.get("Message", r.get("FailureMessage", ""))
                    # Correlate to skill
                    skills = _correlate_to_skills(f"{test_name} {suite_name} {fail_msg}")
                    findings.append(Finding(
                        check="nga_failure",
                        target=f"{suite_name}/{test_name}",
                        status="WARN",
                        message=f"NGA failure: {test_name}",
                        severity="medium",
                        details=json.dumps({
                            "suite": suite_name,
                            "test": test_name,
                            "failure_message": fail_msg[:500],
                            "correlated_skills": skills,
                            "source": "nga",
                            "date": r.get("StartTime", ""),
                        }),
                    ))
                return findings
            else:
                findings.append(Finding(
                    check="nga_api",
                    target="nga_results",
                    status="PASS",
                    message=f"No failed results since {start_date}",
                ))
                return findings
        else:
            logger.warning("NGA API returned %d — falling back to offline mode", resp.status_code)
    except ImportError:
        logger.warning("requests library not available — NGA offline mode")
    except Exception as e:
        logger.warning("NGA API unreachable (%s) — offline mode", e)

    # --- Offline/mock mode ---
    findings.append(Finding(
        check="nga_api",
        target="nga_connection",
        status="SKIP",
        message="NGA API not available — no live failure data ingested",
        severity="info",
        details="Install 'requests' and ensure NGA network access for live data.",
    ))
    return findings


# ---------------------------------------------------------------------------
# HSDES Ingestion
# ---------------------------------------------------------------------------

def _ingest_hsdes(config: Dict[str, Any], since: Optional[str] = None) -> List[Finding]:
    """Ingest open THC sightings from HSDES via pysvtools.hsdes.

    Falls back to offline/mock mode if pysvtools is unavailable.
    """
    findings: List[Finding] = []
    hsdes_cfg = config.get("self_learn", {}).get("hsdes", {})
    tenants = hsdes_cfg.get("tenants", ["sighting_central.sighting"])
    components = hsdes_cfg.get("query_filters", {}).get("component",
                               ["THC", "Touch Host Controller"])
    statuses = hsdes_cfg.get("query_filters", {}).get("status",
                              ["open", "new", "investigating"])
    lookback = hsdes_cfg.get("lookback_days", 30)

    if since:
        start_date = since
    else:
        start_date = (datetime.now() - timedelta(days=lookback)).strftime("%Y-%m-%d")

    try:
        from pysvtools.hsdes import HsdesApi  # type: ignore
        api = HsdesApi()
        total_sightings = 0

        for tenant in tenants:
            for component in components:
                try:
                    # Build HSDES query
                    query = (
                        f"component:'{component}' AND "
                        f"status IN ({','.join(repr(s) for s in statuses)}) AND "
                        f"updated_date >= '{start_date}'"
                    )
                    results = api.query(tenant, query, max_results=100)
                    if not results:
                        continue

                    total_sightings += len(results)
                    for sighting in results:
                        sid = sighting.get("id", "unknown")
                        title = sighting.get("title", sighting.get("subject", ""))
                        status = sighting.get("status", "unknown")
                        description = sighting.get("description", "")[:500]

                        skills = _correlate_to_skills(f"{title} {description}")
                        findings.append(Finding(
                            check="hsdes_sighting",
                            target=f"HSDES:{sid}",
                            status="WARN",
                            message=f"Open sighting: {title[:100]}",
                            severity="medium",
                            details=json.dumps({
                                "sighting_id": sid,
                                "title": title,
                                "status": status,
                                "tenant": tenant,
                                "component": component,
                                "correlated_skills": skills,
                                "source": "hsdes",
                            }),
                        ))
                except Exception as e:
                    logger.warning("HSDES query failed for %s/%s: %s",
                                   tenant, component, e)
                    findings.append(Finding(
                        check="hsdes_query",
                        target=f"{tenant}/{component}",
                        status="ERROR",
                        message=f"HSDES query error: {e}",
                    ))

        if total_sightings == 0 and not any(f.status == "ERROR" for f in findings):
            findings.append(Finding(
                check="hsdes_sightings",
                target="hsdes",
                status="PASS",
                message=f"No open THC sightings found since {start_date}",
            ))
        else:
            findings.insert(0, Finding(
                check="hsdes_api",
                target="hsdes",
                status="INFO",
                message=f"Ingested {total_sightings} sightings since {start_date}",
            ))
        return findings

    except ImportError:
        logger.warning("pysvtools.hsdes not available — HSDES offline mode")
    except Exception as e:
        logger.warning("HSDES API error (%s) — offline mode", e)

    findings.append(Finding(
        check="hsdes_api",
        target="hsdes_connection",
        status="SKIP",
        message="HSDES API not available — no sighting data ingested",
        severity="info",
        details="Install 'pysvtools' and ensure HSDES network access for live data.",
    ))
    return findings


# ---------------------------------------------------------------------------
# Manual Feedback Ingestion
# ---------------------------------------------------------------------------

def _ingest_feedback(config: Dict[str, Any]) -> List[Finding]:
    """Ingest manual feedback from feedback_inbox.json.

    Expected format:
    [
      {
        "date": "2026-03-06",
        "author": "willychi",
        "type": "gap|correction|suggestion|sighting",
        "skill": "hidspi",          // optional: target skill
        "keywords": "spi clock",    // optional: for correlation
        "message": "The SPI clock section is missing ...",
        "priority": "high|medium|low"
      }
    ]
    """
    findings: List[Finding] = []
    fb_path_rel = config.get("self_learn", {}).get("feedback_file",
                   ".opencode/skill/fv-thc/tools/feedback_inbox.json")
    repo_root = find_repo_root()
    fb_path = repo_root / fb_path_rel

    if not fb_path.exists():
        findings.append(Finding(
            check="feedback_file",
            target=str(fb_path_rel),
            status="SKIP",
            message="No feedback_inbox.json found — no manual feedback to ingest",
            severity="info",
        ))
        return findings

    try:
        with open(fb_path, "r", encoding="utf-8") as f:
            feedback_items = json.load(f)

        if not isinstance(feedback_items, list):
            feedback_items = [feedback_items]

        if not feedback_items:
            findings.append(Finding(
                check="feedback_file",
                target=str(fb_path_rel),
                status="PASS",
                message="feedback_inbox.json is empty — no pending feedback",
            ))
            return findings

        findings.append(Finding(
            check="feedback_file",
            target=str(fb_path_rel),
            status="INFO",
            message=f"Loaded {len(feedback_items)} feedback items",
        ))

        for i, item in enumerate(feedback_items):
            if not isinstance(item, dict):
                continue
            fb_type = item.get("type", "suggestion")
            skill = item.get("skill", "")
            keywords = item.get("keywords", "")
            message = item.get("message", "")
            priority = item.get("priority", "medium")
            author = item.get("author", "unknown")
            date = item.get("date", "")

            # Determine correlated skills
            if skill:
                skills = [skill]
            elif keywords:
                skills = _correlate_to_skills(keywords)
            else:
                skills = _correlate_to_skills(message)

            severity = {"high": "high", "medium": "medium", "low": "low"}.get(
                priority, "medium"
            )

            findings.append(Finding(
                check="feedback_item",
                target=f"feedback[{i}]/{fb_type}",
                status="WARN",
                message=f"[{fb_type}] {message[:120]}",
                severity=severity,
                details=json.dumps({
                    "index": i,
                    "type": fb_type,
                    "skill": skill,
                    "correlated_skills": skills,
                    "priority": priority,
                    "author": author,
                    "date": date,
                    "full_message": message,
                    "source": "feedback",
                }),
            ))

        return findings

    except json.JSONDecodeError as e:
        findings.append(Finding(
            check="feedback_file",
            target=str(fb_path_rel),
            status="ERROR",
            message=f"Invalid JSON in feedback_inbox.json: {e}",
        ))
    except Exception as e:
        findings.append(Finding(
            check="feedback_file",
            target=str(fb_path_rel),
            status="ERROR",
            message=f"Error reading feedback: {e}",
        ))

    return findings


# ---------------------------------------------------------------------------
# Correlation Engine
# ---------------------------------------------------------------------------

def _correlate_to_skills(text: str) -> List[str]:
    """Map a text blob to relevant THC skill files using keyword matching."""
    if not text:
        return []
    text_lower = text.lower()
    matched_skills: Dict[str, int] = {}  # skill → match count

    for keyword, skills in KEYWORD_SKILL_MAP.items():
        if keyword in text_lower:
            for skill in skills:
                matched_skills[skill] = matched_skills.get(skill, 0) + 1

    # Sort by match count (descending), return top matches
    sorted_skills = sorted(matched_skills.items(), key=lambda x: -x[1])
    return [s for s, _ in sorted_skills]


def _analyze_coverage_gaps(
    all_findings: List[Finding],
    config: Dict[str, Any],
) -> List[Finding]:
    """Analyze all ingested signals and identify skill coverage gaps.

    For each correlated skill, check if the skill file mentions the
    specific failure/sighting topic. If not, flag as a coverage gap.
    """
    gap_findings: List[Finding] = []

    # Collect all external signals (WARN findings with details containing
    # correlated_skills)
    signals: List[Dict[str, Any]] = []
    for f in all_findings:
        if f.status in ("WARN",) and f.details:
            try:
                detail = json.loads(f.details)
                if "correlated_skills" in detail:
                    signals.append(detail)
            except (json.JSONDecodeError, TypeError):
                continue

    if not signals:
        gap_findings.append(Finding(
            check="coverage_analysis",
            target="all_skills",
            status="PASS",
            message="No external signals to analyze — no coverage gaps detected",
        ))
        return gap_findings

    # Aggregate: which skills are most frequently implicated?
    skill_signal_count: Dict[str, int] = {}
    skill_signals: Dict[str, List[Dict[str, Any]]] = {}
    for sig in signals:
        for skill in sig.get("correlated_skills", []):
            skill_signal_count[skill] = skill_signal_count.get(skill, 0) + 1
            skill_signals.setdefault(skill, []).append(sig)

    # For each implicated skill, check content coverage
    for skill_name, count in sorted(skill_signal_count.items(), key=lambda x: -x[1]):
        try:
            skill_content = read_skill(skill_name)
        except Exception:
            gap_findings.append(Finding(
                check="coverage_gap",
                target=f"fv-thc/{skill_name}",
                status="ERROR",
                message=f"Cannot read skill '{skill_name}' for coverage check",
            ))
            continue

        skill_lower = skill_content.lower()

        # Check each signal against skill content
        uncovered_signals = []
        for sig in skill_signals[skill_name]:
            # Extract key terms from the signal
            title = sig.get("title", sig.get("test", sig.get("full_message", "")))
            if not title:
                continue

            # Simple heuristic: check if any significant word from the signal
            # title appears in the skill content
            words = re.findall(r'\b[a-zA-Z_]{4,}\b', title.lower())
            # Filter out common words
            stop_words = {
                "test", "that", "this", "with", "from", "have", "been",
                "should", "could", "would", "will", "shall", "does",
                "after", "before", "during", "intel", "touch",
            }
            significant_words = [w for w in words if w not in stop_words]

            if significant_words:
                match_ratio = sum(1 for w in significant_words
                                  if w in skill_lower) / len(significant_words)
                if match_ratio < 0.3:  # Less than 30% of key terms found
                    uncovered_signals.append({
                        "signal": title[:100],
                        "source": sig.get("source", "unknown"),
                        "missing_terms": [w for w in significant_words
                                          if w not in skill_lower][:10],
                    })

        if uncovered_signals:
            gap_findings.append(Finding(
                check="coverage_gap",
                target=f"fv-thc/{skill_name}",
                status="WARN",
                message=(f"{len(uncovered_signals)} signal(s) with low skill "
                         f"coverage (of {count} total)"),
                severity="medium",
                details=json.dumps({
                    "skill": skill_name,
                    "total_signals": count,
                    "uncovered_count": len(uncovered_signals),
                    "uncovered_signals": uncovered_signals[:10],
                }),
            ))
        else:
            gap_findings.append(Finding(
                check="coverage_check",
                target=f"fv-thc/{skill_name}",
                status="PASS",
                message=f"All {count} signal(s) have adequate skill coverage",
            ))

    return gap_findings


# ---------------------------------------------------------------------------
# Summary Generator
# ---------------------------------------------------------------------------

def _generate_summary(all_findings: List[Finding]) -> List[Finding]:
    """Generate a concise summary of learning results."""
    summary_findings: List[Finding] = []

    # Count by source
    sources = {"nga": 0, "hsdes": 0, "feedback": 0}
    gaps = 0
    for f in all_findings:
        if f.details:
            try:
                d = json.loads(f.details)
                src = d.get("source", "")
                if src in sources:
                    sources[src] += 1
            except (json.JSONDecodeError, TypeError):
                pass
        if f.check == "coverage_gap" and f.status == "WARN":
            gaps += 1

    total_signals = sum(sources.values())

    summary_findings.append(Finding(
        check="learn_summary",
        target="all_sources",
        status="WARN" if gaps > 0 else "PASS",
        message=(
            f"Ingested {total_signals} signals "
            f"(NGA:{sources['nga']}, HSDES:{sources['hsdes']}, "
            f"feedback:{sources['feedback']}), "
            f"identified {gaps} coverage gap(s)"
        ),
        severity="high" if gaps >= 5 else "medium" if gaps > 0 else "info",
        details=json.dumps({
            "total_signals": total_signals,
            "by_source": sources,
            "coverage_gaps": gaps,
        }),
    ))

    return summary_findings


# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------

def run_learn(
    sources: Optional[List[str]] = None,
    since: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Report:
    """Run the self-learn pipeline.

    Args:
        sources: List of sources to ingest ('nga', 'hsdes', 'feedback').
                 None = all sources.
        since: ISO date string for lookback start (e.g. '2026-03-01').
        config: Config dict. Auto-loaded if None.

    Returns:
        Report with all findings.
    """
    if config is None:
        config = load_config()
    assert config is not None, "Failed to load self-improvement config"

    all_sources = sources or ["nga", "hsdes", "feedback"]
    report = Report(name="THC Self-Learn", version="1.0.0")

    # Phase 1: Ingest from external sources
    if "nga" in all_sources:
        logger.info("Ingesting NGA test results...")
        report.findings.extend(_ingest_nga(config, since))

    if "hsdes" in all_sources:
        logger.info("Ingesting HSDES sightings...")
        report.findings.extend(_ingest_hsdes(config, since))

    if "feedback" in all_sources:
        logger.info("Ingesting manual feedback...")
        report.findings.extend(_ingest_feedback(config))

    # Phase 2: Correlate and analyze coverage gaps
    logger.info("Analyzing coverage gaps...")
    report.findings.extend(_analyze_coverage_gaps(report.findings, config))

    # Phase 3: Generate summary
    report.findings.extend(_generate_summary(report.findings))

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="THC Self-Learn: knowledge gap detection from external signals",
    )
    parser.add_argument(
        "--source",
        choices=["nga", "hsdes", "feedback"],
        action="append",
        help="Source to ingest (repeat for multiple; omit for all)",
    )
    parser.add_argument(
        "--since",
        help="Lookback start date (ISO format, e.g. 2026-03-01)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save report to reports/ directory",
    )
    parser.add_argument(
        "--update-timestamp",
        action="store_true",
        help="Update last-run timestamp after successful run",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()
    level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging("thc_self_learn", level)

    report = run_learn(sources=args.source, since=args.since)

    # Output
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report.to_text())

    # Save
    if args.save:
        reports_dir = _TOOLS_DIR / "reports"
        path = report.save(reports_dir)
        logger.info("Report saved to %s", path)

    # Update timestamp
    if args.update_timestamp:
        save_last_run_timestamp("self_learn", _TOOLS_DIR)

    return 1 if report.has_failures or report.has_warnings else 0


if __name__ == "__main__":
    sys.exit(main())
