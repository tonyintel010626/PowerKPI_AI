# TTK3 AI Agent Quick Reference

> Converted from TTK3_AI_AGENT_QUICK_REFERENCE.py for agent/skill discovery.

## Golden Reference Scripts

### 1. ttk3_spi_flash_programmer.py
**Primary tool for SPI flash programming operations.**

```bash
# Basic IFWI flash
python ttk3_spi_flash_programmer.py --image path/to/ifwi.bin

# Flash with backup
python ttk3_spi_flash_programmer.py --image path/to/ifwi.bin --backup

# Read current flash contents
python ttk3_spi_flash_programmer.py --read --output current_flash.bin

# Verify flash contents
python ttk3_spi_flash_programmer.py --verify path/to/ifwi.bin

# Detect chip information
python ttk3_spi_flash_programmer.py --detect
```

### 2. ttk3_automation_example.py
**Automation workflow template for multi-step operations.**

```bash
# Run full automation sequence
python ttk3_automation_example.py --config config.json

# Dry run (show steps without executing)
python ttk3_automation_example.py --config config.json --dry-run
```

### 3. ttk3_documentation_searcher.py
**Search TTK3 documentation and API references.**

```bash
# Search for API usage
python ttk3_documentation_searcher.py --query "PowerControl"

# List all available APIs
python ttk3_documentation_searcher.py --list-apis
```

## Programmatic API Quick Start

### Quick Flash IFWI
```python
from ttk3_spi_flash_programmer import quick_flash_ifwi
result = quick_flash_ifwi("path/to/ifwi.bin", backup=True)
```

### Quick Backup Flash
```python
from ttk3_spi_flash_programmer import quick_backup_flash
result = quick_backup_flash("backup_output.bin")
```

### Full Programmer with Config
```python
from ttk3_spi_flash_programmer import TTK3SPIFlashProgrammer, ProgrammingConfig

config = ProgrammingConfig(
    image_path="path/to/ifwi.bin",
    backup_before_flash=True,
    verify_after_flash=True,
    enable_logging=True
)

programmer = TTK3SPIFlashProgrammer(config)
result = programmer.program()
```

## Best Practices for AI Agents

1. **Always backup before flashing** - Use `--backup` flag or `backup=True` parameter
2. **Always verify after flashing** - Use `--verify` flag or check return status
3. **Enable logging** - Use `enable_logging=True` for full operation traceability
4. **Check device connectivity first** - Run `interface_check.py` before operations
5. **Power down before SPI access** - Platform must be in G3 state for reliable SPI operations
6. **Use 10-second minimum delay** for power cycles (15s recommended for hard cold boot)
7. **Parse JSON output** - All CLI scripts support JSON output for agent consumption

## Troubleshooting

| Issue | Likely Cause | Resolution |
|-------|-------------|------------|
| Device not found | TTK3/SQUID not connected | Check USB connection, run `detect_devices.py` |
| SPI chip not detected | Platform powered on | Power off platform first, then retry |
| Flash verification failed | Incomplete write | Re-flash with `--backup --verify` flags |
| POST code FFFF | Flash corruption or hardware issue | Run `comprehensive_diagnostics.py` |
| Power control timeout | PowerSplitter not responding | Check physical connections, try `verify_power.py` |

## Platform Notes

| Platform | Flash Size | Notes |
|----------|-----------|-------|
| Nova Lake S | 32MB | Primary validation platform |
| Arrow Lake | 32MB | Supported platform |

## Output File Structure

Operations produce output in the following structure:
```
output/
├── backups/
│   └── flash_backup_YYYYMMDD_HHMMSS.bin
├── logs/
│   └── operation_YYYYMMDD_HHMMSS.log
├── diagnostics/
│   └── results_YYYYMMDD_HHMMSS.json
└── reports/
    └── summary_YYYYMMDD_HHMMSS.md
```
