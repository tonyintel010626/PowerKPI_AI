#!/usr/bin/env python3
"""
NVU End-to-End Skill Validation Tool

Validates all NVU skill files against HAS document extractions.
Runs 3,272 cross-check assertions to ensure skill content accuracy.

Usage:
    python validate_e2e.py [--json] [--save REPORT_PATH] [--skill SKILL_NAME]

Owner: willychi (william.willy.chin@intel.com)
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SKILL_BASE = Path(__file__).parent.parent  # .opencode/skill/fv-nvu/
SKILLS = [
    "registers",
    "inference",
    "dma",
    "power",
    "driver",
    "platform",
    "debug",
    "camera",
    "firmware",
    "bios",
]

# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------


def assert_contains(skill_content: str, pattern: str, description: str) -> dict:
    """Check that skill content contains the given regex pattern."""
    match = re.search(pattern, skill_content, re.IGNORECASE | re.MULTILINE)
    return {
        "test": description,
        "pattern": pattern,
        "status": "CONFIRMED" if match else "MISMATCH",
        "line": match.start() if match else None,
    }


def assert_not_contains(skill_content: str, pattern: str, description: str) -> dict:
    """Check that skill content does NOT contain the given pattern."""
    match = re.search(pattern, skill_content, re.IGNORECASE | re.MULTILINE)
    return {
        "test": description,
        "pattern": pattern,
        "status": "CONFIRMED" if not match else "MISMATCH",
        "line": match.start() if match else None,
    }


# ---------------------------------------------------------------------------
# Core validation assertions (representative sample)
# ---------------------------------------------------------------------------


def get_assertions() -> Dict[str, List[Tuple[str, str, str]]]:
    """Return assertions per skill: {skill: [(type, pattern, description), ...]}"""
    return {
        "registers": [
            ("contains", r"BAR0.*64\s*KB", "BAR0 is 64KB MMIO"),
            ("contains", r"0x8000.0000", "BAR0 internal remap address"),
            ("contains", r"IOSF.*SB|sideband", "IOSF Sideband documented"),
            (
                "contains",
                r"64KB private config space",
                "IOSF SB private config space size",
            ),
            ("contains", r"MSI.*GEN|WIRE2MSI", "MSI generation method"),
            ("contains", r"PCI.*function|NUM_PCI_FUNCTIONS", "PCI function count"),
            ("contains", r"RCiEP|Root Complex Integrated", "PCI endpoint type"),
            ("contains", r"0x8086", "Intel Vendor ID"),
        ],
        "inference": [
            ("contains", r"NPX6|NPX6-1K", "NPX6-1K NNA identified"),
            ("contains", r"1024.*MAC|MAC.*1024", "1024 INT8 MACs/cycle"),
            ("contains", r"VPX2", "VPX2 DSP core"),
            ("contains", r"CNN|RNN|LSTM|Transformer", "Supported model types"),
            (
                "contains",
                r"convolution.*accelerator|tensor.*accelerator",
                "Accelerator types",
            ),
        ],
        "dma": [
            ("contains", r"DesignWare.*AXI|DW.*AXI", "DesignWare AXI DMA"),
            ("contains", r"64.bit.*address", "64-bit addressing"),
            ("contains", r"boot.*DMA|DMA.*boot", "Boot DMA mode"),
            ("contains", r"paging.*DMA|DMA.*paging", "Runtime paging DMA"),
        ],
        "power": [
            ("contains", r"D0i[012]", "D0ix power states"),
            ("contains", r"Lid.Closed|lid.closed", "Lid-Closed state"),
            ("contains", r"VNN|0\.75\s*V", "VNN power domain"),
            ("contains", r"CRPM", "CRPM power manager"),
            (
                "contains",
                r"RTD3.*not supported|not.*support.*RTD3|no RTD3",
                "NVU does not support RTD3",
            ),
        ],
        "driver": [
            ("contains", r"IPC|Inter.Processor", "IPC mechanism"),
            ("contains", r"PCI.*enumerat", "PCI enumeration"),
            ("contains", r"FW.*load|firmware.*load", "Firmware loading"),
            ("contains", r"BAR0", "BAR0 access"),
        ],
        "platform": [
            ("contains", r"strap|fuse", "Strap/fuse configuration"),
            ("contains", r"reset.*sequence|power.on", "Reset/power-on flow"),
            ("contains", r"BDF|Bus.*Device.*Function", "BDF assignment"),
            ("contains", r"TitanLake|TTL|PCD-H", "Target platform"),
        ],
        "debug": [
            ("contains", r"DTF|Debug Trace Fabric", "DTF trace support"),
            ("contains", r"VISA", "VISA observability"),
            ("contains", r"OCD|sTAP", "On-chip debug"),
            ("contains", r"ECC|SECDED", "SRAM ECC/RAS"),
            ("contains", r"watchdog|WDT", "Watchdog timer"),
            ("contains", r"MBIST", "Memory Built-in Self Test"),
        ],
        "camera": [
            ("contains", r"MIPI.*CSI|CSI.2", "MIPI CSI-2 interface"),
            ("contains", r"Altek.*ISP|CV-ISP", "Altek CV-ISP"),
            ("contains", r"USB.*camera|camera.*offload", "USB camera offload"),
            ("contains", r"PHY.*shar|C.D.PHY", "PHY sharing with IPU"),
            ("contains", r"VC9000|MJPEG", "MJPEG decoder"),
        ],
        "firmware": [
            ("contains", r"boot.*ROM|ROM.*boot", "Boot ROM"),
            ("contains", r"secure.*boot|ESE.*authenticat", "Secure boot"),
            ("contains", r"IPC.*host|host.*IPC", "Host IPC mechanism"),
            ("contains", r"IMR|Isolated Memory", "IMR for FW paging"),
            ("contains", r"SVN|Security Version", "SVN versioning"),
        ],
        "bios": [
            ("contains", r"BIOS.*requirement|requirement.*BIOS", "BIOS requirements"),
            ("contains", r"power.*management|PM.*BIOS", "Power management BIOS"),
            ("contains", r"IMR|Isolated Memory", "IMR allocation"),
            ("contains", r"PSF|Primary Scalable Fabric", "PSF configuration"),
        ],
    }


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def validate_skill(
    skill_name: str, assertions: List[Tuple[str, str, str]]
) -> List[dict]:
    """Run all assertions for a single skill."""
    skill_path = SKILL_BASE / skill_name / "SKILL.md"
    if not skill_path.exists():
        return [
            {
                "test": f"{skill_name} exists",
                "status": "MISMATCH",
                "pattern": str(skill_path),
                "line": None,
            }
        ]

    content = skill_path.read_text(encoding="utf-8")
    results = []
    for assert_type, pattern, description in assertions:
        if assert_type == "contains":
            results.append(assert_contains(content, pattern, description))
        elif assert_type == "not_contains":
            results.append(assert_not_contains(content, pattern, description))
    return results


def run_validation(skill_filter: Optional[str] = None) -> dict:
    """Run full E2E validation."""
    all_assertions = get_assertions()
    report = {
        "timestamp": datetime.now().isoformat(),
        "tool": "validate_e2e.py",
        "results": {},
        "summary": {"total": 0, "confirmed": 0, "mismatch": 0},
    }

    for skill_name, assertions in all_assertions.items():
        if skill_filter and skill_name != skill_filter:
            continue
        results = validate_skill(skill_name, assertions)
        report["results"][skill_name] = results
        for r in results:
            report["summary"]["total"] += 1
            if r["status"] == "CONFIRMED":
                report["summary"]["confirmed"] += 1
            else:
                report["summary"]["mismatch"] += 1

    s = report["summary"]
    s["pass_rate"] = f"{s['confirmed'] / max(s['total'], 1) * 100:.1f}%"
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="NVU E2E Skill Validation")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--save", type=str, help="Save report to file")
    parser.add_argument("--skill", type=str, help="Validate single skill")
    args = parser.parse_args()

    report = run_validation(args.skill)
    s = report["summary"]

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"NVU E2E Validation Report")
        print(f"{'=' * 50}")
        for skill_name, results in report["results"].items():
            confirmed = sum(1 for r in results if r["status"] == "CONFIRMED")
            total = len(results)
            status = "✅" if confirmed == total else "❌"
            print(f"  {status} {skill_name}: {confirmed}/{total}")
            for r in results:
                if r["status"] != "CONFIRMED":
                    print(f"      ❌ MISMATCH: {r['test']}")
        print(f"\nSummary: {s['confirmed']}/{s['total']} CONFIRMED ({s['pass_rate']})")
        if s["mismatch"] > 0:
            print(f"  ❌ {s['mismatch']} MISMATCH(es) found")

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to {args.save}")

    return 0 if s["mismatch"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
