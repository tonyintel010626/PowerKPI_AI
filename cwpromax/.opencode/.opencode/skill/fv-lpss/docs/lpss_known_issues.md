# LPSS Known Issues & Sighting Tracker

> **Last updated:** 2026-03-10
> **Scope:** I2C, I3C, SPI, UART on NVL (PCD-H, PCH-S) and PTL (PTL-H)
>
> This file tracks confirmed bugs, HSDES sightings, and known workarounds for LPSS IP validation.
> Format follows the FV structured issue tracker pattern for agent consumption.

---

## Issue Classification

| Prefix | Category | Description |
|--------|----------|-------------|
| BUG-xxx | RTL/IP Bug | Confirmed silicon or IP-level defect |
| HSDES-xxx | Sighting | Filed in HSDES with tracking ID |
| CONFIG-xxx | Configuration | BIOS/FW/driver misconfiguration that mimics a bug |
| KERN-xxx | OS/Driver Fix | Linux kernel or Windows driver patch |
| VJT-xxx | Test Framework | VJT/PythonSV framework issue (not silicon) |

---

## Critical RTL Bugs

### BUG-001: I3C DMA Abort Recovery Failure (DMAC_NO_CLEAR_CTRL_Q_ON_ABORT)

| Field | Value |
|-------|-------|
| **HSDES** | 18044213731 |
| **Severity** | Critical |
| **Affected IP** | DWC MIPI I3C (DMA mode) |
| **Affected Platforms** | NVL (PCD-H, PCH-S), PTL (PTL-H) — all steppings |
| **Root Cause** | Chicken bit register `gen_pvt_high_regrw4` bits[1:0] defaults to 3 in some steppings, causing DMA controller to NOT clear control queue on abort |
| **Symptoms** | (1) Subsequent transfers abort after first abort; (2) TID mismatch on responses; (3) BUS_ENABLE (HC_CONTROL bit31) stuck at 1 — cannot be cleared |
| **Workaround** | Set `gen_pvt_high_regrw4` bits[1:0] = 0 during I3C init (before BUS_ENABLE) |
| **VJT Status** | Workaround applied in `lpss_i3c.py` line ~136 for DMA mode |
| **Register Path (NVL)** | `socket0.pcd.lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_high_regrw4.gen_pvt_high_regrw4` |
| **Register Path (PTL)** | `socket0.soc.lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_high_regrw4.gen_pvt_high_regrw4` |
| **Verification** | Read chicken bit: if bits[1:0]==3 → buggy; if bits[1:0]==0 → safe |

**Quick Check:**
```python
cb = nn.sv.socket0.<die>.lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_private_configreg_top.gen_pvt_high_regrw4.gen_pvt_high_regrw4
val = cb.read()
print('DMAC_NO_CLEAR_CTRL_Q_ON_ABORT = %d' % (val & 3))
# 0 = safe (workaround applied), 3 = buggy
```

---

### BUG-002: I2C SDA Stuck Recovery May Miss in High-Speed Mode

| Field | Value |
|-------|-------|
| **HSDES** | TBD — under investigation |
| **Severity** | Medium |
| **Affected IP** | DW_apb_i2c (High-Speed 3.4 Mbps mode) |
| **Affected Platforms** | NVL (PCD-H) — observed on A0 stepping |
| **Root Cause** | IC_ENABLE bit[3] SDA_STUCK_RECOVERY (9 SCL clocks + STOP) may not reliably recover bus when operating at HS mode with clock stretching enabled |
| **Symptoms** | I2C bus remains stuck after SDA recovery attempt; subsequent transfers NACK |
| **Workaround** | Issue software reset via IC_ENABLE bit[0]=0 then re-enable, or reduce to Fast+ mode for recovery |
| **VJT Status** | Not yet automated — manual verification needed |

---

### BUG-003: I3C HDR Mode TX Underflow When TX_START_THLD Too Low

