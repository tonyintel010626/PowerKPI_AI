# Audio Power — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only. All test content at `C:\validation\windows-test-content\audio\power\`.
> **Platform**: NVL (Novalake) ACE 4.x.

---

## Power State Overview (Windows Perspective)

| HW State | Windows Model | Trigger |
|----------|--------------|---------|
| D0 (active) | `PowerDeviceD0` | Stream active or keep-alive |
| D0i3 (clock-gated) | `PowerDeviceD0` sub-state | No active stream, PoFx idle callback |
| D3Hot | `PowerDeviceD3` | PoFx device idle, PCI PMCSR[1:0]=11b |
| D3Cold | `PowerDeviceD3` + power rail off | System-level S0ix (requires D3Hot first) |

Windows uses the **PoFx (Power Framework)** for runtime idle management of the ACE/HDA device. The driver calls `PoFxActivateComponent` / `PoFxIdleComponent` to request D0 / D3 transitions.

---

## PMCSR Register (PCI Power Management)

**Location**: PCI config space, PM Capability offset `0x84` (NVL ACE).

| Bit(s) | Field | Values |
|--------|-------|--------|
| [1:0] | `PowerState` | 00=D0, 01=D1 (N/A), 10=D2 (N/A), 11=D3Hot |
| [8] | `PME_En` | 1=enable PME wake signaling |
| [15] | `PME_Status` | 1=PME event pending (write 1 to clear) |

Read/write from Windows (requires kernel access or PythonSV):
```python
# PythonSV
soc.ace.pcicfg(0, 0, 0, 0x84)                 # Read PMCSR
soc.ace.pcicfg(0, 0, 0, 0x84, value=0x0003)   # Write D3Hot
```

Windows does not expose PMCSR directly to userland. Use `powercfg` or Device Manager power properties to observe D-state transitions indirectly.

---

## Windows Registry Knobs

### PoFx Component Count and Idle Timeout
```
HKLM\SYSTEM\CurrentControlSet\Control\Class\{4D36E96C-E325-11CE-BFC1-08002BE10318}\0000\
```
| Value | Type | Purpose |
|-------|------|---------|
| `IdlePowerState` | REG_DWORD | Target idle D-state: 3 = D3Hot (default) |
| `ConservationIdleTime` | REG_DWORD | Idle timeout (ms) before D3 on battery |
| `PerformanceIdleTime` | REG_DWORD | Idle timeout (ms) before D3 on AC |
| `WakeEnabled` | REG_DWORD | 1=enable PME wake from D3 |

### Audio Device Power Caps (DEVPROPKEY)
These are set by the INF and read by Windows power framework:
```
DEVPKEY_Device_PowerData
DEVPKEY_Device_WakeFromD0
DEVPKEY_Device_WakeFromD3
```
> Inspect via `devcon driverfiles "PCI\VEN_8086&DEV_7728"` and look in the associated INF for `AddReg` entries with `{83DA6326-97A6-4088-9453-A1923F573B29}` (WDF power props).

### D3Cold Power Rail Control
```
HKLM\SYSTEM\CurrentControlSet\Control\Class\{4D36E96C-E325-11CE-BFC1-08002BE10318}\0000\
```
| Value | Type | Purpose |
|-------|------|---------|
| `D3ColdSupported` | REG_DWORD | 1=driver declares D3Cold support to ACPI |
| `EnableD3Cold` | REG_DWORD | 1=OS may remove power rail (ACPI `_PR3`) |

---

## S0ix Debug (Windows)

### powercfg Tools
```cmd
:: Run S0ix sleep study (5-minute trace, then generate HTML report)
powercfg /sleepstudy /duration 60 /output C:\Temp\sleepstudy.html
start C:\Temp\sleepstudy.html

:: Check active power requests blocking sleep
powercfg /requests

:: Check energy drains
powercfg /energy /duration 60 /output C:\Temp\energy.html

:: List devices preventing sleep
powercfg /devicequery wake_armed
powercfg /devicequery s0_enabled
```

### Reading the Sleep Study for Audio Blockers
In `sleepstudy.html`, look for:
- **ACE / IntcSST2** in the "Active Time" column — audio device not entering D3
- `PoFx Component` rows showing the audio device staying in D0 (idle refcount > 0)
- Active audio streams in `Audio Session` section — any active WASAPI session blocks D3

> **Common cause**: A background app (e.g. Cortana, Teams, browser) holds a WASAPI stream open, keeping ACE in D0. Use `powercfg /requests` to identify the process.

### Manual D3 Force (debug only)
```powershell
# PowerShell — force device to D3 via PnP stop/start cycle
$dev = Get-PnpDevice -FriendlyName "*Smart Sound*"
Disable-PnpDevice -InstanceId $dev.InstanceId -Confirm:$false
Enable-PnpDevice -InstanceId $dev.InstanceId -Confirm:$false
```

