---
name: fv-gbe/traffic
description: "GbE TX/RX data path validation, loopback testing, throughput measurement, TCP/UDP offloads, and interrupt coalescing for Intel I219 and I226/I225."
disable: false
---

# Skill: fv-gbe/traffic

## Overview

This skill covers data path validation for Intel GbE controllers. It includes ping tests, iperf throughput measurements, loopback testing, hardware offload verification (TSO, LRO, checksum), interrupt coalescing, and multi-queue (RSS) validation.

---

## Basic Connectivity Tests

### ICMP Ping (Windows)

```powershell
# Basic ping
ping 192.168.1.1 -n 100

# Large packet ping (checks MTU/fragmentation)
ping 192.168.1.1 -l 8972 -n 10 -f

# Continuous ping for stability test
ping 192.168.1.1 -t
```

### ICMP Ping (Linux)

```bash
# Basic ping
ping -c 100 192.168.1.1

# Large packet ping (MTU test)
ping -s 8972 -M do -c 10 192.168.1.1

# Flood ping (requires root, use for quick link stress)
ping -f -c 10000 192.168.1.1
```

---

## Throughput Testing with iperf3

### Server Setup (remote system)
```bash
iperf3 -s -p 5201
```

### Client Commands

```bash
# TCP throughput (1 stream, 30 seconds)
iperf3 -c <server_ip> -t 30 -p 5201

# TCP throughput (multiple streams for higher utilization)
iperf3 -c <server_ip> -t 30 -P 4 -p 5201

# UDP throughput (target 900Mbps for 1GbE)
iperf3 -c <server_ip> -t 30 -u -b 900M -p 5201

# Bidirectional test
iperf3 -c <server_ip> -t 30 --bidir -p 5201

# 2.5GbE target throughput (I226)
iperf3 -c <server_ip> -t 30 -P 4 -b 2400M -p 5201
```

### Expected Throughput

| Controller | Protocol | Expected |
|------------|----------|----------|
| I219 | TCP (single stream) | ~940 Mbps |
| I219 | UDP | ~950 Mbps |
| I226 / I225 | TCP (multi-stream) | ~2300–2400 Mbps |

---

## Loopback Testing

### MAC Loopback (no cable required)

Forces TX data to loop back internally in the MAC. Useful for data path validation without external hardware.

```python
# Enable MAC loopback via RCTL register (offset 0x0100)
# Bit 6 = LBM[1:0] = 01 = MAC Loopback
rctl = sv.mem.read(base + 0x0100, 4)
rctl |= (1 << 6)     # Set LBM bit 0
rctl &= ~(1 << 7)    # Clear LBM bit 1
sv.mem.write(base + 0x0100, 4, rctl)
```

### PHY Loopback (full SGMII path)

Loops at the PHY level — exercises the full SGMII path.

```bash
# Linux — enable PHY loopback via ethtool
ethtool -t eth0     # Runs built-in self-test including loopback

# Or manual PHY loopback
ethtool -s eth0 loopback phy
```

### External Loopback

Use an RJ-45 loopback plug (pins 1-3, 2-6 connected). Good for cable and switch-independent tests.

---

## Hardware Offload Validation

### Checksum Offload

**Windows:**
```powershell
# Check offload state
Get-NetAdapterChecksumOffload -Name "Ethernet"

# Enable/Disable
Set-NetAdapterChecksumOffload -Name "Ethernet" -IpIPv4 Enabled
Set-NetAdapterChecksumOffload -Name "Ethernet" -TcpIPv4 Enabled
```

**Linux:**
```bash
# Check current offload settings
ethtool -k eth0 | grep checksum

# Enable TX checksum offload
ethtool -K eth0 tx-checksum-ip-generic on

# Disable for testing
ethtool -K eth0 tx on
ethtool -K eth0 rx on
```

### TSO (TCP Segmentation Offload)

