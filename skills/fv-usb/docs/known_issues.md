# FV-USB — Known Issues & RTL Bugs

<!-- owner: kvejaya -->

> Last Updated: 2026-04-02 (HSDES sighting research additions: HCIVERSION wrong value, U1 entry phy_status fail, PM USBCMD.RS clkreq; classification expansions)
> **Before triaging any USB failure**, scan this file for a matching entry. If found, apply the documented workaround and file a duplicate HSDES sighting referencing the original.

---

## Issue Table

| HSDES ID    | Platform(s) | Component     | Severity | Classification | Summary                                                       | Workaround                                                              | Status       |
|-------------|-------------|---------------|----------|----------------|---------------------------------------------------------------|-------------------------------------------------------------------------|--------------|
| 16029865294 | PTL         | UAOL / ACE3   | High     | FW / RTL       | USB audio recording stuck after ~30s–3min (Astro40 headset). Device FW enters error state on missed isochronous poll. ACE3 Feedback FIFO (~1ms) too small to absorb pNDE scheduling jitter. | (1) Disable UAOL via registry. (2) Update headset FW if vendor provides update. (3) Test with NVL/ACE4 — larger FIFO absorbs the jitter. | Open         |
| 18043001729 | NVL         | UAOL / ACE4   | Medium   | FW             | ACE4 Feedback FIFO sizing adjustment required. Initial silicon had suboptimal FIFO configuration leading to intermittent isochronous gaps. | Update to BIOS/ACE FW version specified in current BKC. Use `onebkc` skill to confirm correct FW version. | Resolved (BKC) |
| —           | MTL         | UAOL          | High     | RTL            | UAOL behind USB hub not supported. Isochronous offload fails when audio device is connected through a USB hub. | Do NOT use UAOL behind hub on MTL. Upgrade to PTL+ where this is fixed. Feature fixed from PTL Standalone USB onwards. | Fixed (PTL+) |
| —           | Generic     | xHCI / LTSSM  | Medium   | RTL / INTEG    | Compliance Mode trap: PORTSC.PLS stuck at 10 (Compliance Mode) after device connect. Link cannot exit compliance mode without warm reset. | (1) Replace cable with certified SuperSpeed cable. (2) Check board trace SI. (3) Warm port reset (PORTSC.WPR=1). (4) If persistent across cables/ports, file HSDES sighting — may be RTL/board SI issue. | Per-platform |
| —           | Generic     | xHCI / PM     | High     | CONFIG         | USB preventing S0ix entry: SLP_S0# not asserting with USB identified as blocker. xHCI not entering D3, or device not entering U3/suspend. | (1) Run `slp_s0.py` to identify specific blocker port. (2) Check RTD3 policy (BIOS knob). (3) Run `LTR_checker.py` — aggressive LTR may prevent deep C-state. (4) Verify all ports show PLS=U3 before S0ix. Delegate to **FV-PM-SOUTH** for platform-level power gating issues. | Per-platform |
| —           | Generic     | xHCI          | Medium   | DRIVER         | USBSTS.HSE=1 (Host System Error) after driver init. Usually caused by invalid MMIO access or DMA address error in TRB. | (1) Check DCBAAP 64-byte alignment. (2) Check PCIe AER for xHCI BDF. (3) Verify BAR0 is correctly allocated (not conflicting). (4) Issue HCRST and re-initialize. | Per-platform |
| —           | Generic     | Enumeration   | Low      | CONFIG         | Device lost after S3 resume: CCS=0 post-resume for device that was connected pre-S3. | (1) Check PORTSC.PP (port power restored?). (2) Check PORTSC.CCS and PED after resume. (3) Verify USBCMD.Run after S3 resume path. (4) Collect BIOS POST log via UART-MONITOR. | Per-platform |
| 15013449180 | PTL / NVL (PCH-H + PCH-S) | xHCI / Isochronous | High | RTL | USB3 camera + bulk traffic triggers missed service events for isochronous/transaction errors → device re-enumeration. Affects USB3 camera streams when concurrent bulk traffic is active. | SW retry logic; FW update from OEM. Avoid concurrent bulk + isochronous if device re-enumerates. | Open |
| 15013245412 | PTL / NVL (PCH-H + PCH-S) | xHCI / RTD3   | High     | RTL            | HC Reset during bulk traffic on Gen2 device behind Gen1 Hub in RTD3 state causes link instability. | FW/driver update for hub state transitions; avoid Gen2 device behind Gen1 hub in RTD3 until updated BKC. | Open |
| 14020114105 | PTL / NVL   | USB-C / DP    | Medium   | INTEG          | No TC0b entries with DisplayPort on second connect (even at EFI) and after disconnect. Affects DP Alt-Mode bring-up validation. | Disconnect/reconnect cycle; re-test at EFI prompt. File sighting if persistent across platforms. | Open |
| 14018741394 | PTL / NVL   | USB Compliance | Medium  | RTL            | Chapter 7 SS/SSP TD 7.06 Data Payload Framing Robustness Test fails — subsequent requests do not issue GetDescriptor bRequest 0x6. | Skip TD 7.06 in automated compliance run; document as known PTL/NVL RTL issue in compliance report. | Open |
| 1509699522  | PTL / NVL   | xDCI / PHY    | Medium   | RTL            | Cannot provide `xdci_pipe_clk_gen1` at 125 MHz when configuring Gen2 freq in xHCI port. Affects device-mode (xDCI) operation alongside xHCI Gen2. | Use Gen1 frequency config when xDCI is active. Avoid simultaneous xHCI Gen2 + xDCI. | Open |
| 1509308928  | PTL / NVL   | xHCI / PHY    | Medium   | RTL            | Wrong `set_port_attribute` at IP top boundary + redundant isolation on power switch ack path. May manifest as port attribute mismatch or power-sequencing delay. | Check PORTSC power attribute bits; account for extra ack latency in power sequencing tests. | Open |
| 1509209950  | PTL / NVL   | xHCI / PHY    | Medium   | RTL            | xHC makes back-to-back powerdown transitions without waiting for `phystatus` assertion from first powerdown. Can cause PHY state corruption. | Increase powerdown-to-powerdown spacing in test; if persistent, escalate via HSDES sighting. | Open |
| 22018119897 | PTL / NVL   | UAOL          | Medium   | RTL            | VISA signals/registers needed to indicate UAOL audio glitch events not fully implemented. Makes glitch root-cause diagnosis difficult without hardware trace. | Use ACE FW trace logs + UAOL debug registers to correlate glitch timing. File sighting if VISA signals absent in Si. | Open |
| 1304166922  | Pre-silicon (FPGA/SLE) | xHCI | Medium | RTL | HCIVERSION register reads `0x0100` instead of required `0x0110`. xHCI 1.1 is the first revision to support SuperSpeedPlus (Gen2). OS driver gates Gen2 support on HCIVERSION >= 0x0110 — wrong value silently blocks all Gen2 enumeration at the driver level. | Verify HCIVERSION = 0x0110 on new platform bringup. Read via PythonSV: `sv.socket0.uncore.usb.xhci.hciversion`. If wrong, file RTL sighting. | Open (pre-Si only) |
| —           | Generic     | xHCI / PM     | Medium   | CONFIG         | PM clock request stuck high (USB3_PRIM_CLKREQ=1 or ux_ibbs_prim_clkreq=1) after applying USB PM register settings. Prevents Main PLL shutdown or ROSC gating. Root cause: USBCMD.RS (Run/Stop bit) not cleared after PORTSC.PP=0. Both bits must be cleared for clkreq to de-assert. | Clear USBCMD.RS = 0 **after** clearing PORTSC.PP for all ports. Verify with P2SB/PythonSV register read-back. See debug_playbooks.md Playbook 6. | Per-platform |
| —           | Generic     | xHCI / PHY    | Medium   | RTL            | U1 entry failure: link training stalls, LTSSM stuck at Rx.Detect (LTSSM=5, PORTSC=0x611). Root cause: PHY does not assert `phystatus` after first U1 powerdown. xHCI waits for `phystatus` before completing U1 transition — timeout causes LTSSM rollback to Rx.Detect. | Check PORTSC for PLS=5 (Rx.Detect) immediately after U1 entry attempt. Increase powerdown-to-powerdown spacing (see HSDES 1509209950). Escalate if persistent on post-silicon. | Per-platform |

