#!/usr/bin/env python3
"""NVU Self-Learn — Knowledge gap detection from NGA, HSDES, and feedback.

Ingests signals from test infrastructure (NGA failures, HSDES sightings)
and manual feedback to identify knowledge gaps in NVU skill files.

Ported from thc_self_learn.py — adapted for NVU IP domain.
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from nvu_self_common import (
    Finding,
    Report,
    load_config,
    read_skill,
    setup_logging,
    get_all_skill_paths,
    load_last_run_timestamp,
    save_last_run_timestamp,
    TIMESTAMP_FMT,
)

logger = logging.getLogger("nvu_self_learn")

# ---------------------------------------------------------------------------
# Keyword → Skill mapping (NVU-specific)
# ---------------------------------------------------------------------------

KEYWORD_SKILL_MAP: Dict[str, List[str]] = {
    # Inference / Neural Processing
    "npx6": ["inference"],
    "nna": ["inference"],
    "neural": ["inference"],
    "vpx2": ["inference"],
    "dsp": ["inference"],
    "vliw": ["inference"],
    "simd": ["inference"],
    "cnn": ["inference"],
    "rnn": ["inference"],
    "lstm": ["inference"],
    "transformer": ["inference"],
    "int8": ["inference"],
    "convolution": ["inference"],
    "tensor": ["inference"],
    "model": ["inference"],
    "inference": ["inference"],
    "mac": ["inference"],
    "hs3x": ["inference"],
    # Registers
    "register": ["registers"],
    "mmio": ["registers"],
    "bar0": ["registers"],
    "bar1": ["registers"],
    "pci": ["registers", "driver", "platform"],
    "bdf": ["registers", "platform"],
    "msi": ["registers", "driver"],
    "iosf": ["registers"],
    "iosf2axi": ["registers"],
    "pvt": ["registers"],
    "pmctl": ["registers", "power"],
    # DMA
    "dma": ["dma"],
    "designware": ["dma"],
    "axi": ["dma"],
    "paging": ["dma", "firmware"],
    "sram": ["dma", "power"],
    "imr": ["dma", "firmware"],
    "dram": ["dma", "firmware"],
    "boot_dma": ["dma"],
    "misc": ["dma"],
    "handshake": ["dma"],
    # Power Management
    "power": ["power"],
    "d0i0": ["power"],
    "d0i1": ["power"],
    "d0i2": ["power"],
    "d3": ["power", "driver"],
    "d3hot": ["power"],
    "rtd3": ["power"],
    "vnn": ["power"],
    "crpm": ["power"],
    "pmc": ["power"],
    "clock_gating": ["power"],
    "power_gating": ["power"],
    "ipapg": ["power"],
    "ltr": ["power"],
    "lid_closed": ["power"],
    "chassis": ["power"],
    "s0ix": ["power"],
    "sleep": ["power"],
    "wake": ["power"],
    # Camera / Sensor Interface
    "mipi": ["camera"],
    "csi": ["camera"],
    "csi2": ["camera"],
    "phy": ["camera"],
    "ipu": ["camera"],
    "altek": ["camera"],
    "isp": ["camera"],
    "cv-isp": ["camera"],
    "mjpeg": ["camera"],
    "vc9000": ["camera"],
    "sio": ["camera"],
    "usb_camera": ["camera"],
    "camera": ["camera"],
    "sensor": ["camera"],
    # Firmware
    "firmware": ["firmware"],
    "fw": ["firmware"],
    "boot_rom": ["firmware"],
    "rom": ["firmware"],
    "secure_boot": ["firmware"],
    "ese": ["firmware"],
    "svn": ["firmware"],
    "ipc": ["firmware", "driver"],
    "host2nvu": ["firmware", "driver"],
    "nvu2host": ["firmware", "driver"],
    "bup": ["firmware"],
    "rom_bypass": ["firmware"],
    # Driver
    "driver": ["driver"],
    "enumeration": ["driver", "platform"],
    "rcirep": ["driver"],
    "rciep": ["driver"],
    "suspend": ["driver", "power"],
    "resume": ["driver", "power"],
    "irq": ["driver"],
    # Platform
    "platform": ["platform"],
    "strap": ["platform"],
    "fuse": ["platform"],
    "reset": ["platform"],
    "pltrst": ["platform"],
    "titanlake": ["platform"],
    "ttl": ["platform"],
    "pcd": ["platform"],
    "sai": ["platform"],
    "att": ["platform"],
    # Debug
    "debug": ["debug"],
    "dtf": ["debug"],
    "visa": ["debug"],
    "ecc": ["debug"],
    "secded": ["debug"],
    "watchdog": ["debug"],
    "wdt": ["debug"],
    "syst": ["debug"],
    "mbist": ["debug"],
    "ocd": ["debug"],
    "stap": ["debug"],
    "telemetry": ["debug"],
    # BIOS
    "bios": ["bios"],
    "acpi": ["bios", "driver"],
    "deven": ["bios"],
    "knob": ["bios"],
    "brp": ["bios"],
    "bios_init": ["bios"],
    # Cross-cutting
    "nvu": ["registers", "driver", "platform"],
    "i2c": ["platform"],
    "i3c": ["platform"],
    "spi": ["platform"],
    "uart": ["platform", "debug"],
    "gpio": ["platform"],
    "noc": ["platform"],
    "flexnoc": ["platform"],
    "arteris": ["platform"],
}


def _correlate_to_skills(text: str) -> List[Tuple[str, int]]:
    """Match keywords in text to skill files. Return sorted (skill, count) pairs."""
    text_lower = text.lower()
    skill_hits: Dict[str, int] = {}

    for keyword, skills in KEYWORD_SKILL_MAP.items():
        # Use word boundary matching for short keywords
        if len(keyword) <= 3:
            pattern = rf"\b{re.escape(keyword)}\b"
        else:
            pattern = re.escape(keyword)

        count = len(re.findall(pattern, text_lower))
        if count > 0:
            for skill in skills:
                skill_hits[skill] = skill_hits.get(skill, 0) + count

    return sorted(skill_hits.items(), key=lambda x: -x[1])


# ---------------------------------------------------------------------------
# Source: NGA API
# ---------------------------------------------------------------------------


def _ingest_nga(config: Dict, since: Optional[str] = None) -> List[Finding]:
    """Ingest NGA test failures for NVU-related tests."""
    findings: List[Finding] = []
    nga_config = config.get("self_learn", {}).get("nga", {})

    if not nga_config.get("enabled", False):
        findings.append(
            Finding(
                check="learn_nga",
                target="NGA",
                status="SKIP",
                message="NGA ingestion disabled in config",
                severity="info",
            )
        )
        return findings

    api_url = nga_config.get("api_url", "")
    project_name = nga_config.get("project_name", "NVU")

    if not api_url:
        findings.append(
            Finding(
                check="learn_nga",
                target="NGA",
                status="SKIP",
                message="NGA API URL not configured",
                severity="info",
            )
        )
        return findings

    try:
        import requests

        # Build OData filter
        filters = [f"ProjectName eq '{project_name}'", "Status eq 'Failed'"]
        if since:
            filters.append(f"StartTime ge {since}")

        filter_str = " and ".join(filters)
        url = f"{api_url}/odata/TestRuns?$filter={filter_str}&$top=100"

        logger.info("Querying NGA: %s", url)
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        runs = data.get("value", [])
        logger.info("Found %d failed NGA test runs", len(runs))

        for run in runs:
            name = run.get("TestName", "Unknown")
            msg = run.get("FailureMessage", "")
            combined_text = f"{name} {msg}"

            correlations = _correlate_to_skills(combined_text)
            if correlations:
                top_skill = correlations[0][0]
                findings.append(
                    Finding(
                        check="learn_nga",
                        target=f"fv-nvu/{top_skill}",
                        status="WARN",
                        message=f"NGA failure in '{name}' may relate to {top_skill}",
                        severity="medium",
                        details=msg[:200] if msg else None,
                    )
                )

    except ImportError:
        findings.append(
            Finding(
                check="learn_nga",
                target="NGA",
                status="SKIP",
                message="requests module not available — NGA offline",
                severity="info",
            )
        )
    except Exception as e:
        findings.append(
            Finding(
                check="learn_nga",
                target="NGA",
                status="ERROR",
                message=f"NGA ingestion error: {e}",
                severity="medium",
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Source: HSDES
# ---------------------------------------------------------------------------


def _ingest_hsdes(config: Dict, since: Optional[str] = None) -> List[Finding]:
    """Ingest HSDES sightings related to NVU."""
    findings: List[Finding] = []
    hsdes_config = config.get("self_learn", {}).get("hsdes", {})

    if not hsdes_config.get("enabled", True):
        findings.append(
            Finding(
                check="learn_hsdes",
                target="HSDES",
                status="SKIP",
                message="HSDES ingestion disabled in config",
                severity="info",
            )
        )
        return findings

    tenants = hsdes_config.get("tenants", ["sighting_central", "heia_soc"])
    components = hsdes_config.get("components", ["NVU", "NPU", "NPX6", "VPX2"])

    try:
        from pysvtools.hsdes import HsdesApi  # type: ignore[import-not-found]

        api = HsdesApi()

        for tenant in tenants:
            for component in components:
                query = {
                    "tenant": tenant,
                    "component": component,
                    "status": "open",
                }
                if since:
                    query["updated_date"] = f">={since}"

                logger.info(
                    "Querying HSDES: tenant=%s, component=%s", tenant, component
                )
                try:
                    results = api.query(query)
                    for item in results:
                        title = item.get("title", "")
                        desc = item.get("description", "")
                        hsd_id = item.get("id", "unknown")
                        combined = f"{title} {desc}"

                        correlations = _correlate_to_skills(combined)
                        if correlations:
                            top_skill = correlations[0][0]
                            findings.append(
                                Finding(
                                    check="learn_hsdes",
                                    target=f"fv-nvu/{top_skill}",
                                    status="WARN",
                                    message=f"HSDES {hsd_id}: '{title[:100]}' may relate to {top_skill}",
                                    severity="medium",
                                    details=f"Tenant: {tenant}, Component: {component}",
                                )
                            )
                except Exception as e:
                    logger.warning(
                        "HSDES query failed for %s/%s: %s", tenant, component, e
                    )

    except ImportError:
        findings.append(
            Finding(
                check="learn_hsdes",
                target="HSDES",
                status="SKIP",
                message="pysvtools.hsdes not available — HSDES offline",
                severity="info",
            )
        )
    except Exception as e:
        findings.append(
            Finding(
                check="learn_hsdes",
                target="HSDES",
                status="ERROR",
                message=f"HSDES ingestion error: {e}",
                severity="medium",
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Source: Manual feedback
# ---------------------------------------------------------------------------


def _ingest_feedback(config: Dict) -> List[Finding]:
    """Ingest manual feedback from feedback_inbox.json."""
    findings: List[Finding] = []
    tools_dir = Path(__file__).parent
    inbox_path = tools_dir / "feedback_inbox.json"

    if not inbox_path.exists():
        findings.append(
            Finding(
                check="learn_feedback",
                target="feedback",
                status="SKIP",
                message="No feedback_inbox.json found",
                severity="info",
            )
        )
        return findings

    try:
        with open(inbox_path, "r", encoding="utf-8") as f:
            feedback_items = json.load(f)

        if not isinstance(feedback_items, list):
            feedback_items = [feedback_items]

        for item in feedback_items:
            skill = item.get("skill", "")
            message = item.get("message", "")
            priority = item.get("priority", "medium")
            keywords = item.get("keywords", [])

            if skill:
                target = f"fv-nvu/{skill}"
            else:
                # Try to correlate from keywords/message
                combined = " ".join(keywords) + " " + message
                correlations = _correlate_to_skills(combined)
                target = (
                    f"fv-nvu/{correlations[0][0]}" if correlations else "fv-nvu/unknown"
                )

            findings.append(
                Finding(
                    check="learn_feedback",
                    target=target,
                    status="WARN",
                    message=f"Feedback: {message[:200]}",
                    severity=priority,
                    details=f"Author: {item.get('author', 'unknown')}, Date: {item.get('date', 'unknown')}",
                )
            )

        logger.info("Ingested %d feedback items", len(feedback_items))

    except Exception as e:
        findings.append(
            Finding(
                check="learn_feedback",
                target="feedback",
                status="ERROR",
                message=f"Feedback ingestion error: {e}",
                severity="medium",
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Coverage gap analysis
# ---------------------------------------------------------------------------


def _analyze_coverage_gaps(config: Dict) -> List[Finding]:
    """Check if signal terms from ingested data appear in skill content."""
    findings: List[Finding] = []
    skill_paths = get_all_skill_paths(config)

    # Collect all skill content
    all_content: Dict[str, str] = {}
    for name in skill_paths:
        content_dict = read_skill(name, config)
        combined = ""
        for key in ("skill", "linux", "windows"):
            val = content_dict.get(key)
            if val:
                combined += val + "\n"
        all_content[name] = combined.lower()

    # Check coverage of important NVU terms
    important_terms = [
        # HAS section references
        ("NVU HAS Section", r"section\s+\d+"),
        # Key component names
        ("NPX6-1K", r"npx6"),
        ("VPX2 DSP", r"vpx2"),
        ("Altek CV-ISP", r"altek"),
        ("VC9000NanoD", r"vc9000"),
        ("DesignWare AXI DMA", r"designware.*axi|axi.*dma"),
        ("IOSF2AXI Bridge", r"iosf2axi"),
        ("FlexNoC Fabric", r"flexnoc|arteris"),
        # Power state terms
        ("D0i2 state", r"d0i2"),
        ("Lid-Closed", r"lid.?closed"),
        ("CRPM", r"crpm"),
        # Security terms
        ("SAI access control", r"sai"),
        ("ATT translation", r"att.*translat"),
        ("ESE authentication", r"ese"),
        # Debug terms
        ("DTF trace", r"dtf"),
        ("VISA2", r"visa"),
        ("MBIST", r"mbist"),
    ]

    for term_name, pattern in important_terms:
        found_in: List[str] = []
        for skill_name, content in all_content.items():
            if re.search(pattern, content, re.IGNORECASE):
                found_in.append(skill_name)

        if not found_in:
            findings.append(
                Finding(
                    check="learn_coverage_gap",
                    target="fv-nvu",
                    status="WARN",
                    message=f"Coverage gap: '{term_name}' not found in any skill file",
                    severity="low",
                    details=f"Pattern: {pattern}",
                )
            )
        elif len(found_in) == 1:
            # Present but only in one skill — might need broader coverage
            logger.debug("'%s' found only in: %s", term_name, found_in[0])

    return findings


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def _generate_summary(findings: List[Finding]) -> Dict:
    """Generate a summary of learn findings."""
    summary: Dict = {
        "total": len(findings),
        "by_source": {},
        "by_skill": {},
        "gaps": 0,
    }

    for f in findings:
        source = f.check.replace("learn_", "")
        summary["by_source"][source] = summary["by_source"].get(source, 0) + 1

        if f.target.startswith("fv-nvu/"):
            skill = f.target.split("/", 1)[1]
            summary["by_skill"][skill] = summary["by_skill"].get(skill, 0) + 1

        if "coverage_gap" in f.check:
            summary["gaps"] += 1

    return summary


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


def run_learn(
    sources: Optional[List[str]] = None,
    since: Optional[str] = None,
    config: Optional[Dict] = None,
) -> Report:
    """Run knowledge gap detection from configured sources."""
    if config is None:
        config = load_config()

    report = Report(name="NVU Self-Learn", version="1.0")
    all_sources = sources or ["nga", "hsdes", "feedback", "coverage"]

    if "nga" in all_sources:
        logger.info("Ingesting NGA failures...")
        report.findings.extend(_ingest_nga(config, since))

    if "hsdes" in all_sources:
        logger.info("Ingesting HSDES sightings...")
        report.findings.extend(_ingest_hsdes(config, since))

    if "feedback" in all_sources:
        logger.info("Ingesting manual feedback...")
        report.findings.extend(_ingest_feedback(config))

    if "coverage" in all_sources:
        logger.info("Analyzing coverage gaps...")
        report.findings.extend(_analyze_coverage_gaps(config))

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_since(since_str: str) -> str:
    """Parse relative time string (7d, 2w, 1m) to ISO date."""
    now = datetime.utcnow()
    match = re.match(r"(\d+)([dwm])", since_str.lower())
    if not match:
        return since_str  # Assume ISO date

    amount = int(match.group(1))
    unit = match.group(2)

    if unit == "d":
        delta = timedelta(days=amount)
    elif unit == "w":
        delta = timedelta(weeks=amount)
    elif unit == "m":
        delta = timedelta(days=amount * 30)
    else:
        delta = timedelta(days=7)

    return (now - delta).strftime(TIMESTAMP_FMT)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NVU Self-Learn — Knowledge gap detection"
    )
    parser.add_argument(
        "--source",
        "-s",
        nargs="+",
        choices=["nga", "hsdes", "feedback", "coverage"],
        help="Sources to ingest",
    )
    parser.add_argument(
        "--since", help="Look back period (e.g., 7d, 2w, 1m, or ISO date)"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--save", help="Save report to file")
    parser.add_argument(
        "--update-timestamp",
        action="store_true",
        help="Update last-run timestamp after completion",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()
    setup_logging("DEBUG" if args.verbose else "INFO")

    config = load_config()

    # Resolve since
    since = None
    if args.since:
        since = _parse_since(args.since)
    else:
        last_run = load_last_run_timestamp("self_learn")
        if last_run:
            since = last_run

    report = run_learn(args.source, since, config)
    summary = _generate_summary(report.findings)

    if args.json:
        output = report.to_dict()
        output["summary"] = summary
        print(json.dumps(output, indent=2))
    else:
        print(report.to_text())
        print(f"\n--- Summary ---")
        print(f"Total findings: {summary['total']}")
        print(f"Coverage gaps: {summary['gaps']}")
        for source, count in summary.get("by_source", {}).items():
            print(f"  {source}: {count}")

    if args.save:
        report.save(Path(args.save))
        logger.info("Report saved to %s", args.save)

    if args.update_timestamp:
        save_last_run_timestamp("self_learn")
        logger.info("Updated self_learn timestamp")

    return 0 if not report.has_failures else 1


if __name__ == "__main__":
    sys.exit(main())
