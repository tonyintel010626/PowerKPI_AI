# FV-TCSS — Type-C Subsystem Functional Validation Skill

## Overview

This skill provides domain knowledge for Type-C Subsystem (TCSS) functional validation on Intel Client SoC platforms. TCSS encompasses USB4, USB3, Thunderbolt 4/3, I/O Manager (IOM), DisplayPort Alt Mode, PCIe tunneling, and DMA validation.

## Sub-Skills

Detailed domain knowledge is organized into specialized sub-skills:

| Sub-Skill | Description |
|-----------|-------------|
| **enumeration** | PCI enumeration, device discovery, BDF/BAR allocation, device tree validation |
| **usb4** | USB4 router configuration, tunneling protocols, link management |
| **thunderbolt** | Thunderbolt 4/3 authentication, link training, security, daisy-chaining |
| **iom** | I/O Manager configuration, mux control, orientation detection, port management |
| **displayport** | DisplayPort Alt Mode, link training, stream management, resolution support |
| **dma** | DMA engine architecture, data path management, tunneling performance |
| **power** | Power management validation — D-states, power gating, S0ix, wake-on-connect |
| **debug** | Failure triage workflows, HSDES sighting database, debug tools, known errata |

## Platform Support

| Platform | TCSS Generation | Key Features |
|----------|-----------------|--------------|
| MTL      | iTBT 1.0        | First USB4 integration |
| NVL      | iTBT 2.0        | Enhanced power management |
| TTL      | iTBT 2.x        | Latest generation |

## Usage

From the FV-TCSS agent, load sub-skills as needed:
```
skill("fv-tcss/enumeration")
skill("fv-tcss/usb4")
skill("fv-tcss/thunderbolt")
```

## Owner

- **Owner:** Ooi, Ling Wei (lingweio)
- **Email:** ling.wei.ooi@intel.com
- **Team:** Client Validation Engineering (CVE)
