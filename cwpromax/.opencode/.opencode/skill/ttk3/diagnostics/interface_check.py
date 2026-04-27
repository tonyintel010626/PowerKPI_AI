#!/usr/bin/env python3
"""
TTK3 Interface Availability Check

Pre-flight validation script to verify which TTK3 interfaces are accessible
before running diagnostics or debug operations.

Tests: Device, I2C, GPIO, Power, Port80 (POST code)

Usage:
    python interface_check.py [--serial SERIAL]

Auto-detects the first available TTK3 device if --serial is not specified.
Outputs structured JSON to stdout for agent/automation consumption.
"""

import argparse
import json
import sys
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


def check_device_interface(device_index):
    """Check TTK3 Device interface availability.

    Args:
        device_index: TTK3 device index.

    Returns:
        dict with interface check result.
    """
    result = {
        "interface": "Device",
        "available": False,
        "details": {}
    }

    try:
        from ttk3_agent_platform.tools.device_tool import Ttk3Device, DeviceType

        device = Ttk3Device()
        device.OpenIndex(device_index, deviceType=0)

        serial = device.GetDeviceSeriaNumberByIndex(device_index).rstrip('\x00\t ')
        fw_rev = device.GetFirmwareRevision()
        hw_rev = device.GetHardwareRevision()
        connected = device.IsDeviceConnected(DeviceType.TTK3)

        device.Close()

        result["available"] = bool(connected)
        result["details"] = {
            "serial": serial,
            "firmware_revision": str(fw_rev),
            "hardware_revision": str(hw_rev),
            "connected": bool(connected)
        }
    except Exception as e:
        result["error"] = str(e)

    return result


def check_i2c_interface():
    """Check I2C interface availability.

    Returns:
        dict with interface check result.
    """
    result = {
        "interface": "I2C",
        "available": False,
        "details": {}
    }

    try:
        from ttk3_agent_platform.tools.i2c_tool import I2cControl

        i2c = I2cControl()
        i2c.Open()
        i2c.SetClock(100)
        i2c.Close()

        result["available"] = True
        result["details"]["clock_set"] = "100 kHz"
    except Exception as e:
        result["error"] = str(e)

    return result


def check_gpio_interface():
    """Check GPIO interface availability.

    Returns:
        dict with interface check result.
    """
    result = {
        "interface": "GPIO",
        "available": False,
        "details": {}
    }

    try:
        from ttk3_agent_platform.tools.gpio_tool import Gpio
        result["available"] = True
        result["details"]["import"] = "success"
    except ImportError as e:
        result["error"] = f"Import failed: {e}"
    except Exception as e:
        result["error"] = str(e)

    return result


def check_power_interface():
    """Check Power control interface availability.

    Tests PowerSplitter open/close and probes for available methods.

    Returns:
        dict with interface check result.
    """
    result = {
        "interface": "Power",
        "available": False,
        "details": {}
    }

    try:
        from ttk3_agent_platform.tools.power_tool import PowerControl

        power = PowerControl()
        power.OpenPowerSplitter()

        # Probe available methods
        available_methods = []
        for method_name in ["GetPortState", "AllPortsOn", "AllPortsOff",
                            "GetPowerState", "GetSystemState", "GetS5State"]:
            if hasattr(power, method_name):
                available_methods.append(method_name)

        power.Close()

        result["available"] = True
        result["details"]["available_methods"] = available_methods
    except Exception as e:
        result["error"] = str(e)

    return result


def check_port80_interface():
    """Check Port80 (POST code) interface availability.

    Returns:
        dict with interface check result.
    """
    result = {
        "interface": "Port80",
        "available": False,
        "details": {}
    }

    try:
        from ttk3_agent_platform.tools.postcode_tool import Port80

        port80 = Port80()
        port80.Open()

        post_code = port80.Read()
        post_hex = hex(post_code) if isinstance(post_code, int) else str(post_code)

        port80.Close()

        result["available"] = True
        result["details"]["current_post_code"] = post_hex
    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="TTK3 Interface Availability Check",
        epilog="Auto-detects first available TTK3 device if --serial is not specified."
    )
    parser.add_argument("--serial", type=str, default=None,
                        help="TTK3 device serial number (auto-detect if omitted)")
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

    print(f"Checking TTK3 interfaces for device: {device_info['serial']} (index {device_index})", file=sys.stderr)

    # Run all interface checks
    interfaces = []
    interfaces.append(check_device_interface(device_index))
    interfaces.append(check_i2c_interface())
    interfaces.append(check_gpio_interface())
    interfaces.append(check_power_interface())
    interfaces.append(check_port80_interface())

    # Summary
    available_count = sum(1 for i in interfaces if i["available"])
    total_count = len(interfaces)

    output = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "device": device_info,
        "summary": {
            "available": available_count,
            "total": total_count,
            "all_available": available_count == total_count
        },
        "interfaces": interfaces
    }

    print(json.dumps(output, indent=2, default=str))
    sys.exit(0 if available_count > 0 else 1)


if __name__ == "__main__":
    main()
