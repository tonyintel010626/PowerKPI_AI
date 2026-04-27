---
name: fv-audio/interrupts
description: "ACE Audio Interrupt Architecture — HD Audio interrupt tree, DSP offload IRQ mapping, MSI/INTA routing, and per-instance IPC masking"
version: 1.1.0
author: FV-Audio Team
platform: NVL, PTL, MTL, LNL, ARL, WCL, TTL, RZL
ip: ACE 1.5 / 2.x / 3.0 / 4.x
tags: [audio, interrupts, MSI, INTA, IPC, DSP, HDA, IRQ, NVLDP, APIC]
source: "NVLDP ACE4.x Integration HAS Rev 1.2 §5"
owner: huiyingt
---

# ACE Audio Interrupt Architecture

> **Scope**: Interrupt tree hierarchy, host interrupt mapping, DSP offload IRQ assignment, MSI vs legacy INTA routing, APIC/GIC routing, and per-instance IPC masking for the ACE IP across Intel Client SoC platforms. Covers both Intel HD Audio controller interrupts and DSP (Tensilica) offload interrupts.
>
> **Source**: NVLDP ACE4.x Integration HAS Rev 1.2, §5 Interrupts

---

## Host Interrupt Mapping

ACE IP is a PCI device that sends interrupts via **MSI** (Message Signaled Interrupt) or **virtual INTA/B/C/D** over IOSF Sideband.

**Key rules:**
- Interrupts are only delivered in **D0 state** (per PCI spec)
- In **D3**, only PME (Power Management Event) is used for wake
- ACPI mode option: BIOS sets `HxPCICFGCTL.ACPIIE` + `APCIIN` field for ACPI-specific IRQ routing

**NVLDP implementation**: Both Intel HD Audio and PCI config related interrupt trees are implemented.

---

### BAR0 Register Offsets (Intel HDA Spec — All ACE Platforms)

| Offset | Register | Width | Description |
|--------|----------|-------|-------------|
| 0x0C | WAKEEN | 2B | Wake Enable — enable codec presence wake per SDI lane |
| 0x0E | STATESTS | 2B | State Change Status — one bit per SDI (codec present/removed) |
| 0x20 | INTCTL | 4B | Interrupt Control — GIE (bit 31), CIE (bit 30), SIE bits [29:0] |
| 0x24 | INTSTS | 4B | Interrupt Status — GIS/PIS (bit 31)¹, CIS (bit 30), SIS bits [29:0] |
| 0x30 | WALCLK | 4B | Wall Clock Counter — 25 ns resolution, wraps ~107s |

> ¹ Bit 31: GIS (Global Interrupt Status) in standard HDA mode; repurposed as PIS (DSP Offload interrupt) in ACE DSP mode when `DSPMPC != 0`

---

## Intel HD Audio Interrupt Tree (3-Level Hierarchy)

The HDA interrupt tree uses a 3-level qualification/aggregation model:

### Level 1 — Individual Status Bits

Individual status bits are set by **pulse events** and cleared by software writing `1` to the bit position. Setting is **independent of enable bits** (status always reflects HW state).

Per-stream interrupt sources (up to 30 streams):
| Source | Description |
|--------|-------------|
| Buffer Completion (IOC) | Interrupt On Completion — stream DMA reached a buffer descriptor with IOC=1 |
| Descriptor Error | DMA encountered an invalid buffer descriptor |
| FIFO Error | Stream FIFO overrun (capture) or underrun (playback) |

### Level 2 — Qualified Status Groups

| Group | Status Register | Enable Register | Sources |
|-------|----------------|-----------------|---------|
| **Wake** | PMESTS | PMEEN | PME signal — wake events from sleep states |
| **Controller (CIS)** | INTSTS[30] | CIE | Input link wake (incl SoundWire), RIRB overrun, RIRB count, command error, error present, D0i3 completion, extended audio link events |
| **Stream (SIS)** | INTSTS[x] | SIE(x) | Per-stream: buffer completion, descriptor error, FIFO error |
| **DSP Offload (PIS)** | INTSTS[31] | PIE | IPC reply, FW ready, error. **Only exists if DSPMPC != 0** (DSP mode configured) |

