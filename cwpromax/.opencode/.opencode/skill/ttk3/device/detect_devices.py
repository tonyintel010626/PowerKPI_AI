#!/usr/bin/env python3
"""Detect and enumerate all connected TTK3/SQUID devices.

Usage:
    python detect_devices.py
    python detect_devices.py --device-type 1
    python detect_devices.py --verbose

Steps:
    1. Open Ttk3Device
    2. GetNumConnectedDevices
    3. Enumerate serial numbers, FW/HW revision
    4. Close

Requires:
    - TTK3 API at C:\\SVSHARE\\User_Apps\\TTK3\\API\\Python\\
    - TTK3/SQUID USB device connected
"""

import argparse
import json
import sys

TTK3_API_PATH = r"C:\SVSHARE\User_Apps\TTK3\API\Python"
sys.path.insert(0, TTK3_API_PATH)


def detect_devices(device_type=0, verbose=False):
    """Detect and enumerate connected TTK3/SQUID devices.

    Args:
        device_type: 0=TTK3, 1=SQUID.
        verbose: If True, include FW/HW revision for each device.

    Returns:
        dict with device list and details.
    """
    from Ttk3Device import Ttk3Device

    # Import DeviceType enum if available
    try:
        from Ttk3Device import DeviceType
        device_type_names = {0: "TTK3", 1: "SQUID"}
    except ImportError:
        device_type_names = {0: "TTK3", 1: "SQUID"}

    result = {
        "status": "unknown",
        "device_type": device_type,
        "device_type_name": device_type_names.get(device_type, "unknown"),
        "num_devices": 0,
        "devices": [],
    }

    device = Ttk3Device()
    try:
        if device_type > 0:
            device.OpenIndex(0, deviceType=device_type)
        else:
            device.Open()

        num = device.GetNumConnectedDevices()
        result["num_devices"] = num

        # Check connection
        try:
            connected = device.IsDeviceConnected(device_type)
            result["is_connected"] = bool(connected)
        except Exception as e:
            result["is_connected_error"] = str(e)

        # Enumerate devices
        for i in range(num):
            dev_info = {"index": i}
            try:
                # Note: real API has typo — GetDeviceSeriaNumberByIndex (missing 'l')
                serial = device.GetDeviceSeriaNumberByIndex(i)
                dev_info["serial_number"] = str(serial)
            except Exception as e:
                dev_info["serial_number_error"] = str(e)

            result["devices"].append(dev_info)

        # Get FW/HW info (applies to currently opened device)
        if verbose:
            try:
                result["firmware_revision"] = str(device.GetFirmwareRevision())
            except Exception as e:
                result["firmware_revision_error"] = str(e)
            try:
                result["hardware_revision"] = str(device.GetHardwareRevision())
            except Exception as e:
                result["hardware_revision_error"] = str(e)

        result["status"] = "success"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["error_type"] = type(e).__name__

    finally:
        device.Close()

    return result


def main():
    parser = argparse.ArgumentParser(description="Detect connected TTK3/SQUID devices")
    parser.add_argument("--device-type", type=int, default=0, choices=[0, 1],
                        help="Device type: 0=TTK3, 1=SQUID (default: 0)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Include firmware and hardware revision info")

    args = parser.parse_args()

    result = detect_devices(
        device_type=args.device_type,
        verbose=args.verbose,
    )

    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
