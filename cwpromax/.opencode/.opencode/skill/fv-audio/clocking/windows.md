# Clocking — Windows Debug Reference

> **Owner**: huiyingt (Tan Hui Ying)

> **Scope**: Windows-only ACE clock architecture validation — clock source verification, clock gating status, PLL lock, CRO/WoV clock, and S0ix clock behavior.
> **Platform**: NVL (ACE 4.x), extensible to PTL, LNL, MTL, ARL.

---

## Driver Stack

| Layer | Binary | Description |
|-------|--------|-------------|
| Intel audio bus | `IntcAudioBus.sys` | FNCFG.CGD clock gating init, XTAL config |
| Intel SST | `IntcSmartSound.sys` | DSP clock selection (FVS), PLL management |
| PMC integration | (kernel) | Clock request/ack handshake for S0ix |

---

## Device Enumeration

### Verify Clock State
```cmd
:: Clock state is not directly visible from Windows user-space
:: Use PythonSV for register-level clock verification
:: From Windows, verify functional indicators:

:: Check audio device working (implies clocks OK)
devcon status "PCI\VEN_8086&DEV_D328*"

:: Check DSP FW loaded (implies PLL locked)
sc query IntcSmartSound

:: Check DMIC working (implies XTAL 38.4 MHz active)
powershell -c "Get-PnpDevice | Where-Object {$_.FriendlyName -like '*Microphone*'} | Select-Object Status"
```

---

## Windows Registry Knobs

### Clock Debug Settings
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcSmartSound\Parameters\
```
| Value | Type | Purpose |
|-------|------|---------|
| `ForceFullPerformance` | REG_DWORD | 1=keep ACE PLL at max VCO (disable dynamic scaling) |
| `DisableClockGating` | REG_DWORD | 1=prevent FNCFG.CGD=0 (keep all clocks running) |
| `LogLevel` | REG_DWORD | WPP verbosity — clock events at level 3+ |

### WoV Clock Settings
```
HKLM\SYSTEM\CurrentControlSet\Services\IntcSmartSound\Parameters\WoV\
```
| Value | Type | Purpose |
|-------|------|---------|
| `CroClockEnable` | REG_DWORD | 1=enable CRO for ultra-low-power WoV |
| `ForceXtalForWoV` | REG_DWORD | 1=use XTAL instead of CRO for WoV (debug, higher power) |

---

## ETW / WPP Trace Capture

### Capture Clock Transition Events
```cmd
:: Extract TMF
tracepdb.exe -f %SystemRoot%\System32\drivers\IntcSmartSound.pdb -p C:\Temp\SstTmf

:: Start trace
logman create trace ClockTrace ^
  -p {GUID-IntcSmartSound} 0xFFFFFFFF 0xFF ^
  -o C:\Temp\Clock.etl -mode Circular -nb 16 256
logman start ClockTrace

:: Trigger clock transitions: play audio → stop → sleep → wake, then:
logman stop ClockTrace
tracefmt C:\Temp\Clock.etl -tmf C:\Temp\SstTmf -o C:\Temp\Clock.txt
```

### Key Trace Events
| Pattern | Meaning |
|---------|---------|
| `PLL_LOCK` / `PLL_UNLOCK` | ACE PLL lock state change |
| `FVS=` | DSP VCO frequency select changed |
| `CGD=` | Clock gating disable state |
| `CRO_ENABLE` / `CRO_DISABLE` | CRO for WoV enabled/disabled |
| `XTAL_ON` / `XTAL_OFF` | XTAL oscillator power state |
| `CLOCK_REQ` / `CLOCK_ACK` | Chassis 2.2 clock handshake |

---

## Common Failure Modes

### Failure: No audio after boot (clock not running)
1. Check `FNCFG.CGD` — if 1, BIOS failed to enable clock gating init
2. Check PLL lock: PythonSV `soc.ace.hda.bar4.intclkctl` — FVS field
3. Check XTAL strap: `XOCFS` = 01b for 38.4 MHz
4. Try `DisableClockGating=1` registry to keep all clocks running

### Failure: DSP FW load timeout (PLL not locked)
1. ACE PLL must be locked before DSP can boot
2. Check `CLKINTE=1` and `CLKINTHP=1` in platform config
3. WPP trace: search for `PLL_LOCK` event — if absent, PLL never locked
4. Check power rail: VnnAON iCLK (1.05V) must be present

### Failure: Audio drift/glitch (clock coherency violation)
1. All audio clocks must derive from common XTAL reference
2. UAOL requires xHCI XTAL coherent with ACE clocks
3. Check for ASRC (sample rate conversion) — should not be needed if clocks coherent
4. PythonSV: verify XTAL → PLL → divider chain is intact

### Failure: S0ix blocked (clock not gating)
1. Check ACE PLL is not still running in S0ix
2. Active PLL prevents package-level clock gating → S0ix blocked
3. Run `print_s0ix_y_blocking_conditions` doctor script
4. Check `print_LTRs` for ACE device reporting active LTR
5. WPP trace: `XTAL_OFF` should appear before S0ix entry

### Failure: WoV clock switch hangs DSP
1. CRO↔XTAL switch only during WoV arm/disarm transitions
2. Never switch mid-stream — see `wov/SKILL.md` for sequence
3. Check `CLKSTS.WOVROSCS` confirms trunk switched
4. WPP trace: `CRO_ENABLE` timing relative to DSP pipeline state

---

## NGA Validation Tests (Windows)

Test content: `C:\validation\windows-test-content\audio\clocking\`

Key test categories:
- `clock_gating_verify\` — FNCFG.CGD state after init
- `pll_lock_check\` — ACE PLL lock timing and stability
- `clock_coherency\` — verify no audio drift during long playback
- `s0ix_clock_gating\` — verify clocks gate during S0ix
- `wov_cro_switch\` — CRO clock switch for WoV arm/disarm

Run manually:
```cmd
cd C:\validation\windows-test-content\audio\clocking\clock_gating_verify
python run_test.py --verbose
```
