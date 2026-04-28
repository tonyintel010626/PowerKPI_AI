#!/usr/bin/env python3
"""NVU HAS Coverage Report — Tracks which HAS sections are covered by skill files.

Generates a Markdown or JSON report showing HAS section coverage across all
NVU sub-skill files. Helps identify gaps where HAS content is not yet
reflected in the skill tree.

Usage:
    python nvu_coverage_report.py                 # Markdown report to stdout
    python nvu_coverage_report.py --json           # JSON output
    python nvu_coverage_report.py --output report.md  # Write to file
    python nvu_coverage_report.py --details        # Show per-section detail

HAS Sections (from SIP-NVU1.0-HAS v1.0):
    1. Introduction / Overview
    2. Architecture Overview (sub-IP components)
    3. Register Definitions
    4. IOSF2AXI Bridge / PCI Config
    5. IPC (Inter-Processor Communication)
    6. DMA Controller
    7. MIPI-IF Subsystem (Camera/ISP)
    8. USB-IF Subsystem
    9. SRAM Subsystem
   10. NOC Fabric (Arteris FlexNoC)
   11. ARC VPX2 DSP
   12. NPX6-1K NNA
   13. Power Management
   14. Security / Secure Boot
   15. Debug / DFx / Telemetry
   16. GPIO / Peripherals (I2C, I3C, SPI, UART)
   17. Timers (Watchdog, HPET, RTC)
   18. Clocking
   19. Resets
   20. Fuses / Straps
   21. Software Interface (Driver/BIOS)
   22. Known Opens / Errata
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent

logger = logging.getLogger("nvu_coverage_report")


# ---------------------------------------------------------------------------
# HAS Section Definitions
# ---------------------------------------------------------------------------
# Each section: (id, title, keywords that indicate coverage, expected sub-skills)
HAS_SECTIONS = [
    {
        "id": "HAS-1",
        "title": "Introduction / Overview",
        "keywords": [r"NVU1p0", r"Neural Vision", r"Always-ON.*visual", r"AON"],
        "expected_skills": ["SKILL.md"],
        "priority": "P0",
    },
    {
        "id": "HAS-2",
        "title": "Architecture Overview",
        "keywords": [
            r"ARC VPX2",
            r"NPX6-1K",
            r"MIPI-IF",
            r"USB-IF",
            r"SRAM Subsystem",
            r"DMA Controller",
            r"NOC Fabric",
            r"IOSF2AXI",
            r"Arteris FlexNoC",
        ],
        "expected_skills": ["SKILL.md", "registers/SKILL.md"],
        "priority": "P0",
    },
    {
        "id": "HAS-3",
        "title": "Register Definitions",
        "keywords": [
            r"register map",
            r"MMIO.*offset",
            r"bitfield",
            r"BAR0",
            r"0x[0-9A-Fa-f]{4,}",
        ],
        "expected_skills": ["registers/SKILL.md"],
        "priority": "P0",
    },
    {
        "id": "HAS-4",
        "title": "IOSF2AXI Bridge / PCI Config",
        "keywords": [
            r"IOSF2AXI",
            r"PCI.*config",
            r"BAR0.*64\s*KB",
            r"MSI.*GEN",
            r"RCiEP",
            r"NUM_PCI_FUNCTIONS",
            r"nvu_br_strap",
        ],
        "expected_skills": [
            "registers/SKILL.md",
            "platform/SKILL.md",
            "driver/SKILL.md",
        ],
        "priority": "P0",
    },
    {
        "id": "HAS-5",
        "title": "IPC (Inter-Processor Communication)",
        "keywords": [
            r"Host IPC",
            r"NVU2HOST",
            r"HOST2NVU",
            r"IPC.*doorbell",
            r"IPC.*mailbox",
            r"CSE.*IPC",
            r"PMC.*IPC",
        ],
        "expected_skills": [
            "driver/SKILL.md",
            "firmware/SKILL.md",
            "registers/SKILL.md",
        ],
        "priority": "P0",
    },
    {
        "id": "HAS-6",
        "title": "DMA Controller",
        "keywords": [
            r"DesignWare.*AXI.*DMA",
            r"DW.*DMA",
            r"DMA.*channel",
            r"DMA.*MISC",
            r"boot.*DMA",
            r"paging.*DMA",
            r"v2\.00a",
        ],
        "expected_skills": ["dma/SKILL.md"],
        "priority": "P0",
    },
    {
        "id": "HAS-7",
        "title": "MIPI-IF Subsystem (Camera/ISP)",
        "keywords": [
            r"MIPI.*CSI",
            r"C/D-PHY",
            r"Altek.*ISP",
            r"CV-ISP",
            r"PHY sharing",
            r"IPU.*sharing",
            r"camera.*offload",
        ],
        "expected_skills": ["camera/SKILL.md"],
        "priority": "P0",
    },
    {
        "id": "HAS-8",
        "title": "USB-IF Subsystem",
        "keywords": [
            r"USB.*IF",
            r"XHCI.*camera",
            r"USB.*offload",
            r"SIO.*component",
            r"VC9000NanoD",
            r"MJPEG.*decoder",
        ],
        "expected_skills": ["camera/SKILL.md"],
        "priority": "P0",
    },
    {
        "id": "HAS-9",
        "title": "SRAM Subsystem",
        "keywords": [
            r"3584\s*KB",
            r"7.*slices.*512",
            r"SECDED.*ECC",
            r"SRAM.*retention",
            r"SMMU.*paging",
            r"IMR",
        ],
        "expected_skills": ["SKILL.md", "power/SKILL.md", "firmware/SKILL.md"],
        "priority": "P0",
    },
    {
        "id": "HAS-10",
        "title": "NOC Fabric (Arteris FlexNoC)",
        "keywords": [
            r"Arteris.*FlexNoC",
            r"v5\.4",
            r"NOC.*fabric",
            r"initiator.*target",
        ],
        "expected_skills": ["SKILL.md"],
        "priority": "P1",
    },
    {
        "id": "HAS-11",
        "title": "ARC VPX2 DSP",
        "keywords": [
            r"ARC VPX2",
            r"VPX2",
            r"VLIW.*SIMD",
            r"32KB I\$",
            r"32KB D\$",
            r"128KB VCCM",
            r"scalar.*vector",
        ],
        "expected_skills": ["inference/SKILL.md", "SKILL.md"],
        "priority": "P0",
    },
    {
        "id": "HAS-12",
        "title": "NPX6-1K NNA",
        "keywords": [
            r"NPX6-1K",
            r"1024.*INT8.*MAC",
            r"neural.*processing",
            r"convolution.*accelerator",
            r"tensor.*accelerator",
            r"HS3x",
        ],
        "expected_skills": ["inference/SKILL.md"],
        "priority": "P0",
    },
    {
        "id": "HAS-13",
        "title": "Power Management",
        "keywords": [
            r"D0i[0-3]",
            r"Lid-Closed",
            r"clock.*gating",
            r"power.*gating",
            r"VNN.*0\.75",
            r"CRPM",
            r"PMC.*sideband",
            r"LTR",
            r"Chassis 2\.2",
        ],
        "expected_skills": ["power/SKILL.md"],
        "priority": "P0",
    },
    {
        "id": "HAS-14",
        "title": "Security / Secure Boot",
        "keywords": [
            r"secure boot",
            r"ROM.*code",
            r"SHA.*hash",
            r"SAI",
            r"ATT.*Address.*Translation",
            r"ESE.*authenticate",
            r"SVN",
        ],
        "expected_skills": ["firmware/SKILL.md"],
        "priority": "P0",
    },
    {
        "id": "HAS-15",
        "title": "Debug / DFx / Telemetry",
        "keywords": [
            r"VISA2?",
            r"OCD.*sTAP",
            r"DTF.*trace",
            r"NorthPeak",
            r"MIPI-SysT",
            r"telemetry",
            r"MBIST",
            r"DFx",
        ],
        "expected_skills": ["debug/SKILL.md"],
        "priority": "P0",
    },
    {
        "id": "HAS-16",
        "title": "GPIO / Peripherals",
        "keywords": [
            r"GPIO.*32",
            r"I2C.*3x",
            r"I3C.*2x",
            r"SPI.*2x",
            r"UART.*3x",
            r"DesignWare.*peripheral",
            r"sensor.*control",
        ],
        "expected_skills": ["platform/SKILL.md", "SKILL.md"],
        "priority": "P1",
    },
    {
        "id": "HAS-17",
        "title": "Timers",
        "keywords": [r"watchdog", r"HPET", r"RTC.*64-bit", r"VPX2.*timer"],
        "expected_skills": ["debug/SKILL.md", "SKILL.md"],
        "priority": "P1",
    },
    {
        "id": "HAS-18",
        "title": "Clocking",
        "keywords": [
            r"clock domain",
            r"PLL",
            r"trunk clock",
            r"ring clock",
            r"10 clock domain",
        ],
        "expected_skills": ["power/SKILL.md", "platform/SKILL.md"],
        "priority": "P1",
    },
    {
        "id": "HAS-19",
        "title": "Resets",
        "keywords": [
            r"reset.*sequence",
            r"IP.*reset",
            r"warm.*reset",
            r"cold.*reset",
            r"PLTRST",
            r"SoC.*reset",
        ],
        "expected_skills": ["platform/SKILL.md"],
        "priority": "P0",
    },
    {
        "id": "HAS-20",
        "title": "Fuses / Straps",
        "keywords": [
            r"fuse",
            r"strap",
            r"nvu_br_strap",
            r"NVU_VSI9000NanoD_enable",
            r"devfuncnum",
            r"deviceid",
        ],
        "expected_skills": ["platform/SKILL.md"],
        "priority": "P0",
    },
    {
        "id": "HAS-21",
        "title": "Software Interface (Driver/BIOS)",
        "keywords": [
            r"driver.*interface",
            r"BIOS.*init",
            r"ACPI",
            r"FW.*load",
            r"power.*transition",
            r"NVU FAS",
        ],
        "expected_skills": ["driver/SKILL.md", "bios/SKILL.md"],
        "priority": "P0",
    },
    {
        "id": "HAS-22",
        "title": "Known Opens / Errata",
        "keywords": [
            r"HSD \d+",
            r"open.*issue",
            r"errata",
            r"corner.*case",
            r"RTL.*open",
            r"ECN",
        ],
        "expected_skills": ["debug/SKILL.md", "SKILL.md"],
        "priority": "P1",
    },
]


# ---------------------------------------------------------------------------
# Coverage analysis
# ---------------------------------------------------------------------------
def load_skill_content(skill_path: str) -> str:
    """Load a skill file's content."""
    full_path = SKILL_ROOT / skill_path
    if full_path.exists():
        return full_path.read_text(encoding="utf-8", errors="replace")
    return ""


