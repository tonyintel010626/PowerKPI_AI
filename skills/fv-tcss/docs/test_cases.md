# FV-TCSS Test Cases Reference

## Overview

This document provides comprehensive test case coverage for TCSS (Type-C Subsystem) functional validation across Intel Client SoC platforms. Test cases cover USB4, USB3, Thunderbolt 4/3, IOM, DisplayPort Alt Mode, PCIe tunneling, and DMA operations.

**Platforms Supported:** MTL, PTL, RZL, NVL, TTL

---

## Test Case Organization

TCSS test cases are organized by functional domain and test type:

```
TCSS Test Suite
├── Enumeration Tests
├── USB4 Tests
├── Thunderbolt Tests
├── IOM Tests
├── DisplayPort Tests
├── DMA Tests
├── Power Management Tests
├── Performance Tests
├── Stress/Reliability Tests
└── Compliance Tests
```

---

## TEST CASE CATEGORIES

### 1. ENUMERATION TESTS

**Purpose:** Verify TCSS device discovery, PCI enumeration, BAR allocation, and configuration space setup.

| Test ID | Test Name | Description | Platforms | Priority |
|---------|-----------|-------------|-----------|----------|
| TCSS-ENUM-001 | PCI Device Discovery | Verify TCSS PCI device present in lspci | All | P0 |
| TCSS-ENUM-002 | Device ID Verification | Verify TCSS DID matches platform spec | All | P0 |
| TCSS-ENUM-003 | BAR0 Allocation | Verify BAR0 allocated and within valid range | All | P0 |
| TCSS-ENUM-004 | PCI Capabilities | Verify PM, MSI, PCIe, LTR capabilities present | All | P0 |
| TCSS-ENUM-005 | Bus Master Enable | Verify bus master bit set in Command register | All | P0 |
| TCSS-ENUM-006 | Memory Space Enable | Verify memory space enable bit set | All | P0 |
| TCSS-ENUM-007 | Device Tree Validation | Verify device tree node present (Linux) | All | P1 |
| TCSS-ENUM-008 | ACPI Table Check | Verify TCSS ACPI entries present | All | P1 |
| TCSS-ENUM-009 | Multi-Port Enumeration | Verify all TCSS ports enumerated correctly | All | P0 |
| TCSS-ENUM-010 | Hot Plug Enumeration | Verify device enumeration after hot plug | All | P1 |

**Expected Results:**
- TCSS device visible in `lspci` or Device Manager
- Correct DID/VID values per platform HAS
- BAR0 allocated with correct size
- All required capabilities present and enabled

**Debug Commands:**
```bash
# Linux
lspci -nn | grep -i type-c
lspci -vvv -s <BDF> | grep -E "Device|BAR|Capabilities"
cat /sys/bus/pci/devices/<BDF>/config

# Windows
Get-PciDevice | Where-Object {$_.DeviceID -like "*TCSS*"}

# PythonSV
from pythonsv.device import pci
tcss = pci.Device("00:0d.2")  # Query HAS for BDF
print(f"DID: 0x{tcss.config.read16(0x02):04X}")
```

---

### 2. USB4 TESTS

**Purpose:** Validate USB4 router functionality, tunneling, link training, and bandwidth management.

| Test ID | Test Name | Description | Platforms | Priority |
|---------|-----------|-------------|-----------|----------|
| TCSS-USB4-001 | USB4 Router Detection | Verify USB4 router enumerated | All | P0 |
| TCSS-USB4-002 | Link Training Gen2 | Verify USB4 Gen2 (10G) link training | All | P0 |
| TCSS-USB4-003 | Link Training Gen3 | Verify USB4 Gen3 (20G) link training | All | P0 |
| TCSS-USB4-004 | Link Training Gen4 | Verify USB4 Gen4 (40G) link training | MTL, NVL, TTL | P1 |
| TCSS-USB4-005 | Link Training Gen5 | Verify USB4 Gen5 (80G) link training | NVL, TTL | P2 |
| TCSS-USB4-006 | USB Tunneling | Verify USB3 device tunneling over USB4 | All | P0 |
| TCSS-USB4-007 | PCIe Tunneling | Verify PCIe device tunneling over USB4 | All | P0 |
| TCSS-USB4-008 | DP Tunneling | Verify DisplayPort tunneling over USB4 | All | P0 |
| TCSS-USB4-009 | Bandwidth Allocation | Verify dynamic bandwidth allocation | All | P1 |
| TCSS-USB4-010 | Asymmetric Link | Verify asymmetric link (different TX/RX speeds) | All | P2 |
| TCSS-USB4-011 | Multi-Tunnel | Verify simultaneous USB+PCIe+DP tunnels | All | P1 |
| TCSS-USB4-012 | Link Recovery | Verify link recovery after error | All | P1 |
| TCSS-USB4-013 | Router Reset | Verify router reset and re-enumeration | All | P2 |

