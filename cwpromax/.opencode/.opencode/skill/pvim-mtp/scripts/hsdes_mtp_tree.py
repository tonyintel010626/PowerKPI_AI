#!/usr/bin/env python3
"""
HSDES MTP Hierarchy Tree Walker

Recursively traverses HSDES PVIM Master Test Plan hierarchies using the
/rest/article/{id}/links endpoint. Works with any FV domain's MTP.

Usage:
    python hsdes_mtp_tree.py --root <MTP_ROOT_ID> --depth 3
    python hsdes_mtp_tree.py --root <MTP_ROOT_ID> --format json --output mtp.json
    python hsdes_mtp_tree.py --root <MTP_ROOT_ID> --stats-only

Requirements:
    pip install requests pysvtools

Author: willychi (William Willy Chin)
Created: 2026-03-29
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import Optional

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from requests_kerberos import HTTPKerberosAuth, OPTIONAL

    HAS_KERBEROS = True
except ImportError:
    HAS_KERBEROS = False

try:
    from pysvtools.hsdes import HSDES

    HAS_PYSVTOOLS = True
except ImportError:
    HAS_PYSVTOOLS = False


# ─── HSDES REST API Configuration ──────────────────────────────────────────

HSDES_API_BASE = "https://hsdes-api.intel.com/rest"
HSDES_BROWSER_BASE = "https://hsdes.intel.com/rest"

# Endpoints discovered 2026-03-29
# ✅ /rest/article/{id}        → 200 OK (article details)
# ✅ /rest/article/{id}/links   → 200 OK (parent-child relationships)
# ✅ /rest/article/{id}/children → 200 OK (requires child_subject + tenant params)
# ❌ /rest/article/{id}/relationship → 404
# ❌ /rest/article/{id}/hierarchy → 404

# MTP Hierarchy Levels (subject types):
#   L0: test_plan           → MTP (Master Test Plan) root
#   L1: test_plan           → TPF (Test Plan Feature)
#   L2: test_case_definition → TCD (Test Case Definition)
#   L3: test_case           → TC (Test Case)
#   L4: test_result         → TR (Test Result)


# ─── Data Classes ──────────────────────────────────────────────────────────


@dataclass
class MTPNode:
    """Represents a single node in the MTP hierarchy."""

    id: int
    title: str = ""
    status: str = ""
    owner: str = ""
    tenant: str = ""
    subject: str = ""  # test_plan, test_case_definition, test_case, test_result
    level: int = 0
    relationship: str = ""  # "root", "parent-child"
    children: list = field(default_factory=list)

    # Optional extended fields
    description: str = ""
    component: str = ""
    release: str = ""

    @property
    def is_rejected(self) -> bool:
        return self.status.lower() in ("rejected", "reject")

    @property
    def is_complete(self) -> bool:
        return self.status.lower() == "complete"

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    @property
    def node_type_label(self) -> str:
        """Human-readable label based on subject type and level."""
        SUBJECT_LABELS = {
            "test_plan": "MTP" if self.level == 0 else "TPF",
            "test_case_definition": "TCD",
            "test_case": "TC",
            "test_result": "TR",
        }
        return SUBJECT_LABELS.get(self.subject, f"L{self.level}")

    def to_dict(self) -> dict:
        """Convert to dict, recursively including children."""
        d = {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "owner": self.owner,
            "subject": self.subject,
            "node_type": self.node_type_label,
            "level": self.level,
        }
        if self.tenant:
            d["tenant"] = self.tenant
        if self.description:
            d["description"] = self.description
        if self.component:
            d["component"] = self.component
        if self.release:
            d["release"] = self.release
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


# ─── Session Management ───────────────────────────────────────────────────


def _create_session() -> requests.Session:
    """Create an authenticated requests session for HSDES REST API.

    Authentication priority:
      1. requests_kerberos (HTTPKerberosAuth) — proven to work on Intel intranet
      2. pysvtools.hsdes session — fallback, may not cover /links endpoint
      3. Unauthenticated — will likely get 401, but allows offline testing
    """
    session = requests.Session()

    # Priority 1: Kerberos auth (proven working for /rest/article/{id}/links)
    if HAS_KERBEROS:
        session.auth = HTTPKerberosAuth(mutual_authentication=OPTIONAL)
    elif HAS_PYSVTOOLS:
        # Priority 2: Try pysvtools session (works for /rest/article/{id} only)
        try:
            from pysvtools.hsdes.rest.client import Hsdes

            h = Hsdes()
            session = h._session
        except Exception:
            pass  # Fall through to unauthenticated session

    session.headers.update(
        {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    )
    return session


# ─── API Functions ─────────────────────────────────────────────────────────


def get_article(
    session: requests.Session, article_id: int, base_url: str = HSDES_API_BASE
) -> Optional[dict]:
    """Fetch article details by HSDES ID.

    Args:
        session: Authenticated requests session
        article_id: HSDES article ID
        base_url: API base URL

    Returns:
        Article data dict or None on failure
    """
    url = f"{base_url}/article/{article_id}"
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "data" in data and len(data["data"]) > 0:
            return data["data"][0]
    except requests.exceptions.RequestException as e:
        print(f"  [WARN] Failed to fetch article {article_id}: {e}", file=sys.stderr)
    return None


def get_children(
    session: requests.Session, article_id: int, base_url: str = HSDES_API_BASE
) -> list:
    """Get child articles linked to the given article via parent-child relationship.

    Uses the /rest/article/{id}/links endpoint and filters for
    relationship == 'parent-child' (meaning this article is the parent).

    Args:
        session: Authenticated requests session
        article_id: HSDES article ID of the parent
        base_url: API base URL

    Returns:
        List of child dicts with id, title, status, owner, tenant, subject
    """
    url = f"{base_url}/article/{article_id}/links"
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        children = []
        for item in data.get("responses", []):
            if item.get("relationship") == "parent-child":
                children.append(
                    {
                        "id": item.get("id"),
                        "title": item.get("title", ""),
                        "status": item.get("status", ""),
                        "owner": item.get("owner", ""),
                        "tenant": item.get("tenant", ""),
                        "subject": item.get("subject", ""),
                    }
                )
        return children
    except requests.exceptions.RequestException as e:
        print(f"  [WARN] Failed to fetch links for {article_id}: {e}", file=sys.stderr)
    return []


def get_test_results(
    session: requests.Session,
    article_id: int,
    tenant: str = "sighting_central",
    base_url: str = HSDES_API_BASE,
) -> list:
    """Get test result children of a test case using the /children endpoint.

    Unlike get_children() which uses /links, this uses /children with
    child_subject=test_result to find TRs linked to a TC.

    Args:
        session: Authenticated requests session
        article_id: HSDES article ID of the parent TC
        tenant: HSDES tenant (default: sighting_central)
        base_url: API base URL

    Returns:
        List of test result dicts with id, title, status, owner, tenant, subject
    """
    url = f"{base_url}/article/{article_id}/children"
    params = {"child_subject": "test_result", "tenant": tenant}
    try:
        resp = session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("data", []):
            results.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title", ""),
                    "status": item.get("status", ""),
                    "owner": item.get("owner", ""),
                    "tenant": item.get("tenant", tenant),
                    "subject": "test_result",
                }
            )
        return results
    except requests.exceptions.RequestException as e:
        print(
            f"  [WARN] Failed to fetch test results for {article_id}: {e}",
            file=sys.stderr,
        )
    return []


# ─── Node Type Labels ─────────────────────────────────────────────────────

# Maps HSDES subject + level to human-readable MTP hierarchy label
LEVEL_LABELS = {
    0: "MTP",  # Master Test Plan (root)
    1: "TPF",  # Test Plan Feature
    2: "TCD",  # Test Case Definition
    3: "TC",  # Test Case
    4: "TR",  # Test Result
}

SUBJECT_LABELS = {
    "test_plan": "Test Plan",
    "test_case_definition": "Test Case Definition",
    "test_case": "Test Case",
    "test_result": "Test Result",
}


def node_type_label(node) -> str:
    """Return human-readable label for a node based on subject or level."""
    if node.subject in SUBJECT_LABELS:
        return SUBJECT_LABELS[node.subject]
    return LEVEL_LABELS.get(node.level, f"L{node.level}")


# ─── Tree Walker ───────────────────────────────────────────────────────────


class MTPTreeWalker:
    """Recursively walks an HSDES MTP hierarchy."""

    def __init__(
        self,
        base_url: str = HSDES_API_BASE,
        max_parallel: int = 8,
        verbose: bool = False,
    ):
        self.base_url = base_url
        self.max_parallel = max_parallel
        self.verbose = verbose
        self.session = _create_session()
        self._fetch_count = 0

    def build_tree(
        self,
        root_id: int,
        max_depth: int = 4,
        fetch_details: bool = False,
        include_results: bool = False,
    ) -> MTPNode:
        """Build complete MTP hierarchy tree from root.

        Args:
            root_id: HSDES ID of the root MTP article
            max_depth: Maximum recursion depth (0 = root only)
            fetch_details: Whether to fetch full article details (slower)
            include_results: Whether to fetch Test Results (TRs) under Test Cases

        Returns:
            MTPNode tree with all descendants
        """
        self._include_results = include_results

        if self.verbose:
            print(f"[INFO] Fetching root article {root_id}...", file=sys.stderr)

        # Fetch root article details
        root_data = get_article(self.session, root_id, self.base_url)
        if not root_data:
            print(f"[ERROR] Could not fetch root article {root_id}", file=sys.stderr)
            return MTPNode(id=root_id, title="(fetch failed)", level=0)

        root = MTPNode(
            id=root_data.get("id", root_id),
            title=root_data.get("title", ""),
            status=root_data.get("status", ""),
            owner=root_data.get("owner", ""),
            tenant=root_data.get("tenant", ""),
            subject=root_data.get("subject", ""),
            level=0,
            relationship="root",
            description=root_data.get("description", "") if fetch_details else "",
            component=root_data.get("component", ""),
            release=root_data.get("release", ""),
        )
        self._fetch_count = 1

        if max_depth > 0:
            self._expand_children(root, max_depth, fetch_details)

        if self.verbose:
            print(
                f"[INFO] Tree complete. {self._fetch_count} API calls made.",
                file=sys.stderr,
            )

        return root

    def _expand_children(
        self, parent: MTPNode, remaining_depth: int, fetch_details: bool
    ):
        """Recursively expand children of a node using parallel API calls.

        When include_results is True and we reach leaf TCs (test_case nodes
        with no parent-child children), also queries /children endpoint for
        test_result records.
        """
        if remaining_depth <= 0:
            return

        # Fetch children via /links (parent-child relationship)
        children_data = get_children(self.session, parent.id, self.base_url)
        self._fetch_count += 1

        # If no parent-child children and include_results is enabled,
        # try /children endpoint for test_results (TR layer)
        if not children_data and self._include_results:
            tr_data = get_test_results(
                self.session,
                parent.id,
                tenant="sighting_central",
                base_url=self.base_url,
            )
            if tr_data:
                self._fetch_count += 1
                if self.verbose:
                    print(
                        f"  [L{parent.level + 1}] {parent.title} → {len(tr_data)} test results (TR)",
                        file=sys.stderr,
                    )
                for tr in tr_data:
                    node = MTPNode(
                        id=tr["id"],
                        title=tr["title"],
                        status=tr["status"],
                        owner=tr.get("owner", ""),
                        tenant=tr.get("tenant", ""),
                        subject="test_result",
                        level=parent.level + 1,
                        relationship="parent-child",
                    )
                    parent.children.append(node)
                parent.children.sort(key=lambda n: n.id)
            return

        if not children_data:
            return

        if self.verbose:
            print(
                f"  [L{parent.level + 1}] {parent.title} → {len(children_data)} children",
                file=sys.stderr,
            )

        # Create child nodes
        child_nodes = []
        for cd in children_data:
            node = MTPNode(
                id=cd["id"],
                title=cd["title"],
                status=cd["status"],
                owner=cd["owner"],
                tenant=cd.get("tenant", ""),
                subject=cd.get("subject", ""),
                level=parent.level + 1,
                relationship="parent-child",
            )
            child_nodes.append(node)

        # Fetch details for children if requested (parallel)
        if fetch_details:
            with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
                futures = {
                    executor.submit(get_article, self.session, n.id, self.base_url): n
                    for n in child_nodes
                }
                for future in as_completed(futures):
                    node = futures[future]
                    self._fetch_count += 1
                    try:
                        data = future.result()
                        if data:
                            node.description = data.get("description", "")
                            node.component = data.get("component", "")
                            node.release = data.get("release", "")
                    except Exception:
                        pass

        parent.children = sorted(child_nodes, key=lambda n: n.id)

        # Recursively expand grandchildren (parallel at each level)
        if remaining_depth > 1:
            with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
                futures = {
                    executor.submit(
                        self._expand_children, node, remaining_depth - 1, fetch_details
                    ): node
                    for node in child_nodes
                }
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        node = futures[future]
                        if self.verbose:
                            print(
                                f"  [WARN] Error expanding {node.id}: {e}",
                                file=sys.stderr,
                            )

    # ─── Statistics ────────────────────────────────────────────────────

    def get_stats(self, root: MTPNode) -> dict:
        """Compute summary statistics for the MTP tree.

        Returns:
            Dict with total, complete, rejected, open, by_level, by_status,
            by_subject counts
        """
        stats = {
            "total": 0,
            "complete": 0,
            "rejected": 0,
            "open": 0,
            "future": 0,
            "other": 0,
            "leaves": 0,
            "max_depth": 0,
            "by_level": {},
            "by_status": {},
            "by_owner": {},
            "by_subject": {},
            "test_results": 0,
            "test_cases": 0,
            "test_case_definitions": 0,
            "test_plans": 0,
        }

        def _walk(node):
            stats["total"] += 1
            status = node.status.lower()

            if status == "complete":
                stats["complete"] += 1
            elif status in ("rejected", "reject"):
                stats["rejected"] += 1
            elif status == "open":
                stats["open"] += 1
            elif status == "future":
                stats["future"] += 1
            else:
                stats["other"] += 1

            # By level
            level_key = f"level_{node.level}"
            stats["by_level"][level_key] = stats["by_level"].get(level_key, 0) + 1

            # By status
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # By owner
            if node.owner:
                stats["by_owner"][node.owner] = stats["by_owner"].get(node.owner, 0) + 1

            # By subject (node type tracking)
            subj = node.subject or "unknown"
            stats["by_subject"][subj] = stats["by_subject"].get(subj, 0) + 1
            if subj == "test_result":
                stats["test_results"] += 1
            elif subj == "test_case":
                stats["test_cases"] += 1
            elif subj == "test_case_definition":
                stats["test_case_definitions"] += 1
            elif subj == "test_plan":
                stats["test_plans"] += 1

            # Leaf tracking
            if node.is_leaf:
                stats["leaves"] += 1

            # Max depth
            if node.level > stats["max_depth"]:
                stats["max_depth"] = node.level

            for child in node.children:
                _walk(child)

        _walk(root)
        return stats

    # ─── Output Formatters ─────────────────────────────────────────────

    def print_tree(
        self,
        root: MTPNode,
        show_id: bool = True,
        show_status: bool = True,
        indent: str = "  ",
    ):
        """Print tree in ASCII art format to stdout."""

        def _print_node(node, prefix="", is_last=True):
            connector = "└── " if is_last else "├── "
            if node.level == 0:
                connector = ""
                prefix = ""

            # Node type label based on subject
            type_label = {
                "test_plan": "MTP" if node.level == 0 else "TPF",
                "test_case_definition": "TCD",
                "test_case": "TC",
                "test_result": "TR",
            }.get(node.subject, "")
            type_prefix = f"[{type_label}] " if type_label else ""

            # Build display line
            parts = []
            if show_id:
                parts.append(f"[{node.id}]")
            parts.append(f"{type_prefix}{node.title or '(untitled)'}")
            if show_status:
                status_icon = {
                    "complete": "✅",
                    "rejected": "❌",
                    "open": "⏳",
                    "future": "🔮",
                }.get(node.status.lower(), "❓")
                parts.append(f"({node.status}) {status_icon}")

            line = f"{prefix}{connector}{' '.join(parts)}"
            print(line)

            # Print children
            child_prefix = prefix + ("    " if is_last else "│   ")
            if node.level == 0:
                child_prefix = ""
            for i, child in enumerate(node.children):
                _print_node(child, child_prefix, i == len(node.children) - 1)

        _print_node(root)

    def to_json(self, root: MTPNode, indent: int = 2) -> str:
        """Serialize tree to JSON string."""
        return json.dumps(root.to_dict(), indent=indent)

    def to_markdown(
        self, root: MTPNode, include_ids: bool = True, include_links: bool = True
    ) -> str:
        """Generate markdown documentation from tree."""
        lines = []
        stats = self.get_stats(root)

        # Header
        lines.append(f"# {root.title}")
        lines.append("")
        lines.append(f"> **HSDES ID**: `{root.id}`  ")
        lines.append(f"> **Status**: {root.status}  ")
        lines.append(f"> **Owner**: {root.owner}  ")
        lines.append(f"> **Total Records**: {stats['total']}  ")
        lines.append(f"> **Generated**: {time.strftime('%Y-%m-%d %H:%M')}  ")
        lines.append("")

        # Summary stats
        lines.append("## Summary Statistics")
        lines.append("")
        lines.append(f"| Metric | Count |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Records | {stats['total']} |")
        lines.append(f"| Complete | {stats['complete']} |")
        lines.append(f"| Rejected | {stats['rejected']} |")
        lines.append(f"| Open | {stats['open']} |")
        lines.append(f"| Leaf Nodes | {stats['leaves']} |")
        lines.append(f"| Max Depth | {stats['max_depth']} |")
        lines.append("")

        # By-subject breakdown
        if stats.get("by_subject"):
            lines.append("### By Node Type")
            lines.append("")
            subject_labels = {
                "test_plan": "MTP / TPF",
                "test_case_definition": "TCD (Test Case Definition)",
                "test_case": "TC (Test Case)",
                "test_result": "TR (Test Result)",
            }
            lines.append("| Node Type | Count |")
            lines.append("|-----------|-------|")
            for subj, count in sorted(stats["by_subject"].items()):
                label = subject_labels.get(subj, subj)
                lines.append(f"| {label} | {count} |")
            lines.append("")

        # Hierarchy
        lines.append("## Full Hierarchy")
        lines.append("")

        def _write_node(node, depth=0):
            if node.level == 0:
                # Skip root in hierarchy (already in header)
                for child in node.children:
                    _write_node(child, depth)
                return

            indent = "  " * (node.level - 1)
            status_icon = {
                "complete": "✅",
                "rejected": "❌",
                "open": "⏳",
                "future": "🔮",
            }.get(node.status.lower(), "❓")

            id_part = f"`{node.id}` " if include_ids else ""
            link_part = ""
            if include_links:
                link_part = f" [↗](https://hsdes.intel.com/resource/{node.id})"

            line = f"{indent}- {status_icon} {id_part}**{node.title}** ({node.status}){link_part}"
            lines.append(line)

            for child in node.children:
                _write_node(child, depth + 1)

        _write_node(root)
        lines.append("")

        return "\n".join(lines)

    def to_csv(self, root: MTPNode) -> str:
        """Export tree as flat CSV."""
        rows = ["level,id,subject,title,status,owner,parent_id"]

        def _walk(node, parent_id=0):
            row = f'{node.level},{node.id},{node.subject},"{node.title}",{node.status},{node.owner},{parent_id}'
            rows.append(row)
            for child in node.children:
                _walk(child, node.id)

        _walk(root)
        return "\n".join(rows)


# ─── CLI Entry Point ───────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="HSDES PVIM Master Test Plan Hierarchy Walker",
        epilog="Example: python hsdes_mtp_tree.py --root <MTP_ROOT_ID> --depth 3",
    )
    parser.add_argument(
        "--root", type=int, required=True, help="Root MTP article HSDES ID"
    )
    parser.add_argument(
        "--depth", type=int, default=4, help="Max recursion depth (default: 4)"
    )
    parser.add_argument(
        "--format",
        choices=["tree", "json", "markdown", "csv"],
        default="tree",
        help="Output format (default: tree)",
    )
    parser.add_argument(
        "--output", type=str, default=None, help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--stats-only", action="store_true", help="Print summary statistics only"
    )
    parser.add_argument(
        "--parallel", type=int, default=8, help="Max parallel API requests (default: 8)"
    )
    parser.add_argument(
        "--include-descriptions",
        action="store_true",
        help="Fetch full article descriptions (slower)",
    )
    parser.add_argument(
        "--include-rejected",
        action="store_true",
        help="Include rejected items in output",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=HSDES_API_BASE,
        help=f"HSDES API base URL (default: {HSDES_API_BASE})",
    )
    parser.add_argument(
        "--include-results",
        action="store_true",
        help="Include test_result (TR) children under test_case (TC) nodes",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show progress during traversal"
    )

    args = parser.parse_args()

    # Build tree
    walker = MTPTreeWalker(
        base_url=args.base_url,
        max_parallel=args.parallel,
        verbose=args.verbose,
    )

    print(
        f"[INFO] Walking MTP hierarchy from root {args.root} (depth={args.depth})...",
        file=sys.stderr,
    )
    start_time = time.time()

    tree = walker.build_tree(
        root_id=args.root,
        max_depth=args.depth,
        fetch_details=args.include_descriptions,
        include_results=args.include_results,
    )

    elapsed = time.time() - start_time
    stats = walker.get_stats(tree)
    print(
        f"[INFO] Done. {stats['total']} records in {elapsed:.1f}s "
        f"({walker._fetch_count} API calls)",
        file=sys.stderr,
    )

    # Stats-only mode
    if args.stats_only:
        print(json.dumps(stats, indent=2))
        return

    # Format output
    if args.format == "tree":
        output = None  # print_tree writes directly to stdout
        walker.print_tree(tree)
    elif args.format == "json":
        output = walker.to_json(tree)
    elif args.format == "markdown":
        output = walker.to_markdown(tree)
    elif args.format == "csv":
        output = walker.to_csv(tree)

    # Write output
    if output:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"[INFO] Output written to {args.output}", file=sys.stderr)
        else:
            print(output)


if __name__ == "__main__":
    main()