def check_section_coverage(
    section: Dict[str, Any],
    skill_contents: Dict[str, str],
) -> Dict[str, Any]:
    """Check coverage of a HAS section across skill files.

    Returns coverage data with per-keyword and per-file results.
    """
    result: Dict[str, Any] = {
        "id": section["id"],
        "title": section["title"],
        "priority": section["priority"],
        "expected_skills": section["expected_skills"],
        "status": "UNCOVERED",
        "coverage_pct": 0.0,
        "keywords_found": 0,
        "keywords_total": len(section["keywords"]),
        "skill_hits": {},
        "keyword_details": [],
    }

    total_keywords = len(section["keywords"])
    found_keywords = 0
    keyword_details = []

    for kw_pattern in section["keywords"]:
        kw_found = False
        kw_files = []

        for skill_path in section["expected_skills"]:
            content = skill_contents.get(skill_path, "")
            if content and re.search(kw_pattern, content, re.IGNORECASE):
                kw_found = True
                kw_files.append(skill_path)
                result["skill_hits"].setdefault(skill_path, 0)
                result["skill_hits"][skill_path] += 1

        if not kw_found:
            # Search ALL skill files as fallback
            for skill_path, content in skill_contents.items():
                if content and re.search(kw_pattern, content, re.IGNORECASE):
                    kw_found = True
                    kw_files.append(f"{skill_path} (fallback)")
                    result["skill_hits"].setdefault(skill_path, 0)
                    result["skill_hits"][skill_path] += 1

        if kw_found:
            found_keywords += 1

        keyword_details.append(
            {
                "pattern": kw_pattern,
                "found": kw_found,
                "files": kw_files,
            }
        )

    result["keywords_found"] = found_keywords
    result["keywords_total"] = total_keywords
    result["keyword_details"] = keyword_details

    if total_keywords > 0:
        result["coverage_pct"] = round(100.0 * found_keywords / total_keywords, 1)

    # Status classification
    if result["coverage_pct"] >= 80:
        result["status"] = "COVERED"
    elif result["coverage_pct"] >= 40:
        result["status"] = "PARTIAL"
    else:
        result["status"] = "UNCOVERED"

    return result


