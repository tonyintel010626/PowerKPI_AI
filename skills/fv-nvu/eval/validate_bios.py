#!/usr/bin/env python3
"""
NVU BIOS Sub-Skill Validator (validate_bios.py)
================================================
Validates bios/SKILL.md against the NVU Requirements to BIOS source document
(Rev 0.8RC, March 2026, 18 REQs, 16 pages).

Categories:
  1. Header & Metadata
  2. Overview / Platform Connectivity
  3. Power Domain
  4. Firmware Architecture
  5. NVU SoC IDs
  6. Boot Flow
  7. REQ1: IMR Allocation
  8. REQ2: Enable/Disable IOC
  9. REQ3: Enable/Disable Menu
  10. REQ Numbering Gap
  11. REQ6: PCI Mode
  12. REQ7: Clock Gating (PMCTL)
  13. REQ8: HAE / SLEEP_EN
  14. REQ9: D0i3 Max Power Latency
  15. REQ10: IRQ Configuration
  16. REQ11: MSI Configuration
  17. REQ12-14: GPIO/I2C/VGPIO
  18. REQ15: VGPIO Configuration
  19. REQ16-17: RTD3 / Wake
  20. REQ18: IOMMU
  21. REQ19: UEFI Capsule
  22. REQ20: Camera Config (_DSM)
  23. BRP Table
  24. ACPI Configuration
  25. HSD Table
  26. Cross-References
  27. Validation Checklist
  28. Terminology
  29. Document References
  30. Audit Trail

Run:  python .opencode/skill/fv-nvu/eval/validate_bios.py
"""

import re
import sys
import os
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────
REPO_ROOT = (
    Path(__file__).resolve().parents[4]
)  # .opencode/skill/fv-nvu/eval/ -> parents[4] = repo root
BIOS_SKILL = REPO_ROOT / ".opencode" / "skill" / "fv-nvu" / "bios" / "SKILL.md"


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────
class ValidationResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []  # list of (category, check_name, passed, detail)

    def check(self, category: str, name: str, condition: bool, detail: str = ""):
        self.results.append((category, name, condition, detail))
        if condition:
            self.passed += 1
        else:
            self.failed += 1

    @property
    def total(self):
        return self.passed + self.failed

    def summary(self):
        cats = {}
        for cat, name, ok, detail in self.results:
            cats.setdefault(cat, {"pass": 0, "fail": 0})
            cats[cat]["pass" if ok else "fail"] += 1

        lines = ["\n" + "=" * 72]
        lines.append(
            f"  NVU BIOS Validator — {self.total} checks: "
            f"{self.passed} PASS, {self.failed} FAIL"
        )
        lines.append("=" * 72)

        for cat in sorted(cats.keys()):
            p, f = cats[cat]["pass"], cats[cat]["fail"]
            status = "✓" if f == 0 else "✗"
            lines.append(f"  {status}  {cat}: {p + f} checks ({p} pass, {f} fail)")

        if self.failed > 0:
            lines.append("\n--- FAILURES ---")
            for cat, name, ok, detail in self.results:
                if not ok:
                    lines.append(f"  FAIL [{cat}] {name}")
                    if detail:
                        lines.append(f"       {detail}")

        lines.append("=" * 72)
        pct = (self.passed / self.total * 100) if self.total else 0
        lines.append(f"  RESULT: {pct:.1f}% pass rate ({self.passed}/{self.total})")
        lines.append("=" * 72 + "\n")
        return "\n".join(lines)


def load_skill():
    if not BIOS_SKILL.exists():
        print(f"ERROR: {BIOS_SKILL} not found")
        sys.exit(1)
    return BIOS_SKILL.read_text(encoding="utf-8")


def has_text(content, text):
    """Case-sensitive substring check."""
    return text in content


def has_itext(content, text):
    """Case-insensitive substring check."""
    return text.lower() in content.lower()


def has_pattern(content, pattern):
    """Regex search (case-sensitive)."""
    return bool(re.search(pattern, content))


def count_pattern(content, pattern):
    """Count regex matches."""
    return len(re.findall(pattern, content))


# ──────────────────────────────────────────────────────────────────────
# Category validators
# ──────────────────────────────────────────────────────────────────────


def validate_header(content, v):
    cat = "01-Header"
    v.check(cat, "YAML frontmatter present", has_text(content, "name: fv-nvu/bios"))
    v.check(cat, "description present", has_text(content, "NVU BIOS requirements"))
    v.check(cat, "license MIT", has_text(content, "license: MIT"))
    v.check(cat, "source doc Rev 0.8RC", has_text(content, "Rev 0.8RC"))
    v.check(cat, "author Hemin Han", has_text(content, "Hemin Han"))
    v.check(cat, "18 REQs noted", has_text(content, "18 REQs"))
    v.check(cat, "16 pages noted", has_text(content, "16 pages"))
    v.check(cat, "domain lead blee9", has_itext(content, "blee9"))
    v.check(cat, "maintainer willychi", has_text(content, "willychi"))
    v.check(cat, "maintainer yleem", has_text(content, "yleem"))
    v.check(cat, "mobile-only note", has_itext(content, "mobile-only"))


