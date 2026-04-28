#!/usr/bin/env python3
"""
BIOS UART Log Analyzer — Post-capture analysis engine for UART boot logs.

Features:
  - Error pattern detection (BIOS, EC, platform errors)
  - Boot phase timing (SEC -> PEI -> DXE -> BDS -> OS)
  - POST code correlation (merge UART + Port80 timelines)
  - Structured JSON + text summary output

Usage:
  python log_analyzer.py --input boot.log
  python log_analyzer.py --input boot.log --json --output analysis.json
  python log_analyzer.py --input boot.log --postcodes postcode_log.txt
  python log_analyzer.py --input boot.log --errors-only
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# Error Pattern Library
# =============================================================================

# BIOS error patterns — ordered by severity (critical first)
BIOS_ERROR_PATTERNS: List[Dict[str, Any]] = [
    # Critical hardware errors
    {"pattern": r"(?i)\bMCA\b.*(?:error|exception|bank)", "category": "MCA", "severity": "critical",
     "description": "Machine Check Architecture error — hardware fault detected"},
    {"pattern": r"(?i)\bPANIC\b", "category": "PANIC", "severity": "critical",
     "description": "System panic — unrecoverable firmware error"},
    {"pattern": r"(?i)\bDEAD\s*LOOP\b", "category": "DEAD_LOOP", "severity": "critical",
     "description": "Dead loop detected — firmware stuck"},
    {"pattern": r"(?i)\bTRIPLE\s+FAULT\b", "category": "TRIPLE_FAULT", "severity": "critical",
     "description": "Triple fault — CPU reset imminent"},

    # Firmware phase errors
    {"pattern": r"(?i)\bSEC\s+ERROR\b", "category": "SEC_ERROR", "severity": "critical",
     "description": "Security phase error — early boot failure"},
    {"pattern": r"(?i)\bPEI\s+ERROR\b", "category": "PEI_ERROR", "severity": "critical",
     "description": "Pre-EFI Initialization error"},
    {"pattern": r"(?i)\bDXE\s+ERROR\b", "category": "DXE_ERROR", "severity": "high",
     "description": "Driver Execution Environment error"},
    {"pattern": r"(?i)\bBDS\s+ERROR\b", "category": "BDS_ERROR", "severity": "high",
     "description": "Boot Device Selection error"},

    # ASSERT / FAULT
    {"pattern": r"(?i)\bASSERT\b.*(?:failed|\()", "category": "ASSERT", "severity": "high",
     "description": "Firmware assertion failure"},
    {"pattern": r"(?i)\bFAULT\b(?!\s*toleran)", "category": "FAULT", "severity": "high",
     "description": "Processor or bus fault"},
    {"pattern": r"(?i)\bEXCEPTION\b.*(?:handler|vector|\d)", "category": "EXCEPTION", "severity": "high",
     "description": "CPU exception triggered"},

    # Boot failures
    {"pattern": r"(?i)POST\s+CODE[:\s]+0*[Ff]{2,4}\b", "category": "POST_FF", "severity": "critical",
     "description": "POST code FF — boot failure / no progress"},
    {"pattern": r"(?i)\bRECOVERY\s+MODE\b", "category": "RECOVERY", "severity": "high",
     "description": "System entered recovery mode"},
    {"pattern": r"(?i)\bCAPSULE\s+(?:ERROR|FAIL)", "category": "CAPSULE_ERROR", "severity": "high",
     "description": "Firmware capsule update failure"},
    {"pattern": r"(?i)\bBSOD\b", "category": "BSOD", "severity": "critical",
     "description": "Blue Screen of Death indicator"},

    # General errors
    {"pattern": r"(?i)\bERROR\b", "category": "ERROR", "severity": "medium",
     "description": "Generic error message"},
    {"pattern": r"(?i)\bFAIL(?:ED|URE)?\b", "category": "FAIL", "severity": "medium",
     "description": "Operation failure"},
    {"pattern": r"(?i)\bTIMEOUT\b", "category": "TIMEOUT", "severity": "medium",
     "description": "Operation timeout"},
    {"pattern": r"(?i)\bHANG\b", "category": "HANG", "severity": "high",
     "description": "System hang detected"},
    {"pattern": r"(?i)\bWARNING\b", "category": "WARNING", "severity": "low",
     "description": "Warning message"},
]

# EC/Embedded Controller error patterns (placeholder for future expansion)
EC_ERROR_PATTERNS: List[Dict[str, Any]] = [
    {"pattern": r"(?i)\bEC\s+(?:ERROR|FAIL)", "category": "EC_ERROR", "severity": "high",
     "description": "Embedded Controller error"},
    {"pattern": r"(?i)\bTHERMAL\s+(?:TRIP|SHUTDOWN|CRITICAL)", "category": "THERMAL", "severity": "critical",
     "description": "Thermal protection triggered"},
    {"pattern": r"(?i)\bFAN\s+(?:FAIL|ERROR|STALL)", "category": "FAN_FAIL", "severity": "high",
     "description": "Fan failure detected"},
    {"pattern": r"(?i)\bBATTERY\s+(?:CRITICAL|FAIL|ERROR)", "category": "BATTERY", "severity": "high",
     "description": "Battery critical condition"},
    {"pattern": r"(?i)\bPOWER\s+RAIL\s+(?:FAIL|ERROR|FAULT)", "category": "POWER_RAIL", "severity": "critical",
     "description": "Power rail failure"},
]

ALL_ERROR_PATTERNS = BIOS_ERROR_PATTERNS + EC_ERROR_PATTERNS


# =============================================================================
# Boot Phase Detection
# =============================================================================

# Boot phase markers — patterns that indicate phase transitions
BOOT_PHASE_MARKERS: List[Dict[str, str]] = [
    # SEC phase (Security)
    {"phase": "SEC", "pattern": r"(?i)(?:SEC\s+(?:phase|entry|start|init)|SecStartupWithFsp|"
                                r"Reset\s+vector|SEC\s+Core|SecMain)"},
    # PEI phase (Pre-EFI Initialization)
    # NOTE: Must NOT match SEC lines like "SEC: PEI Core Entry Point" — require PEI: prefix or PeiMain
    {"phase": "PEI", "pattern": r"(?i)(?:^[\[\d:.:\s\]]*PEI\s*:\s|PEI\s+(?:phase|entry|start|init)|PeiMain|"
                                r"PEI\s+Services|Install\s+PEI|PeiDispatcher|"
                                r"Memory\s+(?:Init|Training|Detected))"},
    # DXE phase (Driver Execution Environment)
    {"phase": "DXE", "pattern": r"(?i)(?:DXE\s+(?:phase|entry|start|init|Core|Main)|DxeMain|"
                                r"DXE\s+Services|DXE\s+Dispatcher|Loading\s+driver|"
                                r"DxeCore)"},
    # BDS phase (Boot Device Selection)
    {"phase": "BDS", "pattern": r"(?i)(?:BDS\s+(?:phase|entry|start|init)|BdsEntry|"
                                r"Boot\s+Device\s+Selection|Boot\s+Option|"
                                r"BdsLibConnectAll|Attempting\s+boot)"},
    # OS Handoff / Shell — NOTE: ExitBootServices is still DXE/BDS, not OS
    # NOTE: Must NOT match BDS boot option lines like "BDS: Boot0000 - Windows Boot Manager"
    # Only match actual OS loader execution or Shell prompt
    {"phase": "OS", "pattern": r"(?i)(?:Shell>|UEFI\s+Shell|OS\s+(?:handoff|Loader|Boot)|"
                               r"Control\s+transferred\s+to\s+OS|"
                               r"Starting\s+(?:Windows|Linux)|Grub\s+loading|"
                               r"Loading\s+BOOTX64\.efi)"},
]


# =============================================================================
# Timestamp Parsing
# =============================================================================

# Common timestamp formats in UART logs
TIMESTAMP_PATTERNS = [
    # [MM:SS.mmm] — our default capture format (minutes:seconds.milliseconds)
    (r"\[(\d{2}:\d{2}\.\d{3})\]", "mm_ss_ms"),
    # [HH:MM:SS.mmm] — full timestamp format
    (r"\[(\d{2}:\d{2}:\d{2}\.\d{3})\]", "%H:%M:%S.%f"),
    # [HH:MM:SS] — simpler format
    (r"\[(\d{2}:\d{2}:\d{2})\]", "%H:%M:%S"),
    # YYYY-MM-DD HH:MM:SS.mmm
    (r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})", "%Y-%m-%d %H:%M:%S.%f"),
    # MM/DD/YYYY HH:MM:SS
    (r"(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})", "%m/%d/%Y %H:%M:%S"),
    # Seconds since boot: [    1.234567]
    (r"\[\s*(\d+\.\d+)\]", "seconds_since_boot"),
]


def parse_timestamp(line: str) -> Optional[float]:
    """Extract timestamp from a log line as seconds since first timestamp.

    Returns seconds as float, or None if no timestamp found.
    """
    for pattern, fmt in TIMESTAMP_PATTERNS:
        match = re.search(pattern, line)
        if match:
            ts_str = match.group(1)
            if fmt == "seconds_since_boot":
                return float(ts_str)
            if fmt == "mm_ss_ms":
                # Parse MM:SS.mmm -> seconds
                try:
                    parts = ts_str.split(":")
                    minutes = int(parts[0])
                    seconds = float(parts[1])
                    return minutes * 60 + seconds
                except (ValueError, IndexError):
                    continue
            try:
                dt = datetime.strptime(ts_str, fmt)
                # Convert to seconds since midnight
                return dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1_000_000
            except ValueError:
                continue
    return None


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration string."""
    if seconds < 0.001:
        return "0.000s"
    if seconds < 60:
        return f"{seconds:.3f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.3f}s"