### Level 3 — Global Interrupt Aggregation

All qualified SIS(x) are **OR'd** with qualified CIS and PIS to produce:
- **GIS** — Global Interrupt Status (in MMR space)
- **IS** — Interrupt Status (in PCI config space)

**Interrupt delivery conditions:**

| Mode | Conditions |
|------|-----------|
| **Legacy INTA** | GIS=1, ID=0 (Interrupt Disable in PCI CMD), ME=0 (MSI Enable), device in D0. Uses Interrupt Widget → IOSF Sideband assert/deassert protocol |
| **MSI** | GIS=1, ME=1, device in D0, new 0→1 transition on GIS. Single MSI message per edge |

### PythonSV — Read HDA Interrupt State

```python
# Read Global Interrupt Status
gis = soc.ace.hda.mmr.intsts.read()
print(f"GIS={gis:#010x}")
print(f"  CIS (bit 30): {(gis >> 30) & 1}")
print(f"  PIS (bit 31): {(gis >> 31) & 1}")
for s in range(30):
    if (gis >> s) & 1:
        print(f"  SIS[{s}]: ACTIVE")

# Read Controller Interrupt Status / Enable
cis = soc.ace.hda.mmr.intctl.read()
print(f"INTCTL={cis:#010x}  (CIE={bool(cis & (1<<30))}, GIE={bool(cis & (1<<31))})")

# Read Wake Enable
wakeen = soc.ace.hda.mmr.wakeen.read()
wakests = soc.ace.hda.mmr.wakests.read()
print(f"WAKEEN={wakeen:#06x}  WAKESTS={wakests:#06x}")
```

---

## DSP Offload Interrupt Tree

When DSP offload is enabled (DSPMPC != 0), the ACE uses a **Synopsys DW_apb_ictl** interrupt controller for DSP-side interrupt aggregation.

### NVLDP IRQ Mapping

| IRQ# | Source | NVLDP Status | Description |
|------|--------|-------------|-------------|
| 0 | Host IPC | **Valid** | Host-to-DSP IPC message available |
| 1 | ML Interrupt | **Valid** | Machine Learning accelerator (ANNA) completion |
| 2 | AON Vision | Reserved | Not used on NVLDP |
| 3–6 | Reserved | Reserved | — |
| 7 | Timers/Timestamp | **Valid** | DSP timer and wall clock timestamp events |
| 8 | Watchdog (2nd timeout) | **Valid** | DSP watchdog second-timeout (recovery trigger) |
| 9 | I3C | Reserved | Not connected on NVLDP |
| 10 | GPDMA | Reserved | Not connected on NVLDP |
| 11 | PWM | Reserved | Not connected on NVLDP |
| 12 | I2C | Reserved | Not connected on NVLDP |
| 13 | SPI | Reserved | Not connected on NVLDP |
| 14 | UART | Reserved | Not connected on NVLDP |
| 15 | GPIO | Reserved | Not connected on NVLDP |
| 16 | FW Loading/Verification | **Valid** | FW load complete or authentication result |

---

## Multi-Platform DSP IRQ Comparison

DSP interrupt assignments vary by ACE generation. The table below compares active IRQ sources across platforms. Only IRQs that differ or are noteworthy are listed.

