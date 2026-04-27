#!/usr/bin/env python3
"""
THC FV Wiki Cross-Check — Verifies THC skill files against Intel Confluence wiki pages.

Reads THC-relevant Confluence wiki pages (BKMs, known issues, BOM configs) and
cross-checks key facts against the THC FV skill tree. Flags drift between wiki
content and documented knowledge.

Owner: Chin, William Willy (willychi)
Version: 1.0
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Bootstrap: add tools/ to path so we can import thc_self_common
# ---------------------------------------------------------------------------
TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

try:
    from thc_self_common import (
        Finding,
        Report,
        find_repo_root,
        load_config,
        resolve_path,
        get_skill_path,
        read_skill,
        setup_logging,
    )
except ImportError:
    # Fallback: minimal stubs if thc_self_common is not available
    class Finding:
        def __init__(
            self, check, target, status, message, severity="info", details=None
        ):
            self.check = check
            self.target = target
            self.status = status
            self.message = message
            self.severity = severity
            self.details = details or {}

        def to_dict(self):
            return vars(self)

    class Report:
        def __init__(self, name, version="1.0"):
            self.name = name
            self.version = version
            self.findings = []
            self.timestamp = datetime.now().isoformat()

        def add(self, finding):
            self.findings.append(finding)

        def to_dict(self):
            return {
                "name": self.name,
                "version": self.version,
                "timestamp": self.timestamp,
                "findings": [f.to_dict() for f in self.findings],
                "summary": self._summary(),
            }

        def _summary(self):
            s = {}
            for f in self.findings:
                s[f.status] = s.get(f.status, 0) + 1
            return s

        def to_json(self):
            return json.dumps(self.to_dict(), indent=2)

        def to_text(self):
            lines = [
                f"=== {self.name} v{self.version} ===",
                f"Time: {self.timestamp}",
                "",
            ]
            for f in self.findings:
                lines.append(
                    f"[{f.status.upper()}] {f.check}: {f.message} (target={f.target})"
                )
            lines.append("")
            lines.append(f"Summary: {self._summary()}")
            return "\n".join(lines)

        def save(self, path):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(self.to_json(), encoding="utf-8")

    def find_repo_root():
        return str(TOOLS_DIR.parent.parent.parent.parent)

    def load_config():
        cfg_path = TOOLS_DIR / "self_improvement_config.json"
        if cfg_path.exists():
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        return {}

    def resolve_path(rel):
        return str(Path(find_repo_root()) / rel)

    def get_skill_path(name):
        return str(
            Path(find_repo_root())
            / ".opencode"
            / "skill"
            / "fv-thc"
            / name
            / "SKILL.md"
        )

    def read_skill(name):
        p = Path(get_skill_path(name))
        if p.exists():
            return p.read_text(encoding="utf-8")
        return ""

    def setup_logging(verbose=False):
        logging.basicConfig(
            level=logging.DEBUG if verbose else logging.INFO,
            format="%(levelname)s: %(message)s",
        )


logger = logging.getLogger("thc_self_wiki")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VERSION = "1.0"
SECUREWIKI_SCRIPT = str(
    Path(find_repo_root()) / ".opencode" / "skill" / "securewiki" / "securewiki.py"
)

# Default user — on lab machines os.getlogin() returns system account
DEFAULT_USER = "willychi"

# Cache directory for wiki pages (avoids redundant fetches within a run)
CACHE_DIR = TOOLS_DIR / ".wiki_cache"

# ---------------------------------------------------------------------------
# Wiki Page Definitions
# ---------------------------------------------------------------------------
# Each page has:
#   id:          Confluence page ID
#   title:       Human-readable title
#   space:       Confluence space key
#   priority:    1=critical, 2=important, 3=nice-to-have
#   skill_targets: which skill files this page is expected to inform
#   assertions:  list of (search_pattern, target_skill, description)
#     - search_pattern: regex to find in WIKI content (if found, cross-check target_skill)
#     - target_skill:   skill name whose SKILL.md should contain related info
#     - description:    what we're checking

WIKI_PAGES: List[Dict[str, Any]] = [
    {
        "id": "4200761602",
        "title": "WCL THC BKM",
        "space": "FVCommon",
        "priority": 1,
        "skill_targets": ["platform", "debug", "hidspi", "hidi2c"],
        "assertions": [
            # Platform data cross-checks
            (
                r"(?i)WCL.*device\s*id",
                "platform",
                "WCL Device ID mentioned in wiki should be in platform skill",
            ),
            (
                r"(?i)WCL.*BDF",
                "platform",
                "WCL BDF assignment should be in platform skill",
            ),
            (
                r"(?i)WCL.*BIOS.*knob",
                "platform",
                "WCL BIOS knob settings should be in platform skill",
            ),
            # Debug cross-checks
            (
                r"(?i)workaround|WA\b",
                "debug",
                "WCL workarounds should be tracked in debug skill",
            ),
            (
                r"(?i)HSDES|sighting|1[56]\d{9}",
                "debug",
                "WCL sightings should be in debug skill sighting DB",
            ),
            # Protocol cross-checks
            (
                r"(?i)SPI.*clock|SPI.*freq",
                "hidspi",
                "SPI clock/freq info should be in HIDSPI skill",
            ),
            (
                r"(?i)I2C.*address|I2C.*speed",
                "hidi2c",
                "I2C config info should be in HIDI2C skill",
            ),
        ],
    },
    {
        "id": "3466824139",
        "title": "THC SPI",
        "space": "FVCommon",
        "priority": 1,
        "skill_targets": ["hidspi", "registers", "dma"],
        "assertions": [
            (
                r"(?i)SPI.*mode|single|dual|quad",
                "hidspi",
                "SPI IO modes should be in HIDSPI skill",
            ),
            (
                r"(?i)opcode|read\s*opcode|write\s*opcode",
                "hidspi",
                "SPI opcodes should be in HIDSPI skill",
            ),
            (
                r"(?i)ICR|input\s*cause",
                "hidspi",
                "ICR/Input Cause Register info should be in HIDSPI skill",
            ),
            (r"(?i)DMA|PRD|ring", "dma", "DMA/PRD info should be in DMA skill"),
            (
                r"(?i)register|offset|0x[0-9A-Fa-f]+",
                "registers",
                "Register offsets should be in registers skill",
            ),
            (
                r"(?i)clock.*125|base.*clock|half.*divider",
                "hidspi",
                "SPI base clock info should be in HIDSPI skill",
            ),
        ],
    },
    {
        "id": "4606212223",
        "title": "THC WCL Issues",
        "space": "FVCommon",
        "priority": 1,
        "skill_targets": ["debug", "platform"],
        "assertions": [
            (
                r"(?i)HSDES|1[56]\d{9}",
                "debug",
                "WCL issue sightings should be in debug skill",
            ),
            (
                r"(?i)workaround|WA\b|fix",
                "debug",
                "WCL issue workarounds should be in debug skill",
            ),
            (
                r"(?i)BIOS|firmware|IFWI",
                "platform",
                "BIOS/firmware issues should be in platform skill",
            ),
            (
                r"(?i)D3|D0i2|power|LTR|S0ix",
                "power",
                "Power-related issues should be in power skill",
            ),
            (
                r"(?i)WoT|wake.on.touch",
                "wot",
                "Wake-on-Touch issues should be in WoT skill",
            ),
        ],
    },
    {
        "id": "1355098344",
        "title": "Post Si BKM THC",
        "space": "FVCommon",
        "priority": 2,
        "skill_targets": ["debug", "platform", "driver"],
        "assertions": [
            (
                r"(?i)debug.*procedure|triage|debug.*flow",
                "debug",
                "Debug procedures should be in debug skill",
            ),
            (
                r"(?i)BKM|best.*known.*method",
                "debug",
                "THC BKMs should be in debug skill",
            ),
            (
                r"(?i)driver.*version|INF|install",
                "driver",
                "Driver version info should be in driver skill",
            ),
            (
                r"(?i)PythonSV|namednode|pch_thc",
                "debug",
                "PythonSV debug commands should be in debug skill",
            ),
            (
                r"(?i)enumeration|PCI.*config|BAR",
                "platform",
                "Enum/PCI config info should be in platform skill",
            ),
        ],
    },
    {
        "id": "4501129290",
        "title": "BOM52 I2C Touch Panel",
        "space": "FVCommon",
        "priority": 2,
        "skill_targets": ["hidi2c", "platform"],
        "assertions": [
            (
                r"(?i)I2C.*address|slave.*addr|0x[0-9A-Fa-f]{1,2}\b",
                "hidi2c",
                "I2C device address should be in HIDI2C skill",
            ),
            (
                r"(?i)ELAN|WACOM|ALPS|Goodix|Synaptics",
                "platform",
                "Touch vendor info should be in platform BOM matrix",
            ),
            (
                r"(?i)VID.*PID|vendor.*id|product.*id",
                "platform",
                "Device VID/PID should be in platform BOM matrix",
            ),
            (
                r"(?i)report.*descriptor|HID.*desc",
                "hidi2c",
                "HID descriptor info should be in HIDI2C skill",
            ),
            (
                r"(?i)interrupt|GPIO|IRQ",
                "hidi2c",
                "Interrupt config should be in HIDI2C skill",
            ),
        ],
    },
]

# ---------------------------------------------------------------------------
# Wiki Access Functions
# ---------------------------------------------------------------------------


def _find_securewiki() -> str:
    """Locate the securewiki.py script."""
    if os.path.exists(SECUREWIKI_SCRIPT):
        return SECUREWIKI_SCRIPT
    # Fallback: search relative to repo root
    alt = os.path.join(
        find_repo_root(), ".opencode", "skill", "securewiki", "securewiki.py"
    )
    if os.path.exists(alt):
        return alt
    raise FileNotFoundError(
        f"securewiki.py not found at {SECUREWIKI_SCRIPT} or {alt}. "
        "Ensure the securewiki skill is installed."
    )


def read_wiki_page(
    page_id: str, user: str = DEFAULT_USER, use_cache: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Read a Confluence wiki page via securewiki.py.

    Returns dict with keys: id, title, space, version, url, body_text, body_length
    Returns None on error.
    """
    # Check cache first
    if use_cache:
        cache_file = CACHE_DIR / f"{page_id}.json"
        if cache_file.exists():
            age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
            if age_hours < 24:  # Cache valid for 24 hours
                logger.debug(f"Cache hit for page {page_id} (age: {age_hours:.1f}h)")
                return json.loads(cache_file.read_text(encoding="utf-8"))

    try:
        script = _find_securewiki()
        cmd = [sys.executable, script, "read", page_id, "--user", user, "--json"]
        logger.info(f"Reading wiki page {page_id}...")
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, encoding="utf-8"
        )
        if result.returncode != 0:
            logger.error(
                f"securewiki read failed for {page_id}: {result.stderr.strip()}"
            )
            return None

        # securewiki.py may emit [INFO] lines to stdout before JSON —
        # strip everything before the first '{' to isolate the JSON payload.
        raw = result.stdout
        json_start = raw.find("{")
        if json_start < 0:
            logger.error(
                f"No JSON object found in securewiki output for page {page_id}"
            )
            return None
        data = json.loads(raw[json_start:])

        # Cache the result
        if use_cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file = CACHE_DIR / f"{page_id}.json"
            cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.debug(f"Cached page {page_id}")

        return data

    except subprocess.TimeoutExpired:
        logger.error(f"Timeout reading wiki page {page_id}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from securewiki for page {page_id}: {e}")
        return None
    except FileNotFoundError as e:
        logger.error(str(e))
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading page {page_id}: {e}")
        return None


