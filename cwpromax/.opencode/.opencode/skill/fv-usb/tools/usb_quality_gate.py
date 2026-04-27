#!/usr/bin/env python3
"""
FV-USB Quality Gate Script
Domain: USB Functional Validation
Owner: kvejaya
Version: 2.0.0

Combined quality gate that runs self-check + self-verify and produces
a composite pass/fail score. Designed for pre-commit or CI integration.

Usage:
    python usb_quality_gate.py [--config CONFIG_PATH] [--verbose] [--strict]
    python usb_quality_gate.py --pre-commit   # Minimal output for git hook
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONFIG = REPO_ROOT / ".opencode" / "skill" / "fv-usb" / "tools" / "self_improvement_config.json"

# Import sibling scripts
sys.path.insert(0, str(Path(__file__).parent))
from usb_self_check import run_self_check
from usb_self_verify import run_self_verify


def compute_score(check_passes: int, check_fails: int,
                  verify_passes: int, verify_fails: int, verify_skips: int) -> float:
    """
    Compute composite quality score (0-100).

    Weighting:
      - Structural checks (self_check): 30%
      - Content assertions (self_verify): 70%
    """
    check_total = check_passes + check_fails
    verify_total = verify_passes + verify_fails  # skips excluded

    check_pct = (check_passes / max(check_total, 1)) * 100
    verify_pct = (verify_passes / max(verify_total, 1)) * 100

    score = (check_pct * 0.30) + (verify_pct * 0.70)
    return round(score, 1)


def run_quality_gate(config_path: str = None, verbose: bool = False,
                     strict: bool = False, pre_commit: bool = False) -> int:
    """
    Run the full quality gate.

    Returns:
        0 = PASS, 1 = FAIL
    """
    config_file = config_path or str(DEFAULT_CONFIG)

    if not pre_commit:
        print("=" * 60)
        print("FV-USB QUALITY GATE")
        print(f"Date: {datetime.now().isoformat()}")
        print("=" * 60)

    # Phase 1: Structural checks
    if not pre_commit:
        print("\n--- Phase 1: Self-Check (Structural) ---")
    check_passes, check_fails, check_msgs = run_self_check(config_file, verbose)

    # Phase 2: Content assertions
    if not pre_commit:
        print("\n--- Phase 2: Self-Verify (Content) ---")
    verify_passes, verify_fails, verify_skips, verify_msgs = run_self_verify(
        config_file, verbose
    )

    # Compute score
    score = compute_score(check_passes, check_fails, verify_passes, verify_fails, verify_skips)

    # Load threshold from config
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    threshold = config["self_verify"]["pass_threshold_pct"]

    # In strict mode, any failure = gate fail
    if strict:
        gate_pass = (check_fails == 0) and (verify_fails == 0)
    else:
        gate_pass = score >= threshold

    # Output
    status = "PASS" if gate_pass else "FAIL"

    if pre_commit:
        # Minimal output for git hooks
        if not gate_pass:
            print(f"FV-USB Quality Gate: {status} (score={score}%, threshold={threshold}%)")
            print(f"  Structural: {check_passes}/{check_passes + check_fails}")
            print(f"  Content: {verify_passes}/{verify_passes + verify_fails}")
        return 0 if gate_pass else 1

    # Full report
    print(f"\n{'='*60}")
    print(f"QUALITY GATE: {status}")
    print(f"  Composite Score: {score}%")
    print(f"  Threshold: {threshold}%")
    print(f"  Structural: {check_passes} pass / {check_fails} fail")
    print(f"  Content: {verify_passes} pass / {verify_fails} fail / {verify_skips} skip")
    print(f"{'='*60}")

    # Write gate report to reports dir
    reports_dir = REPO_ROOT / config["paths"]["reports_dir"]
    if reports_dir.exists():
        report = {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "score": score,
            "threshold": threshold,
            "structural": {
                "passes": check_passes,
                "fails": check_fails,
            },
            "content": {
                "passes": verify_passes,
                "fails": verify_fails,
                "skips": verify_skips,
            },
        }
        report_file = reports_dir / "quality_gate_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Report written to: {report_file}")

    return 0 if gate_pass else 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FV-USB Quality Gate")
    parser.add_argument("--config", type=str, default=None, help="Config file path")
    parser.add_argument("--verbose", action="store_true", help="Show all results")
    parser.add_argument("--strict", action="store_true", help="Any failure = gate fail")
    parser.add_argument("--pre-commit", action="store_true", help="Minimal pre-commit output")
    args = parser.parse_args()

    rc = run_quality_gate(args.config, args.verbose, args.strict, args.pre_commit)
    sys.exit(rc)