def validate_overview_connectivity(content, v):
    cat = "02-Connectivity"
    v.check(cat, "IOSF Primary Fabric PSF6", has_text(content, "PSF6"))
    v.check(cat, "VC0d channel", has_text(content, "VC0d"))
    v.check(cat, "IPU P2P via NoC", has_itext(content, "NoC Crux"))
    v.check(cat, "xHCI-CAM offload", has_text(content, "xHCI-CAM"))
    v.check(cat, "ESE sideband", has_text(content, "ESE"))
    v.check(cat, "ISH sideband", has_text(content, "ISH"))
    v.check(cat, "PMC sideband", has_text(content, "PMC"))
    v.check(cat, "PCD-H die", has_text(content, "PCD-H"))
    v.check(cat, "VNN domain", has_text(content, "VNN"))


def validate_power_domain(content, v):
    cat = "03-PowerDomain"
    v.check(cat, "VNN IP", has_text(content, "VNN IP"))
    v.check(cat, "S0 and Modern Standby", has_text(content, "S0 and Modern Standby"))
    v.check(cat, "lid open S0i2.0", has_text(content, "S0i2.0"))
    v.check(cat, "lid closed S0i2.1 or S0i2.2", has_text(content, "S0i2.1 or S0i2.2"))
    v.check(
        cat, "NOT functional in Sx", has_text(content, "NOT functional in Sx states")
    )
    v.check(cat, "S3/S4/S5 mentioned", has_text(content, "S3/S4/S5"))


def validate_firmware_arch(content, v):
    cat = "04-FirmwareArch"
    v.check(cat, "three-stage FW model", has_text(content, "three-stage"))
    v.check(cat, "BUP 80 KB", has_text(content, "80 KB"))
    v.check(cat, "IMR 16 MB", has_text(content, "16 MB"))
    v.check(cat, "ESE authenticates", has_text(content, "ESE (SVN + signature)"))
    v.check(cat, "storage limit 20 KB", has_text(content, "20 KB"))
    # Check main content (before audit trail) doesn't claim CSME NVM partition
    main_content = (
        content.split("## AUDIT TRAIL")[0] if "## AUDIT TRAIL" in content else content
    )
    v.check(
        cat,
        "no CSME NVM partition claim",
        not has_text(main_content, "CSME NVM partition"),
        "Should not claim '20 KB (CSME NVM partition)' — source says only '20KB'",
    )
    v.check(cat, "ACPI scope NVUD", has_text(content, "\\_SB.PC00.NVUD"))


def validate_soc_ids(content, v):
    cat = "05-SoCIDs"
    v.check(
        cat, "Section 1.4 NVU SoC IDs exists", has_text(content, "### 1.4 NVU SoC IDs")
    )
    v.check(
        cat, "SB Port ID ref", has_itext(content, "TTL PCD IOSF Sideband Interface HAS")
    )
    v.check(cat, "SAI ref", has_itext(content, "TTL PCD Security HAS"))
    v.check(
        cat,
        "BDF/Device IDs ref",
        has_itext(content, "TTL PCD Register and Memory Mappings"),
    )


def validate_boot_flow(content, v):
    cat = "06-BootFlow"
    v.check(cat, "Step 1 power-on ROM", has_text(content, "Power-on"))
    v.check(cat, "Step 2 ESE loads BUP", has_text(content, "ESE loads"))
    v.check(cat, "Step 3 BUP waits for host", has_text(content, "BUP waits for host"))
    v.check(
        cat,
        "Step 3 communicates with NVU SW driver",
        has_text(content, "communicates with NVU SW driver"),
    )
    v.check(
        cat,
        "Step 4 BUP FW communicates with ESE",
        has_text(content, "NVU BUP FW communicates with ESE"),
    )
    v.check(cat, "Step 5 jumps to Base FW", has_text(content, "jumps to Base FW"))
    v.check(cat, "Step 6 executes App FW", has_text(content, "executes App FW"))
    v.check(cat, "Host IPC disabled post-boot", has_text(content, "disabled post-boot"))
    v.check(cat, "SVN rollback prevention", has_text(content, "SVN check"))


def validate_req1_imr(content, v):
    cat = "07-REQ1-IMR"
    v.check(cat, "REQ1 section exists", has_text(content, "### REQ1:"))
    v.check(cat, "IMR18", has_text(content, "IMR18"))
    v.check(cat, "16 MB size", has_text(content, "16 MB"))
    v.check(cat, "ESE splits IMR", has_text(content, "ESE splits IMR"))
    v.check(cat, "After DID timing", has_text(content, "After DID"))
    v.check(cat, "GET_IMR_SIZE request", has_text(content, "GET_IMR_SIZE"))
    v.check(
        cat,
        "non-allocation when disabled",
        has_itext(content, "shall not be allocated"),
    )
    v.check(cat, "HSD 13013571608", has_text(content, "13013571608"))
    v.check(cat, "HSD 18043973548", has_text(content, "18043973548"))


def validate_req2_ioc(content, v):
    cat = "08-REQ2-IOC"
    v.check(cat, "REQ2 section exists", has_text(content, "### REQ2:"))
    v.check(cat, "DEVEN[NVU_EN]", has_text(content, "DEVEN[NVU_EN]"))
    v.check(cat, "LPVS to PSF6 VC0d", has_text(content, "LPVS"))
    v.check(cat, "DWB usage context", has_text(content, "DWB"))
    v.check(cat, "CAPID[NVU]", has_text(content, "CAPID[NVU]"))
    v.check(cat, "CAPID[XHCI_CAM] pre-check", has_text(content, "CAPID[XHCI_CAM]"))
    v.check(cat, "DEVEN[XHCI_CAM_EN]", has_text(content, "DEVEN[XHCI_CAM_EN]"))
    v.check(
        cat,
        "fuse check STPG_FUSE_SS_DIS_RD_2",
        has_text(content, "STPG_FUSE_SS_DIS_RD_2"),
    )
    v.check(cat, "NVU_FUSE_SS_DIS bit", has_text(content, "NVU_FUSE_SS_DIS"))
    v.check(cat, "DEVEN locked log note", has_itext(content, "already locked"))
    v.check(cat, "IOC Programming reference", has_itext(content, "IOC Programming"))
    v.check(
        cat,
        "TTL North-South Interface HAS ref",
        has_itext(content, "North-South Interface HAS"),
    )
    v.check(cat, "HSD 16029834234", has_text(content, "16029834234"))
    v.check(cat, "HSD 22021790860", has_text(content, "22021790860"))
    v.check(cat, "HSD 14025737351", has_text(content, "14025737351"))


