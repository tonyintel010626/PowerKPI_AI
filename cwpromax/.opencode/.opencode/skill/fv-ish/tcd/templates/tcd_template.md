# TCD — {{TC_TITLE}}

> **Template Version**: Based on "TCD & TC Template Details.docx" Version 20 (12/17/2025)
> Reference: https://intel.sharepoint.com/:w:/r/sites/csve/Shared%20Documents/FV%20Domains%20alignment/Test%20Plan%20Methodologies/TCTCD%20new%20template.docx
>
> Fill every section. Use `[TODO: <description>]` for missing information — never leave blank.
> Sections marked **(optional)** may be removed if not applicable — but document why.

---

## Identification

| Field | Value |
|-------|-------|
| **TCD Title** | {{TC_TITLE}} |
| **HSDES ID** | {{HSDES_ID}} |
| **Parent Test Plan** | {{PARENT_TESTPLAN}} |
| **System** | {{SYSTEM}} |
| **Category** | {{CATEGORY}} |
| **Family** | {{FAMILY}} |
| **Family Affected** | {{FAMILY_AFFECTED}} |
| **Priority** | {{PRIORITY}} |
| **Product Segment** | {{PRODUCT_SEGMENT}} |
| **Owner** | {{OWNER}} |
| **Owner Team** | {{OWNER_TEAM}} |
| **Val Teams** | {{VAL_TEAMS}} |
| **Status** | {{STATUS}} |
| **Origin Project** | {{ORIGIN_PROJECT}} |
| **Date Created** | {{DATE_CREATED}} |
| **Last Updated** | {{LAST_UPDATED}} |

---

## 1. Description

[TODO: Describe the test case in detail. What feature or behavior is being tested?
What is the scope? What is the expected behavior of the IP/feature under test?
Include high-level context so a reader unfamiliar with the feature can understand
what this TCD covers.]

---

## 2. Algorithm of Testing

[TODO: Describe the step-by-step test algorithm. How will the test be executed?
Include:
- Setup/initialization steps
- Stimulus/action to apply
- What to observe/measure/read back
- Pass/fail decision logic
- Cleanup/teardown steps

Use numbered steps for clarity.]

1. [TODO: Step 1 — Setup]
2. [TODO: Step 2 — Action/Stimulus]
3. [TODO: Step 3 — Observation/Verification]
4. [TODO: Step 4 — Pass/Fail Decision]
5. [TODO: Step 5 — Cleanup/Teardown]

---

## 3. Randomization

[TODO: Describe any randomization applied in this test.
- Which parameters are randomized? (e.g., data patterns, timing, order of operations)
- What is the randomization range/seed?
- Is the test deterministic or stochastic?
- If no randomization: state "No randomization — deterministic test."]

---

## 4. Required Configuration and Dependencies

[TODO: List ALL prerequisites, configurations, and dependencies needed before executing this test.]

| # | Requirement | Details |
|---|------------|---------|
| 1 | **Platform/Silicon** | [TODO: Platform, stepping, SKU] |
| 2 | **BIOS Configuration** | [TODO: Required BIOS knobs, settings, or BIOS version] |
| 3 | **Firmware** | [TODO: Required FW version (e.g., ISH FW, ME FW, CSME)] |
| 4 | **OS / Driver** | [TODO: OS version, driver version, tool version] |
| 5 | **Hardware BOM** | [TODO: Required hardware components (e.g., sensor model, board rework)] |
| 6 | **IP Initial State** | [TODO: Required initial state of the IP under test] |
| 7 | **External Equipment** | [TODO: Any external equipment needed (e.g., analyzer, TTK3, scope)] |
| 8 | **Other Dependencies** | [TODO: Other test dependencies, or "None"] |

---

## 5. Coverage (optional)

[TODO: Define the coverage model for this test.
- What parameter space does this test cover?
- What are the coverage bins or cross-products?
- What is the target coverage percentage?
- If not applicable: state "Coverage model not applicable for this test." and remove this section.]

| Coverage Dimension | Values / Bins | Notes |
|-------------------|---------------|-------|
| [TODO: Dimension 1] | [TODO: Value range or bins] | [TODO] |
| [TODO: Dimension 2] | [TODO: Value range or bins] | [TODO] |

---

## 6. Cross-Feature Interaction

[TODO: Describe interactions with other features or IPs that may affect this test.
- Which other features/IPs does this test depend on or interact with?
- Are there known cross-feature sensitivities?
- What shared resources are involved?
- If none: state "No known cross-feature interactions."]

| Interacting Feature/IP | Type of Interaction | Impact on Test |
|-----------------------|--------------------:|----------------|
| [TODO: Feature/IP name] | [TODO: dependency / shared resource / timing] | [TODO: How it affects this test] |

---

## 7. DFx Requirements

[TODO: Describe Design-for-Test / Design-for-Debug requirements.
- What debug hooks, trace points, or DFx features are needed?
- Are there specific DFx modes required for this test?
- What observability is needed (registers, signals, logs)?
- If none: state "No specific DFx requirements."]

---

## 8. Negative Testing (optional)

[TODO: Describe negative test scenarios — what happens when things go WRONG.
- Error injection scenarios
- Invalid input handling
- Timeout / watchdog behavior
- Recovery from error conditions
- If not applicable: state "Negative testing not applicable." and remove this section.]

| # | Negative Scenario | Expected Behavior | How to Inject |
|---|-------------------|-------------------|---------------|
| 1 | [TODO: Error scenario] | [TODO: Expected error handling] | [TODO: Injection method] |

---

## 9. PVT Aspects (optional)

[TODO: Describe Post-Silicon Validation Test (PVT) specific considerations.
- Silicon-specific behaviors to validate
- Stepping-dependent behavior
- Fuse/configuration dependencies
- If not applicable: state "No PVT-specific aspects." and remove this section.]

---

## 10. Performance / Bandwidth Testing (optional)

[TODO: Describe performance or bandwidth validation aspects.
- What throughput, latency, or bandwidth metrics are measured?
- What are the pass thresholds?
- What load/stress conditions are applied?
- If not applicable: state "No performance/bandwidth testing." and remove this section.]

| Metric | Target | Measurement Method | Pass Threshold |
|--------|--------|--------------------|----------------|
| [TODO: Metric name] | [TODO: Target value] | [TODO: How to measure] | [TODO: Min/max acceptable] |

---

## Sources & References

| # | Source Document | Section/Page | Link | Date Accessed |
|---|----------------|-------------|------|---------------|
| 1 | [TODO: Document Name] | [TODO: Section or Page] | [TODO: URL or file path] | [TODO: YYYY-MM-DD] |
| 2 | [TODO: Document Name] | [TODO: Section or Page] | [TODO: URL or file path] | [TODO: YYYY-MM-DD] |

### Source Notes
- **Primary**: [TODO: Which source was the main basis for this TCD]
- **Cross-referenced with**: [TODO: HSDES #id if based on existing TCD, or "N/A"]
- **Generated by**: TCD Skill v1.1 on [TODO: generation date]