---

## Classification Definitions

| Prefix | Meaning |
|--------|---------|
| **RTL** | Silicon/RTL bug — requires ECO or silicon fix |
| **FW** | Firmware issue (ACE FW, BIOS, device FW) — fix via FW update |
| **DRIVER** | OS driver bug — fix via driver update |
| **CONFIG** | Misconfiguration (BIOS knobs, registry, test setup) — fix via config change |
| **INTEG** | Integration issue (cross-IP, board-level, strap) — fix via platform integration |
| **HSDES** | Tracked in HSDES with active sighting |

## How to Add a New Entry

When you discover a new confirmed RTL bug or HSDES sighting:

1. Add a row to the table above
2. Include the HSDES ID if available (or `—` if not yet filed)
3. Set **Classification** to one of: `RTL`, `FW`, `DRIVER`, `CONFIG`, `INTEG`, or `HSDES` (can combine: `FW / RTL`)
4. Document the exact platform, component, severity, symptom, and workaround
5. Set status to `Open`, `Resolved (BKC)`, `Fixed (platform+)`, or `Per-platform`
6. Update `Last Updated` date at the top of this file
7. Run `self-improve` skill to propagate the finding to the agent and sub-skills

## Severity Definitions

| Severity | Definition |
|----------|------------|
| **High** | Test blocking or data integrity failure. Requires immediate workaround before proceeding. |
| **Medium** | Intermittent or device-specific failure. Workaround exists; may require additional triage. |
| **Low** | Edge case or cosmetic. Does not block primary test scenarios. |

