#!/usr/bin/env python3
"""
USB Functional Validation — Test Template

This template provides a standard structure for USB validation test scripts
that integrate with Intel's NGA (Next Generation Automation) framework and
Galaxy XML test orchestration.

Usage:
    python usb_test_template.py --test <test_name> [--device <device_id>] [--port <port>]

NGA Exit Codes:
    0  = PASS
    1  = FAIL
    12 = Device not found
    13 = Configuration error

Owner: kvejaya (Kalaivanan Vejaya)
Version: 2.0.0
"""

import argparse
import logging
import sys
import os
import time

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

# NGA Exit Codes
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_DEVICE_NOT_FOUND = 12
EXIT_CONFIG_ERROR = 13

# USB Speed Values (xHCI spec)
USB_SPEED = {
    0: "Unknown",
    1: "Full Speed (12 Mbps)",
    2: "Low Speed (1.5 Mbps)",
    3: "High Speed (480 Mbps)",
    4: "SuperSpeed (5 Gbps)",
    5: "SuperSpeed+ (10 Gbps)",
    6: "SuperSpeed+ (20 Gbps)",
}

# PLS (Port Link State) Values
PLS_STATE = {
    0: "U0 (Active)",
    1: "U1 (Standby)",
    2: "U2 (Sleep)",
    3: "U3 (Suspend)",
    4: "Disabled",
    5: "Rx.Detect",
    6: "Inactive",
    7: "Polling",
    8: "Recovery",
    9: "Hot Reset",
    10: "Compliance Mode",
    15: "Resume",
}

# ─────────────────────────────────────────────────────────────
# Logging Setup
# ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        # Uncomment to log to file:
        # logging.FileHandler("usb_test.log"),
    ],
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────

def check_usb_device_present(device_id: str) -> bool:
    """
    Check if a USB device with the given ID is present in the system.

    Args:
        device_id: USB device identifier (VID:PID format, e.g., '8087:0032')

    Returns:
        True if device is found, False otherwise
    """
    # PLACEHOLDER: Replace with actual device detection logic
    # Example using usb_helper_ipsv.py:
    #   from usb_helper_ipsv import USBHelper
    #   helper = USBHelper()
    #   return helper.is_device_present(device_id)
    log.info(f"Checking for USB device: {device_id}")
    raise NotImplementedError("Replace with actual device detection logic")


def get_port_status(port_number: int) -> dict:
    """
    Read the PORTSC register for a given port and return parsed status.

    Args:
        port_number: 1-based USB port number

    Returns:
        Dictionary with CCS, PED, PLS, Speed, PP fields
    """
    # PLACEHOLDER: Replace with actual register read
    # Example using usb_helper_ipsv.py:
    #   from usb_helper_ipsv import USBHelper
    #   helper = USBHelper()
    #   return helper.get_port_status(port_number)
    log.info(f"Reading PORTSC for port {port_number}")
    raise NotImplementedError("Replace with actual PORTSC read logic")


def verify_usb_speed(port_number: int, expected_speed: int) -> bool:
    """
    Verify that a USB port is operating at the expected speed.

    Args:
        port_number: 1-based USB port number
        expected_speed: Expected speed value (see USB_SPEED dict)

    Returns:
        True if speed matches expected, False otherwise
    """
    status = get_port_status(port_number)
    actual_speed = status.get("speed", 0)
    expected_name = USB_SPEED.get(expected_speed, "Unknown")
    actual_name = USB_SPEED.get(actual_speed, "Unknown")

    if actual_speed == expected_speed:
        log.info(f"Port {port_number} speed OK: {actual_name}")
        return True
    else:
        log.error(
            f"Port {port_number} speed MISMATCH: "
            f"expected={expected_name}, actual={actual_name}"
        )
        return False


def wait_for_device(device_id: str, timeout_sec: int = 30) -> bool:
    """
    Wait for a USB device to appear in the system.

    Args:
        device_id: USB device identifier
        timeout_sec: Maximum time to wait in seconds

    Returns:
        True if device appeared, False if timeout
    """
    log.info(f"Waiting for device {device_id} (timeout={timeout_sec}s)")
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            if check_usb_device_present(device_id):
                log.info(f"Device {device_id} found after {time.time() - start:.1f}s")
                return True
        except NotImplementedError:
            log.warning("Device check not implemented — skipping wait")
            return False
        time.sleep(1)
    log.error(f"Device {device_id} not found after {timeout_sec}s")
    return False


# ─────────────────────────────────────────────────────────────
# Test Functions
# ─────────────────────────────────────────────────────────────

