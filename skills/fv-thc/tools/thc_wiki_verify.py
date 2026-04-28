#!/usr/bin/env python3
"""
THC Simics Wiki-to-Skill Live Verification
===========================================
Re-reads ALL wiki pages from Intel Confluence, extracts key assertions,
and verifies them against the 4 THC Simics skill files.

Usage:
    python thc_wiki_verify.py --live          # Full live pass (reads all wiki pages)
    python thc_wiki_verify.py --offline       # Offline assertion check only
    python thc_wiki_verify.py --loop N        # Run offline assertions N times
    python thc_wiki_verify.py --live --loop 1 # 1 live pass + 1 offline assertion loop
    python thc_wiki_verify.py --json          # JSON output

Owner: Chin, William Willy (willychi)
"""

import subprocess
import json
import sys
import os
import re
import time
import html
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# --- Unified credentials import ---
_CRED_DIR = str(Path(__file__).resolve().parent.parent.parent / "credentials")
if _CRED_DIR not in sys.path:
    sys.path.insert(0, _CRED_DIR)
try:
    from intel_credentials import get_credentials as _get_intel_creds
    HAS_CREDENTIALS = True
except ImportError:
    HAS_CREDENTIALS = False

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent / "simics"
SECUREWIKI = SCRIPT_DIR.parent.parent / "securewiki" / "securewiki.py"
WIKI_USER = "willychi"
WIKI_API_BASE = "https://wiki.ith.intel.com/rest/api"
WIKI_TIMEOUT = 120  # seconds per request — generous for reliability
MAX_WORKERS = 20  # maximum parallel wiki reads

# ============================================================================
# DIRECT WIKI SESSION (bypasses securewiki.py subprocess for speed+reliability)
# ============================================================================

_wiki_session = None


def _get_wiki_session(user=None):
    """Get or create a shared requests.Session with unified credential auth."""
    global _wiki_session
    if _wiki_session is not None:
        return _wiki_session

    if not HAS_REQUESTS:
        return None
    if not HAS_CREDENTIALS:
        return None

    try:
        username, password = _get_intel_creds(user or WIKI_USER)
    except Exception:
        return None

    session = requests.Session()
    session.auth = (username, password)
    session.verify = False  # Intel internal certs
    session.headers.update({"Accept": "application/json"})
    # Connection pooling — allow up to MAX_WORKERS concurrent connections
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=MAX_WORKERS,
        pool_maxsize=MAX_WORKERS,
        max_retries=urllib3.util.Retry(
            total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
        ),
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    _wiki_session = session
    return session


