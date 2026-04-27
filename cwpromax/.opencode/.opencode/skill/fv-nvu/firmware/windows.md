# NVU Firmware — Windows-Specific Notes

> **Status**: PLACEHOLDER — awaiting NVU SwAS (Software Architecture Specification) release
> **Last Updated**: 2026-03-28
> **Owner**: William Willy Chin ()

## Overview

This file will contain **Windows-specific** details for NVU firmware loading and secure boot.

The NVU HAS v1.0 (Section 21) defers all driver details to external specifications:
- NVU FAS (Functional Architecture Specification)
- NVU SwAS (Software Architecture Specification)  
- BIOS Programming Guide

Until those documents are available, OS-specific behavior is not yet documented.

## Pending Content

<!-- TODO: Populate when NVU SwAS is released -->

### Windows Driver
- Driver name: TBD
- Device node / path: TBD
- INF/sys files (Windows): TBD

### Windows-Specific Behavior
- Init sequence differences: TBD
- Power management hooks: TBD
- Error handling: TBD
- Known workarounds: TBD

### Windows Debug Tools
- Trace capture: TBD
- Register dump utilities: TBD
- Diagnostic commands: TBD

## Cross-References

- Parent: [fv-nvu/firmware](SKILL.md)
- Peer: [linux.md](linux.md)
- Agent definition: [FV-NVU](../../../agent/FV/FV-NVU.md)