## PTL / NVL Integration Notes (No HSDES — from Co-Design HAS)

These are integration constraints found in PTL/NVL HAS documents (not yet tracked in HSDES). They affect test setup and validation methodology.

| # | Platform | Topic | Detail | Action |
|---|----------|-------|--------|--------|
| 1 | NVL | **UAOL PSF Glitch Risk** | xHCI and ACE share PSF segment on NVPS SoC. If PSF is not kept alive during UAOL operation, audio glitch occurs. ACE FW must request PSF logical resource via `DfSPSREQ` register. | Verify `DfSPSREQ` is set in ACE FW before running UAOL audio tests on NVL. |
| 2 | PTL/NVL | **Low Power Debug / XTAL refclk** | Using XTAL as refclk breaks LP debug requirements. PMC must conditionally switch refclk. UAOL requires audio + xHCI on a common clock. DTS SW must override XTAL shutdown requirements before LP state entry. | Confirm PMC refclk switching is active before running UAOL + low-power combined tests. |
| 3 | PTL/NVL | **USB2DBC S0ix Interaction** | If USB2DBC connects before CSE boot stall: USB2 camera unavailable but S0ix debug works. If after: reverse. No validation of IMGPLL override for USB2DBC in S0ix debug mode. | Document USB2DBC connection timing relative to CSE boot in test setup notes. Do not rely on IMGPLL override in S0ix debug configurations. |
| 4 | PTL/NVL | **eUSB2 PHY / PGA Integration** | PCRs 14019161428, 14019160906, 14019160996 require careful integration of eUSB2 PHY and PGA with backward compatibility to USB2. Platform FW must support correct clocking and initialization sequences. | Validate eUSB2 PHY init sequence on PTL/NVL bring-up. Check FW version includes PCR fixes before running USB2 enumeration tests. |
| 5 | PTL/NVL | **USB3DbC Enablement Qualification** | PCR 14019220945: USB3DbC enablement must be qualified by both `USB3DbC_EN` and `Debug_enable` bits in the ECTRL register. Enabling only one bit is insufficient. | In USB3DbC test setup, verify both ECTRL bits are set. Add ECTRL register readback to debug bring-up checklist. |
| 6 | PTL/NVL | **PID / Strap Config for DBC** | PCRs 15013245854, 15013243196: New PID values and input strap configuration required for TCSS.XHCI.DBC and standalone XHCI.DBC. Wrong strap = DBC not enumerated. | Confirm strap configuration in platform BOM matches HAS-specified values before DBC validation. |

---

## Cross-Reference: Sub-Skill Coverage

| Issue Type | Sub-Skill with Detailed Triage |
|------------|-------------------------------|
| UAOL recording/playback stuck | `fv-usb/debug` → UAOL Failure Triage section |
| Compliance mode (PLS=10) | `fv-usb/debug` → Common Failure Signatures §1 |
| USBSTS.HSE=1 | `fv-usb/debug` → Common Failure Signatures §2 |
| Device lost after S3 | `fv-usb/debug` → Common Failure Signatures §3 |
| USB S0ix blocker | `fv-usb/power` → Common PM Failures table |
| ACE3 vs ACE4 FIFO | `fv-usb/debug` → ACE3 vs ACE4 Debug Considerations |