def search_wiki(
    query: str, spaces: str = "FVCommon", user: str = DEFAULT_USER, limit: int = 10
) -> Optional[Dict[str, Any]]:
    """
    Search Confluence wiki via securewiki.py.

    Returns dict with keys: query, cql, total, returned, results
    Returns None on error.
    """
    try:
        script = _find_securewiki()
        cmd = [
            sys.executable,
            script,
            "search",
            query,
            "--spaces",
            spaces,
            "--limit",
            str(limit),
            "--user",
            user,
            "--json",
        ]
        logger.info(f"Searching wiki for '{query}' in {spaces}...")
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, encoding="utf-8"
        )
        if result.returncode != 0:
            logger.error(f"securewiki search failed: {result.stderr.strip()}")
            return None
        # Strip non-JSON lines (e.g. [INFO] from securewiki.py)
        raw = result.stdout
        brace = raw.find("{")
        if brace > 0:
            raw = raw[brace:]
        return json.loads(raw)

    except subprocess.TimeoutExpired:
        logger.error(f"Timeout searching wiki for '{query}'")
        return None
    except Exception as e:
        logger.error(f"Unexpected error searching wiki: {e}")
        return None


# ---------------------------------------------------------------------------
# Cross-Check Logic
# ---------------------------------------------------------------------------