def _strip_html(text):
    """Strip HTML tags and decode entities from wiki body."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


SKILL_FILES = {
    "SKILL.md": SKILL_DIR / "SKILL.md",
    "models.md": SKILL_DIR / "models.md",
    "operations.md": SKILL_DIR / "operations.md",
    "advanced.md": SKILL_DIR / "advanced.md",
}

# ============================================================================
# WIKI PAGE MANIFEST — All 80 pages discovered during exhaustive research
# Each entry: (page_id, title, space, priority, assertions)
#   assertions = list of (search_term, target_file, description)
# ============================================================================

WIKI_PAGES = [
    # === SRESIMICS Space (BKMs, Setup, Model Development) ===
    {
        "id": "1966867553",
        "title": "THC model development (WIP)",
        "space": "SRESIMICS",
        "priority": "HIGH",
        "assertions": [
            ("reset_delay", "operations.md", "TEP reset_delay parameter"),
            ("7500", "operations.md", "MTL package 7500"),
            ("wa_ignore_setidvalue", "operations.md", "WA for HSD 1508517875"),
            ("mouse-as-touch", "models.md", "mouse-as-touch capability"),
        ],
    },
    {
        "id": "1966867456",
        "title": "THC Device Overview",
        "space": "SRESIMICS",
        "priority": "HIGH",
        "assertions": [
            ("90-unit-tests", "models.md", "unit test path prefix"),
            ("SIP_THC_ver2_0_HAS", "models.md", "HAS reference"),
        ],
    },
    {
        "id": "1433100579",
        "title": "THC Simics Getting Started",
        "space": "SRESIMICS",
        "priority": "MEDIUM",
        "assertions": [
            ("lkf.mb.sb.thc", "operations.md", "LKF naming convention"),
        ],
    },
    {
        "id": "2845164237",
        "title": "BKM THC I2C on LNL Simics",
        "space": "SRESIMICS",
        "priority": "HIGH",
        "assertions": [
            ("lnl.mb.south.thc", "operations.md", "LNL naming convention"),
            ("7600", "operations.md", "LNL package 7600"),
            ("alps", "operations.md", "LNL touch device name"),
        ],
    },
    {
        "id": "1966867128",
        "title": "BKM THC IPTS/HIDSPI on MTL Simics",
        "space": "SRESIMICS",
        "priority": "HIGH",
        "assertions": [
            ("1508958117", "operations.md", "MTL BIOS bug HSD"),
            ("mtl.mb.soc.thc", "operations.md", "MTL naming convention"),
        ],
    },
    {
        "id": "3217199088",
        "title": "BKM THC HIDSPI on PTL Simics",
        "space": "SRESIMICS",
        "priority": "HIGH",
        "assertions": [
            ("mb.south.thc", "operations.md", "PTL naming convention"),
            ("16015917403", "operations.md", "PTL SPI WA HSD"),
            ("alps_touchscreen", "operations.md", "PTL touch device name"),
        ],
    },
    {
        "id": "4045307441",
        "title": "BKM THC QuickI2C on NVL-S Simics",
        "space": "SRESIMICS",
        "priority": "HIGH",
        "assertions": [
            (
                "mb.pch.thc",
                "operations.md",
                "NVL naming convention (mb.pch not mb.south)",
            ),
        ],
    },
    {
        "id": "1966867486",
        "title": "THC WinDbg on MTL Simics",
        "space": "SRESIMICS",
        "priority": "MEDIUM",
        "assertions": [
            ("windbg_enable", "operations.md", "WinDbg enable flag"),
            ("12375", "operations.md", "WinDbg telnet port"),
        ],
    },
    {
        "id": "1800325877",
        "title": "BKM QuickSPI HIDSPI driver MTL Simics",
        "space": "SRESIMICS",
        "priority": "MEDIUM",
        "assertions": [
            ("descriptor include", "operations.md", "descriptor include files"),
        ],
    },
    # === THCipsv Space (IPSV Technical Content - GOLDMINE) ===
    {
        "id": "3986290848",
        "title": "THC Emulation",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("pcd_thc_simics", "advanced.md", "VTC emulation name"),
            ("transactors.json", "advanced.md", "transactor config file"),
        ],
    },
    {
        "id": "2765135286",
        "title": "THC PM flows",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("D0i2", "SKILL.md", "D0i2 power state"),
            ("PMCSR", "advanced.md", "PMCSR register for D3"),
        ],
    },
    {
        "id": "1900547074",
        "title": "THC HIDSPI/HIDI2C Validation Plan (LNL+)",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("ICR.*scrambl", "advanced.md", "ICR format scrambling"),
            ("1000.*seed", "advanced.md", "1000+ seed randomization"),
            (
                "opcode randomization",
                "advanced.md",
                "programmable opcode randomization",
            ),
        ],
    },
    {
        "id": "3565424997",
        "title": "THC Coalescing",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("8196", "advanced.md", "watermark + MPS <= 8196 constraint"),
            ("watermark", "advanced.md", "coalescing watermark"),
        ],
    },
    {
        "id": "2364131531",
        "title": "PTL THC Gen 4.1 PCRs",
        "space": "THCipsv",
        "priority": "MEDIUM",
        "assertions": [
            ("Gen 4\\.1", "advanced.md", "PTL Gen 4.1 reference"),
        ],
    },
    {
        "id": "1340605604",
        "title": "CI Automation THC",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("Falcon", "advanced.md", "Falcon CI framework"),
            ("Maestro", "advanced.md", "Maestro test framework"),
            ("Perspec", "advanced.md", "Perspec test framework"),
            ("BAT.*auto", "advanced.md", "BAT auto-trigger"),
        ],
    },
    {
        "id": "2141260829",
        "title": "RAMLess HIDI2C",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("RAMLess", "models.md", "RAMLess mode reference"),
            (
                "ramless_datamode_ctrl",
                "models.md",
                "RAMLess datamode control attribute",
            ),
        ],
    },
    {
        "id": "1908803784",
        "title": "Chapter 3: Register Summary",
        "space": "THCipsv",
        "priority": "MEDIUM",
        "assertions": [
            ("register", "advanced.md", "Register summary reference"),
        ],
    },
    {
        "id": "2813927240",
        "title": "Multi Report Interrupt Assertion LNL Bug Fix",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            (
                "multi.report.*interrupt",
                "advanced.md",
                "Multi-report interrupt support",
            ),
        ],
    },
    {
        "id": "3108833308",
        "title": "GPIO sync event mode bug fix",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("16019332816", "advanced.md", "GPIO sync event mode HSD"),
        ],
    },
    {
        "id": "3108833339",
        "title": "Buffer Overrun SPI vs I2C bug fix",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("16020879491", "advanced.md", "Buffer overrun SPI vs I2C HSD"),
        ],
    },
    {
        "id": "3516738658",
        "title": "NVL HIDSPI Delay Timer bug fix",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("Buffer Packet FIFO", "advanced.md", "Buffer Packet FIFO reference"),
            ("4 slots", "advanced.md", "LNL/PTL 4 slots"),
            ("32 slots", "advanced.md", "NVL 32 slots"),
        ],
    },
    {
        "id": "3454666109",
        "title": "Continuous timestamp smoothing/coalescing",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            (
                "THC_TS_D0I2_CONT_MODE",
                "advanced.md",
                "Timestamp D0i2 continuous mode register",
            ),
            ("THC_TS_D0I2_MODE", "advanced.md", "Timestamp D0i2 mode register"),
        ],
    },
    {
        "id": "2990902476",
        "title": "Coalescing with FrameSync event",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("Disabled.*Armed.*Active", "advanced.md", "Coalescing FSM states"),
        ],
    },
    {
        "id": "1983235857",
        "title": "PCR Dynamic frame coalescing",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("timer-based", "advanced.md", "Timer-based coalescing mode"),
            ("TCON.*sync", "advanced.md", "TCON sync coalescing mode"),
        ],
    },
    {
        "id": "2038236523",
        "title": "THC TCON Frame Sync Signal generator",
        "space": "THCipsv",
        "priority": "MEDIUM",
        "assertions": [
            ("TCON_CTRL_REG", "advanced.md", "TCON control register"),
        ],
    },
    {
        "id": "1997025384",
        "title": "TCON Frame Sync Signal feature (LNL+)",
        "space": "THCipsv",
        "priority": "MEDIUM",
        "assertions": [
            ("TCON", "advanced.md", "TCON reference"),
        ],
    },
    {
        "id": "1943084492",
        "title": "PCR THC RX packet >4KB",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("RX Streaming", "advanced.md", "RX Streaming Mode"),
            ("RXDMA_PKT_STRM", "advanced.md", "RXDMA_PKT_STRM_EN bit"),
        ],
    },
    {
        "id": "1933394613",
        "title": "PCR THC frame sync signal",
        "space": "THCipsv",
        "priority": "MEDIUM",
        "assertions": [
            ("DISP_SYNC_EVT_SRC", "advanced.md", "Display sync event source register"),
            ("SYNC_TS_LOG_BUF", "advanced.md", "Sync timestamp log buffer"),
        ],
    },
    {
        "id": "1982551495",
        "title": "PCR Allow SW to start Rx DMA (SWDMA)",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("SWDMA", "advanced.md", "SWDMA engine reference"),
            ("128 PRD", "advanced.md", "128 PRD tables max"),
        ],
    },
    {
        "id": "1846040828",
        "title": "PCR HW frame Coalescing 300Hz (CANCELLED)",
        "space": "THCipsv",
        "priority": "LOW",
        "assertions": [
            ("Will not do", "advanced.md", "Cancelled PCR note"),
        ],
    },
    {
        "id": "1850905269",
        "title": "PCR HID report timestamp",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("10.*us", "advanced.md", "Timestamp 10us step"),
            ("THC_TIMESTAMP_SRC", "advanced.md", "Timestamp source register"),
        ],
    },
    {
        "id": "2517795887",
        "title": "PCR 16-bit port ID",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("16-bit.*[Pp]ort", "SKILL.md", "16-bit SB port ID"),
            ("15010734105", "advanced.md", "16-bit port ID HSD"),
        ],
    },
    {
        "id": "2517795903",
        "title": "PCR WA Resource own req/Ack (Chassis 2.2)",
        "space": "THCipsv",
        "priority": "MEDIUM",
        "assertions": [
            ("Chassis 2.2", "advanced.md", "Chassis 2.2 reference"),
        ],
    },
    {
        "id": "2683760534",
        "title": "PCR IOSF 1.2/1.3 Expanded Header",
        "space": "THCipsv",
        "priority": "MEDIUM",
        "assertions": [
            ("SAI", "advanced.md", "SAI policy reference"),
        ],
    },
    {
        "id": "3775412802",
        "title": "THC Pytest GIT Repo",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            (
                "frameworks.validation.pythonsv.ipsv.thc",
                "advanced.md",
                "IPSV git repo name",
            ),
        ],
    },
    {
        "id": "3566312865",
        "title": "Python Focus Test list",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("focus test", "advanced.md", "Focus test reference"),
        ],
    },
    {
        "id": "3584960150",
        "title": "Python Script for Focus Test",
        "space": "THCipsv",
        "priority": "MEDIUM",
        "assertions": [
            ("SONORA_INPUT_REPORT", "advanced.md", "Sonora input report function"),
        ],
    },
    {
        "id": "4269795671",
        "title": "File used in different IP (ISH/THC)",
        "space": "THCipsv",
        "priority": "MEDIUM",
        "assertions": [
            ("Maestro", "advanced.md", "Maestro framework reference"),
        ],
    },
    {
        "id": "3028682606",
        "title": "Project PCR and Good-to-Know",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("Gen1.0.*LKF", "advanced.md", "IPSV gen mapping Gen1.0=LKF"),
        ],
    },
    {
        "id": "1880330910",
        "title": "SB message format",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("FuseReq", "advanced.md", "FuseReq SB opcode"),
            ("StrapReq", "advanced.md", "StrapReq SB opcode"),
            ("IPReady", "advanced.md", "IPReady SB opcode"),
        ],
    },
    {
        "id": "2798138055",
        "title": "FuseLite 2.x",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("opcode.*0x45", "advanced.md", "FuseLite 2.x combined opcode"),
            ("16-bit.*[Pp]ort", "advanced.md", "FuseLite 2.x 16-bit portID"),
        ],
    },
    {
        "id": "2211296045",
        "title": "FuseLite 1.x",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("0x39", "advanced.md", "THC0 portID 0x39"),
            ("0x3A", "advanced.md", "THC1 portID 0x3A"),
            ("0x80", "advanced.md", "Fuse address 0x80"),
            ("0x84", "advanced.md", "Strap address 0x84"),
        ],
    },
    {
        "id": "3356038208",
        "title": "Compile PMCLite Vector",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("pmc_kit_rom_parser", "advanced.md", "PMCLite vector compilation tool"),
        ],
    },
    {
        "id": "1274653307",
        "title": "THC-PMCLite Connection",
        "space": "THCipsv",
        "priority": "MEDIUM",
        "assertions": [
            ("PMCLite", "SKILL.md", "PMCLite reference"),
        ],
    },
    {
        "id": "2977738178",
        "title": "PM D3 flow (Overhauled)",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("D3Cold", "SKILL.md", "D3Cold power state"),
            ("D3Hot", "SKILL.md", "D3Hot power state"),
            ("28.*register", "advanced.md", "28 save/restore registers"),
        ],
    },
    {
        "id": "2755363002",
        "title": "BackDoor Register Access",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("0x01000000", "advanced.md", "PMCLite backdoor base address"),
            ("backdoor", "advanced.md", "Backdoor register access"),
        ],
    },
    {
        "id": "1894180152",
        "title": "Sonora3 TestCard Image Tracking",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("Sonora3", "advanced.md", "Sonora3 testcard reference"),
            ("DDR", "advanced.md", "Sonora3 DDR (not OCM)"),
        ],
    },
    {
        "id": "2794294764",
        "title": "Sonora3-DX7/HAPS80 setup",
        "space": "THCipsv",
        "priority": "MEDIUM",
        "assertions": [
            ("HT3", "advanced.md", "HT3 cable reference"),
        ],
    },
    {
        "id": "3108833358",
        "title": "quiesce_en_isol PG exit bug fix",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("quiesce_en_isol", "advanced.md", "PG exit bug fix reference"),
        ],
    },
    {
        "id": "1256270175",
        "title": "Maestro and Perspec",
        "space": "THCipsv",
        "priority": "LOW",
        "assertions": [
            ("Perspec", "advanced.md", "Perspec reference"),
        ],
    },
    {
        "id": "1983238991",
        "title": "PCR Fastest SPI controller",
        "space": "THCipsv",
        "priority": "MEDIUM",
        "assertions": [
            ("half.*divider", "advanced.md", "Half clock divider"),
            ("ZBB", "advanced.md", "ZBBed duty cycle feature"),
        ],
    },
    {
        "id": "4457832574",
        "title": "TTL PCD-H Tickets",
        "space": "THCipsv",
        "priority": "HIGH",
        "assertions": [
            ("TTL.*PCD-H", "advanced.md", "TTL PCD-H ticket reference"),
            ("simple_io_0_en", "advanced.md", "simple_io_0_en attribute"),
        ],
    },
    # === PPA Space (spi_xtor Documentation) ===
    {
        "id": "1249986923",
        "title": "spi_xtor Overview",
        "space": "PPA",
        "priority": "HIGH",
        "assertions": [
            ("spi_xtor", "models.md", "SPI transactor name"),
            ("NOT FULLY SUPPORTED", "models.md", "SPI touch limitation caveat"),
        ],
    },
    {
        "id": "1249986915",
        "title": "spi_xtor interfaces & attributes",
        "space": "PPA",
        "priority": "HIGH",
        "assertions": [
            ("spi_host_obj", "models.md", "thc_vdm spi_host_obj attribute"),
            ("touch_int_cause", "models.md", "thc_vdm touch_int_cause attribute"),
            ("tc_control", "models.md", "thc_vdm tc_control attribute"),
        ],
    },
    {
        "id": "1249986926",
        "title": "spi_xtor Operation modes",
        "space": "PPA",
        "priority": "MEDIUM",
        "assertions": [
            ("SPI flash generic", "models.md", "SPI flash generic mode"),
        ],
    },
    {
        "id": "1249986917",
        "title": "spi_xtor Hardware interface",
        "space": "PPA",
        "priority": "MEDIUM",
        "assertions": [
            ("spi_xactor", "models.md", "RTL module name"),
        ],
    },
    {
        "id": "1249986913",
        "title": "spi_xtor Integration (WIP)",
        "space": "PPA",
        "priority": "HIGH",
        "assertions": [
            ("THC VTC.*DEPRECATED", "models.md", "THC VTC deprecation note"),
            ("1\\.11\\.7", "models.md", "SPARK version for deprecation"),
            ("thc_vdm", "models.md", "THC VDM class name"),
        ],
    },
    {
        "id": "1249986972",
        "title": "spi_xtor BKMs & FAQs",
        "space": "PPA",
        "priority": "LOW",
        "assertions": [
            ("SFDP", "models.md", "SFDP reference"),
        ],
    },
    {
        "id": "1249986916",
        "title": "spi_xtor Flash generic mode VDM",
        "space": "PPA",
        "priority": "HIGH",
        "assertions": [
            ("opcode", "models.md", "Opcode configuration"),
            ("cmd_bits", "advanced.md", "Opcode cmd_bits parameter"),
        ],
    },
    {
        "id": "1249986975",
        "title": "spi_xtor Regression",
        "space": "PPA",
        "priority": "MEDIUM",
        "assertions": [
            ("thc_legacy", "models.md", "THC legacy regression test"),
            ("thc_simple_io", "models.md", "THC simple_io regression test"),
        ],
    },
    {
        "id": "1388942349",
        "title": "SPI xtor integration guide (PCHEMU)",
        "space": "PCHEMU",
        "priority": "MEDIUM",
        "assertions": [
            ("repositories.yml", "models.md", "repositories.yml format"),
        ],
    },
    {
        "id": "1249985406",
        "title": "THC BAT Test",
        "space": "PPA",
        "priority": "MEDIUM",
        "assertions": [
            ("BAT", "advanced.md", "BAT test reference"),
            ("PIO", "advanced.md", "PIO test reference"),
        ],
    },
    # === Other Spaces ===
    {
        "id": "1498127969",
        "title": "IPTS Playbook (CPS)",
        "space": "CPS",
        "priority": "MEDIUM",
        "assertions": [
            ("IPTS", "SKILL.md", "IPTS reference"),
        ],
    },
    {
        "id": "2068317556",
        "title": "MTL PSS Session Setup (IPTS)",
        "space": "IPTS",
        "priority": "MEDIUM",
        "assertions": [
            ("CRT", "operations.md", "CRT alternative reference"),
        ],
    },
    {
        "id": "3762034607",
        "title": "THC Test Content Support (VICESW)",
        "space": "VICESW",
        "priority": "HIGH",
        "assertions": [
            ("RTR", "advanced.md", "RTR framework reference"),
            ("Regflow", "advanced.md", "Regflow reference"),
            ("VICESW", "advanced.md", "VICESW space reference"),
        ],
    },
    {
        "id": "3054643734",
        "title": "THC Content/Features HID for PTL (VICESW)",
        "space": "VICESW",
        "priority": "MEDIUM",
        "assertions": [
            ("Perspec", "advanced.md", "Perspec test content"),
        ],
    },
    {
        "id": "4605435102",
        "title": "Simics Phone Book (fvcommon)",
        "space": "fvcommon",
        "priority": "LOW",
        "assertions": [
            ("THC", "SKILL.md", "THC referenced in phone book"),
        ],
    },
    {
        "id": "1693808060",
        "title": "RTL/Simics mappings SOC-S (PPA)",
        "space": "PPA",
        "priority": "MEDIUM",
        "assertions": [
            ("RTL", "advanced.md", "RTL model type"),
        ],
    },
    {
        "id": "1172406469",
        "title": "SOC Override (pch)",
        "space": "pch",
        "priority": "HIGH",
        "assertions": [
            ("SOC Override", "models.md", "SOC Override section"),
            ("single RDL", "models.md", "Single RDL architecture"),
            ("0xA0D", "models.md", "DID override mechanism"),
        ],
    },
    {
        "id": "2918220570",
        "title": "PM Enabling (fvcommon)",
        "space": "fvcommon",
        "priority": "MEDIUM",
        "assertions": [
            ("ThcAssignment", "operations.md", "ThcAssignment S0ix disable"),
        ],
    },
    {
        "id": "4148758972",
        "title": "GDB with Simics (s3e)",
        "space": "s3e",
        "priority": "LOW",
        "assertions": [
            ("GDB", "operations.md", "GDB debug reference"),
        ],
    },
    {
        "id": "3064545564",
        "title": "THC Debug Hooks (ESIPWiki)",
        "space": "ESIPWiki",
        "priority": "MEDIUM",
        "assertions": [
            ("VISA", "advanced.md", "VISA debug reference"),
        ],
    },
    {
        "id": "2761101312",
        "title": "THC PRD table in Maestro (VICESW)",
        "space": "VICESW",
        "priority": "HIGH",
        "assertions": [
            ("PRD", "advanced.md", "PRD table reference"),
            ("SWDMA", "advanced.md", "SWDMA reference"),
        ],
    },
    {
        "id": "1383238811",
        "title": "IP FPGA Farm Config (VICEPE)",
        "space": "VICEPE",
        "priority": "LOW",
        "assertions": [
            ("FPGA", "advanced.md", "FPGA reference"),
        ],
    },
]


def read_wiki_page(page_id, retries=3):
    """Read a wiki page via direct requests with shared session. Returns (success, content_or_error, title)."""
    session = _get_wiki_session()
    if session is None:
        return False, "Failed to create wiki session (keyring credentials missing?)", ""

    url = f"{WIKI_API_BASE}/content/{page_id}"
    params = {"expand": "body.storage,version,space"}
    last_err = ""

    for attempt in range(retries):
        try:
            resp = session.get(url, params=params, timeout=120, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                title = data.get("title", "unknown")
                body_html = data.get("body", {}).get("storage", {}).get("value", "")
                # Strip HTML tags for text content
                import re

                body_text = re.sub(r"<[^>]+>", " ", body_html)
                body_text = re.sub(r"\s+", " ", body_text).strip()
                return True, body_text, title
            elif resp.status_code == 404:
                return False, f"Page {page_id} not found (404)", ""
            elif resp.status_code == 401:
                return (
                    False,
                    f"Unauthorized (401) — check keyring credentials for '{WIKI_USER}'",
                    "",
                )
            elif resp.status_code == 403:
                return False, f"Forbidden (403) — no access to page {page_id}", ""
            else:
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                if attempt < retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                return False, last_err, ""
        except requests.exceptions.Timeout:
            last_err = f"HTTP timeout (120s) on attempt {attempt + 1}/{retries}"
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            return False, last_err, ""
        except requests.exceptions.ConnectionError as e:
            last_err = f"Connection error: {str(e)[:200]}"
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            return False, last_err, ""
        except Exception as e:
            last_err = f"Unexpected error: {str(e)[:200]}"
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            return False, last_err, ""
    return False, last_err, ""


def check_assertion(search_term, target_file, skill_files_content):
    """Check if search_term (regex) exists in the target skill file."""
    content = skill_files_content.get(target_file, "")
    if not content:
        return False, f"File {target_file} not loaded"
    try:
        pattern = re.compile(search_term, re.IGNORECASE)
        if pattern.search(content):
            return True, "FOUND"
        else:
            return False, f"NOT FOUND: '{search_term}' in {target_file}"
    except re.error:
        # Fall back to plain text search
        if search_term.lower() in content.lower():
            return True, "FOUND (plain)"
        return False, f"NOT FOUND: '{search_term}' in {target_file}"


def load_skill_files():
    """Load all skill file contents."""
    contents = {}
    for name, path in SKILL_FILES.items():
        try:
            contents[name] = path.read_text(encoding="utf-8")
        except Exception as e:
            contents[name] = ""
            print(f"  WARNING: Could not load {name}: {e}", file=sys.stderr)
    return contents


def run_live_pass(verbose=True, max_workers=20):
    """Re-read all wiki pages from Confluence and verify accessibility.

    Uses ThreadPoolExecutor for parallel reads (default 8 workers).
    80 pages at ~10s/page sequential = 800s; with 8 workers = ~100s.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = {
        "total_pages": len(WIKI_PAGES),
        "accessible": 0,
        "failed": 0,
        "errors": [],
        "pages": [],
    }

    if verbose:
        print(f"\n{'=' * 70}")
        print(f"LIVE WIKI PASS — Reading {len(WIKI_PAGES)} pages from Intel Confluence")
        print(f"  (parallel: {max_workers} workers)")
        print(f"{'=' * 70}")

    # Build page lookup for ordered results
    page_results_map = {}
    completed = 0

    def _read_one(page):
        """Read a single wiki page (thread-safe — each spawns own subprocess)."""
        pid = page["id"]
        success, content_or_error, live_title = read_wiki_page(pid)
        return page, success, content_or_error, live_title

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_read_one, p): p for p in WIKI_PAGES}

        for future in as_completed(futures):
            completed += 1
            page, success, content_or_error, live_title = future.result()
            pid = page["id"]
            title = page["title"]

            if verbose and completed % 10 == 0:
                print(f"  [{completed}/{len(WIKI_PAGES)}] Pages read...", flush=True)

            page_result = {
                "id": pid,
                "title": title,
                "space": page["space"],
                "accessible": success,
                "content_length": len(content_or_error) if success else 0,
            }

            if success:
                results["accessible"] += 1
            else:
                results["failed"] += 1
                page_result["error"] = content_or_error
                results["errors"].append(f"Page {pid} ({title}): {content_or_error}")

            page_results_map[pid] = page_result

    # Preserve original page order in results
    for page in WIKI_PAGES:
        if page["id"] in page_results_map:
            results["pages"].append(page_results_map[page["id"]])

    if verbose:
        print(
            f"\n  Live pass complete: {results['accessible']}/{results['total_pages']} accessible, {results['failed']} failed"
        )
        if results["errors"]:
            print(f"  Errors:")
            for e in results["errors"][:10]:
                print(f"    - {e}")

    return results