| IRQ# | Source | NVL (ACE 4.x) | PTL/WCL (ACE 3.0) | LNL (ACE 2.x) | MTL/ARL (ACE 1.5) |
|------|--------|---------------|-------------------|---------------|-------------------|
| 0 | Host IPC | ✅ Valid | ✅ Valid | ✅ Valid | ✅ Valid |
| 1 | ML / ANNA | ✅ Valid | ✅ Valid ¹ | ❌ Reserved | ❌ Reserved |
| 2 | AON Vision | ❌ Reserved | ❌ Reserved | Consult HAS ¹ | ❌ Reserved |
| 7 | Timers | ✅ Valid | ✅ Valid | ✅ Valid | ✅ Valid |
| 8 | Watchdog | ✅ Valid | ✅ Valid | ✅ Valid | ✅ Valid |
| 9 | I3C | ❌ Not connected | Consult HAS ¹ | ❌ Reserved | ❌ Reserved |
| 10 | GPDMA | ❌ Not connected | ✅ Valid ¹ | ✅ Valid ¹ | ✅ Valid ¹ |
| 16 | FW Load/Verify | ✅ Valid | ✅ Valid | ✅ Valid | ✅ Valid |
| **DSP Cores** | — | 4 HP + 1 ULP | 3 HP + 1 ULP ¹ | 3 HP ¹ | 2 HP ¹ |
| **ictl Type** | — | DW_apb_ictl | DW_apb_ictl | DW_apb_ictl ¹ | DW_apb_ictl ¹ |

> ¹ **HAS verification required** — Values for non-NVL platforms are inferred from ACE generation architecture. Consult the platform ACE Integration HAS §5 (Interrupts) for exact IRQ mapping on your target. Query Co-Design: `"DSP IRQ mapping <PLATFORM> ACE integration HAS §5"`.

### Key Cross-Platform Differences

| Aspect | ACE 1.5 (MTL/ARL) | ACE 2.x (LNL) | ACE 3.0 (PTL/WCL) | ACE 4.x (NVL) |
|--------|-------------------|---------------|-------------------|---------------|
| **ML accelerator IRQ** | Not present | Not present | Present (ANNA v1) | Present (ANNA v2) |
| **GPDMA IRQ** | Connected ¹ | Connected ¹ | Connected ¹ | Not connected (uses DMA MISC) |
| **Max stream interrupts** | Up to 16 ¹ | Up to 16 ¹ | Up to 30 | Up to 30 |
| **IPC instances** | 1 ¹ | 1 ¹ | Multiple ¹ | Multiple (HIPCIE/HIPCIS) |
| **DSP watchdog** | Single timeout ¹ | Single timeout ¹ | Dual timeout ¹ | Dual timeout (2nd = IRQ 8) |

> ¹ **HAS verification required** — Exact counts and capabilities vary by platform SKU.

---

### Per-Instance IPC Masking

The ACE supports multiple IPC instances. Per-instance masking is controlled by:

| Register | Purpose |
|----------|---------|
| **HIPCIE** | Host IPC Instance Enable — masks specific IPC instance interrupts |
| **HIPCIS** | Host IPC Instance Status — reads which host IPC instance is asserting |

```python
# Read DSP IPC interrupt state
hipcie = soc.ace.hda.bar4.hipcie.read()
hipcis = soc.ace.hda.bar4.hipcis.read()
print(f"HIPCIE (instance enable)={hipcie:#010x}")
print(f"HIPCIS (instance status)={hipcis:#010x}")

# Read DSP offload interrupt status (PIS in INTSTS bit 31)
intsts = soc.ace.hda.mmr.intsts.read()
pis = (intsts >> 31) & 1
print(f"PIS (DSP offload interrupt): {'ACTIVE' if pis else 'inactive'}")
```

---

## Interrupt Routing Summary (NVLDP)

