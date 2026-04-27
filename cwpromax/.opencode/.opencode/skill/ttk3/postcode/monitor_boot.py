#!/usr/bin/env python3
"""Monitor POST codes during boot via TTK3 Port80.

Usage:
    python monitor_boot.py
    python monitor_boot.py --timeout 120 --interval 0.5
    python monitor_boot.py --target-code A0B1 --timeout 60

Steps:
    1. Open Port80
    2. Poll Read() at interval until timeout or target code reached
    3. Print POST code sequence as JSON
    4. Close

Requires:
    - TTK3 API at C:\\SVSHARE\\User_Apps\\TTK3\\API\\Python\\
    - TTK3/SQUID USB device connected
    - Platform powered on and booting
"""

import argparse
import json
import sys
import time

TTK3_API_PATH = r"C:\SVSHARE\User_Apps\TTK3\API\Python"
sys.path.insert(0, TTK3_API_PATH)


def monitor_boot(timeout=60, interval=1.0, target_code=None, device_type=0):
    """Monitor POST codes during boot.

    Args:
        timeout: Maximum seconds to monitor.
        interval: Seconds between reads.
        target_code: Stop when this POST code is seen (hex string, e.g., "A0B1").
        device_type: Device type (0=TTK3, 1=SQUID).

    Returns:
        dict with POST code sequence and result.
    """
    from Port80 import Port80

    result = {
        "status": "unknown",
        "timeout": timeout,
        "interval": interval,
        "target_code": target_code,
        "post_codes": [],
        "unique_codes": [],
        "elapsed_seconds": 0,
    }

    port80 = Port80()
    start_time = time.time()
    last_code = None

    try:
        port80.Open(deviceType=device_type)

        while (time.time() - start_time) < timeout:
            code = port80.Read()
            code_str = str(code)
            elapsed = round(time.time() - start_time, 2)

            # Only log changes
            if code_str != last_code:
                entry = {"code": code_str, "elapsed": elapsed}
                result["post_codes"].append(entry)
                last_code = code_str

                # Print progress to stderr for real-time monitoring
                print(f"[{elapsed:6.1f}s] POST: {code_str}", file=sys.stderr)

                # Check target
                if target_code and code_str.upper() == target_code.upper():
                    result["status"] = "target_reached"
                    result["target_reached_at"] = elapsed
                    break

            time.sleep(interval)
        else:
            result["status"] = "timeout"

        if result["status"] == "unknown":
            result["status"] = "timeout"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["error_type"] = type(e).__name__

    finally:
        port80.Close()

    result["elapsed_seconds"] = round(time.time() - start_time, 2)
    result["unique_codes"] = list(dict.fromkeys(
        entry["code"] for entry in result["post_codes"]
    ))
    result["total_transitions"] = len(result["post_codes"])

    return result


def main():
    parser = argparse.ArgumentParser(description="Monitor POST codes during boot via TTK3")
    parser.add_argument("--timeout", type=int, default=60, help="Max seconds to monitor (default: 60)")
    parser.add_argument("--interval", type=float, default=1.0, help="Poll interval in seconds (default: 1.0)")
    parser.add_argument("--target-code", help="Stop when this POST code is seen (hex string, e.g., A0B1)")
    parser.add_argument("--device-type", type=int, default=0, choices=[0, 1],
                        help="Device type: 0=TTK3, 1=SQUID (default: 0)")

    args = parser.parse_args()

    result = monitor_boot(
        timeout=args.timeout,
        interval=args.interval,
        target_code=args.target_code,
        device_type=args.device_type,
    )

    print(json.dumps(result, indent=2))

    if result["status"] == "target_reached":
        return 0
    elif result["status"] == "timeout":
        return 0  # Timeout is not an error — data was collected
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