def test_enumeration(args) -> int:
    """
    Verify USB device enumeration.

    Checks:
    1. Device is present in system
    2. Device is connected at expected speed
    3. No yellow-bang in Device Manager
    """
    log.info("=" * 60)
    log.info("TEST: USB Enumeration")
    log.info("=" * 60)

    device_id = args.device
    if not device_id:
        log.error("No device ID specified (--device VID:PID)")
        return EXIT_CONFIG_ERROR

    # Step 1: Check device presence
    try:
        if not check_usb_device_present(device_id):
            log.error(f"Device {device_id} not enumerated")
            return EXIT_DEVICE_NOT_FOUND
    except NotImplementedError:
        log.warning("Device check not implemented — PLACEHOLDER test")
        return EXIT_PASS  # Remove this in real tests

    # Step 2: Verify speed (if port specified)
    if args.port:
        expected_speed = args.expected_speed or 4  # Default: SuperSpeed
        if not verify_usb_speed(args.port, expected_speed):
            return EXIT_FAIL

    # Step 3: Check for yellow-bang
    # PLACEHOLDER: Add yellow-bang check
    # from yellowbang_usb import check_yellowbang
    # if check_yellowbang():
    #     log.error("Yellow-bang detected!")
    #     return EXIT_FAIL

    log.info("TEST PASSED: USB Enumeration")
    return EXIT_PASS


def test_bulk_transfer(args) -> int:
    """
    Run USB bulk data transfer test.

    Checks:
    1. Device enumerated
    2. Bulk transfer completes without errors
    3. Data integrity verified
    """
    log.info("=" * 60)
    log.info("TEST: USB Bulk Transfer")
    log.info("=" * 60)

    # PLACEHOLDER: Replace with actual bulk transfer logic
    # Example:
    #   from bulkstart import BulkTransfer
    #   bt = BulkTransfer(device=args.device, duration=args.duration)
    #   result = bt.run()
    #   return EXIT_PASS if result.passed else EXIT_FAIL

    log.warning("Bulk transfer test not implemented — PLACEHOLDER")
    return EXIT_PASS


def test_power_management(args) -> int:
    """
    Verify USB power management (LPM, D-states, S0ix).

    Checks:
    1. Device enters U1/U2 link states
    2. xHCI enters D3 when idle
    3. LTR values are correct
    4. Platform reaches S0ix (if applicable)
    """
    log.info("=" * 60)
    log.info("TEST: USB Power Management")
    log.info("=" * 60)

    # PLACEHOLDER: Replace with actual PM validation
    # Example:
    #   from lpm import LPMChecker
    #   checker = LPMChecker(port=args.port)
    #   if not checker.verify_u1_entry():
    #       return EXIT_FAIL
    #   if not checker.verify_u2_entry():
    #       return EXIT_FAIL

    log.warning("Power management test not implemented — PLACEHOLDER")
    return EXIT_PASS


def test_hotplug(args) -> int:
    """
    Verify USB hot-plug/unplug behavior.

    Checks:
    1. Device enumerates after plug
    2. Device de-enumerates after unplug
    3. No system errors during plug/unplug cycles
    """
    log.info("=" * 60)
    log.info("TEST: USB Hot-Plug")
    log.info("=" * 60)

    # PLACEHOLDER: Replace with actual hotplug logic
    # Example using CSwitch:
    #   from cswitch_api import CSwitch
    #   cs = CSwitch()
    #   cs.disconnect_port(args.port)
    #   time.sleep(2)
    #   cs.connect_port(args.port)
    #   if not wait_for_device(args.device):
    #       return EXIT_FAIL

    log.warning("Hot-plug test not implemented — PLACEHOLDER")
    return EXIT_PASS


# ─────────────────────────────────────────────────────────────
# Test Registry
# ─────────────────────────────────────────────────────────────

TESTS = {
    "enumeration": test_enumeration,
    "bulk_transfer": test_bulk_transfer,
    "power_management": test_power_management,
    "hotplug": test_hotplug,
}


# ─────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="USB Functional Validation Test Template"
    )
    parser.add_argument(
        "--test",
        choices=list(TESTS.keys()),
        required=True,
        help="Test to run",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="USB device ID in VID:PID format (e.g., 8087:0032)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="USB port number (1-based)",
    )
    parser.add_argument(
        "--expected-speed",
        type=int,
        default=None,
        help="Expected USB speed value (1=FS, 2=LS, 3=HS, 4=SS, 5=SS+10G, 6=SS+20G)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Test duration in seconds (for transfer tests)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    log.info(f"Platform: {os.environ.get('PLATFORM', 'Unknown')}")
    log.info(f"Test: {args.test}")
    log.info(f"Device: {args.device or 'N/A'}")
    log.info(f"Port: {args.port or 'N/A'}")

    test_func = TESTS[args.test]
    exit_code = test_func(args)

    exit_name = {
        EXIT_PASS: "PASS",
        EXIT_FAIL: "FAIL",
        EXIT_DEVICE_NOT_FOUND: "DEVICE_NOT_FOUND",
        EXIT_CONFIG_ERROR: "CONFIG_ERROR",
    }.get(exit_code, f"UNKNOWN({exit_code})")

    log.info(f"Exit code: {exit_code} ({exit_name})")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
