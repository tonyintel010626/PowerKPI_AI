# TTK3 Diagnostics Scripts

Standalone diagnostic scripts for TTK3 platform health checks. All scripts auto-detect the first available TTK3 device by default.

## Scripts

### interface_check.py - Pre-flight Validation

Quick check of which TTK3 interfaces are available before starting diagnostics.

```bash
# Auto-detect device
python interface_check.py

# Specify device serial
python interface_check.py --serial 883001B0916
```

**Checks:** Device connectivity, I2C bus, GPIO, PowerControl, Port80 POST codes.

### comprehensive_diagnostics.py - Full Health Assessment

Multi-aspect diagnostic suite with health scoring and FFFF root cause analysis.

```bash
# Run with JSON output
python comprehensive_diagnostics.py --output results.json

# Specify device
python comprehensive_diagnostics.py --serial 883001B0916 --output results.json
```

**Tests:** Device connectivity, firmware/hardware versions, SPI chip detection, BIOS version read, health scoring, FFFF assessment.

### enhanced_diagnostics.py - Power-Aware SPI Diagnostics

Safely powers down the platform before accessing SPI flash. Required when platform is running.

```bash
# Run and power back on when done
python enhanced_diagnostics.py

# Run and leave platform powered off (for subsequent SPI flashing)
python enhanced_diagnostics.py --keep-power-off

# Save results
python enhanced_diagnostics.py --output diag_results.json
```

**Tests:** Power state management, POST code capture, SPI flash with power-down safety, enhanced FFFF root cause analysis with confidence scoring.

## Recommended Workflow

```
1. interface_check.py          # Verify TTK3 connectivity
2. comprehensive_diagnostics.py # Full health assessment
3. enhanced_diagnostics.py      # If SPI access needed with power safety
```

## JSON Output Format

All scripts output structured JSON to stdout for agent/automation parsing:

```json
{
  "status": "success",
  "device_serial": "883001B0916",
  "timestamp": "2025-01-15T10:30:00",
  "health_score": 85,
  "tests": { ... },
  "ffff_assessment": { ... }
}
```

## Integration with Agents

These scripts are designed for invocation by TTK3-DIAG and FV_Debugger_V1 agents via the `bash` tool:

```python
import subprocess, json
result = subprocess.run(
    ['python', 'comprehensive_diagnostics.py', '--output', 'results.json'],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
if data['health_score'] < 50:
    # Trigger recovery workflow
    pass
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All diagnostics passed |
| 1 | One or more diagnostics failed (check JSON output) |
| 2 | Device not found or connection error |
