---
name: ttk3/diagnostics
description: TTK3 Flash Diagnostics and Platform Health Checks with scoring
---

# TTK3 Flash Diagnostics

Flash diagnostics skill for comprehensive SPI flash health assessment. Runs a configurable suite of diagnostic tests and produces a health score percentage.

## Quick Start

```python
from ttk3_agent_platform.skills.flash_diagnostics_skill import FlashDiagnosticsSkill
from ttk3_agent_platform.tools import create_default_registry
from ttk3_agent_platform.core.event_store import EventStore

event_store = EventStore()  # Required: SQLite-backed event/audit logging
tools = create_default_registry(event_store)
skill = FlashDiagnosticsSkill(tools)
result = await skill.execute({
    "tests": ["chip_detect", "read_test", "region_check", "version_check"],
    "min_health_score": 50
})
print(f"Health: {result.data['health_score']}%")
```

## Available Tests

| Test | Description |
|------|-------------|
| `chip_detect` | Detect and identify the SPI flash chip |
| `read_test` | Read flash data and verify accessibility |
| `region_check` | Validate BIOS, ME, and GBE flash regions |
| `version_check` | Read and verify BIOS/IFWI version strings |
| `mac_check` | Read and validate the MAC address |
| `serial_check` | Read and validate the serial number |

## API Reference

### Running Diagnostics

```python
from ttk3_agent_platform.skills.flash_diagnostics_skill import FlashDiagnosticsSkill
from ttk3_agent_platform.tools import create_default_registry
from ttk3_agent_platform.core.event_store import EventStore

event_store = EventStore()  # Required: SQLite-backed event/audit logging
tools = create_default_registry(event_store)
skill = FlashDiagnosticsSkill(tools)

# Run all tests
result = await skill.execute({
    "tests": ["chip_detect", "read_test", "region_check", "version_check", "mac_check", "serial_check"],
    "min_health_score": 50
})

# Run specific tests only
result = await skill.execute({
    "tests": ["chip_detect", "version_check"],
    "min_health_score": 0
})

# Result structure
if result.success:
    data = result.data
    print(f"Health Score: {data['health_score']}%")
    print(f"Tests Passed: {data['passed']} / {data['total']}")
    for test_name, test_result in data['test_results'].items():
        status = "PASS" if test_result['passed'] else "FAIL"
        print(f"  {test_name}: {status} - {test_result.get('detail', '')}")
```

### Platform Health Check (using skill)

```python
from ttk3_agent_platform.skills.platform_health_check_skill import PlatformHealthCheckSkill
from ttk3_agent_platform.tools import create_default_registry
from ttk3_agent_platform.core.event_store import EventStore

event_store = EventStore()  # Required: SQLite-backed event/audit logging
tools = create_default_registry(event_store)
skill = PlatformHealthCheckSkill(tools)
result = await skill.execute({})
# Multi-aspect health scoring across device, power, flash, and communication
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| tests | list[str] | all tests | List of test names to run |
| min_health_score | int | 50 | Minimum passing health score (0-100) |

## Notes

- Health score is calculated as (passed_tests / total_tests) * 100
- Region check tests bios, me, and gbe flash regions
- If min_health_score is not met, the skill result reports failure even if individual tests pass

## TTK3 Device Health Verification (Learned from NVL-S Debug Session)

### Pre-Debug Checklist
Before starting any debug session, verify TTK3 device health:
1. **Device discovery** — confirm TTK3 device is detected via `Ttk3Device.GetNumConnectedDevices()`
2. **Firmware revision** — check with `GetFirmwareRevision()` (verified working; NVL-S host returned FW rev 130)
3. **SPI chip detect** — run `BiosProgrammer.DetectChip()` to confirm SPI bus is functional
4. **Power control** — verify `PowerControl.OpenPowerSplitter()` and `GetPortState()` respond correctly
5. **POST code reader** — verify `Port80.Open()` and `Read()` return a value

### Validated vs Unvalidated TTK3 Interfaces
| Interface | Health Check Method | Status |
|-----------|-------------------|--------|
| Ttk3Device | `Open()`, `GetNumConnectedDevices()`, `GetFirmwareRevision()` | **VALIDATED** |
| BiosProgrammer (SPI) | `Open()`, `DetectChip()` | **VALIDATED** |
| PowerControl | `OpenPowerSplitter()`, `GetPortState()` | **VALIDATED** |
| Port80 (POST code) | `Open()`, `Read()` | **VALIDATED** |
| I2cControl | `Open()`, `SetClock()`, `Read()` | **NOT VALIDATED** |
| GPIO | Constructor fails (_controller bug) | **NOT VALIDATED** |
| UART | Only `BiosLogEnable`/`BiosLogDisable` available | **NOT VALIDATED** |

### API Version Awareness
- `Detect_Connected_Devices` module is **Linux-only** — fails on Windows hosts
- Use `Ttk3Device` class instead for Windows-based device discovery
- Always check platform (Windows vs Linux) before selecting discovery method

## CLI Diagnostic Scripts

Pre-built standalone scripts for platform diagnostics. All scripts auto-detect the first available TTK3 device, or accept `--serial` to target a specific device. All output JSON to stdout for agent parsing.

| Script | Usage | Description |
|--------|-------|-------------|
| `comprehensive_diagnostics.py` | `python comprehensive_diagnostics.py [--serial SN] [--output result.json]` | Full device + SPI health check with scoring and POST FFFF root cause assessment |
| `enhanced_diagnostics.py` | `python enhanced_diagnostics.py [--serial SN] [--output result.json] [--keep-power-off]` | Power-aware diagnostics: powers down platform before SPI access, POST code monitoring, enhanced FFFF assessment |
| `interface_check.py` | `python interface_check.py [--serial SN]` | Pre-flight validation of all TTK3 interfaces (Device, I2C, GPIO, Power, POST code) |

### Running Diagnostic Scripts

```bash
# Pre-flight check before any debug session
python .opencode/skill/ttk3/diagnostics/interface_check.py

# Full health check with JSON output file
python .opencode/skill/ttk3/diagnostics/comprehensive_diagnostics.py --output results.json

# Power-aware SPI diagnostics (keeps platform powered off after)
python .opencode/skill/ttk3/diagnostics/enhanced_diagnostics.py --keep-power-off

# Target a specific TTK3 device
python .opencode/skill/ttk3/diagnostics/comprehensive_diagnostics.py --serial 883001B0916
```

### Script Output Format

All diagnostic scripts output JSON to stdout:

```json
{
  "status": "success",
  "device_serial": "883001B0916",
  "health_score": 85,
  "tests": {
    "device_connectivity": {"passed": true, "detail": "Device connected"},
    "spi_chip_detect": {"passed": true, "detail": "Chip detected"},
    "bios_readable": {"passed": false, "detail": "Read failed"}
  },
  "ffff_assessment": {
    "flash_corruption_likely": true,
    "hardware_issue_likely": false,
    "recommendation": "Re-flash IFWI image"
  }
}
```

### When to Use Which Script

| Scenario | Recommended Script |
|----------|--------------------|
| Start of any debug session | `interface_check.py` |
| Platform stuck at POST FFFF | `comprehensive_diagnostics.py` |
| Need SPI access (flash read/write) | `enhanced_diagnostics.py --keep-power-off` |
| Quick health assessment | `comprehensive_diagnostics.py` |
| Validating after IFWI re-flash | `comprehensive_diagnostics.py` |