def validate_req3_menu(content, v):
    cat = "09-REQ3-Menu"
    v.check(cat, "REQ3 section exists", has_text(content, "### REQ3:"))
    v.check(cat, "menu option", has_itext(content, "menu option"))
    v.check(cat, "disable flow D3 PMCSR", has_text(content, "PMCSR[1:0] = 11b"))
    v.check(cat, "disable clear DEVEN", has_text(content, "clear DEVEN[NVU_EN]"))
    v.check(
        cat, "static PG check before set", has_itext(content, "already in Static PG")
    )
    v.check(cat, "ST_PG_FDIS_PMC_2", has_text(content, "ST_PG_FDIS_PMC_2"))
    v.check(cat, "NVU_FDIS_PMC bit", has_text(content, "NVU_FDIS_PMC"))
    v.check(cat, "global reset required", has_text(content, "global reset"))
    v.check(
        cat,
        "PMC applies during boot/reset justification",
        has_itext(content, "PMC only applies these settings during the boot/reset"),
    )
    v.check(
        cat, "enable flow clear static PG", has_text(content, "Clear static power gate")
    )
    v.check(
        cat,
        "pre-check fuse for both flows",
        has_itext(content, "applies to both enable and disable"),
    )


def validate_req_numbering_gap(content, v):
    cat = "10-REQGap"
    v.check(
        cat, "REQ numbering gap note exists", has_itext(content, "REQ numbering gap")
    )
    v.check(cat, "REQ4 mentioned", has_text(content, "REQ4"))
    v.check(cat, "REQ5 mentioned", has_text(content, "REQ5"))
    v.check(cat, "removed as of Rev 0.4", has_text(content, "removed as of Rev 0.4"))
    v.check(cat, "BAR1/FN1 mentioned", has_text(content, "BAR1/FN1"))
    v.check(cat, "Privacy LED mentioned", has_text(content, "Privacy LED"))


def validate_req6_pci(content, v):
    cat = "11-REQ6-PCI"
    v.check(cat, "REQ6 section exists", has_text(content, "### REQ6:"))
    v.check(cat, "BAR0 64 KB", has_text(content, "64 KB"))
    v.check(cat, "BAR1 4 KB", has_text(content, "4 KB"))
    v.check(cat, "BAR1 OS invisible", has_text(content, "OS invisible"))
    v.check(
        cat,
        "BAR1 bridge internal registers",
        has_itext(content, "Bridge internal registers"),
    )
    v.check(cat, "single-function PCI", has_text(content, "Single-function"))
    v.check(
        cat, "disabled UR or dropped", has_pattern(content, r"UR.*dropped|dropped.*UR")
    )
    v.check(cat, "SIP HAS 2 PCI functions note", has_text(content, "2 PCI functions"))


def validate_req7_pmctl(content, v):
    cat = "12-REQ7-PMCTL"
    v.check(cat, "REQ7 section exists", has_text(content, "### REQ7:"))
    v.check(cat, "PCR offset 0x1D0", has_text(content, "0x1D0"))
    v.check(cat, "PMCTL register name", has_text(content, "PMCTL"))
    v.check(cat, "6 clock gate bits", has_text(content, "6 clock gate"))
    v.check(cat, "bits [5:0]", has_text(content, "[5:0]"))
    v.check(cat, "reset 0x00", has_pattern(content, r"PMCTL.*0x00|0x00.*PMCTL"))
    v.check(cat, "recommended 0x3F", has_text(content, "0x3F"))
    # Sub-field names
    v.check(
        cat, "IOSF_SB_LOCAL_GATE_EN [5]", has_text(content, "IOSF_SB_LOCAL_GATE_EN")
    )
    v.check(
        cat, "IOSF_PRIM_LOCAL_GATE_EN [4]", has_text(content, "IOSF_PRIM_LOCAL_GATE_EN")
    )
    v.check(cat, "AXI_LOCAL_GATE_EN [3]", has_text(content, "AXI_LOCAL_GATE_EN"))
    v.check(
        cat, "IOSF_PRIM_TRUNK_GATE_EN [2]", has_text(content, "IOSF_PRIM_TRUNK_GATE_EN")
    )
    v.check(
        cat, "IOSF_SB_TRUNK_GATE_EN [1]", has_text(content, "IOSF_SB_TRUNK_GATE_EN")
    )
    v.check(cat, "AXI_TRUNK_GATE_EN [0]", has_text(content, "AXI_TRUNK_GATE_EN"))
    v.check(
        cat, "HW defaults disable CG/PG note", has_itext(content, "HW defaults disable")
    )
    v.check(
        cat,
        "power/SKILL.md cross-ref",
        has_text(content, "power/SKILL.md") or has_text(content, "fv-nvu/power"),
    )