**Expected Results:**
- USB4 router present in `lsusb` or Device Manager
- Link training completes successfully at target speed
- Tunneled devices enumerated correctly
- Bandwidth allocated according to priority

**Debug Commands:**
```bash
# Linux
lsusb -t  # View USB4 topology
cat /sys/bus/thunderbolt/devices/0-0/generation  # Check USB4 generation

# Windows
Get-PnpDevice | Where-Object {$_.FriendlyName -like "*USB4*"}

# PythonSV
bar0 = tcss.bars[0]
link_status = bar0.read32(0x1004)  # Query HAS for offset
link_speed = ["Gen2 (10G)", "Gen3 (20G)", "Gen4 (40G)", "Gen5 (80G)"][(link_status >> 1) & 0x3]
print(f"USB4 Link Speed: {link_speed}")
```

---

### 3. THUNDERBOLT TESTS

**Purpose:** Validate Thunderbolt authentication, security levels, link training, and device compatibility.

| Test ID | Test Name | Description | Platforms | Priority |
|---------|-----------|-------------|-----------|----------|
| TCSS-TBT-001 | TBT Device Detection | Verify Thunderbolt device detected | All | P0 |
| TCSS-TBT-002 | TBT3 Authentication | Verify TBT3 device authentication | All | P0 |
| TCSS-TBT-003 | TBT4 Authentication | Verify TBT4 device authentication | All | P0 |
| TCSS-TBT-004 | Security Level SL0 | Verify SL0 (no auth) mode | All | P1 |
| TCSS-TBT-005 | Security Level SL1 | Verify SL1 (user approval) mode | All | P0 |
| TCSS-TBT-006 | Security Level SL2 | Verify SL2 (secure connect) mode | All | P0 |
| TCSS-TBT-007 | Security Level SL3 | Verify SL3 (DP only) mode | All | P1 |
| TCSS-TBT-008 | TBT Link Training | Verify TBT link training at 40Gbps | All | P0 |
| TCSS-TBT-009 | TBT PCIe Tunnel | Verify PCIe tunneling over TBT | All | P0 |
| TCSS-TBT-010 | TBT USB Tunnel | Verify USB tunneling over TBT | All | P0 |
| TCSS-TBT-011 | TBT DP Tunnel | Verify DP tunneling over TBT | All | P0 |
| TCSS-TBT-012 | TBT Daisy Chain | Verify TBT daisy chain (2+ devices) | All | P1 |
| TCSS-TBT-013 | TBT Dock | Verify TBT dock with multiple devices | All | P0 |
| TCSS-TBT-014 | TBT Hot Plug | Verify TBT hot plug/unplug | All | P1 |
| TCSS-TBT-015 | TBT Wake from S3 | Verify wake from S3 with TBT device | All | P1 |
| TCSS-TBT-016 | TBT Authorization Timeout | Verify auth timeout handling | All | P2 |

**Expected Results:**
- Thunderbolt device authorized and enumerated
- Correct security level applied
- Link training completes at expected speed
- All tunneled devices functional

**Debug Commands:**
```bash
# Linux
boltctl list  # List Thunderbolt devices
boltctl info <device>  # Device details
cat /sys/bus/thunderbolt/devices/*/authorized

# Windows
Get-PnpDevice | Where-Object {$_.FriendlyName -like "*Thunderbolt*"}

# PythonSV
tbt_auth = bar0.read32(0x2004)  # Query HAS for offset
auth_status = ["Not Authorized", "Authorizing", "Authorized", "Challenge"][tbt_auth & 0x3]
print(f"TBT Auth Status: {auth_status}")
```

