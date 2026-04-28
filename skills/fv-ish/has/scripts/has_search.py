#!/usr/bin/env python3
"""
has_search.py — ISH HAS Document Search Utility
================================================
Owner : Leem, Yi Jie (yleem) — CVE ISH Validation
Team  : CVE - ISH Validation
Usage : python has_search.py --help
"""

import os
import re
import sys
import json
import argparse
import textwrap
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Optional dependency imports (graceful fallback if not installed)
# ---------------------------------------------------------------------------
BS4_AVAILABLE = False
BeautifulSoup = None  # type: ignore[assignment]
try:
    from bs4 import BeautifulSoup as _BS  # type: ignore[import-untyped]
    BeautifulSoup = _BS
    BS4_AVAILABLE = True
except ImportError:
    pass

PDF_AVAILABLE = False
_pdf_extract: object = None

try:
    from pdfminer.high_level import extract_text as _pdfminer_extract  # type: ignore[import-untyped]
    _pdf_extract = _pdfminer_extract
    PDF_AVAILABLE = True
except ImportError:
    try:
        import importlib
        _pypdf = importlib.import_module("pypdf2")  # type: ignore[assignment]
        def _pypdf_extract(path: str) -> str:
            reader = _pypdf.PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        _pdf_extract = _pypdf_extract
        PDF_AVAILABLE = True
    except ImportError:
        pass

def pdf_extract_text(path: str) -> str:
    if PDF_AVAILABLE and callable(_pdf_extract):
        return _pdf_extract(path)  # type: ignore[call-arg]
    return "[PDF extraction unavailable — install pdfminer: pip install pdfminer.six]\n"

# ---------------------------------------------------------------------------
# Colour helpers — fall back to plain text if colorama not available
# ---------------------------------------------------------------------------
_FORE_GREEN = _FORE_YELLOW = _FORE_CYAN = _FORE_RED = _FORE_MAGENTA = ""
_STYLE_BRIGHT = _STYLE_RESET = ""

try:
    from colorama import init as colorama_init  # type: ignore[import-untyped]
    from colorama import Fore as _Fore, Style as _Style
    colorama_init(autoreset=True)
    _FORE_GREEN   = _Fore.GREEN
    _FORE_YELLOW  = _Fore.YELLOW
    _FORE_CYAN    = _Fore.CYAN
    _FORE_RED     = _Fore.RED
    _FORE_MAGENTA = _Fore.MAGENTA
    _STYLE_BRIGHT = _Style.BRIGHT
    _STYLE_RESET  = _Style.RESET_ALL
except ImportError:
    pass

def c_green(t: object) -> str:    return f"{_FORE_GREEN}{t}{_STYLE_RESET}"
def c_yellow(t: object) -> str:   return f"{_FORE_YELLOW}{t}{_STYLE_RESET}"
def c_cyan(t: object) -> str:     return f"{_FORE_CYAN}{t}{_STYLE_RESET}"
def c_red(t: object) -> str:      return f"{_FORE_RED}{t}{_STYLE_RESET}"
def c_bold(t: object) -> str:     return f"{_STYLE_BRIGHT}{t}{_STYLE_RESET}"
def c_platform(t: object) -> str: return f"{_FORE_MAGENTA}{t}{_STYLE_RESET}"

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).resolve().parent
SKILL_DIR    = SCRIPT_DIR.parent          # .opencode/skill/fv-ish/has/
DOCS_DIR     = SKILL_DIR / "docs"
INDEX_FILE   = SKILL_DIR / ".has_index.json"

PLATFORMS    = ["nvl", "mtl", "lnl", "ptl", "arl"]
FORMATS      = [".html", ".htm", ".pdf", ".md", ".txt"]

TOPIC_KEYWORDS = {
    "register":   ["register", "offset", "bit field", "reset value", "mmio", "bar0"],
    "heci":       ["heci", "hbm", "circular buffer", "doorbell", "h_csr", "me_csr", "ishtp"],
    "dma":        ["dma", "descriptor", "prd", "physical region", "ring buffer", "scatter"],
    "power":      ["d0i2", "d0i3", "d3", "runtime pm", "power state", "ltr", "s0ix", "wake"],
    "sensors":    ["sensor", "accelerometer", "gyroscope", "magnetometer", "als", "proximity",
                   "hid", "report descriptor", "usage page"],
    "firmware":   ["firmware", "fw status", "fw_status", "boot state", "fw load", "ish fw"],
    "interrupt":  ["interrupt", "msi", "pisr", "pimr", "irq", "apic"],
    "platform":   ["device id", "pci id", "bdf", "stepping", "bom", "bios", "sensor bom"],
}

