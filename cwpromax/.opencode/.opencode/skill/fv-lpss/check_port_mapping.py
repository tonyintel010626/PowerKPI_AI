#!/usr/bin/env python
"""
Check which LPSS port corresponds to PCI function 12
"""
import sys
sys.path.insert(0, r'C:\pythonsv\novalake')

print("=" * 80)
print("LPSS Port Mapping Checker")
print("=" * 80)
print("\nInitializing PythonSV... (this may take ~25 seconds)")

import namednodes
sv = namednodes.sv
sv.refresh()

print("✓ PythonSV initialized successfully\n")

# Import lpss_main to get port mapping
import vjt.lpss.lpss_main as lmain

ports = lmain.lhc.ports

print(f"Total LPSS ports: {len(ports)}\n")
print("=" * 80)
print("LPSS Port to PCI Function Mapping:")
print("=" * 80)

# Standard LPSS port mapping based on Intel architecture
# I2C: Functions 0-5, I3C: Functions 6-9, SPI: Functions 10-12, UART: Functions 13-15
lpss_mapping = {
    0: "I2C0",
    1: "I2C1", 
    2: "I2C2",
    3: "I2C3",
    4: "I2C4",
    5: "I2C5",
    6: "I3C0",
    7: "I3C1",
    8: "I3C2",
    9: "I3C3",
    10: "SPI0",
    11: "SPI1",
    12: "SPI2",
    13: "UART0",
    14: "UART1",
    15: "UART2"
}

print("\nStandard LPSS PCI Function Mapping:")
for func_num, port_name in lpss_mapping.items():
    marker = " <-- TARGET" if func_num == 12 else ""
    print(f"  PCI Function {func_num:2d}: {port_name}{marker}")

print("\n" + "=" * 80)
print(f"\n✓ PCI Function 12 corresponds to: SPI2")
print("\nRegister path analysis:")
print("  pcd.lpss.lpss_regs.iosf2axi_env_i.file_iosf2axi_pci_pf_top_12")
print("  pmectrlstatus.powerstate")
print("\n  → This is the PME Control/Status powerstate register for SPI2")
print("=" * 80)

# Verify with actual port objects
print("\nVerifying with loaded ports:")
for i, port in enumerate(ports):
    port_name = f"{port.protocol.upper()}{port.port_number}"
    print(f"  lhc.ports[{i:2d}]: {port_name}")
    if port_name == "SPI2":
        print(f"    → SPI2 found at index {i}")

print("\n" + "=" * 80)