---

### 4. IOM (I/O MANAGER) TESTS

**Purpose:** Validate IOM port configuration, Type-C orientation detection, mux control, and protocol switching.

| Test ID | Test Name | Description | Platforms | Priority |
|---------|-----------|-------------|-----------|----------|
| TCSS-IOM-001 | Port Connection Detection | Verify IOM detects port connection | All | P0 |
| TCSS-IOM-002 | Orientation Normal | Verify normal orientation detection | All | P0 |
| TCSS-IOM-003 | Orientation Flipped | Verify flipped orientation detection | All | P0 |
| TCSS-IOM-004 | USB2 Mode Detection | Verify USB2 mode detection | All | P0 |
| TCSS-IOM-005 | USB3 Mode Detection | Verify USB3 mode detection | All | P0 |
| TCSS-IOM-006 | USB4 Mode Detection | Verify USB4 mode detection | All | P0 |
| TCSS-IOM-007 | TBT Mode Detection | Verify Thunderbolt mode detection | All | P0 |
| TCSS-IOM-008 | DP Alt Mode Detection | Verify DP Alt Mode detection | All | P0 |
| TCSS-IOM-009 | Mux Control USB | Verify mux switches to USB | All | P0 |
| TCSS-IOM-010 | Mux Control TBT | Verify mux switches to Thunderbolt | All | P0 |
| TCSS-IOM-011 | Mux Control DP | Verify mux switches to DisplayPort | All | P0 |
| TCSS-IOM-012 | Multi-Port Config | Verify multiple ports configured independently | All | P1 |
| TCSS-IOM-013 | Hot Swap Detection | Verify IOM detects cable swap | All | P1 |
| TCSS-IOM-014 | Vbus Detection | Verify Vbus voltage detection | All | P1 |
| TCSS-IOM-015 | CC Pin Status | Verify CC1/CC2 pin status reporting | All | P2 |

**Expected Results:**
- IOM correctly detects connection state
- Orientation detected accurately (normal/flipped)
- Mux switches to correct protocol
- Multi-port configurations independent

**Debug Commands:**
```bash
# Linux
cat /sys/class/typec/port*/data_role
cat /sys/class/typec/port*/orientation

# PythonSV
iom_status = bar0.read32(0x00)  # Query HAS for offset
connected = (iom_status & 0x1) != 0
orientation = "Flipped" if (iom_status & 0x2) else "Normal"
usb_mode = ["USB2", "USB3", "USB4", "Reserved"][(iom_status >> 2) & 0x3]
print(f"Connected: {connected}, Orientation: {orientation}, Mode: {usb_mode}")
```

---

### 5. DISPLAYPORT ALT MODE TESTS

**Purpose:** Validate DisplayPort Alt Mode over Type-C, link training, multi-stream, and display functionality.

| Test ID | Test Name | Description | Platforms | Priority |
|---------|-----------|-------------|-----------|----------|
| TCSS-DP-001 | DP Alt Mode Entry | Verify DP Alt Mode negotiation | All | P0 |
| TCSS-DP-002 | DP Link Training 1.62G | Verify link training at 1.62 Gbps (RBR) | All | P0 |
| TCSS-DP-003 | DP Link Training 2.7G | Verify link training at 2.7 Gbps (HBR) | All | P0 |
| TCSS-DP-004 | DP Link Training 5.4G | Verify link training at 5.4 Gbps (HBR2) | All | P0 |
| TCSS-DP-005 | DP Link Training 8.1G | Verify link training at 8.1 Gbps (HBR3) | All | P0 |
| TCSS-DP-006 | DP 1 Lane Config | Verify 1-lane DP configuration | All | P1 |
| TCSS-DP-007 | DP 2 Lane Config | Verify 2-lane DP configuration | All | P0 |
| TCSS-DP-008 | DP 4 Lane Config | Verify 4-lane DP configuration | All | P0 |
| TCSS-DP-009 | DP Single Stream | Verify single display output (SST) | All | P0 |
| TCSS-DP-010 | DP Multi-Stream | Verify multi-stream transport (MST) | All | P1 |
| TCSS-DP-011 | DP EDID Read | Verify EDID read from display | All | P0 |
| TCSS-DP-012 | DP 1080p Display | Verify 1080p resolution | All | P0 |
| TCSS-DP-013 | DP 4K Display | Verify 4K (3840x2160) resolution | All | P0 |
| TCSS-DP-014 | DP 8K Display | Verify 8K resolution (if supported) | NVL, TTL | P2 |
| TCSS-DP-015 | DP Hot Plug Detect | Verify HPD signal handling | All | P1 |
| TCSS-DP-016 | DP Audio | Verify audio over DP | All | P1 |

