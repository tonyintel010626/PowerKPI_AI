# TC — {{TC_TITLE}}

> **Template Version**: Based on "TCD & TC Template Details.docx" Version 20 (12/17/2025)
> Reference: https://intel.sharepoint.com/:w:/r/sites/csve/Shared%20Documents/FV%20Domains%20alignment/Test%20Plan%20Methodologies/TCTCD%20new%20template.docx
>
> This is the **Test Case (TC)** template — 11 sections (different from the 10-section TCD template).
> A TC is a child of a TCD. It describes HOW to execute a specific test scenario.
> Fill every section. Use `[TODO: <description>]` for missing information — never leave blank.
> Sections marked **(optional)** may be removed if not applicable — but document why.

---

## Identification

| Field | Value |
|-------|-------|
| **TC Title** | {{TC_TITLE}} |
| **HSDES ID** | {{HSDES_ID}} |
| **HSDES Tenant** | {{TENANT}} |
| **Parent TCD** | {{PARENT_TCD_TITLE}} ({{PARENT_TCD_ID}}) |
| **Original Test Plan** | {{ORIGINAL_TESTPLAN}} |
| **System** | {{SYSTEM}} |
| **Category** | {{CATEGORY}} |
| **Family** | {{FAMILY}} |
| **Family Affected** | {{FAMILY_AFFECTED}} |
| **Product Segment** | {{PRODUCT_SEGMENT}} |
| **Scope** | {{SCOPE}} |
| **Owner** | {{OWNER}} |
| **Owner Team** | {{OWNER_TEAM}} |
| **Val Teams** | {{VAL_TEAMS}} |
| **Val Environment** | {{VAL_ENVIRONMENT}} |
| **Val Framework** | {{VAL_FRAMEWORK}} |
| **Automation** | {{AUTOMATION}} |
| **Status** | {{STATUS}} |
| **Free Tag 1** | {{FREE_TAG_1}} |
| **Free Tag 3** | {{FREE_TAG_3}} |
| **Date Created** | {{DATE_CREATED}} |
| **Last Updated** | {{LAST_UPDATED}} |

---

## 1. TC Description

[TODO: Describe what this specific test case validates. How does it differ from the parent TCD scope?
What is the specific scenario, configuration, or variant being tested?
Include: feature under test, expected behavior, and why this test matters.]

---

## 2. Test Steps

[TODO: Provide detailed, numbered, executable test steps. Each step should be specific enough
that another engineer can reproduce the test without ambiguity.

Include for each step:
- Pre-action setup (if needed)
- Exact action to perform (register read/write, command, tool invocation)
- What to observe/record]

1. [TODO: Step 1 — Setup/Precondition]
2. [TODO: Step 2 — Action/Stimulus]
3. [TODO: Step 3 — Observation/Verification]
4. [TODO: Step N — Cleanup/Teardown]

---

## 3. Pass/Fail Criteria & HW Errors

### Pass Criteria
[TODO: Define the exact conditions under which this test is considered PASS.
Use measurable, observable criteria — register values, status flags, functional outcomes.]

### Fail Criteria
[TODO: Define the exact conditions under which this test is considered FAIL.
Include specific error conditions, timeout scenarios, and unexpected states.]

### HW Errors
[TODO: List any known HW errors (errata, sightings) that may affect this test.
Reference HSDES sighting IDs if applicable.
If none known: state "No known HW errors affecting this test."]

---

## 4. Intent Verify

[TODO: Describe the design intent being verified by this test case.
What specific HW/FW behavior is being validated?
Map back to the HAS/spec requirement being verified.
Include HAS section references.]

---

## 5. Validation SW: Tool and Content Requirements

[TODO: List all software tools and content required to execute this test.]

| # | Tool/Content | Version/Details | Purpose |
|---|-------------|----------------|---------|
| 1 | [TODO: Tool name] | [TODO: Version] | [TODO: Purpose] |

---

## 6. Ecosystem SW: Test Requirements

[TODO: Describe OS, driver, firmware, and ecosystem software requirements.]

| # | Requirement | Details |
|---|------------|---------|
| 1 | **OS** | [TODO: OS version and configuration] |
| 2 | **Driver** | [TODO: Driver version and configuration] |
| 3 | **Firmware** | [TODO: FW version and configuration] |
| 4 | **BIOS** | [TODO: BIOS knobs and configuration] |
| 5 | **Other** | [TODO: Other ecosystem SW requirements] |

---

## 7. Test HW Requirements and HW Configuration

[TODO: Describe the hardware platform, BOM, and configuration required.]

| # | Requirement | Details |
|---|------------|---------|
| 1 | **Platform** | [TODO: Platform, stepping, SKU] |
| 2 | **BOM** | [TODO: Required hardware components] |
| 3 | **External Equipment** | [TODO: Any external equipment needed] |
| 4 | **HW Configuration** | [TODO: Specific board reworks, jumper settings, etc.] |

---

## 8. PVT (optional)

[TODO: Post-Silicon Validation Test specific considerations.
- Stepping-dependent behavior
- Voltage/temperature corner sensitivity
- Fuse/CAPID configuration
- If not applicable: state "No PVT-specific aspects." and remove this section.]

---

## 9. Performance/BW (optional)

[TODO: Performance or bandwidth metrics to measure during this test.
- Latency, throughput, bandwidth targets
- Measurement methodology
- Pass thresholds
- If not applicable: state "No performance/BW testing." and remove this section.]

| Metric | Target | Measurement Method | Pass Threshold |
|--------|--------|--------------------|----------------|
| [TODO: Metric] | [TODO: Target] | [TODO: Method] | [TODO: Threshold] |

---

## 10. Validation Automation Global Checkers (optional)

[TODO: Describe any global checker integration for automated validation.
- Which checkers apply to this test?
- Checker configuration
- Expected checker output
- If not applicable: state "No global checkers." and remove this section.]

---

## 11. ISOC Validation (optional)

[TODO: Describe iSOC (In-Silicon Observability and Control) validation aspects.
- Which iSOC features are used?
- iSOC trigger configuration
- Expected iSOC capture data
- If not applicable: state "Not applicable." and remove this section.]

---

## Sources & References

| # | Source Document | Section/Page | Link | Date Accessed |
|---|----------------|-------------|------|---------------|
| 1 | [TODO: Document Name] | [TODO: Section or Page] | [TODO: URL or file path] | [TODO: YYYY-MM-DD] |
| 2 | [TODO: Document Name] | [TODO: Section or Page] | [TODO: URL or file path] | [TODO: YYYY-MM-DD] |

### Source Notes
- **Primary**: [TODO: Which source was the main basis for this TC]
- **Parent TCD**: HSDES #{{PARENT_TCD_ID}} — {{PARENT_TCD_TITLE}}
- **Cross-referenced with**: [TODO: HSDES #id if based on existing TC, or "N/A"]
- **Generated by**: TC Skill v1.0 on [TODO: generation date]
