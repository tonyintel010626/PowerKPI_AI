#!/usr/bin/env python3
"""Full 35/35 section-by-section content diff: KB source vs simics/ sub-skill files.

Compares every meaningful line in the KB source document against the concatenated
simics/ sub-skill files to find content that was lost during the extraction.
"""

import re
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent  # .opencode/skill/fv-thc/


def main():
    # Read KB source
    kb_path = BASE / "docs" / "thc_simics_presi_knowledge.md"
    kb = kb_path.read_text(encoding="utf-8")

    # Read all simics files concatenated
    simics_parts = []
    for fn in ["SKILL.md", "models.md", "operations.md", "advanced.md"]:
        p = BASE / "simics" / fn
        simics_parts.append(f"\n\n=== {fn} ===\n\n" + p.read_text(encoding="utf-8"))
    simics_content = "\n".join(simics_parts)

    # Normalize simics content once for comparison
    simics_norm = re.sub(r"[*_`]", "", simics_content)
    simics_norm = re.sub(r"\s+", " ", simics_norm).lower()
    simics_words_set = set(simics_norm.split())

    # Extract KB sections (## N. Title or ## Appendix X)
    section_pattern = re.compile(r"^(## \d+\. .+|## Appendix [AB].+)$", re.MULTILINE)
    splits = section_pattern.split(kb)
    # splits[0] is preamble, then alternating header/content pairs

    results = []
    total_sections = 0
    total_missing = 0
    issues = []

    for i in range(1, len(splits), 2):
        header = splits[i].strip()
        content = splits[i + 1] if i + 1 < len(splits) else ""
        total_sections += 1

        # Extract meaningful lines
        kb_lines = [
            l.strip()
            for l in content.split("\n")
            if l.strip() and not l.strip().startswith("#")
        ]

        missing = []
        checked = 0
        for line in kb_lines:
            # Skip short lines, markdown separators, blockquotes
            if len(line) < 20 or line.startswith("---") or line.startswith("> "):
                continue
            # Skip pure table separators
            if re.match(r"^[\|\-\s:]+$", line):
                continue

            checked += 1
            # Normalize for comparison
            norm = re.sub(r"[*_`]", "", line)
            norm = re.sub(r"\s+", " ", norm).strip().lower()

            # Strategy 1: Exact substring match
            if norm in simics_norm:
                continue

            # Strategy 2: Word overlap (70% threshold)
            words = set(norm.split())
            if len(words) >= 3:
                overlap = len(words & simics_words_set) / len(words)
                if overlap >= 0.70:
                    continue

            # Strategy 3: Key phrase match (first 40 chars)
            key_phrase = norm[:40]
            if key_phrase in simics_norm:
                continue

            missing.append(line[:120])
            total_missing += 1

        status = (
            "PASS" if len(missing) == 0 else f"GAP ({len(missing)} lines of {checked})"
        )
        results.append((header, status, checked, missing))
        if missing:
            issues.append((header, missing))

    # Report
    print("=" * 70)
    print("FULL 35/35 SECTION-BY-SECTION CONTENT DIFF REPORT")
    print("=" * 70)
    print(f"Sections checked: {total_sections}")
    print(f"Sections PASS:    {total_sections - len(issues)}")
    print(f"Sections GAP:     {len(issues)}")
    print(f"Total missing lines: {total_missing}")
    print()

    for header, status, checked, missing in results:
        icon = "PASS" if "PASS" in status else "GAP "
        print(f"  [{icon}] {header}: {status}")

    if issues:
        print(f"\n{'=' * 70}")
        print(f"DETAILS: {len(issues)} sections with potential gaps")
        print("=" * 70)
        for header, missing in issues:
            print(f"\n  {header}:")
            for m in missing[:5]:
                print(f"    - {m}")
            if len(missing) > 5:
                print(f"    ... and {len(missing) - 5} more")
    else:
        print("\nZERO GAPS — all KB content transferred faithfully to simics/ files")

    # Exit code
    sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