def validate_req8_hae_sleep(content, v):
    cat = "13-REQ8-HAE"
    v.check(cat, "REQ8 section exists", has_text(content, "### REQ8:"))
    v.check(cat, "HAE bit 21", has_text(content, "HAE"))
    v.check(cat, "SLEEP_EN bit 19", has_text(content, "SLEEP_EN"))
    v.check(cat, "CFG offset 0xA0", has_text(content, "0xA0"))
    v.check(
        cat,
        "D0I3_MAX_POW_LAT_PG_CONFIG",
        has_text(content, "D0I3_MAX_POW_LAT_PG_CONFIG"),
    )
    v.check(cat, "IPAPG term used", has_text(content, "IPAPG"))
    v.check(
        cat,
        "IP Autonomous Power Gating",
        has_text(content, "IP Autonomous Power Gating"),
    )
    v.check(cat, "byte-level 0xA2h notation", has_text(content, "0xA2h"))
    v.check(cat, "0xA2h[5] = HAE", has_pattern(content, r"0xA2h\[5\].*HAE"))
    v.check(cat, "0xA2h[3] = SLEEP_EN", has_pattern(content, r"0xA2h\[3\].*SLEEP_EN"))


def validate_req9_latency(content, v):
    cat = "14-REQ9-Latency"
    v.check(cat, "REQ9 section exists", has_text(content, "### REQ9:"))
    v.check(cat, "POW_LAT_SCALE [12:10]", has_text(content, "POW_LAT_SCALE"))
    v.check(cat, "POW_LAT_VALUE [9:0]", has_text(content, "POW_LAT_VALUE"))
    v.check(
        cat, "scale reset 0x2", has_pattern(content, r"POW_LAT_SCALE.*0x2|Scale.*0x2")
    )
    v.check(
        cat,
        "scale recommended 0x7",
        has_pattern(content, r"POW_LAT_SCALE.*0x7|Scale.*0x7"),
    )
    v.check(cat, "value recommended 0x3FF", has_text(content, "0x3FF"))
    v.check(
        cat,
        "SW directed D0i3 not used",
        has_itext(content, "SW directed D0i3 is not used"),
    )


def validate_req10_irq(content, v):
    cat = "15-REQ10-IRQ"
    v.check(cat, "REQ10 section exists", has_text(content, "### REQ10:"))
    v.check(cat, "PCR offset 0x200", has_text(content, "0x200"))
    v.check(cat, "PCICFGCTR1 register", has_text(content, "PCICFGCTR1"))
    v.check(cat, "IPIN [11:8]", has_text(content, "IPIN"))
    v.check(cat, "IPIN default 0x1 INTA#", has_text(content, "INTA#"))
    v.check(cat, "ACPI_IRQ [19:12]", has_text(content, "ACPI_IRQ"))
    v.check(cat, "IRQ > 23", has_text(content, ">23"))
    v.check(cat, "[27:20] platform-specific", has_text(content, "[27:20]"))
    v.check(
        cat,
        "[27:20] not named IRQ secondary",
        not has_itext(content, "IRQ (secondary)"),
        "Should not invent name 'IRQ (secondary)' for [27:20] — source doesn't name it",
    )
    v.check(cat, "non-shareable IRQ", has_itext(content, "non-shareable"))
    v.check(cat, "recommended before BUP/FW loading", has_itext(content, "recommended"))


def validate_req11_msi(content, v):
    cat = "16-REQ11-MSI"
    v.check(cat, "REQ11 section exists", has_text(content, "### REQ11:"))
    v.check(cat, "DIS_MSI_CAP [29]", has_text(content, "DIS_MSI_CAP"))
    v.check(
        cat,
        "DIS_MSI_CAP=0 enabled",
        has_pattern(content, r"DIS_MSI_CAP.*=.*0.*enabled"),
    )
    v.check(
        cat,
        "DIS_MSI_CAP=1 disabled",
        has_pattern(content, r"DIS_MSI_CAP.*=.*1.*disabled"),
    )
    v.check(cat, "MSI-X not supported", has_text(content, "NOT MSI-X"))


def validate_req12_14_gpio(content, v):
    cat = "17-REQ12-14-GPIO"
    v.check(cat, "REQ12 section exists", has_text(content, "### REQ12:"))
    v.check(cat, "REQ13 section exists", has_text(content, "### REQ13:"))
    v.check(cat, "REQ14 section exists", has_text(content, "### REQ14:"))
    v.check(cat, "I2C pad Group Host ownership", has_text(content, "Group Host"))
    v.check(cat, "I2C do NOT lock", has_itext(content, "Do NOT lock"))
    v.check(cat, "I3C pad mode native", has_itext(content, "I3C"))
    v.check(cat, "GPIO PMode=0", has_text(content, "PMode = 0"))
    v.check(
        cat,
        "GPIO pad lock required",
        has_pattern(content, r"GPIO.*Lock.*PadCfgLock|GPIO.*Yes"),
    )
    v.check(
        cat, "GPIO pad Group Host ownership", has_pattern(content, r"GPIO.*Group Host")
    )
    v.check(cat, "VGPIO pad lock required", has_pattern(content, r"VGPIO.*Yes"))
    v.check(
        cat,
        "post-BIOS NVU FW controls PMode",
        has_itext(content, "NVU FW is responsible for controlling PMode"),
    )
    v.check(cat, "post-BIOS PMode fixed for GPIO", has_itext(content, "PMode is fixed"))
    v.check(cat, "HSD 16027548460", has_text(content, "16027548460"))
    v.check(cat, "HSD 16027080559", has_text(content, "16027080559"))


