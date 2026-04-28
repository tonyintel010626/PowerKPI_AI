#!/usr/bin/env python3
"""
NVU Simics Content Diff Tool
===============================
Compares reference documentation content against the NVU simics/ sub-skill
and other skill files to identify coverage gaps.

Ported from: fv-thc/tools/thc_simics_diff.py (127 lines)
Adapted for: NVU domain — compares any reference doc sections against skill files

When NVU Simics model becomes available, this tool will compare:
  - Simics model register definitions vs registers/SKILL.md
  - Simics DMA descriptors vs dma/SKILL.md
  - Simics power states vs power/SKILL.md
  - Simics device config vs platform/SKILL.md

Currently operates in scaffold mode since NVU Simics model doesn't exist yet.

Usage:
    python nvu_simics_diff.py                          # Check simics placeholder status
    python nvu_simics_diff.py --source docs/ref.md     # Diff reference doc against skills
    python nvu_simics_diff.py --json                   # JSON output for CI
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SKILL_ROOT = Path(__file__).parent.parent
SIMICS_SKILL = SKILL_ROOT / "simics" / "SKILL.md"

# Skill files to compare against (in priority order)
COMPARISON_TARGETS = {
    "registers": SKILL_ROOT / "registers" / "SKILL.md",
    "dma": SKILL_ROOT / "dma" / "SKILL.md",
    "power": SKILL_ROOT / "power" / "SKILL.md",
    "platform": SKILL_ROOT / "platform" / "SKILL.md",
    "driver": SKILL_ROOT / "driver" / "SKILL.md",
    "firmware": SKILL_ROOT / "firmware" / "SKILL.md",
    "inference": SKILL_ROOT / "inference" / "SKILL.md",
    "camera": SKILL_ROOT / "camera" / "SKILL.md",
    "debug": SKILL_ROOT / "debug" / "SKILL.md",
    "bios": SKILL_ROOT / "bios" / "SKILL.md",
}

# Key terms that should appear in a Simics model reference
SIMICS_EXPECTED_TERMS = [
    "register",
    "MMIO",
    "BAR",
    "PCI",
    "config space",
    "DMA",
    "interrupt",
    "MSI",
    "power state",
    "D0i0",
    "D0i1",
    "D0i2",
    "clock gating",
    "SRAM",
    "VPX2",
    "NPX6",
    "IOSF",
    "strap",
    "fuse",
    "reset",
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("nvu_simics_diff")
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
# Text Normalization
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, strip markdown, collapse whitespace."""
    # Remove markdown formatting
    text = re.sub(r"[#*`\[\]()_|>-]", " ", text)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def extract_word_set(text: str) -> Set[str]:
    """Extract unique words from normalized text."""
    normalized = normalize_text(text)
    return set(w for w in normalized.split() if len(w) > 2)


def extract_sections(content: str) -> List[Dict[str, str]]:
    """Extract ## N. numbered sections from markdown content."""
    sections = []
    # Match ## 1. Title or ## Section Title patterns
    pattern = r"^##\s+(?:\d+\.\s+)?(.+?)$"
    lines = content.split("\n")
    current_title = None
    current_body = []

    for line in lines:
        match = re.match(pattern, line, re.MULTILINE)
        if match:
            if current_title:
                sections.append(
                    {
                        "title": current_title,
                        "body": "\n".join(current_body),
                    }
                )
            current_title = match.group(1).strip()
            current_body = []
        elif current_title:
            current_body.append(line)

    if current_title:
        sections.append(
            {
                "title": current_title,
                "body": "\n".join(current_body),
            }
        )

    return sections


# ---------------------------------------------------------------------------
# Diff Engine
# ---------------------------------------------------------------------------


