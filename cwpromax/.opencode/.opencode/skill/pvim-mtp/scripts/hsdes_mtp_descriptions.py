#!/usr/bin/env python3
"""
Fetch and document 'Description' field from all HSDES MTP hierarchy records.

Walks an HSDES MTP tree (specified via --root), fetches descriptions for every
record (TP, TPF, TCD, TC, TR), and writes a comprehensive local markdown document.

Usage:
    python hsdes_mtp_descriptions.py                          # Default output
    python hsdes_mtp_descriptions.py -o custom_output.md      # Custom output path
    python hsdes_mtp_descriptions.py --include-results        # Include TR layer
    python hsdes_mtp_descriptions.py --html                   # Keep raw HTML (default: strip to plain text)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from _html_utils import HTMLStripper, html_to_text  # noqa: F401 — shared module


# ---------------------------------------------------------------------------
# Tree flattener
# ---------------------------------------------------------------------------
LEVEL_LABELS = {0: "MTP", 1: "TPF", 2: "TCD", 3: "TC", 4: "TR"}


def flatten_tree(node: dict, records: list[dict] | None = None) -> list[dict]:
    """Flatten nested tree into a sorted list of records."""
    if records is None:
        records = []

    level = node.get("level", 0)
    records.append(
        {
            "id": node.get("id", ""),
            "title": node.get("title", ""),
            "status": node.get("status", ""),
            "subject": node.get("subject", ""),
            "owner": node.get("owner", ""),
            "level": level,
            "label": node.get("node_type", LEVEL_LABELS.get(level, f"L{level}")),
            "description": node.get("description", ""),
        }
    )

    for child in node.get("children", []):
        flatten_tree(child, records)

    return records


# ---------------------------------------------------------------------------
# Markdown document generator
# ---------------------------------------------------------------------------
def generate_markdown(records: list[dict], keep_html: bool = False) -> str:
    """Generate comprehensive markdown document from flattened records."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Group by level
    by_level: dict[int, list[dict]] = {}
    for r in records:
        by_level.setdefault(r["level"], []).append(r)

    # Statistics
    total = len(records)
    with_desc = sum(1 for r in records if r["description"].strip())
    without_desc = total - with_desc

    lines = [
        f"# MTP Hierarchy — Full Description Catalog",
        f"",
        f"> **Generated**: {now}",
        f"> **Root**: {records[0]['id'] if records else 'N/A'}",
        f"> **Total Records**: {total}",
        f"> **With Description**: {with_desc}",
        f"> **Without Description**: {without_desc}",
        f"",
        f"---",
        f"",
        f"## Summary by Level",
        f"",
        f"| Level | Label | Count | With Desc | Without Desc |",
        f"|-------|-------|-------|-----------|--------------|",
    ]

    for lvl in sorted(by_level.keys()):
        recs = by_level[lvl]
        label = LEVEL_LABELS.get(lvl, f"L{lvl}")
        wd = sum(1 for r in recs if r["description"].strip())
        wo = len(recs) - wd
        lines.append(f"| L{lvl} | {label} | {len(recs)} | {wd} | {wo} |")

    lines.extend(["", "---", ""])

    # Emit each level section
    for lvl in sorted(by_level.keys()):
        recs = by_level[lvl]
        label = LEVEL_LABELS.get(lvl, f"L{lvl}")
        lines.append(f"## L{lvl} — {label} ({len(recs)} records)")
        lines.append("")

        # Sort by title within level
        for r in sorted(recs, key=lambda x: x["title"]):
            status_badge = (
                "✅"
                if r["status"] == "complete"
                else "❌"
                if r["status"] == "rejected"
                else "⏳"
            )
            lines.append(f"### {status_badge} [{r['label']}] {r['title']}")
            lines.append(f"")
            lines.append(f"| Field | Value |")
            lines.append(f"|-------|-------|")
            lines.append(f"| **ID** | {r['id']} |")
            lines.append(f"| **Status** | {r['status']} |")
            lines.append(f"| **Subject** | {r['subject']} |")
            lines.append(f"| **Owner** | {r['owner']} |")
            lines.append(f"| **Level** | L{r['level']} ({r['label']}) |")
            lines.append(f"")

            desc = r["description"].strip()
            if desc:
                lines.append(f"**Description:**")
                lines.append(f"")
                if keep_html:
                    lines.append(f"```html")
                    lines.append(desc)
                    lines.append(f"```")
                else:
                    plain = html_to_text(desc)
                    # Indent each line for readability
                    for dline in plain.split("\n"):
                        lines.append(f"> {dline}" if dline.strip() else f">")
            else:
                lines.append(f"**Description:** *(none)*")

            lines.append(f"")
            lines.append(f"---")
            lines.append(f"")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Fetch and document HSDES MTP descriptions locally"
    )
    parser.add_argument(
        "--root",
        required=True,
        help="MTP root article HSDES ID (get from your FV-agent definition)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output markdown file path (default: reports/<root>_mtp_descriptions.md)",
    )
    parser.add_argument(
        "--include-results", action="store_true", help="Include TR (Test Result) layer"
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Keep raw HTML in descriptions (default: convert to plain text)",
    )
    args = parser.parse_args()

    # Determine paths
    script_dir = Path(__file__).parent
    reports_dir = script_dir.parent / "reports"
    reports_dir.mkdir(exist_ok=True)

    output_path = (
        Path(args.output)
        if args.output
        else reports_dir / f"{args.root}_mtp_descriptions.md"
    )

    # Step 1: Run tree walker with --include-descriptions
    tree_cmd = [
        sys.executable,
        str(script_dir / "hsdes_mtp_tree.py"),
        "--root",
        args.root,
        "--include-descriptions",
        "--format",
        "json",
    ]
    if args.include_results:
        tree_cmd.append("--include-results")

    print(f"[1/3] Walking MTP tree with descriptions (root={args.root})...")
    result = subprocess.run(tree_cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print(f"ERROR: Tree walker failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    tree_data = json.loads(result.stdout)

    # Step 2: Flatten tree
    print(f"[2/3] Flattening tree and extracting descriptions...")
    records = flatten_tree(tree_data)
    total = len(records)
    with_desc = sum(1 for r in records if r["description"].strip())
    print(f"       {total} records found, {with_desc} with descriptions")

    # Step 3: Generate and write markdown
    print(f"[3/3] Generating markdown document...")
    md = generate_markdown(records, keep_html=args.html)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")
    print(f"       Written to: {output_path}")
    print(f"       Size: {len(md):,} bytes, {md.count(chr(10)):,} lines")

    # Summary
    by_level = {}
    for r in records:
        by_level.setdefault(r["level"], []).append(r)
    print(f"\n{'=' * 60}")
    print(f"DESCRIPTION CATALOG SUMMARY")
    print(f"{'=' * 60}")
    for lvl in sorted(by_level):
        recs = by_level[lvl]
        wd = sum(1 for r in recs if r["description"].strip())
        label = LEVEL_LABELS.get(lvl, f"L{lvl}")
        print(f"  L{lvl} {label:>4}: {len(recs):>4} records, {wd:>4} with description")
    print(f"  {'':>5} Total: {total:>3} records, {with_desc:>4} with description")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