def validate_req15_vgpio(content, v):
    cat = "18-REQ15-VGPIO"
    v.check(cat, "REQ15 section exists", has_text(content, "### REQ15:"))
    v.check(cat, "16 Virtual GPIOs", has_text(content, "16 Virtual GPIO"))
    v.check(cat, "4 handshake channels", has_text(content, "4 handshake channels"))
    # VGPIO signal mapping (all 16)
    for i in range(8):
        v.check(cat, f"VGPIOx{i} GPIO Mode", has_text(content, f"VGPIOx{i}"))
    for i in range(8, 16):
        v.check(cat, f"VGPIOx{i} Native FN", has_text(content, f"VGPIOx{i}"))
    # NVU_GP mapping
    for i in range(8):
        v.check(cat, f"NVU_GP[{i}] mapping", has_text(content, f"NVU_GP[{i}]"))
    # Handshake signals
    v.check(cat, "release_req signals", has_text(content, "release_req"))
    v.check(cat, "release_ack signals", has_text(content, "release_ack"))
    # rxdata/txdata
    v.check(cat, "rxdata signal", has_text(content, "rxdata"))
    v.check(cat, "txdata signal", has_text(content, "txdata"))
    # Handshake flow diagram
    v.check(
        cat, "handshake flow diagram present", has_text(content, "Handshake complete")
    )
    v.check(cat, "interrupt from ack pins", has_text(content, "VGPIOx1/x3/x5/x7"))
    v.check(cat, "HSD 16029668165", has_text(content, "16029668165"))


def validate_req16_17_rtd3(content, v):
    cat = "19-REQ16-17-RTD3"
    v.check(cat, "REQ16 section exists", has_text(content, "### REQ16:"))
    v.check(cat, "REQ17 section exists", has_text(content, "### REQ17:"))
    v.check(cat, "PEP D3hot constraint", has_text(content, "D3hot"))
    v.check(cat, "_S0W returns 0x03", has_text(content, "0x03"))
    v.check(
        cat,
        "NOT true RTD3 note",
        has_itext(content, "NVU does NOT support true RTD3")
        or has_itext(content, "NVU does **NOT** support true RTD3"),
    )
    v.check(cat, "GPE1_NVU_PME_B0", has_text(content, "GPE1_NVU_PME_B0"))
    v.check(cat, "_L94 GPE handler", has_text(content, "_L94"))
    v.check(cat, "NVU_PME_B0_EN", has_text(content, "NVU_PME_B0_EN"))
    v.check(cat, "NVU_PME_B0_STS", has_text(content, "NVU_PME_B0_STS"))
    # 22-step RTD3 flow
    for step in range(1, 23):
        v.check(cat, f"RTD3 step [{step:03d}]", has_text(content, f"[{step:03d}]"))
    v.check(cat, "PME wake exception reset", has_itext(content, "exception reset"))
    v.check(cat, "PME wake lid transition", has_itext(content, "lid transition"))
    v.check(cat, "HOST_WAKEUP bit", has_text(content, "HOST_WAKEUP"))
    v.check(cat, "PME_STS bit", has_text(content, "PME_STS"))
    v.check(cat, "HSD 16028199143", has_text(content, "16028199143"))


def validate_req18_iommu(content, v):
    cat = "20-REQ18-IOMMU"
    v.check(cat, "REQ18 section exists", has_text(content, "### REQ18:"))
    v.check(
        cat,
        "DMA_CTRL_PLATFORM_OPT_IN_FLAG",
        has_text(content, "DMA_CTRL_PLATFORM_OPT_IN_FLAG"),
    )
    v.check(cat, "platform-wide note", has_itext(content, "not specific to NVU"))
    v.check(cat, "DesignWare AXI DMA ref", has_text(content, "DesignWare AXI DMA"))
    v.check(
        cat, "security threat model present", has_itext(content, "compromised NVU FW")
    )
    v.check(cat, "proxy access host memory", has_itext(content, "proxy"))
    v.check(cat, "OS kernel risk mentioned", has_itext(content, "OS kernel"))
    v.check(
        cat,
        "dma/SKILL.md cross-ref",
        has_text(content, "dma/SKILL.md") or has_text(content, "fv-nvu/dma"),
    )


def validate_req19_capsule(content, v):
    cat = "21-REQ19-Capsule"
    v.check(cat, "REQ19 section exists", has_text(content, "### REQ19:"))
    v.check(cat, "CSME FW package", has_text(content, "CSME FW package"))
    v.check(cat, "ESE sub-partition", has_text(content, "ESE sub-partition"))
    v.check(cat, "UEFI capsule mechanism", has_text(content, "UEFI capsule"))
    v.check(cat, "BUP only update scope", has_text(content, "BUP firmware only"))


