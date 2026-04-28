#!/usr/bin/env python3
"""
TTK3 Advanced Power Cycle Script

Full power cycle with extended capacitor drain delay for hard cold boot scenarios.
Uses 15-second delay by default (configurable) for complete capacitor discharge,
ensuring a clean G3 power state before power-on.

Usage:
    python advanced_power_cycle.py [--serial SERIAL] [--delay SECONDS]

Use Cases:
    - Recovery after flash operations
    - Hard reset for platforms stuck in bad state
    - Post-IFWI-flash cold boot validation
    - Clearing persistent hardware state

Auto-detects the first available TTK3 device if --serial is not specified.
Outputs structured JSON to stdout for agent/automation consumption.
"""

import argparse
import json
import sys
import time
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


def advanced_power_cycle(delay=15):
    """Execute full power cycle with extended cold boot delay.

    Sequence:
        1. AllPortsOff
        2. Wait for capacitor drain (default 15s countdown)
        3. Verify ports are OFF
        4. AllPortsOn
        5. Wait 2s for stabilization
        6. Verify ports are ON

    Args:
        delay: Seconds to wait for capacitor drain (default 15).

    Returns:
        dict with operation result, timing, and port states.
    """
    from ttk3_agent_platform.tools.power_tool import PowerControl

    result = {
        "action": "advanced_power_cycle",
        "success": False,
        "delay_seconds": delay,
        "phases": {},
        "timestamp": datetime.now().isoformat()
    }

    power = None
    try:
        power = PowerControl()
        power.OpenPowerSplitter()

        # Phase 1: Power off
        power.AllPortsOff()
        result["phases"]["power_off"] = {"completed": True, "timestamp": datetime.now().isoformat()}

        # Phase 2: Capacitor drain countdown
        print(f"Capacitor drain: waiting {delay} seconds...", file=sys.stderr)
        for remaining in range(delay, 0, -1):
            print(f"  {remaining}s remaining...", file=sys.stderr)
            time.sleep(1)
        result["phases"]["capacitor_drain"] = {
            "completed": True,
            "duration_seconds": delay,
            "timestamp": datetime.now().isoformat()
        }

        # Phase 3: Verify OFF
        try:
            off_state = power.GetPortState(1)
            ports_off = str(off_state) in ("0", "False", "OFF", "off")
            result["phases"]["verify_off"] = {
                "completed": True,
                "port1_state": str(off_state),
                "confirmed_off": ports_off
            }
        except Exception as e:
            result["phases"]["verify_off"] = {"completed": False, "error": str(e)}

        # Phase 4: Power on
        power.AllPortsOn()
        result["phases"]["power_on"] = {"completed": True, "timestamp": datetime.now().isoformat()}

        # Phase 5: Stabilization
        time.sleep(2)
        result["phases"]["stabilization"] = {
            "completed": True,
            "duration_seconds": 2,
            "timestamp": datetime.now().isoformat()
        }

        # Phase 6: Verify ON
        try:
            on_state = power.GetPortState(1)
            ports_on = str(on_state) not in ("0", "False", "OFF", "off")
            result["phases"]["verify_on"] = {
                "completed": True,
                "port1_state": str(on_state),
                "confirmed_on": ports_on
            }
            result["success"] = ports_on
        except Exception as e:
            result["phases"]["verify_on"] = {"completed": False, "error": str(e)}

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
        description="TTK3 Advanced Power Cycle with Extended Cold Boot Delay",
        epilog="Auto-detects first available TTK3 device if --serial is not specified."
    )
    parser.add_argument("--serial", type=str, default=None,
                        help="TTK3 device serial number (auto-detect if omitted)")
    parser.add_argument("--delay", type=int, default=15,
                        help="Capacitor drain delay in seconds (default: 15)")
    args = parser.parse_args()

    # Find device
    device_info = find_device(args.serial)
    if device_info is None:
        print(json.dumps({"status": "error", "message": "No TTK3 device found"}, indent=2))
        sys.exit(1)
    if "error" in device_info:
        print(json.dumps({"status": "error", "message": device_info["error"]}, indent=2))
        sys.exit(1)

    print(f"Advanced power cycle on TTK3 device: {device_info['serial']} (delay: {args.delay}s)", file=sys.stderr)

    result = advanced_power_cycle(delay=args.delay)
    output = {
        "status": "success" if result["success"] else "error",
        "device": device_info,
        **result
    }

    print(json.dumps(output, indent=2, default=str))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
