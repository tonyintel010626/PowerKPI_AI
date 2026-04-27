# Audio Test Gap Analysis
<!-- owner: huiyingt | platform: NVL, PTL, MTL, LNL, ARL, WCL, TTL, RZL | os: Windows 11 only | last updated: 2026-04-06 -->
<!-- companion to: audio_test_coverage_matrix.md, audio_known_issues.md -->

> Identifies missing or insufficient test coverage in the NVL audio validation suite.
> Each gap entry has a severity, owning domain, and recommended action.
> See `audio_test_coverage_matrix.md` for the full coverage matrix.

---

## Gap Severity Legend

| Severity | Meaning |
|----------|---------|
| **Sev1** | Showstopper — gate-blocking gap; must be closed before PV |
| **Sev2** | High — significant coverage hole; should be closed pre-QS |
| **Sev3** | Medium — notable gap; address post-QS or next cycle |
| **Sev4** | Low — minor gap; nice-to-have |

---

## Section 1 — HDA Domain Gaps

| Gap ID | Description | Severity | Status | Action |
|--------|-------------|----------|--------|--------|
| GAP-HDA-001 | No test for CORB/RIRB DMA stall recovery (BUG-001 scenario) | Sev2 | Open | Add `hda_corb_rirb_recovery.py` that injects D3→D0 cycle and verifies DMA re-init |
| GAP-HDA-002 | No test for unsolicited response (jack hotplug under load) | Sev2 | Open | Extend `jack_detect_headset.py` with simultaneous stream playback |
| GAP-HDA-003 | No test for HDA stream descriptor error injection | Sev3 | Open | Add `hda_stream_error.py` using BIST/error inject path |
| GAP-HDA-004 | No multi-codec verb ordering test | Sev3 | Open | Add `hda_verb_order.py` for systems with secondary PCH codec |
| GAP-HDA-005 | No test for GCAP capability register correctness | Sev4 | Open | Add assertion in `audio_enum_checkout.py` for ISS/OSS/BSS counts |

---

## Section 2 — SoundWire Domain Gaps

| Gap ID | Description | Severity | Status | Action |
|--------|-------------|----------|--------|--------|
| GAP-SDW-001 | CLK_STOP recovery after abrupt power loss not tested (BUG-002 scenario) | Sev2 | Open | Add `sdw_clk_stop_recovery.py` — force CLK_STOP mid-stream + recover |
| GAP-SDW-002 | No test for Segment 2 / Segment 3 enumeration (NVL PCD-H only) | Sev2 | Open | Add `sdw_multi_segment.py` for 4-segment NVL PCD-H configs |
| GAP-SDW-003 | No stress test for SoundWire bandwidth saturation | Sev3 | Open | Add concurrent SDW capture + playback on all active segments |
| GAP-SDW-004 | No test for DisCo manifest validation | Sev3 | Open | Add `sdw_disco_verify.py` — read and validate slave capability registers |
| GAP-SDW-005 | No parity error injection test | Sev4 | Open | Add `sdw_parity_inject.py` using segment loopback |

---

## Section 3 — DSP Domain Gaps

| Gap ID | Description | Severity | Status | Action |
|--------|-------------|----------|--------|--------|
| GAP-DSP-001 | No test for DSP wakeup after clock gate (BUG-003 scenario) | Sev2 | Open | Add `dsp_clkgate_wakeup.py` — force core clock gate + wake via IPC |
| GAP-DSP-002 | No test for HP-SRAM retention after D0i3 | Sev2 | Open | Add `dsp_d0i3_sram_retention.py` — load pattern, D0i3, wake, verify |
| GAP-DSP-003 | No test for DSP FW update (load new version without reboot) | Sev2 | Open | Add `dsp_fw_hot_update.py` — unload + reload via intelaud.sys IOCTL |
| GAP-DSP-004 | No IPC timeout stress test | Sev3 | Open | Add `dsp_ipc_stress.py` — rapid-fire IPC with various message types |
| GAP-DSP-005 | No test for all DSP pipeline topologies | Sev3 | Open | Add manifest for each topology type: playback, capture, loopback, WoV |
| GAP-DSP-006 | NVL PCH-S DSP coverage is partial (2 cores vs 4 for PCD-H) | Sev3 | Open | Validate `dsp_pipeline_create.py` on PCH-S and document core count delta |