```
                    ┌─────────────────────────────────┐
                    │     Level 1: Raw Status Bits     │
                    │  (set by HW pulse, SW clears)    │
                    ├─────────┬───────────┬────────────┤
                    │ Stream  │ Controller│ DSP Offload│
                    │ SIS(x)  │   CIS     │    PIS     │
                    └────┬────┴─────┬─────┴──────┬─────┘
                         │          │            │
                    ┌────▼────┐┌────▼────┐ ┌─────▼────┐
                    │ SIE(x)  ││  CIE    │ │   PIE    │  Level 2: Enable
                    │ qualify ││ qualify │ │  qualify  │  Qualification
                    └────┬────┘└────┬────┘ └─────┬────┘
                         │          │            │
                         └──────────┼────────────┘
                                    │ OR
                              ┌─────▼─────┐
                              │    GIS    │  Level 3: Global
                              │  (MMR)    │  Aggregation
                              └─────┬─────┘
                                    │
                         ┌──────────┼──────────┐
                         │                     │
                    ┌────▼────┐           ┌────▼────┐
                    │  INTA   │           │   MSI   │
                    │ (ID=0,  │           │ (ME=1,  │
                    │  ME=0)  │           │  edge)  │
                    └─────────┘           └─────────┘
```

---

## MSI vs Legacy INTA Routing

### MSI (Message Signaled Interrupt) — Preferred

MSI is the default and preferred interrupt delivery mechanism for ACE on modern platforms. It avoids shared interrupt lines and provides lower latency.

**PCI Config Space MSI Capability:**

| Offset (from MSI Cap) | Field | Description |
|------------------------|-------|-------------|
| +0x00 | MSI_CAP_ID | Capability ID = 0x05 |
| +0x02 | MSI_MSG_CTRL | Message Control — ME (bit 0), MMC/MME (multi-message) |
| +0x04 | MSI_MSG_ADDR | Message Address (written by OS/BIOS) |
| +0x0C | MSI_MSG_DATA | Message Data (interrupt vector) |

**MSI delivery**: On GIS 0→1 transition, a single MSI write is generated to the address/data programmed by the OS. The OS APIC routes this to the assigned CPU core.

### Legacy INTA — Fallback

Legacy INTA is used only when MSI is disabled (ME=0 in MSI Message Control). The ACE asserts virtual INTA over IOSF Sideband to the PCH interrupt controller.

**INTA assertion protocol:**
1. GIS transitions 0→1 → ACE sends `assert INTA` message on sideband
2. OS ISR runs, clears all status bits
3. GIS transitions 1→0 → ACE sends `deassert INTA` message on sideband

> **Platform Note**: Legacy INTA is shared with other PCI devices on the same interrupt line. This causes latency due to interrupt sharing. MSI is strongly preferred for audio to avoid glitches from ISR latency.

### APIC Routing

On x86 Intel Client SoC platforms, MSI interrupts are routed through the **Local APIC** on each CPU core:

```
ACE MSI Write → System Bus → IOAPIC (legacy) or Direct LAPIC (MSI)
                                    │
                              ┌─────▼─────┐
                              │  Local     │
                              │  APIC      │
                              │ (per core) │
                              └─────┬─────┘
                                    │
                              ┌─────▼─────┐
                              │  CPU Core  │
                              │  ISR       │
                              └───────────┘
```

**Key APIC considerations for audio:**
- **Affinity**: Audio MSI can be pinned to a specific core via interrupt affinity. Avoid core 0 (busy with timer interrupts) for latency-sensitive audio.
- **Priority**: Audio interrupts should have higher priority than background I/O to prevent buffer underrun.
- **Power gating**: If the target core is in C6 or deeper, the interrupt wakes the core — adding latency. For low-latency audio, consider keeping the audio-affinity core in C1/C1E.

```python
# PythonSV: Check MSI configuration in PCI config space
# MSI Capability pointer is at offset found via Cap Pointer chain
cap_ptr = soc.ace.hda.pcicfg.capptr.read() & 0xFF
print(f"PCI Capability Pointer: 0x{cap_ptr:02X}")

# Walk capability list to find MSI (ID=0x05)
ptr = cap_ptr
while ptr:
    cap_id = soc.ace.hda.pcicfg.read(ptr, 1)
    if cap_id == 0x05:
        msg_ctrl = soc.ace.hda.pcicfg.read(ptr + 2, 2)
        msi_enable = msg_ctrl & 1
        print(f"MSI Capability at 0x{ptr:02X}: MSG_CTRL=0x{msg_ctrl:04X} ME={msi_enable}")
        break
    ptr = soc.ace.hda.pcicfg.read(ptr + 1, 1) & 0xFF
```