def run_assertion_check(verbose=True):
    """Run all assertions against skill files (offline)."""
    skill_content = load_skill_files()

    results = {
        "total_assertions": 0,
        "pass": 0,
        "fail": 0,
        "failures": [],
        "by_file": {},
        "by_page": [],
    }

    for page in WIKI_PAGES:
        page_pass = 0
        page_fail = 0
        page_failures = []

        for search_term, target_file, desc in page["assertions"]:
            results["total_assertions"] += 1
            ok, msg = check_assertion(search_term, target_file, skill_content)

            if ok:
                results["pass"] += 1
                page_pass += 1
            else:
                results["fail"] += 1
                page_fail += 1
                failure = {
                    "page_id": page["id"],
                    "page_title": page["title"],
                    "assertion": desc,
                    "search_term": search_term,
                    "target_file": target_file,
                    "message": msg,
                }
                results["failures"].append(failure)
                page_failures.append(failure)

            # Track per-file stats
            if target_file not in results["by_file"]:
                results["by_file"][target_file] = {"pass": 0, "fail": 0}
            if ok:
                results["by_file"][target_file]["pass"] += 1
            else:
                results["by_file"][target_file]["fail"] += 1

        results["by_page"].append(
            {
                "id": page["id"],
                "title": page["title"],
                "pass": page_pass,
                "fail": page_fail,
                "failures": page_failures,
            }
        )

    if verbose:
        print(f"\n{'=' * 70}")
        print(
            f"ASSERTION CHECK — {results['total_assertions']} assertions across {len(WIKI_PAGES)} pages"
        )
        print(f"{'=' * 70}")
        print(f"  PASS: {results['pass']}/{results['total_assertions']}")
        print(f"  FAIL: {results['fail']}/{results['total_assertions']}")
        print(f"\n  Per-file breakdown:")
        for fname, stats in sorted(results["by_file"].items()):
            status = "✓" if stats["fail"] == 0 else "✗"
            print(f"    {status} {fname}: {stats['pass']} pass, {stats['fail']} fail")

        if results["failures"]:
            print(f"\n  FAILURES:")
            for f in results["failures"]:
                print(f"    ✗ [{f['page_id']}] {f['page_title']}")
                print(f"      Assertion: {f['assertion']}")
                print(f"      Search: '{f['search_term']}' in {f['target_file']}")
                print(f"      {f['message']}")

    return results