**Expected Results:**
- DP Alt Mode negotiates successfully
- Link training completes at target rate/lanes
- Display output functional at expected resolution
- EDID read successfully

**Debug Commands:**
```bash
# Linux
xrandr --verbose  # Check DP output status
cat /sys/kernel/debug/dri/0/DP-*/link_status

# Windows
Get-CimInstance -ClassName Win32_VideoController

# PythonSV
dp_link_status = bar0.read32(0x3004)  # Query HAS for offset
link_trained = (dp_link_status & 0x1) != 0
link_rate = ["1.62 Gbps", "2.7 Gbps", "5.4 Gbps", "8.1 Gbps"][(dp_link_status >> 1) & 0x3]
lane_count = [1, 2, 4, 4][(dp_link_status >> 3) & 0x3]
print(f"DP Trained: {link_trained}, Rate: {link_rate}, Lanes: {lane_count}")
```

---

### 6. DMA TESTS

**Purpose:** Validate DMA engine functionality, data transfer, performance, and error handling.

| Test ID | Test Name | Description | Platforms | Priority |
|---------|-----------|-------------|-----------|----------|
| TCSS-DMA-001 | DMA Channel Init | Verify DMA channel initialization | All | P0 |
| TCSS-DMA-002 | DMA Single Transfer | Verify single DMA transfer completes | All | P0 |
| TCSS-DMA-003 | DMA Large Transfer | Verify large (1GB+) DMA transfer | All | P1 |
| TCSS-DMA-004 | DMA USB Tunnel | Verify DMA for USB tunneling | All | P0 |
| TCSS-DMA-005 | DMA PCIe Tunnel | Verify DMA for PCIe tunneling | All | P0 |
| TCSS-DMA-006 | DMA DP Tunnel | Verify DMA for DP tunneling | All | P0 |
| TCSS-DMA-007 | DMA Performance USB | Measure USB tunneling throughput | All | P1 |
| TCSS-DMA-008 | DMA Performance PCIe | Measure PCIe tunneling throughput | All | P1 |
| TCSS-DMA-009 | DMA Error Handling | Verify DMA error detection/recovery | All | P2 |
| TCSS-DMA-010 | DMA Multi-Channel | Verify concurrent DMA channels | All | P1 |

**Expected Results:**
- DMA channels initialize successfully
- Transfers complete without errors
- Performance meets platform targets
- Errors handled gracefully

**Debug Commands:**
```bash
# Linux
cat /sys/kernel/debug/dma_buf/bufinfo

# PythonSV
dma_status = bar0.read32(0x4004)  # Query HAS for offset
active_channels = (dma_status >> 8) & 0xFF
errors = (dma_status >> 16) & 0xFF
print(f"Active DMA Channels: {active_channels}, Errors: {errors}")
```

---

### 7. POWER MANAGEMENT TESTS

**Purpose:** Validate TCSS power states (D0, D0i2, D3), clock gating, power gating, S0ix, and wake events.