---

## PythonSV — Full Interrupt State Dump

Use this comprehensive script to capture the complete ACE interrupt state for debug:

```python
def dump_ace_interrupt_state(soc):
    """Dump complete ACE interrupt state — run during active audio or failure triage."""
    print("=" * 70)
    print("ACE INTERRUPT STATE DUMP")
    print("=" * 70)

    # 1. PCI Command Register — check Interrupt Disable (ID) bit
    pci_cmd = soc.ace.hda.pcicfg.cmd.read()
    id_bit = (pci_cmd >> 10) & 1
    print(f"\n[PCI CMD] = 0x{pci_cmd:04X}  Interrupt Disable (ID) = {id_bit}")
    if id_bit:
        print("  WARNING: PCI Interrupt Disable is SET — no INTA delivery")

    # 2. INTCTL — Global, Controller, Stream enables
    intctl = soc.ace.hda.mmr.intctl.read()
    gie = (intctl >> 31) & 1
    cie = (intctl >> 30) & 1
    sie_mask = intctl & 0x3FFFFFFF
    print(f"\n[INTCTL] = 0x{intctl:08X}")
    print(f"  GIE (Global Int Enable) = {gie}")
    print(f"  CIE (Controller Int Enable) = {cie}")
    print(f"  SIE mask (stream enables) = 0x{sie_mask:08X}  ({bin(sie_mask).count('1')} streams enabled)")

    # 3. INTSTS — Current interrupt status
    intsts = soc.ace.hda.mmr.intsts.read()
    gis = (intsts >> 31) & 1
    cis = (intsts >> 30) & 1
    sis_mask = intsts & 0x3FFFFFFF
    print(f"\n[INTSTS] = 0x{intsts:08X}")
    print(f"  GIS/PIS (bit 31) = {gis}  {'← DSP offload IRQ ACTIVE' if gis else ''}")
    print(f"  CIS (bit 30) = {cis}  {'← Controller IRQ ACTIVE' if cis else ''}")
    active_streams = [s for s in range(30) if (sis_mask >> s) & 1]
    if active_streams:
        print(f"  Active stream IRQs: {active_streams}")
    else:
        print(f"  No active stream IRQs")

    # 4. Wake registers
    wakeen = soc.ace.hda.mmr.wakeen.read()
    wakests = soc.ace.hda.mmr.wakests.read()
    statests = soc.ace.hda.mmr.statests.read()
    print(f"\n[WAKEEN]  = 0x{wakeen:04X}")
    print(f"[WAKESTS] = 0x{wakests:04X}")
    print(f"[STATESTS]= 0x{statests:04X}  (codec presence: {bin(statests)})")

    # 5. DSP IPC interrupt state (if DSP mode enabled)
    try:
        hipcie = soc.ace.hda.bar4.hipcie.read()
        hipcis = soc.ace.hda.bar4.hipcis.read()
        print(f"\n[HIPCIE] (IPC instance enable) = 0x{hipcie:08X}")
        print(f"[HIPCIS] (IPC instance status) = 0x{hipcis:08X}")
        if hipcis:
            print(f"  IPC instances asserting: {bin(hipcis)}")
    except Exception:
        print("\n[HIPCIE/HIPCIS] Not accessible (DSP mode may not be configured)")

    # 6. ADSPIC — DSP interrupt control (ACE-specific)
    try:
        adspic = soc.ace.hda.bar4.adspic.read()
        adspis = soc.ace.hda.bar4.adspis.read()
        print(f"\n[ADSPIC] (DSP Int Control) = 0x{adspic:08X}")
        print(f"[ADSPIS] (DSP Int Status)  = 0x{adspis:08X}")
    except Exception:
        print("\n[ADSPIC/ADSPIS] Not accessible")

    print("\n" + "=" * 70)
    return {
        'intctl': intctl, 'intsts': intsts, 'pci_cmd': pci_cmd,
        'wakeen': wakeen, 'wakests': wakests, 'statests': statests,
    }

# Usage:
# state = dump_ace_interrupt_state(soc)
```