def check_assertion(
    wiki_content: str,
    search_pattern: str,
    target_skill: str,
    description: str,
    page_title: str,
) -> Finding:
    """
    Check a single assertion: if search_pattern matches in wiki_content,
    verify that related content exists in the target skill file.

    Returns a Finding with status PASS, WARN, or INFO.
    """
    # Step 1: Check if the pattern exists in the wiki page
    wiki_matches = re.findall(search_pattern, wiki_content, re.IGNORECASE)
    if not wiki_matches:
        # Pattern not found in wiki — assertion is not applicable
        return Finding(
            check=f"wiki-xref-{target_skill}",
            target=f"wiki:{page_title}",
            status="SKIP",
            message=f"Pattern not found in wiki page: {description}",
            severity="info",
            details={
                "pattern": search_pattern,
                "target_skill": target_skill,
                "wiki_page": page_title,
            },
        )

    # Step 2: Pattern found in wiki — read the target skill file
    skill_content = read_skill(target_skill)
    if not skill_content:
        return Finding(
            check=f"wiki-xref-{target_skill}",
            target=target_skill,
            status="WARN",
            message=f"Cannot read skill '{target_skill}' to cross-check: {description}",
            severity="warning",
            details={
                "pattern": search_pattern,
                "wiki_matches_count": len(wiki_matches),
                "wiki_page": page_title,
            },
        )

    # Step 3: Extract concrete values from wiki matches for deeper cross-check
    # Look for specific values: hex numbers, device IDs, HSDES IDs, vendor names
    concrete_values = _extract_concrete_values(
        wiki_content, wiki_matches, search_pattern
    )

    # Step 4: Check if skill has coverage for the matched topic
    missing_values = []
    found_values = []
    for val in concrete_values:
        if val.lower() in skill_content.lower():
            found_values.append(val)
        else:
            missing_values.append(val)

    if concrete_values and missing_values:
        return Finding(
            check=f"wiki-xref-{target_skill}",
            target=target_skill,
            status="WARN",
            message=f"Wiki has values not found in skill: {description}",
            severity="warning",
            details={
                "wiki_page": page_title,
                "found_in_skill": found_values[:5],
                "missing_from_skill": missing_values[:10],
                "total_wiki_matches": len(wiki_matches),
            },
        )

    if concrete_values and not missing_values:
        return Finding(
            check=f"wiki-xref-{target_skill}",
            target=target_skill,
            status="PASS",
            message=f"Wiki content verified in skill: {description}",
            severity="info",
            details={
                "wiki_page": page_title,
                "verified_values": found_values[:5],
                "total_wiki_matches": len(wiki_matches),
            },
        )

    # No concrete values extracted — just check topic coverage
    # Use key terms from the pattern as a loose check
    topic_terms = _pattern_to_topic_terms(search_pattern)
    topic_found = any(t.lower() in skill_content.lower() for t in topic_terms)

    if topic_found:
        return Finding(
            check=f"wiki-xref-{target_skill}",
            target=target_skill,
            status="PASS",
            message=f"Topic covered in skill: {description}",
            severity="info",
            details={
                "wiki_page": page_title,
                "topic_terms": topic_terms,
                "total_wiki_matches": len(wiki_matches),
            },
        )
    else:
        return Finding(
            check=f"wiki-xref-{target_skill}",
            target=target_skill,
            status="WARN",
            message=f"Wiki topic not found in skill: {description}",
            severity="warning",
            details={
                "wiki_page": page_title,
                "topic_terms": topic_terms,
                "total_wiki_matches": len(wiki_matches),
            },
        )


