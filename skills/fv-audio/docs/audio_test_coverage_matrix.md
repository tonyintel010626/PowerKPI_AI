# Audio Test Coverage Matrix
<!-- owner: huiyingt | platform: NVL, PTL, MTL, LNL, ARL, WCL, TTL, RZL | last updated: 2026-04-06 -->
<!-- companion to: ../SKILL.md, audio_test_gap_analysis.md -->

> Coverage matrix mapping NGA test scripts/suites to IP domains, OS platforms, and
> validation categories. Use `audio_test_gap_analysis.md` for gap action items.

---

## 1. Test Suite → IP Domain Coverage

### Legend
- ✅ **Covered** — test fully exercises this domain
- 🔶 **Partial** — test touches domain but not exhaustively
- ❌ **Not covered** — domain not exercised by this test
- 🚫 **N/A** — domain not present on this platform

| Test Script | HDA | SDW | DSP | DMIC | SSP/BT | UAOL | PM/S0ix | Interrupt | Config |
|-------------|-----|-----|-----|------|--------|------|---------|-----------|--------|
| audio_enum_checkout.py | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| hda_codec_discovery.py | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔶 | 🔶 |
| hda_stream_playback.py | ✅ | ❌ | 🔶 | ❌ | ❌ | ❌ | 🔶 | ✅ | ❌ |
| hda_stream_capture.py | ✅ | ❌ | 🔶 | ❌ | ❌ | ❌ | 🔶 | ✅ | ❌ |
| sdw_enum_test.py | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔶 | 🔶 |
| sdw_stream_playback.py | ❌ | ✅ | 🔶 | ❌ | ❌ | ❌ | 🔶 | ✅ | ❌ |
| sdw_stream_capture.py | ❌ | ✅ | 🔶 | ❌ | ❌ | ❌ | 🔶 | ✅ | ❌ |
| dsp_fw_load.py | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | 🔶 | ✅ | ❌ |
| dsp_ipc_basic.py | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 🔶 | ❌ |
| dsp_pipeline_create.py | ❌ | 🔶 | ✅ | 🔶 | ❌ | ❌ | ❌ | ✅ | ❌ |
| dmic_capture_pdm0.py | ❌ | ❌ | 🔶 | ✅ | ❌ | ❌ | ❌ | 🔶 | ❌ |
| dmic_capture_pdm1.py | ❌ | ❌ | 🔶 | ✅ | ❌ | ❌ | ❌ | 🔶 | ❌ |
| dmic_capture_all.py | ❌ | ❌ | 🔶 | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| dmic_privacy_mode.py | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| ssp_bt_sco.py | ❌ | ❌ | 🔶 | ❌ | ✅ | ❌ | 🔶 | 🔶 | ❌ |
| ssp_bclk_config.py | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| uaol_basic_playback.py | ❌ | ❌ | 🔶 | ❌ | ❌ | ✅ | ❌ | 🔶 | ❌ |
| uaol_usb_audio.py | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ |
| pm_d3_entry_exit.py | 🔶 | 🔶 | ✅ | 🔶 | 🔶 | 🔶 | ✅ | ❌ | ❌ |
| pm_s0ix_residency.py | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| pm_ltr_validation.py | ❌ | ❌ | 🔶 | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| jack_detect_headset.py | ✅ | 🔶 | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| jack_detect_hdmi.py | 🔶 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| wov_keyword_detect.py | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| irq_routing_check.py | 🔶 | 🔶 | 🔶 | 🔶 | 🔶 | 🔶 | ❌ | ✅ | ❌ |
| bios_knob_audio.py | ❌ | ❌ | 🔶 | ❌ | ❌ | ❌ | 🔶 | ❌ | ✅ |

---

## 2. Platform Coverage per Test

| Test Script | NVL PCD-H | NVL PCH-S | PTL | MTL | LNL | ARL | WCL | TTL | RZL |
|-------------|-----------|-----------|-----|-----|-----|-----|-----|-----|-----|
| audio_enum_checkout.py | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| hda_codec_discovery.py | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| hda_stream_playback.py | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| sdw_enum_test.py | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| sdw_stream_playback.py | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| dsp_fw_load.py | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| dmic_capture_pdm0.py | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| dmic_capture_all.py | ✅ | 🔶 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| ssp_bt_sco.py | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| uaol_basic_playback.py | ✅ | ✅ | ✅ | 🔶 | 🔶 | ❌ | ❌ | ❌ | ❌ |
| pm_s0ix_residency.py | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| wov_keyword_detect.py | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| jack_detect_headset.py | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

> **Note**: ARL, WCL, TTL, and RZL test execution is not yet started (❌). Test scripts
> are expected to be platform-portable with DID updates. Priority: WCL/TTL first (ACE 3.x/4.x
> bring-up), then RZL (ACE 4.x), then ARL (ACE 1.5 legacy).

