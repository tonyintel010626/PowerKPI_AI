#!/usr/bin/env python3
"""Detect SPI flash chip connected via TTK3.

Usage:
    python detect_chip.py
    python detect_chip.py --device-index 1
    python detect_chip.py --read-bios-version

IMPORTANT: Platform power MUST be OFF and a MANDATORY 10-second wait must
elapse after power-off before running this script. SPI flash access while
the platform is powered on or before power fully discharges can cause
unreliable chip detection or data corruption.

Steps:
    1. Ensure platform power is OFF (wait 10s after power-off)
    2. Open BiosProgrammer
    3. DetectChip
    4. Optionally read BIOS version
    5. Close

Requires:
    - TTK3 API at C:\\SVSHARE\\User_Apps\\TTK3\\API\\Python\\
    - TTK3/SQUID USB device connected
    - Platform power OFF for at least 10 seconds
"""

import argparse
import json
import sys

TTK3_API_PATH = r"C:\SVSHARE\User_Apps\TTK3\API\Python"
sys.path.insert(0, TTK3_API_PATH)


def detect_chip(device_index=0, read_bios_version=False):
    """Detect SPI flash chip and optionally read BIOS version.

    Args:
        device_index: TTK3 device index if multiple connected.
        read_bios_version: If True, also read the BIOS version string.

    Returns:
        dict with detection results.
    """
    from SPI_Programmer import BiosProgrammer

    result = {
        "status": "unknown",
        "device_index": device_index,
        "chip_detected": False,
    }

    flash = BiosProgrammer()
    try:
        if device_index > 0:
            flash.OpenIndex(device_index)
        else:
            flash.Open()

        flash.DetectChip()
        result["chip_detected"] = True

        if read_bios_version:
            try:
                version = flash.ReadBiosVersion(turnOff=True)
                result["bios_version"] = str(version)
            except Exception as e:
                result["bios_version_error"] = str(e)

        result["status"] = "success"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["error_type"] = type(e).__name__

    finally:
        flash.Close()

    return result


def main():
    parser = argparse.ArgumentParser(description="Detect SPI flash chip via TTK3")
    parser.add_argument("--device-index", type=int, default=0, help="TTK3 device index (default: 0)")
    parser.add_argument("--read-bios-version", action="store_true", help="Also read current BIOS version")

    args = parser.parse_args()

    result = detect_chip(
        device_index=args.device_index,
        read_bios_version=args.read_bios_version,
    )

    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
