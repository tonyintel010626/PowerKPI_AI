---
name: fv-audio/platform
version: "1.1.0"
owner: huiyingt
description: >-
  Per-platform Audio/ACE configuration data — die variants, Device IDs, BDF assignments,
  BAR layout, PythonSV namednode paths, DSP core counts, SoundWire segments, SRAM sizes,
  BIOS knobs, reset architecture, power domains, DMIC/SSP/HDA counts, AIOC/UAOL hardware
  configs, coupled/decoupled mode, fuse/strap tables, bring-up checklists, and
  platform-specific quirks across Intel Client SoC platforms (NVL, PTL, LNL, MTL, ARL, WCL, TTL, RZL).
---

# Audio/ACE Per-Platform Configuration Data

> **Purpose**: Single source of truth for platform-specific Audio/ACE hardware configuration.
> Load this sub-skill when answering questions about device IDs, BDF assignments, BAR sizes,
> PythonSV paths, BIOS knobs, die variants, DSP core counts, or any platform-specific
> audio configuration.

---

## ACE Version History

| ACE Version | Platforms | DSP Cores | SoundWire | DMIC | Key Feature |
|-------------|-----------|-----------|-----------|------|-------------|
| **ACE 1.5** | MTL, ARL | 3 HiFi4 + ANNA (SOC-M) / 2 HiFi4 + ANNA (PCH-S) | 4 links v1.2 | 2 PDM | Internal UAOL (MTL behind-hub bug) |
| **ACE 2.x** | LNL | 5 LX7 + HiFi4 + ANNA | 4 links v1.2 | 2 PDM | Single SOC die, internal UAOL |
| **ACE 3.0** | PTL, WCL | 5 LX7 + HiFi4 + ANNA | 5 links v1.2 | 2 PDM | PCD/PCH dual-die, internal UAOL |
| **ACE 3.0/4.0** | TTL | ACE 3.0: 5 LX7-HiFi4 / ACE 4.0: 4 HiFi5 | 5 links v1.2 | 2 PDM | Dual ACE option (fuse-selected); PCD-H, PCD-S dies |
| **ACE 4.x** | NVL, RZL | 4 HiFi5 HP + ULP (PCD-H) / 2 HiFi5 HP + ULP + ANNA (PCH-S) | 5 segments | PCD-H: **3 PDM** (6ch), others: 2 PDM (4ch) | Full UAOL (behind-hub ✅), AIOC (ALC712/ALC1320) |

---

## Die Type Mapping

All Audio/ACE instances are accessed via PythonSV namednode paths rooted at `namednodes.sv.socket0`.

| Platform | Die Type | Die Location | PythonSV Path | Namednode Shorthand |
|----------|----------|-------------|---------------|---------------------|
| NVL PCD-H | PCD (Primary Compute Die) | Compute tile | `namednodes.sv.socket0.pcd.ace` | `socket0.pcd.ace` |
| NVL PCH-S | PCH (Platform Controller Hub) | PCH chiplet | `namednodes.sv.socket0.pch.ace` | `socket0.pch.ace` |
| PTL | PCD / SOC | Compute tile | `namednodes.sv.socket0.soc.ace` | `socket0.soc.ace` |
| LNL | SOC (single die) | Monolithic SOC | `namednodes.sv.socket0.soc.ace` | `socket0.soc.ace` |
| MTL SOC-M | SOC | SOC tile | `namednodes.sv.socket0.soc.ace` | `socket0.soc.ace` |
| MTL PCH-S | PCH | PCH chiplet | `namednodes.sv.socket0.pch.ace` | `socket0.pch.ace` |
| ARL-U | PCH | PCH | `namednodes.sv.socket0.pch.ace` | `socket0.pch.ace` |
| ARL-S | PCH | PCH | `namednodes.sv.socket0.pch.ace` | `socket0.pch.ace` |
| WCL | PCD / SOC | Compute tile | `namednodes.sv.socket0.soc.ace` | `socket0.soc.ace` |
| TTL PCD-H | PCD (Primary Compute Die) | Compute tile | `namednodes.sv.socket0.pcd.ace` | `socket0.pcd.ace` |
| TTL PCD-S | PCD (S-series) | S-series die | `namednodes.sv.socket0.pcd.ace` | `socket0.pcd.ace` |
| RZL PCD-H | PCD (Primary Compute Die) | Compute tile | `namednodes.sv.socket0.pcd.ace` | `socket0.pcd.ace` |
| RZL PCD-S | PCD (S-series) | S-series die | `namednodes.sv.socket0.pcd.ace` | `socket0.pcd.ace` |
| RZL PCD-M | PCD (Mobile) | Mobile die | `namednodes.sv.socket0.pcd.ace` | `socket0.pcd.ace` |
| RZL PCD-W | PCD (Workstation) | Workstation die | `namednodes.sv.socket0.pcd.ace` | `socket0.pcd.ace` |

> **IMPORTANT**: Using the wrong die path is the #1 PythonSV bring-up mistake. If you get
> `AttributeError: 'NoneType' object has no attribute 'ace'`, you are using the wrong die
> for your platform. Cross-check against this table.

---

## Device ID Table

All Audio/ACE devices enumerate at **BDF 0:31:3** (Bus 0, Device 31, Function 3), VID = **0x8086**.