| Test ID | Test Name | Description | Platforms | Priority |
|---------|-----------|-------------|-----------|----------|
| TCSS-PM-001 | D0 State Entry | Verify TCSS enters D0 (active) state | All | P0 |
| TCSS-PM-002 | D0i2 State Entry | Verify TCSS enters D0i2 (idle) state | All | P0 |
| TCSS-PM-003 | D3hot State Entry | Verify TCSS enters D3hot state | All | P0 |
| TCSS-PM-004 | D3cold State Entry | Verify TCSS enters D3cold state | All | P1 |
| TCSS-PM-005 | D3 to D0 Resume | Verify TCSS resumes from D3 to D0 | All | P0 |
| TCSS-PM-006 | Clock Gating Enable | Verify clock gating enabled when idle | All | P0 |
| TCSS-PM-007 | Power Gating Enable | Verify power gating enabled in D3 | All | P0 |
| TCSS-PM-008 | S0ix Entry | Verify TCSS allows S0ix entry | All | P0 |
| TCSS-PM-009 | S0ix Exit | Verify TCSS functional after S0ix exit | All | P0 |
| TCSS-PM-010 | S3 Suspend | Verify TCSS suspends for S3 | All | P0 |
| TCSS-PM-011 | S3 Resume | Verify TCSS resumes from S3 | All | P0 |
| TCSS-PM-012 | S4 Hibernate | Verify TCSS survives S4 hibernate | All | P1 |
| TCSS-PM-013 | RTD3 Entry | Verify Runtime D3 (RTD3) entry | All | P1 |
| TCSS-PM-014 | RTD3 Exit | Verify RTD3 exit on device connection | All | P1 |
| TCSS-PM-015 | Wake on Connect | Verify wake from S3/S0ix on device connect | All | P1 |
| TCSS-PM-016 | LTR Programming | Verify LTR values programmed correctly | All | P1 |
| TCSS-PM-017 | PM Transition Timing | Measure D0→D3→D0 transition latency | All | P2 |

**Expected Results:**
- All power states entered/exited successfully
- Clock/power gating functional
- S0ix entry/exit without hang
- Wake events trigger resume correctly

**Debug Commands:**
```bash
# Linux
cat /sys/bus/pci/devices/<BDF>/power_state
cat /sys/kernel/debug/pmc_core/substate_residencies

# Windows
powercfg /sleepstudy

# PythonSV
pm_status = bar0.read32(0x5004)  # Query HAS for offset
power_state = ["D0", "D0i2", "D3hot", "D3cold"][pm_status & 0x3]
clock_gated = (pm_status & 0x4) != 0
power_gated = (pm_status & 0x8) != 0
print(f"Power State: {power_state}, Clock Gated: {clock_gated}, Power Gated: {power_gated}")
```

---

### 8. PERFORMANCE TESTS

**Purpose:** Measure TCSS throughput, latency, and performance characteristics.

| Test ID | Test Name | Description | Platforms | Priority |
|---------|-----------|-------------|-----------|----------|
| TCSS-PERF-001 | USB4 Gen2 Throughput | Measure USB4 Gen2 (10G) throughput | All | P1 |
| TCSS-PERF-002 | USB4 Gen3 Throughput | Measure USB4 Gen3 (20G) throughput | All | P1 |
| TCSS-PERF-003 | USB4 Gen4 Throughput | Measure USB4 Gen4 (40G) throughput | MTL, NVL, TTL | P1 |
| TCSS-PERF-004 | TBT3 Throughput | Measure TBT3 (40Gbps) throughput | All | P1 |
| TCSS-PERF-005 | TBT4 Throughput | Measure TBT4 (40Gbps) throughput | All | P1 |
| TCSS-PERF-006 | USB3 Tunnel Throughput | Measure USB3 over USB4/TBT throughput | All | P1 |
| TCSS-PERF-007 | PCIe Tunnel Throughput | Measure PCIe over USB4/TBT throughput | All | P1 |
| TCSS-PERF-008 | DP Bandwidth | Measure DisplayPort bandwidth utilization | All | P1 |
| TCSS-PERF-009 | DMA Latency | Measure DMA transfer latency | All | P2 |
| TCSS-PERF-010 | Concurrent Tunnels | Measure throughput with USB+PCIe+DP active | All | P1 |
| TCSS-PERF-011 | Power vs Performance | Measure power consumption at different loads | All | P2 |

**Expected Results:**
- Throughput meets platform specifications
- Latency within acceptable bounds
- Concurrent tunnels share bandwidth appropriately

**Performance Targets (Example — query HAS for actual targets):**
- USB4 Gen2: ~8 Gbps actual throughput
- USB4 Gen3: ~16 Gbps actual throughput
- TBT3/4: ~32 Gbps actual throughput
- USB3 tunnel: ~4 Gbps actual throughput

---

### 9. STRESS AND RELIABILITY TESTS

**Purpose:** Validate TCSS stability under stress conditions, long-duration operation, and error recovery.