---

## PythonSV — IRQ Storm Detector

Detect interrupt storms (excessive IRQ rate) that can cause audio dropouts or system hangs:

```python
import time

def detect_irq_storm(soc, duration_s=5, threshold_per_sec=1000):
    """Monitor INTSTS transitions over a time window to detect IRQ storms.

    Args:
        soc: PythonSV SoC handle
        duration_s: Monitoring duration in seconds
        threshold_per_sec: IRQ rate above this = storm detected
    """
    print(f"Monitoring ACE interrupts for {duration_s}s (storm threshold: {threshold_per_sec}/s)...")

    irq_count = 0
    storm_detected = False
    start = time.time()
    prev_gis = 0

    while time.time() - start < duration_s:
        intsts = soc.ace.hda.mmr.intsts.read()
        gis = (intsts >> 31) & 1
        cis = (intsts >> 30) & 1

        # Count GIS 0→1 transitions (new interrupt edges)
        if gis and not prev_gis:
            irq_count += 1
        prev_gis = gis

        # Also count CIS transitions as separate events
        if cis:
            irq_count += 1

        time.sleep(0.001)  # 1ms poll interval

    elapsed = time.time() - start
    rate = irq_count / elapsed if elapsed > 0 else 0
    print(f"\nResults: {irq_count} IRQ edges in {elapsed:.1f}s = {rate:.0f} IRQ/s")

    if rate > threshold_per_sec:
        print(f"*** IRQ STORM DETECTED *** (rate {rate:.0f} > threshold {threshold_per_sec})")
        print("  Likely cause: status bit not being cleared by ISR, or hardware asserting continuously")
        print("  Debug: read INTSTS to identify which source (SIS/CIS/PIS) is firing repeatedly")
        storm_detected = True
    else:
        print(f"IRQ rate normal ({rate:.0f}/s)")

    return {'count': irq_count, 'rate': rate, 'storm': storm_detected}

# Usage:
# result = detect_irq_storm(soc, duration_s=10, threshold_per_sec=500)
```

---

## ACPI Interrupt Routing

BIOS configures ACPI interrupt routing for ACE via the `HxPCICFGCTL` register:

| Field | Description |
|-------|-------------|
| **ACPIIE** | ACPI Interrupt Enable — when set, ACE uses ACPI-routed interrupt instead of PCI INTx |
| **APCIIN** | ACPI Interrupt Input — selects which ACPI interrupt line (SCI) is used |

**When ACPI mode is used:**
- The ACE interrupt bypasses the normal PCI INTA/MSI path
- Instead, it routes through the ACPI SCI (System Control Interrupt) mechanism
- This is typically used in S3/S4 wake scenarios where normal PCI interrupts are disabled

**ACPI Routing in \_SB.PCI0 DSDT:**
```
// ACPI device entry for ACE (BDF 0:31:3)
Device (HDAS) {
    Name (_ADR, 0x001F0003)    // BDF 0:31:3
    Name (_S0W, 0x03)           // D3 wake capability
    // Interrupt resource: MSI or ACPI SCI based on BIOS config
}
```

> **Debug tip**: If audio interrupts work in Windows but fail in Linux (or vice versa), check whether the BIOS is programming ACPIIE differently for each OS. Some BIOS implementations enable ACPI mode for one OS and MSI for another based on OS detection during boot.

---

## Troubleshooting

