#!/usr/bin/env python3
"""Flash a BIOS/IFWI image to the SPI flash chip via TTK3.

Usage:
    python flash_bios.py --image <path_to_bin>
    python flash_bios.py --image <path_to_bin> --chip-select 1
    python flash_bios.py --image <path_to_bin> --device-index 0 --skip-verify

Steps:
    1. Open BiosProgrammer (and optionally PowerControl)
    2. DetectChip + SetChipSelect
    3. LoadImage from file
    4. Erase flash
    5. ProgramAndVerify (or Program only with --skip-verify)
    6. Close all resources (LIFO order)

Requires:
    - TTK3 API at C:\\SVSHARE\\User_Apps\\TTK3\\API\\Python\\
    - TTK3/SQUID USB device connected
    - Platform power OFF before flashing (or use --power-off)
"""

import argparse
import json
import os
import sys
import time

# TTK3 API path
TTK3_API_PATH = r"C:\SVSHARE\User_Apps\TTK3\API\Python"
sys.path.insert(0, TTK3_API_PATH)


def flash_bios(image_path, chip_select=0, device_index=0, skip_verify=False, power_off=False):
    """Flash a BIOS image with full error handling and resource cleanup.

    Args:
        image_path: Path to the .bin BIOS/IFWI image file.
        chip_select: SPI chip select (0 or 1). Default 0.
        device_index: TTK3 device index if multiple connected. Default 0.
        skip_verify: If True, use Program() instead of ProgramAndVerify().
        power_off: If True, power off platform before flashing via PowerSplitter.

    Returns:
        dict with status, timing, and details.
    """
    from SPI_Programmer import BiosProgrammer

    result = {
        "status": "unknown",
        "image": image_path,
        "chip_select": chip_select,
        "device_index": device_index,
        "steps": [],
        "elapsed_seconds": 0,
    }

    if not os.path.isfile(image_path):
        result["status"] = "error"
        result["error"] = f"Image file not found: {image_path}"
        return result

    start_time = time.time()
    power = None

    try:
        # Optional: power off platform first
        if power_off:
            from PowerControl import PowerControl
            power = PowerControl()
            power.OpenPowerSplitter()
            result["steps"].append("power_splitter_opened")
            power.AllPortsOff()
            result["steps"].append("power_off")
            time.sleep(10)  # MANDATORY 10s wait for power to fully discharge before SPI access

        # Open SPI programmer
        flash = BiosProgrammer()
        try:
            if device_index > 0:
                flash.OpenIndex(device_index)
            else:
                flash.Open()
            result["steps"].append("programmer_opened")

            # Detect chip
            flash.DetectChip()
            result["steps"].append("chip_detected")

            # Set chip select
            flash.SetChipSelect(chip_select)
            result["steps"].append(f"chip_select_{chip_select}")

            # Load image
            flash.LoadImage(image_path)
            result["steps"].append("image_loaded")

            # Erase
            flash.Erase()
            result["steps"].append("flash_erased")

            # Program and verify
            if skip_verify:
                flash.Program()
                result["steps"].append("programmed")
            else:
                flash.ProgramAndVerify()
                result["steps"].append("programmed_and_verified")

            result["status"] = "success"

        finally:
            flash.Close()
            result["steps"].append("programmer_closed")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["error_type"] = type(e).__name__

    finally:
        # LIFO: close power last (opened first)
        if power is not None:
            try:
                power.Close()
                result["steps"].append("power_closed")
            except Exception as e:
                result["power_close_error"] = str(e)

    result["elapsed_seconds"] = round(time.time() - start_time, 2)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Flash a BIOS/IFWI image via TTK3 SPI programmer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--image", required=True, help="Path to .bin BIOS/IFWI image file")
    parser.add_argument("--chip-select", type=int, default=0, choices=[0, 1], help="SPI chip select (default: 0)")
    parser.add_argument("--device-index", type=int, default=0, help="TTK3 device index (default: 0)")
    parser.add_argument("--skip-verify", action="store_true", help="Skip verify step (Program only, no ProgramAndVerify)")
    parser.add_argument("--power-off", action="store_true", help="Power off platform via PowerSplitter before flashing")

    args = parser.parse_args()

    result = flash_bios(
        image_path=args.image,
        chip_select=args.chip_select,
        device_index=args.device_index,
        skip_verify=args.skip_verify,
        power_off=args.power_off,
    )

    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
