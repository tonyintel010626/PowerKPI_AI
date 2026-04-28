# Interrupts — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only ACE interrupt architecture validation — MSI/INTA routing, GIS/CIS/SIS/PIS qualification, DSP IPC interrupts, and interrupt storm debug.
> **Platform**: NVL (ACE 4.x), extensible to PTL, LNL, MTL, ARL.

---

## Driver Stack

| Layer | Binary | Description |
|-------|--------|-------------|
| PCI bus | `pci.sys` | MSI capability setup, interrupt vector allocation |
| Intel audio bus | `IntcAudioBus.sys` | HDA interrupt handler — GIS/CIS/SIS service |
| Intel SST | `IntcSmartSound.sys` | DSP interrupt handler — PIS/IPC service |
| HAL | `hal.dll` | Interrupt dispatch, IRQL management |

---

## Device Enumeration

### Verify Interrupt Assignment
```cmd
:: Check audio device interrupt assignment
powershell -c "Get-PnpDeviceProperty -InstanceId (Get-PnpDevice -Class MEDIA | Select-Object -First 1).InstanceId -KeyName DEVPKEY_Device_InterruptNumber"

:: Check MSI capability via device properties
:: Device Manager → Intel SST → Properties → Resources → IRQ

:: Check interrupt affinity and mode
powershell -c "Get-WmiObject Win32_IRQResource | Where-Object {$_.Description -like '*audio*'}"
```

---

## Windows Registry Knobs

### Interrupt Configuration
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcAudioBus\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `ForceLegacyInterrupt` | REG_DWORD | 1=force INTA (disable MSI) for debug |
| `InterruptCoalescing` | REG_DWORD | 1=batch interrupts for performance |

### MSI Override (Debug)
```
HKLM\SYSTEM\CurrentControlSet\Enum\PCI\VEN_8086&DEV_D328&*\Device Parameters\Interrupt Management\
```
| Value | Type | Purpose |
|-------|------|---------|
| `MSISupported` | REG_DWORD | 1=enable MSI, 0=force legacy INTA |
| `MessageNumberLimit` | REG_DWORD | Max MSI vectors (usually 1 for ACE) |

---

## ETW / WPP Trace Capture

### Capture Interrupt Activity
```cmd
:: For interrupt-level debug, use xperf (Windows Performance Toolkit)
xperf -on PROC_THREAD+INTERRUPT+DPC -start AudioIrq ^
  -on Microsoft-Windows-Audio:0xFFFF:4 ^
  -f C:\Temp\AudioIrq.etl

:: Play audio for 30 seconds to generate interrupt traffic, then:
xperf -stop AudioIrq -stop -d C:\Temp\AudioIrq_merged.etl

:: Analyze in Windows Performance Analyzer (WPA)
wpa C:\Temp\AudioIrq_merged.etl
:: Navigate to: System Activity → DPCs / ISRs → filter by IntcAudioBus or IntcSmartSound
```

### Key Metrics in WPA
| Metric | Expected | Abnormal |
|--------|----------|----------|
| ISR duration | < 10 µs | > 100 µs (indicates ISR doing too much work) |
| DPC duration | < 50 µs | > 500 µs (deferred work taking too long) |
| ISR frequency | ~48 per ms for 48 kHz stream | 10× expected = interrupt storm |
| ISR CPU% | < 1% | > 5% (excessive interrupt overhead) |

---

## Common Failure Modes

### Failure: No audio interrupts (stream not progressing)
1. Check `INTCTL` register: GIE (bit 31) must be 1 (global interrupt enable)
2. Check MSI enabled: `MSISupported=1` in PCI interrupt management
3. Check stream interrupt enable: `SIE[x]` in INTCTL for the active stream
4. Try `ForceLegacyInterrupt=1` to rule out MSI configuration issue
5. PythonSV: read `soc.ace.hda.mmr.intsts` — check GIS, CIS, SIS bits

### Failure: Interrupt storm (high CPU / audio dropout)
1. Check `INTSTS` — are status bits being cleared by driver ISR?
2. Status bits not cleared = continuous interrupt re-assertion
3. Check for FIFO error bits (FIFOE in stream status) causing rapid interrupts
4. xperf trace: ISR frequency >> expected → status bit stuck
5. Temporarily set `ForceLegacyInterrupt=1` to change interrupt delivery path

### Failure: DSP IPC interrupt lost (FW timeout)
1. Check PIS (bit 31 of `INTSTS`) — should assert on IPC reply
2. Check `DSPMPC` ≠ 0 — PIS only exists when DSP mode configured
3. Check `HIPCIE` / `HIPCIS` — per-instance IPC masking
4. WPP trace: `IPC_SEND` without corresponding `IPC_RECV` = IPC lost

### Failure: No wake from D3 via audio event
1. D3 uses PME path, not normal interrupt
2. Check `PMEEN` and `WAKEEN` registers
3. Check ACPI `_PRW` (Power Resources for Wake) for audio device
4. WPP trace: search for `PME` or `WAKE` events

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\interrupts\`

Key test categories:
- `interrupt_routing\` — verify MSI vs INTA delivery
- `interrupt_storm_detect\` — monitor ISR frequency during stress
- `ipc_interrupt\` — DSP IPC send/reply interrupt verification
- `wake_interrupt\` — D3 → D0 wake via codec/SoundWire event

Run manually:
```cmd
cd C:\validation\windows-test-content\audio\interrupts\interrupt_routing
python run_test.py --verbose
```