**Linux:**
```bash
# Check TSO state
ethtool -k eth0 | grep segmentation

# Enable/disable
ethtool -K eth0 tso on
ethtool -K eth0 tso off
```

**Windows:**
```powershell
Get-NetAdapterLso -Name "Ethernet"
Set-NetAdapterLso -Name "Ethernet" -IPv4Enabled $true
```

### LRO / RSC (Large Receive Offload / Receive Segment Coalescing)

**Linux (LRO):**
```bash
ethtool -k eth0 | grep large-receive
ethtool -K eth0 lro on
```

**Windows (RSC):**
```powershell
Get-NetAdapterRsc -Name "Ethernet"
Set-NetAdapterRsc -Name "Ethernet" -IPv4Enabled $true
```

---

## RSS (Receive Side Scaling) / Multi-Queue

### Verify RSS Configuration

**Windows:**
```powershell
Get-NetAdapterRss -Name "Ethernet"
# Check: NumberOfReceiveQueues should match CPU count (up to hardware limit)
# I219 typically supports up to 2 queues
# I226 supports more queues
```

**Linux:**
```bash
# Check number of queues
ethtool -l eth0

# Set number of queues
ethtool -L eth0 combined 4

# Check RSS hash key and indirection table
ethtool -x eth0
```

---

## Interrupt Coalescing

Reduces CPU overhead by batching interrupts. Default values may need tuning for low-latency vs. throughput tradeoff.

**Linux:**
```bash
# Check current coalescing settings
ethtool -c eth0

# Set adaptive coalescing (recommended)
ethtool -C eth0 adaptive-rx on adaptive-tx on

# Set fixed values for testing
ethtool -C eth0 rx-usecs 50 tx-usecs 50
```

**Windows:**
```powershell
# Check interrupt moderation
Get-NetAdapterAdvancedProperty -Name "Ethernet" -DisplayName "Interrupt Moderation"
Set-NetAdapterAdvancedProperty -Name "Ethernet" -DisplayName "Interrupt Moderation" -DisplayValue "Enabled"
```

---

## Traffic Test Validation Checklist

| Test | Tool | Pass Criteria |
|------|------|---------------|
| Basic connectivity | ping | 0% packet loss, <1ms latency (LAN) |
| TCP throughput | iperf3 | >940 Mbps (I219), >2300 Mbps (I226) |
| UDP throughput | iperf3 | <0.1% loss at 900Mbps (I219) |
| Checksum offload | ethtool | No CHECKSUM_BAD errors in `ip -s link` |
| TSO | iperf3 + wireshark | MSS >1500 bytes seen on wire |
| MAC loopback | ethtool -t | PASS on all self-test items |
| Jumbo frames (9KB MTU) | ping -s 8972 | No fragmentation errors |

---

## Common Traffic Issues

| Symptom | Likely Cause | Debug |
|---------|-------------|-------|
| High packet loss at >100Mbps | Checksum offload issue, ring buffer full | Check `ethtool -S eth0 | grep drop`; increase ring size |
| Low TCP throughput despite fast link | TSO off or flow control mismatch | Check offloads; check switch flow control |
| UDP loss at high rates | TX ring exhaustion | Increase TX ring: `ethtool -G eth0 tx 4096` |
| Latency spikes | Interrupt coalescing too aggressive | Reduce `rx-usecs` or enable adaptive mode |
| CRC errors | Cable issue, duplex mismatch | Check `ethtool -S eth0 | grep crc`; inspect cable |
| TX hangs | TX descriptor ring stuck | Check driver error log; may need reset |

---

## NGA Traffic Test Suites

GbE traffic tests in NGA typically cover:
- `GbE_Throughput_TCP_*` — TCP throughput at various speeds
- `GbE_Throughput_UDP_*` — UDP throughput and loss
- `GbE_Loopback_*` — Loopback self-test variants
- `GbE_Offload_*` — Hardware offload enable/disable tests
- `GbE_Jumbo_*` — Jumbo frame (9KB MTU) tests

To query NGA results: `/skill nga/results`