---

## Section 4 — DMIC Domain Gaps

| Gap ID | Description | Severity | Status | Action |
|--------|-------------|----------|--------|--------|
| GAP-DMIC-001 | No test for PDM2 (NVL PCD-H third PDM port) | Sev2 | Open | Add `dmic_capture_pdm2.py` — NVL PCD-H only test |
| GAP-DMIC-002 | No audio quality metric (SNR / THD+N) test | Sev2 | Open | Add `dmic_quality_snr.py` with signal generator + loopback analysis |
| GAP-DMIC-003 | No test for privacy mode LED indicator GPIO | Sev3 | Open | Add `dmic_privacy_led.py` — toggle privacy, verify GPIO state via TTK3 |
| GAP-DMIC-004 | No multi-rate test (16 kHz, 32 kHz, 48 kHz simultaneous) | Sev3 | Open | Add `dmic_multi_rate.py` — requires DSP SRC pipeline |

---

## Section 5 — SSP / BT Offload Domain Gaps

| Gap ID | Description | Severity | Status | Action |
|--------|-------------|----------|--------|--------|
| GAP-SSP-001 | No test for BCLK recovery after power gate (HSDES-003 scenario) | Sev2 | Open | Add `ssp_bclk_pg_recovery.py` — power gate SSP then verify BCLK re-locks |
| GAP-SSP-002 | No test for eSCO (A2DP not just SCO) path | Sev3 | Open | Add `ssp_bt_esoo.py` using BT stack loopback |
| GAP-SSP-003 | No BT HFP offload power measurement | Sev3 | Open | Add power measurement step to `ssp_bt_sco.py` |

---

## Section 6 — UAOL Domain Gaps

| Gap ID | Description | Severity | Status | Action |
|--------|-------------|----------|--------|--------|
| GAP-UAOL-001 | No stress test for USB audio isochronous continuity | Sev2 | Open | Add `uaol_iso_stress.py` — 100 cycles of USB audio start/stop |
| GAP-UAOL-002 | NVL PCH-S UAOL validation not started | Sev2 | Open | Confirm UAOL hardware presence on PCH-S; add coverage or mark N/A |
| GAP-UAOL-003 | No test for UAOL + S0ix interaction | Sev2 | Open | Add `uaol_s0ix_coexist.py` — UAOL stream active during S0ix attempt |
| GAP-UAOL-004 | No behind-hub USB audio test | Sev3 | Open | Add `uaol_behind_hub.py` — USB audio dongle behind USB hub |

---

## Section 7 — Power Management Domain Gaps

| Gap ID | Description | Severity | Status | Action |
|--------|-------------|----------|--------|--------|
| GAP-PM-001 | S0ix LTR tuning test missing (HSDES-001 scenario root cause) | Sev1 | Closed | Addressed by `pm_ltr_audio_tune.py` — reads/sets ACE LTR via `SvNnDef.NN_LTR_C2P2_IP_ACE`, verifies S0ix entry with `print_LTRs` doctor script. See `power/SKILL.md` §S0ix LTR Validation. |
| GAP-PM-002 | No test for D3cold re-enumeration | Sev2 | Open | Add `pm_d3cold_reenum.py` — power remove + restore, verify full re-init |
| GAP-PM-003 | No audio-during-suspend test (WoV + DMIC in S0ix) | Sev2 | Open | Covered by `wov_keyword_detect.py` only; need explicit S0ix residency assert |
| GAP-PM-004 | No PROCHOT assertion impact test on audio | Sev3 | Open | Add `pm_prochot_audio.py` — assert PROCHOT via TTK3, verify audio continues |
| GAP-PM-005 | No Modern Standby entry/exit stress (100 cycles) | Sev3 | Open | Extend `pm_s0ix_residency.py` with cycle stress mode |