---

## 3. NGA XML → Test Category Mapping

| NGA XML | Category | Tests Included | Run Time (est.) |
|---------|----------|----------------|-----------------|
| audio_bkc_checkout.xml | BKC Checkout | enum, hda_basic, sdw_basic, dsp_basic | 15 min |
| audio_hda_full.xml | HDA Full Suite | all hda_* tests | 45 min |
| audio_sdw_full.xml | SoundWire Full | all sdw_* tests | 60 min |
| audio_dsp_full.xml | DSP Full Suite | all dsp_* tests | 30 min |
| audio_dmic_full.xml | DMIC Full Suite | all dmic_* tests | 20 min |
| audio_pm_full.xml | PM Full Suite | all pm_* tests | 90 min |
| audio_uaol_full.xml | UAOL Full Suite | all uaol_* tests | 45 min |
| audio_wov_full.xml | WoV Full Suite | wov_* + dmic_* | 30 min |
| audio_jack_full.xml | Jack Detect Full | all jack_* tests | 20 min |
| audio_ssp_full.xml | SSP/BT Offload | all ssp_* tests | 25 min |
| audio_regression_light.xml | Light Regression | BKC + 1 stream/domain | 25 min |
| audio_regression_full.xml | Full Regression | All suites | 6 hr |
| audio_stress_overnight.xml | Stress/Endurance | pm_* × 100 cycles + streams | 12 hr |
| audio_s0ix_validation.xml | S0ix Audio | pm_s0ix + wov + dmic in S0ix | 3 hr |
| audio_concurrent_streams.xml | Concurrent | Multi-stream playback+capture | 1 hr |

---

## 4. OS Coverage

> **NVL audio validation is Windows-only.** All test suites run exclusively on
> Windows 11. There is no Linux test execution in this project scope.
> The `audio_self_study.py` tool monitors Linux kernel audio driver commits as a
> *research signal* only — it does not imply test execution coverage on Linux.

| Test Group | Windows 11 | Notes |
|------------|------------|-------|
| audio_enum_checkout | ✅ | PCI/BAR enumeration via PythonSV |
| hda_full | ✅ | intcaudiobus.sys + intcpchsnd.sys |
| sdw_full | ✅ | intcpchsnd.sys SoundWire stack |
| dsp_full | ✅ | intelaud.sys SOF runtime |
| dmic_full | ✅ | intelpch_dmic.sys |
| pm_full | ✅ | Windows Modern Standby (S0ix) |
| uaol_full | ✅ | USB Audio Offload via ACE4 |
| wov_full | ✅ | Keyword Detect via Windows Speech platform |
| jack_full | ✅ | HDA pin sense + SoundWire alerts |
| ssp_full | ✅ | BT HFP offload via CNVi |
| stress_overnight | ✅ | Windows-only endurance |

---

## 5. BIOS Knob Matrix

| BIOS Knob | Default | Tests That Require Change | Rationale |
|-----------|---------|--------------------------|-----------|
| AudioDsp | Enabled | dsp_fw_load, wov_* | Must be enabled for SOF load |
| SoundWireEnable | Enabled | sdw_* | Must be enabled |
| DmicEnable | Enabled | dmic_* | Must be enabled |
| I2S_SSP_Enable | Enabled | ssp_* | Must be enabled for BT offload |
| AudioD3PG | Enabled | pm_d3_entry_exit | D3 power gate must be active |
| UsitEnable | Enabled | uaol_* | UAOL requires USIT |
| ModernStandby | S0ix | pm_s0ix_residency | S0 → S0ix mode |
| WoVEnable | Enabled | wov_keyword_detect | WoV requires special knob |

---

## 6. Coverage Summary by Domain

| Domain | Total Tests | Pass Rate (NVL baseline) | Sev1/2 Gaps |
|--------|-------------|--------------------------|-------------|
| HDA | 5 tests | ~95% | None known |
| SoundWire | 5 tests | ~90% | SDW CLK_STOP recovery |
| DSP | 6 tests | ~85% | DSP wakeup race |
| DMIC | 4 tests | ~92% | None known |
| SSP/BT | 2 tests | ~88% | BCLK recovery after PG |
| UAOL | 2 tests | ~80% | NVL PCD-H only; PCD-S not yet characterized |
| PM/S0ix | 3 tests | ~75% | S0ix LTR tuning |
| WoV | 1 test | ~82% | CRO accuracy |
| Jack Detect | 2 tests | ~93% | DP audio hotplug |
| Interrupts | 1 test | ~98% | None known |
| Config | 2 tests | ~99% | None known |

> Pass rates are approximate baselines from NVL PCD-H A0 ES2 runs.
> See `audio_test_gap_analysis.md` for specific gap action items.
