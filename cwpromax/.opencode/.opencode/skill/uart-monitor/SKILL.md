---
name: uart-monitor
disable: false
description: "UART serial port monitoring for BIOS boot logs and EC/Embedded Controller logs with RealTerm CLI and PySerial capture"
license: MIT
---

# UART Monitor Skill

## Script Location

All scripts are located at: `<cwd>/.opencode/skill/uart-monitor/`

## Overview

This skill provides UART serial port monitoring capabilities for capturing and analyzing BIOS boot logs and EC (Embedded Controller) debug output. It supports four capture backends — RealTerm COM/ActiveX automation (primary), RealTerm native CLI (first fallback), RealTerm CLI for send operations, and PySerial (second fallback) — with real-time live viewing, pattern-based stop triggers, multi-port simultaneous capture, and comprehensive log analysis including boot phase timing, POST code correlation, and error pattern detection.

### Key Capabilities

1. **Boot log capture** — Capture UART output to timestamped log files
2. **Error pattern analysis** — Detect BIOS errors, ASSERT failures, hardware init failures
3. **Port discovery** — Auto-detect available COM ports with descriptions
4. **Pattern-based stop trigger** — Stop capture when a regex pattern is matched
5. **POST code correlation** — Cross-reference POST codes with UART log events
6. **Live console output** — Real-time display of UART data during capture
7. **Boot phase timing** — Track SEC → PEI → DXE → BDS → OS phase transitions
8. **Continuous monitor mode** — Long-running capture without duration limit
9. **UART send/write** — Send strings or file contents to the UART port
10. **Multi-port simultaneous capture** — Capture from multiple COM ports at once

## Prerequisites

- **Python 3.8+**
- **pyserial >= 3.5** — Serial port access and port discovery
- **pywin32 >= 306** — RealTerm COM/ActiveX automation (Windows only)
- **RealTerm** (optional but recommended) — Installed at `C:\Program Files (x86)\BEL\Realterm\realterm.exe`

Install dependencies:

```bash
pip install -r <cwd>/.opencode/skill/uart-monitor/requirements.txt
```

## Available Scripts

### 1. `bios_uart_capture.py` — UART Capture & Send

Main capture script with four internal backends:

| Backend | Method | Best For |
|---------|--------|----------|
| `realterm-com` | COM/ActiveX automation (`realterm.realtermintf`) | Hidden headless capture, production use, advanced features |
| `realterm-native` | Native `realterm.exe` CLI (`/capture` flag) | Standalone capture, validation engineer workflows, first fallback |
| `realterm-cli` | Subprocess + `FIRST` param | Sending commands to running RealTerm instance |
| `pyserial` | Direct serial byte reads | Live console streaming, port discovery, cross-platform fallback |

The script auto-selects the best available backend if `--backend` is not specified.

**Auto-selection priority:** `realterm-com` → `realterm-native` → `realterm-cli` → `pyserial`
**Exception:** `--live` flag prefers `pyserial` for direct byte-level console streaming.

### Backend Selection Guide

- **`realterm-com`** (Primary) — Best for automated/headless capture. Requires `pywin32` and RealTerm installed. Supports hardware DataTrigger, character count verification, and send+capture simultaneously.
- **`realterm-native`** (Fallback 1) — Uses native `realterm.exe /capture` CLI directly. No `pywin32` dependency — only needs `realterm.exe` on the system. Simple, reliable, familiar to validation engineers. Capture-only (no send during capture).
- **`realterm-cli`** (Fallback 2) — Designed for sending commands to an already-running RealTerm GUI instance via the `FIRST` parameter. Not optimized for standalone capture.
- **`pyserial`** (Fallback 3) — Pure Python fallback. Works cross-platform (Windows/Linux/macOS). Best for live console streaming and port discovery. No RealTerm dependency.

### 2. `log_analyzer.py` — Log Analysis Engine

Offline analysis of captured UART logs. Detects boot phases, errors, POST code correlations, and determines overall boot status.

## Capture Operations

### List Available COM Ports

```bash
python <cwd>/.opencode/skill/uart-monitor/bios_uart_capture.py --list-ports
```

Returns JSON array of detected ports with descriptions.

### Basic Capture (30 seconds)

```bash
python <cwd>/.opencode/skill/uart-monitor/bios_uart_capture.py --port COM8 --baud 115200 --duration 30 --output boot_log.txt
```

