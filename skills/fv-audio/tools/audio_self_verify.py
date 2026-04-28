#!/usr/bin/env python3
"""
FV-AUDIO Self-Verify — Eval test runner and content accuracy verification.

Runs assertion-based tests against the audio skill tree to verify that
skill file content is accurate and complete. Tests are defined in the
eval JSON file (if present) or run as built-in structural verifications.

Built-in verification categories:
  V01  architecture     — ACE 4.x, PCI identity, IP blocks
  V02  hda_protocol     — HDA link, codec discovery, CORB/RIRB
  V03  soundwire        — SoundWire enumeration, stream config
  V04  dmic             — DMIC PDM interface, clock config
  V05  display_audio    — iDisp, HDMI/DP audio, ELD
  V06  uaol             — USB Audio Offload, xHCI integration
  V07  power            — D0i3, D3, SRAM-PG, S0ix, LTR
  V08  dsp              — DSP cores, firmware load, IPC
  V09  wov              — Wake on Voice, CRO, DMIC always-on
  V10  clocking         — Clock sources, PLL, CRO
  V11  subskill_coverage — all 17 sub-skills have minimum content
  V12  cross_domain     — cross-references between related skills

Usage:
    python audio_self_verify.py [--json] [-v]

Adapted from FV-THC thc_self_verify.py.
Owner: huiyingt (Tan Hui Ying)
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
)


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------
def assert_contains(text: str, pattern: str, case_sensitive: bool = False) -> bool:
    """Return True if *pattern* is found in *text*."""
    if not case_sensitive:
        return pattern.lower() in text.lower()
    return pattern in text


def assert_not_contains(text: str, pattern: str, case_sensitive: bool = False) -> bool:
    return not assert_contains(text, pattern, case_sensitive)


def assert_regex(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, text, re.IGNORECASE))


def assert_min_lines(text: str, min_lines: int) -> bool:
    return len(text.splitlines()) >= min_lines


def assert_has_section(text: str, heading: str) -> bool:
    """Check if markdown has a section with given heading text."""
    return bool(re.search(rf'^#{{1,4}}\s+.*{re.escape(heading)}', text, re.MULTILINE | re.IGNORECASE))


# ---------------------------------------------------------------------------
# Built-in verification tests
# ---------------------------------------------------------------------------

def verify_architecture(cfg: dict, report: Report) -> None:
    """V01: Core architecture terms present in agent def and key skills."""
    cid = "V01_architecture"
    agent = read_agent_def(cfg)
    if not agent:
        report.skip(cid, "Agent definition not found")
        return

    required_terms = [
        ("ACE", "ACE audio engine reference"),
        ("PCI", "PCI device identity"),
        ("HDA", "HD Audio reference"),
        ("SoundWire", "SoundWire bus reference"),
        ("DSP", "DSP core reference"),
    ]
    for term, desc in required_terms:
        if assert_contains(agent, term):
            report.pass_(f"{cid}_{term}", f"Agent def contains '{term}' ({desc})")
        else:
            report.fail(f"{cid}_{term}", f"Agent def missing '{term}' ({desc})")


def verify_hda_protocol(cfg: dict, report: Report) -> None:
    """V02: HDA skill covers core protocol elements."""
    cid = "V02_hda"
    content = read_skill("hda", cfg)
    if not content:
        report.skip(cid, "HDA skill not found")
        return

    terms = ["CORB", "RIRB", "codec", "verb", "stream", "widget"]
    for term in terms:
        if assert_contains(content, term):
            report.pass_(f"{cid}_{term}", f"HDA skill contains '{term}'")
        else:
            report.warn(f"{cid}_{term}", f"HDA skill missing '{term}'")


def verify_soundwire(cfg: dict, report: Report) -> None:
    """V03: SoundWire skill covers bus enumeration and stream config."""
    cid = "V03_soundwire"
    content = read_skill("soundwire", cfg)
    if not content:
        report.skip(cid, "SoundWire skill not found")
        return

    terms = ["enumeration", "stream", "data port", "lane", "MIPI"]
    for term in terms:
        if assert_contains(content, term):
            report.pass_(f"{cid}_{term.replace(' ', '_')}", f"SoundWire skill contains '{term}'")
        else:
            report.warn(f"{cid}_{term.replace(' ', '_')}", f"SoundWire skill missing '{term}'")


def verify_dmic(cfg: dict, report: Report) -> None:
    """V04: DMIC skill covers PDM interface and clock configuration."""
    cid = "V04_dmic"
    content = read_skill("dmic", cfg)
    if not content:
        report.skip(cid, "DMIC skill not found")
        return

    terms = ["PDM", "clock", "FIFO", "gain", "GPIO"]
    for term in terms:
        if assert_contains(content, term):
            report.pass_(f"{cid}_{term}", f"DMIC skill contains '{term}'")
        else:
            report.warn(f"{cid}_{term}", f"DMIC skill missing '{term}'")


def verify_display_audio(cfg: dict, report: Report) -> None:
    """V05: Display audio skill covers HDMI/DP and ELD."""
    cid = "V05_display_audio"
    content = read_skill("display-audio", cfg)
    if not content:
        report.skip(cid, "Display-audio skill not found")
        return

    terms = ["HDMI", "DisplayPort", "ELD", "hot plug", "iDisp"]
    for term in terms:
        if assert_contains(content, term):
            report.pass_(f"{cid}_{term.replace(' ', '_')}", f"Display-audio skill contains '{term}'")
        else:
            report.warn(f"{cid}_{term.replace(' ', '_')}", f"Display-audio skill missing '{term}'")


def verify_uaol(cfg: dict, report: Report) -> None:
    """V06: UAOL skill covers USB Audio Offload and xHCI integration."""
    cid = "V06_uaol"
    content = read_skill("uaol", cfg)
    if not content:
        report.skip(cid, "UAOL skill not found")
        return

    terms = ["xHCI", "isochronous", "FIFO", "offload", "ACE"]
    for term in terms:
        if assert_contains(content, term):
            report.pass_(f"{cid}_{term}", f"UAOL skill contains '{term}'")
        else:
            report.warn(f"{cid}_{term}", f"UAOL skill missing '{term}'")


def verify_power(cfg: dict, report: Report) -> None:
    """V07: Power skill covers D-states, SRAM-PG, LTR, S0ix."""
    cid = "V07_power"
    content = read_skill("power", cfg)
    if not content:
        report.skip(cid, "Power skill not found")
        return

    terms = ["D0i3", "D3", "SRAM", "LTR", "S0ix", "power gate", "PLL"]
    for term in terms:
        if assert_contains(content, term):
            report.pass_(f"{cid}_{term.replace(' ', '_')}", f"Power skill contains '{term}'")
        else:
            report.warn(f"{cid}_{term.replace(' ', '_')}", f"Power skill missing '{term}'")


def verify_dsp(cfg: dict, report: Report) -> None:
    """V08: DSP skill covers core bring-up, firmware, IPC."""
    cid = "V08_dsp"
    content = read_skill("dsp", cfg)
    if not content:
        report.skip(cid, "DSP skill not found")
        return

    terms = ["firmware", "IPC", "SRAM", "pipeline", "core"]
    for term in terms:
        if assert_contains(content, term):
            report.pass_(f"{cid}_{term}", f"DSP skill contains '{term}'")
        else:
            report.warn(f"{cid}_{term}", f"DSP skill missing '{term}'")


def verify_wov(cfg: dict, report: Report) -> None:
    """V09: WoV skill covers wake-on-voice, CRO, DMIC always-on."""
    cid = "V09_wov"
    content = read_skill("wov", cfg)
    if not content:
        report.skip(cid, "WoV skill not found")
        return

    terms = ["keyword", "CRO", "always-on", "S0ix", "DMIC"]
    for term in terms:
        if assert_contains(content, term):
            report.pass_(f"{cid}_{term.replace('-', '_')}", f"WoV skill contains '{term}'")
        else:
            report.warn(f"{cid}_{term.replace('-', '_')}", f"WoV skill missing '{term}'")


def verify_clocking(cfg: dict, report: Report) -> None:
    """V10: Clocking skill covers clock sources, PLL, CRO."""
    cid = "V10_clocking"
    content = read_skill("clocking", cfg)
    if not content:
        report.skip(cid, "Clocking skill not found")
        return

    terms = ["PLL", "XTAL", "clock", "CRO", "domain"]
    for term in terms:
        if assert_contains(content, term):
            report.pass_(f"{cid}_{term}", f"Clocking skill contains '{term}'")
        else:
            report.warn(f"{cid}_{term}", f"Clocking skill missing '{term}'")


def verify_subskill_coverage(cfg: dict, report: Report) -> None:
    """V11: All 17 sub-skills have minimum content (>20 lines)."""
    cid = "V11_subskill_coverage"
    min_lines = 20
    for name, path in get_all_skill_paths(cfg):
        content = read_skill(name, cfg)
        if content is None:
            report.fail(f"{cid}_{name}", f"Sub-skill '{name}' SKILL.md not found")
            continue
        lines = len(content.splitlines())
        if lines >= min_lines:
            report.pass_(f"{cid}_{name}", f"Sub-skill '{name}' has {lines} lines (≥{min_lines})")
        else:
            report.warn(f"{cid}_{name}", f"Sub-skill '{name}' only has {lines} lines (<{min_lines})")


def verify_cross_domain(cfg: dict, report: Report) -> None:
    """V12: Cross-domain references between related skills."""
    cid = "V12_cross_domain"
    # UAOL should reference both audio and USB domains
    uaol = read_skill("uaol", cfg)
    if uaol:
        if assert_contains(uaol, "USB") and assert_contains(uaol, "audio"):
            report.pass_(f"{cid}_uaol_domains", "UAOL references both USB and audio domains")
        else:
            report.warn(f"{cid}_uaol_domains", "UAOL should reference both USB and audio")

    # Power should reference S0ix integration
    power = read_skill("power", cfg)
    if power:
        if assert_contains(power, "S0ix"):
            report.pass_(f"{cid}_power_s0ix", "Power skill references S0ix integration")
        else:
            report.warn(f"{cid}_power_s0ix", "Power skill should reference S0ix")

    # WoV should reference DMIC and clocking
    wov = read_skill("wov", cfg)
    if wov:
        refs = sum(1 for t in ["DMIC", "clock", "CRO"] if assert_contains(wov, t))
        if refs >= 2:
            report.pass_(f"{cid}_wov_refs", f"WoV has {refs}/3 expected cross-refs")
        else:
            report.warn(f"{cid}_wov_refs", f"WoV only has {refs}/3 expected cross-refs (DMIC, clock, CRO)")

    # BT-offload should reference SSP/I2S
    bt = read_skill("bt-offload", cfg)
    if bt:
        if assert_contains(bt, "SSP") or assert_contains(bt, "I2S"):
            report.pass_(f"{cid}_bt_ssp", "BT-offload references SSP/I2S interface")
        else:
            report.warn(f"{cid}_bt_ssp", "BT-offload should reference SSP or I2S")


# ---------------------------------------------------------------------------
# Eval-file based tests (if eval JSON exists)
# ---------------------------------------------------------------------------
def run_eval_tests(cfg: dict, report: Report) -> None:
    """Run tests from the eval JSON file if it exists."""
    verify_cfg = cfg.get("self_verify", {})
    eval_file = verify_cfg.get("eval_tests_file", "")
    if not eval_file:
        report.skip("eval_tests", "No eval_tests_file configured")
        return

    base = resolve_path(cfg["paths"]["skill_base"])
    path = base / eval_file
    if not path.exists():
        report.skip("eval_tests", f"Eval file not found: {eval_file}")
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            tests = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        report.error("eval_tests", f"Failed to load eval file: {exc}")
        return

    # Process each test
    for test in tests if isinstance(tests, list) else tests.get("tests", []):
        test_id = test.get("id", "unknown")
        skill_name = test.get("skill", "")
        assertion = test.get("assertion", "contains")
        pattern = test.get("pattern", "")
        description = test.get("description", "")

        content = read_skill(skill_name, cfg) if skill_name else read_agent_def(cfg)
        if content is None:
            report.skip(f"eval_{test_id}", f"Target not found for test: {description}")
            continue

        passed = False
        if assertion == "contains":
            passed = assert_contains(content, pattern)
        elif assertion == "not_contains":
            passed = assert_not_contains(content, pattern)
        elif assertion == "regex":
            passed = assert_regex(content, pattern)
        elif assertion == "min_lines":
            passed = assert_min_lines(content, int(pattern))
        elif assertion == "has_section":
            passed = assert_has_section(content, pattern)
        else:
            report.skip(f"eval_{test_id}", f"Unknown assertion type: {assertion}")
            continue

        if passed:
            report.pass_(f"eval_{test_id}", description or f"{assertion}({pattern})")
        else:
            report.fail(f"eval_{test_id}", description or f"FAILED: {assertion}({pattern})")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
ALL_VERIFICATIONS = [
    verify_architecture,
    verify_hda_protocol,
    verify_soundwire,
    verify_dmic,
    verify_display_audio,
    verify_uaol,
    verify_power,
    verify_dsp,
    verify_wov,
    verify_clocking,
    verify_subskill_coverage,
    verify_cross_domain,
]


def run_all_tests(cfg: dict | None = None) -> Report:
    """Execute all verification tests and return aggregated report."""
    t0 = time.time()
    cfg = cfg or load_config()
    report = Report(stage="self-verify")

    # Built-in verifications
    for verify_fn in ALL_VERIFICATIONS:
        try:
            verify_fn(cfg, report)
        except Exception as exc:
            report.error(verify_fn.__name__, f"Unhandled exception: {exc}")

    # Eval-file tests
    try:
        run_eval_tests(cfg, report)
    except Exception as exc:
        report.error("eval_tests_runner", f"Eval runner failed: {exc}")

    report.finalize(t0)
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="FV-AUDIO content verification")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    setup_logging(args.verbose)

    report = run_all_tests()
    if args.json:
        print(report.to_json())
    else:
        report.print_text()
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
