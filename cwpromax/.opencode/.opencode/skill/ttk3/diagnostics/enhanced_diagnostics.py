#!/usr/bin/env python3
"""
TTK3 Enhanced Diagnostics with Power-Aware SPI Operations

Extends comprehensive diagnostics with:
- Power state management (powers down before SPI access)
- POST code monitoring for FFFF detection
- Enhanced root cause assessment with power/bus analysis

Usage:
    python enhanced_diagnostics.py [--serial SERIAL] [--output FILE] [--keep-power-off]

Auto-detects the first available TTK3 device if --serial is not specified.
Outputs structured JSON to stdout for agent/automation consumption.

IMPORTANT: This script will power OFF the platform for safe SPI access.
Use --keep-power-off to leave the platform powered down after diagnostics.
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


def run_power_diagnostics(device_index):
    """Run power subsystem diagnostics and power down for SPI access.

    Powers down all ports via PowerSplitter and verifies state.

    Args:
        device_index: TTK3 device index.

    Returns:
        dict with power diagnostic results and port states.
    """
    from ttk3_agent_platform.tools.power_tool import PowerControl

    results = {
        "category": "power",
        "tests": {},
        "info": {},
        "timestamp": datetime.now().isoformat()
    }

    power = None
    try:
        power = PowerControl()
        power.OpenPowerSplitter()

        # Test: Read initial power state
        try:
            initial_state = power.GetPortState(1)
            results["tests"]["initial_state_read"] = {
                "passed": True,
                "value": str(initial_state),
                "description": "Read initial PowerSplitter port state"
            }
            results["info"]["initial_port1_state"] = str(initial_state)
        except Exception as e:
            results["tests"]["initial_state_read"] = {"passed": False, "error": str(e)}

        # Action: Power off all ports for safe SPI access
        try:
            power.AllPortsOff()
            time.sleep(2)  # Allow power to settle

            off_state = power.GetPortState(1)
            ports_off = str(off_state) in ("0", "False", "OFF", "off")
            results["tests"]["power_off"] = {
                "passed": ports_off,
                "value": str(off_state),
                "description": "Power off all ports for SPI access"
            }
            results["info"]["power_off_success"] = ports_off
        except Exception as e:
            results["tests"]["power_off"] = {"passed": False, "error": str(e)}

    except Exception as e:
        results["error"] = str(e)
    finally:
        if power:
            try:
                power.Close()
            except Exception:
                pass

    return results


def run_postcode_diagnostics(device_index):
    """Read POST code to check for FFFF condition.

    Args:
        device_index: TTK3 device index.

    Returns:
        dict with POST code results and FFFF analysis.
    """
    from ttk3_agent_platform.tools.postcode_tool import Port80

    results = {
        "category": "postcode",
        "tests": {},
        "info": {},
        "timestamp": datetime.now().isoformat()
    }

    port80 = None
    try:
        port80 = Port80()
        port80.Open()

        try:
            post_code = port80.Read()
            post_hex = hex(post_code) if isinstance(post_code, int) else str(post_code)
            is_ffff = post_hex.upper().endswith("FFFF")

            results["tests"]["postcode_read"] = {
                "passed": True,
                "value": post_hex,
                "description": "POST code readback via Port80"
            }
            results["tests"]["ffff_check"] = {
                "passed": not is_ffff,
                "value": post_hex,
                "description": "POST code FFFF check (pass = not FFFF)"
            }
            results["info"]["post_code"] = post_hex
            results["info"]["is_ffff"] = is_ffff
        except Exception as e:
            results["tests"]["postcode_read"] = {"passed": False, "error": str(e)}

    except Exception as e:
        results["error"] = str(e)
    finally:
        if port80:
            try:
                port80.Close()
            except Exception:
                pass

    return results


def run_spi_diagnostics_with_power_down(device_index):
    """Run SPI diagnostics after ensuring platform is powered down.

    Uses SetChipSelect(0) for safe SPI bus access.

    Args:
        device_index: TTK3 device index.

    Returns:
        dict with SPI diagnostic results.
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

        # Set chip select for safe access
        try:
            programmer.SetChipSelect(0)
            results["tests"]["chip_select"] = {
                "passed": True,
                "value": "CS0",
                "description": "SPI chip select configured"
            }
        except Exception as e:
            results["tests"]["chip_select"] = {"passed": False, "error": str(e)}

        # Test: Chip detection
        try:
            chip_info = programmer.DetectChip()
            chip_detected = chip_info is not None and str(chip_info) != ""
            results["tests"]["chip_detect"] = {
                "passed": chip_detected,
                "value": str(chip_info) if chip_info else "No chip detected",
                "description": "SPI flash chip detection (power-safe)"
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
                "description": "BIOS version readback from flash (power-safe)"
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


def restore_power():
    """Restore power after diagnostics by turning all ports back on.

    Returns:
        dict with power restore status.
    """
    from ttk3_agent_platform.tools.power_tool import PowerControl

    result = {"action": "power_restore"}
    power = None
    try:
        power = PowerControl()
        power.OpenPowerSplitter()
        power.AllPortsOn()
        time.sleep(2)

        state = power.GetPortState(1)
        result["success"] = str(state) not in ("0", "False", "OFF", "off")
        result["port1_state"] = str(state)
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
    finally:
        if power:
            try:
                power.Close()
            except Exception:
                pass

    return result


def enhanced_ffff_assessment(diagnostics):
    """Enhanced root cause assessment with power and bus analysis.

    Extends basic FFFF analysis with power delivery and SPI bus contention checks.

    Args:
        diagnostics: dict of all diagnostic category results.

    Returns:
        dict with detailed FFFF root cause assessment.
    """
    assessment = {
        "ffff_analysis": True,
        "possible_causes": [],
        "recommendations": [],
        "confidence": "low",
        "details": {}
    }

    power = diagnostics.get("power", {})
    spi = diagnostics.get("spi_flash", {})
    postcode = diagnostics.get("postcode", {})

    power_tests = power.get("tests", {})
    spi_tests = spi.get("tests", {})
    postcode_tests = postcode.get("tests", {})

    # Check power delivery
    power_off_ok = power_tests.get("power_off", {}).get("passed", False)
    if not power_off_ok:
        assessment["possible_causes"].append("Power delivery issue - unable to control PowerSplitter")
        assessment["recommendations"].append("Check ATX/PowerSplitter connections to TTK3")
        assessment["details"]["power_delivery_issue"] = True
        assessment["confidence"] = "high"
    else:
        assessment["details"]["power_delivery_issue"] = False

    # Check SPI bus
    chip_ok = spi_tests.get("chip_detect", {}).get("passed", False)
    bios_ok = spi_tests.get("bios_version", {}).get("passed", False)
    cs_ok = spi_tests.get("chip_select", {}).get("passed", False)

    if not cs_ok:
        assessment["possible_causes"].append("SPI bus contention - chip select failed")
        assessment["recommendations"].append("Verify SPI connections and check for bus conflicts")
        assessment["details"]["spi_bus_issue"] = True
        assessment["confidence"] = "high"
    elif not chip_ok:
        assessment["possible_causes"].append("SPI flash chip not detected with power off - hardware failure likely")
        assessment["recommendations"].append("Inspect SPI flash chip physical connections")
        assessment["details"]["spi_bus_issue"] = True
        assessment["confidence"] = "high"
    elif chip_ok and not bios_ok:
        assessment["possible_causes"].append("Flash chip responds but BIOS unreadable - flash corruption")
        assessment["recommendations"].append("Re-flash IFWI using ttk3_spi_flash_programmer.py")
        assessment["details"]["spi_bus_issue"] = False
        assessment["confidence"] = "high"
    else:
        assessment["details"]["spi_bus_issue"] = False

    # Check POST code
    is_ffff = postcode.get("info", {}).get("is_ffff", False)
    if is_ffff:
        assessment["details"]["post_code_ffff_confirmed"] = True
        if chip_ok and bios_ok:
            assessment["possible_causes"].append("Flash healthy but POST FFFF - check CPU/memory/power rail issues")
            assessment["recommendations"].append("Capture UART boot log for detailed failure point")
            assessment["confidence"] = "medium"

    if not assessment["possible_causes"]:
        assessment["possible_causes"].append("All diagnostics passed - platform may need manual inspection")
        assessment["recommendations"].append("Try a full power cycle with advanced_power_cycle.py (15s cold boot)")

    return assessment


def calculate_health_score(diagnostics):
    """Calculate overall health score from all diagnostic results.

    Args:
        diagnostics: dict containing all diagnostic category results.

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


def main():
    parser = argparse.ArgumentParser(
        description="TTK3 Enhanced Diagnostics with Power-Aware SPI Operations",
        epilog="Auto-detects first available TTK3 device if --serial is not specified."
    )
    parser.add_argument("--serial", type=str, default=None,
                        help="TTK3 device serial number (auto-detect if omitted)")
    parser.add_argument("--output", type=str, default=None,
                        help="Save JSON results to file")
    parser.add_argument("--keep-power-off", action="store_true",
                        help="Leave platform powered off after diagnostics (default: restore power)")
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

    print(f"Running enhanced diagnostics on TTK3 device: {device_info['serial']} (index {device_index})", file=sys.stderr)

    diagnostics = {}

    # Step 1: Read POST code before power-down
    print("Step 1/4: Reading POST code...", file=sys.stderr)
    diagnostics["postcode"] = run_postcode_diagnostics(device_index)

    # Step 2: Power down for safe SPI access
    print("Step 2/4: Powering down platform for SPI access...", file=sys.stderr)
    diagnostics["power"] = run_power_diagnostics(device_index)

    # Step 3: SPI diagnostics with platform powered off
    print("Step 3/4: Running SPI diagnostics (power-safe)...", file=sys.stderr)
    diagnostics["spi_flash"] = run_spi_diagnostics_with_power_down(device_index)

    # Step 4: Restore power (unless --keep-power-off)
    power_restore = None
    if not args.keep_power_off:
        print("Step 4/4: Restoring power...", file=sys.stderr)
        power_restore = restore_power()
    else:
        print("Step 4/4: Skipped - platform left powered off per --keep-power-off", file=sys.stderr)

    # Calculate health score
    health = calculate_health_score(diagnostics)

    # Enhanced FFFF assessment
    ffff_assessment = enhanced_ffff_assessment(diagnostics)

    # Build output
    output = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "device": device_info,
        "health": health,
        "diagnostics": diagnostics,
        "ffff_assessment": ffff_assessment,
    }
    if power_restore:
        output["power_restore"] = power_restore

    # Output JSON
    json_output = json.dumps(output, indent=2, default=str)
    print(json_output)

    # Save to file if requested
    if args.output:
        with open(args.output, "w") as f:
            f.write(json_output)
        print(f"Results saved to {args.output}", file=sys.stderr)

    sys.exit(0 if health["grade"] in ("HEALTHY", "DEGRADED") else 1)


if __name__ == "__main__":
    main()