def format_timestamp(seconds: float) -> str:
    """Format seconds into MM:SS.mmm timestamp string."""
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes:02d}:{secs:06.3f}"


# =============================================================================
# Core Analysis Functions
# =============================================================================

def analyze_errors(lines: List[str], patterns: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Scan log lines for error patterns.

    Args:
        lines: List of log lines to analyze.
        patterns: Error patterns to match against. Defaults to ALL_ERROR_PATTERNS.

    Returns:
        List of error dicts with line number, timestamp, category, severity, text.
    """
    if patterns is None:
        patterns = ALL_ERROR_PATTERNS

    errors: List[Dict[str, Any]] = []
    seen_categories: Dict[str, int] = {}  # Track first occurrence per category

    for line_num, line in enumerate(lines, 1):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        for pat in patterns:
            if re.search(pat["pattern"], line_stripped):
                ts = parse_timestamp(line_stripped)
                error_entry: Dict[str, Any] = {
                    "line": line_num,
                    "timestamp": format_timestamp(ts) if ts is not None else None,
                    "timestamp_sec": ts,
                    "category": pat["category"],
                    "severity": pat["severity"],
                    "description": pat["description"],
                    "text": line_stripped[:200],  # Truncate long lines
                }

                # Track first occurrence
                if pat["category"] not in seen_categories:
                    seen_categories[pat["category"]] = line_num
                    error_entry["first_occurrence"] = True
                else:
                    error_entry["first_occurrence"] = False

                errors.append(error_entry)
                break  # Only match first (highest severity) pattern per line

    return errors


def detect_boot_phases(lines: List[str]) -> List[Dict[str, Any]]:
    """Detect BIOS boot phase transitions from log content.

    Returns:
        List of phase dicts with phase name, start line, timestamp.
    """
    phases: List[Dict[str, Any]] = []
    detected_phases: set = set()

    for line_num, line in enumerate(lines, 1):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        for marker in BOOT_PHASE_MARKERS:
            if marker["phase"] not in detected_phases:
                if re.search(marker["pattern"], line_stripped):
                    ts = parse_timestamp(line_stripped)
                    phases.append({
                        "phase": marker["phase"],
                        "start_line": line_num,
                        "timestamp": format_timestamp(ts) if ts is not None else None,
                        "timestamp_sec": ts,
                        "marker_text": line_stripped[:150],
                    })
                    detected_phases.add(marker["phase"])
                    break

    # Calculate phase durations
    for i in range(len(phases)):
        if i + 1 < len(phases):
            start = phases[i].get("timestamp_sec")
            end = phases[i + 1].get("timestamp_sec")
            if start is not None and end is not None:
                duration = end - start
                phases[i]["duration_sec"] = round(duration, 3)
                phases[i]["duration_str"] = format_duration(duration)
                phases[i]["end_timestamp"] = phases[i + 1]["timestamp"]
            else:
                phases[i]["duration_sec"] = None
                phases[i]["duration_str"] = "unknown"
                phases[i]["end_timestamp"] = None
        else:
            # Last phase — duration unknown (no next phase marker)
            phases[i]["duration_sec"] = None
            phases[i]["duration_str"] = "ongoing"
            phases[i]["end_timestamp"] = None

    return phases


def correlate_postcodes(lines: List[str], postcode_file: str) -> List[Dict[str, Any]]:
    """Merge UART log timestamps with POST code log into unified timeline.

    POST code log format (from TTK3 postcode monitoring):
      [HH:MM:SS.mmm] POST: 0xNN
      or
      timestamp,postcode

    Args:
        lines: UART log lines.
        postcode_file: Path to POST code log file.

    Returns:
        List of unified timeline entries, sorted by timestamp.
    """
    timeline: List[Dict[str, Any]] = []

    # Parse UART log entries
    for line_num, line in enumerate(lines, 1):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        ts = parse_timestamp(line_stripped)
        if ts is not None:
            timeline.append({
                "timestamp_sec": ts,
                "timestamp": format_timestamp(ts),
                "source": "UART",
                "line": line_num,
                "text": line_stripped[:200],
            })

    # Parse POST code log
    if os.path.exists(postcode_file):
        try:
            with open(postcode_file, "r", encoding="utf-8", errors="replace") as f:
                for pc_line_num, pc_line in enumerate(f, 1):
                    pc_line = pc_line.strip()
                    if not pc_line:
                        continue

                    # Try [HH:MM:SS.mmm] POST: 0xNN format
                    match = re.match(
                        r"\[(\d{2}:\d{2}:\d{2}\.\d{3})\]\s*POST[:\s]+(?:0x)?([0-9A-Fa-f]+)",
                        pc_line
                    )
                    if match:
                        ts_str, postcode = match.group(1), match.group(2)
                        try:
                            dt = datetime.strptime(ts_str, "%H:%M:%S.%f")
                            ts = dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1_000_000
                        except ValueError:
                            continue
                        timeline.append({
                            "timestamp_sec": ts,
                            "timestamp": format_timestamp(ts),
                            "source": "POST",
                            "postcode": f"0x{postcode.upper()}",
                            "text": pc_line[:200],
                        })
                        continue

                    # Try CSV format: timestamp,postcode
                    match = re.match(r"([\d.]+)\s*,\s*(?:0x)?([0-9A-Fa-f]+)", pc_line)
                    if match:
                        ts = float(match.group(1))
                        postcode = match.group(2)
                        timeline.append({
                            "timestamp_sec": ts,
                            "timestamp": format_timestamp(ts),
                            "source": "POST",
                            "postcode": f"0x{postcode.upper()}",
                            "text": pc_line[:200],
                        })

        except IOError as e:
            timeline.append({
                "timestamp_sec": 0,
                "timestamp": "00:00.000",
                "source": "ERROR",
                "text": f"Failed to read postcode file: {e}",
            })

    # Sort by timestamp
    timeline.sort(key=lambda x: x.get("timestamp_sec", 0))

    return timeline


def determine_boot_status(errors: List[Dict[str, Any]],
                          phases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Determine overall boot status from errors and phases detected.

    Returns:
        Dict with status string, confidence, and reasoning.
    """
    critical_errors = [e for e in errors if e["severity"] == "critical"]
    high_errors = [e for e in errors if e["severity"] == "high"]
    phase_names = [p["phase"] for p in phases]

    # Check for boot success indicators
    reached_os = "OS" in phase_names
    reached_bds = "BDS" in phase_names
    has_critical = len(critical_errors) > 0
    has_high = len(high_errors) > 0
    # Shell> without actual OS handoff = failed boot that fell to Shell
    reached_shell_only = reached_os and any(
        "Shell>" in p.get("marker_text", "") or "UEFI Shell" in p.get("marker_text", "")
        for p in phases if p["phase"] == "OS"
    )

    if reached_shell_only:
        # Falling to EFI Shell is NOT a successful boot — it means all boot options failed
        if has_critical or has_high:
            n_errs = len(critical_errors) + len(high_errors)
            return {
                "status": "BOOT_FAILURE",
                "confidence": "high",
                "reason": f"Boot fell to EFI Shell with {n_errs} critical/high error(s)",
            }
        else:
            return {
                "status": "BOOT_TO_SHELL",
                "confidence": "medium",
                "reason": "Boot fell to EFI Shell — no OS loaded",
            }
    elif reached_os and not has_critical and not has_high:
        return {
            "status": "BOOT_SUCCESS",
            "confidence": "high",
            "reason": "Reached OS handoff with no critical/high errors",
        }
    elif reached_os and (has_critical or has_high):
        n_errs = len(critical_errors) + len(high_errors)
        return {
            "status": "BOOT_SUCCESS_WITH_ERRORS",
            "confidence": "medium",
            "reason": f"Reached OS handoff but {n_errs} critical/high error(s) detected",
        }
    elif reached_bds and not has_critical and not has_high:
        return {
            "status": "BOOT_PARTIAL",
            "confidence": "medium",
            "reason": "Reached BDS phase but OS handoff not detected",
        }
    elif has_critical or has_high:
        # Find which phase the first critical/high error occurred in
        severe_errors = critical_errors + high_errors
        severe_errors.sort(key=lambda e: e.get("line_number", 0))
        first_severe = severe_errors[0]
        error_phase = "unknown"
        for p in reversed(phases):
            p_ts = p.get("timestamp_sec")
            e_ts = first_severe.get("timestamp_sec")
            if p_ts is not None and e_ts is not None and p_ts <= e_ts:
                error_phase = p["phase"]
                break
        severity_label = "Critical" if has_critical else "High"
        return {
            "status": "BOOT_FAILURE",
            "confidence": "high" if has_critical else "medium",
            "reason": f"{severity_label} error ({first_severe['category']}) during {error_phase} phase",
        }
    elif len(phases) == 0:
        return {
            "status": "NO_BOOT_DATA",
            "confidence": "low",
            "reason": "No boot phase markers detected in log",
        }
    else:
        last_phase = phases[-1]["phase"]
        return {
            "status": "BOOT_STALL",
            "confidence": "medium",
            "reason": f"Boot stalled at {last_phase} phase — no further progress detected",
        }


# =============================================================================
# Main Analysis Pipeline
# =============================================================================

def analyze_log(input_file: str,
                postcode_file: Optional[str] = None,
                errors_only: bool = False) -> Dict[str, Any]:
    """Run full analysis pipeline on a UART log file.

    Args:
        input_file: Path to the UART log file.
        postcode_file: Optional path to POST code log for correlation.
        errors_only: If True, only run error detection (skip phases, correlation).

    Returns:
        Dict with complete analysis results.
    """
    # Read input file
    if not os.path.exists(input_file):
        return {"status": "error", "message": f"File not found: {input_file}"}

    try:
        with open(input_file, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except IOError as e:
        return {"status": "error", "message": f"Failed to read file: {e}"}

    if not lines:
        return {"status": "error", "message": "File is empty"}

    # Capture info
    first_ts = None
    last_ts = None
    for line in lines:
        ts = parse_timestamp(line)
        if ts is not None:
            if first_ts is None:
                first_ts = ts
            last_ts = ts

    duration = (last_ts - first_ts) if (first_ts is not None and last_ts is not None) else None

    result: Dict[str, Any] = {
        "capture_info": {
            "file": os.path.basename(input_file),
            "file_path": os.path.abspath(input_file),
            "total_lines": len(lines),
            "non_empty_lines": sum(1 for l in lines if l.strip()),
            "first_timestamp": format_timestamp(first_ts) if first_ts is not None else None,
            "last_timestamp": format_timestamp(last_ts) if last_ts is not None else None,
            "duration_sec": round(duration, 3) if duration is not None else None,
            "duration_str": format_duration(duration) if duration is not None else None,
        },
    }

    # Error detection (always runs)
    errors = analyze_errors(lines)
    error_summary: Dict[str, int] = {}
    severity_summary: Dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for e in errors:
        cat = e["category"]
        sev = e["severity"]
        error_summary[cat] = error_summary.get(cat, 0) + 1
        severity_summary[sev] = severity_summary.get(sev, 0) + 1

    result["errors"] = {
        "total_count": len(errors),
        "by_category": error_summary,
        "by_severity": severity_summary,
        "details": errors,
    }

    if not errors_only:
        # Boot phase detection
        phases = detect_boot_phases(lines)
        result["boot_phases"] = {
            "phases_detected": len(phases),
            "phase_sequence": [p["phase"] for p in phases],
            "details": phases,
        }

        # Boot status determination
        boot_status = determine_boot_status(errors, phases)
        result["boot_status"] = boot_status

        # POST code correlation (if file provided)
        if postcode_file:
            timeline = correlate_postcodes(lines, postcode_file)
            post_entries = [t for t in timeline if t.get("source") == "POST"]
            result["postcode_correlation"] = {
                "correlated": True,
                "postcode_file": postcode_file,
                "total_timeline_entries": len(timeline),
                "postcode_entries": len(post_entries),
                "uart_entries": len(timeline) - len(post_entries),
                "timeline": timeline[:500],  # Cap at 500 entries for JSON output
            }
        else:
            result["postcode_correlation"] = {"correlated": False}

    result["status"] = "ok"
    return result


# =============================================================================
# Text Summary Formatter
# =============================================================================

def format_text_summary(result: Dict[str, Any]) -> str:
    """Format analysis result as human-readable text summary."""
    lines: List[str] = []

    lines.append("=" * 72)
    lines.append("  BIOS UART Log Analysis Report")
    lines.append("=" * 72)

    # Capture info
    info = result.get("capture_info", {})
    lines.append(f"\n  File:       {info.get('file', 'unknown')}")
    lines.append(f"  Lines:      {info.get('total_lines', 0)} total, {info.get('non_empty_lines', 0)} non-empty")
    lines.append(f"  Duration:   {info.get('duration_str', 'unknown')}")
    lines.append(f"  Time range: {info.get('first_timestamp', '?')} -> {info.get('last_timestamp', '?')}")

    # Boot status
    boot_status = result.get("boot_status", {})
    if boot_status:
        status = boot_status.get("status", "UNKNOWN")
        status_icons = {
            "BOOT_SUCCESS": "[OK]",
            "BOOT_SUCCESS_WITH_ERRORS": "[WARN]",
            "BOOT_PARTIAL": "[PARTIAL]",
            "BOOT_FAILURE": "[FAIL]",
            "BOOT_STALL": "[STALL]",
            "NO_BOOT_DATA": "[??]",
        }
        icon = status_icons.get(status, "[??]")
        lines.append(f"\n  Boot Status: {icon} {status}")
        lines.append(f"  Confidence:  {boot_status.get('confidence', '?')}")
        lines.append(f"  Reason:      {boot_status.get('reason', '?')}")

    # Boot phases
    phases = result.get("boot_phases", {})
    if phases and phases.get("phases_detected", 0) > 0:
        lines.append(f"\n  Boot Phases ({phases['phases_detected']} detected):")
        lines.append("  " + "-" * 68)
        lines.append(f"  {'Phase':<8} {'Start':<14} {'Duration':<14} {'Marker'}")
        lines.append("  " + "-" * 68)
        for p in phases.get("details", []):
            phase = p.get("phase") or "?"
            start = p.get("timestamp") or "?"
            dur = p.get("duration_str") or "?"
            marker = (p.get("marker_text") or "")[:50]
            lines.append(f"  {phase:<8} {start:<14} {dur:<14} {marker}")

    # Error summary
    errors = result.get("errors", {})
    total_errors = errors.get("total_count", 0)
    if total_errors > 0:
        sev = errors.get("by_severity", {})
        lines.append(f"\n  Errors ({total_errors} total):")
        lines.append(f"    Critical: {sev.get('critical', 0)}  |  High: {sev.get('high', 0)}  "
                     f"|  Medium: {sev.get('medium', 0)}  |  Low: {sev.get('low', 0)}")

        lines.append(f"\n  Error Details (first occurrences):")
        lines.append("  " + "-" * 68)
        lines.append(f"  {'Line':<7} {'Time':<14} {'Severity':<10} {'Category':<16} {'Text'}")
        lines.append("  " + "-" * 68)
        shown = 0
        for e in errors.get("details", []):
            if e.get("first_occurrence", False) and shown < 30:
                line_num = e.get("line", "?")
                ts = e.get("timestamp", "?") or "?"
                sev_str = e.get("severity", "?")
                cat = e.get("category", "?")
                text = e.get("text", "")[:40]
                lines.append(f"  {line_num:<7} {ts:<14} {sev_str:<10} {cat:<16} {text}")
                shown += 1

        if total_errors > shown:
            lines.append(f"\n  ... and {total_errors - shown} more error(s). Use --json for full details.")
    else:
        lines.append("\n  Errors: None detected")

    # POST code correlation
    pc = result.get("postcode_correlation", {})
    if pc.get("correlated"):
        lines.append(f"\n  POST Code Correlation:")
        lines.append(f"    POST codes:     {pc.get('postcode_entries', 0)}")
        lines.append(f"    UART entries:    {pc.get('uart_entries', 0)}")
        lines.append(f"    Timeline total:  {pc.get('total_timeline_entries', 0)}")

    lines.append("\n" + "=" * 72)
    return "\n".join(lines)


# =============================================================================
# CLI Entry Point
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="BIOS UART Log Analyzer — error detection, boot phase timing, POST code correlation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input boot.log
  %(prog)s --input boot.log --json --output analysis.json
  %(prog)s --input boot.log --postcodes postcode_log.txt
  %(prog)s --input boot.log --errors-only
        """
    )

    parser.add_argument("--input", "-i", required=True,
                        help="Path to UART log file to analyze")
    parser.add_argument("--output", "-o",
                        help="Output file path (default: stdout)")
    parser.add_argument("--json", "-j", action="store_true",
                        help="Output as JSON (default: text summary)")
    parser.add_argument("--postcodes", "-p",
                        help="Path to POST code log file for correlation")
    parser.add_argument("--errors-only", "-e", action="store_true",
                        help="Only detect errors, skip boot phase and correlation analysis")

    args = parser.parse_args()

    # Run analysis
    result = analyze_log(
        input_file=args.input,
        postcode_file=args.postcodes,
        errors_only=args.errors_only,
    )

    # Check for analysis errors
    if result.get("status") == "error":
        print(json.dumps(result, indent=2) if args.json else f"ERROR: {result.get('message')}", file=sys.stderr)
        return 1

    # Format output
    if args.json:
        # Remove internal fields not needed in JSON output
        for e in result.get("errors", {}).get("details", []):
            e.pop("timestamp_sec", None)
        for p in result.get("boot_phases", {}).get("details", []):
            p.pop("timestamp_sec", None)
        output = json.dumps(result, indent=2, default=str)
    else:
        output = format_text_summary(result)

    # Write output
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Analysis written to: {args.output}")
        except IOError as e:
            print(f"ERROR: Failed to write output: {e}", file=sys.stderr)
            return 1
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