### Capture with Live Console Output

```bash
python <cwd>/.opencode/skill/uart-monitor/bios_uart_capture.py --port COM8 --duration 60 --output boot_log.txt --live
```

### Capture Until Pattern Match (e.g., OS handoff)

```bash
python <cwd>/.opencode/skill/uart-monitor/bios_uart_capture.py --port COM8 --output boot_log.txt --until "ExitBootServices|Shell>"
```

### Continuous Monitor Mode (no time limit)

```bash
python <cwd>/.opencode/skill/uart-monitor/bios_uart_capture.py --port COM8 --output boot_log.txt --continuous --live
```

Stop with Ctrl+C. The log file is saved on exit.

### Force a Specific Backend

```bash
# Force RealTerm native CLI capture (first fallback)
python <cwd>/.opencode/skill/uart-monitor/bios_uart_capture.py --port COM8 --duration 30 --output boot_log.txt --backend realterm-native

# Force PySerial capture (second fallback)
python <cwd>/.opencode/skill/uart-monitor/bios_uart_capture.py --port COM8 --duration 30 --output boot_log.txt --backend pyserial
```

### JSON Output Mode

```bash
python <cwd>/.opencode/skill/uart-monitor/bios_uart_capture.py --port COM8 --duration 10 --output boot_log.txt --json
```

Returns structured JSON with `status`, `output_file`, `bytes_captured`, `duration`, `backend_used`.

## Send / Write Operations

### Send a String to UART

```bash
python <cwd>/.opencode/skill/uart-monitor/bios_uart_capture.py --port COM8 --send "reset\r\n"
```

Supports escape sequences: `\r`, `\n`, `\t`.

### Send File Contents to UART

```bash
python <cwd>/.opencode/skill/uart-monitor/bios_uart_capture.py --port COM8 --sendfile commands.txt
```

### Send + Capture Response

```bash
python <cwd>/.opencode/skill/uart-monitor/bios_uart_capture.py --port COM8 --send "version\r\n" --duration 5 --output response.txt --live
```

## Multi-Port Simultaneous Capture

Capture from multiple COM ports at once (e.g., BIOS UART + EC UART):

```bash
python <cwd>/.opencode/skill/uart-monitor/bios_uart_capture.py --port COM8,COM9 --duration 30 --output bios_log.txt,ec_log.txt --live
```

Each port gets its own output file. All ports are captured concurrently using threads.

## Log Analysis

### Full Analysis (text report)

```bash
python <cwd>/.opencode/skill/uart-monitor/log_analyzer.py --input boot_log.txt
```

### JSON Analysis Output

```bash
python <cwd>/.opencode/skill/uart-monitor/log_analyzer.py --input boot_log.txt --json
```

Returns structured JSON with `boot_status`, `boot_phases`, `errors`, `postcodes`, `total_boot_time_seconds`, `summary`.

### Errors Only

```bash
python <cwd>/.opencode/skill/uart-monitor/log_analyzer.py --input boot_log.txt --errors-only
```

### With POST Code Correlation

```bash
python <cwd>/.opencode/skill/uart-monitor/log_analyzer.py --input boot_log.txt --postcodes postcode_log.txt --json
```

Cross-references POST code transitions (from TTK3 Port80 capture) with UART log timestamps to identify which BIOS module was active at each POST code.

## Boot Phase Detection

The analyzer tracks these UEFI boot phases and their transition markers:

| Phase | Detection Pattern | Typical POST Codes |
|-------|------------------|--------------------|
| **SEC** | `SEC:` prefix, `SEC Entry`, `Reset Vector` | 0x01–0x0F |
| **PEI** | `PEI:` prefix, `PEI Entry`, `PEIM` | 0x10–0x2F |
| **DXE** | `DXE:` prefix, `DXE Entry`, `DXE Dispatcher` | 0x30–0x6F |
| **BDS** | `BDS:` prefix, `BDS Entry`, `Boot Device Selection` | 0x70–0x8F |
| **OS** | `OS Boot:`, `Starting.*OS`, `GRUB`, `Linux version`, `ntoskrnl` | 0x90–0xFF |

Boot status is determined as:
- **BOOT_SUCCESS** — Reached OS phase with no critical/high-severity errors
- **BOOT_FAILURE** — Critical/high errors detected, or boot fell to EFI Shell
- **BOOT_PARTIAL** — Some phases completed but did not reach OS
- **BOOT_UNKNOWN** — No phase markers detected (may not be a BIOS log)