# ---------------------------------------------------------------------------
# Document text extraction
# ---------------------------------------------------------------------------
def extract_text_from_file(filepath: Path) -> str:
    """Extract plain text from HTML, PDF, Markdown, or text files."""
    suffix = filepath.suffix.lower()
    try:
        if suffix in (".html", ".htm"):
            if BS4_AVAILABLE and BeautifulSoup is not None:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    soup = BeautifulSoup(f.read(), "html.parser")
                    return soup.get_text(separator="\n")
            else:
                # Fallback: strip HTML tags with regex
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    raw = f.read()
                return re.sub(r"<[^>]+>", " ", raw)

        elif suffix == ".pdf":
            if PDF_AVAILABLE:
                return pdf_extract_text(str(filepath))
            else:
                return f"[PDF extraction unavailable — install pdfminer: pip install pdfminer.six]\n"

        else:  # .md, .txt, etc.
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

    except Exception as exc:
        return f"[Error reading {filepath.name}: {exc}]"


def extract_tables_from_html(filepath: Path) -> list:
    """Extract HTML tables as list-of-list-of-strings."""
    if not BS4_AVAILABLE or BeautifulSoup is None:
        return []
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f.read(), "html.parser")  # type: ignore[operator]
    tables = []
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables

# ---------------------------------------------------------------------------
# Index management
# ---------------------------------------------------------------------------
def build_index(verbose=True) -> dict:
    """Scan all HAS docs and build a search index."""
    index = {"built_at": datetime.now().isoformat(), "documents": {}}
    for platform in PLATFORMS:
        plat_dir = DOCS_DIR / platform
        if not plat_dir.exists():
            continue
        for fpath in sorted(plat_dir.rglob("*")):
            if fpath.suffix.lower() not in FORMATS:
                continue
            rel = str(fpath.relative_to(DOCS_DIR))
            if verbose:
                print(f"  Indexing: {rel}")
            text = extract_text_from_file(fpath)
            lines = text.splitlines()
            index["documents"][rel] = {
                "platform": platform,
                "path": str(fpath),
                "lines": len(lines),
                "size_kb": round(fpath.stat().st_size / 1024, 1),
            }
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    if verbose:
        n = len(index["documents"])
        print(c_green(f"\n[OK] Index built — {n} document(s) indexed → {INDEX_FILE}"))
    return index


def load_index() -> dict:
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ---------------------------------------------------------------------------
# Search engine
# ---------------------------------------------------------------------------
def search_documents(query: str, platforms: list, context_lines: int = 2) -> list:
    """
    Search for query string across HAS documents.
    Returns list of dicts: {platform, file, line_no, line, context}
    """
    results = []
    pattern = re.compile(re.escape(query), re.IGNORECASE)

    for platform in platforms:
        plat_dir = DOCS_DIR / platform
        if not plat_dir.exists():
            continue
        for fpath in sorted(plat_dir.rglob("*")):
            if fpath.suffix.lower() not in FORMATS:
                continue
            text = extract_text_from_file(fpath)
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if pattern.search(line):
                    start = max(0, i - context_lines)
                    end   = min(len(lines), i + context_lines + 1)
                    ctx   = lines[start:end]
                    results.append({
                        "platform": platform,
                        "file":     fpath.name,
                        "path":     str(fpath),
                        "line_no":  i + 1,
                        "line":     line.strip(),
                        "context":  ctx,
                    })
    return results


def topic_search(topic: str, platforms: list) -> list:
    """Search using topic keyword expansion."""
    keywords = TOPIC_KEYWORDS.get(topic.lower(), [topic])
    all_results = []
    seen = set()
    for kw in keywords:
        for r in search_documents(kw, platforms, context_lines=1):
            key = (r["platform"], r["file"], r["line_no"])
            if key not in seen:
                seen.add(key)
                all_results.append(r)
    return all_results


def extract_register_table(register_name: str, platform: str) -> list:
    """
    Try to extract a register bit-field table for a named register.
    Returns extracted table rows or empty list.
    """
    plat_dir = DOCS_DIR / platform
    tables_found = []
    pattern = re.compile(re.escape(register_name), re.IGNORECASE)

    for fpath in sorted(plat_dir.rglob("*")):
        if fpath.suffix.lower() not in (".html", ".htm"):
            continue
        tables = extract_tables_from_html(fpath)
        # Find tables that contain the register name
        for table in tables:
            flat = " ".join(cell for row in table for cell in row)
            if pattern.search(flat):
                tables_found.append({"file": fpath.name, "table": table})
    return tables_found

# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------
def format_results_terminal(results: list, query: str, max_results: int = 50):
    """Print search results to terminal with colour."""
    if not results:
        print(c_yellow(f"No matches found for: '{query}'"))
        print("Tip: Try querying Co-De Sign at https://chat.co-design.intel.com/chat")
        return

    # Group by platform
    by_platform = {}
    for r in results[:max_results]:
        by_platform.setdefault(r["platform"], []).append(r)

    total = len(results)
    shown = min(total, max_results)
    print(c_bold(f"\n=== HAS Search: '{query}' — {total} match(es), showing {shown} ===\n"))

    for platform, matches in by_platform.items():
        count = len(matches)
        label = platform.upper().ljust(6)
        bar = "█" * min(count, 30)
        print(f"  {c_platform(label)} {bar} {count} match(es)")

    print()
    for r in results[:max_results]:
        print(c_cyan(f"[{r['platform'].upper()}] {r['file']}:{r['line_no']}"))
        for ctx_line in r["context"]:
            highlighted = re.sub(
                f"(?i)({re.escape(query)})",
                lambda m: c_green(m.group(1)),
                ctx_line
            )
            print(f"    {highlighted}")
        print()

    if total > max_results:
        print(c_yellow(f"... {total - max_results} more result(s) not shown. Use --max N to see more."))


def format_results_markdown(results: list, query: str) -> str:
    """Format search results as Markdown."""
    if not results:
        return f"## HAS Search: `{query}`\n\nNo matches found.\n"

    lines = [f"## HAS Search: `{query}`", f"", f"**{len(results)} match(es)**", ""]
    by_platform = {}
    for r in results:
        by_platform.setdefault(r["platform"], []).append(r)

    for platform, matches in by_platform.items():
        lines.append(f"### {platform.upper()}")
        for r in matches:
            lines.append(f"- **{r['file']}** line {r['line_no']}: `{r['line'][:120]}`")
        lines.append("")
    return "\n".join(lines)


def format_table_terminal(table_data: list):
    """Print extracted HTML tables to terminal."""
    for item in table_data:
        print(c_bold(f"\nTable from: {item['file']}"))
        table = item["table"]
        if not table:
            continue
        # Calculate column widths
        col_widths = []
        for col_i in range(max(len(row) for row in table)):
            w = max((len(row[col_i]) if col_i < len(row) else 0) for row in table)
            col_widths.append(min(w, 40))
        sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        for row_i, row in enumerate(table):
            print(sep)
            cells = []
            for col_i, w in enumerate(col_widths):
                cell = row[col_i] if col_i < len(row) else ""
                cells.append(f" {cell[:w]:<{w}} ")
            print("|" + "|".join(cells) + "|")
        print(sep)


def list_documents():
    """List all HAS documents in the docs directory."""
    print(c_bold("\n=== ISH HAS Document Library ===\n"))
    found_any = False
    for platform in PLATFORMS:
        plat_dir = DOCS_DIR / platform
        if not plat_dir.exists():
            continue
        docs = [f for f in sorted(plat_dir.rglob("*")) if f.suffix.lower() in FORMATS]
        label = platform.upper()
        if docs:
            found_any = True
            print(c_platform(f"[{label}]"))
            for d in docs:
                size_kb = d.stat().st_size / 1024
                print(f"  {d.name:<50} {size_kb:>7.1f} KB")
        else:
            print(c_yellow(f"[{label}] — no documents yet (place files in docs/{platform}/)"))
    if not found_any:
        print(c_yellow("\nNo HAS documents found in any platform directory."))
        print("Place your ISH HAS files in:")
        for p in PLATFORMS:
            print(f"  {DOCS_DIR / p}/")

# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------
def export_markdown(results: list, query: str, output_path: "Path | None" = None):
    """Export search results to a markdown file."""
    md = format_results_markdown(results, query)
    if output_path is None:
        safe_q = re.sub(r"[^\w]", "_", query)[:40]
        output_path = SKILL_DIR / f"has_search_{safe_q}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(c_green(f"[OK] Exported to: {output_path}"))


def export_json(results: list, query: str, output_path: "Path | None" = None):
    """Export search results to a JSON file."""
    if output_path is None:
        safe_q = re.sub(r"[^\w]", "_", query)[:40]
        output_path = SKILL_DIR / f"has_search_{safe_q}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"query": query, "results": results}, f, indent=2)
    print(c_green(f"[OK] Exported to: {output_path}"))

# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="has_search.py",
        description="ISH HAS Document Search Utility — CVE ISH Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          # Full-text search in NVL HAS
          python has_search.py "HECI_H_CSR" --platform nvl

          # Topic-based search (expands to related keywords)
          python has_search.py --topic power --platform nvl

          # Extract register bit-field table
          python has_search.py --name "ISH_FW_STATUS" --extract-table --platform nvl

          # Search all platforms and compare
          python has_search.py "DMA descriptor" --platform all --compare

          # Export results to markdown
          python has_search.py "sensor batching" --platform nvl --export-md

          # Build search index
          python has_search.py --build-index

          # List all available HAS documents
          python has_search.py --list-docs
        """)
    )

    p.add_argument("query",         nargs="?",       help="Search query string")
    p.add_argument("--platform",    default="nvl",   help="Platform(s): nvl|mtl|lnl|ptl|arl|all (default: nvl)")
    p.add_argument("--topic",                        help=f"Topic search: {', '.join(TOPIC_KEYWORDS.keys())}")
    p.add_argument("--name",                         help="Register/field name for targeted lookup")
    p.add_argument("--extract-table", action="store_true", help="Extract register bit-field table (HTML only)")
    p.add_argument("--compare",     action="store_true",   help="Compare results across all platforms")
    p.add_argument("--export-md",   action="store_true",   help="Export results to Markdown file")
    p.add_argument("--export-json", action="store_true",   help="Export results to JSON file")
    p.add_argument("--build-index", action="store_true",   help="Build/rebuild the HAS search index")
    p.add_argument("--list-docs",   action="store_true",   help="List all available HAS documents")
    p.add_argument("--max",         type=int, default=50,  help="Max results to display (default: 50)")
    p.add_argument("--context",     type=int, default=2,   help="Context lines around match (default: 2)")
    p.add_argument("--format",      choices=["terminal", "markdown", "json"], default="terminal",
                   help="Output format (default: terminal)")
    return p


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = build_parser()
    args = parser.parse_args()

    # ── Special commands ────────────────────────────────────────────────────
    if args.list_docs:
        list_documents()
        return 0

    if args.build_index:
        print(c_bold("Building HAS search index..."))
        build_index(verbose=True)
        return 0

    # ── Resolve platforms ───────────────────────────────────────────────────
    if args.platform.lower() == "all" or args.compare:
        platforms = PLATFORMS
    else:
        platforms = [p.strip().lower() for p in args.platform.split(",")]
        for p in platforms:
            if p not in PLATFORMS:
                print(c_red(f"Unknown platform: '{p}'. Valid: {', '.join(PLATFORMS)}"))
                return 1

    # ── Table extraction ────────────────────────────────────────────────────
    if args.extract_table:
        name = args.name or args.query
        if not name:
            print(c_red("--extract-table requires --name <register_name> or a positional query"))
            return 1
        print(c_bold(f"Extracting register table: '{name}' on {platforms}"))
        for plat in platforms:
            tables = extract_register_table(name, plat)
            if tables:
                print(c_platform(f"\n[{plat.upper()}]"))
                format_table_terminal(tables)
            else:
                print(c_yellow(f"[{plat.upper()}] No table found for '{name}'"))
        return 0

    # ── Topic search ─────────────────────────────────────────────────────────
    if args.topic:
        if args.topic not in TOPIC_KEYWORDS:
            print(c_yellow(f"Unknown topic '{args.topic}'. Available: {', '.join(TOPIC_KEYWORDS.keys())}"))
        print(c_bold(f"Topic search: '{args.topic}' on {[p.upper() for p in platforms]}"))
        results = topic_search(args.topic, platforms)
        format_results_terminal(results, args.topic, max_results=args.max)
        if args.export_md:
            export_markdown(results, args.topic)
        if args.export_json:
            export_json(results, args.topic)
        return 0

    # ── Full-text search ─────────────────────────────────────────────────────
    query = args.query or args.name
    if not query:
        parser.print_help()
        return 1

    results = search_documents(query, platforms, context_lines=args.context)

    if args.format == "markdown":
        print(format_results_markdown(results, query))
    elif args.format == "json":
        print(json.dumps({"query": query, "results": results}, indent=2))
    else:
        format_results_terminal(results, query, max_results=args.max)

    if args.export_md:
        export_markdown(results, query)
    if args.export_json:
        export_json(results, query)

    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