| Platform | Die | DID | DID Range | Class Code | Sub-Class |
|----------|-----|-----|-----------|------------|-----------|
| **NVL PCD-H** | PCD | **0xD328** | 0xD328–0xD32F | 0x04 (Multimedia) | 0x01 (Audio) |
| **NVL PCH-S** | PCH | **0xD228** | 0xD228–0xD22F | 0x04 | 0x01 |
| **MTL SOC-M** | SOC | **0x7E28** | 0x7E28–0x7E2F | 0x04 | 0x01 |
| **MTL PCH-S** | PCH | **0xAE28** | 0xAE28–0xAE2F | 0x04 | 0x01 |
| **PTL** | PCD | ⚠️ *UNVERIFIED* | — | 0x04 | 0x01 |
| **LNL** | SOC | ⚠️ *UNVERIFIED* | — | 0x04 | 0x01 |
| **ARL-U** | PCH | ⚠️ *UNVERIFIED* | — | 0x04 | 0x01 |
| **ARL-S** | PCH | ⚠️ *UNVERIFIED* | — | 0x04 | 0x01 |
| **WCL** | PCD | ⚠️ *UNVERIFIED (shares PTL)* | — | 0x04 | 0x01 |
| **TTL PCD-H** | PCD | **0xD228** ⚠️ | 0xD228–0xD22F | 0x04 | 0x01 |
| **TTL PCD-S** | PCD | **0xD228** ⚠️ | 0xD228–0xD22F | 0x04 | 0x01 |
| **RZL PCD-H** | PCD | **0xD328** ⚠️ | 0xD328–0xD32F | 0x04 | 0x01 |
| **RZL PCD-S/M/W** | PCD | **0xD328** ⚠️ | 0xD328–0xD32F | 0x04 | 0x01 |

> ⚠️ **TTL / RZL DID CAVEAT**: The DIDs above were obtained from Co-Design AI (April 2026)
> but overlap with NVL PCH-S (0xD228) and NVL PCD-H (0xD328) respectively. This may indicate
> shared silicon or a Co-Design conflation error. **Always verify against the HAS document
> for your specific stepping/SKU before relying on these values.** The low nibble (bits [2:0])
> of the DID differentiates SKU variants within each range.

> **DID = 0xFFFF** at BDF 0:31:3 means Audio/ACE is disabled in BIOS. Check the
> `AudioController` BIOS knob and the `FNCFG.ACED` fuse/register.

### DID Range Encoding

The low nibble of the DID (bits [2:0]) encodes the SKU/stepping variant within a platform.
The base DID (ending in `8`) is the primary silicon variant. Values `9`–`F` are reserved
for different steppings or SKU differentiation.

---

## BDF Assignment

**All platforms**: Audio/ACE is always at **Bus 0, Device 31, Function 3** (B0:D31:F3).

```
PCI Address: 0:31:3
  Bus      = 0x00
  Device   = 0x1F (31)
  Function = 0x03
```

This is a fixed assignment — Audio/ACE is an integrated PCH/SOC function and does not
participate in PCI bus enumeration or bridge assignment.

---

## BAR Layout

All Audio/ACE instances share the same BAR structure:

| BAR | Size | Purpose | Access Requirement |
|-----|------|---------|-------------------|
| **BAR0** (offset 0x10) | **512 KB** | HDA controller registers (CORB, RIRB, streams, GCTL, WAKEEN, STATESTS) | Always accessible after PCI enum |
| **BAR1** (offset 0x14) | **4 KB** | ACPI/PCI extension registers, additional config space | Always accessible after PCI enum |
| **BAR2** (offset 0x18) | **2 MB** | DSP registers, SRAM, FW load interface, IPC mailboxes | **Requires GPROCEN=1** (decoupled mode) |

### BAR Verification

```python
# PythonSV BAR check (adjust die path per platform table above)
ace = namednodes.sv.socket0.pcd.ace  # NVL PCD-H example

# BAR0 — must be non-zero
bar0 = ace.pcicfg.bar0.read()
print(f"BAR0 = 0x{bar0:08X}")  # Expect non-zero, 512KB aligned

# BAR1 — must be non-zero
bar1 = ace.pcicfg.bar1.read()
print(f"BAR1 = 0x{bar1:08X}")  # Expect non-zero, 4KB aligned

# BAR2 — non-zero ONLY if GPROCEN=1 (decoupled mode)
bar2 = ace.pcicfg.bar2.read()
print(f"BAR2 = 0x{bar2:08X}")  # 0 = coupled mode or GPROCEN not set
```

> **BAR0 = 0** means PCI BARs were not assigned. Check BIOS PCI resource allocation.
> **BAR2 = 0** in decoupled (SOF) mode means GPROCEN is not set — check BIOS `AudioDsp` knob.

---

## PCI Configuration Space Quick Reference

| Offset | Width | Register | Notes |
|--------|-------|----------|-------|
| 0x00 | 16-bit | VID | Always 0x8086 |
| 0x02 | 16-bit | DID | See Device ID Table |
| 0x04 | 16-bit | Command | Bit 1=Memory Space, Bit 2=Bus Master |
| 0x08 | 8-bit | RevID | Silicon stepping |
| 0x09 | 24-bit | Class Code | 0x040100 (Multimedia Audio Device) |
| 0x10 | 32-bit | BAR0 | HDA registers, 512 KB |
| 0x14 | 32-bit | BAR1 | ACPI/PCI ext, 4 KB |
| 0x18 | 32-bit | BAR2 | DSP registers, 2 MB (requires GPROCEN) |
| 0x84 | 32-bit | PMCSR | Power Management Control/Status |

---

## Coupled vs Decoupled Mode

Audio/ACE operates in one of two mutually exclusive modes:

| Mode | GPROCEN | Driver Model | BAR2 | DSP Access | Use Case |
|------|---------|-------------|------|-----------|----------|
| **Coupled** | 0 | MS HD Audio Class (hdaudbus.sys) | Not mapped (0) | No DSP access | Legacy HDA only |
| **Decoupled** | 1 (default) | Intel SOF / SST (intelaud.sys) | 2 MB mapped | Full DSP + FW load | Modern audio stack |