| Test ID | Test Name | Description | Platforms | Priority |
|---------|-----------|-------------|-----------|----------|
| TCSS-STRESS-001 | Hot Plug Stress | 1000+ hot plug/unplug cycles | All | P1 |
| TCSS-STRESS-002 | PM Transition Stress | 1000+ D0↔D3 transitions | All | P1 |
| TCSS-STRESS-003 | S0ix Stress | 1000+ S0ix entry/exit cycles | All | P1 |
| TCSS-STRESS-004 | S3 Suspend Stress | 1000+ S3 suspend/resume cycles | All | P1 |
| TCSS-STRESS-005 | Link Training Stress | 1000+ link training cycles | All | P1 |
| TCSS-STRESS-006 | Data Transfer Stress | 24+ hours continuous data transfer | All | P1 |
| TCSS-STRESS-007 | Multi-Device Stress | Stress with max devices connected | All | P1 |
| TCSS-STRESS-008 | Thermal Stress | Operation at max thermal limits | All | P2 |
| TCSS-STRESS-009 | Cable Quality Stress | Test with marginal/poor cables | All | P2 |
| TCSS-STRESS-010 | Concurrent Tunnel Stress | Long-duration USB+PCIe+DP active | All | P1 |

**Expected Results:**
- No hangs or crashes during stress
- All cycles complete successfully
- Error recovery functional
- Performance stable over time

---

### 10. COMPLIANCE TESTS

**Purpose:** Validate TCSS compliance with USB4, Thunderbolt, DisplayPort, and USB-IF specifications.

| Test ID | Test Name | Description | Platforms | Priority |
|---------|-----------|-------------|-----------|----------|
| TCSS-COMP-001 | USB4 Compliance | Run USB-IF USB4 compliance suite | All | P0 |
| TCSS-COMP-002 | TBT3 Compliance | Run TBT3 compliance tests | All | P0 |
| TCSS-COMP-003 | TBT4 Compliance | Run TBT4 compliance tests | All | P0 |
| TCSS-COMP-004 | USB3 Compliance | Run USB3 electrical/protocol tests | All | P0 |
| TCSS-COMP-005 | DP Alt Mode Compliance | Run DP Alt Mode compliance tests | All | P0 |
| TCSS-COMP-006 | Type-C Compliance | Run USB Type-C compliance tests | All | P0 |
| TCSS-COMP-007 | Interop Testing | Test with wide range of devices/docks | All | P1 |

**Expected Results:**
- All compliance tests pass
- No protocol violations detected
- Interoperability with major vendors

---

## PLATFORM-SPECIFIC TEST COVERAGE

### Meteor Lake (MTL)

**Focus Areas:**
- First-generation USB4 support
- TBT4 baseline functionality
- D3/S0ix basic power management

**Key Tests:** All P0 tests + TCSS-USB4-003, TCSS-TBT-008, TCSS-PM-008

### Panther Lake (PTL)

**Focus Areas:**
- Enhanced USB4 Gen3/Gen4 support
- Improved power management
- Multi-port configuration

**Key Tests:** All P0/P1 tests + TCSS-USB4-004, TCSS-PERF-003, TCSS-PM-017

### Raptor Lake (RZL)

**Focus Areas:**
- Legacy TBT3 support
- Mature power management
- Stability and reliability

**Key Tests:** All P0 tests + TCSS-STRESS-* series

### Nova Lake (NVL)

**Focus Areas:**
- USB4 Gen5 (80G) support
- Advanced power management (enhanced D0i2/D3)
- 8K DisplayPort support

**Key Tests:** All tests including TCSS-USB4-005, TCSS-DP-014, TCSS-PM-017

### Thunder Lake (TTL)

**Focus Areas:**
- Next-generation USB4 features
- Power efficiency improvements
- New features (query HAS for details)

**Key Tests:** All applicable tests + platform-specific features

---

## NGA PROJECT MAPPING

TCSS test cases are organized in NGA projects per platform:

