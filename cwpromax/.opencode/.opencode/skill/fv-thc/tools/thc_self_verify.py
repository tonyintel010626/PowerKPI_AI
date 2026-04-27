# > **Owner**: Chin, William Willy (`willychi`)
# THC Self-Verify: Automated eval test runner for THC skill accuracy
# Part of the THC Self-Improvement Framework
#
# Programmatically verifies skill content against ground truth assertions.
# Each eval test ID has machine-readable assertions that check specific
# content in specific files.
#
# Usage:
#   python thc_self_verify.py                    # Run all assertions
#   python thc_self_verify.py --json             # JSON output
#   python thc_self_verify.py --category REG     # Run only REG-* tests
#   python thc_self_verify.py --test REG-001     # Run specific test
#   python thc_self_verify.py --save report.json # Save results
#
# Exit codes: 0 = all pass, 1 = failures found, 2 = error
# Support: For any issues, contact the owner above. Please collect the complete
#          session transcript (AI log dump) before reporting for faster root-cause analysis.

import sys
import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from thc_self_common import (
    find_repo_root,
    load_config,
    get_skill_path,
    read_skill,
    find_pattern_in_file,
    Finding,
    Report,
    setup_logging,
)

logger = setup_logging("thc_self_verify")


# =============================================================================
# ASSERTION HELPERS
# =============================================================================


def assert_contains(skill_name: str, pattern: str, description: str = "") -> Finding:
    """Assert that a skill file contains the given pattern."""
    content = read_skill(skill_name)
    if content is None:
        return Finding(
            check="content_assert",
            target=f"fv-thc/{skill_name}",
            status="ERROR",
            message=f"Could not read {skill_name}/SKILL.md",
        )
    if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
        return Finding(
            check="content_assert",
            target=f"fv-thc/{skill_name}",
            status="PASS",
            message=description or f"Contains: {pattern[:60]}",
        )
    else:
        return Finding(
            check="content_assert",
            target=f"fv-thc/{skill_name}",
            status="FAIL",
            message=f"NOT FOUND: {description or pattern[:80]}",
            severity="medium",
        )


def assert_not_contains(
    skill_name: str, pattern: str, description: str = ""
) -> Finding:
    """Assert that a skill file does NOT contain the given pattern."""
    content = read_skill(skill_name)
    if content is None:
        return Finding(
            check="content_assert",
            target=f"fv-thc/{skill_name}",
            status="ERROR",
            message=f"Could not read {skill_name}/SKILL.md",
        )
    if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
        return Finding(
            check="negative_assert",
            target=f"fv-thc/{skill_name}",
            status="FAIL",
            message=f"SHOULD NOT CONTAIN: {description or pattern[:80]}",
            severity="medium",
        )
    else:
        return Finding(
            check="negative_assert",
            target=f"fv-thc/{skill_name}",
            status="PASS",
            message=description or f"Correctly absent: {pattern[:60]}",
        )


def assert_value_match(
    skill_name: str, field_pattern: str, expected_value: str, description: str = ""
) -> Finding:
    """Assert a specific value appears near a field name in the skill."""
    content = read_skill(skill_name)
    if content is None:
        return Finding(
            check="value_assert",
            target=f"fv-thc/{skill_name}",
            status="ERROR",
            message=f"Could not read {skill_name}/SKILL.md",
        )

    # Search for field pattern and check nearby context for expected value
    for match in re.finditer(field_pattern, content, re.IGNORECASE):
        # Get surrounding context (200 chars after match)
        start = match.start()
        context = content[start : start + 300]
        if re.search(re.escape(expected_value), context, re.IGNORECASE):
            return Finding(
                check="value_assert",
                target=f"fv-thc/{skill_name}",
                status="PASS",
                message=description or f"{field_pattern} = {expected_value}",
            )

    return Finding(
        check="value_assert",
        target=f"fv-thc/{skill_name}",
        status="FAIL",
        message=f"Value mismatch: {description or f'{field_pattern} should have {expected_value}'}",
        severity="medium",
    )


# =============================================================================
# TEST DEFINITIONS — Machine-readable assertions per eval test ID
# =============================================================================