def diff_section_against_skills(
    section: Dict[str, str],
    skill_contents: Dict[str, str],
) -> Dict[str, Any]:
    """
    Compare a source section against all skill file contents.
    Uses 3-strategy matching:
      1. Exact substring match (section body found verbatim in skill)
      2. Word overlap (>= 70% of source words found in skill)
      3. Key phrase match (first 40 chars of normalized section found)
    """
    title = section["title"]
    body = section["body"]
    if not body.strip():
        return {
            "section": title,
            "status": "EMPTY",
            "match_skill": None,
            "coverage": 0.0,
        }

    source_words = extract_word_set(body)
    if not source_words:
        return {
            "section": title,
            "status": "EMPTY",
            "match_skill": None,
            "coverage": 0.0,
        }

    normalized_body = normalize_text(body)
    key_phrase = normalized_body[:40]

    best_match = None
    best_coverage = 0.0
    best_strategy = None

    for skill_name, skill_content in skill_contents.items():
        skill_normalized = normalize_text(skill_content)
        skill_words = extract_word_set(skill_content)

        # Strategy 1: Exact substring
        if normalized_body[:100] in skill_normalized:
            return {
                "section": title,
                "status": "PASS",
                "match_skill": skill_name,
                "coverage": 1.0,
                "strategy": "exact_substring",
            }

        # Strategy 2: Word overlap
        if source_words:
            overlap = source_words & skill_words
            coverage = len(overlap) / len(source_words)
            if coverage > best_coverage:
                best_coverage = coverage
                best_match = skill_name
                best_strategy = "word_overlap"

        # Strategy 3: Key phrase
        if key_phrase and key_phrase in skill_normalized:
            if best_coverage < 0.7:
                best_coverage = 0.7
                best_match = skill_name
                best_strategy = "key_phrase"

    threshold = 0.70
    status = "PASS" if best_coverage >= threshold else "GAP"

    result = {
        "section": title,
        "status": status,
        "match_skill": best_match,
        "coverage": round(best_coverage, 3),
        "strategy": best_strategy,
    }

    if status == "GAP":
        # Find missing terms
        if best_match and source_words:
            skill_words = extract_word_set(skill_contents[best_match])
            missing = source_words - skill_words
            # Filter to significant words (>4 chars)
            significant_missing = sorted(w for w in missing if len(w) > 4)[:10]
            result["missing_terms"] = significant_missing

    return result


# ---------------------------------------------------------------------------
# Scaffold Mode (No Simics model yet)
# ---------------------------------------------------------------------------


def run_scaffold_checks() -> List[dict]:
    """
    Run checks for scaffold mode — verify simics placeholder exists and
    skill files contain Simics-relevant content.
    """
    results = []

    # Check 1: Simics SKILL.md exists
    exists = SIMICS_SKILL.exists()
    results.append(
        {
            "label": "Simics sub-skill exists",
            "ok": exists,
            "path": str(SIMICS_SKILL),
        }
    )
    log.info(f"  [{'PASS' if exists else 'FAIL'}] simics/SKILL.md exists")

    if exists:
        content = SIMICS_SKILL.read_text(encoding="utf-8", errors="replace")
        # Check it's a placeholder
        is_placeholder = (
            "PLACEHOLDER" in content.upper() or "placeholder" in content.lower()
        )
        results.append(
            {
                "label": "Simics sub-skill is placeholder",
                "ok": True,  # Expected state
                "is_placeholder": is_placeholder,
                "severity": "info",
            }
        )
        log.info(f"  [INFO] Placeholder status: {'yes' if is_placeholder else 'no'}")

    # Check 2: Key Simics-relevant terms in skill files
    log.info("\n--- Simics Term Coverage in Skill Files ---")
    all_content = ""
    for name, path in COMPARISON_TARGETS.items():
        if path.exists():
            all_content += path.read_text(encoding="utf-8", errors="replace") + "\n"

    for term in SIMICS_EXPECTED_TERMS:
        found = term.lower() in all_content.lower()
        results.append(
            {
                "label": f"Simics-relevant term: '{term}'",
                "ok": found,
            }
        )
        status = "PASS" if found else "GAP"
        log.info(f"  [{status}] '{term}' found in skill files")

    # Check 3: Cross-references to simics from other skills
    log.info("\n--- Simics Cross-References ---")
    xref_count = 0
    for name, path in COMPARISON_TARGETS.items():
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="replace")
            if "simics" in content.lower():
                xref_count += 1

    results.append(
        {
            "label": f"Skills referencing 'simics': {xref_count}/{len(COMPARISON_TARGETS)}",
            "ok": True,  # INFO — simics is new, xrefs will grow
            "severity": "info",
            "count": xref_count,
        }
    )
    log.info(f"  [INFO] {xref_count} skill files reference 'simics'")

    return results