def _extract_concrete_values(full_text: str, matches: list, pattern: str) -> List[str]:
    """
    Extract concrete, cross-checkable values from wiki content near the match.
    Looks for: hex values, HSDES IDs, vendor names, register names, BDF strings.
    """
    values = set()

    # Hex values (device IDs, register offsets, addresses)
    hex_vals = re.findall(r"\b0x[0-9A-Fa-f]{2,8}\b", full_text)
    for h in hex_vals[:20]:  # Cap to avoid noise
        values.add(h)

    # HSDES sighting IDs (10+ digit numbers starting with 1)
    hsdes_ids = re.findall(r"\b1[456]\d{8,10}\b", full_text)
    for h in hsdes_ids[:10]:
        values.add(h)

    # Vendor names
    vendors = re.findall(
        r"\b(?:ELAN|WACOM|ALPS|Goodix|Synaptics|Atmel|Hid-i2c|QuickSPI|QuickI2C)\b",
        full_text,
        re.IGNORECASE,
    )
    for v in vendors:
        values.add(v)

    # BDF patterns (Bus:Dev.Fun)
    bdfs = re.findall(r"\b\d+:\d+\.\d+\b", full_text)
    for b in bdfs[:5]:
        values.add(b)

    return list(values)


def _pattern_to_topic_terms(pattern: str) -> List[str]:
    """Extract human-readable topic terms from a regex pattern."""
    # Remove regex metacharacters and extract words
    cleaned = re.sub(r"[\\()?|.*+\[\]{}^$]", " ", pattern)
    cleaned = re.sub(r"(?i)\bi\b", "", cleaned)  # remove lone 'i' from (?i)
    words = [w.strip() for w in cleaned.split() if len(w.strip()) > 2]
    return list(set(words))