> **Default is Decoupled** (GPROCEN=1) on all modern platforms. Coupled mode is legacy
> and only used for basic HDA codec passthrough without DSP processing.

### Checking Mode

```python
# Check GPROCEN bit
gprocen = ace.hda.gctl.gprocen.read()
print(f"GPROCEN = {gprocen}")  # 1 = decoupled (normal), 0 = coupled (legacy)
```

---

## Per-Platform Configuration

### NVL PCD-H (ACE 4.x — Primary Compute Die)

| Property | Value |
|----------|-------|
| **DID** | 0xD328 (range D328–D32F) |
| **BDF** | 0:31:3 |
| **Die Path** | `socket0.pcd.ace` |
| **DSP Cores** | 4 HiFi5 HP + 1 ULP |
| **SRAM** | 4.5 MB |
| **SoundWire Segments** | 5 (all external on PCD-H). Seg 0: iDisp-A alt. Seg 2/3: up to 4 data lanes. Seg 4: external (up to 5 lanes) |
| **SSP/I2S** | 3 (SSP0 = BT HFP offload) |
| **DMIC** | 3 PDM (PDM0, PDM1, PDM2) = 6 channels (3×2ch) |
| **HDA SDI** | 2 |
| **UAOL** | ACE4 offload engine, behind-hub ✅ supported, enhanced FIFO (>1ms) |
| **AIOC** | Supported (ALC712 + ALC1320 on SoundWire Seg 2) |
| **iDisplay Audio** | Via SoundWire Seg 0 Alt or HDA SDI |

#### NVL PCD-H Key Differences from PCH-S
- More DSP cores (4 HP vs 2 HP)
- Larger SRAM (4.5 MB vs 2.25 MB)
- PDM2 DMIC available (3 vs 2 PDMs)
- Different iDisplay Audio routing path

---

### NVL PCH-S (ACE 4.x — PCH Chiplet)

| Property | Value |
|----------|-------|
| **DID** | 0xD228 (range D228–D22F) |
| **BDF** | 0:31:3 |
| **Die Path** | `socket0.pch.ace` |
| **DSP Cores** | 2 HiFi5 HP + 1 ULP + 1 ANNA |
| **SRAM** | 2.25 MB |
| **SoundWire Segments** | 5 (4 external + 1 on-die). Seg 4: on-die iDisp-A/CNVi alt. Seg 2/3: up to 4 data lanes |
| **SSP/I2S** | 3 (SSP0 = BT HFP offload) |
| **DMIC** | 2 PDM (PDM0, PDM1) = 4 channels (2×2ch) |
| **HDA SDI** | 2 |
| **UAOL** | ACE4 offload engine, behind-hub ✅ supported, enhanced FIFO (>1ms) |
| **AIOC** | Supported (ALC712 + ALC1320 on SoundWire Seg 2) |
| **iDisplay Audio** | Via on-die SoundWire Seg or HDA SDI |

#### NVL-S ERB DIP Switch Configuration (for AIOC)

To route SoundWire Segment 2 to the JE header for AIOC on the NVL-S ERB:

| Switch | Setting | Purpose |
|--------|---------|---------|
| SW9B2 | OFF-ON-OFF-ON | Routes SDW Seg 2 data to JE header |
| SW9C1 | OFF-ON-OFF-ON | Routes SDW Seg 2 clock to JE header |

#### NVL AIOC Hardware Requirements

| Component | Description | Connection |
|-----------|-------------|------------|
| **Base AIC** | 3PE Gen6 Audio Base AIOC kit (ALC712 + ALC1320) | JA→JA, JD→JD, JE→JE, JH→JH |
| **Transducer AIC** | 3PE AIOC GEN4.1 Transducer board | Mounts on Base AIC |
| **Subsystem ID** | 0x305610EC | Must match for driver binding |

> **Topology Selection**: ES vs MP topology selection is critical. Wrong topology causes
> silent enumeration failure — devices appear in SoundWire bus scan but audio routing fails.
> 5-Star config: ALC712-VB (combo codec) + ALC1320 (smart amp) on SoundWire Segment 2.

---

### PTL (ACE 3.0)

| Property | Value |
|----------|-------|
| **DID** | *(query CoDesign — HAS: ptlsm_ace3.x_integration_has.html)* |
| **BDF** | 0:31:3 |
| **Die Path** | `socket0.soc.ace` |
| **DSP Cores** | 5 LX7 + HiFi4 + ANNA |
| **SoundWire** | 5 links v1.2 |
| **SSP/I2S** | 3 |
| **DMIC** | 2 PDM |
| **UAOL** | ACE3 offload engine, behind-hub ✅ supported, ~1ms FIFO |
| **AIOC** | Not supported |

#### PTL-Specific Notes
- Dual-die (PCD/PCH) but ACE is on PCD/SOC side
- Shares ACE 3.x architecture with WCL
- HAS reference: `ptlsm_ace3.x_integration_has.html`

---

### LNL (ACE 2.x)

| Property | Value |
|----------|-------|
| **DID** | *(query CoDesign)* |
| **BDF** | 0:31:3 |
| **Die Path** | `socket0.soc.ace` |
| **DSP Cores** | 5 LX7 + HiFi4 + ANNA |
| **SoundWire** | 4 links v1.2 |
| **SSP/I2S** | 3 |
| **DMIC** | 2 PDM |
| **UAOL** | ACE 2.x internal UAOL only, no behind-hub support |
| **AIOC** | Not supported |

#### LNL-Specific Notes
- Single monolithic SOC die
- 4 SoundWire links (vs 5 on NVL/PTL)
- DMIC clock source: Audio PLL (XTAL-derived, 24.576 MHz/N)