def validate_req20_camera(content, v):
    cat = "22-REQ20-Camera"
    v.check(cat, "REQ20 section exists", has_text(content, "### REQ20:"))
    v.check(cat, "_DSM method", has_text(content, "_DSM"))
    v.check(cat, "HSD 15018922537", has_text(content, "15018922537"))
    v.check(cat, "IPU/NVU sync note", has_itext(content, "IPU and NVU"))
    v.check(cat, "subset of IPU configs", has_itext(content, "subset"))

    # ConfigGeneral
    v.check(cat, "ConfigGeneral section", has_text(content, "ConfigGeneral"))
    v.check(cat, "CameraHostMode 0=HW Hosted", has_text(content, "HW Hosted"))
    v.check(cat, "CameraHostMode 1=SW Hosted", has_text(content, "SW Hosted"))
    v.check(cat, "CameraHostMode XHCI_CAM visibility", has_itext(content, "XHCI_CAM"))
    v.check(cat, "CameraType 0=MIPI", has_pattern(content, r"CameraType.*0.*MIPI"))
    v.check(cat, "CameraType 1=USB Raw", has_pattern(content, r"1.*USB Raw"))
    v.check(cat, "CameraType 2=Hybrid", has_pattern(content, r"2.*Hybrid"))
    v.check(
        cat, "CameraType source doc range bug", has_itext(content, "source doc bug")
    )
    v.check(cat, "NvuEnable field", has_text(content, "NvuEnable"))
    v.check(cat, "TTL-H POR HW Hosted", has_text(content, "TTL-H POR"))

    # MipiConfig
    v.check(cat, "MipiConfig section", has_text(content, "MipiConfig"))
    v.check(
        cat,
        "MipiConfig validity condition",
        has_itext(content, "Valid only if CameraType is MIPI"),
    )
    v.check(
        cat,
        "SensorModel Char[16] manufacturer's part number",
        has_itext(content, "Manufacturer's part number"),
    )
    v.check(cat, "CameraModule Char[16]", has_text(content, "Char[16]"))
    v.check(cat, "PhyConfig 0=D-PHY 1=C-PHY", has_text(content, "D-PHY"))
    v.check(cat, "LinkUsed 0=PortA 1=PortB 2=PortC", has_text(content, "Port A"))
    v.check(cat, "LanesUsed 1-4", has_text(content, "1–4"))
    v.check(cat, "UseExtMclkSource", has_text(content, "UseExtMclkSource"))
    v.check(cat, "MCLK UINT32 Hz", has_text(content, "MCLK"))
    v.check(
        cat,
        "Rotation 0=none 1=180 2=90 3=270",
        has_text(content, "180°")
        and has_text(content, "90°")
        and has_text(content, "270°"),
    )
    v.check(
        cat,
        "PHY aggregation Port A only",
        has_itext(content, "only Port A can configure"),
    )

    # GPIO functions (23)
    gpio_functions = [
        (0, "GPIO_RESET"),
        (1, "GPIO_PWDN"),
        (2, "GPIO_STROBE"),
        (3, "GPIO_TORCH"),
        (4, "GPIO_FLASH"),
        (5, "GPIO_INDICATOR_REAR"),
        (6, "GPIO_INDICATOR_FRONT"),
        (7, "GPIO_POWER0"),
        (8, "GPIO_POWER1"),
        (9, "GPIO_STANDBY"),
        (10, "GPIO_WP"),
        (11, "GPIO_POWER_EN"),
        (12, "GPIO_MCLK"),
        (13, "GPIO_PRIVATE_LED"),
        (14, "GPIO_AF"),
        (15, "GPIO_IO"),
        (16, "GPIO_AVDD"),
        (17, "GPIO_CORE"),
        (18, "GPIO_HANDSHAKE"),
        (19, "GPIO_INT_IO"),
        (20, "GPIO_HDMI_DETECT"),
        (21, "GPIO_AON_HANDSHAKE_REQ"),
        (22, "GPIO_AON_HANDSHAKE_ACK"),
    ]
    for gid, gname in gpio_functions:
        v.check(cat, f"GPIO func {gid}={gname}", has_text(content, gname))

    # I2C config
    v.check(cat, "I2cSet section", has_text(content, "I2cSet"))
    v.check(cat, "I2C_GENERAL function 0", has_text(content, "I2C_GENERAL"))
    v.check(cat, "I2C_VCM function 1", has_text(content, "I2C_VCM"))
    v.check(cat, "I2C_EEPROM function 2", has_text(content, "I2C_EEPROM"))
    v.check(cat, "I2C speed 400 KHz fixed", has_text(content, "400 KHz"))

    # UsbRawConfig
    v.check(cat, "UsbRawConfig section", has_text(content, "UsbRawConfig"))
    v.check(
        cat,
        "UsbRawConfig validity condition",
        has_itext(content, "Valid only if CameraType is USB Raw"),
    )
    v.check(
        cat,
        "UsbRawConfig SensorModel manufacturer's part number",
        count_pattern(content, r"[Mm]anufacturer.s part number") >= 2,
        "Both MipiConfig and UsbRawConfig should use 'manufacturer's part number'",
    )