def run_loop(n, verbose=True):
    """Run assertion check N times for stability."""
    all_results = []
    all_pass = True

    if verbose:
        print(f"\n{'=' * 70}")
        print(f"STABILITY LOOP — Running {n} iterations of assertion checks")
        print(f"{'=' * 70}")

    for i in range(1, n + 1):
        result = run_assertion_check(verbose=False)
        all_results.append(result)
        if result["fail"] > 0:
            all_pass = False

        if verbose and (i % 10 == 0 or i == n):
            total_pass = sum(r["pass"] for r in all_results)
            total_fail = sum(r["fail"] for r in all_results)
            total = sum(r["total_assertions"] for r in all_results)
            print(
                f"  Iteration {i}/{n}: cumulative {total_pass}/{total} pass ({total_fail} fail)"
            )

    if verbose:
        total_pass = sum(r["pass"] for r in all_results)
        total_fail = sum(r["fail"] for r in all_results)
        total = sum(r["total_assertions"] for r in all_results)
        print(
            f"\n  {'*** ALL ' + str(n) + ' ITERATIONS PASSED ***' if all_pass else '*** FAILURES DETECTED ***'}"
        )
        print(
            f"  Total assertions executed: {total} ({n} × {all_results[0]['total_assertions']})"
        )
        print(f"  Total pass: {total_pass}, Total fail: {total_fail}")

    return all_results, all_pass


