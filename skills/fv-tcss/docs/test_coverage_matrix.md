# TCSS Test Coverage Matrix

## Overview

This document tracks test coverage across TCSS components and platforms.

## Test Categories

| Category | Description | Test Count | Coverage |
|----------|-------------|------------|----------|
| **Enumeration** | PCI enumeration, device discovery, BDF/BAR | TBD | TBD% |
| **USB4 Router** | Router config, tunneling, link management | TBD | TBD% |
| **Thunderbolt** | TBT authentication, link training, security | TBD | TBD% |
| **IOM** | I/O Manager config, mux control, orientation | TBD | TBD% |
| **DisplayPort** | DP Alt Mode, link training, stream mgmt | TBD | TBD% |
| **DMA** | DMA engine, data path, performance | TBD | TBD% |
| **Power** | D-states, power gating, S0ix, wake | TBD | TBD% |
| **Hot-Plug** | Connect/disconnect, cable orientation | TBD | TBD% |
| **Stress** | Long-duration, repeated cycles | TBD | TBD% |
| **Error** | Error detection, recovery, timeout | TBD | TBD% |
| **Interop** | Multi-vendor devices, OS compatibility | TBD | TBD% |
| **Performance** | Throughput, latency, bandwidth | TBD | TBD% |

## Platform Coverage Matrix

| Test Category | MTL | NVL | TTL | Notes |
|---------------|-----|-----|-----|-------|
| Enumeration | TBD | TBD | TBD | |
| USB4 Router | TBD | TBD | TBD | |
| Thunderbolt | TBD | TBD | TBD | |
| IOM | TBD | TBD | TBD | |
| DisplayPort | TBD | TBD | TBD | |
| DMA | TBD | TBD | TBD | |
| Power | TBD | TBD | TBD | |
| Hot-Plug | TBD | TBD | TBD | |
| Stress | TBD | TBD | TBD | |
| Error | TBD | TBD | TBD | |
| Interop | TBD | TBD | TBD | |
| Performance | TBD | TBD | TBD | |

**Legend:**
- ✅ Full coverage
- ⚠️ Partial coverage
- ❌ No coverage
- TBD To be determined

## Detailed Test List

### Enumeration Tests

| Test ID | Test Name | Description | Platforms | Status |
|---------|-----------|-------------|-----------|--------|
| TCSS_ENUM_001 | Basic PCI enumeration | Verify TCSS device enumerated | All | TBD |
| TCSS_ENUM_002 | Device ID verification | Check DID matches spec | All | TBD |
| TCSS_ENUM_003 | BAR allocation | Verify BAR0 allocated correctly | All | TBD |

> **TODO:** Expand test list as tests are developed.

### USB4 Router Tests

| Test ID | Test Name | Description | Platforms | Status |
|---------|-----------|-------------|-----------|--------|
| TCSS_USB4_001 | Router discovery | Verify router enumeration | All | TBD |
| TCSS_USB4_002 | Tunnel establishment | Test USB3 tunnel setup | All | TBD |
| TCSS_USB4_003 | Bandwidth allocation | Verify bandwidth negotiation | All | TBD |

> **TODO:** Expand test list as tests are developed.

### Thunderbolt Tests

| Test ID | Test Name | Description | Platforms | Status |
|---------|-----------|-------------|-----------|--------|
| TCSS_TBT_001 | Authentication SL1 | Test user authorization | All | TBD |
| TCSS_TBT_002 | Authentication SL2 | Test secure connect | All | TBD |
| TCSS_TBT_003 | Link training Gen 3 | Test 40Gbps link | All | TBD |
| TCSS_TBT_004 | Daisy chain 2 devices | Test 2-device chain | All | TBD |

> **TODO:** Expand test list as tests are developed.

### IOM Tests

| Test ID | Test Name | Description | Platforms | Status |
|---------|-----------|-------------|-----------|--------|
| TCSS_IOM_001 | Port mode selection | Test USB/DP/TBT mode | All | TBD |
| TCSS_IOM_002 | Mux state transition | Test mux switching | All | TBD |
| TCSS_IOM_003 | Orientation detection | Test normal/flipped | All | TBD |

> **TODO:** Expand test list as tests are developed.

### DisplayPort Tests

| Test ID | Test Name | Description | Platforms | Status |
|---------|-----------|-------------|-----------|--------|
| TCSS_DP_001 | DP Alt Mode 2-lane | Test 4K @60Hz | All | TBD |
| TCSS_DP_002 | DP Alt Mode 4-lane | Test 8K @30Hz | All | TBD |
| TCSS_DP_003 | HPD detection | Test hot plug detect | All | TBD |
| TCSS_DP_004 | EDID read | Test display capabilities read | All | TBD |

> **TODO:** Expand test list as tests are developed.

### DMA Tests

| Test ID | Test Name | Description | Platforms | Status |
|---------|-----------|-------------|-----------|--------|
| TCSS_DMA_001 | Single descriptor | Test basic DMA transfer | All | TBD |
| TCSS_DMA_002 | Descriptor chaining | Test multi-descriptor transfer | All | TBD |
| TCSS_DMA_003 | DMA throughput | Measure transfer rate | All | TBD |

> **TODO:** Expand test list as tests are developed.

### Power Management Tests

| Test ID | Test Name | Description | Platforms | Status |
|---------|-----------|-------------|-----------|--------|
| TCSS_PM_001 | D0 to D3hot | Test D-state transition | All | TBD |
| TCSS_PM_002 | D3hot to D0 | Test resume from D3 | All | TBD |
| TCSS_PM_003 | S0ix entry with TCSS idle | Test S0ix integration | All | TBD |
| TCSS_PM_004 | Wake-on-connect | Test wake from cable plug | All | TBD |
| TCSS_PM_005 | RTD3 entry/exit | Test runtime PM | All | TBD |

> **TODO:** Expand test list as tests are developed.

### Hot-Plug Tests

| Test ID | Test Name | Description | Platforms | Status |
|---------|-----------|-------------|-----------|--------|
| TCSS_HP_001 | Basic hot-plug | Connect/disconnect device | All | TBD |
| TCSS_HP_002 | Orientation flip | Test both orientations | All | TBD |
| TCSS_HP_003 | Rapid plug/unplug | Stress test hot-plug | All | TBD |

> **TODO:** Expand test list as tests are developed.

### Stress Tests

| Test ID | Test Name | Description | Platforms | Status |
|---------|-----------|-------------|-----------|--------|
| TCSS_STRESS_001 | 1000 hot-plug cycles | Stress test connect/disconnect | All | TBD |
| TCSS_STRESS_002 | 24-hour data transfer | Long-duration transfer | All | TBD |
| TCSS_STRESS_003 | PM cycling | Repeated D0/D3 transitions | All | TBD |

> **TODO:** Expand test list as tests are developed.

## Coverage Goals

| Milestone | Target Coverage | Target Date | Status |
|-----------|----------------|-------------|--------|
| M1 - Basic functionality | 50% | TBD | TBD |
| M2 - Full feature set | 80% | TBD | TBD |
| M3 - Stress & edge cases | 95% | TBD | TBD |

## Gap Analysis

> **TODO:** Track coverage gaps and plan test development.

| Gap | Priority | Plan | Owner |
|-----|----------|------|-------|
| TBD | TBD | TBD | TBD |

## Update Log

| Date | Author | Changes |
|------|--------|---------|
| 2026-03-30 | AI-assist | Initial template created |

---

## Owner

- **Owner:** Ooi, Ling Wei (lingweio)
- **Email:** ling.wei.ooi@intel.com