def validate_brp_table(content, v):
    cat = "23-BRP-Table"
    v.check(cat, "BRP section exists", has_text(content, "BIOS PROGRAMMING RECIPE"))
    # 8 BRP entries
    brp_entries = [
        ("PMCTL", "0x1D0", "[5:0]", "0x3F", "REQ7"),
        ("D0I3_MAX_POW_LAT_PG_CONFIG", "0xA0", "[12:10]", "0x7", "REQ9"),
        ("D0I3_MAX_POW_LAT_PG_CONFIG", "0xA0", "[9:0]", "0x3FF", "REQ9"),
        ("D0I3_MAX_POW_LAT_PG_CONFIG", "0xA0", "[19]", "0x1", "REQ8"),
        ("D0I3_MAX_POW_LAT_PG_CONFIG", "0xA0", "[21]", "0x1", "REQ8"),
        ("PCICFGCTR1", "0x200", "[11:8]", "0x1", "REQ10"),
        ("PCICFGCTR1", "0x200", "[19:12]", ">23", "REQ10"),
        ("PCICFGCTR1", "0x200", "[29]", "0x0", "REQ11"),
    ]
    for reg, off, bits, val, req in brp_entries:
        v.check(
            cat,
            f"BRP {reg} {bits}={val}",
            has_text(content, reg) and has_text(content, off),
        )
    v.check(cat, "Attr column exists (RW/O)", has_text(content, "RW/O"))
    v.check(cat, "POW_LAT_SCALE is RW/O", has_pattern(content, r"POW_LAT_SCALE.*RW/O"))
    v.check(cat, "POW_LAT_VALUE is RW/O", has_pattern(content, r"POW_LAT_VALUE.*RW/O"))
    v.check(cat, "combined 0x00281FFF", has_text(content, "0x00281FFF"))
    v.check(cat, "PCR access method IOSF SB", has_itext(content, "IOSF Sideband"))
    v.check(
        cat, "CFG access method PCI Config", has_itext(content, "PCI Configuration")
    )
    v.check(cat, "mask check formula", has_text(content, "0x00281FFF"))


def validate_acpi_config(content, v):
    cat = "24-ACPI"
    v.check(cat, "ACPI section exists", has_text(content, "## 4. ACPI"))
    v.check(cat, "ACPI scope SB.PC00", has_text(content, "\\_SB.PC00"))
    v.check(cat, "NVUD device", has_text(content, "NVUD"))
    v.check(cat, "_S0W method returns 0x03", has_pattern(content, r"_S0W.*0x03"))
    v.check(
        cat,
        "_PRW method with GPE1_NVU_PME_B0",
        has_pattern(content, r"_PRW.*GPE1_NVU_PME_B0"),
    )
    v.check(
        cat,
        "_PRW 0x04 ACPI convention note",
        has_itext(content, "ACPI convention") and has_text(content, "0x04"),
    )
    v.check(cat, "_L94 handler details", has_text(content, "_L94"))
    v.check(cat, "_L94 serialized attribute", has_itext(content, "serialized"))
    v.check(cat, "_L94 ADBG L94 Event", has_text(content, 'ADBG("L94 Event")'))
    v.check(cat, "_L94 CondRefOf guard", has_text(content, "CondRefOf"))
    v.check(cat, "_L94 Notify NVUD 0x02", has_text(content, "Notify(NVUD, 0x02)"))
    v.check(cat, "PEP integration section", has_text(content, "PEP"))
    v.check(cat, "DMAR table section", has_text(content, "DMAR"))
    v.check(
        cat,
        "DMA_CTRL_PLATFORM_OPT_IN_FLAG = 1",
        has_text(content, "DMA_CTRL_PLATFORM_OPT_IN_FLAG = 1"),
    )


def validate_hsd_table(content, v):
    cat = "25-HSD"
    v.check(cat, "HSD table section exists", has_text(content, "## 5. HSD"))
    hsds = [
        ("13013571608", "6.1"),
        ("18043973548", "6.1"),
        ("16029834234", "6.2"),
        ("22021790860", "6.2"),
        ("14025737351", "6.2"),
        ("16027548460", "6.7"),
        ("16027080559", "6.7"),
        ("16029668165", "6.7"),
        ("16028199143", "6.8"),
        ("15018922537", "6.11"),
    ]
    for hsd_id, section in hsds:
        v.check(cat, f"HSD {hsd_id} (Section {section})", has_text(content, hsd_id))
    v.check(cat, "10 HSDs total", count_pattern(content, r"HSD \d{11}") >= 10)


def validate_cross_refs(content, v):
    cat = "26-CrossRefs"
    v.check(
        cat, "cross-ref section exists", has_text(content, "## 6. CROSS-REFERENCES")
    )
    skill_refs = [
        ("power/SKILL.md", "fv-nvu/power"),
        ("registers/SKILL.md", "fv-nvu/registers"),
        ("camera/SKILL.md", "fv-nvu/camera"),
        ("firmware/SKILL.md", "fv-nvu/firmware"),
        ("driver/SKILL.md", "fv-nvu/driver"),
        ("platform/SKILL.md", "fv-nvu/platform"),
        ("dma/SKILL.md", "fv-nvu/dma"),
        ("debug/SKILL.md", "fv-nvu/debug"),
    ]
    for old_ref, new_ref in skill_refs:
        v.check(
            cat,
            f"cross-ref to {old_ref}",
            has_text(content, old_ref) or has_text(content, new_ref),
        )


def validate_checklist(content, v):
    cat = "27-Checklist"
    v.check(cat, "validation checklist exists", has_text(content, "## 7. VALIDATION"))
    v.check(cat, "config checkout tests", has_text(content, "7.1 Config Checkout"))
    v.check(cat, "enable/disable tests", has_text(content, "7.2 Enable/Disable"))
    v.check(cat, "power management tests", has_text(content, "7.3 Power Management"))
    # Key checklist items
    v.check(cat, "BAR0 64KB test", has_pattern(content, r"BAR0.*64 KB"))
    v.check(cat, "PMCTL 0x3F test", has_pattern(content, r"PMCTL.*0x3F"))
    v.check(cat, "HAE=1 test", has_pattern(content, r"HAE.*1"))
    v.check(cat, "SLEEP_EN=1 test", has_pattern(content, r"SLEEP_EN.*1"))
    v.check(cat, "ACPI_IRQ >23 test", has_pattern(content, r"ACPI_IRQ.*23"))
    v.check(cat, "DMAR flag test", has_pattern(content, r"DMAR.*ACPI"))
    v.check(
        cat,
        "16 config checkout items",
        count_pattern(content, r"\| \d+ \|.*\|.*\|.*\|") >= 16,
    )