---

### MTL SOC-M (ACE 1.5)

| Property | Value |
|----------|-------|
| **DID** | **0x7E28** (range 0x7E28–0x7E2F) |
| **BDF** | 0:31:3 |
| **Die Path** | `socket0.soc.ace` |
| **DSP Cores** | 3 HiFi4 + ANNA |
| **SRAM** | *(standard ACE 1.5)* |
| **SoundWire** | 4 links v1.2 |
| **SSP/I2S** | 3 |
| **DMIC** | 2 PDM |
| **UAOL** | ACE (early), behind-hub ❌ NOT supported (RTL bug — behind-hub broken on MTL) |
| **AIOC** | Not supported |

#### MTL UAOL Behind-Hub Bug
MTL has a known issue where UAOL does not work correctly with USB devices connected
behind a hub. Direct-connect UAOL works. This is fixed in ACE 2.x+ (LNL and later).

#### MTL-Specific Notes
- DMIC clock source: Audio PLL **or** RING_OSC (unique to MTL)
- SOC-M is the mobile variant; PCH-S is the desktop/server variant

---

### MTL PCH-S (ACE 1.5)

| Property | Value |
|----------|-------|
| **DID** | **0xAE28** (range 0xAE28–0xAE2F) |
| **BDF** | 0:31:3 |
| **Die Path** | `socket0.pch.ace` |
| **DSP Cores** | 2 HiFi4 + ANNA |
| **SoundWire** | 4 links v1.2 |
| **SSP/I2S** | 3 |
| **DMIC** | 2 PDM |
| **UAOL** | ACE (early), behind-hub ❌ NOT supported (same RTL bug as SOC-M) |

---

### ARL (ACE 1.5)

| Property | Value |
|----------|-------|
| **DID** | *(query CoDesign)* |
| **BDF** | 0:31:3 |
| **Die Path** | `socket0.pch.ace` |
| **DSP Cores** | ARL-U: 3 LX7 + HiFi4 + ANNA / ARL-S: 2 LX7 + HiFi4 + ANNA |
| **SoundWire** | 4 links v1.2 |
| **SSP/I2S** | 3 |
| **DMIC** | 2 PDM |
| **UAOL** | ACE 1.5 internal UAOL only, no behind-hub support |

#### ARL Variants
- **ARL-U** (mobile): 3 DSP cores, single PCH
- **ARL-S** (desktop): 2 DSP cores, larger PCH

---

### WCL (ACE 3.x)

| Property | Value |
|----------|-------|
| **DID** | *(shares PTL DIDs — verify against HAS)* |
| **BDF** | 0:31:3 |
| **Die Path** | `socket0.soc.ace` |
| **DSP Cores** | 5 LX7 + HiFi4 + ANNA |
| **SoundWire** | 5 links v1.2 |
| **SSP/I2S** | 3 |
| **DMIC** | 2 PDM |
| **UAOL** | ACE3 offload engine, behind-hub ✅ supported, ~1ms FIFO |
| **AIOC** | Not supported |

#### WCL-Specific Notes
- Shares ACE 3.x architecture with PTL — same DSP core config (5 LX7 + HiFi4 + ANNA)
- HAS reference: `wcl_ace3.x_integration_has.html`
- **BIOS menu path**: Same as PTL — `PCH-IO Configuration → HD Audio Configuration`
- **Known shared issues with PTL**: SSP BCLK inversion (HSDES-003), BT offload S0ix blocking (HSDES-006)
- For WCL-specific BIOS knob differences from PTL, query CoDesign: `"WCL ACE audio BIOS configuration differences from PTL"`
- **Debug approach**: Apply PTL debug procedures first. If WCL-specific behavior differs, check WCL erratum list.
- **Bring-up priority**: Verify PCI enumeration → codec detection → basic playback → PM before advanced features

---

### TTL (ACE 3.0 / ACE 4.0 — TitanLake)

> ⚠️ **From Co-Design AI (April 2026)** — verify all values against HAS for your stepping/SKU.
> TTL has a **dual ACE option**: ACE 3.0 (older/LX7-based) or ACE 4.0 (newer/HiFi5-based),
> selected by fuse configuration. Check which ACE version your TTL SKU is fused for.

| Property | ACE 4.0 Value | ACE 3.0 Value |
|----------|--------------|---------------|
| **DID** | 0xD228 ⚠️ (range D228–D22F) | 0xD228 ⚠️ (range D228–D22F) |
| **BDF** | 0:31:3 | 0:31:3 |
| **Die Path** | `socket0.pcd.ace` | `socket0.pcd.ace` |
| **Die Types** | PCD-H, PCD-S | PCD-H, PCD-S |
| **DSP Cores** | 4 HiFi5 | 5 LX7-HiFi4 |
| **SRAM** | 3.0 MB | 4.6 MB |
| **SoundWire** | 5 links v1.2 | 5 links v1.2 |
| **SSP/I2S** | 3 | 3 |
| **DMIC** | 2 PDM | 2 PDM |
| **UAOL** | Yes | Yes |
| **AIOC** | *(verify against HAS)* | *(verify against HAS)* |
| **HAS Reference** | ACE 4.x Integration HAS | ACE 3.x Integration HAS |

#### TTL-Specific Notes
- **Dual ACE architecture**: TTL is unique in offering both ACE 3.0 and ACE 4.0 variants,
  fuse-selected at manufacturing. Confirm your SKU's ACE version before debug.
- DID 0xD228 overlaps with NVL PCH-S — may indicate shared silicon IP block or
  Co-Design conflation. Verify against platform-specific HAS.
