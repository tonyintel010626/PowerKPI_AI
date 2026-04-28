#!/usr/bin/env python3
"""
TTK3 Power Off Script

Powers OFF all ATX PowerSplitter ports with state verification.

Usage:
    python power_off.py [--serial SERIAL]

Auto-detects the first available TTK3 device if --serial is not specified.
Outputs structured JSON to stdout for agent/automation consumption.
"""

import argparse
import json
import sys
from datetime import datetime


def find_device(target_serial=None):
    """Find TTK3 device by serial number or auto-detect first available."""
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

            if target_serial is None or serial == target_serial:
                return {"device_index": i, "serial": serial, "total_devices": num_devices}

        return None
    except Exception as e:
        return {"error": str(e)}


def power_off():
    """Power off all PowerSplitter ports and verify state.

    Returns:
        dict with operation result and port states.
    """
    from ttk3_agent_platform.tools.power_tool import PowerControl

    result = {
        "action": "power_off",
        "success": False,
        "port_states": {},
        "timestamp": datetime.now().isoformat()
    }

    power = None
    try:
        power = PowerControl()
        power.OpenPowerSplitter()
        power.AllPortsOff()

        # Verify all ports are off
        all_off = True
        for port in range(1, 5):
            try:
                state = power.GetPortState(port)
                port_off = str(state) in ("0", "False", "OFF", "off")
                result["port_states"][f"port_{port}"] = {
                    "state": str(state),
                    "off": port_off
                }
                if not port_off:
                    all_off = False
            except Exception as e:
                result["port_states"][f"port_{port}"] = {"error": str(e)}
                all_off = False

        result["success"] = all_off

    except Exception as e:
        result["error"] = str(e)
    finally:
        if power:
            try:
                power.Close()
            except Exception:
                pass

    return result


def main():
    parser = argparse.ArgumentParser(
        description="TTK3 Power Off - All PowerSplitter Ports",
        epilog="Auto-detects first available TTK3 device if --serial is not specified."
    )
    parser.add_argument("--serial", type=str, default=None,
                        help="TTK3 device serial number (auto-detect if omitted)")
    args = parser.parse_args()

    # Find device
    device_info = find_device(args.serial)
    if device_info is None:
        print(json.dumps({"status": "error", "message": "No TTK3 device found"}, indent=2))
        sys.exit(1)
    if "error" in device_info:
        print(json.dumps({"status": "error", "message": device_info["error"]}, indent=2))
        sys.exit(1)

    print(f"Powering off TTK3 device: {device_info['serial']}", file=sys.stderr)

    result = power_off()
    output = {
        "status": "success" if result["success"] else "error",
        "device": device_info,
        **result
    }

    print(json.dumps(output, indent=2, default=str))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