# ---------------------------------------------------------------------------
# Freshness Check
# ---------------------------------------------------------------------------


def check_freshness(
    page_data: Dict[str, Any],
    page_config: Dict[str, Any],
    last_checked: Optional[str] = None,
) -> Finding:
    """
    Check if a wiki page has been updated since our last check.
    """
    page_title = page_config.get("title", page_config["id"])
    page_version = page_data.get("version", "unknown")

    # Try to detect last-modified from page metadata
    body_length = page_data.get("body_length", 0)

    return Finding(
        check="wiki-freshness",
        target=f"wiki:{page_title}",
        status="INFO",
        message=f"Wiki page version={page_version}, body_length={body_length}",
        severity="info",
        details={
            "page_id": page_config["id"],
            "page_title": page_title,
            "version": page_version,
            "body_length": body_length,
            "last_checked": last_checked or "never",
        },
    )


# ---------------------------------------------------------------------------
# Main Check Runners
# ---------------------------------------------------------------------------


def run_live_check(
    pages: Optional[List[Dict]] = None, user: str = DEFAULT_USER, use_cache: bool = True
) -> Report:
    """
    Run live wiki cross-check: read wiki pages and cross-check against skill files.
    """
    report = Report("THC FV Wiki Cross-Check", VERSION)
    pages = pages or WIKI_PAGES

    total_assertions = 0
    total_pass = 0
    total_warn = 0
    total_skip = 0
    total_error = 0

    for page_cfg in pages:
        page_id = page_cfg["id"]
        page_title = page_cfg.get("title", page_id)
        logger.info(f"\n--- Checking wiki page: {page_title} (ID: {page_id}) ---")

        # Read the wiki page
        page_data = read_wiki_page(page_id, user=user, use_cache=use_cache)
        if page_data is None:
            report.add(
                Finding(
                    check="wiki-read",
                    target=f"wiki:{page_title}",
                    status="ERROR",
                    message=f"Failed to read wiki page {page_id} ({page_title})",
                    severity="error",
                    details={"page_id": page_id, "page_title": page_title},
                )
            )
            total_error += 1
            continue

        wiki_content = page_data.get("body_text", "")
        if not wiki_content:
            report.add(
                Finding(
                    check="wiki-read",
                    target=f"wiki:{page_title}",
                    status="WARN",
                    message=f"Wiki page {page_id} has empty body",
                    severity="warning",
                    details={"page_id": page_id},
                )
            )
            total_warn += 1
            continue

        # Freshness check
        report.add(check_freshness(page_data, page_cfg))

        # Run assertions
        for pattern, target_skill, desc in page_cfg.get("assertions", []):
            finding = check_assertion(
                wiki_content, pattern, target_skill, desc, page_title
            )
            report.add(finding)
            total_assertions += 1

            if finding.status == "PASS":
                total_pass += 1
            elif finding.status == "WARN":
                total_warn += 1
            elif finding.status == "SKIP":
                total_skip += 1
            elif finding.status == "ERROR":
                total_error += 1

        logger.info(f"  Page {page_title}: assertions checked")

    # Summary finding
    report.add(
        Finding(
            check="wiki-summary",
            target="all",
            status="PASS" if total_warn == 0 and total_error == 0 else "WARN",
            message=(
                f"Wiki cross-check complete: {total_assertions} assertions, "
                f"{total_pass} PASS, {total_warn} WARN, {total_skip} SKIP, {total_error} ERROR"
            ),
            severity="info",
            details={
                "total_assertions": total_assertions,
                "pass": total_pass,
                "warn": total_warn,
                "skip": total_skip,
                "error": total_error,
                "pages_checked": len(pages),
            },
        )
    )

    return report