| Symptom | Likely Cause | Debug Steps |
|---------|-------------|-------------|
| No interrupts in D0 | GIE not set, or ME=0 and ID=1 | Check `INTCTL` bit 31 (GIE), PCI CMD register bit 10 (ID), and MSI capability enable |
| Stream interrupt not firing | SIE(x) not enabled | Read `INTCTL` bits [0:29] for per-stream enables |
| CIS not asserting | CIE=0 or no qualifying source | Check `CIE` enable and individual CIS source status bits |
| PIS missing | DSPMPC=0 (DSP mode not configured) | Verify DSP mode in `DSPMPC` register. PIS only exists when DSP offload enabled |
| IPC interrupt lost | HIPCIE masking wrong instance | Read `HIPCIE`/`HIPCIS` to identify which instance is masked vs asserting |
| Interrupt storm | Status not cleared by SW | SW must write 1 to status bits to clear. Check driver ISR is acking all active sources. Use IRQ storm detector script above. |
| No wake from D3 | PMEEN not set or WAKEEN not configured | Check `PMEEN` and `WAKEEN` registers. D3 uses PME, not normal interrupt path |
| ACPI routing mismatch | ACPIIE/APCIIN misconfigured | BIOS must set `HxPCICFGCTL.ACPIIE` and `APCIIN` for ACPI mode |
| MSI not working, INTA OK | MSI capability not enabled | Walk PCI cap list, verify MSI MSG_CTRL.ME=1. Check OS MSI support and BIOS allocation. |
| Audio glitch under CPU load | ISR latency on shared INTA | Switch to MSI if on legacy INTA. Pin audio IRQ affinity away from busy core 0. |
| Interrupt lost after D3→D0 | MSI address/data lost on D3 | OS must re-program MSI address/data after D3→D0 transition (PCI PM spec). Check driver PM resume path. |
| Linux no audio IRQ | IRQ not allocated by kernel | Check `cat /proc/interrupts` for snd_sof or snd_hda_intel entry. Verify `dmesg | grep -i "irq\|msi"` for allocation messages. |
| Windows IRQ conflict | Shared INTA with other device | Check Device Manager → Resources for IRQ sharing. Switch to MSI via registry if needed. |

---

## Multi-Platform Interrupt Configuration Summary

| Feature | NVL (ACE 4.x) | PTL/WCL (ACE 3.0) | LNL (ACE 2.x) | MTL/ARL (ACE 1.5) |
|---------|---------------|-------------------|---------------|-------------------|
| **PCI BDF** | 0:31:3 | 0:31:3 | 0:31:3 ¹ | 0:31:3 |
| **MSI Support** | Yes (preferred) | Yes | Yes | Yes |
| **Legacy INTA** | Yes (fallback) | Yes | Yes | Yes |
| **Max Streams (SIS)** | 30 | 30 | 16 ¹ | 16 ¹ |
| **DSP IPC Instances** | Multiple (HIPCIE) | Multiple ¹ | 1 ¹ | 1 ¹ |
| **ACPI SCI Mode** | Supported | Supported | Supported ¹ | Supported |
| **PME Wake** | D3 PME via PCH | D3 PME via PCH | D3 PME ¹ | D3 PME |
| **ADSPIC/ADSPIS** | BAR4 DSP IRQ regs | BAR4 ¹ | BAR4 ¹ | BAR4 ¹ |

> ¹ **HAS verification required** — Verify against the platform ACE Integration HAS §5 for your specific stepping/SKU.

---

## Cross-References

- **[power/SKILL.md](../power/SKILL.md)** — D0/D0i3/D3 transitions that affect interrupt delivery
- **[dsp/SKILL.md](../dsp/SKILL.md)** — DSP IPC messaging that drives PIS/HIPCIE interrupts
- **[config-checkout/SKILL.md](../config-checkout/SKILL.md)** — PCI enumeration and MSI capability verification
- **[hda/SKILL.md](../hda/SKILL.md)** — HDA stream setup that generates SIS interrupts
- **[soundwire/SKILL.md](../soundwire/SKILL.md)** — SoundWire link wake events that feed CIS
- **[wov/SKILL.md](../wov/SKILL.md)** — Wake on Voice events routed through PME path
- **[platform/SKILL.md](../platform/SKILL.md)** — Per-platform BDF assignments, DSP core counts, ACE versions