EVAL_TESTS = {
    # =========================================================================
    # REG — Register Knowledge
    # =========================================================================
    "REG-001": {
        "name": "THC MMIO BAR Size",
        "skill": "registers",
        "assertions": [
            ("contains", "registers", r"32\s*KB|0x8000", "BAR0 is 32KB"),
        ],
    },
    "REG-002": {
        "name": "THC_M_PRT_CONTROL Register",
        "skill": "registers",
        "assertions": [
            (
                "contains",
                "registers",
                r"thc_m_prt_control",
                "PRT_CONTROL register documented",
            ),
            ("contains", "registers", r"port_type", "port_type field documented"),
        ],
    },
    "REG-003": {
        "name": "PIO Opcode Values",
        "skill": "registers",
        "assertions": [
            ("contains", "registers", r"0x4.*read|read.*0x4", "PIO Read opcode = 0x4"),
            (
                "contains",
                "registers",
                r"0x6.*write|write.*0x6",
                "PIO Write opcode = 0x6",
            ),
        ],
    },
    "REG-004": {
        "name": "SPI_RD_MPS Register",
        "skill": "registers",
        "assertions": [
            ("contains", "registers", r"spi_rd_mps", "SPI_RD_MPS register documented"),
        ],
    },
    "REG-005": {
        "name": "THC Register Restore Order",
        "skill": "registers",
        "assertions": [
            (
                "contains",
                "registers",
                r"restore.*order|order.*restore",
                "Register restore order documented",
            ),
        ],
    },
    "REG-006": {
        "name": "DEVINT_CFG Register Offsets",
        "skill": "registers",
        "assertions": [
            (
                "contains",
                "registers",
                r"DEVINT_CFG_1.*0x0EC|0x0EC.*DEVINT_CFG_1",
                "DEVINT_CFG_1 at 0x0EC",
            ),
            (
                "contains",
                "registers",
                r"DEVINT_CFG_2.*0x0F0|0x0F0.*DEVINT_CFG_2",
                "DEVINT_CFG_2 at 0x0F0",
            ),
        ],
    },
    "REG-007": {
        "name": "READ_DMA_CNTRL Key Bits",
        "skill": "registers",
        "assertions": [
            (
                "contains",
                "registers",
                r"SOO|[Ss]top.on.[Oo]verflow",
                "SOO bit in READ_DMA_CNTRL documented",
            ),
            (
                "contains",
                "registers",
                r"TPCWP|TPCRP",
                "TPCWP/TPCRP pointer fields documented",
            ),
        ],
    },
    "REG-008": {
        "name": "SWDMA PRD Registers",
        "skill": "registers",
        "assertions": [
            ("contains", "registers", r"SWDMA|sw.?dma", "SWDMA registers documented"),
            (
                "contains",
                "registers",
                r"0x2[Cc]0|0x2[Ee]0",
                "SWDMA PRD register range documented",
            ),
        ],
    },
    "REG-009": {
        "name": "TIMESTAMP Registers",
        "skill": "registers",
        "assertions": [
            (
                "contains",
                "registers",
                r"TIMESTAMP|timestamp",
                "Timestamp registers documented",
            ),
        ],
    },
    "REG-010": {
        "name": "Max Register and Port Base",
        "skill": "registers",
        "assertions": [
            (
                "contains",
                "registers",
                r"0x1320|max.register",
                "Max register offset documented",
            ),
            (
                "contains",
                "registers",
                r"0x1000|0x2000|port.*base",
                "Port base offsets documented",
            ),
        ],
    },
    # =========================================================================
    # SPI — HIDSPI Protocol
    # =========================================================================
    "SPI-001": {
        "name": "SPI Base Clock Frequency",
        "skill": "hidspi",
        "assertions": [
            ("contains", "hidspi", r"125\s*MHz", "SPI base clock is 125 MHz"),
            ("not_contains", "hidspi", r"128\s*MHz", "Should NOT say 128 MHz"),
        ],
    },
    "SPI-002": {
        "name": "SPI IO Modes",
        "skill": "hidspi",
        "assertions": [
            ("contains", "hidspi", r"single|dual|quad", "SPI IO modes documented"),
        ],
    },
    "SPI-003": {
        "name": "ICR (Input Cause Register)",
        "skill": "hidspi",
        "assertions": [
            ("contains", "hidspi", r"ICR|input.cause.register", "ICR documented"),
        ],
    },
    "SPI-004": {
        "name": "HIDSPI Report Types",
        "skill": "hidspi",
        "assertions": [
            ("contains", "hidspi", r"input.report", "Input reports documented"),
            ("contains", "hidspi", r"output.report", "Output reports documented"),
        ],
    },
    "SPI-005": {
        "name": "SPI Clock Divider Formula",
        "skill": "hidspi",
        "assertions": [
            ("contains", "hidspi", r"divider|divid", "Clock divider documented"),
        ],
    },
    "SPI-006": {
        "name": "WCL HIDSPI Device IDs",
        "skill": "hidspi",
        "assertions": [
            ("contains", "hidspi", r"0x4D49", "WCL THC0 HIDSPI DID = 0x4D49"),
            ("contains", "hidspi", r"0x4D4B", "WCL THC1 HIDSPI DID = 0x4D4B"),
            (
                "not_contains",
                "hidspi",
                r"0x5749",
                "Should NOT have stale WCL DID 0x5749",
            ),
        ],
    },
    "SPI-007": {
        "name": "Half-Divider Clock (PTL+)",
        "skill": "hidspi",
        "assertions": [
            ("contains", "hidspi", r"half.divider|DCG", "Half-divider/DCG documented"),
        ],
    },
    "SPI-008": {
        "name": "Host Reset via TXDMA",
        "skill": "hidspi",
        "assertions": [
            (
                "contains",
                "hidspi",
                r"TXDMA|txdma|write_cmd_to_txdma",
                "Host Reset uses TXDMA",
            ),
        ],
    },
    # =========================================================================
    # I2C — HIDI2C Protocol
    # =========================================================================
    "I2C-001": {
        "name": "I2C Speed Modes",
        "skill": "hidi2c",
        "assertions": [
            (
                "contains",
                "hidi2c",
                r"100\s*K|standard",
                "Standard mode (100K) documented",
            ),
            (
                "contains",
                "hidi2c",
                r"400\s*K|fast\s*mode",
                "Fast mode (400K) documented",
            ),
        ],
    },
    "I2C-002": {
        "name": "Synopsys I2C Sub-IP",
        "skill": "hidi2c",
        "assertions": [
            (
                "contains",
                "hidi2c",
                r"synopsys|designware|IC_CON",
                "Synopsys sub-IP documented",
            ),
        ],
    },
    "I2C-003": {
        "name": "IC_CON Default Value",
        "skill": "hidi2c",
        "assertions": [
            (
                "contains",
                "hidi2c",
                r"0x0?663",
                "IC_CON Linux default = 0x663 or 0x0663",
            ),
        ],
    },
    "I2C-004": {
        "name": "SPI_RD_MPS Workaround for I2C",
        "skill": "hidi2c",
        "assertions": [
            (
                "contains",
                "hidi2c",
                r"SPI_RD_MPS.*4096|4096.*SPI_RD_MPS",
                "I2C MPS workaround documented",
            ),
        ],
    },
    "I2C-005": {
        "name": "HIDI2C Port Type Configuration",
        "skill": "hidi2c",
        "assertions": [
            ("contains", "hidi2c", r"port_type", "PORT_TYPE config documented"),
        ],
    },
    "I2C-006": {
        "name": "I2C Target Address (0x0A driver default vs 0x086 IC_TAR)",
        "skill": "hidi2c",
        "assertions": [
            (
                "contains",
                "hidi2c",
                r"0x0A",
                "Driver default target address 0x0A documented",
            ),
            (
                "contains",
                "hidi2c",
                r"0x086",
                "Synopsys IC_TAR hardware default 0x086 documented",
            ),
            (
                "contains",
                "hidi2c",
                r"driver.default|IC_TAR",
                "Context disambiguation documented",
            ),
        ],
    },
    "I2C-007": {
        "name": "RXDMA2 for I2C Input",
        "skill": "hidi2c",
        "assertions": [
            (
                "contains",
                "hidi2c",
                r"RXDMA2|rxdma2",
                "RXDMA2 as primary I2C input path",
            ),
        ],
    },
    "I2C-008": {
        "name": "WCL HIDI2C Device IDs",
        "skill": "hidi2c",
        "assertions": [
            ("contains", "hidi2c", r"0x4D48", "WCL THC0 HIDI2C DID = 0x4D48"),
            ("contains", "hidi2c", r"0x4D4A", "WCL THC1 HIDI2C DID = 0x4D4A"),
            (
                "not_contains",
                "hidi2c",
                r"0x5748",
                "Should NOT have stale WCL DID 0x5748",
            ),
        ],
    },
    "I2C-009": {
        "name": "I2C Timing Cross-Platform Difference",
        "skill": "hidi2c",
        "assertions": [
            (
                "contains",
                "hidi2c",
                r"FS_HCNT|HCNT|LCNT",
                "I2C timing registers documented",
            ),
        ],
    },
    # =========================================================================
    # DMA — DMA Architecture
    # =========================================================================
    "DMA-001": {
        "name": "PRD Ring Structure",
        "skill": "dma",
        "assertions": [
            ("contains", "dma", r"PRD|physical.region.descriptor", "PRD documented"),
        ],
    },
    "DMA-002": {
        "name": "RXDMA Channels",
        "skill": "dma",
        "assertions": [
            ("contains", "dma", r"RXDMA", "RXDMA channels documented"),
        ],
    },
    "DMA-003": {
        "name": "SWDMA Engine",
        "skill": "dma",
        "assertions": [
            ("contains", "dma", r"SWDMA|sw.?dma", "SWDMA engine documented"),
        ],
    },
    "DMA-004": {
        "name": "RXDMA2 for I2C Routing",
        "skill": "dma",
        "assertions": [
            (
                "contains",
                "dma",
                r"RXDMA2.*I2C|I2C.*RXDMA2|HIDI2C.*Frame Type|Frame Type.*routing",
                "RXDMA2 for I2C routing",
            ),
        ],
    },
    "DMA-005": {
        "name": "DMA Pause Mechanism",
        "skill": "dma",
        "assertions": [
            ("contains", "dma", r"pause|INT_STS", "DMA pause mechanism documented"),
        ],
    },
    "DMA-006": {
        "name": "PRD 4KB Alignment Bug",
        "skill": "dma",
        "assertions": [
            (
                "contains",
                "dma",
                r"4KB.*align|align.*4KB|15014172472",
                "PRD alignment RTL bug documented",
            ),
        ],
    },
    "DMA-007": {
        "name": "TXDMA for Commands",
        "skill": "dma",
        "assertions": [
            ("contains", "dma", r"TXDMA|txdma", "TXDMA documented"),
        ],
    },
    "DMA-008": {
        "name": "DMA Streaming Mode",
        "skill": "dma",
        "assertions": [
            ("contains", "dma", r"stream|burst", "DMA streaming/burst mode documented"),
        ],
    },
    # =========================================================================
    # PWR — Power Management
    # =========================================================================
    "PWR-001": {
        "name": "LTR (Latency Tolerance Reporting)",
        "skill": "power",
        "assertions": [
            ("contains", "power", r"LTR|latency.tolerance", "LTR documented"),
        ],
    },
    "PWR-002": {
        "name": "D0i2 Sub-State",
        "skill": "power",
        "assertions": [
            ("contains", "power", r"D0i2", "D0i2 documented"),
        ],
    },
    "PWR-003": {
        "name": "D3 Power Levels",
        "skill": "power",
        "assertions": [
            (
                "contains",
                "power",
                r"D3.*level|level.*D3|D3Hot|D3Cold",
                "D3 power levels documented",
            ),
        ],
    },
    "PWR-004": {
        "name": "Wake-on-Touch Reference",
        "skill": "power",
        "assertions": [
            (
                "contains",
                "power",
                r"WoT|Wake.on.Touch|fv-thc/wot",
                "WoT cross-reference in power skill",
            ),
        ],
    },
    "PWR-005": {
        "name": "PMCLite Sideband",
        "skill": "power",
        "assertions": [
            ("contains", "power", r"PMCLite|pmclite|sideband", "PMCLite documented"),
        ],
    },
    "PWR-006": {
        "name": "CGPG (Clock Gating / Power Gating)",
        "skill": "power",
        "assertions": [
            ("contains", "power", r"CGPG|clock.gat|power.gat", "CGPG documented"),
        ],
    },
    "PWR-007": {
        "name": "LTR Unconfig Pattern",
        "skill": "power",
        "assertions": [
            (
                "contains",
                "power",
                r"LP_LTR_EN|ACTIVE_LTR_EN|LP_LTR_REQ|ACTIVE_LTR_REQ",
                "LTR unconfig fields documented [DOC-002]",
            ),
        ],
    },
    # =========================================================================
    # PLAT — Platform Data
    # =========================================================================
    "PLAT-001": {
        "name": "NVL THC1 BDF Change",
        "skill": "platform",
        "assertions": [
            (
                "contains",
                "platform",
                r"NVL.*THC1|THC1.*Dev.?=.?8",
                "NVL THC1 BDF change documented",
            ),
        ],
    },
    "PLAT-002": {
        "name": "Platform Init Sequence",
        "skill": "platform",
        "assertions": [
            (
                "contains",
                "platform",
                r"init.*sequence|boot.*sequence|probe",
                "Platform init sequence documented",
            ),
        ],
    },
    "PLAT-003": {
        "name": "BOM Device Matrix",
        "skill": "platform",
        "assertions": [
            (
                "contains",
                "platform",
                r"BOM|WACOM|ELAN|ALPS",
                "BOM device matrix documented",
            ),
        ],
    },
    "PLAT-004": {
        "name": "DID Pattern (Even=I2C, Odd=SPI)",
        "skill": "platform",
        "assertions": [
            (
                "contains",
                "platform",
                r"even.*I2C|I2C.*even|odd.*SPI|SPI.*odd",
                "DID even=I2C, odd=SPI pattern documented",
            ),
        ],
    },
    "PLAT-005": {
        "name": "QuickSPI Non-POR from PTL+",
        "skill": "platform",
        "assertions": [
            (
                "contains",
                "platform",
                r"QuickSPI.*[Nn]on.POR|[Nn]on.POR.*QuickSPI|Non-POR.*PTL",
                "QuickSPI Non-POR from PTL+ documented",
            ),
        ],
    },
    "PLAT-006": {
        "name": "THC1 Requires THC0 Enabled",
        "skill": "platform",
        "assertions": [
            (
                "contains",
                "platform",
                r"THC1.*THC0|THC0.*required|Function.?0.*active",
                "THC1 requires THC0 enabled documented",
            ),
        ],
    },
    "PLAT-007": {
        "name": "PMC SSRAM Base Address",
        "skill": "platform",
        "assertions": [
            (
                "contains",
                "platform",
                r"0xFE010000|PMC_SSRAM|SSRAM_BASE",
                "PMC SSRAM base address documented",
            ),
        ],
    },
    "PLAT-008": {
        "name": "Per-Platform Die Type Mapping",
        "skill": "platform",
        "assertions": [
            (
                "contains",
                "platform",
                r"SOC_SOUTH|PCH|die.*type|die_type",
                "Per-platform die type mapping documented",
            ),
        ],
    },
    # =========================================================================
    # DRV — Driver Source
    # =========================================================================
    "DRV-001": {
        "name": "Linux THC Driver Path",
        "skill": "driver",
        "assertions": [
            ("contains", "driver", r"intel-thc-hid", "Linux driver path documented"),
        ],
    },
    "DRV-002": {
        "name": "Windows HIDSPI Version",
        "skill": "driver",
        "assertions": [
            (
                "contains",
                "driver",
                r"v4\.0\.0\.9000|4\.0\.0\.9000",
                "Windows HIDSPI version documented",
            ),
        ],
    },
    "DRV-003": {
        "name": "Probe Sequence Steps",
        "skill": "driver",
        "assertions": [
            (
                "contains",
                "driver",
                r"probe|14.step|init.*sequence",
                "Probe sequence documented",
            ),
        ],
    },
    "DRV-004": {
        "name": "Cross-Platform Differences",
        "skill": "driver",
        "assertions": [
            (
                "contains",
                "driver",
                r"Linux.*Windows|Windows.*Linux|cross.platform",
                "Cross-platform differences documented",
            ),
        ],
    },
    "DRV-005": {
        "name": "DMA Cross-Reference",
        "skill": "driver",
        "assertions": [
            ("contains", "driver", r"fv-thc/dma", "DMA skill cross-reference present"),
        ],
    },
    "DRV-006": {
        "name": "GBL_INT_EN Divergence (SPI vs I2C)",
        "skill": "driver",
        "assertions": [
            (
                "contains",
                "driver",
                r"GBL_INT_EN|Global.*IE|per.vector.*mask",
                "GBL_INT_EN interrupt masking documented",
            ),
        ],
    },
    "DRV-007": {
        "name": "Reset Timeout Values",
        "skill": "driver",
        "assertions": [
            (
                "contains",
                "driver",
                r"reset.*timeout|timeout.*reset",
                "Reset timeout values documented",
            ),
        ],
    },
    "DRV-008": {
        "name": "TIC Register Map",
        "skill": "driver",
        "assertions": [
            (
                "contains",
                "driver",
                r"TIC|0x43495424|\$TIC",
                "TIC register map or magic value documented",
            ),
        ],
    },
    "DRV-009": {
        "name": "Special Report IDs",
        "skill": "driver",
        "assertions": [
            (
                "contains",
                "driver",
                r"0x40|0x47|0x5[AaBbCcDd]",
                "Special report IDs (debug/heartbeat/telemetry) documented",
            ),
        ],
    },
    "DRV-010": {
        "name": "DEFAULT_MAX_PACKET_SIZE Per-Protocol",
        "skill": "driver",
        "assertions": [
            (
                "contains",
                "driver",
                r"MAX_PACKET_SIZE|max.packet|default.*packet",
                "DEFAULT_MAX_PACKET_SIZE per-protocol documented",
            ),
        ],
    },
    # =========================================================================
    # DBG — Debug & Triage
    # =========================================================================
    "DBG-001": {
        "name": "Debug Playbooks Exist",
        "skill": "debug",
        "assertions": [
            ("contains", "debug", r"playbook|Playbook", "Debug playbooks documented"),
        ],
    },
    "DBG-002": {
        "name": "HSDES Sighting References",
        "skill": "debug",
        "assertions": [
            ("contains", "debug", r"HSDES|hsdes|sighting", "HSDES sighting references"),
        ],
    },
    "DBG-003": {
        "name": "Failure Signatures",
        "skill": "debug",
        "assertions": [
            (
                "contains",
                "debug",
                r"failure.*signature|signature|symptom",
                "Failure signatures documented",
            ),
        ],
    },
    "DBG-004": {
        "name": "Triage Flow",
        "skill": "debug",
        "assertions": [
            (
                "contains",
                "debug",
                r"triage|debug.*flow|systematic",
                "Triage flow documented",
            ),
        ],
    },
    "DBG-005": {
        "name": "WoT Debug Playbook",
        "skill": "debug",
        "assertions": [
            (
                "contains",
                "debug",
                r"WoT.*playbook|playbook.*WoT|Wake.on.Touch.*debug",
                "WoT debug playbook present",
            ),
        ],
    },
    "DBG-006": {
        "name": "WoT Cross-Reference",
        "skill": "debug",
        "assertions": [
            ("contains", "debug", r"fv-thc/wot", "WoT skill cross-reference in debug"),
        ],
    },
    "DBG-007": {
        "name": "Known RTL Bugs",
        "skill": "debug",
        "assertions": [
            (
                "contains",
                "debug",
                r"RTL.*bug|bug.*RTL|errata|workaround",
                "Known RTL bugs documented",
            ),
        ],
    },
    "DBG-008": {
        "name": "Linux dynamic_debug",
        "skill": "debug",
        "assertions": [
            (
                "contains",
                "debug",
                r"dynamic_debug",
                "dynamic_debug documented for Linux THC debug",
            ),
        ],
    },
    "DBG-009": {
        "name": "Linux ftrace THC functions",
        "skill": "debug",
        "assertions": [
            (
                "contains",
                "debug",
                r"ftrace|set_ftrace_filter",
                "ftrace documented for THC function tracing",
            ),
        ],
    },
    "DBG-010": {
        "name": "Linux dmesg signature patterns",
        "skill": "debug",
        "assertions": [
            (
                "contains",
                "debug",
                r"dmesg.*pattern|signature.*pattern|probe.*success|probe.*fail",
                "dmesg signature patterns documented",
            ),
        ],
    },
    "DBG-011": {
        "name": "Linux sysfs and PCI entries",
        "skill": "debug",
        "assertions": [
            (
                "contains",
                "debug",
                r"sysfs|/sys/bus/pci|runtime_status",
                "sysfs PCI entries documented for THC debug",
            ),
        ],
    },
    "DBG-012": {
        "name": "Linux evtest and touch event analysis",
        "skill": "debug",
        "assertions": [
            (
                "contains",
                "debug",
                r"evtest|touch.*event|input.*event",
                "evtest / touch event analysis documented",
            ),
        ],
    },
    # =========================================================================
    # WOT — Wake-on-Touch (Architecture-corrected rev2.0)
    # =========================================================================
    "WOT-001": {
        "name": "UGD/PGD Power Domains (Runtime vs Platform Wake)",
        "skill": "wot",
        "assertions": [
            ("contains", "wot", r"UGD|un.?gated", "UGD (un-gated domain) documented"),
            (
                "contains",
                "wot",
                r"PGD|power.?gat",
                "PGD (power-gated domain) documented",
            ),
            (
                "contains",
                "wot",
                r"runtime.*interrupt|D0i2.*wake|interrupt.*routing",
                "UGD role clarified as runtime D0i2 interrupt routing",
            ),
        ],
    },
    "WOT-002": {
        "name": "GPIO Wake Configuration",
        "skill": "wot",
        "assertions": [
            (
                "contains",
                "wot",
                r"GPIO.*wake|wake.*GPIO",
                "GPIO wake configuration documented",
            ),
        ],
    },
    "WOT-003": {
        "name": "WoT Entry/Exit Flows",
        "skill": "wot",
        "assertions": [
            (
                "contains",
                "wot",
                r"entry.*flow|exit.*flow|WoT.*entry|WoT.*exit",
                "WoT entry/exit flows documented",
            ),
        ],
    },
    "WOT-004": {
        "name": "ACPI _DSM for WoT",
        "skill": "wot",
        "assertions": [
            ("contains", "wot", r"ACPI|_DSM|DSM", "ACPI DSM for WoT documented"),
        ],
    },
    "WOT-005": {
        "name": "GPIO IP Wake Path (Not THC UGD)",
        "skill": "wot",
        "assertions": [
            (
                "contains",
                "wot",
                r"GPIO\s*IP|vGPIO|virtual\s*GPIO",
                "Wake path through GPIO IP/vGPIO documented",
            ),
            (
                "contains",
                "wot",
                r"WAKE.*No|PME.*No|cannot.*generate.*wake",
                "THC PCI WAKE=No/PME=No documented",
            ),
        ],
    },
    "WOT-006": {
        "name": "WoG Not POR Status",
        "skill": "wot",
        "assertions": [
            (
                "contains",
                "wot",
                r"[Nn]ot\s*POR|NOT\s*POR|WoG.*[Nn]ot",
                "WoG Not POR status documented",
            ),
            (
                "contains",
                "wot",
                r"ISH|Integrated\s*Sensor\s*Hub",
                "WoG ISH architecture documented",
            ),
        ],
    },
    "WOT-007": {
        "name": "Windows WoT Extension INF",
        "skill": "wot",
        "assertions": [
            (
                "contains",
                "wot",
                r"Extension.*INF|WoT_Quick.*Extension",
                "Windows WoT Extension INF requirement documented",
            ),
        ],
    },
    "WOT-008": {
        "name": "WoT BIOS Knob",
        "skill": "wot",
        "assertions": [
            (
                "contains",
                "wot",
                r"BIOS.*[Kk]nob|Wake\s*on\s*Touch.*[Ee]nabled|THC\s*Configuration",
                "WoT BIOS enablement knob documented",
            ),
        ],
    },
    "WOT-009": {
        "name": "vGPIO Pad Locking (PADCFGLOCK)",
        "skill": "wot",
        "assertions": [
            ("contains", "wot", r"PADCFGLOCK", "PADCFGLOCK documented"),
            (
                "contains",
                "wot",
                r"PADCFGLOCK.*0x0|0x0.*PADCFGLOCK|unlocked",
                "PADCFGLOCK must be 0x0 (unlocked) for WoT",
            ),
            (
                "contains",
                "wot",
                r"15018635096",
                "HSD 15018635096 (NVL PADCFGLOCK) referenced",
            ),
        ],
    },
    "WOT-010": {
        "name": "HSDES WoT Sighting Knowledge",
        "skill": "wot",
        "assertions": [
            ("contains", "wot", r"15018635096", "HSD 15018635096 documented"),
            ("contains", "wot", r"16029769688", "HSD 16029769688 documented"),
            (
                "contains",
                "wot",
                r"16028429994",
                "HSD 16028429994 (BIOS fix) documented",
            ),
        ],
    },
    "WOT-011": {
        "name": "WCL IO APIC Wake Failure",
        "skill": "wot",
        "assertions": [
            ("contains", "wot", r"IO\s*APIC|IOAPIC", "IO APIC wake issue documented"),
            ("contains", "wot", r"RTE84|RTE\s*84", "RTE84 mask bit failure documented"),
            (
                "contains",
                "wot",
                r"ForceIdleTimeout|0x3",
                "ForceIdleTimeout mitigation documented",
            ),
        ],
    },
    "WOT-012": {
        "name": "pinctrl-intel Wake Architecture",
        "skill": "wot",
        "assertions": [
            (
                "contains",
                "wot",
                r"pinctrl.intel",
                "pinctrl-intel wake architecture documented",
            ),
            (
                "contains",
                "wot",
                r"IRQCHIP_MASK_ON_SUSPEND",
                "IRQCHIP_MASK_ON_SUSPEND flag documented",
            ),
            (
                "contains",
                "wot",
                r"padcfg0|HOSTSW_OWN|GPI_IE|GPI_GPE_EN",
                "Pad config save/restore registers documented",
            ),
        ],
    },
    "WOT-013": {
        "name": "QuickI2C WoT Implementation",
        "skill": "wot",
        "assertions": [
            (
                "contains",
                "wot",
                r"quicki2c_gpios|quicki2c.*wake-on-touch",
                "QuickI2C GPIO mapping documented",
            ),
            (
                "contains",
                "wot",
                r"i2c_subip_regs_save|i2c_subip_regs_restore",
                "I2C sub-IP register save/restore for WoT documented",
            ),
            (
                "contains",
                "wot",
                r"freeze.*thaw|thaw.*freeze|freeze/thaw",
                "QuickI2C freeze/thaw PM callbacks documented",
            ),
            (
                "contains",
                "wot",
                r"0xA848|0xE348|0x4D48",
                "QuickI2C I2C Device IDs documented",
            ),
        ],
    },
    "WOT-014": {
        "name": "Linux WoT Driver Functions",
        "skill": "wot",
        "assertions": [
            (
                "contains",
                "wot",
                r"thc_wot_config",
                "thc_wot_config function documented in WoT skill",
            ),
            (
                "contains",
                "wot",
                r"thc_wot_unconfig",
                "thc_wot_unconfig function documented in WoT skill",
            ),
            (
                "contains",
                "wot",
                r"ZERO THC.*register|zero.*THC.*register",
                "Linux WoT writes zero THC registers documented",
            ),
        ],
    },
    "WOT-015": {
        "name": "Windows WoT Extension INF",
        "skill": "wot",
        "assertions": [
            (
                "contains",
                "wot",
                r"Extension.*INF|WoT_Quick",
                "Windows WoT Extension INF requirement documented",
            ),
            (
                "contains",
                "wot",
                r"EWOG|ExternalWakeOnGpio",
                "EWOG bit usage documented in WoT skill",
            ),
            (
                "contains",
                "wot",
                r"ARM_FOR_WAKE|ArmForWake",
                "ARM_FOR_WAKE TIC state documented in WoT skill",
            ),
        ],
    },
    "WOT-016": {
        "name": "WoT pinctrl-intel Architecture",
        "skill": "wot",
        "assertions": [
            (
                "contains",
                "wot",
                r"pinctrl.intel|PADCFGLOCK",
                "pinctrl-intel wake controller architecture documented",
            ),
            (
                "contains",
                "wot",
                r"vGPIO|virtual.*GPIO",
                "vGPIO wake path documented in WoT skill",
            ),
        ],
    },
    # =========================================================================
    # BWG — BIOS Writer Guide (Audit-derived)
    # =========================================================================
    "BWG-001": {
        "name": "BIOS Init Flow",
        "skill": "registers",
        "assertions": [
            (
                "contains",
                "registers",
                r"BIOS|SAI|CDC|init",
                "BIOS init/SAI/CDC documented in registers",
            ),
        ],
    },
    "BWG-002": {
        "name": "Port Config Scenarios",
        "skill": "platform",
        "assertions": [
            (
                "contains",
                "platform",
                r"port.*config|config.*scenario|BIOS.*policy",
                "Port config scenarios documented",
            ),
        ],
    },
    "BWG-003": {
        "name": "Function Disable Flow",
        "skill": "registers",
        "assertions": [
            (
                "contains",
                "registers",
                r"function.*disable|disable.*function|FD",
                "Function disable flow documented",
            ),
        ],
    },
    "BWG-004": {
        "name": "DEVRST Sequencing",
        "skill": "power",
        "assertions": [
            (
                "contains",
                "power",
                r"DEVRST|reset.*sequence|BIOS.*power",
                "DEVRST/reset sequencing documented",
            ),
        ],
    },
    "BWG-005": {
        "name": "THC_CFG_PCE Bits",
        "skill": "registers",
        "assertions": [
            (
                "contains",
                "registers",
                r"THC_CFG_PCE|PCE|power.*clock",
                "THC_CFG_PCE bits documented",
            ),
        ],
    },
    "BWG-006": {
        "name": "BIOS Lock Enable",
        "skill": "registers",
        "assertions": [
            (
                "contains",
                "registers",
                r"BIOS_LOCK|lock|security",
                "BIOS lock/security documented",
            ),
        ],
    },
    # =========================================================================
    # SwAS CROSS-CHECK ASSERTIONS (QuickSPI + QuickI2C SwAS v1.0)
    # =========================================================================
    "SWAS-001": {
        "name": "ACPI SPI Frequency Encoding",
        "skill": "hidspi",
        "assertions": [
            (
                "contains",
                "hidspi",
                r"011.*40\s*MHz|40\s*MHz.*011",
                "ACPI SPI frequency encoding 011=40MHz documented",
            ),
            (
                "contains",
                "hidspi",
                r"LimitPacketSize|limit.*packet.*size",
                "LimitPacketSize ACPI parameter documented",
            ),
        ],
    },
    "SWAS-002": {
        "name": "RXDMA2 Software Throttle Threshold",
        "skill": "hidspi",
        "assertions": [
            (
                "contains",
                "hidspi",
                r"THROTLE_THRESHOLD.*8|throttle.*8|8\s+free\s+buffer",
                "RXDMA2 throttle threshold of 8 free buffers documented",
            ),
        ],
    },
    "SWAS-003": {
        "name": "Quiesce Scenarios",
        "skill": "hidspi",
        "assertions": [
            (
                "contains",
                "hidspi",
                r"[Qq]uiesce",
                "Quiesce scenarios documented in HIDSPI",
            ),
            (
                "contains",
                "hidspi",
                r"during\s+reset|buffer\s+threshold|D0Exit",
                "Multiple quiesce trigger conditions documented",
            ),
        ],
    },
    "SWAS-004": {
        "name": "Unused-Errors (Write DMA / Fatal)",
        "skill": "hidspi",
        "assertions": [
            (
                "contains",
                "hidspi",
                r"[Uu]nused.error",
                "Write DMA and Fatal errors documented as Unused-errors",
            ),
        ],
    },
    "SWAS-005": {
        "name": "ISR Per-Vector Masking Divergence",
        "skill": "driver",
        "assertions": [
            (
                "contains",
                "driver",
                r"GBL_INT_EN|per.vector.*mask|Global.*IE",
                "ISR interrupt masking strategy documented",
            ),
            (
                "contains",
                "driver",
                r"HIDSPI.*NOT.*toggl|no.*GBL_INT_EN.*ISR|HIDI2C.*toggl",
                "SPI vs I2C interrupt masking divergence documented",
            ),
        ],
    },
    "SWAS-006": {
        "name": "IC_DMA_RDLR Constraint",
        "skill": "hidi2c",
        "assertions": [
            (
                "contains",
                "hidi2c",
                r"IC_DMA_RDLR|DMA_RDLR",
                "IC_DMA_RDLR register documented",
            ),
            (
                "contains",
                "hidi2c",
                r"RDLR.*7|DMA_RDLR.*7|7.*watermark",
                "IC_DMA_RDLR <= 7 constraint documented",
            ),
        ],
    },
    "SWAS-007": {
        "name": "I2C ECO Registry Keys",
        "skill": "hidi2c",
        "assertions": [
            (
                "contains",
                "hidi2c",
                r"DoNotWaitForResetResponse",
                "DoNotWaitForResetResponse ECO registry key documented",
            ),
            (
                "contains",
                "hidi2c",
                r"I2C_Max_Frame_Size|I2C_Int_Delay",
                "I2C frame size and interrupt delay ECO keys documented",
            ),
        ],
    },
    "SWAS-008": {
        "name": "RTD3 PRW ACPI Crash Workaround",
        "skill": "power",
        "assertions": [
            (
                "contains",
                "power",
                r"_PRW.*crash|PRW.*GPIO.*crash|PRW.*workaround",
                "RTD3 _PRW ACPI crash with GPIO workaround documented",
            ),
            (
                "contains",
                "power",
                r"_PS0.*_PS3|_DSW|_PS0/_PS3/_DSW",
                "_PS0/_PS3/_DSW replacement for _PRW documented",
            ),
        ],
    },
    "SWAS-009": {
        "name": "Bus Clear SDA/SCL Stuck Recovery",
        "skill": "hidi2c",
        "assertions": [
            (
                "contains",
                "hidi2c",
                r"[Bb]us\s+[Cc]lear|SDA.*stuck|SDA_STUCK",
                "I2C bus clear / SDA stuck recovery documented",
            ),
            (
                "contains",
                "hidi2c",
                r"Linux.*NOT.*bus.*clear|Linux.*not.*enable|Windows.*enable.*bus.*clear",
                "Bus clear Windows vs Linux divergence documented",
            ),
        ],
    },
    "SWAS-010": {
        "name": "Interrupt Servicing Delay",
        "skill": "hidi2c",
        "assertions": [
            (
                "contains",
                "hidi2c",
                r"1\s*ms.*PTL|PTL.*1\s*ms|fixed.*1\s*ms|interrupt.*servic.*delay",
                "Interrupt servicing delay (1ms PTL/WCL) documented",
            ),
        ],
    },
    "SWAS-011": {
        "name": "PRD Ring Initialization Rules",
        "skill": "dma",
        "assertions": [
            (
                "contains",
                "dma",
                r"TPCWP.*0x80|POINTER_WRAPAROUND|write.pointer.*0x80",
                "Write pointer init = TPCWP=0x80 (POINTER_WRAPAROUND) documented",
            ),
            (
                "contains",
                "dma",
                r"babble|0x00.*unused|unused.*0x00",
                "Unused PRD entries init to 0x00 for babble detection documented",
            ),
        ],
    },
    "SWAS-012": {
        "name": "STALL_READ_EN and SOO Interaction",
        "skill": "dma",
        "assertions": [
            (
                "contains",
                "dma",
                r"STALL_READ_EN|THC_STALL_READ",
                "THC_STALL_READ_EN documented",
            ),
            (
                "contains",
                "dma",
                r"SOO|[Ss]top.on.[Oo]verflow",
                "SOO (Stop-on-Overflow) interaction documented",
            ),
        ],
    },
    "SWAS-013": {
        "name": "RxDMA Channel Usage (RXDMA2 Primary)",
        "skill": "dma",
        "assertions": [
            (
                "contains",
                "dma",
                r"RxDMA1.*[Nn]ot\s+used|RXDMA1.*not\s+used|RxDMA2.*primary|RXDMA2.*primary",
                "RxDMA1 not used, RxDMA2 is primary for both HIDSPI and HIDI2C",
            ),
        ],
    },
    "SWAS-014": {
        "name": "D0Exit Quiesce Optimization",
        "skill": "power",
        "assertions": [
            (
                "contains",
                "power",
                r"skip.*quiesce|touch.*disabled|already.*disabled|lid\s+close|monitor\s+off",
                "D0Exit skip quiesce when touch already disabled documented",
            ),
        ],
    },
    "SWAS-015": {
        "name": "Performance Limit Delay",
        "skill": "dma",
        "assertions": [
            (
                "contains",
                "dma",
                r"perf_limit.*10.*[µu]s|10\s*[µu]s.*perf|performance.*limit.*delay",
                "TXDMA performance limit delay (perf_limit x 10us) documented",
            ),
        ],
    },
    "SWAS-016": {
        "name": "SmartFilter (Windows HIDI2C)",
        "skill": "dma",
        "assertions": [
            (
                "contains",
                "dma",
                r"SmartFilter|smart.filter|SMART_FILTER",
                "SmartFilter module documented in DMA context",
            ),
        ],
    },
    "SWAS-017": {
        "name": "P0582 Double Interrupt Pre-LNL",
        "skill": "debug",
        "assertions": [
            (
                "contains",
                "debug",
                r"P0582|double\s+interrupt|pre.LNL.*interrupt",
                "P0582 double interrupt pre-LNL workaround documented",
            ),
            (
                "contains",
                "debug",
                r"level.trigger.*first|level.*triggered.*workaround",
                "Level-triggered first interrupt workaround documented",
            ),
        ],
    },
    "SWAS-018": {
        "name": "Reset Timeout SPI vs I2C",
        "skill": "driver",
        "assertions": [
            (
                "contains",
                "driver",
                r"reset.*timeout|timeout.*reset|1.000\s*ms|5.000\s*ms",
                "Reset timeout values documented in driver skill",
            ),
        ],
    },
    "SWAS-019": {
        "name": "DMA Pause Timing Cross-Platform",
        "skill": "dma",
        "assertions": [
            (
                "contains",
                "dma",
                r"10\s*ms.*Linux|Linux.*10\s*ms|10\s*ms.*pause",
                "DMA pause timeout (Linux 10ms) documented",
            ),
            (
                "contains",
                "dma",
                r"1-second.*timeout|1s.*quiesce|Windows.*1.*timeout",
                "DMA pause timeout (Windows 1s) documented",
            ),
        ],
    },
    "SWAS-020": {
        "name": "SWDMA 14-Step Workflow",
        "skill": "dma",
        "assertions": [
            (
                "contains",
                "dma",
                r"14.step|14.Step|14-step",
                "SWDMA 14-step workflow sequence documented",
            ),
            (
                "contains",
                "dma",
                r"SwDmaActive|SWDMA.*exclusive|pause.*RXDMA.*before|exclusive.*access",
                "SWDMA exclusive access requirement documented",
            ),
        ],
    },
    # =========================================================================
    # SIM — Simics Pre-Silicon Validation (NEW: 2026-03-26)
    # =========================================================================
    "SIM-001": {
        "name": "DML Framework Documented",
        "skill": "simics",
        "assertions": [
            (
                "contains",
                "simics",
                r"DML|Device Modeling Language",
                "DML (Device Modeling Language) framework documented",
            ),
            ("contains", "simics", r"dml_1\.4|DML\s*1\.4", "DML version 1.4 mentioned"),
        ],
    },
    "SIM-002": {
        "name": "AutoDML Pipeline Documented",
        "skill": "simics",
        "assertions": [
            (
                "contains",
                "simics",
                r"AutoDML|auto.?DML|auto.?dml",
                "AutoDML automated model generation documented",
            ),
            (
                "contains",
                "simics",
                r"collateral.*json|IP-XACT|ipxact|RDL",
                "AutoDML input collateral formats documented",
            ),
        ],
    },
    "SIM-003": {
        "name": "Chassis PM Framework Documented",
        "skill": "simics",
        "assertions": [
            (
                "contains",
                "simics",
                r"Chassis.*PM|chassis.*pm|PMC.*sideband|pmclite",
                "Chassis PM framework or PMC sideband documented",
            ),
        ],
    },
    "SIM-004": {
        "name": "FV Strategy Phases Documented",
        "skill": "simics",
        "assertions": [
            (
                "contains",
                "simics",
                r"Phase\s*[1-3]|pre.?silicon.*strategy|Pre-Si.*Strategy",
                "FV strategy phases documented",
            ),
            (
                "contains",
                "simics",
                r"register.*checkout|config.*checkout|enumeration",
                "Register/config checkout strategy mentioned",
            ),
        ],
    },
    "SIM-005": {
        "name": "Gap Analysis G1-G37 Present",
        "skill": "simics",
        "assertions": [
            (
                "contains",
                "simics",
                r"G1[:\s]|G1\b.*gap|Gap\s*ID",
                "Gap analysis starts with G1",
            ),
            (
                "contains",
                "simics",
                r"G37|G3[5-7]",
                "Gap analysis includes late entries (G35+)",
            ),
            (
                "contains",
                "simics",
                r"P0|P1|P2|Critical|High|Medium",
                "Gap severity/priority levels documented",
            ),
        ],
    },
    "SIM-006": {
        "name": "SPI Transactor Model Documented",
        "skill": "simics",
        "assertions": [
            (
                "contains",
                "simics",
                r"SPI.*[Tt]ransactor|spi_transactor|VTC",
                "SPI transactor model documented",
            ),
            (
                "contains",
                "simics",
                r"opcode|0x0B|0x3B|0x6B|read.*opcode",
                "SPI opcodes documented in transactor context",
            ),
        ],
    },
    "SIM-007": {
        "name": "thc_vdm Model Documented",
        "skill": "simics",
        "assertions": [
            (
                "contains",
                "simics",
                r"thc_vdm|THC.*VDM|Virtual.*Device.*Model",
                "thc_vdm (Virtual Device Model) documented",
            ),
        ],
    },
    "SIM-008": {
        "name": "Touch Device Models Documented",
        "skill": "simics",
        "assertions": [
            (
                "contains",
                "simics",
                r"WACOM|Wacom|wacom|touch.*device.*model",
                "Touch device models (e.g., WACOM) documented",
            ),
        ],
    },
    "SIM-009": {
        "name": "SPARK Transactor Documented",
        "skill": "simics",
        "assertions": [
            (
                "contains",
                "simics",
                r"SPARK|spark.*transactor",
                "SPARK transactor documented",
            ),
        ],
    },
    "SIM-010": {
        "name": "Setup and Launch Commands Documented",
        "skill": "simics",
        "assertions": [
            (
                "contains",
                "simics",
                r"load-target|simlauncher|simics.*launch",
                "Simics launch commands documented",
            ),
            (
                "contains",
                "simics",
                r"pip install|simics.*install|setup.*environment",
                "Environment setup instructions documented",
            ),
        ],
    },
    "SIM-011": {
        "name": "Per-Platform Guide Present",
        "skill": "simics",
        "assertions": [
            (
                "contains",
                "simics",
                r"LNL|PTL|NVL|WCL|MTL",
                "Per-platform Simics guidance covers known platforms",
            ),
            (
                "contains",
                "simics",
                r"object.*path|thc0|thc1|pch.*thc",
                "THC object paths documented per platform",
            ),
        ],
    },
    "SIM-012": {
        "name": "S0ix PM Enabling Documented",
        "skill": "simics",
        "assertions": [
            (
                "contains",
                "simics",
                r"S0ix|s0ix|package.*[Cc].*state|Pkg.*C",
                "S0ix / package C-state enabling in Simics documented",
            ),
        ],
    },
    "SIM-013": {
        "name": "PythonSV SW-CI Integration Documented",
        "skill": "simics",
        "assertions": [
            (
                "contains",
                "simics",
                r"SW.?CI|sw.?ci|PythonSV.*Simics|namednodes.*simics",
                "PythonSV SW-CI integration documented",
            ),
        ],
    },
    "SIM-014": {
        "name": "THC IPSV Repository Documented",
        "skill": "simics",
        "assertions": [
            (
                "contains",
                "simics",
                r"IPSV|ipsv|ip.*silicon.*validation|pre.?silicon.*test",
                "THC IPSV (IP Silicon Validation) repository documented",
            ),
        ],
    },
    "SIM-015": {
        "name": "PRD/DMA Maestro Documented",
        "skill": "simics",
        "assertions": [
            (
                "contains",
                "simics",
                r"PRD.*[Mm]aestro|DMA.*[Mm]aestro|maestro",
                "PRD/DMA Maestro concept documented",
            ),
        ],
    },
    # =========================================================================
    # XREF — Cross-Reference Completeness (added by improvement iteration)
    # =========================================================================
    "XREF-001": {
        "name": "Registers See-Also References WoT",
        "skill": "registers",
        "assertions": [
            (
                "contains",
                "registers",
                r"fv-thc/wot|wot/SKILL|Wake.on.Touch",
                "Registers sub-skill cross-references WoT",
            ),
        ],
    },
    "XREF-002": {
        "name": "DMA See-Also References WoT",
        "skill": "dma",
        "assertions": [
            (
                "contains",
                "dma",
                r"fv-thc/wot|wot/SKILL|Wake.on.Touch",
                "DMA sub-skill cross-references WoT",
            ),
        ],
    },
    "XREF-003": {
        "name": "Platform See-Also References DMA",
        "skill": "platform",
        "assertions": [
            (
                "contains",
                "platform",
                r"fv-thc/dma|dma/SKILL|DMA arch",
                "Platform sub-skill cross-references DMA",
            ),
        ],
    },
    "XREF-004": {
        "name": "HIDSPI See-Also References Power",
        "skill": "hidspi",
        "assertions": [
            (
                "contains",
                "hidspi",
                r"fv-thc/power|power/SKILL|[Pp]ower [Mm]anagement",
                "HIDSPI sub-skill cross-references Power",
            ),
        ],
    },
    "XREF-005": {
        "name": "WoT Has See-Also Section",
        "skill": "wot",
        "assertions": [
            (
                "contains",
                "wot",
                r"## See Also",
                "WoT sub-skill has See Also section",
            ),
            (
                "contains",
                "wot",
                r"fv-thc/power|power/SKILL",
                "WoT See Also references power sub-skill",
            ),
            (
                "contains",
                "wot",
                r"fv-thc/registers|registers/SKILL",
                "WoT See Also references registers sub-skill",
            ),
        ],
    },
    # =========================================================================
    # VP — Validation Points Presence (added by improvement iteration)
    # =========================================================================
    "VP-001": {
        "name": "DMA Has Validation Points",
        "skill": "dma",
        "assertions": [
            (
                "contains",
                "dma",
                r"[Vv]alidation [Pp]oint",
                "DMA sub-skill contains validation points section",
            ),
        ],
    },
    "VP-002": {
        "name": "Registers Has Validation Points",
        "skill": "registers",
        "assertions": [
            (
                "contains",
                "registers",
                r"[Vv]alidation [Pp]oint",
                "Registers sub-skill contains validation points section",
            ),
        ],
    },
    "VP-003": {
        "name": "Platform Has Validation Points",
        "skill": "platform",
        "assertions": [
            (
                "contains",
                "platform",
                r"[Vv]alidation [Pp]oint",
                "Platform sub-skill contains validation points section",
            ),
        ],
    },
    "VP-004": {
        "name": "Driver Has Validation Points",
        "skill": "driver",
        "assertions": [
            (
                "contains",
                "driver",
                r"[Vv]alidation [Pp]oint",
                "Driver sub-skill contains validation points section",
            ),
        ],
    },
    "VP-005": {
        "name": "Debug Has Validation Points",
        "skill": "debug",
        "assertions": [
            (
                "contains",
                "debug",
                r"[Vv]alidation [Pp]oint",
                "Debug sub-skill contains validation points section",
            ),
            (
                "contains",
                "debug",
                r"VP-DBG-00[1-6]",
                "Debug sub-skill has numbered VP items (VP-DBG-001 through VP-DBG-006)",
            ),
        ],
    },
    "VP-006": {
        "name": "Simics Has Validation Points",
        "skill": "simics",
        "assertions": [
            (
                "contains",
                "simics",
                r"[Vv]alidation [Pp]oint",
                "Simics sub-skill contains validation points section",
            ),
            (
                "contains",
                "simics",
                r"VP-SIM-00[1-6]",
                "Simics sub-skill has numbered VP items (VP-SIM-001 through VP-SIM-006)",
            ),
        ],
    },
    # =========================================================================
    # CONSIST — Cross-Skill Consistency (added by improvement iteration)
    # =========================================================================
    "CONSIST-001": {
        "name": "PCE Offset Consistent 0xA2",
        "skill": "power",
        "assertions": [
            (
                "contains",
                "power",
                r"0xA2",
                "Power sub-skill uses authoritative PCE offset 0xA2",
            ),
        ],
    },
    "CONSIST-002": {
        "name": "SPI Base Clock 125 MHz Consistent",
        "skill": "hidspi",
        "assertions": [
            (
                "contains",
                "hidspi",
                r"125\s*MHz",
                "HIDSPI documents 125 MHz base clock (not 128 MHz)",
            ),
        ],
    },
    "CONSIST-003": {
        "name": "IC_CON Value 0x663 Consistent",
        "skill": "hidi2c",
        "assertions": [
            (
                "contains",
                "hidi2c",
                r"0x0?663",
                "HIDI2C documents IC_CON value 0x663",
            ),
        ],
    },
    "CONSIST-004": {
        "name": "Autosuspend 5000ms Consistent",
        "skill": "driver",
        "assertions": [
            (
                "contains",
                "driver",
                r"5000\s*ms|5000ms|5\s*second",
                "Driver documents 5000ms autosuspend delay",
            ),
        ],
    },
}