## Error Pattern Reference

The analyzer detects these BIOS error categories:

| Category | Severity | Example Patterns |
|----------|----------|-----------------|
| ASSERT failure | High | `ASSERT: module.c(line)`, `ASSERT failed` |
| Memory error | Critical | `Memory Init Failed`, `DIMM.*error`, `ECC error` |
| PCIe error | High | `PCIe.*error`, `Link Training Failed` |
| Storage error | High | `NVMe.*fail`, `SATA.*error`, `eMMC.*fail` |
| GOP/Display error | Medium | `GOP.*fail`, `No display found` |
| USB error | Medium | `USB.*error`, `XHCI.*fail` |
| TPM error | Medium | `TPM.*error`, `TPM not detected` |
| Thermal error | High | `Thermal.*critical`, `CPU overtemp` |
| Boot failure | Critical | `Boot.*fail`, `No bootable device` |
| Timeout | Medium | `Timeout`, `PXE.*timeout` |
| Generic error | Medium | `(?i)\bERROR\b`, `(?i)\bFAILED\b` |

## Configuration

### Common Baud Rates

| Use Case | Baud Rate |
|----------|-----------|
| Standard BIOS UART | 115200 (default) |
| High-speed debug | 921600 |
| EC debug | 57600 or 115200 |
| Legacy serial | 9600 |

### Flow Control

| Value | Mode |
|-------|------|
| 0 | None (default, most common for BIOS UART) |
| 2 | RTS/CTS hardware flow control |
| 3 | XON/XOFF software flow control |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REALTERM_PATH` | Path to RealTerm executable | Auto-detected from Program Files |
| `UART_DEFAULT_BAUD` | Default baud rate | `115200` |
| `UART_DEFAULT_PORT` | Default COM port | None (must specify or use `--list-ports`) |

## Limitations

- **Windows only** — RealTerm COM/ActiveX and RealTerm CLI backends require Windows. PySerial backend works cross-platform but RealTerm features are unavailable on Linux/macOS.
- **COM port locking** — Only one process can open a COM port at a time. If RealTerm or another tool has the port open, capture will fail with "Access Denied". Close other serial tools first.
- **RealTerm COM registration** — The `realterm.realtermintf` COM object must be registered. If RealTerm was installed normally, this is automatic. If not, run `regsvr32 realterm.dll`.
- **EC log analysis** — Error patterns are currently tuned for BIOS/UEFI boot logs. EC-specific patterns (fan control, battery, thermals) are a future enhancement.
- **Timestamp formats** — The analyzer supports `[HH:MM:SS.mmm]`, `[MM:SS.mmm]`, `[SS.mmm]`, and ISO 8601 timestamps. Other formats may not be parsed.

## Troubleshooting

### "Access Denied" on COM port

Another process has the port open. Check:
```bash
python <cwd>/.opencode/skill/uart-monitor/bios_uart_capture.py --list-ports
```
If the port is listed but capture fails, close RealTerm, PuTTY, or other serial tools.

### RealTerm COM backend fails

1. Verify RealTerm is installed: check `C:\Program Files (x86)\BEL\Realterm\realterm.exe`
2. Verify COM registration: run `python -c "import win32com.client; print(win32com.client.Dispatch('realterm.realtermintf'))"`
3. Fall back to RealTerm native CLI: use `--backend realterm-native` (no pywin32 needed, only requires realterm.exe)
4. Fall back to PySerial: use `--backend pyserial`

### No data captured

1. Verify baud rate matches the target device (115200 for most BIOS UARTs)
2. Verify physical connection — TX/RX pins, ground, correct COM port
3. Use `--live` to see if any data arrives in real-time
4. Try flow control `--flow 0` (none) if hardware flow control is blocking

### Analyzer reports BOOT_UNKNOWN

The log may not contain standard UEFI phase markers. This can happen with:
- EC logs (not BIOS logs)
- Non-UEFI firmware (coreboot, U-Boot)
- Partial captures that missed the boot start

## Support

For issues with this skill, check the scripts' `--help` output:

```bash
python <cwd>/.opencode/skill/uart-monitor/bios_uart_capture.py --help
python <cwd>/.opencode/skill/uart-monitor/log_analyzer.py --help
```