def run_offline_check(pages: Optional[List[Dict]] = None) -> Report:
    """
    Run offline assertion check: verify that skill files have content
    corresponding to known wiki topics (without reading wiki).
    Uses cached wiki content if available, otherwise just checks skill coverage.
    """
    report = Report("THC FV Wiki Cross-Check (Offline)", VERSION)
    pages = pages or WIKI_PAGES

    total_checks = 0
    total_pass = 0
    total_warn = 0

    for page_cfg in pages:
        page_title = page_cfg.get("title", page_cfg["id"])
        logger.info(f"\n--- Offline check for: {page_title} ---")

        # Check if we have cached content
        cache_file = CACHE_DIR / f"{page_cfg['id']}.json"
        wiki_content = None
        if cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                wiki_content = cached.get("body_text", "")
                logger.info(f"  Using cached content for {page_title}")
            except Exception:
                pass

        # For each target skill, verify it exists and has relevant content
        for target_skill in page_cfg.get("skill_targets", []):
            skill_content = read_skill(target_skill)
            if not skill_content:
                report.add(
                    Finding(
                        check=f"wiki-offline-{target_skill}",
                        target=target_skill,
                        status="WARN",
                        message=f"Skill '{target_skill}' not readable for wiki cross-check",
                        severity="warning",
                        details={"wiki_page": page_title},
                    )
                )
                total_warn += 1
                total_checks += 1
                continue

            # Check assertions if we have wiki content
            if wiki_content:
                for pattern, tgt_skill, desc in page_cfg.get("assertions", []):
                    if tgt_skill != target_skill:
                        continue
                    finding = check_assertion(
                        wiki_content, pattern, target_skill, desc, page_title
                    )
                    report.add(finding)
                    total_checks += 1
                    if finding.status == "PASS":
                        total_pass += 1
                    elif finding.status == "WARN":
                        total_warn += 1
            else:
                # No wiki content — just verify skill file has non-trivial content
                if len(skill_content) > 500:
                    report.add(
                        Finding(
                            check=f"wiki-offline-{target_skill}",
                            target=target_skill,
                            status="PASS",
                            message=f"Skill '{target_skill}' has content ({len(skill_content)} chars)",
                            severity="info",
                            details={
                                "wiki_page": page_title,
                                "skill_length": len(skill_content),
                            },
                        )
                    )
                    total_pass += 1
                else:
                    report.add(
                        Finding(
                            check=f"wiki-offline-{target_skill}",
                            target=target_skill,
                            status="WARN",
                            message=f"Skill '{target_skill}' has thin content ({len(skill_content)} chars)",
                            severity="warning",
                            details={
                                "wiki_page": page_title,
                                "skill_length": len(skill_content),
                            },
                        )
                    )
                    total_warn += 1
                total_checks += 1

    report.add(
        Finding(
            check="wiki-offline-summary",
            target="all",
            status="PASS" if total_warn == 0 else "WARN",
            message=f"Offline check: {total_checks} checks, {total_pass} PASS, {total_warn} WARN",
            severity="info",
            details={"total": total_checks, "pass": total_pass, "warn": total_warn},
        )
    )

    return report


def run_loop(
    n: int = 1, user: str = DEFAULT_USER, use_cache: bool = True
) -> List[Report]:
    """
    Run wiki cross-check N times (for stress/reliability testing).
    """
    reports = []
    for i in range(n):
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Wiki Cross-Check Iteration {i + 1}/{n}")
        logger.info(f"{'=' * 60}")
        report = run_live_check(user=user, use_cache=use_cache)
        reports.append(report)

        # Count pass/warn/error
        summary = report.to_dict().get("summary", {})
        logger.info(f"Iteration {i + 1} summary: {summary}")

    return reports


