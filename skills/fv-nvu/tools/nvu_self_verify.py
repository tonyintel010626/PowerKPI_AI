#!/usr/bin/env python3
"""NVU Self-Verify — Content assertion tests for NVU skill files.

Runs structured assertion tests against NVU SKILL.md files to verify
that critical NVU-specific content (registers, power states, DMA, camera,
firmware, inference, etc.) is present and accurate.

Ported from thc_self_verify.py — adapted for NVU IP domain.
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nvu_self_common import (
    Finding,
    Report,
    load_config,
    read_skill,
    setup_logging,
)

logger = logging.getLogger("nvu_self_verify")

# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------


def assert_contains(
    skill_name: str,
    pattern: str,
    description: str,
    config: Optional[Dict] = None,
) -> Finding:
    """Assert that a skill file contains a regex pattern."""
    content_dict = read_skill(skill_name, config)
    combined = ""
    for key in ("skill", "linux", "windows"):
        val = content_dict.get(key)
        if val:
            combined += val + "\n"

    if not combined.strip():
        return Finding(
            check="verify_contains",
            target=f"fv-nvu/{skill_name}",
            status="ERROR",
            message=f"Could not read skill '{skill_name}'",
            severity="high",
        )

    if re.search(pattern, combined, re.IGNORECASE | re.MULTILINE):
        return Finding(
            check="verify_contains",
            target=f"fv-nvu/{skill_name}",
            status="PASS",
            message=description,
            severity="info",
        )
    else:
        return Finding(
            check="verify_contains",
            target=f"fv-nvu/{skill_name}",
            status="FAIL",
            message=f"MISSING: {description}",
            severity="high",
            details=f"Pattern not found: {pattern}",
        )


def assert_not_contains(
    skill_name: str,
    pattern: str,
    description: str,
    config: Optional[Dict] = None,
) -> Finding:
    """Assert that a skill file does NOT contain a regex pattern."""
    content_dict = read_skill(skill_name, config)
    combined = ""
    for key in ("skill", "linux", "windows"):
        val = content_dict.get(key)
        if val:
            combined += val + "\n"

    if not combined.strip():
        return Finding(
            check="verify_not_contains",
            target=f"fv-nvu/{skill_name}",
            status="ERROR",
            message=f"Could not read skill '{skill_name}'",
            severity="high",
        )

    if re.search(pattern, combined, re.IGNORECASE | re.MULTILINE):
        return Finding(
            check="verify_not_contains",
            target=f"fv-nvu/{skill_name}",
            status="FAIL",
            message=f"UNWANTED: {description}",
            severity="medium",
            details=f"Pattern should not appear: {pattern}",
        )
    else:
        return Finding(
            check="verify_not_contains",
            target=f"fv-nvu/{skill_name}",
            status="PASS",
            message=description,
            severity="info",
        )


def assert_value_match(
    skill_name: str,
    field_pattern: str,
    expected: str,
    description: str,
    config: Optional[Dict] = None,
) -> Finding:
    """Assert that a captured value matches expected."""
    content_dict = read_skill(skill_name, config)
    combined = ""
    for key in ("skill", "linux", "windows"):
        val = content_dict.get(key)
        if val:
            combined += val + "\n"

    if not combined.strip():
        return Finding(
            check="verify_value_match",
            target=f"fv-nvu/{skill_name}",
            status="ERROR",
            message=f"Could not read skill '{skill_name}'",
            severity="high",
        )

    match = re.search(field_pattern, combined, re.IGNORECASE | re.MULTILINE)
    if not match:
        return Finding(
            check="verify_value_match",
            target=f"fv-nvu/{skill_name}",
            status="FAIL",
            message=f"MISSING FIELD: {description}",
            severity="high",
            details=f"Pattern not found: {field_pattern}",
        )

    actual = match.group(1) if match.lastindex else match.group(0)
    if re.fullmatch(expected, actual.strip(), re.IGNORECASE):
        return Finding(
            check="verify_value_match",
            target=f"fv-nvu/{skill_name}",
            status="PASS",
            message=description,
            severity="info",
        )
    else:
        return Finding(
            check="verify_value_match",
            target=f"fv-nvu/{skill_name}",
            status="FAIL",
            message=f"MISMATCH: {description}",
            severity="high",
            details=f"Expected '{expected}', got '{actual.strip()}'",
        )


# ---------------------------------------------------------------------------
# Eval test definitions — NVU domain-specific
# ---------------------------------------------------------------------------

EVAL_TESTS: Dict[str, List[Dict]] = {
    # -----------------------------------------------------------------------
    # REGISTERS — NVU register map, offsets, bitfields
    # -----------------------------------------------------------------------
    "REG": [
        {
            "name": "REG-01: BAR0 size documented",
            "skill": "registers",
            "assertions": [
                ("contains", "registers", r"64\s*KB|65536|0x10000", "BAR0 is 64KB"),
            ],
        },
        {
            "name": "REG-02: Host IPC register base",
            "skill": "registers",
            "assertions": [
                (
                    "contains",
                    "registers",
                    r"0x8000[_\s]?0000|NVU2HOST|HOST2NVU",
                    "Host IPC base address documented",
                ),
            ],
        },
        {
            "name": "REG-03: IOSF2AXI bridge registers",
            "skill": "registers",
            "assertions": [
                (
                    "contains",
                    "registers",
                    r"IOSF2AXI|iosf.*axi|bridge.*register",
                    "IOSF2AXI bridge register section",
                ),
            ],
        },
        {
            "name": "REG-04: MSI support documented",
            "skill": "registers",
            "assertions": [
                (
                    "contains",
                    "registers",
                    r"MSI|WIRE2MSI|MSI_GEN",
                    "MSI interrupt support",
                ),
            ],
        },
        {
            "name": "REG-05: PCI vendor ID",
            "skill": "registers",
            "assertions": [
                (
                    "contains",
                    "registers",
                    r"0x8086|8086h|vendor.*intel",
                    "Intel vendor ID 0x8086",
                ),
            ],
        },
        {
            "name": "REG-06: No MSI-X documented",
            "skill": "registers",
            "assertions": [
                (
                    "contains",
                    "registers",
                    r"MSI-?X.*not|ENABLE_MSIX_CAP\s*=\s*0|no\s+MSI-?X",
                    "MSI-X not enabled",
                ),
            ],
        },
        {
            "name": "REG-07: PCI functions count",
            "skill": "registers",
            "assertions": [
                (
                    "contains",
                    "registers",
                    r"2\s*PCI\s*function|NUM_PCI_FUNCTIONS\s*=\s*2|FN0.*FN1",
                    "2 PCI functions",
                ),
            ],
        },
        {
            "name": "REG-08: SRAM ECC register",
            "skill": "registers",
            "assertions": [
                (
                    "contains",
                    "registers",
                    r"ECC|SECDED|error.*correct",
                    "SRAM ECC documented",
                ),
            ],
        },
        {
            "name": "REG-09: Private config space size",
            "skill": "registers",
            "assertions": [
                (
                    "contains",
                    "registers",
                    r"64\s*KB.*private|private.*64\s*KB|PVT\s*CFG",
                    "64KB private config space",
                ),
            ],
        },
        {
            "name": "REG-10: Power management register",
            "skill": "registers",
            "assertions": [
                (
                    "contains",
                    "registers",
                    r"PMCTL|PM.*register|power.*management.*reg",
                    "Power management register",
                ),
            ],
        },
    ],
    # -----------------------------------------------------------------------
    # INFERENCE — NPX6-1K NNA, VPX2 DSP, model loading
    # -----------------------------------------------------------------------
    "INF": [
        {
            "name": "INF-01: NPX6-1K architecture",
            "skill": "inference",
            "assertions": [
                (
                    "contains",
                    "inference",
                    r"NPX6.*1K|1024.*MAC|NPX6-1K",
                    "NPX6-1K NNA with 1024 MACs",
                ),
            ],
        },
        {
            "name": "INF-02: VPX2 DSP architecture",
            "skill": "inference",
            "assertions": [
                (
                    "contains",
                    "inference",
                    r"VPX2|ARC\s*VPX|VLIW.*SIMD",
                    "VPX2 DSP documented",
                ),
            ],
        },
        {
            "name": "INF-03: Supported neural network types",
            "skill": "inference",
            "assertions": [
                (
                    "contains",
                    "inference",
                    r"CNN|RNN|LSTM|Transformer",
                    "Supported NN types",
                ),
            ],
        },
        {
            "name": "INF-04: INT8 precision",
            "skill": "inference",
            "assertions": [
                (
                    "contains",
                    "inference",
                    r"INT8|int8|8[- ]?bit\s*integer",
                    "INT8 precision support",
                ),
            ],
        },
        {
            "name": "INF-05: Convolution accelerator",
            "skill": "inference",
            "assertions": [
                (
                    "contains",
                    "inference",
                    r"convolution|conv.*accel",
                    "Convolution accelerator",
                ),
            ],
        },
        {
            "name": "INF-06: Tensor accelerator",
            "skill": "inference",
            "assertions": [
                (
                    "contains",
                    "inference",
                    r"tensor.*accel|tensor.*process",
                    "Tensor accelerator",
                ),
            ],
        },
        {
            "name": "INF-07: VPX2 cache sizes",
            "skill": "inference",
            "assertions": [
                (
                    "contains",
                    "inference",
                    r"32\s*KB.*I\$|32\s*KB.*D\$|32KB\s*I-?cache|128\s*KB.*VCCM",
                    "VPX2 cache/VCCM sizes",
                ),
            ],
        },
        {
            "name": "INF-08: HS3x L1 controller",
            "skill": "inference",
            "assertions": [
                (
                    "contains",
                    "inference",
                    r"HS3x|L1.*controller|NNA.*controller",
                    "HS3x-based L1 controller",
                ),
            ],
        },
    ],
    # -----------------------------------------------------------------------
    # DMA — DesignWare AXI DMA Controller
    # -----------------------------------------------------------------------
    "DMA": [
        {
            "name": "DMA-01: DesignWare AXI DMA",
            "skill": "dma",
            "assertions": [
                (
                    "contains",
                    "dma",
                    r"DesignWare|DW.*AXI|AXI\s*DMA",
                    "DesignWare AXI DMA controller",
                ),
            ],
        },
        {
            "name": "DMA-02: 64-bit addressing",
            "skill": "dma",
            "assertions": [
                (
                    "contains",
                    "dma",
                    r"64[- ]?bit.*address|64-bit|address.*64",
                    "64-bit addressing support",
                ),
            ],
        },
        {
            "name": "DMA-03: Boot DMA vs runtime DMA",
            "skill": "dma",
            "assertions": [
                (
                    "contains",
                    "dma",
                    r"boot.*DMA|runtime.*DMA|paging.*DMA",
                    "Boot and runtime DMA modes",
                ),
            ],
        },
        {
            "name": "DMA-04: DMA version",
            "skill": "dma",
            "assertions": [
                (
                    "contains",
                    "dma",
                    r"v2\.00a|version.*2\.00",
                    "DMA controller version v2.00a",
                ),
            ],
        },
        {
            "name": "DMA-05: SRAM paging to DRAM",
            "skill": "dma",
            "assertions": [
                (
                    "contains",
                    "dma",
                    r"SRAM.*paging|paging.*DRAM|IMR.*paging|FW.*paging",
                    "SRAM-to-DRAM paging via DMA",
                ),
            ],
        },
        {
            "name": "DMA-06: Peripheral handshake",
            "skill": "dma",
            "assertions": [
                (
                    "contains",
                    "dma",
                    r"handshake|peripheral.*DMA|DMA.*peripheral",
                    "Peripheral handshake interface",
                ),
            ],
        },
        {
            "name": "DMA-07: DMA MISC logic",
            "skill": "dma",
            "assertions": [
                (
                    "contains",
                    "dma",
                    r"DMA.*MISC|MISC.*logic|misc.*dma",
                    "DMA MISC logic documented",
                ),
            ],
        },
    ],
    # -----------------------------------------------------------------------
    # POWER — Power states, clock gating, CRPM
    # -----------------------------------------------------------------------
    "PWR": [
        {
            "name": "PWR-01: D0i2 max power state",
            "skill": "power",
            "assertions": [
                ("contains", "power", r"D0i2|D0i2.*max", "D0i2 as maximum idle state"),
            ],
        },
        {
            "name": "PWR-02: No RTD3 support",
            "skill": "power",
            "assertions": [
                (
                    "contains",
                    "power",
                    r"no.*RTD3|not.*support.*RTD3|RTD3.*not",
                    "RTD3 not supported",
                ),
            ],
        },
        {
            "name": "PWR-03: VNN power domain",
            "skill": "power",
            "assertions": [
                (
                    "contains",
                    "power",
                    r"VNN|0\.75\s*V|vnn.*domain",
                    "VNN power domain (0.75V)",
                ),
            ],
        },
        {
            "name": "PWR-04: Chassis 2.2",
            "skill": "power",
            "assertions": [
                (
                    "contains",
                    "power",
                    r"Chassis\s*2\.2|chassis.*2\.2",
                    "Chassis 2.2 power architecture",
                ),
            ],
        },
        {
            "name": "PWR-05: CRPM documented",
            "skill": "power",
            "assertions": [
                (
                    "contains",
                    "power",
                    r"CRPM|clock.*reset.*power",
                    "CRPM (Clock Reset Power Manager)",
                ),
            ],
        },
        {
            "name": "PWR-06: PMC integration",
            "skill": "power",
            "assertions": [
                (
                    "contains",
                    "power",
                    r"PMC|power.*management.*controller",
                    "PMC integration documented",
                ),
            ],
        },
        {
            "name": "PWR-07: SRAM power management",
            "skill": "power",
            "assertions": [
                (
                    "contains",
                    "power",
                    r"SRAM.*power|SRAM.*retention|SRAM.*PM",
                    "SRAM power management",
                ),
            ],
        },
        {
            "name": "PWR-08: LTR reporting",
            "skill": "power",
            "assertions": [
                (
                    "contains",
                    "power",
                    r"LTR|latency.*tolerance",
                    "LTR (Latency Tolerance Reporting)",
                ),
            ],
        },
        {
            "name": "PWR-09: Lid-Closed state",
            "skill": "power",
            "assertions": [
                (
                    "contains",
                    "power",
                    r"[Ll]id[- ]?[Cc]losed|lid.*close",
                    "Lid-Closed power state",
                ),
            ],
        },
        {
            "name": "PWR-10: Clock gating",
            "skill": "power",
            "assertions": [
                (
                    "contains",
                    "power",
                    r"clock.*gat|CG|gated.*clock",
                    "Clock gating documented",
                ),
            ],
        },
    ],
    # -----------------------------------------------------------------------
    # DRIVER — Host driver interface, IPC, PCI enumeration
    # -----------------------------------------------------------------------
    "DRV": [
        {
            "name": "DRV-01: PCI enumeration",
            "skill": "driver",
            "assertions": [
                (
                    "contains",
                    "driver",
                    r"PCI|enumerat|BDF|bus.*device.*function",
                    "PCI enumeration documented",
                ),
            ],
        },
        {
            "name": "DRV-02: IPC mechanism",
            "skill": "driver",
            "assertions": [
                (
                    "contains",
                    "driver",
                    r"IPC|inter.*processor.*comm|HOST2NVU|NVU2HOST",
                    "IPC mechanism documented",
                ),
            ],
        },
        {
            "name": "DRV-03: BAR0 MMIO mapping",
            "skill": "driver",
            "assertions": [
                (
                    "contains",
                    "driver",
                    r"BAR0|MMIO|memory.*mapped",
                    "BAR0 MMIO mapping",
                ),
            ],
        },
        {
            "name": "DRV-04: Power management hooks",
            "skill": "driver",
            "assertions": [
                (
                    "contains",
                    "driver",
                    r"D3|suspend|resume|power.*state",
                    "Driver power management hooks",
                ),
            ],
        },
        {
            "name": "DRV-05: Firmware loading from driver",
            "skill": "driver",
            "assertions": [
                (
                    "contains",
                    "driver",
                    r"firmware.*load|FW.*load|download.*FW",
                    "Firmware loading documented",
                ),
            ],
        },
        {
            "name": "DRV-06: MSI interrupt handling",
            "skill": "driver",
            "assertions": [
                ("contains", "driver", r"MSI|interrupt|IRQ", "MSI interrupt handling"),
            ],
        },
        {
            "name": "DRV-07: RCiEP device type",
            "skill": "driver",
            "assertions": [
                (
                    "contains",
                    "driver",
                    r"RCiEP|Root.*Complex.*Integrated",
                    "RCiEP device type",
                ),
            ],
        },
    ],
    # -----------------------------------------------------------------------
    # PLATFORM — Reset, straps, fuses, BDF assignment
    # -----------------------------------------------------------------------
    "PLAT": [
        {
            "name": "PLAT-01: Strap configuration",
            "skill": "platform",
            "assertions": [
                (
                    "contains",
                    "platform",
                    r"strap|nvu_br_strap",
                    "Strap configuration documented",
                ),
            ],
        },
        {
            "name": "PLAT-02: Fuse configuration",
            "skill": "platform",
            "assertions": [
                (
                    "contains",
                    "platform",
                    r"fuse|fuse.*gate",
                    "Fuse configuration documented",
                ),
            ],
        },
        {
            "name": "PLAT-03: Reset sequence",
            "skill": "platform",
            "assertions": [
                (
                    "contains",
                    "platform",
                    r"reset|PLTRST|power.*on.*reset",
                    "Reset sequence documented",
                ),
            ],
        },
        {
            "name": "PLAT-04: BDF assignment",
            "skill": "platform",
            "assertions": [
                (
                    "contains",
                    "platform",
                    r"BDF|nvu_br_devfuncnum|bus.*number",
                    "BDF assignment documented",
                ),
            ],
        },
        {
            "name": "PLAT-05: TitanLake platform",
            "skill": "platform",
            "assertions": [
                (
                    "contains",
                    "platform",
                    r"Titan\s*Lake|TTL|PCD-?H",
                    "TitanLake platform reference",
                ),
            ],
        },
        {
            "name": "PLAT-06: IP configuration",
            "skill": "platform",
            "assertions": [
                (
                    "contains",
                    "platform",
                    r"IP.*config|configuration|integration",
                    "IP configuration documented",
                ),
            ],
        },
        {
            "name": "PLAT-07: SAI access control",
            "skill": "platform",
            "assertions": [
                (
                    "contains",
                    "platform",
                    r"SAI|access.*control|security",
                    "SAI access control",
                ),
            ],
        },
    ],
    # -----------------------------------------------------------------------
    # DEBUG — Debug interfaces, RAS, DTF trace
    # -----------------------------------------------------------------------
    "DBG": [
        {
            "name": "DBG-01: DTF trace",
            "skill": "debug",
            "assertions": [
                (
                    "contains",
                    "debug",
                    r"DTF|Debug\s*Trace\s*Fabric|trace.*fabric",
                    "DTF (Debug Trace Fabric)",
                ),
            ],
        },
        {
            "name": "DBG-02: VISA observability",
            "skill": "debug",
            "assertions": [
                ("contains", "debug", r"VISA|VISA2|observab", "VISA observability"),
            ],
        },
        {
            "name": "DBG-03: ECC error reporting",
            "skill": "debug",
            "assertions": [
                (
                    "contains",
                    "debug",
                    r"ECC|SECDED|error.*correct",
                    "ECC/SECDED error reporting",
                ),
            ],
        },
        {
            "name": "DBG-04: Watchdog timer",
            "skill": "debug",
            "assertions": [
                ("contains", "debug", r"watchdog|WDT|watch.*dog", "Watchdog timer"),
            ],
        },
        {
            "name": "DBG-05: MIPI SysT format",
            "skill": "debug",
            "assertions": [
                (
                    "contains",
                    "debug",
                    r"MIPI.*SysT|SysT|STP|system.*trace",
                    "MIPI SysT trace format",
                ),
            ],
        },
        {
            "name": "DBG-06: OCD debug via sTAP",
            "skill": "debug",
            "assertions": [
                (
                    "contains",
                    "debug",
                    r"OCD|sTAP|on[- ]?chip.*debug|JTAG",
                    "OCD debug interface",
                ),
            ],
        },
        {
            "name": "DBG-07: Telemetry",
            "skill": "debug",
            "assertions": [
                ("contains", "debug", r"telemetry|TELEM", "Telemetry documented"),
            ],
        },
        {
            "name": "DBG-08: MBIST",
            "skill": "debug",
            "assertions": [
                (
                    "contains",
                    "debug",
                    r"MBIST|memory.*BIST|built.*in.*self.*test",
                    "MBIST documented",
                ),
            ],
        },
    ],
    # -----------------------------------------------------------------------
    # CAMERA — MIPI-IF, USB camera, Altek ISP, MJPEG
    # -----------------------------------------------------------------------
    "CAM": [
        {
            "name": "CAM-01: MIPI CSI-2 interface",
            "skill": "camera",
            "assertions": [
                (
                    "contains",
                    "camera",
                    r"MIPI.*CSI|CSI-?2|C-?PHY|D-?PHY",
                    "MIPI CSI-2 interface",
                ),
            ],
        },
        {
            "name": "CAM-02: PHY sharing with IPU",
            "skill": "camera",
            "assertions": [
                (
                    "contains",
                    "camera",
                    r"PHY.*shar|IPU.*shar|shar.*PHY|shar.*IPU",
                    "PHY sharing with IPU",
                ),
            ],
        },
        {
            "name": "CAM-03: Altek CV-ISP",
            "skill": "camera",
            "assertions": [
                (
                    "contains",
                    "camera",
                    r"Altek|CV-?ISP|computer.*vision.*ISP",
                    "Altek CV-ISP documented",
                ),
            ],
        },
        {
            "name": "CAM-04: USB camera offload",
            "skill": "camera",
            "assertions": [
                (
                    "contains",
                    "camera",
                    r"USB.*camera|camera.*offload|XHCI.*camera",
                    "USB camera offload",
                ),
            ],
        },
        {
            "name": "CAM-05: MJPEG decoder",
            "skill": "camera",
            "assertions": [
                (
                    "contains",
                    "camera",
                    r"MJPEG|VC9000|NanoD|jpeg.*decode",
                    "MJPEG decoder (VC9000NanoD)",
                ),
            ],
        },
        {
            "name": "CAM-06: Synopsys CSI2 host controller",
            "skill": "camera",
            "assertions": [
                (
                    "contains",
                    "camera",
                    r"Synopsys.*CSI|CSI.*host.*controller",
                    "Synopsys CSI2 host controller",
                ),
            ],
        },
        {
            "name": "CAM-07: SIO component",
            "skill": "camera",
            "assertions": [
                (
                    "contains",
                    "camera",
                    r"SIO|stream.*IO|streaming",
                    "SIO streaming component",
                ),
            ],
        },
        {
            "name": "CAM-08: ISP features (AE, AWB, BLC)",
            "skill": "camera",
            "assertions": [
                (
                    "contains",
                    "camera",
                    r"AE|AWB|BLC|auto.*exposure|white.*balance|black.*level",
                    "ISP features",
                ),
            ],
        },
    ],
    # -----------------------------------------------------------------------
    # FIRMWARE — Boot ROM, secure boot, IPC, FW loading
    # -----------------------------------------------------------------------
    "FW": [
        {
            "name": "FW-01: Boot ROM",
            "skill": "firmware",
            "assertions": [
                (
                    "contains",
                    "firmware",
                    r"boot\s*ROM|ROM.*code|boot.*code",
                    "Boot ROM documented",
                ),
            ],
        },
        {
            "name": "FW-02: Secure boot",
            "skill": "firmware",
            "assertions": [
                (
                    "contains",
                    "firmware",
                    r"secure\s*boot|signature.*verif|SHA.*hash",
                    "Secure boot mechanism",
                ),
            ],
        },
        {
            "name": "FW-03: ESE authentication",
            "skill": "firmware",
            "assertions": [
                (
                    "contains",
                    "firmware",
                    r"ESE|authenticat|SVN.*check",
                    "ESE authentication",
                ),
            ],
        },
        {
            "name": "FW-04: IMR (Isolated Memory Region)",
            "skill": "firmware",
            "assertions": [
                (
                    "contains",
                    "firmware",
                    r"IMR|isolated.*memory|reserved.*memory",
                    "IMR memory region",
                ),
            ],
        },
        {
            "name": "FW-05: IPC protocol",
            "skill": "firmware",
            "assertions": [
                (
                    "contains",
                    "firmware",
                    r"IPC|inter.*processor|message.*protocol",
                    "IPC protocol documented",
                ),
            ],
        },
        {
            "name": "FW-06: FW loading lifecycle",
            "skill": "firmware",
            "assertions": [
                (
                    "contains",
                    "firmware",
                    r"FW.*load|firmware.*load|download.*sequence",
                    "FW loading lifecycle",
                ),
            ],
        },
        {
            "name": "FW-07: ROM bypass survivability",
            "skill": "firmware",
            "assertions": [
                (
                    "contains",
                    "firmware",
                    r"ROM.*bypass|bypass.*ROM|survivab|HSD.*15018614010",
                    "ROM bypass survivability",
                ),
            ],
        },
        {
            "name": "FW-08: Host IPC disabled post-boot",
            "skill": "firmware",
            "assertions": [
                (
                    "contains",
                    "firmware",
                    r"disabled.*post.*boot|post.*boot.*disable|RS0.*disable",
                    "Host IPC disabled post-boot",
                ),
            ],
        },
    ],
    # -----------------------------------------------------------------------
    # BIOS — BIOS requirements, init sequences, knobs
    # -----------------------------------------------------------------------
    "BIOS": [
        {
            "name": "BIOS-01: BIOS initialization flow",
            "skill": "bios",
            "assertions": [
                (
                    "contains",
                    "bios",
                    r"init.*flow|initialization|BIOS.*init|boot.*flow",
                    "BIOS init flow documented",
                ),
            ],
        },
        {
            "name": "BIOS-02: NVU enable/disable knob",
            "skill": "bios",
            "assertions": [
                (
                    "contains",
                    "bios",
                    r"enable.*disable|NVU.*enable|device.*enable|DEVEN",
                    "NVU enable/disable knob",
                ),
            ],
        },
        {
            "name": "BIOS-03: Power-on reset requirements",
            "skill": "bios",
            "assertions": [
                (
                    "contains",
                    "bios",
                    r"power.*on|reset.*seq|PLTRST|cold.*reset",
                    "Power-on reset requirements",
                ),
            ],
        },
        {
            "name": "BIOS-04: Memory allocation (IMR/DRAM)",
            "skill": "bios",
            "assertions": [
                (
                    "contains",
                    "bios",
                    r"IMR|memory.*alloc|DRAM.*alloc|reserved.*memory",
                    "Memory allocation documented",
                ),
            ],
        },
        {
            "name": "BIOS-05: ACPI integration",
            "skill": "bios",
            "assertions": [
                ("contains", "bios", r"ACPI|_STA|_CRS|DSDT|SSDT", "ACPI integration"),
            ],
        },
        {
            "name": "BIOS-06: D3 post-FW-load behavior",
            "skill": "bios",
            "assertions": [
                (
                    "contains",
                    "bios",
                    r"D3.*post.*FW|post.*FW.*D3|SW.*function.*D3",
                    "D3 post-FW-load behavior",
                ),
            ],
        },
        {
            "name": "BIOS-07: BAR configuration",
            "skill": "bios",
            "assertions": [
                (
                    "contains",
                    "bios",
                    r"BAR.*config|BAR0|BAR1|base.*address.*register",
                    "BAR configuration",
                ),
            ],
        },
        {
            "name": "BIOS-08: Fuse gating control",
            "skill": "bios",
            "assertions": [
                (
                    "contains",
                    "bios",
                    r"fuse.*gat|soft.*disable|NVU_VSI9000",
                    "Fuse gating control",
                ),
            ],
        },
    ],
    # -----------------------------------------------------------------------
    # SIMICS — Pre-silicon simulation model (placeholder)
    # -----------------------------------------------------------------------
    "SIMICS": [
        {
            "name": "SIM-01: Simics placeholder status",
            "skill": "simics",
            "assertions": [
                (
                    "contains",
                    "simics",
                    r"[Pp]laceholder|PLACEHOLDER|[Ff]uture|[Pp]ending",
                    "Simics sub-skill marked as placeholder",
                ),
            ],
        },
        {
            "name": "SIM-02: Simics cross-references",
            "skill": "simics",
            "assertions": [
                (
                    "contains",
                    "simics",
                    r"fv-nvu|FV-NVU|NVU",
                    "Simics references parent NVU skill",
                ),
            ],
        },
    ],
}


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------


def run_test(
    test_def: Dict,
    config: Optional[Dict] = None,
) -> List[Finding]:
    """Run a single test (which may have multiple assertions)."""
    findings: List[Finding] = []
    test_name = test_def["name"]

    for assertion in test_def.get("assertions", []):
        assert_type = assertion[0]
        skill_name = assertion[1]
        pattern = assertion[2]
        desc = assertion[3] if len(assertion) > 3 else test_name

        try:
            if assert_type == "contains":
                finding = assert_contains(skill_name, pattern, desc, config)
            elif assert_type == "not_contains":
                finding = assert_not_contains(skill_name, pattern, desc, config)
            elif assert_type == "value_match":
                expected = assertion[4] if len(assertion) > 4 else ".*"
                finding = assert_value_match(
                    skill_name, pattern, expected, desc, config
                )
            else:
                finding = Finding(
                    check="verify_unknown",
                    target=f"fv-nvu/{skill_name}",
                    status="ERROR",
                    message=f"Unknown assertion type: {assert_type}",
                    severity="high",
                )
            findings.append(finding)
        except Exception as e:
            findings.append(
                Finding(
                    check="verify_exception",
                    target=f"fv-nvu/{skill_name}",
                    status="ERROR",
                    message=f"Exception in {test_name}: {e}",
                    severity="high",
                )
            )

    return findings


def run_all_tests(
    config: Optional[Dict] = None,
    category: Optional[str] = None,
    test_id: Optional[str] = None,
) -> Report:
    """Run all eval tests, optionally filtered by category or test ID."""
    report = Report(name="NVU Self-Verify", version="1.0")

    for cat_name, tests in EVAL_TESTS.items():
        if category and cat_name.upper() != category.upper():
            continue

        for test_def in tests:
            if test_id and test_id not in test_def["name"]:
                continue

            findings = run_test(test_def, config)
            report.findings.extend(findings)

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NVU Self-Verify — Content assertion tests"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--category", "-c", help="Run only tests in CATEGORY")
    parser.add_argument("--test", "-t", help="Run only test matching TEST id")
    parser.add_argument("--save", "-s", help="Save report to file")
    parser.add_argument("--list", "-l", action="store_true", help="List all tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()
    setup_logging("DEBUG" if args.verbose else "INFO")

    if args.list:
        for cat, tests in EVAL_TESTS.items():
            print(f"\n{'=' * 60}")
            print(f"Category: {cat} ({len(tests)} tests)")
            print(f"{'=' * 60}")
            for t in tests:
                print(f"  {t['name']}")
                for a in t.get("assertions", []):
                    print(f"    [{a[0]}] {a[1]}: {a[3] if len(a) > 3 else a[2]}")
        total = sum(len(t) for t in EVAL_TESTS.values())
        print(f"\nTotal: {total} tests across {len(EVAL_TESTS)} categories")
        return 0

    config = load_config()
    report = run_all_tests(config, args.category, args.test)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report.to_text())

    if args.save:
        report.save(Path(args.save))
        logger.info("Report saved to %s", args.save)

    return 0 if not report.has_failures else 1


if __name__ == "__main__":
    sys.exit(main())