- ACE 4.0 variant: HiFi5 cores with 3.0 MB SRAM (smaller than NVL PCD-H's 4.5 MB)
- ACE 3.0 variant: LX7-HiFi4 cores with 4.6 MB SRAM (larger SRAM, different core arch)
- **Determining ACE version at runtime**: Read `ADSPCS` register — HiFi5 cores will report
  4 cores max, LX7-HiFi4 will report 5 cores. Alternatively check DSP FW capabilities via IPC.
- **Debug approach by ACE variant**:
  - ACE 4.0 → Use NVL PCD-H debug procedures (same core architecture)
  - ACE 3.0 → Use PTL debug procedures (same LX7 core architecture)
- **BIOS**: TTL BIOS may expose an ACE variant selector or auto-detect from fuses. If audio
  fails after BIOS update, verify the BIOS correctly detects the fused ACE variant.

---

### RZL (ACE 4.0 — RazorLake)

> ⚠️ **From Co-Design AI (April 2026)** — verify all values against HAS for your stepping/SKU.

| Property | Value |
|----------|-------|
| **DID** | 0xD328 ⚠️ (range D328–D32F) |
| **BDF** | 0:31:3 |
| **Die Path** | `socket0.pcd.ace` |
| **Die Types** | PCD-H, PCD-S, PCD-M (Mobile), PCD-W (Workstation) |
| **DSP Cores** | 4 HiFi5 |
| **SRAM** | 4.5 MB |
| **SoundWire** | 5 links v1.2 |
| **SSP/I2S** | 3 |
| **DMIC** | 2 PDM |
| **UAOL** | Yes (ACE4 offload engine) |
| **AIOC** | *(verify against HAS — expected, ACE 4.x)* |
| **HAS Reference** | ACE 4.x Integration HAS |

#### RZL-Specific Notes
- ACE 4.0 architecture, closest to NVL PCD-H configuration
- DID 0xD328 overlaps with NVL PCD-H — may indicate shared silicon IP block or
  Co-Design conflation. Verify against platform-specific HAS.
- **4 die variants**: PCD-H (High), PCD-S (S-series), PCD-M (Mobile), PCD-W (Workstation)
  — widest die variant spread of any audio platform
- 4.5 MB SRAM matches NVL PCD-H
- **Debug approach**: Apply NVL PCD-H debug procedures directly — same ACE 4.0 architecture,
  same DSP cores, same SRAM size. Key differences are likely limited to:
  - Platform-specific GPIO pad assignments (DMIC, jack detect, SSP)
  - Board-specific codec BOM (may differ from NVL reference boards)
  - Power domain configuration (PCD-M and PCD-W may have different PG behavior)
- **Die variant selection**: When connecting PythonSV, verify the die path for your variant:
  - PCD-H/PCD-S: `sv.socket0.pcd.ace` (standard)
  - PCD-M: Check if `sv.socket0.pcd.ace` or `sv.socket0.pcm.ace` — HAS-dependent
  - PCD-W: Check if `sv.socket0.pcd.ace` or `sv.socket0.pcw.ace` — HAS-dependent

---

## Platform Feature Comparison Matrix

| Feature | NVL PCD-H | NVL PCH-S | PTL | LNL | MTL-M | MTL-S | ARL-U | ARL-S | WCL | TTL (ACE4) | TTL (ACE3) | RZL |
|---------|-----------|-----------|-----|-----|-------|-------|-------|-------|-----|------------|------------|-----|
| ACE Version | 4.x | 4.x | 3.0 | 2.x | 1.5 | 1.5 | 1.5 | 1.5 | 3.0 | 4.0 | 3.0 | 4.0 |
| DSP HP Cores | 4 HiFi5 | 2 HiFi5 | 5 LX7 | 5 LX7 | 3 HiFi4 | 2 HiFi4 | 3 LX7 | 2 LX7 | 5 LX7 | 4 HiFi5 | 5 LX7-HiFi4 | 4 HiFi5 |
| ULP/ANNA | 1 ULP | 1 ULP+1 ANNA | HiFi4+ANNA | HiFi4+ANNA | ANNA | ANNA | HiFi4+ANNA | HiFi4+ANNA | HiFi4+ANNA | ULP | — | ULP |
| SRAM | 4.5 MB | 2.25 MB | — | — | — | — | — | — | — | 3.0 MB | 4.6 MB | 4.5 MB |
| SoundWire Segs | 5 | 5 | 5 | 4 | 4 | 4 | 4 | 4 | 5 | 5 | 5 | 5 |
| SSP | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| DMIC PDMs | 3 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| UAOL | ACE4 hub✅ | ACE4 hub✅ | ACE3 hub✅ | Internal | Hub❌ bug | Hub❌ bug | Internal | Internal | ACE3 hub✅ | Yes | Yes | Yes |
| AIOC | Yes | Yes | No | No | No | No | No | No | No | *(TBD)* | *(TBD)* | *(TBD)* |
| Die Path | pcd.ace | pch.ace | soc.ace | soc.ace | soc.ace | pch.ace | pch.ace | pch.ace | soc.ace | pcd.ace | pcd.ace | pcd.ace |

---

## Reset Architecture

Audio/ACE has 4 reset signals with different trigger conditions:

| Reset Signal | Type | Trigger | Clears |
|-------------|------|---------|--------|
| **arsm_rst_b** | Sticky | Deep reset only | Sticky registers, full ACE state |
| **aprim_rst_b** | Primary | Primary IOSF reset (warm/cold boot) | Most registers, DSP state |
| **aside_rst_b** | Sideband | Sideband IOSF reset | Sideband interface only |
| **aon_rst_b** | Always-on | Sticky reset, global/G3 only | Everything including wake logic |

### Reset Behavior by Scenario

| Scenario | arsm_rst_b | aprim_rst_b | aside_rst_b | aon_rst_b |
|----------|-----------|------------|------------|----------|
| Warm Boot | No | **Yes** | **Yes** | No |
| Cold Boot | **Yes** | **Yes** | **Yes** | No |
| Sx Entry/Exit | No | **Yes** | **Yes** | No |
| Global Reset | **Yes** | **Yes** | **Yes** | No |
| G3 (full power loss) | **Yes** | **Yes** | **Yes** | **Yes** |

### HDA-Specific Resets

| Reset | Mechanism | Effect |
|-------|-----------|--------|
| **PLTRST#** | Platform reset (from PCH/PMC) | Full HDA controller reset |
| **CRST#** | Controller Reset (GCTL.CRST bit) | Codec discovery reset — toggle to re-enumerate codecs |
| **SRST** | Stream Reset (per-stream) | Resets individual stream DMA state |
| **FLR** | Function Level Reset (PCI) | Full PCI function reset, equivalent to PLTRST# scope |

### Toggling CRST for Codec Re-Enumeration

```python
# If STATESTS=0 (no codecs detected), toggle CRST:
ace.hda.gctl.crst.write(0)   # Assert controller reset
# Wait ~100us
ace.hda.gctl.crst.write(1)   # De-assert — triggers codec enumeration
# Read STATESTS after ~500us
statests = ace.hda.statests.read()
print(f"STATESTS = 0x{statests:04X}")  # Non-zero = codec(s) detected
```

---

## Power Domains

Audio/ACE power is organized into 4 power gate domains:

| Domain | Scope | Gated When | Retained State |
|--------|-------|-----------|---------------|
| **PG0** | Always-on: PMC sideband, wake logic | Never (always powered) | Wake events, PMC comms |
| **PG1** | HDA controller, SoundWire links | D3 entry | None — full re-init needed |
| **PG2** | DSP cores, SRAM | DSP idle / D0i3 | SRAM contents in D0i3 (LP-SRAM retention) |
| **PG3** | DMIC PDM interfaces | No active capture | None |

### Power States

| State | PG0 | PG1 | PG2 | PG3 | Description |
|-------|-----|-----|-----|-----|-------------|
| **D0 (Active)** | On | On | On | On | Full operation |
| **D0i3 (Idle)** | On | On | Gated (SRAM retained) | Gated | DSP suspended, CLK_STOP on SoundWire |
| **D3hot** | On | Gated | Gated | Gated | FW unloaded, codec reset, minimal power |
| **D3cold** | On | Off | Off | Off | No power to audio IP |

### S0ix Integration
- ACE must complete D0i3 transition before platform can enter S0ix
- PMC waits for ACE LTR (Latency Tolerance Reporting) value ≤ exit latency threshold
- **DSP FW loaded blocks D0i3** — FW must be suspended/unloaded first
- Check S0ix blocking: use `power` sub-skill or `print_s0ix_y_blocking_conditions` doctor script

---

## BIOS Knobs

| Knob | BIOS Menu Path | Default | Effect |
|------|---------------|---------|--------|
| **AudioController** | PCH Configuration | Enabled | Master audio enable/disable (FNCFG.ACED) |
| **AudioDsp** | Audio Configuration | Enabled (SOF) | DSP enable, sets GPROCEN for decoupled mode |
| **SoundWireEnable** | Audio Configuration | Enabled | Enable SoundWire links (LCTL.SPA) |
| **DmicEnable** | Audio Configuration | Enabled | Enable DMIC PDM interfaces |
| **I2S_SSP_Enable** | Audio Configuration | Enabled | Enable SSP/I2S ports (BT offload) |
| **AudioD3PG** | PM Configuration | Enabled | D3 power gating enable |
| **UsitEnable** | USB Configuration | Enabled | UAOL enable (USB Audio Offload) |
| **ModernStandby** | PM Configuration | S0ix | S0ix / Modern Standby enable |
| **WoVEnable** | Audio Configuration | Enabled | Wake on Voice (DMIC-based keyword detect) |
| **HdaVerbTableEnable** | Audio Configuration | Enabled | HDA verb table initialization in BIOS |

### BIOS Knobs for AIOC (NVL Only)

| Knob | Setting | Purpose |
|------|---------|---------|
| SNDW#2 | Enabled | SoundWire Segment 2 for AIOC codecs |
| SNDW#2 Data Lanes | 3 | BIOS default for AIOC bandwidth (HW supports up to 4 lanes) |
| HDA Link | Disabled | Disable HDA when using AIOC on SoundWire |
| DMIC#0, DMIC#1 | Disabled | Free up pins for AIOC routing |
| ACX/SDCA | Enabled | SDCA driver model for ALC712/ALC1320 |
| Speaker Aggregation | Enabled | Multi-speaker AIOC topology |

---

## BIOS Register Reference

Key BIOS-programmed registers that control Audio/ACE behavior:

| Register | Bit/Field | Purpose |
|----------|-----------|---------|
| **FNCFG.BCLD** | Lock down | BIOS Configuration Lock Down — prevents further changes |
| **FNCFG.CGD** | Clock gate | Clock Gate Disable (debug: set to disable clock gating) |
| **FNCFG.ACED** | ACE disable | Audio Controller Enable/Disable — master kill switch |
| **EM1.BBRK** | Break | DSP break-on-boot for debug |
| **DEVIDLEPOL** | — | Device idle policy register |
| **PCICFGHWI0** | — | PCI config hardware init |
| **PTDC** | — | Power/thermal design current |
| **TCA / TTCCFG** | — | Thermal/throttle configuration |

---

## Fuse and Strap Reference

| Fuse/Strap | Bits | Purpose |
|------------|------|---------|
| **SSKUID[15:8]** | 8-bit | SKU identification — determines DID variant within range |
| **SNDWD[6]** | 1-bit | SoundWire Disable — fuse-level SoundWire kill |
| **DSPSD[1]** | 1-bit | DSP Disable — fuse-level DSP kill |
| **XOCFS** | — | XTAL frequency = 38.4 MHz (fixed on all modern platforms) |
| **DPGE** | 1-bit | Dynamic Power Gate Enable |
| **DCGE** | 1-bit | Dynamic Clock Gate Enable |

> **Fuse-disabled features** cannot be overridden by BIOS knobs. If DID shows the device
> but a specific sub-IP (SoundWire, DSP, DMIC) doesn't work, check fuses first.

---

## DMIC Clock Sources by Platform

| Platform | Clock Source | Frequency | Notes |
|----------|-------------|-----------|-------|
| NVL | Audio PLL | XTAL-derived, 24.576 MHz/N | Standard ACE4 clock tree |
| PTL | Audio PLL | XTAL-derived, 24.576 MHz/N | Standard ACE3 clock tree |
| LNL | Audio PLL | XTAL-derived, 24.576 MHz/N | Standard ACE2 clock tree |
| **MTL** | Audio PLL **or RING_OSC** | 24.576 MHz/N or Ring Osc | **Unique**: MTL can use Ring Oscillator as DMIC clock |
| WCL | Audio PLL | XTAL-derived, 24.576 MHz/N | Standard ACE3 clock tree (same as PTL) |
| TTL (ACE4) | Audio PLL | XTAL-derived, 24.576 MHz/N | Standard ACE4 clock tree |
| TTL (ACE3) | Audio PLL | XTAL-derived, 24.576 MHz/N | Standard ACE3 clock tree |
| RZL | Audio PLL | XTAL-derived, 24.576 MHz/N | Standard ACE4 clock tree |

---

## Windows Driver Stack

```
audiodg.exe (Windows Audio Device Graph)
    └── portcls.sys (Port Class driver)
        ├── intcaudiobus.sys  — HDA miniport (codec interface)
        ├── intcpchsnd.sys    — SoundWire controller driver
        ├── intelaud.sys      — SOF DSP driver (FW load, pipeline mgmt)
        ├── intelpch_dmic.sys — DMIC capture driver
        └── ACE Hardware
```

---

## NGA Test Content

| Test Suite | Duration | Coverage |
|-----------|----------|---------|
| `audio_bkc_checkout.xml` | ~15 min | Quick BKC sanity |
| `audio_regression_full.xml` | ~6 hr | Full regression |
| `audio_hda_full.xml` | — | HDA codec/stream tests |
| `audio_sdw_full.xml` | — | SoundWire link tests |
| `audio_dsp_full.xml` | — | DSP FW/pipeline tests |
| `audio_dmic_full.xml` | — | DMIC capture tests |
| `audio_pm_full.xml` | — | Power management tests |
| `audio_uaol_full.xml` | — | USB Audio Offload tests |
| `audio_wov_full.xml` | — | Wake on Voice tests |
| `audio_jack_full.xml` | — | Jack detection tests |
| `audio_ssp_full.xml` | — | SSP/I2S (BT offload) tests |

**Test content root**: `C:\validation\windows-test-content\audio\`

---

## Bring-Up Checklist

Follow this sequence for first-boot audio bring-up on any platform:

### Step 1: BIOS Prerequisites
- [ ] `AudioController` = Enabled
- [ ] `AudioDsp` = Enabled (for SOF/decoupled mode)
- [ ] `SoundWireEnable` = Enabled (if SoundWire codecs present)
- [ ] `DmicEnable` = Enabled (if DMIC microphones present)
- [ ] PMC firmware at BKC version (check via `pmc` skill)

### Step 2: PCI Enumeration Verification
- [ ] Device enumerates at BDF 0:31:3
- [ ] DID matches expected value for platform (see Device ID Table)
- [ ] DID ≠ 0xFFFF (if 0xFFFF: BIOS audio disabled or FNCFG.ACED fuse set)

### Step 3: BAR Assignment Verification
- [ ] BAR0 ≠ 0 (512 KB HDA registers)
- [ ] BAR1 ≠ 0 (4 KB extension registers)
- [ ] BAR2 ≠ 0 **if** decoupled mode (GPROCEN=1); BAR2=0 is expected in coupled mode

### Step 4: HDA Controller Init
- [ ] GCTL.CRST = 1 (controller out of reset)
- [ ] STATESTS ≠ 0 (at least one codec detected)
- [ ] If STATESTS = 0: toggle CRST (write 0, wait, write 1) to re-enumerate

### Step 5: DSP Bring-Up (Decoupled Mode)
- [ ] Set SPA = 1 (Stream Processor Active) for target DSP core
- [ ] Wait for CPA = 1 (Core Power Active) — confirms DSP core powered
- [ ] If CPA stays 0: DSP power gate stuck, check PG2 domain and BIOS `AudioDsp` knob
- [ ] Load FW via BAR2 SRAM interface

### Step 6: SoundWire Link Bring-Up
- [ ] Set LCTL.SPA = 1 for each SoundWire link to activate
- [ ] Wait for LCTL.CPA = 1 (Link Controller Power Active)
- [ ] If no SoundWire devices enumerate: check BIOS `SoundWireEnable` and physical connections

### PythonSV Bring-Up Script Template

```python
# Audio/ACE Bring-Up Verification
# Adjust die path per platform table at top of this file

import time

# 1. Select correct die path
ace = namednodes.sv.socket0.pcd.ace  # <-- CHANGE per platform

# 2. Check PCI enumeration
vid = ace.pcicfg.vid.read()
did = ace.pcicfg.did.read()
print(f"VID=0x{vid:04X} DID=0x{did:04X}")
assert vid == 0x8086, f"ERROR: VID=0x{vid:04X}, expected 0x8086"
assert did != 0xFFFF, "ERROR: DID=0xFFFF — Audio disabled in BIOS"

# 3. Check BARs
bar0 = ace.pcicfg.bar0.read()
bar1 = ace.pcicfg.bar1.read()
bar2 = ace.pcicfg.bar2.read()
print(f"BAR0=0x{bar0:08X} BAR1=0x{bar1:08X} BAR2=0x{bar2:08X}")
assert bar0 != 0, "ERROR: BAR0=0 — PCI BARs not assigned"

# 4. Check HDA controller
gctl = ace.hda.gctl.read()
crst = (gctl >> 0) & 1
print(f"GCTL=0x{gctl:08X} CRST={crst}")
if crst == 0:
    print("WARN: CRST=0 — controller in reset, toggling...")
    ace.hda.gctl.crst.write(0)
    time.sleep(0.001)
    ace.hda.gctl.crst.write(1)
    time.sleep(0.001)

# 5. Check codec presence
statests = ace.hda.statests.read()
print(f"STATESTS=0x{statests:04X}")
if statests == 0:
    print("WARN: No codecs detected — check physical connections and CRST toggle")

# 6. Check DSP (decoupled mode)
gprocen = ace.hda.gctl.gprocen.read()
print(f"GPROCEN={gprocen}")
if gprocen == 1 and bar2 != 0:
    print("Decoupled mode active — DSP accessible via BAR2")
else:
    print("Coupled mode or BAR2 not mapped — DSP not accessible")

print("\n=== Audio Bring-Up Check Complete ===")
```

---

## Common Bring-Up Failures

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| DID = 0xFFFF at 0:31:3 | Audio disabled in BIOS | Enable `AudioController` BIOS knob; check `FNCFG.ACED` fuse |
| BAR0 = 0 | PCI BAR not assigned | Check BIOS PCI resource allocation; reflash BIOS |
| STATESTS = 0 | No HDA codecs detected | Toggle CRST (write 0 then 1); check physical codec connection |
| GCTL.CRST = 0 | Controller stuck in reset | Write GCTL.CRST = 1; if stuck, check platform reset signals |
| BAR2 = 0 in decoupled mode | GPROCEN not set | Enable `AudioDsp` BIOS knob (sets GPROCEN=1) |
| DSP CPA = 0 after SPA = 1 | DSP power gate stuck | Check PG2 power domain; verify PMC FW version; check `AudioDsp` knob |
| No SoundWire devices | Link not active or no physical devices | Check LCTL.SPA=1; verify `SoundWireEnable` knob; check cable/connector |
| PythonSV `AttributeError` on ace path | Wrong die path for platform | Cross-check die path against Die Type Mapping table above |
| AIOC codecs enumerate but no audio | Wrong topology (ES vs MP) selected | Verify correct topology file; check Subsystem ID = 0x305610EC |

---

## Failure-to-Sub-Skill Routing

When a platform-level check reveals a failure, route to the appropriate sub-skill:

| Failure Symptom | Route To |
|----------------|----------|
| DID = 0xFFFF, BAR issues, enum failures | `config-checkout` |
| STATESTS = 0, codec discovery issues | `hda` |
| No SoundWire slaves, link training failure | `soundwire` |
| DSP timeout, FW load failure, CPA=0 | `dsp` |
| DMIC silent, no capture data | `dmic` |
| BT audio not working, SSP issues | `bt-offload` |
| HDMI/DP audio not working | `display-audio` |
| Jack not detected, wrong pin sense | `jack-detect` |
| S0ix blocked by audio, D3 not entering | `power` |
| LTR values too high, PM residency low | `power` |
| IRQ missing, interrupt storms | `interrupts` |
| UAOL dropouts, USB audio offload failure | `uaol` |
| WoV not waking, keyword detect failure | `wov` |
| AIOC enumeration or routing issues | `aioc` |
| PLL lock failure, clock issues | `clocking` |
| NGA test failure analysis | `failure-analysis` |

---

## HAS Document References

| Platform | HAS Document |
|----------|-------------|
| NVL PCD-H | `nvldp_ace4.x_integration_has.html` |
| NVL PCH-S | `nvps_ace4.x_integration_has.html` |
| PTL | `ptlsm_ace3.x_integration_has.html` |
| WCL | `wcl_ace3.x_integration_has.html` |
| TTL (ACE 4.0) | ACE 4.x Integration HAS *(same family as NVL — verify exact doc name)* |
| TTL (ACE 3.0) | ACE 3.x Integration HAS *(same family as PTL — verify exact doc name)* |
| RZL | ACE 4.x Integration HAS *(same family as NVL — verify exact doc name)* |
| LNL | *(query CoDesign)* |
| MTL | *(query CoDesign)* |
| ARL | *(query CoDesign)* |

---

## See Also

- **`config-checkout`** — Detailed PCI enumeration verification, BAR checks, register validation
- **`hda`** — HDA codec discovery, CORB/RIRB, stream management
- **`soundwire`** — SoundWire link training, multi-drop, data lanes
- **`dsp`** — DSP core bring-up, FW load, IPC, SRAM management
- **`power`** — D-state transitions, LTR, S0ix integration, power gating
- **`aioc`** — AIOC hardware setup, ALC712/ALC1320, 5-Star topology
- **`clocking`** — Clock sources, PLL, CRO, XTAL configuration
- **`interrupts`** — MSI/INTA routing, IRQ mapping