def run_coverage_analysis() -> Dict[str, Any]:
    """Run full coverage analysis across all HAS sections."""
    # Load all skill files
    skill_files = [
        "SKILL.md",
        "registers/SKILL.md",
        "inference/SKILL.md",
        "dma/SKILL.md",
        "power/SKILL.md",
        "driver/SKILL.md",
        "platform/SKILL.md",
        "debug/SKILL.md",
        "camera/SKILL.md",
        "firmware/SKILL.md",
        "bios/SKILL.md",
        "simics/SKILL.md",
    ]
    skill_contents: Dict[str, str] = {}
    for sf in skill_files:
        skill_contents[sf] = load_skill_content(sf)

    # Check each section
    sections = []
    for section_def in HAS_SECTIONS:
        result = check_section_coverage(section_def, skill_contents)
        sections.append(result)

    # Aggregate stats
    total = len(sections)
    covered = sum(1 for s in sections if s["status"] == "COVERED")
    partial = sum(1 for s in sections if s["status"] == "PARTIAL")
    uncovered = sum(1 for s in sections if s["status"] == "UNCOVERED")

    p0_sections = [s for s in sections if s["priority"] == "P0"]
    p0_covered = sum(1 for s in p0_sections if s["status"] == "COVERED")

    avg_coverage = round(
        sum(s["coverage_pct"] for s in sections) / total if total else 0, 1
    )

    return {
        "generated": datetime.now().isoformat(),
        "tool": "nvu_coverage_report.py",
        "summary": {
            "total_sections": total,
            "covered": covered,
            "partial": partial,
            "uncovered": uncovered,
            "avg_coverage_pct": avg_coverage,
            "p0_total": len(p0_sections),
            "p0_covered": p0_covered,
        },
        "sections": sections,
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def generate_markdown(data: Dict[str, Any], details: bool = False) -> str:
    """Generate Markdown coverage report."""
    summary = data["summary"]
    sections = data["sections"]

    lines = [
        "# NVU HAS Coverage Report",
        "",
        f"> Generated: {data['generated'][:19]}",
        f"> Tool: `{data['tool']}`",
        "",
        "## Summary",
        "",
        f"- **Total HAS Sections**: {summary['total_sections']}",
        f"- **Covered (≥80%)**: {summary['covered']} ✅",
        f"- **Partial (40-79%)**: {summary['partial']} ⚠️",
        f"- **Uncovered (<40%)**: {summary['uncovered']} ❌",
        f"- **Average Coverage**: {summary['avg_coverage_pct']}%",
        f"- **P0 Coverage**: {summary['p0_covered']}/{summary['p0_total']}",
        "",
        "## Section Coverage",
        "",
        "| # | Section | Priority | Coverage | Status |",
        "|---|---------|----------|----------|--------|",
    ]

    for s in sections:
        status_icon = {"COVERED": "✅", "PARTIAL": "⚠️", "UNCOVERED": "❌"}[s["status"]]
        lines.append(
            f"| {s['id']} | {s['title']} | {s['priority']} | "
            f"{s['coverage_pct']}% ({s['keywords_found']}/{s['keywords_total']}) | "
            f"{status_icon} {s['status']} |"
        )

    lines.append("")

    # Gaps section
    gaps = [s for s in sections if s["status"] != "COVERED"]
    if gaps:
        lines.append("## Coverage Gaps")
        lines.append("")
        for s in gaps:
            lines.append(f"### {s['id']}: {s['title']} ({s['coverage_pct']}%)")
            lines.append("")
            missing = [kd for kd in s["keyword_details"] if not kd["found"]]
            if missing:
                lines.append("Missing keywords:")
                for kd in missing:
                    lines.append(f"- `{kd['pattern']}`")
            lines.append(f"- Expected in: {', '.join(s['expected_skills'])}")
            lines.append("")

    if details:
        lines.append("## Detailed Keyword Coverage")
        lines.append("")
        for s in sections:
            lines.append(f"### {s['id']}: {s['title']}")
            lines.append("")
            for kd in s["keyword_details"]:
                icon = "✅" if kd["found"] else "❌"
                files = ", ".join(kd["files"]) if kd["files"] else "none"
                lines.append(f"- {icon} `{kd['pattern']}` → {files}")
            lines.append("")

    lines.append("---")
    lines.append(
        "*Generated by nvu_coverage_report.py — part of the NVU self-improvement toolchain*"
    )
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="NVU HAS Coverage Report")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--details", action="store_true", help="Per-keyword detail")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Fail if average coverage below threshold (e.g. 70.0)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.json else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # Run analysis
    data = run_coverage_analysis()
    summary = data["summary"]

    # Output
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        report = generate_markdown(data, details=args.details)
        if args.output:
            Path(args.output).write_text(report, encoding="utf-8")
            logger.info(
                "Wrote coverage report to %s — %d/%d covered (%.1f%%)",
                args.output,
                summary["covered"],
                summary["total_sections"],
                summary["avg_coverage_pct"],
            )
        else:
            print(report)

    # Threshold check
    if args.threshold > 0 and summary["avg_coverage_pct"] < args.threshold:
        logger.warning(
            "Coverage %.1f%% is below threshold %.1f%%",
            summary["avg_coverage_pct"],
            args.threshold,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
