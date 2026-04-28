#!/usr/bin/env python3
"""
TTK3 Comprehensive Diagnostics Script

Full platform health check including device connectivity, SPI flash health,
BIOS version verification, and POST FFFF root cause assessment.

Usage:
    python comprehensive_diagnostics.py [--serial SERIAL] [--output FILE]

Auto-detects the first available TTK3 device if --serial is not specified.
Outputs structured JSON to stdout for agent/automation consumption.
"""

import argparse
import json
import sys
import time
from datetime import datetime


def find_device(target_serial=None):
    """Find TTK3 device by serial number or auto-detect first available.

    Args:
        target_serial: Optional serial number. If None, uses first available device.

    Returns:
        dict with 'device_index', 'serial', 'total_devices' or None if not found.
    """
    try:
        from ttk3_agent_platform.tools.device_tool import Ttk3Device

        device = Ttk3Device()
        device.Open()
        num_devices = device.GetNumConnectedDevices()
        device.Close()

        if num_devices == 0:
            return None

        for i in range(num_devices):
            device.Open()
            serial = device.GetDeviceSeriaNumberByIndex(i).rstrip('\x00\t ')
            device.Close()

            if target_serial is None:
                return {"device_index": i, "serial": serial, "total_devices": num_devices}

            if serial == target_serial:
                return {"device_index": i, "serial": serial, "total_devices": num_devices}

        return None
    except Exception as e:
        return {"error": str(e)}


def run_device_diagnostics(device_index):
    """Run device-level diagnostics: connectivity, firmware, hardware revision, serials.

    Args:
        device_index: TTK3 device index to diagnose.

    Returns:
        dict with test results for device connectivity and info.
    """
    from ttk3_agent_platform.tools.device_tool import Ttk3Device, DeviceType

    results = {
        "category": "device",
        "tests": {},
        "info": {},
        "timestamp": datetime.now().isoformat()
    }

    device = None
    try:
        device = Ttk3Device()
        device.OpenIndex(device_index, deviceType=0)

        # Test: Device connectivity
        try:
            connected = device.IsDeviceConnected(DeviceType.TTK3)
            results["tests"]["connectivity"] = {
                "passed": bool(connected),
                "value": connected,
                "description": "TTK3 device connectivity check"
            }
        except Exception as e:
            results["tests"]["connectivity"] = {"passed": False, "error": str(e)}

        # Test: Firmware revision
        try:
            fw_rev = device.GetFirmwareRevision()
            results["tests"]["firmware"] = {
                "passed": fw_rev is not None and fw_rev != "",
                "value": str(fw_rev),
                "description": "Firmware revision readback"
            }
            results["info"]["firmware_revision"] = str(fw_rev)
        except Exception as e:
            results["tests"]["firmware"] = {"passed": False, "error": str(e)}

        # Test: Hardware revision
        try:
            hw_rev = device.GetHardwareRevision()
            results["tests"]["hardware"] = {
                "passed": hw_rev is not None and hw_rev != "",
                "value": str(hw_rev),
                "description": "Hardware revision readback"
            }
            results["info"]["hardware_revision"] = str(hw_rev)
        except Exception as e:
            results["tests"]["hardware"] = {"passed": False, "error": str(e)}

        # Test: Serial numbers
        try:
            serial = device.GetDeviceSeriaNumberByIndex(device_index).rstrip('\x00\t ')
            results["tests"]["serial"] = {
                "passed": serial is not None and len(serial) > 0,
                "value": serial,
                "description": "Device serial number readback"
            }
            results["info"]["serial_number"] = serial
        except Exception as e:
            results["tests"]["serial"] = {"passed": False, "error": str(e)}

    except Exception as e:
        results["error"] = str(e)
    finally:
        if device:
            try:
                device.Close()
            except Exception:
                pass

    return results


def run_spi_diagnostics(device_index):
    """Run SPI flash diagnostics: chip detection, BIOS version read.

    Args:
        device_index: TTK3 device index to diagnose.

    Returns:
        dict with test results for SPI flash health.
    """
    from ttk3_agent_platform.tools.spi_tool import BiosProgrammer

    results = {
        "category": "spi_flash",
        "tests": {},
        "info": {},
        "timestamp": datetime.now().isoformat()
    }

    programmer = None
    try:
        programmer = BiosProgrammer()
        programmer.Open()

        # Test: Chip detection
        try:
            chip_info = programmer.DetectChip()
            chip_detected = chip_info is not None and str(chip_info) != ""
            results["tests"]["chip_detect"] = {
                "passed": chip_detected,
                "value": str(chip_info) if chip_info else "No chip detected",
                "description": "SPI flash chip detection"
            }
            results["info"]["chip_info"] = str(chip_info) if chip_info else None
        except Exception as e:
            results["tests"]["chip_detect"] = {"passed": False, "error": str(e)}

        # Test: BIOS version read
        try:
            bios_version = programmer.ReadBiosVersion(turnOff=True)
            bios_readable = bios_version is not None and str(bios_version) != ""
            results["tests"]["bios_version"] = {
                "passed": bios_readable,
                "value": str(bios_version) if bios_version else "Unable to read",
                "description": "BIOS version readback from flash"
            }
            results["info"]["bios_version"] = str(bios_version) if bios_version else None
        except Exception as e:
            results["tests"]["bios_version"] = {"passed": False, "error": str(e)}

    except Exception as e:
        results["error"] = str(e)
    finally:
        if programmer:
            try:
                programmer.Close()
            except Exception:
                pass

    return results