| Field | Value |
|-------|-------|
| **HSDES** | TBD — under investigation |
| **Severity** | High |
| **Affected IP** | DWC MIPI I3C (HDR-DDR, HDR-TSP modes) |
| **Affected Platforms** | NVL, PTL — all steppings (by design) |
| **Root Cause** | HDR modes have NO clock stalling — TX data must be pre-loaded before entering HDR. If TX_START_THLD is set too low, TX FIFO underflows causing HALT state |
| **Symptoms** | ERR_STATUS=0x6 (OVL_UFL) in response, controller enters HALT (PRESENT_STATE_DEBUG CM_TFR_ST_STATUS=0x13) |
| **Workaround** | Set TX_START_THLD high enough to pre-fill TX buffer before HDR entry. For small transfers, use IMMED_DATA command (CMD_ATTR=0x1) instead |
| **VJT Status** | Framework sets TX_START_THLD during init; value validated in config-checkout |

---

## HSDES Sightings

### HSDES-001: S0ix Blocked by LPSS Controller Stuck in D0

| Field | Value |
|-------|-------|
| **HSDES** | TBD |
| **Severity** | High |
| **Affected Platforms** | NVL (PCD-H) |
| **Description** | One or more LPSS controllers fail to enter D3 during OS idle, blocking S0ix entry. PMCSR reads 0x00 (D0) instead of 0x03 (D3) |
| **Root Cause** | Pending DMA transfer or uncleared interrupt prevents D3 transition |
| **Detection** | Read PMCSR (PCI+0x84) bits[1:0] for all LPSS controllers; any value != 0x3 blocks S0ix |
| **Resolution** | Clear pending interrupts, abort outstanding DMA, ensure driver releases controller |

### HSDES-002: UART Baud Rate Mismatch at 3.6864 MHz

| Field | Value |
|-------|-------|
| **HSDES** | TBD |
| **Severity** | Medium |
| **Affected Platforms** | NVL (PCD-H, PCH-S) |
| **Description** | UART max baud rate (3.6864 MHz) shows bit errors due to clock divider rounding |
| **Root Cause** | Input clock frequency and divisor combination doesn't produce exact 3.6864 MHz |
| **Workaround** | Use next-lower standard baud rate (1.8432 MHz or 921600) |
| **VJT Status** | Traffic tests default to 115200; high-baud tests should use validated rates only |

### HSDES-003: I3C DAA Fails When I2C Legacy Device Present on Bus

| Field | Value |
|-------|-------|
| **HSDES** | TBD |
| **Severity** | Medium |
| **Affected Platforms** | NVL, PTL |
| **Description** | ENTDAA CCC fails or assigns wrong addresses when I2C legacy devices are present on the same I3C bus |
| **Root Cause** | I2C devices may pull SDA during DAA, causing collision |
| **Detection** | HC_CONTROL bit[7] I2C_SLAVE_PRESENT must be set when I2C devices are on the bus |
| **Workaround** | Set I2C_SLAVE_PRESENT=1 in HC_CONTROL before issuing ENTDAA; use SETDASA for known addresses |

### HSDES-004: IOAPIC Interrupt Delivery Race Condition — GPIO Mode Stuck RTE (Clickpad/Touchpad Lost)

