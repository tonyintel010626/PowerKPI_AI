---
name: fv-gbe/driver
description: "Intel GbE Windows (e1d68.sys / e1e68.sys) and Linux (e1000e / igc) driver validation — INF loading, PnP binding, advanced properties, version checks, and cross-platform behavioral differences."
disable: false
---

# Skill: fv-gbe/driver

## Overview

This skill covers driver validation for Intel I219 (e1000e family) and I226/I225 (igc family) GbE controllers. It addresses Windows and Linux driver behavior, INF/udev binding, PnP lifecycle, advanced property configuration, and known driver-level errata.

---

## Driver Mapping

| Controller | Windows Driver | Linux Driver | Module |
|------------|----------------|--------------|--------|
| I219 | e1d68.sys (NDIS 6.x) | e1000e | `e1000e.ko` |
| I226-LM / I226-V | e2f68.sys | igc | `igc.ko` |
| I225-LM / I225-V | e2f68.sys | igc | `igc.ko` |

---

## Windows Driver Validation

### Checking Driver Version

```powershell
# Get driver version
Get-WmiObject Win32_PnPSignedDriver | Where-Object { $_.DeviceName -like "*I219*" -or $_.DeviceName -like "*I226*" } | Select-Object DeviceName, DriverVersion, DriverDate

# Alternative — check via device manager PowerShell
Get-PnpDevice | Where-Object { $_.FriendlyName -like "*Intel*Ethernet*" } | ForEach-Object {
    $dev = $_
    Get-PnpDeviceProperty -InstanceId $dev.InstanceId -KeyName "DEVPKEY_Device_DriverVersion" | Select-Object Data
}
```

### Verifying Driver Binding (INF)

```powershell
# Check device status
Get-PnpDevice | Where-Object { $_.FriendlyName -like "*Intel*Ethernet*" } | Select-Object FriendlyName, Status, ProblemCode

# Status "OK" = driver loaded correctly
# Status "Unknown" = driver missing or not matched
# ProblemCode 0 = no error
# ProblemCode 28 = driver not installed
# ProblemCode 43 = driver reported an error
```

### Checking INF Match

Intel GbE INFs declare supported hardware IDs. If a new Device ID is not in the INF, the device shows as "Unknown Device".

```powershell
# Find the INF file for the GbE adapter
$infPath = (Get-WmiObject Win32_PnPSignedDriver | Where-Object { $_.DeviceName -like "*I219*" }).InfName
Write-Host "INF: $infPath"
# Usually: C:\Windows\System32\DriverStore\FileRepository\e1d68x64.inf_amd64_*\e1d68x64.inf

# Check HWIDs in INF (search for VEN_8086)
Select-String -Path "C:\Windows\INF\oem*.inf" -Pattern "VEN_8086&DEV_550A" | Select-Object Filename, Line
```

### Advanced Driver Properties (Windows)

Key properties accessible via Device Manager → Advanced tab or PowerShell:

```powershell
# List all advanced properties
Get-NetAdapterAdvancedProperty -Name "Ethernet"

# Key properties to validate:
# - "Speed & Duplex" = Auto Negotiation
# - "Interrupt Moderation" = Enabled
# - "Receive Buffers" >= 256
# - "Transmit Buffers" >= 256
# - "Energy Efficient Ethernet" = Enabled (if EEE test)
# - "Wake on Magic Packet" = Enabled (if WoL test)
```

### Device Manager Error Codes

| Code | Meaning | Resolution |
|------|---------|------------|
| 0 | No error | OK |
| 10 | Device can't start | Driver or hardware error → check event log |
| 28 | Drivers not installed | Install driver, or add Device ID to INF |
| 43 | Device reported an error | Hardware or firmware issue → check MMIO access |
| 45 | Not connected | PCIe link issue, device not enumerated |

---

## Linux Driver Validation

### Verifying Driver Loaded

```bash
# Check e1000e module
lsmod | grep e1000e
modinfo e1000e | head -20

# Check igc module
lsmod | grep igc
modinfo igc | head -20

# Check which driver is bound
ls -la /sys/bus/pci/devices/0000:00:1f.6/driver
# Should link to: ../../../bus/pci/drivers/e1000e
```