def calculate_health_score(diagnostics):
    """Calculate overall health score from diagnostic results.

    Args:
        diagnostics: dict containing 'device' and 'spi_flash' diagnostic results.

    Returns:
        dict with score (0-100), total tests, passed tests, and grade.
    """
    total = 0
    passed = 0

    for category in diagnostics.values():
        if isinstance(category, dict) and "tests" in category:
            for test_name, test_result in category["tests"].items():
                total += 1
                if test_result.get("passed", False):
                    passed += 1

    score = int((passed / total) * 100) if total > 0 else 0

    if score >= 90:
        grade = "HEALTHY"
    elif score >= 70:
        grade = "DEGRADED"
    elif score >= 50:
        grade = "WARNING"
    else:
        grade = "CRITICAL"

    return {
        "score": score,
        "grade": grade,
        "tests_passed": passed,
        "tests_total": total
    }


def assess_ffff_cause(diagnostics):
    """Assess potential root cause if platform is stuck at POST FFFF.

    Args:
        diagnostics: dict containing device and SPI diagnostic results.

    Returns:
        dict with FFFF root cause assessment and recommendations.
    """
    assessment = {
        "ffff_analysis": True,
        "possible_causes": [],
        "recommendations": [],
        "confidence": "low"
    }

    spi = diagnostics.get("spi_flash", {})
    device = diagnostics.get("device", {})
    spi_tests = spi.get("tests", {})
    device_tests = device.get("tests", {})

    # Check flash corruption
    chip_ok = spi_tests.get("chip_detect", {}).get("passed", False)
    bios_ok = spi_tests.get("bios_version", {}).get("passed", False)
    device_ok = device_tests.get("connectivity", {}).get("passed", False)

    if not chip_ok:
        assessment["possible_causes"].append("SPI flash chip not detected - possible hardware failure or bus contention")
        assessment["recommendations"].append("Check SPI connections and ensure platform power is OFF for SPI access")
        assessment["confidence"] = "high"

    if chip_ok and not bios_ok:
        assessment["possible_causes"].append("Flash chip detected but BIOS unreadable - likely flash corruption")
        assessment["recommendations"].append("Re-flash IFWI image using ttk3_spi_flash_programmer.py")
        assessment["confidence"] = "high"

    if not device_ok:
        assessment["possible_causes"].append("TTK3 device connectivity issue - check USB connection")
        assessment["recommendations"].append("Reconnect TTK3 device and verify with interface_check.py")

    if chip_ok and bios_ok:
        assessment["possible_causes"].append("Flash appears healthy - FFFF may be caused by other hardware issues")
        assessment["recommendations"].append("Check power delivery, memory, and CPU seating")
        assessment["recommendations"].append("Capture UART boot log for detailed failure analysis")
        assessment["confidence"] = "medium"

    if not assessment["possible_causes"]:
        assessment["possible_causes"].append("Insufficient data for root cause determination")
        assessment["recommendations"].append("Run enhanced_diagnostics.py with --keep-power-off for power-aware SPI access")

    return assessment


def main():
    parser = argparse.ArgumentParser(
        description="TTK3 Comprehensive Platform Diagnostics",
        epilog="Auto-detects first available TTK3 device if --serial is not specified."
    )
    parser.add_argument("--serial", type=str, default=None,
                        help="TTK3 device serial number (auto-detect if omitted)")
    parser.add_argument("--output", type=str, default=None,
                        help="Save JSON results to file")
    args = parser.parse_args()

    # Find device
    device_info = find_device(args.serial)
    if device_info is None:
        result = {"status": "error", "message": "No TTK3 device found"}
        if args.serial:
            result["message"] = f"TTK3 device with serial '{args.serial}' not found"
        print(json.dumps(result, indent=2))
        sys.exit(1)

    if "error" in device_info:
        print(json.dumps({"status": "error", "message": device_info["error"]}, indent=2))
        sys.exit(1)

    device_index = device_info["device_index"]

    # Run diagnostics
    print(f"Running comprehensive diagnostics on TTK3 device: {device_info['serial']} (index {device_index})", file=sys.stderr)

    diagnostics = {}
    diagnostics["device"] = run_device_diagnostics(device_index)
    diagnostics["spi_flash"] = run_spi_diagnostics(device_index)

    # Calculate health score
    health = calculate_health_score(diagnostics)

    # Assess FFFF if health is not perfect
    ffff_assessment = None
    if health["score"] < 100:
        ffff_assessment = assess_ffff_cause(diagnostics)

    # Build output
    output = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "device": device_info,
        "health": health,
        "diagnostics": diagnostics,
    }
    if ffff_assessment:
        output["ffff_assessment"] = ffff_assessment

    # Output JSON
    json_output = json.dumps(output, indent=2, default=str)
    print(json_output)

    # Save to file if requested
    if args.output:
        with open(args.output, "w") as f:
            f.write(json_output)
        print(f"Results saved to {args.output}", file=sys.stderr)

    # Exit code based on health
    sys.exit(0 if health["grade"] in ("HEALTHY", "DEGRADED") else 1)


if __name__ == "__main__":
    main()