# ---------------------------------------------------------------------------
# Source Diff Mode
# ---------------------------------------------------------------------------


def run_source_diff(source_path: str) -> List[dict]:
    """
    Compare a reference document against all NVU skill files.
    Extracts sections from the source and checks coverage in skills.
    """
    results = []
    source = Path(source_path)

    if not source.exists():
        results.append(
            {
                "label": f"Source file: {source_path}",
                "ok": False,
                "error": f"File not found: {source_path}",
            }
        )
        return results

    content = source.read_text(encoding="utf-8", errors="replace")
    sections = extract_sections(content)

    if not sections:
        results.append(
            {
                "label": "Section extraction",
                "ok": False,
                "error": f"No ## sections found in {source_path}",
            }
        )
        return results

    log.info(f"  Extracted {len(sections)} sections from {source.name}")

    # Load all skill contents
    skill_contents = {}
    for name, path in COMPARISON_TARGETS.items():
        if path.exists():
            skill_contents[name] = path.read_text(encoding="utf-8", errors="replace")

    # Also include simics skill
    if SIMICS_SKILL.exists():
        skill_contents["simics"] = SIMICS_SKILL.read_text(
            encoding="utf-8", errors="replace"
        )

    # Diff each section
    pass_count = 0
    gap_count = 0
    for section in sections:
        diff = diff_section_against_skills(section, skill_contents)
        ok = diff["status"] in ("PASS", "EMPTY")
        results.append(
            {
                "label": f"Section: {section['title'][:50]}",
                "ok": ok,
                **diff,
            }
        )
        status = diff["status"]
        skill = diff.get("match_skill", "—")
        coverage = diff.get("coverage", 0)
        log.info(f"  [{status}] {section['title'][:50]} → {skill} ({coverage:.0%})")
        if ok:
            pass_count += 1
        else:
            gap_count += 1
            if "missing_terms" in diff:
                log.info(f"         Missing: {diff['missing_terms'][:5]}")

    log.info(
        f"\n  Summary: {pass_count} PASS / {gap_count} GAP across {len(sections)} sections"
    )

    return results


# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------


def run_all(source: Optional[str] = None) -> dict:
    """Run all checks and return structured results."""
    start = time.time()
    results = []

    # Always run scaffold checks
    log.info("=== Simics Scaffold Checks ===")
    scaffold = run_scaffold_checks()
    results.extend(scaffold)

    # Run source diff if provided
    if source:
        log.info(f"\n=== Source Diff: {source} ===")
        diff = run_source_diff(source)
        results.extend(diff)

    elapsed = time.time() - start
    total_pass = sum(1 for r in results if r.get("ok"))
    total_fail = sum(
        1 for r in results if not r.get("ok") and r.get("severity") != "info"
    )
    total_info = sum(
        1 for r in results if not r.get("ok") and r.get("severity") == "info"
    )

    summary = {
        "total_pass": total_pass,
        "total_fail": total_fail,
        "total_info": total_info,
        "total_checks": len(results),
        "elapsed_seconds": round(elapsed, 2),
        "exit_code": 0 if total_fail == 0 else 1,
        "mode": "source_diff" if source else "scaffold",
    }

    log.info(f"\n{'=' * 60}")
    log.info(
        f"Simics Diff: {total_pass} PASS / {total_fail} FAIL / {total_info} INFO in {elapsed:.1f}s"
    )
    log.info(f"{'=' * 60}")

    return {"results": results, "summary": summary}


def main():
    parser = argparse.ArgumentParser(description="NVU Simics Content Diff Tool")
    parser.add_argument(
        "--source", type=str, help="Reference document to diff against skills"
    )
    parser.add_argument("--json", action="store_true", help="JSON output for CI")
    parser.add_argument("--verbose", action="store_true", help="Detailed output")
    args = parser.parse_args()

    if args.json:
        log.setLevel(logging.WARNING)
    if args.verbose:
        log.setLevel(logging.DEBUG)

    results = run_all(source=args.source)

    if args.json:
        print(json.dumps(results, indent=2, default=str))

    sys.exit(results["summary"]["exit_code"])


if __name__ == "__main__":
    main()