def clear_cache():
    """Clear the wiki page cache."""
    if CACHE_DIR.exists():
        import shutil

        shutil.rmtree(CACHE_DIR)
        logger.info(f"Cache cleared: {CACHE_DIR}")
    else:
        logger.info("No cache to clear")


# ---------------------------------------------------------------------------
# Pipeline Integration
# ---------------------------------------------------------------------------


def run_wiki_check(
    config: Optional[Dict] = None,
    live: bool = True,
    user: str = DEFAULT_USER,
    use_cache: bool = True,
) -> Tuple[Report, List[Finding]]:
    """
    Entry point for integration with thc_self_improve.py pipeline.

    Returns (report, list_of_actionable_findings)
    where actionable_findings are WARN/ERROR findings that may need attention.
    """
    cfg = config or load_config()

    # Get wiki config from self_improvement_config.json if available
    wiki_cfg = cfg.get("wiki_check", {})
    wiki_user = wiki_cfg.get("user", user)
    wiki_pages = wiki_cfg.get("pages", None)  # None = use default WIKI_PAGES

    if wiki_pages:
        # Override page list from config
        pages = []
        for p in wiki_pages:
            # Find matching page in WIKI_PAGES by ID
            matched = next(
                (wp for wp in WIKI_PAGES if wp["id"] == str(p.get("id", ""))), None
            )
            if matched:
                pages.append(matched)
            else:
                # Add custom page from config
                pages.append(p)
    else:
        pages = WIKI_PAGES

    if live:
        report = run_live_check(pages=pages, user=wiki_user, use_cache=use_cache)
    else:
        report = run_offline_check(pages=pages)

    # Extract actionable findings
    actionable = [f for f in report.findings if f.status in ("WARN", "ERROR")]

    return report, actionable


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="THC FV Wiki Cross-Check — Verify skill files against Confluence wiki pages"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Read live wiki pages (requires securewiki credentials)",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        default=False,
        help="Run offline check (uses cached content or skill-only checks)",
    )
    parser.add_argument(
        "--loop", type=int, default=1, help="Number of iterations to run (default: 1)"
    )
    parser.add_argument(
        "--user",
        type=str,
        default=DEFAULT_USER,
        help=f"Wiki user IDSID (default: {DEFAULT_USER})",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        default=False,
        help="Disable wiki page caching",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        default=False,
        help="Clear the wiki page cache and exit",
    )
    parser.add_argument(
        "--json", action="store_true", default=False, help="Output in JSON format"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        default=False,
        help="Save report to reports/ directory",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", default=False, help="Verbose logging"
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.clear_cache:
        clear_cache()
        return 0

    if args.loop > 1:
        reports = run_loop(args.loop, user=args.user, use_cache=not args.no_cache)
        # Summarize loop results
        all_pass = sum(
            1 for r in reports if all(f.status != "ERROR" for f in r.findings)
        )
        print(f"\n{'=' * 60}")
        print(f"Loop complete: {all_pass}/{len(reports)} iterations clean")
        print(f"{'=' * 60}")
        return 0 if all_pass == len(reports) else 1

    if args.live:
        report = run_live_check(user=args.user, use_cache=not args.no_cache)
    elif args.offline:
        report = run_offline_check()
    else:
        # Default: try live, fall back to offline
        logger.info(
            "No mode specified — trying live check, will fall back to offline on error"
        )
        try:
            report = run_live_check(user=args.user, use_cache=not args.no_cache)
        except Exception as e:
            logger.warning(f"Live check failed ({e}), falling back to offline")
            report = run_offline_check()

    # Output
    if args.json:
        print(report.to_json())
    else:
        print(report.to_text())

    # Save
    if args.save:
        reports_dir = resolve_path(".opencode/skill/fv-thc/reports")
        os.makedirs(reports_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(reports_dir, f"wiki_crosscheck_{ts}.json")
        report.save(report_path)
        logger.info(f"Report saved to {report_path}")

    # Exit code
    summary = report.to_dict().get("summary", {})
    has_errors = summary.get("ERROR", 0) > 0
    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