def validate_terminology(content, v):
    cat = "28-Terminology"
    v.check(cat, "terminology section exists", has_text(content, "## 8. TERMINOLOGY"))
    terms = [
        "BUP",
        "CAPID",
        "DEVEN",
        "ESE",
        "GPE",
        "IMR",
        "IOC",
        "LPVS",
        "PadCfgLock",
        "PCR",
        "PEP",
        "PMode",
        "PME#",
        "PSF",
        "ST_PG_FDIS_PMC_2",
        "STPG_FUSE_SS_DIS_RD_2",
        "VGPIO",
        "_DSM",
        "_L94",
        "_PRW",
        "_S0W",
        "CCPAL/U",
        "DWB",
        "SSDB",
        "UCDB",
        "IOSF-NoC",
        "IPAPG",
        "SIO",
        "TTL",
        "UVOL",
    ]
    for term in terms:
        v.check(
            cat,
            f"term: {term}",
            has_text(content, f"| {term} |") or has_text(content, f"| **{term}** |"),
            f"Term '{term}' not found in terminology table",
        )


def validate_references(content, v):
    cat = "29-References"
    v.check(
        cat, "references section exists", has_text(content, "## 9. DOCUMENT REFERENCES")
    )
    v.check(cat, "38 documents note", has_text(content, "38 documents"))
    # Key reference categories
    v.check(
        cat,
        "NVU IP Specifications category",
        has_text(content, "NVU IP Specifications"),
    )
    v.check(
        cat,
        "TTL Platform Integration category",
        has_text(content, "TTL Platform Integration"),
    )
    v.check(cat, "Camera & Vision category", has_text(content, "Camera & Vision"))
    v.check(cat, "Security & FW category", has_text(content, "Security & FW"))
    v.check(cat, "Bus Protocols category", has_text(content, "Bus Protocols"))
    v.check(cat, "Power & Event category", has_text(content, "Power & Event"))
    v.check(cat, "Feature Tracking category", has_text(content, "Feature Tracking"))
    # Key individual references
    key_refs = [
        "SIP NVU HAS",
        "SIP NVU FAS",
        "SIP NVU SwAS",
        "SIP NVU SeAS",
        "TTL NVU VNN Resource Management",
        "TTL IP Loading and IMR FAS",
        "TTL PCD-H NVU SoC Integration HAS",
        "TTL North-South Interface HAS",
        "Camera Offload E2E HAS",
        "CSE Layout",
        "CSME Host Interface",
        "SIO Component HAS",
        "Scalable IO Specification",
        "General Purpose Event Handling",
        "InSys sharing CDPHY",
    ]
    for ref in key_refs:
        v.check(cat, f"ref: {ref}", has_itext(content, ref))
    # Count numbered references (should be 38+)
    num_refs = count_pattern(content, r"(?m)^\d+\.\s")
    v.check(
        cat,
        "at least 38 numbered refs",
        num_refs >= 38,
        f"Found {num_refs} numbered refs, expected >=38",
    )


def validate_audit_trail(content, v):
    cat = "30-AuditTrail"
    v.check(cat, "audit trail section exists", has_text(content, "## AUDIT TRAIL"))
    v.check(cat, "rev0.1 entry", has_text(content, "rev0.1"))
    v.check(cat, "rev0.2 entry", has_text(content, "rev0.2"))
    v.check(cat, "rev0.3 entry", has_text(content, "rev0.3"))
    v.check(cat, "rev0.4 entry", has_text(content, "rev0.4"))
    v.check(cat, "rev0.5 entry", has_text(content, "rev0.5"))
    v.check(
        cat,
        "rev0.5 mentions 100-iteration deep re-study",
        has_itext(content, "100-iteration deep re-study"),
    )
    v.check(cat, "rev0.5 mentions 42 findings", has_text(content, "42 findings"))


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────


def main():
    content = load_skill()
    v = ValidationResult()

    validate_header(content, v)
    validate_overview_connectivity(content, v)
    validate_power_domain(content, v)
    validate_firmware_arch(content, v)
    validate_soc_ids(content, v)
    validate_boot_flow(content, v)
    validate_req1_imr(content, v)
    validate_req2_ioc(content, v)
    validate_req3_menu(content, v)
    validate_req_numbering_gap(content, v)
    validate_req6_pci(content, v)
    validate_req7_pmctl(content, v)
    validate_req8_hae_sleep(content, v)
    validate_req9_latency(content, v)
    validate_req10_irq(content, v)
    validate_req11_msi(content, v)
    validate_req12_14_gpio(content, v)
    validate_req15_vgpio(content, v)
    validate_req16_17_rtd3(content, v)
    validate_req18_iommu(content, v)
    validate_req19_capsule(content, v)
    validate_req20_camera(content, v)
    validate_brp_table(content, v)
    validate_acpi_config(content, v)
    validate_hsd_table(content, v)
    validate_cross_refs(content, v)
    validate_checklist(content, v)
    validate_terminology(content, v)
    validate_references(content, v)
    validate_audit_trail(content, v)

    print(v.summary())
    return 0 if v.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