---

## LTR (Latency Tolerance Reporting)

LTR values are set by the driver and reported to the PCIe root port to allow platform power gating.

| LTR Field | Expected Value | If Wrong |
|-----------|---------------|----------|
| Snoop latency | ~125 µs | Platform won't gate; S0ix blocked |
| No-Snoop latency | ~125 µs | Platform won't gate; S0ix blocked |

Check via PythonSV:
```python
soc.ace.pcie.ltr_max_snoop_latency
soc.ace.pcie.ltr_max_nosnoop_latency
```
On Windows, LTR is reported by the driver (`WdfDeviceInitSetPowerPolicyOwnership` + LTR cap). If the driver reports latency = 0x00000000, the root port may refuse to gate.

---

## Windows Audio and MMCSS

The **Multimedia Class Scheduler Service (MMCSS)** boosts thread priority for real-time audio but can prevent aggressive power management:

```cmd
:: Check MMCSS service state
sc query MMCSS

:: MMCSS profiles (Playback keeps CPU awake at higher C-state)
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Audio"
```
| Registry Value | Type | Meaning |
|----------------|------|---------|
| `Priority` | REG_DWORD | Thread priority (default 2) |
| `Scheduling Category` | REG_SZ | `"Medium"` for audio |
| `SFIO Priority` | REG_SZ | `"Normal"` |

> If MMCSS is keeping CPU/ACE awake, verify no rogue audio client holds a stream open.

---

## D3 Entry Sequence Verification

The ACE driver must follow this exact D3 entry sequence (validated via WPP trace):
1. Stop all active PCM streams (CORB/RIRB idle, DMA stopped)
2. Stop SoundWire links (clock-stop sequence)
3. Idle DSP IPC (no pending messages)
4. Gate SRAM EBBs
5. Shut down PLL (ACE PLL off)
6. Write PMCSR[1:0] = 11b (D3Hot)
7. (For D3Cold) ACPI `_PS3` / `_PR3` power rail removal

**Verify via WPP ETL**: search for step sequence in `IntcSST2` / `IntcAudioBus` WPP trace.

If D3 entry fails mid-sequence (e.g. SRAM gate times out), S0ix will be blocked. Check:
```cmd
:: Examine Event Log for audio power errors
wevtutil qe System /q:"*[System[Level<=2]]" /f:text | findstr -i "audio\|IntcSST2\|IntcAudio"
```

---

## Common Windows Audio Power Failure Modes

### Failure: S0ix blocked by audio device
1. Run `powercfg /requests` — look for "DRIVER" entry from `IntcSST2` or `HdAudio`
2. Check active WASAPI sessions: Task Manager → Performance → not all audio session counts zero
3. Verify MMCSS is not holding D0: `sc query MMCSS`
4. Registry: set `ConservationIdleTime=500` to force faster idle entry
5. Check WPP trace for D3 entry sequence failure (see above)

### Failure: Audio dropout after D3/resume
1. D3 exit must reload DSP FW and re-enumerate codecs — if this fails, endpoints disappear
2. Check Windows event log for `IntcSST2` error events post-resume
3. Increase `IpcTimeout` in DSP parameters to allow more time for FW reload
4. Check `GCTL.CRST` cycle completes after D0 restore (HDA controller reset)
5. Verify `PME_Status` bit cleared after wake (write-1-to-clear in PMCSR)

### Failure: D3Cold not entering (power rail not removed)
1. Check `D3ColdSupported=1` and `EnableD3Cold=1` in registry
2. Check ACPI `_PR3` object exists for ACE device (iasl disassembly of DSDT)
3. Check parent bridge also supports D3Cold
4. Verify `powercfg /sleepstudy` shows ACE reaching D3Cold (not just D3Hot)

### Failure: PME wake from D3 not working
1. Check `WakeEnabled=1` in registry
2. Check `PME_En` bit set in PMCSR (bit 8)
3. Check ACPI `_PRW` (Power Resources for Wake) for ACE device
4. Check PCIe root port PME message routing to SCI/GPIO

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\power\`

Key test categories:
- `power_d3_entry\` — verify D3Hot entry after idle timeout
- `power_d3cold\` — verify D3Cold (power rail removal) during S0ix
- `power_s0ix_audio_blocker\` — verify audio device does not block S0ix
- `power_resume_integrity\` — verify audio endpoints survive D3→D0 cycle
- `power_ltr_values\` — verify LTR snoop/no-snoop latency values
- `power_pme_wake\` — verify PME wake from D3 triggers correctly

Run a specific test manually:
```cmd
cd C:\validation\windows-test-content\audio\power\power_d3_entry
python run_test.py --verbose --idle-timeout 2000
```