| Platform | NGA Project Name | Test Suite IDs | Owner |
|----------|------------------|----------------|-------|
| MTL | `MTL_TCSS_FV` | TCSS-ENUM-*, TCSS-USB4-*, TCSS-TBT-*, etc. | lingweio |
| PTL | `PTL_TCSS_FV` | TCSS-ENUM-*, TCSS-USB4-*, TCSS-TBT-*, etc. | lingweio |
| RZL | `RZL_TCSS_FV` | TCSS-ENUM-*, TCSS-USB4-*, TCSS-TBT-*, etc. | lingweio |
| NVL | `NVL_TCSS_FV` | TCSS-ENUM-*, TCSS-USB4-*, TCSS-TBT-*, etc. | lingweio |
| TTL | `TTL_TCSS_FV` | TCSS-ENUM-*, TCSS-USB4-*, TCSS-TBT-*, etc. | lingweio |

**To Query NGA for TCSS Tests:**
```python
# Use NGA search API to find TCSS test cases
# See fv-tcss agent for NGA integration details
```

---

## TEST EXECUTION WORKFLOW

### 1. Pre-Test Setup
```bash
# Identify TCSS device BDF
lspci -nn | grep -i type-c

# Check driver loaded
lsmod | grep -i thunderbolt

# Verify firmware version
cat /sys/bus/thunderbolt/devices/*/nvm_version
```

### 2. Execute Test Suite
```bash
# Run enumeration tests
pytest test_tcss_enumeration.py -v

# Run functional tests
pytest test_tcss_functional.py -v --platform=MTL

# Run stress tests
pytest test_tcss_stress.py -v --duration=24h
```

### 3. Post-Test Analysis
```bash
# Collect logs
journalctl -b | grep -i thunderbolt > tcss_kernel.log
dmesg | grep -i usb4 > tcss_dmesg.log

# Check error registers
python check_tcss_errors.py --bdf 00:0d.2

# Generate test report
pytest --html=tcss_report.html
```

---

## TEST AUTOMATION

### Automated Test Execution via NGA

TCSS tests can be executed automatically via NGA:

1. **Create Test Run:**
   - Select platform project (e.g., `MTL_TCSS_FV`)
   - Choose test suite (e.g., ENUM, USB4, TBT)
   - Assign to station pool

2. **Monitor Execution:**
   - Track test progress via NGA dashboard
   - Review real-time logs
   - Check failure buckets

3. **Analyze Results:**
   - Review pass/fail status
   - Check failure buckets for known issues
   - File HSDES sightings for new failures

### CI/CD Integration

TCSS tests integrated into CI/CD pipeline:
- **Pre-commit:** Run smoke tests (P0 enumeration)
- **Nightly:** Run full functional suite (P0 + P1)
- **Weekly:** Run stress and reliability tests
- **Release:** Run compliance and interop tests

---

## DEBUGGING FAILED TESTS

### Common Failure Scenarios

| Failure Type | Common Causes | Debug Steps |
|--------------|---------------|-------------|
| **Enumeration Fail** | BIOS config, driver issue | Check BIOS settings, verify driver loaded, check dmesg |
| **Link Training Fail** | Cable quality, PHY config | Try different cable, check PHY registers, verify firmware |
| **Auth Failure** | Security policy, device issue | Check security level, verify device authorized, check boltctl |
| **Power State Fail** | PM driver issue, HW bug | Check PM registers, verify LTR config, check S0ix blockers |
| **Performance Fail** | Bandwidth limit, DMA issue | Check link speed, verify DMA channels, measure actual BW |

### Debug Tools

- **lspci/lsusb:** Device enumeration
- **boltctl:** Thunderbolt management
- **dmesg/journalctl:** Kernel logs
- **PythonSV:** Register access
- **Intel VTune:** Performance profiling
- **USB/TBT Analyzer:** Protocol analysis

---

## REFERENCES

- **NGA Projects:** MTL_TCSS_FV, PTL_TCSS_FV, RZL_TCSS_FV, NVL_TCSS_FV, TTL_TCSS_FV
- **HAS Documents:** iTBT80G Thunderbolt Controller HAS (platform-specific)
- **Specifications:** USB4 Spec, TBT3/4 Spec, USB-C Spec, DP Alt Mode Spec
- **Test Scripts:** Query NGA projects for test script repository location
- **HSDES:** Search tenant "sighting" for TCSS-related issues

---

## AUDIT TRAIL

| Date       | Author    | Change |
|------------|-----------|--------|
| 2026-03-30 | lingweio  | Initial test cases documentation |