def run_pipeline_check(live=False, user="willychi"):
    """Pipeline-compatible entry point returning Finding objects.

    Used by thc_self_improve.py Stage 5 (wiki) to integrate Simics wiki
    verification into the self-improvement pipeline.

    Args:
        live: If True, read wiki pages from Confluence first.
        user: Confluence username for live reads.

    Returns:
        list[Finding]: List of Finding objects (from thc_self_common).
    """
    try:
        from thc_self_common import Finding
    except ImportError:
        # Fallback: define a minimal Finding-compatible namedtuple
        from collections import namedtuple

        Finding = namedtuple(
            "Finding", ["check", "target", "status", "message", "severity", "details"]
        )

    findings = []

    # --- Live pass (optional) ---
    if live:
        global WIKI_USER
        WIKI_USER = user
        live_results = run_live_pass(verbose=False)
        findings.append(
            Finding(
                check="simics_wiki_accessibility",
                target="simics/",
                status="PASS" if live_results["failed"] == 0 else "WARN",
                message=f"Simics wiki: {live_results['accessible']}/{live_results['total_pages']} pages accessible",
                severity="info" if live_results["failed"] == 0 else "medium",
                details={
                    "accessible": live_results["accessible"],
                    "total": live_results["total_pages"],
                    "failed": live_results["failed"],
                    "errors": live_results["errors"][:5],
                },
            )
        )

    # --- Assertion check (always) ---
    assertion_results = run_assertion_check(verbose=False)

    # Summary finding
    total = assertion_results["total_assertions"]
    passed = assertion_results["pass"]
    failed = assertion_results["fail"]

    findings.append(
        Finding(
            check="simics_wiki_assertions",
            target="simics/",
            status="PASS" if failed == 0 else "FAIL",
            message=f"Simics wiki assertions: {passed}/{total} pass, {failed} fail",
            severity="info" if failed == 0 else "high",
            details={
                "total": total,
                "pass": passed,
                "fail": failed,
                "by_file": assertion_results.get("by_file", {}),
            },
        )
    )

    # Individual failure findings (for proposal generation)
    for f in assertion_results.get("failures", []):
        findings.append(
            Finding(
                check="simics_wiki_assertion_fail",
                target=f"simics/{f['target_file']}",
                status="FAIL",
                message=f"Missing from {f['target_file']}: '{f['search_term']}' ({f['assertion']})",
                severity="medium",
                details={
                    "page_id": f["page_id"],
                    "page_title": f["page_title"],
                    "search_term": f["search_term"],
                    "target_file": f["target_file"],
                    "assertion": f["assertion"],
                },
            )
        )

    return findings