| Field | Value |
|-------|-------|
| **HSDES** | 14023171649 |
| **Related HSDES** | 22019075886 (Windows OS bug — IOAPIC RTE upper bits programmed before lower bits) |
| **Severity** | P1-Showstopper |
| **Status** | Root-Caused |
| **Affected Platforms** | LNL-MX (confirmed), NVL / PTL / TTL (potential — same ITSS/GPIO architecture) |
| **Description** | Clickpad/touchpad loses function after reboot. GPIO interrupt routed through IOAPIC becomes permanently stuck — no further interrupts delivered on the affected IRQ line |
| **Root Cause** | Race condition between GPIO `DEASSERT_IRQ` (IOSF-SB opcode 0x55) and ITSS `MSI_CMPL` during OS boot. When the GPIO driver clears `GPI_IS` while ITSS MSI send is still in-flight, `DEASSERT_IRQ` arrives at ITSS before `MSI_CMPL` completes, violating ITSS ordering rules. This causes `RTE_DS[N]` and `RTE_Rirr[N]` to get permanently stuck at 1 — no further interrupts on that IRQ |
| **Failure Signature** | `RTE_DS[N]==1 AND RTE_Rirr[N]==1 AND RTE_Mask[N]==0` while the GPIO line is deasserted. The IRQ is effectively dead despite being unmasked |
| **Affected Registers** | See `fv-lpss/config-checkout` — GPIO Interrupt Pad Registers and IOAPIC RTE Validation sections |
| **Detection** | Read ITSS internal state via PythonSV: `itss.icbi.imf.RTE_DS[N]` and `itss.icbi.imf.RTE_Rirr[N]`. If both are 1 while `RTE_Mask[N]==0` and GPIO `GPI_IS` is clear → race condition confirmed |
| **VISA Signals** | `pessbpmsgdec1/msg_visa[7:0]` (sideband opcodes), `itsssbmsigen1/visa_w2sbsm_ps[3:0]` (ITSS MSI state), `icbi/imf/CurrentState[1:0]` (ITSS IMF FSM), `gpcom_gpiirq_visa_gpcom_gpsb_gpi_req` (GPIO IRQ request) |
| **IOSF-SB Messages** | `ASSERT_IRQ` (0x54): GPIO→ITSS, `DEASSERT_IRQ` (0x55): GPIO→ITSS, `MSI MWr` (0x01): ITSS→P2SB, `MSI_CMPL`: P2SB→ITSS, `EOI`: Host→ITSS |
| **Workarounds** | (1) BIOS: Set `rxevcfg=0x2` (disabled) during init — OS enables when ready; (2) BIOS: Set `iosstate=0xF` on all interrupt-generating pads to prevent S0i2.2 glitches; (3) OS Driver: Use IOAPIC direct mode (`gpiroutioxapic=1`) where possible; (4) OS Driver: Fix `GPI_IS` clear ordering — ensure MSI completes before deasserting |
| **Silicon Fix** | ITSS HW should handle `DEASSERT_IRQ` arriving during `MSI_SEND` state gracefully (future silicon) |
| **VJT Status** | Not yet automated — manual PythonSV scripts available. See `fv-lpss/debug` Playbook 6 |
| **Cross-Ref** | `fv-lpss/debug` (Playbook 6), `fv-lpss/config-checkout` (GPIO Interrupt Pad Checks, IOAPIC RTE Validation), `fv-lpss/failure-analysis` (IOAPIC Interrupt Delivery Failures), [HTML Report](https://htmlpreview.github.io/?https://github.com/KongJiaWen/applications.ai.ocode.market.skills/blob/hsdes-14023171649-report/HSDES_14023171649_IOAPIC_Report.html) |

---

## Configuration Issues

### CONFIG-001: Pad Mode Not Set to Native Function

| Field | Value |
|-------|-------|
| **Severity** | High (causes total loss of function) |
| **Affected Platforms** | All (NVL, PTL) |
| **Description** | LPSS pins still in GPIO mode (PMode=0) instead of native function mode after BIOS |
| **Root Cause** | BIOS configuration missing or incorrect pad mux settings |
| **Detection** | `fv-lpss/config-checkout` — reads PMode for each LPSS pad; PMode=0 means GPIO (wrong) |
| **Resolution** | Update BIOS pad configuration or use PythonSV to override PMode for testing |

### CONFIG-002: BAR Not Assigned (Reads 0x00000000)

| Field | Value |
|-------|-------|
| **Severity** | High (blocks all register access) |
| **Affected Platforms** | All |
| **Description** | LPSS controller BAR reads 0x00000000 — no MMIO address assigned |
| **Root Cause** | PCI enumeration failed, device disabled in BIOS, or resource conflict |
| **Detection** | `fv-lpss/config-checkout` — reads BAR0 for each controller |
| **Resolution** | Check BIOS SerialIO device enable settings; verify no PCI resource conflicts |

### CONFIG-003: LPSS Clock Gating Not Enabled in PMC

| Field | Value |
|-------|-------|
| **Severity** | Medium (blocks D0i2/D0i3 power savings) |
| **Affected Platforms** | NVL |
| **Description** | PMC clock gate bits not enabled for LPSS controllers — clocks run continuously |
| **Root Cause** | PMC firmware or BIOS didn't enable LPSS CGPG |
| **Detection** | `fv-lpss/power-state` — reads PMC PGCB registers for clock gate status |
| **Resolution** | Verify PMC firmware version; check BIOS power management settings |

---

## VJT Framework Issues

### VJT-001: run_uart_traffic.py Port Discovery Fails on PCH-S

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Affected Platforms** | NVL PCH-S |
| **Description** | `run_uart_traffic.py` fails to find UART ports because `nvlh_cltap.py` is configured for PCD-H |
| **Root Cause** | Port configuration script hardcoded for PCD-H die |
| **Workaround** | Use `nvls_cltap.py` for PCH-S or modify the die selector in the script |

### VJT-002: I3C Test Scripts Missing from PTL Tree

| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Description** | `test_i3c_abort_recovery.py` exists only in NVL tree (`C:\pythonsv\novalake\vjt\lpss\`), not in PTL tree (`C:\pythonsv\pantherlake\vjt\lpss\`) |
| **Workaround** | Copy NVL test script to PTL tree and update PythonSV paths (`socket0.pcd` → `socket0.soc`) |

---

## HAS Documentation Issues

### DOC-001: I3C Core Clock Table Inconsistency in LPSS HAS v5.2

| Field | Value |
|-------|-------|
| **Severity** | Medium (informational — affects documentation accuracy, not silicon) |
| **HAS Revision** | v5.2 / Doc rev 1.02 (April 14, 2025) |
| **Description** | The HAS clock table (Section: Clocking) groups NVL with PTL/WCL at 100 MHz for `i3c_clk`, but the HAS revision history and a separate text paragraph state NVL uses 200 MHz |
| **Conflicting Data** | Clock table (L5794): "100 MHz for PTL/WCL/NVL, 200 MHz for all other SOCs" |
| **Authoritative Data** | Revision history (L878): "For NVL, LPSS IP is reused from PTL except the memory changes. I3C core clock frequency updated to 200MHz." Also L5829: "The POR clock freq for I3C core_clk is 200MHz for all SOCs except PTL which has 100 MHz" |
| **Supporting Evidence** | Revision L864 explicitly changed PTL/WCL to 100 MHz. Revision L878 explicitly updated NVL to 200 MHz. The clock table was not updated to reflect the NVL exception. |
| **Resolution** | Our skills use: PTL/WCL=100 MHz, NVL=200 MHz (per revision history, which is authoritative). Clock table likely has a documentation bug where NVL was copied from PTL grouping without updating. |
| **Recommended Action** | File HSDES documentation sighting against LPSS HAS to correct the clock table |

### DOC-002: LTR Register Naming Convention (CS_ prefix)

| Field | Value |
|-------|-------|
| **Severity** | Low (naming convention only — offsets are correct) |
| **Description** | Our skill files use `CS_ACTIVELTR` and `CS_IDLELTR` as register names. The HAS uses `ACTIVELTR_VALUE`/`IDLELTR_VALUE` (non-I3C) and `ACTIVELTR`/`IDLELTR` (I3C). The `CS_` prefix is Intel driver convention, not HAS nomenclature. |
| **Offsets (verified)** | Non-I3C: ACTIVELTR at BAR+0x210, IDLELTR at BAR+0x214. I3C: ACTIVELTR at BAR+0x2BC, IDLELTR at BAR+0x2C0. |
| **Decision** | Retain `CS_ACTIVELTR`/`CS_IDLELTR` naming across all skill files for consistency with driver code and PythonSV scripts. Add clarifying note that HAS uses different names. |

---

## OS/Driver Fixes

### KERN-001: SerialIO Driver Timeout on D3 Exit (Windows)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Description** | Windows IntelLpss.sys driver may timeout when resuming LPSS controllers from D3 if PMC power gate takes too long |
| **Resolution** | Update to latest IntelLpss.sys driver; verify PMC firmware is BKC-compliant |

---

## Search Keywords for HSDES

When searching for new LPSS sightings in HSDES, use these keyword combinations:

```
# General LPSS
"LPSS" AND ("NVL" OR "Novalake" OR "PTL" OR "PantherLake")
"SerialIO" AND ("D3" OR "S0ix" OR "clock gate" OR "power gate")

# I2C specific
"I2C" AND "LPSS" AND ("NACK" OR "timeout" OR "abort" OR "stuck")
"IC_TX_ABRT_SOURCE" AND ("NVL" OR "PTL")
"SDA stuck" AND "I2C"

# I3C specific
"I3C" AND ("abort" OR "BUS_ENABLE" OR "chicken" OR "DAA" OR "ENTDAA")
"DMAC_NO_CLEAR_CTRL_Q_ON_ABORT"
"gen_pvt_high_regrw4"
"TID mismatch" AND "I3C"
"HALT" AND "I3C" AND ("NVL" OR "PTL")

# SPI specific
"SPI" AND "LPSS" AND ("FIFO" OR "underrun" OR "DMA")

# UART specific
"UART" AND "LPSS" AND ("baud" OR "flow control" OR "loopback")
"HSUART" AND ("traffic" OR "timeout")

# Power management
"LPSS" AND ("D3" OR "D0i2" OR "D0i3" OR "CGPG" OR "S0ix" OR "LTR")
"PMC" AND "LPSS" AND ("clock gate" OR "power gate" OR "PGCB")

# GPIO / IOAPIC / ITSS interrupt delivery (HSDES-004)
"GPIO" AND ("IOAPIC" OR "ITSS") AND ("stuck" OR "race" OR "interrupt" OR "lost")
"DEASSERT_IRQ" OR "MSI_CMPL" OR "RTE_DS" OR "RTE_Rirr"
"GPI_IS" AND ("clear" OR "race" OR "ordering")
"clickpad" OR "touchpad" AND "lost function" AND "GPIO int mode"
"rxevcfg" OR "iosstate" OR "gpiroutioxapic" AND "interrupt"
```

---

## Filing New Sightings — BKM

When filing a new LPSS sighting in HSDES:

| Field | Recommended Value |
|-------|-------------------|
| **Tenant** | `client_platf_i_val` or relevant project tenant |
| **Subject** | `sighting` |
| **Domain** | `functional_validation` |
| **Component** | `lpss` or `serial_io` |
| **Title** | `[NVL/PTL] LPSS <I2C/I3C/SPI/UART>: <brief symptom>` |
| **Description** | Include: platform, stepping, BKC version, register dump, reproduction steps |
| **Attachments** | PythonSV register dumps, NGA test logs, traffic capture |

**Required information in description:**
1. Platform + die + stepping (e.g., NVL PCD-H A0)
2. Affected controller(s) (e.g., I3C Controller #1, ports I3C0/I3C1)
3. BKC version and PMC firmware version
4. Register dump (PMCSR, controller-specific regs, chicken bit if I3C)
5. Reproduction steps (PythonSV commands or test script name)
6. Expected vs actual behavior
7. Workaround if known