# =============================================================================
# RUNNER
# =============================================================================


def run_test(test_id: str, test_def: dict) -> list:
    """Run a single eval test and return findings."""
    findings = []
    for assertion in test_def["assertions"]:
        assert_type = assertion[0]
        skill_name = assertion[1]
        pattern = assertion[2]
        description = assertion[3] if len(assertion) > 3 else ""

        if assert_type == "contains":
            finding = assert_contains(skill_name, pattern, description)
        elif assert_type == "not_contains":
            finding = assert_not_contains(skill_name, pattern, description)
        elif assert_type == "value_match":
            expected = assertion[3]
            desc = assertion[4] if len(assertion) > 4 else ""
            finding = assert_value_match(skill_name, pattern, expected, desc)
        else:
            finding = Finding(
                check="unknown_assert",
                target=test_id,
                status="ERROR",
                message=f"Unknown assertion type: {assert_type}",
            )

        # Tag with test ID
        finding.check = f"{test_id}: {test_def['name']}"
        findings.append(finding)

    return findings


def run_all_tests(config: dict, category: str = None, test_id: str = None) -> Report:
    """Run all eval tests and return a Report."""
    report = Report(name="THC Self-Verify", version="1.0.0")

    for tid, tdef in sorted(EVAL_TESTS.items()):
        # Filter by category or test ID
        if test_id and tid != test_id:
            continue
        if category and not tid.startswith(category):
            continue

        logger.info(f"Running test: {tid}")
        try:
            findings = run_test(tid, tdef)
            report.findings.extend(findings)
        except Exception as e:
            report.findings.append(
                Finding(
                    check=f"{tid}: {tdef['name']}",
                    target="system",
                    status="ERROR",
                    message=f"Test failed: {e}",
                    severity="critical",
                )
            )

    return report


def main():
    parser = argparse.ArgumentParser(
        description="THC Self-Verify: Automated eval runner"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--category", type=str, help="Run only tests in this category (e.g., REG, SPI)"
    )
    parser.add_argument("--test", type=str, help="Run a specific test (e.g., REG-001)")
    parser.add_argument("--save", type=str, help="Save report to file")
    parser.add_argument("--list", action="store_true", help="List all available tests")
    args = parser.parse_args()

    if args.list:
        print(f"Available tests ({len(EVAL_TESTS)}):")
        for tid, tdef in sorted(EVAL_TESTS.items()):
            assertions_count = len(tdef["assertions"])
            print(
                f"  {tid:10s} | {tdef['skill']:12s} | {assertions_count} assertions | {tdef['name']}"
            )
        sys.exit(0)

    config = load_config()
    report = run_all_tests(config, category=args.category, test_id=args.test)

    if args.json:
        print(report.to_json())
    else:
        print(report.to_text())

    if args.save:
        report.save(args.save)
        logger.info(f"Report saved to {args.save}")

    # Exit code
    has_failures = any(f.status == "FAIL" for f in report.findings)
    sys.exit(1 if has_failures else 0)


if __name__ == "__main__":
    main()