### Driver Version

```bash
# Via modinfo
modinfo e1000e | grep "^version"

# Via ethtool
ethtool -i eth0
# Shows: driver, version, firmware-version, bus-info
```

### dmesg Validation

```bash
# Check driver probe messages
dmesg | grep -i "e1000e\|igc\|Intel.*Ethernet"

# Expected on successful probe:
# e1000e: Intel(R) PRO/1000 Network Driver
# e1000e 0000:00:1f.6: Interrupt Throttling Rate (ints/sec): 8000
# e1000e 0000:00:1f.6 eth0: renamed from enp0s31f6
# e1000e 0000:00:1f.6 eth0: (PCI Express:2.5GT/s:Width x1) ...

# Watch for errors
dmesg | grep -i "e1000e\|igc" | grep -i "error\|warn\|fail"
```

### Runtime PM (Linux)

```bash
# Check if runtime PM is enabled
cat /sys/bus/pci/devices/0000:00:1f.6/power/control
# "auto" = runtime PM enabled (good for D3 testing)
# "on" = runtime PM disabled

# Enable runtime PM
echo "auto" > /sys/bus/pci/devices/0000:00:1f.6/power/control
```

### Driver Statistics

```bash
# Detailed driver statistics (useful for debugging)
ethtool -S eth0

# Key counters to check:
# tx_packets, rx_packets — traffic counters
# tx_errors, rx_errors — error counters (should be 0)
# rx_crc_errors — CRC errors (should be 0)
# rx_dropped — dropped receive packets
# tx_dropped — dropped transmit packets
# rx_fifo_errors — RX FIFO overflow (increase ring buffer if non-zero)
```

---

## Driver Error Handling

### Windows Event Log

```powershell
# Check System event log for GbE driver errors
Get-EventLog -LogName System -Source "*e1d68*" -Newest 20 | Format-List

# Or via Event Viewer filter
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='*Intel*Ethernet*'} -MaxEvents 50
```

### Linux Kernel Log

```bash
# Check for driver errors
journalctl -k | grep -i "e1000e\|igc" | tail -50

# Check for PCIe errors associated with GbE
journalctl -k | grep "0000:00:1f.6" | tail -50
```

---

## Cross-Platform Behavioral Differences

| Feature | Windows e1000e | Linux e1000e |
|---------|---------------|-------------|
| Runtime PM | Managed via NDIS power policy | `power/control` sysfs + driver hooks |
| WoL configuration | Device Manager / PowerShell | ethtool -s wol |
| RSS queues | Configured via Advanced Properties | ethtool -L |
| Interrupt coalescing | Interrupt Moderation Rate property | ethtool -C |
| TSO | LSO property | ethtool -K tso |
| Promiscuous mode | NetSh or raw socket | ip link set promisc on |
| Statistics | WMI / NDISTest | ethtool -S |

---

## Known Driver Issues / Errata

### e1000e Link Restart After Resume
On some platforms, the e1000e driver may fail to restore link after S3/S4 resume. Workaround: reload driver module.
```bash
modprobe -r e1000e; modprobe e1000e
```

### I219 MAC-PHY Reset After D3
After D3cold entry/exit, the I219 MAC requires a PHY reset to re-establish SGMII link. The driver handles this, but timing issues can occur if power sequencing is too fast.

### igc Driver MTU Limitation
The igc driver (I226/I225) has a known limitation where changing MTU above 9000 bytes may require a link restart.

---

## Driver Validation Checklist

| Check | Command | Pass Criteria |
|-------|---------|---------------|
| Driver loaded | `lsmod | grep e1000e` | Module present |
| No probe errors | `dmesg | grep e1000e` | No ERROR/WARN |
| Driver version acceptable | `modinfo e1000e | grep version` | >= minimum version for platform |
| INF match (Windows) | Device Manager | Status = OK, no error code |
| No TX/RX errors | `ethtool -S eth0 | grep error` | All counters = 0 |
| Runtime PM enabled | `cat .../power/control` | "auto" |
| WoL configurable | `ethtool eth0 | grep Wake` | Shows supported modes |