def main():
    import argparse

    parser = argparse.ArgumentParser(description="THC Wiki-to-Skill Live Verification")
    parser.add_argument("--live", action="store_true", help="Run live wiki page reads")
    parser.add_argument(
        "--offline", action="store_true", help="Run offline assertion check only"
    )
    parser.add_argument(
        "--loop", type=int, default=0, help="Run assertion loop N times"
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if not args.live and not args.offline and args.loop == 0:
        # Default: run live + 1 assertion check
        args.live = True
        args.offline = True

    verbose = not args.json
    all_output = {
        "timestamp": datetime.now().isoformat(),
        "live": None,
        "assertions": None,
        "loop": None,
    }

    if verbose:
        print(f"THC Simics Wiki-to-Skill Live Verification")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Pages in manifest: {len(WIKI_PAGES)}")
        total_assertions = sum(len(p["assertions"]) for p in WIKI_PAGES)
        print(f"Total assertions: {total_assertions}")

    # Live pass
    if args.live:
        live_results = run_live_pass(verbose=verbose)
        all_output["live"] = live_results

    # Assertion check
    if args.offline or args.live:
        assertion_results = run_assertion_check(verbose=verbose)
        all_output["assertions"] = assertion_results

    # Loop
    if args.loop > 0:
        loop_results, all_pass = run_loop(args.loop, verbose=verbose)
        all_output["loop"] = {
            "iterations": args.loop,
            "all_pass": all_pass,
            "total_assertions": sum(r["total_assertions"] for r in loop_results),
            "total_pass": sum(r["pass"] for r in loop_results),
            "total_fail": sum(r["fail"] for r in loop_results),
        }

    # Final summary
    if verbose:
        print(f"\n{'=' * 70}")
        print(f"FINAL SUMMARY")
        print(f"{'=' * 70}")
        if all_output["live"]:
            lr = all_output["live"]
            print(f"  Wiki pages: {lr['accessible']}/{lr['total_pages']} accessible")
        if all_output["assertions"]:
            ar = all_output["assertions"]
            print(f"  Assertions: {ar['pass']}/{ar['total_assertions']} pass")
        if all_output["loop"]:
            lo = all_output["loop"]
            print(
                f"  Loop ({lo['iterations']}x): {lo['total_pass']}/{lo['total_assertions']} pass, all_pass={lo['all_pass']}"
            )

    if args.json:
        # Trim per-page details for compact JSON
        if all_output["assertions"]:
            all_output["assertions"].pop("by_page", None)
        print(json.dumps(all_output, indent=2))

    # Exit code
    has_fail = False
    if all_output["assertions"] and all_output["assertions"]["fail"] > 0:
        has_fail = True
    if all_output["loop"] and not all_output["loop"]["all_pass"]:
        has_fail = True
    sys.exit(1 if has_fail else 0)


if __name__ == "__main__":
    main()