---

## Section 8 — WoV Domain Gaps

| Gap ID | Description | Severity | Status | Action |
|--------|-------------|----------|--------|--------|
| GAP-WOV-001 | No negative test (non-keyword phrase should NOT trigger) | Sev2 | Open | Add `wov_false_reject.py` — play 20 non-keyword phrases, assert no trigger |
| GAP-WOV-002 | No WoV + concurrent playback interaction test | Sev3 | Open | Add `wov_with_playback.py` — music playing while WoV listens |
| GAP-WOV-003 | No CRO frequency accuracy test | Sev3 | Open | Add `wov_cro_freq.py` — measure CRO drift, assert < 1% |

---

## Section 9 — Jack Detect Domain Gaps

| Gap ID | Description | Severity | Status | Action |
|--------|-------------|----------|--------|--------|
| GAP-JACK-001 | DP audio hotplug test missing (HSDES-004 scenario) | Sev2 | Open | Add `jack_detect_dp3_hotplug.py` — DP connect/disconnect at D3, verify ELD |
| GAP-JACK-002 | No jack detect under S0ix test | Sev3 | Open | Add `jack_detect_s0ix.py` — plug headset from S0ix, verify wake + detect |
| GAP-JACK-003 | No multi-device jack detect stress (10 plug cycles) | Sev3 | Open | Extend `jack_detect_headset.py` with 10-cycle loop |

---

## Section 10 — Config / Platform Gaps

| Gap ID | Description | Severity | Status | Action |
|--------|-------------|----------|--------|--------|
| GAP-CFG-001 | No test for all BIOS knob combinations (audit) | Sev3 | Open | Add `bios_knob_audio_matrix.py` — sweep key knob combos |
| GAP-CFG-002 | PTL-specific DID not yet validated | Sev2 | Open | Update `audio_enum_checkout.py` with PTL DID when available |
| GAP-CFG-003 | No regression test after BIOS version change | Sev2 | Open | Add pre/post BIOS update delta test to NGA Default Flow |
| GAP-CFG-004 | TTL platform not yet brought up for audio validation | Sev2 | Open | Bring up TTL audio: verify ACE version (3.0 vs 4.0 fuse), validate DID, run enum checkout |
| GAP-CFG-005 | RZL platform not yet brought up for audio validation | Sev2 | Open | Bring up RZL audio: verify DID, run full test suite, validate 4 die variants (H/S/M/W) |
| GAP-CFG-006 | WCL platform test execution not started | Sev2 | Open | Port PTL test suite to WCL, validate DID, confirm ACE 3.x compatibility |
| GAP-CFG-007 | ARL platform test execution not started | Sev3 | Open | Port MTL test suite to ARL, validate DID, confirm ACE 1.5 compatibility |

---

## Gap Summary

| Domain | Total Gaps | Sev1 | Sev2 | Sev3 | Sev4 |
|--------|-----------|------|------|------|------|
| HDA | 5 | 0 | 2 | 2 | 1 |
| SoundWire | 5 | 0 | 2 | 2 | 1 |
| DSP | 6 | 0 | 3 | 3 | 0 |
| DMIC | 4 | 0 | 2 | 2 | 0 |
| SSP/BT | 3 | 0 | 1 | 2 | 0 |
| UAOL | 4 | 0 | 3 | 1 | 0 |
| PM | 5 | 1 | 2 | 2 | 0 |
| WoV | 3 | 0 | 1 | 2 | 0 |
| Jack Detect | 3 | 0 | 1 | 2 | 0 |
| Config | 7 | 0 | 5 | 2 | 0 |
| **Total** | **45** | **1** | **22** | **20** | **2** |

> **Sev1 priority**: GAP-PM-001 (LTR tuning) must be resolved before PV exit.
> The 22 Sev2 gaps should be triaged with the validation lead for the current PV cycle.
> 4 new Sev2 gaps (GAP-CFG-004 through GAP-CFG-007) track TTL/RZL/WCL/ARL platform bring-up.
