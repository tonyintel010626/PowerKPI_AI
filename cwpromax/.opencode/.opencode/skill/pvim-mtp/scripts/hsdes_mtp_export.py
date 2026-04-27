#!/usr/bin/env python3
"""
HSDES MTP Export — Export PVIM Master Test Plan hierarchy to various formats.

Wraps MTPTreeWalker from hsdes_mtp_tree.py with enhanced export capabilities:
- Markdown with collapsible sections (GitHub-flavored)
- JSON with full metadata
- CSV for spreadsheet import
- Summary report with statistics

Usage:
    python hsdes_mtp_export.py --root <MTP_ROOT_ID> --format markdown --output mtp_hierarchy.md
    python hsdes_mtp_export.py --root <MTP_ROOT_ID> --format json --output mtp_hierarchy.json
    python hsdes_mtp_export.py --root <MTP_ROOT_ID> --format csv --output mtp_hierarchy.csv
    python hsdes_mtp_export.py --root <MTP_ROOT_ID> --format report --output mtp_report.md

Requires:
    - requests_kerberos (for Intel SSO authentication)
    - hsdes_mtp_tree.py (in same directory)
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure sibling module is importable
sys.path.insert(0, str(Path(__file__).parent))

from hsdes_mtp_tree import MTPTreeWalker, MTPNode


def _count_by_status(node: MTPNode) -> dict:
    """Recursively count nodes by status."""
    counts = {}
    status = (node.status or "unknown").lower()
    counts[status] = counts.get(status, 0) + 1
    for child in node.children:
        child_counts = _count_by_status(child)
        for k, v in child_counts.items():
            counts[k] = counts.get(k, 0) + v
    return counts


def _count_by_depth(node: MTPNode, depth: int = 0) -> dict:
    """Count nodes at each depth level."""
    counts = {depth: 1}
    for child in node.children:
        child_counts = _count_by_depth(child, depth + 1)
        for k, v in child_counts.items():
            counts[k] = counts.get(k, 0) + v
    return counts


def _count_by_owner(node: MTPNode) -> dict:
    """Count nodes by owner."""
    counts = {}
    owner = node.owner or "unknown"
    counts[owner] = counts.get(owner, 0) + 1
    for child in node.children:
        child_counts = _count_by_owner(child)
        for k, v in child_counts.items():
            counts[k] = counts.get(k, 0) + v
    return counts


def _collect_rejected(node: MTPNode, path: str = "") -> list:
    """Collect all rejected nodes with their hierarchy path."""
    results = []
    current_path = f"{path} > {node.title}" if path else node.title
    if node.status and node.status.lower() == "rejected":
        results.append({"id": node.id, "title": node.title, "path": current_path})
    for child in node.children:
        results.extend(_collect_rejected(child, current_path))
    return results


def _count_by_subject(node: MTPNode) -> dict:
    """Count nodes by HSDES subject type (test_plan, test_case_definition, test_case, test_result)."""
    counts = {}
    subject = (node.subject or "unknown").lower()
    counts[subject] = counts.get(subject, 0) + 1
    for child in node.children:
        child_counts = _count_by_subject(child)
        for k, v in child_counts.items():
            counts[k] = counts.get(k, 0) + v
    return counts


def _collect_leaf_nodes(node: MTPNode) -> list:
    """Collect all leaf nodes (no children)."""
    if not node.children:
        return [
            {
                "id": node.id,
                "title": node.title,
                "status": node.status,
                "owner": node.owner,
            }
        ]
    results = []
    for child in node.children:
        results.extend(_collect_leaf_nodes(child))
    return results


def generate_report(root: MTPNode, walker: MTPTreeWalker) -> str:
    """Generate an enhanced markdown report with statistics and analysis."""
    stats = walker.get_stats(root)
    status_counts = _count_by_status(root)
    depth_counts = _count_by_depth(root)
    owner_counts = _count_by_owner(root)
    rejected = _collect_rejected(root)
    leaves = _collect_leaf_nodes(root)

    lines = []
    lines.append(f"# MTP Report: {root.title}")
    lines.append(f"")
    lines.append(f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> HSDES ID: [{root.id}](https://hsdes.intel.com/resource/{root.id})")
    lines.append(f"> Owner: {root.owner}")
    lines.append(f"")

    # Summary stats
    lines.append(f"## Summary Statistics")
    lines.append(f"")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| **Total Records** | **{stats.get('total', 0)}** |")
    lines.append(f"| Leaf Test Cases | {stats.get('leaves', 0)} |")
    lines.append(f"| Max Depth | {stats.get('max_depth', 'N/A')} |")
    lines.append(f"")

    # Status breakdown
    lines.append(f"### Status Breakdown")
    lines.append(f"")
    lines.append(f"| Status | Count | Percentage |")
    lines.append(f"|--------|-------|-----------|")
    total = sum(status_counts.values())
    for status in sorted(status_counts.keys()):
        count = status_counts[status]
        pct = (count / total * 100) if total > 0 else 0
        icon = {"complete": "✅", "rejected": "❌", "open": "🔵", "future": "🔮"}.get(
            status, "⬜"
        )
        lines.append(f"| {icon} {status} | {count} | {pct:.1f}% |")
    lines.append(f"")

    # Depth breakdown
    lines.append(f"### Hierarchy Depth")
    lines.append(f"")
    lines.append(f"| Level | Label | Count |")
    lines.append(f"|-------|-------|-------|")
    level_labels = {
        0: "MTP (Master Test Plan)",
        1: "TPF (Test Plan Feature)",
        2: "TCD (Test Case Definition)",
        3: "TC (Test Case)",
        4: "TR (Test Result)",
    }
    for depth in sorted(depth_counts.keys()):
        label = level_labels.get(depth, f"Level {depth}")
        lines.append(f"| L{depth} | {label} | {depth_counts[depth]} |")
    lines.append(f"")

    # Node type breakdown
    subject_counts = _count_by_subject(root)
    subject_labels = {
        "test_plan": "MTP / TPF",
        "test_case_definition": "TCD (Test Case Definition)",
        "test_case": "TC (Test Case)",
        "test_result": "TR (Test Result)",
    }
    if subject_counts:
        lines.append(f"### Node Type Breakdown")
        lines.append(f"")
        lines.append(f"| Node Type | Subject | Count |")
        lines.append(f"|-----------|---------|-------|")
        for subj in ["test_plan", "test_case_definition", "test_case", "test_result"]:
            if subj in subject_counts:
                label = subject_labels.get(subj, subj)
                lines.append(f"| {label} | `{subj}` | {subject_counts[subj]} |")
        # Any other subjects
        for subj in sorted(subject_counts.keys()):
            if subj not in subject_labels:
                lines.append(f"| {subj} | `{subj}` | {subject_counts[subj]} |")
        lines.append(f"")

    # Owner breakdown
    if len(owner_counts) > 1:
        lines.append(f"### Owner Distribution")
        lines.append(f"")
        lines.append(f"| Owner | Count |")
        lines.append(f"|-------|-------|")
        for owner in sorted(
            owner_counts.keys(), key=lambda k: owner_counts[k], reverse=True
        ):
            lines.append(f"| {owner} | {owner_counts[owner]} |")
        lines.append(f"")

    # Rejected items
    if rejected:
        lines.append(f"## Rejected Items ({len(rejected)})")
        lines.append(f"")
        lines.append(f"| HSDES ID | Title | Hierarchy Path |")
        lines.append(f"|----------|-------|---------------|")
        for item in rejected:
            lines.append(
                f"| [{item['id']}](https://hsdes.intel.com/resource/{item['id']}) | {item['title'][:60]} | {item['path'][:80]} |"
            )
        lines.append(f"")

    # TPF summary
    lines.append(f"## Test Plan Features (Level 1)")
    lines.append(f"")
    lines.append(
        f"| # | TPF Title | HSDES ID | Status | Direct Children | Leaf Tests |"
    )
    lines.append(f"|---|-----------|----------|--------|----------------|------------|")
    for i, child in enumerate(root.children, 1):
        child_leaf_count = len(_collect_leaf_nodes(child))
        icon = "✅" if child.status and child.status.lower() == "complete" else "❌"
        lines.append(
            f"| {i} | {child.title[:60]} | [{child.id}](https://hsdes.intel.com/resource/{child.id}) | {icon} {child.status} | {len(child.children)} | {child_leaf_count} |"
        )
    lines.append(f"")

    # Full tree
    lines.append(f"## Full Hierarchy Tree")
    lines.append(f"")
    lines.append(f"```")
    lines.append(
        walker.to_markdown(root, include_ids=True, include_links=False)
        .replace("###", "   ")
        .replace("##", "  ")
        .replace("#", "")
    )
    lines.append(f"```")
    lines.append(f"")

    # Leaf test cases
    active_leaves = [l for l in leaves if l.get("status", "").lower() != "rejected"]
    lines.append(
        f"## Leaf Test Cases ({len(active_leaves)} active, {len(leaves) - len(active_leaves)} rejected)"
    )
    lines.append(f"")
    lines.append(f"<details>")
    lines.append(
        f"<summary>Click to expand full test case list ({len(leaves)} total)</summary>"
    )
    lines.append(f"")
    lines.append(f"| # | HSDES ID | Title | Status | Owner |")
    lines.append(f"|---|----------|-------|--------|-------|")
    for i, leaf in enumerate(leaves, 1):
        icon = "✅" if leaf.get("status", "").lower() == "complete" else "❌"
        lines.append(
            f"| {i} | [{leaf['id']}](https://hsdes.intel.com/resource/{leaf['id']}) | {leaf['title'][:70]} | {icon} {leaf.get('status', '')} | {leaf.get('owner', '')} |"
        )
    lines.append(f"")
    lines.append(f"</details>")
    lines.append(f"")

    # HSDES API access info
    lines.append(f"## API Access Reference")
    lines.append(f"")
    lines.append(f"```python")
    lines.append(f"# Reproduce this report programmatically:")
    lines.append(f"from hsdes_mtp_tree import MTPTreeWalker")
    lines.append(f"walker = MTPTreeWalker()")
    lines.append(f"root = walker.build_tree({root.id}, max_depth=3)")
    lines.append(f"print(walker.to_markdown(root))")
    lines.append(f"```")
    lines.append(f"")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Export HSDES PVIM Master Test Plan hierarchy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export MTP to markdown (replace <ROOT_ID> with your domain's MTP root)
  python hsdes_mtp_export.py --root <ROOT_ID> --format markdown -o mtp_export.md

  # Export to JSON for programmatic use
  python hsdes_mtp_export.py --root <ROOT_ID> --format json -o mtp_export.json

  # Generate full report with statistics
  python hsdes_mtp_export.py --root <ROOT_ID> --format report -o mtp_report.md

  # Export to CSV for spreadsheet
  python hsdes_mtp_export.py --root <ROOT_ID> --format csv -o mtp_export.csv
        """,
    )
    parser.add_argument("--root", type=int, required=True, help="Root MTP HSDES ID")
    parser.add_argument(
        "--depth", type=int, default=4, help="Max traversal depth (default: 4)"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json", "csv", "report"],
        default="report",
        help="Export format (default: report)",
    )
    parser.add_argument("-o", "--output", help="Output file path (default: stdout)")
    parser.add_argument(
        "--base-url",
        default="https://hsdes-api.intel.com/rest",
        help="HSDES API base URL",
    )
    parser.add_argument(
        "--parallel", type=int, default=8, help="Max parallel API requests"
    )
    parser.add_argument(
        "--include-results",
        action="store_true",
        help="Include Test Results (TRs) under Test Cases via /children endpoint",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Build tree
    walker = MTPTreeWalker(
        base_url=args.base_url, max_parallel=args.parallel, verbose=args.verbose
    )

    if args.verbose:
        print(
            f"Fetching MTP tree for root ID {args.root} (depth={args.depth}, include_results={args.include_results})...",
            file=sys.stderr,
        )

    root = walker.build_tree(
        args.root, max_depth=args.depth, include_results=args.include_results
    )

    if root is None:
        print(f"ERROR: Failed to fetch root article {args.root}", file=sys.stderr)
        sys.exit(1)

    # Generate output
    if args.format == "markdown":
        output = walker.to_markdown(root, include_ids=True, include_links=True)
    elif args.format == "json":
        output = walker.to_json(root, indent=2)
    elif args.format == "csv":
        output = walker.to_csv(root)
    elif args.format == "report":
        output = generate_report(root, walker)
    else:
        output = walker.to_markdown(root)

    # Write output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        stats = walker.get_stats(root)
        print(
            f"Exported {stats.get('total', 0)} records to {args.output} ({args.format})",
            file=sys.stderr,
        )
    else:
        print(output)


if __name__ == "__main__":
    main()
