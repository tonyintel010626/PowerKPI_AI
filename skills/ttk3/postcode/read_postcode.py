#!/usr/bin/env python3
"""Read the current POST code from Port80 via TTK3.

Usage:
    python read_postcode.py
    python read_postcode.py --device-type 0

Steps:
    1. Open Port80
    2. Read current POST code
    3. Close

Requires:
    - TTK3 API at C:\\SVSHARE\\User_Apps\\TTK3\\API\\Python\\
    - TTK3/SQUID USB device connected
    - Platform powered on and booting
"""

import argparse
import json
import sys

TTK3_API_PATH = r"C:\SVSHARE\User_Apps\TTK3\API\Python"
sys.path.insert(0, TTK3_API_PATH)


def read_postcode(device_type=0):
    """Read the current POST code.

    Args:
        device_type: Device type (0=TTK3, 1=SQUID).

    Returns:
        dict with POST code value.
    """
    from Port80 import Port80

    result = {
        "status": "unknown",
        "device_type": device_type,
    }

    port80 = Port80()
    try:
        port80.Open(deviceType=device_type)

        code = port80.Read()
        result["post_code"] = str(code)
        result["status"] = "success"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["error_type"] = type(e).__name__

    finally:
        port80.Close()

    return result


def main():
    parser = argparse.ArgumentParser(description="Read current POST code via TTK3 Port80")
    parser.add_argument("--device-type", type=int, default=0, choices=[0, 1],
                        help="Device type: 0=TTK3, 1=SQUID (default: 0)")

    args = parser.parse_args()

    result = read_postcode(device_type=args.device_type)

    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
