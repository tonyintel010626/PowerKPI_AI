> **Owner**: Chin, William Willy (`willychi`)

# QuickSPI Software Architecture Specification v1.0
# COMPLETE EXTRACTION — ZERO OMISSIONS
# Source: C:\QuickSPI SwAS v1.0.docx
# Total paragraphs: 1022
# Total tables: 6
# Total sections: 1

P0000: # 
P0001: QuickSpi (HIDSPI over Touch Host Controller)  {style: DocTitle}
P0002: Software Architecture Specification (SwSAS)  {style: DocType}
P0003: Target Platforms: 
P0004: - POR
P0005: - 2021 Raptor Lake
P0006: - 2022 Meteor Lake
P0007: - 2023 Lunar Lake
P0008: - 2024 Panther Lake
P0009: - Panther Lake
P0010: 
P0011: Revision 1.0
P0012: Intel Confidential
P0013: 
P0014: 
P0015: 
P0016: 
P0017: 
P0018: 
P0019: 
P0020: 
P0021: 
P0022: 
P0023: 
P0024: 
P0025: 
P0026: 
P0027: 
P0028: 
P0029: 
P0030: 
P0031: 
P0032: 
P0033: 
P0034: 
P0035: 
P0036: 
P0037: 
P0038: 
P0039: 
P0040: 
P0041: 
P0042: 
P0043: 
P0044:   {style: Legal}
P0045:   {style: Legal}
P0046:   {style: Legal}
P0047:   {style: Legal}
P0048:   {style: Legal}
P0049:   {style: Legal}
P0050:   {style: Legal}
P0051:   {style: Legal}
P0052:   {style: Legal}
P0053:   {style: Legal}
P0054:   {style: Legal}
P0055:   {style: Legal}
P0056:   {style: Legal}
P0057:   {style: Legal}
P0058:   {style: Legal}
P0059:   {style: Legal}
P0060:   {style: Legal}
P0061:   {style: Legal}
P0062:   {style: Legal}
P0063:   {style: Legal}
P0064: INFORMATION IN THIS DOCUMENT IS PROVIDED IN CONNECTION WITH INTEL® PRODUCTS.  NO LICENSE, EXPRESS OR IMPLIED, BY ESTOPPEL OR OTHERWISE, TO ANY INTELLECTUAL PROPERTY RIGHTS IS GRANTED BY THIS DOCUMENT. EXCEPT AS PROVIDED IN INTEL’S TERMS AND CONDITIONS OF SALE FOR SUCH PRODUCTS, INTEL ASSUMES NO LIABILITY WHATSOEVER, AND INTEL DISCLAIMS ANY EXPRESS OR IMPLIED WARRANTY, RELATING TO SALE AND/OR USE OF INTEL PRODUCTS INCLUDING LIABILITY OR WARRANTIES RELATING TO FITNESS FOR A PARTICULAR PURPOSE, MERCHANTABILITY, OR INFRINGEMENT OF ANY PATENT, COPYRIGHT OR OTHER INTELLECTUAL PROPERTY RIGHT.   {style: Legal}
P0065: Recipients of this EDS (“Recipients”) are not obligated to provide Intel with ideas, comments or suggestions regarding the EDS (“Feedback”).  Intel has not agreed to and does not agree to treat as confidential any such Feedback.  Nothing in the EDS or in the parties’ dealings arising out of or related to it will restrict Intel’s right to use, profit from, disclose, publish, or otherwise exploit any Feedback, without compensation to Recipients, unless otherwise agreed in a writing executed by Intel.  {style: Legal}
P0066: Intel products are not intended for use in medical, life saving, or life sustaining applications.  {style: Legal}
P0067: Intel may make changes to specifications and product descriptions at any time, without notice.   {style: Legal}
P0068: Designers must not rely on the absence or characteristics of any features or instructions marked "reserved" or "undefined." Intel reserves these for future definition and shall have no responsibility whatsoever for conflicts or incompatibilities arising from future changes to them.  {style: Legal}
P0069: Intel® Integrated Touch may contain design defects or errors known as errata which may cause the product to deviate from published specifications. Current characterized errata are available on request.  {style: Legal}
P0070: Contact your local Intel sales office or your distributor to obtain the latest specifications and before placing your product order.  {style: Legal}
P0071: Intel and the Intel logo are trademarks or registered trademarks of Intel Corporation or its subsidiaries in the United States and other countries.  {style: Legal}
P0072: *Other names and brands may be claimed as the property of others.  {style: Legal}
P0073: Copyright © 2018, Intel Corporation. All rights reserved.  {style: Legal}
P0074: 
P0075:   {style: Title}
P0076: [TOC] Contents
P0077: Acknowledgments	6  {style: toc 1}
P0078: Revision History	7  {style: toc 1}
P0079: Reviewers / Stakeholders	8  {style: toc 1}
P0080: 1	Introduction	9  {style: toc 1}
P0081: 1.1	Document Scope	9  {style: toc 2}
P0082: 1.2	Terms and Abbreviations	9  {style: toc 2}
P0083: 1.3	REFERENCE DOCUMENTS	10  {style: toc 2}
P0084: 2	THC (Touch Host Controller) Architecture	10  {style: toc 1}
P0085: 2.1	Hardware Overview	10  {style: toc 2}
P0086: 3	Typical HIDSPI Software Stack on generic spi bus (i.e., non-accelerated architecture)	12  {style: toc 1}
P0087: 4	HIDSPI over THC Architecture Overview	13  {style: toc 1}
P0088: 5	THC Initialization Flows	16  {style: toc 1}
P0089: 5.1.1	BIOS Initialization of the THC	16  {style: toc 3}
P0090: 5.1.2	ACPI Enumeration	16  {style: toc 3}
P0091: 5.1.3	Sample ASL	20  {style: toc 3}
P0092: 5.2	QUICKSPI Driver Init Flows	25  {style: toc 2}
P0093: 5.2.1	QUICKSPI Driver	25  {style: toc 3}
P0094: 5.2.2	AddDevice	25  {style: toc 3}
P0095: 5.2.3	PrepareHw	26  {style: toc 3}
P0096: 5.2.4	QUICKSPI D0Entry	26  {style: toc 3}
P0097: 5.2.5	TIC Reset Exit Flow (i.e., Host Initiated Reset)	27  {style: toc 3}
P0098: 5.2.6	Read Device Descriptor	28  {style: toc 3}
P0099: 5.2.6.1	Write DMA Init	31  {style: toc 3}
P0100: 5.2.6.2	RxDMA2 Initialization	32  {style: toc 3}
P0101: 5.2.7	Interrupt Enable	35  {style: toc 3}
P0102: 5.3	QUICKSPI Driver HID Operations	36  {style: toc 2}
P0103: 6	QUICKSPI Driver Runtime Operations	37  {style: toc 1}
P0104: 6.1	QUICKSPI Read Data Flows	37  {style: toc 2}
P0105: 6.1.1	Input Report Data Flow	37  {style: toc 3}
P0106: 6.1.1.1	Input Reports	38  {style: toc 3}
P0107: 6.1.1.2	Output Reports	38  {style: toc 3}
P0108: 6.1.1.3	Commands	40  {style: toc 3}
P0109: 6.1.1.4	Quiescing the THC	41  {style: toc 3}
P0110: 6.1.2	HW/SW Interrupt Handling Behavior	41  {style: toc 3}
P0111: 6.1.2.1	HW Sequencer Behavior	41  {style: toc 3}
P0112: 6.1.2.2	SW Interrupt Behavior	42  {style: toc 3}
P0113: 6.1.2.3	ISR Behavior	43  {style: toc 3}
P0114: 6.1.2.4	DPC Behavior	44  {style: toc 3}
P0115: 6.1.2.4.1	Interrupt Locks	44  {style: toc 3}
P0116: 6.1.3	Throttling	44  {style: toc 3}
P0117: 6.2	Error Handling Operations	45  {style: toc 2}
P0118: 6.2.1	SW Sequencing (PIO) Error	46  {style: toc 3}
P0119: 6.2.2	Read DMA Errors	46  {style: toc 3}
P0120: THC LTR settings	47  {style: toc 2}
P0121: 6.2.3	Driver Init	47  {style: toc 3}
P0122: 6.2.4	THC D3	47  {style: toc 3}
P0123: 6.3	Tap to Wake	48  {style: toc 2}
P0124: 6.3.1	Tap to Wake (Wakeable Mode) Entry	48  {style: toc 3}
P0125: 6.3.2	Tap to Wake (Wakeable Mode) Exit	48  {style: toc 3}
P0126: 7	QUICKSPI Driver Teardown Flows	49  {style: toc 1}
P0127: 7.1	Full Quiesce Operation	49  {style: toc 2}
P0128: 8	QUICKSPI Driver Power Management	49  {style: toc 1}
P0129: 8.1	QUICKSPI Driver D0Exit	51  {style: toc 2}
P0130: 8.2	Idle support	51  {style: toc 2}
P0131: 8.1	Driver Production Debug Features	52  {style: toc 2}
P0132: 8.1.1	Registry Keys	52  {style: toc 2}
P0133:   {style: toc 2}
P0134: [TOC] Revision history

=== TABLE 1 (rows=9, cols=3) ===
  T1R000: Revision Number || Description || Revision Date
  T1R001: 0.3 || Initial release. || February 16, 2021
  T1R002: 0.5 || Updated _DSM definition and added sample ASL || October 25, 2021
  T1R003: 0.8 || Clarified usage of Connection Speed in  _DSM definition  | Updated Wake on Touch exit flow || February 1, 2022
  T1R004: 1.0 || Updated DID table, added sections on frame coalescing || September 22, 2022
  T1R005:  ||  || 
  T1R006:  ||  || 
  T1R007:  ||  || 
  T1R008:  ||  || 
=== END TABLE 1 ===

P0135: 
P0136: 
P0137: Acknowledgments  {style: Header-PreSection}
P0138: Besides the authors and key contributors listed on the front page, additional thanks goes to the following individuals and groups for contributing to the architecture directly or indirectly at different times during the solution development.
P0139: 
P0140: - Anton Cheng
P0141: - Kruthi Murali
P0142: - Scott Webb
P0143: - Luis Lorenzo
P0144: - Jason Gaston
P0145: - Mukesh Komalan
P0146: - Oren Weil
P0147: - Even Xu
P0148: - Pradeep Kumar
P0149: 
P0150: - 
P0151: 
P0152: Please contact Saiprasad Paithara if any names are missing from this list.
P0153: 
P0154: Revision History  {style: Header-PreSection}

=== TABLE 2 (rows=3, cols=3) ===
  T2R000: Rev. || Date || Revision Scope
  T2R001: 0.3 || 02/16/2021 || Branch from THC SwSAS 0.55.   Change in direction to support HIDSPI protocol over THC
  T2R002:  ||  || 
=== END TABLE 2 ===

P0155: 
P0156: Reviewers / Stakeholders  {style: Header-PreSection}

=== TABLE 3 (rows=6, cols=3) ===
  T3R000: Name || Roles || Revision Sent / Acknowledged
  T3R001: Anton Cheng || CCG Architect - Human Input Domain Lead || 
  T3R002: Kevin Zhu || CIG HW Architect – THC-SPI lead || 
  T3R003: Kruthi Murali || CCG SW – HIDSPI SW Engineering || 
  T3R004: Scott Webb || CCG CCE – HIDSPI Enabling Lead, Enabling Guide Owner || 
  T3R005: Jason Gaston || CCG Validation --  Input Subsystem Validation Lead || 
=== END TABLE 3 ===

P0157: 
P0158: 
P0159: # Introduction
P0160: This document specifies the software architecture changes required to support HIDSPI specification on Intel’s Touch Host Controller (THC) subsystem starting from Alder Point P chipset.
P0161: ## Document Scope
P0162: This document was written to guide implementation of QUICKSPI Driver software component for Windows Cobalt OS on CCG platforms starting from Raptor Laker (RPL), Meteor Lake (MTL), Lunar Lake and Panther Lake. This document will focus on the BIOS, ACPI and OS configuration of Touch Host Controller Subsystem to communicate with HIDSPI v1.0 compliant Touch Controller devices. The primary focus for SW operation is supporting the Windows 11 in-box driver frameworks for support of Touch and stylus peripherals connected directly to the THC controller.  
P0163: General BIOS configuration, requirements and architecture are listed in the references.
P0164: 
P0165: ## Terms and Abbreviations
P0166: - The terms and abbreviations listed in Table 1.1.1 are used as described in this document.
P0167: Table 1.1 – Terms and abbreviations  {style: Caption}

=== TABLE 4 (rows=20, cols=2) ===
  T4R000: Term || Description
  T4R001: CS || Connected Standby
  T4R002: I2C || Inter-Integrated Circuit  - in the LPT LP platform there are two instances of the I2C (host) bus controllers.
  T4R003: SPI || Serial Peripheral Interface. Synchronous serial communication bus used to attach peripherals to motherboard. In the ADP-P and MTL chipset, there are two instances of THC-SPI host controllers.
  T4R004: GPIO || General Purpose Input/Output – in the chipset there is General Purpose Input/Output controller that fits within the definition of the ACPI 5.0 GPIO controller.
  T4R005: LTR || Latency Tolerance Reporting
  T4R006: Sideband interrupt || Interrupt from a peripheral direct to the host CPU without intervention of its associated host bus controller.
  T4R007: THC || Touch Host Controller within the chipset that supports SPI based host controller interface to touch devices
  T4R008: HidSpi || Microsoft defined specification  that defines the protocol, procedure and features for input devices to communicate using HID protocol over SPI interface
  T4R009: HidSpi.sys || Microsoft driver that implement HidSpi protocol on top of SPB (Simple Peripheral Bus) framework.   See QuickSPI for HIDSPI-over-THC driver.
  T4R010: HidSCx || Microsoft defined Serial Class Extension framework for HID over Serial Buses. The class extension is defined for clients which implement v1.0 of hidspi protocol
  T4R011: QuickSPI || Name for the HID mini driver that implement HIDSPI protocol over THC-SPI (with HW accelerated interrupt handling).    Not to be confused with HIDSPI.sys that implements HIDSPI protocol on SPB framework.
  T4R012: ACPI || Advanced Configuration and Power Interface – for this specification we are assuming ACPI 5.0
  T4R013: PEP || Power Engine Plugin
  T4R014: RTD3 Power management || Run-time D3 Power Management
  T4R015: Simple Peripheral Buses || Microsoft defined term to refer to the classification of synchronous serial IO buses that can use clock signal to transmit consecutive data bits over the buses.  This classification includes I2C and SPI.
  T4R016: LPSS || Low Power Subsystem – reference to the IOs new to LPT LP that include I2C, (General Purpose) SPI, UART and SDIO controller.
  T4R017:  || 
  T4R018: SoC || System on Chip
  T4R019: WDK || Windows Driver Kit
=== END TABLE 4 ===

P0168: 
P0169: ## REFERENCE DOCUMENTS
P0170: 
P0171: # THC (Touch Host Controller) Architecture
P0172: ## Hardware Overview
P0173:  [IMAGE]
P0174: 
P0175: Figure 1: THC Functional Block Diagram
P0176: 
P0177: 
P0178: The Touch Host Controller (THC) is a soft IP supporting a host controller interface to the HIDSPI device driver for data transfer from SPI based (quad IO, up to 50MHz) touch devices. This cluster has a single root space IOSF Primary interface that supports transactions to/from touch devices. Host driver configures and controls the touch devices over THC interface. THC provides high bandwidth DMA services to the HIDSPI driver and transfers the HID reports to host system main memory that is accessible by internal touch accelerator (host CPU), or host driver respectively.
P0179: The THC Controller has the following interfaces:  {style: BodyText}
P0180: - IOSF Primary Interface for DMA operation and register access  {style: BodyText}
P0181: - Minimum 100MHz 64 bit IOSF bandwidth  {style: BodyText}
P0182: - Dual port RAM interface for RX data buffering  {style: BodyText}
P0183: - Chassis DFT Interface  {style: BodyText}
P0184: - Chassis Clock/Reset/PM interfaces  {style: BodyText}
P0185: Hardware sequencer within the THC is responsible for transferring (via DMA) data from Touch IC into system memory.  A ring buffer is used to avoid data loss due to asynchronous nature of data consumption (by host) in relation to data production (by Touch IC via DMA). For each Touch IC, there is one ring buffer for CPU memory address space. 
P0186: 
P0187: Unaccelerated Reference HIDSPI Driver Stack 
P0188: HIDSPI protocol defines operational flows, data structures and bus characteristics that may be used by a HID compliant Touch controller (aka Touch IC) to communicate with Windows host computer over SPI bus. Typical SW implementations involve an OS inbox hidspi driver communicating with Touch IC using an SPB compliant controller. The underlying assumptions are that the SPI bus is generic, unenlightened (i.e., non-accelerated) and the hidspi driver can send raw bytes to the SPB client driver to be transferred to/from the Touch IC device. The hidspi driver oversees handling of interrupts from the Touch IC and coordinates SPI transfers.   {style: Plain Text}
P0189:   {style: Plain Text}
P0190: 
P0191:  [IMAGE]
P0192: The HIDSPI device in this architecture is enumerated via ACPI and requires the following resources: Interrupt, SPB SPI bus resource and ACPI reset method.  {style: Plain Text}
P0193: 
P0194: # HIDSPI over THC Architecture Overview
P0195: 
P0196:  [IMAGE]
P0197: 
P0198: 
P0199:   {style: Plain Text}
P0200: Figure 2: THC HIDSPI System Architecture Diagram
P0201:   {style: Plain Text}
P0202:   {style: Plain Text}
P0203: This figure illustrates the high-level architecture of THC starting from ADL-P, which is fully capable of supporting Microsoft HIDSPI v1.0 protocol in addition to maintaining compatibility with IPTS protocol.  {style: Plain Text}
P0204:   {style: Plain Text}
P0205: Starting from Cobalt OS, HIDSCx framework allows hardware partners to build new hardware implementations that are able to support HIDSPI protocol and can support higher throughput, as data interrupts are directly consumed by hardware, resulting in much lower latency to fetch input reports from the device. This requires adding a new hardware accelerator controller (aka HWA Client) driver to the software stack using a brand new Microsoft Class extension framework for HID over serial buses (here in referred to as HIDSCx).  {style: Plain Text}
P0206:   {style: Plain Text}
P0207:   {style: Plain Text}
P0208: Hardware partners are required to build the HWA Client driver due to differences in underlying hardware (DMA, register map etc.).   {style: Plain Text}
P0209: 
P0210: Intel QUICKSPI (HIDSPI over THC) Software Overview:  {style: Plain Text}
P0211: 
P0212:  [IMAGE]
P0213: 
P0214: Figure 4: HidSCx SW Architecture
P0215: 
P0216: In this new architecture, HidSCx is an OS based class extension component that will maintain the protocol flow, track device state, communicate with OS HID stack, manage request/device queues and dispatch requests to the HWA Controller/Client driver. The client driver will be responsible for managing the underlying hardware, provide a way to reset the Touch IC device and manage PNP resources assigned by the platform.   {style: Plain Text}
P0217:   {style: Plain Text}
P0218: Client Driver responsibilities:  {style: Plain Text}
P0219: - Manage resources needed by the Touch device using ACPI platform specific definitions
P0220: - Reading/Writing of reports. Provide fully assembled incoming reports to HIDSCx and write outgoing reports to the SPI bus as instructed by HIDSCx
P0221: - Reset handling. Provide a method for HIDSCx to initiate a device reset and send reset responses as input reports to HIDSCx
P0222: - Power state transitions. Hidclass is the power policy owner for the device. HIDSCx will handle reset notifications and idle notification requests from hidclass. Client driver will rely on standard ACPI definitions within the platform BIOS to manage power to the Touch IC
P0223: - Report validation – Client driver is responsible for validating length and other fields of the input report header before passing the input reports to HIDSCx.
P0224:   {style: Plain Text}
P0225: In addition to the above responsibilities, the client driver is also responsible for maintaining two queues for interfacing with HidSCx and configuring HID device specific registry settings.  {style: Plain Text}
P0226:   {style: Plain Text}
P0227: 
P0228: The primary OS environment that supports HIDSCx framework is Windows Cobalt. Intel QUICKSPI driver supports discrete touch processing where the Touch IC sends pre-processed touch/stylus reports, as well as heatmap processing where the Touch IC sends HID reports containing heatmap data that are converted to to Touch reports. QUICKSPI driver is responsible for controlling the flow of information between the THC Host Controller, Touch IC and the Window HID infrastructure (HIDSCx and PnP etc.).   {style: Plain Text}
P0229:   {style: Plain Text}
P0230: THC Touch System Components:  {style: Plain Text}
P0231: - THC Touch IC: AKA the Touch AFE (analog front end). The discrete analog components that sense and transfer either discrete touch data or heatmap data in the form of HID reports over the SPI bus to the THC Controller on the host.
P0232: - THC Host Controller: The PCI device HBA (host bus adapter), integrated into the PCH, that serves as a bridge between the THC Touch ICs and the host.
P0233: - QUICKSPI Client Driver: The OS-based kernel mode driver that manages the THC Controller and the primary focus of this specification.
P0234: - HIDSCx: WDF based class extension library provided by Windows operating system that the QUICKSPI Client driver links against at runtime. This class extension handles the interactions with hidclass and provides a DDI abstraction layer to the QUICKSPI client driver.
P0235: - HIDClass Driver: The kernel mode HID driver from the OSV. In Windows this driver exports a device object for every touch sensor it detects as a result of receiving a Report Descriptor.
P0236: - BIOS (not shown): Contains a THC Host Driver component, likely implemented as a UEFI driver, to control the THC Controller for pre-OS touch operations. More importantly, BIOS is responsible for key THC configuration operations.
P0237: 
P0238: Single and Dual Touch Screen Support:
P0239: As shown in the above diagram, the THC exposes 2 PCI devices, each with a BAR dedicated for an individual SPI bus. In this configuration the PCI bus driver will enumerate 2 device objects for which 2 instances (FDOs) of the QUICKSPI driver loads.
P0240: 
P0241: THC can also to be used for a single touch IC and single touch screen. This is, by far, the most common configuration OEMs will have. In this, most common usage, BIOS shall disable the unused THC and therefore expose only 1 PCI BDF for the OS to load a single instance of the QUICKSPI client driver.
P0242: 
P0243: # THC Initialization Flows
P0244: 
P0245: ### BIOS Initialization of the THC
P0246: BIOS initialization of the THC HW:
P0247: Previous to OS boot BIOS was responsible for the following controller initialization (details can be found in the THC BIOS writers guide):
P0248: - Port initialization based on OEM configuration. Unused THC-SPI ports shall be disabled by BIOS.
P0249: - Assign Class-Code/SCC
P0250: - PCI Configuration space initialization and BAR allocation.
P0251: - Cover management capabilities configuration such as clock gating, D0i2 enable disable, D0i2 entry latency,
P0252: - SAI policies
P0253: - LTR configuration
P0254: - GPIO expectations – not all THC external signals are used
P0255: -  RESET:  owns by GPIO/ACPI (instead of THC)
P0256: - Latencies such as Off duration, Power up to Reset delay, Post Reset Delay should be covered as well
P0257: -  vGPIO for WoT: used
P0258: -  vGPIO for SPB-Workaround:  not-used
P0259: - vGPIO for WoT: used
P0260: -  vGPIO for SPB-Workaround:  not-used
P0261: - TIC Interrupt line should be configured as level-triggered. In addition, Active low or Active High definition is vendor specific
P0262: - 
P0263: 
P0264: 
P0265: ### Device ID mapping
P0266: Reference: 
P0267: https://docs.intel.com/documents/ClientSilicon/PTL/global/PTL_PCD_South_Addr_BDF_DID_HAS/PTL_PCD_South_RegMaps.html
P0268: https://docs.intel.com/documents/ClientSilicon/LNL/global/LNL_SOC_South_Addr_BDF_DID_HAS/LNL_SOC_South_RegMaps.html [LINKS: https://docs.intel.com/documents/ClientSilicon/LNL/global/LNL_SOC_South_Addr_BDF_DID_HAS/LNL_SOC_South_RegMaps.html]
P0269: https://docs.intel.com/documents/pch_doc/MTLS/HAS/Chap06_MTP-S_RegMaps/Chap06_MTP-S_RegMaps.html [LINKS: https://docs.intel.com/documents/pch_doc/MTLS/HAS/Chap06_MTP-S_RegMaps/Chap06_MTP-S_RegMaps.html]
P0270: 
P0271: 
P0272: 
P0273: 
P0274: 

=== TABLE 5 (rows=7, cols=8) ===
  T5R000:  ||  || MTP-S || MTL SIMICS & P/M || LNL-M || PTL-Px/H || PTL-U/P
  T5R001: HIDSPI || Port #0 || 7F59 || 7E49 || A849 || E349 || E449 || 
  T5R002:  || Port #1 || 7F5B || 7E4B || A84B || E34B || E44B || 
  T5R003: IPTS || Port #0 || 7F58 || 7E48 || NA || NA || NA || 
  T5R004:  || Port #1 || 7F5A || 7E4A || NA || NA || NA || 
  T5R005: HIDI2C || Port #0 || NA || NA || A848 || E348 || E448
  T5R006: HIDI2C || Port #1 || NA || NA || A84A || E34A || E44A
=== END TABLE 5 ===

P0275: - 
P0276: - MTL/ARL:
P0277: - Lower DID:  IPTS INF
P0278: - Higher DID: QuickSPI INF
P0279: - 
P0280: - PTL/LNL/CPL+:
P0281: - Lower DID Quick I2C INF
P0282: - Higher DID: QuickSPI INF
P0283: 
P0284: 
P0285: ### ACPI Enumeration
P0286: 
P0287: - ACPI device objects for THC 0 and THC 1 shall be added by BIOS
P0288: - _ADR specifies the PCI Bus/Device/Function address 
P0289: - Configure the THC PCI Virtual Device ID for QUICKSPI mode
P0290: - Virtual interrupt will be defined in _CRS for wake. This Interrupt resource shall be defined as falling edge triggered as defined in HIDSPI spec
P0291: - Only active-low Chip-select line is supported on THC
P0292: - _RST method shall handle Reset line as active low as defined in HIDSPI spec
P0293: - RVP BIOS menu shall define policy via BIOS Init and ACPI to switch between IPTS and HIDSPI protocol
P0294: - BIOS shall define policy/setup menu for the following settings:
P0295: - Vendor specific DSM settings defined in HIDSPI spec
P0296: - DSM settings defined for THC
P0297: - Platform specific DSM settings
P0298: 
P0299:    {style: Normal (Web)}

=== TABLE 6 (rows=8, cols=6) ===
  T6R000: Field || Value || Mandatory | /Optional (M/O) || ACPI Object || Format || Comments
  T6R001: THC PCI Device Address || Platform specific || M || _ADR || Integer || Returns address of THC device on its parent bus (PCI).  | High word–Device #, Low word–Function #  | Example: Device 3, Function 2 is 0x00030002
  T6R002: Current Resource Settings || Platform specific || O || _CRS || Byte Stream || -GpoInt (virtual Gpio Interrupt) for wake | Edge triggered, Active  Low, ExclusiveAndWake | Example: GpioInt(Edge, ActiveLow, ExclusiveAndWake,PullUp 0, “\\_SB.GPI2”)
  T6R003: Device Specific Method || Vendor specific. GUID defined by HIDSPI spec. || M || _DSM ||  || This GUID defines a structure that contains device specific  | information as defined by HIDSPI spec.
  T6R004:  || Vendor specific. GUID defined by THC.  | [300D35B7-AC20-413E-8E9C-92E4DAFD0AFE] || M || _DSM ||  || This GUID defines a structure that contains device specific information  | as defined by HIDSPI spec.
  T6R005:  || Platform specific. GUID defined by THC.  | [300D35B7-AC20-413E-8E9C-92E4DAFD0AFE] || O || _DSM ||  || This GUID defines a structure that contains platform specific configuration or  | workarounds needed for THC. |  | Default LTR will be considered as infinite when _DSM returns the Active and Idle functions as unsupported. Any required Workarounds for Active LTR and Idle LTR values shall be supported via BIOS policy options.
  T6R006: Device Reset Method ||  || M || _RST ||  || ACPI 6.0 7.3.25 compliant device reset method, to be called by the HOST  | OS as an ACPI FLDR (function-level device reset) to reset the touch controller. |  | Refer to HIDSPI spec for details on reset line behavior. | Reset GPIO pad will be owned by BIOS and no longer be in native THC mode. |   | BIOS shall provide configurable policy for reset low hold time so that vendors can add the delay specific to their design.
  T6R007:  ||  ||  ||  ||  || Wake support | _S0W - This is needed, These are platform specific: _PS0/_PS3/_PRW | GPIOInt (Needed) - ExclusiveAndWake - sample code |     If (LNotEqual (THC_WAKE_INT0, 0)) { |       Name (_S0W, 3) |       Method (_CRS) { Return (TINT (THC_WAKE_INT0)) } |     }
=== END TABLE 6 ===

P0300: - 
P0301: ## QUICKSPI Driver Init Flows
P0302: 
P0303: ### QUICKSPI Driver
P0304: Installed via primary INF using new PCI SIG Class/Sub-class code. BIOS is responsible to expose the
P0305: ### AddDevice
P0306: 
P0307: 
P0308: 
P0309: Figure 5: HIDSCx Device Initialization
P0310: 
P0311: As specified by KMDF and HIDSCx requirements QUICKSPI driver shall perform the basic driver tasks:
P0312: - Set Driver Internal State
P0313: - Initialize Cx using HidSCxDeviceInitialize() to configure PnP and Power callbacks for the device
P0314: - Create WDF Device Object and Device Context
P0315: - Create Input WdfQueue object to receive IRP_MJ_READ requests from Cx. Choose Dispatch type as parallel. 
P0316: - Create Output WdfQueue object to receive IRP_MJ_WRITE requests from Cx. Choose Dispatch type as sequential.
P0317: - Configure Cx managed device (HidSCxDeviceConfigure DDI) to provide pointers to Input Queue, Output Queue, number of pending input requests to be pended in the input queue at a time and EvtResetDevice callback to Cx 
P0318: - Cx creates and initializes the Default Parallel I/O Queue to receive requests from hidclass
P0319: ### PrepareHw
P0320: PrepareHw is called by the KMDF infrastructure as a result of device resources being established. This could be the result of an initial system enumeration event or a resource re-balancing. While most initialization operations are contained in the D0Entry API, in PrepareHW the base driver maps its resources including the THC MMIO BAR and interrupt vectors, though interrupts are not enabled at this time.
P0321: ### QUICKSPI D0Entry
P0322: At its most basic level D0Entry requires to the driver to bring the controller from D3 into a D0 state. For THC, there are specific bits in which SW uses to go between D0 and D3 to do this (please refer to the HAS). 
P0323: 
P0324: 
P0325: ### TIC Reset Exit Flow (i.e., Host Initiated Reset)
P0326: 
P0327: QUICKSPI Driver Initialization Operations:
P0328: QUICKSPI Driver initialization occurs in 2 stages: TIC enumeration and initialization and DMA buffer allocation with associated DMA MMIO configuration. TIC enumeration is described in the following section. In order to execute the TIC enumeration the THC driver must execute PIO operations to the TIC registers. As long as PCI enumeration is complete, with the BAR programmed the THC driver can execute PIO operations. None of the THC sequencer or DMA engines need to be programmed to for the TIC enumeration stage.
P0329: 
P0330: Pre-Conditions:
P0331: THC is in D0, MMIO BAR has been mapped.
P0332: 
P0333: Touch ICs that are compliant with HIDSPI protocol are expected to provide a dedicated reset line that is driven by the host to reset the device. The reset line, which is normally high, will be pulled low by the host (using ACPI _RST control method defined under THC device scope) for at least 10ms to reset the device. HIDSCx initiates the Touch IC reset flow by invoking the EvtResetDevice callback implemented by the QUICKSPI client driver. 
P0334: 
P0335: Sequence of initialization steps that occur as part of the reset flow are:
P0336: - QUICKSPI driver ensures the THC is in D0 and the SPI bus is ready.
P0337: - QUICKSPI driver reads the SPI frequency, IO modes supported by the Touch IC from ACPI _DSM method and configures the THC controller
P0338: - QUICKSPI driver quiesces the TIC interrupts (if not already done)
P0339: - Before TIC is out of reset, QuickSpi driver starts by configuring interrupt mode as level triggered in THC (later in the flow switches to edge mode)
P0340: - HIDSCx invokes QUICKSPI client driver’s EvtResetDevice callback, which in turn invokes ACPI reset method to take the TIC out of reset. This should also clear the device state
P0341: - Within 1 second, the device signals an interrupt to the host. In response, THC reads the input report header and sends the reset interrupt as a non-data interrupt to QUICKSPI driver
P0342: - QuickSpi driver configures interrupt mode as edge triggered in THC 
P0343: - QUICKSPI driver processes the reset interrupt by issuing a PIO request to read the input report body containing device reset response
P0344: - QUICKSPI driver validates the reset response body and completes a request from the input report queue with device reset response
P0345: - HIDSPI Cx is expected to validate and handle the errors as described in the HIDSPI specification, some of which may include Cx resetting the device.  QuickSPI driver should validate the responses received from the TIC and generate log messages for ease of debug
P0346: - Open: Is Cx going to validate for the short packet errors and reset the device? Or, is this a responsibility of the QUICKSPI client driver?
P0347: 
P0348: Figure 6: HIDSCx Reset Flow
P0349: 
P0350: ### Read Device Descriptor
P0351: 
P0352:  [IMAGE]
P0353: 
P0354: Sequence of steps to read device descriptor:
P0355: - HIDSCx sends IRP_MJ_WRITE request to QUICKSPI Client driver to request for device descriptor (Output Report Type = 0x01 as defined in HIDSPI spec) 
P0356: - QUICKSPI driver writes the Output Report at the Output Report Address specified in ACPI tables, to request device descriptor from the Touch IC
P0357: - QUICKSPI client driver completes the Write Request with an appropriate status to indicate success along with request information field set to size of output buffer or indicate failure status. 
P0358: - The device prepares the input report containing device descriptor and generates an interrupt to the host within 1 second.
P0359: - Host using PIO operation to read the device descriptor from input report address specified in ACPI. Device descriptor format, shown below, is defined in section 6.1.1 of HIDSPI protocol specification
P0360: - QUICKSPI client driver completes one of the “ping-pong” IRP_MJ_READ requests from the Input Report Queue with input report body to the class extension.   
P0361: - Information field of the request should be set to the total bytes read from the device into the buffer (sizeof(HIDSCX_REPORT) + ReportContentLength) 
P0362: - In the case of any error reading the device descriptor from the TIC, QUICKSPI client driver shall complete the ping-pong IRP_MJ_READ request with an error code.
P0363: - QUICKSPI client driver reads sizes of input/output buffers from device descriptor response, allocates DMA buffers and initializes PRD tables.
P0364: 
P0365:  [IMAGE]
P0366: 
P0367:  [IMAGE]
P0368: 
P0369: 
P0370: D0 entry is called for the following system states:
P0371: Standard boot Flow:
P0372: - Prior to this flow, BIOS initialized the controller into a into a D0 state.
P0373: - Prior to the D0Entry entry-point, PrepareHW would have been called where TIC enumeration and MMIO setup occurs. Therefore, the THC must be in a D0-State.
P0374: - Architectural Requirement --> must ensure the controller is in D0.
P0375: - This flow also includes where the driver is disabled, removed or re-installed because the stack will be torn down in this event.
P0376: 
P0377: Resume flow:
P0378: - The system is exiting Sx or Modern Standby (S0iX).
P0379: - The previous driver state was D0Exit and the controller is in D3.
P0380: - For details on the behavior in the D0Entry following D0Exit please see the THC Driver Power Management section.
P0381: 
P0382: Subsequent sections describes the main THC HW capabilities which the QUICKSPI driver interacts with and initializes the THC HW. The below items are done for each TIC (up to two) on the platform.
P0383: 
P0384: QUICKSPI Client driver Read DMA Buffers Initialization and Usage:
P0385: The QUICKSPI client driver allocates read data buffers to receive various types of input report data (except device descriptor response) from the TIC. Most of the input report body read requests from the Touch IC including data, reset response, command response, get feature response, report descriptor, set feature response, set output report response, get input report response fall into this category.
P0386: 
P0387: QUICKSPI client driver’s use of RxDMA1 and RxDMA2:
P0388: In the QUICKSPI architecture, RxDMA1 engine is no longer used. RxDMA2 is associated with HID data and the THC HW has a read DMA engine and circular buffer dedicated for this engine. Vendor proprietary raw data format, unlike previous generation IPTS protocol, is not used in QUICKSPI implementation. 
P0389: 
P0390: QUICKSPI base driver will automatically allocate buffers and a PRD table for RxDMA2 on its own during the initialization flow, immediately after reading device descriptor response. 
P0391: 
P0392: QUICKSPI Client driver Use of the Circular Buffer
P0393: The THC HW circular buffer allows the THC RxDMA engines to determine the next free read buffer and begin DMA-ing to that buffer without SW interaction. It is the responsibility of the QUICKSPI driver to initialize the circular buffer and advance the circular buffer write pointers once the base driver has consumed the read buffer. The THC HW advances the read pointer once a read DMA is complete.
P0394: 
P0395: QUICKSPI Client driver Write DMA Usage and Initialization
P0396: The QUICKSPI driver automatically initializes the write DMA HW in this sequence. The QUICKSPI driver uses the Write DMA engine to write bulk data to the TIC. As write operations are synchronous requests from SW, no circular buffer exists to support the write DMA engine. The driver must manually start a write DMA operation and either poll for completion or wait for an interrupt. 
P0397:   {style: No Spacing}
P0398: ### Write DMA Init
P0399: The diagram below illustrates the write DMA registers and PRD structure. Unlike with the read DMA engines, the write DMA engine does not contain a circular buffer. The reason for this is that write DMAs are not executed via the HW sequencer. Rather, the write DMA operations are manually invoked via the QUICKSPI driver as a result of being requested by HIDSCx to send output (IRP_MJ_WRITE) requests to the TIC. Therefore, there is a single write DMA buffer associated with a single write DMA PRD.
P0400: 
P0401: Write DMA HW Initialization:
P0402: - QUICKSPI Driver determines the max write size based on wMaxOutputLength field of the Device Descriptor reported by Touch IC 
P0403: - QUICKSPI Driver allocates non-pageable virtual memory for the write buffer.
P0404: - QUICKSPI Driver requests the OS kernel to create an SGL (scatter-gather list) for the output buffer.
P0405: - QUICKSPI Driver allocates a physically contiguous memory buffer for the PRD table.
P0406: - QUICKSPI Driver converts the OS SGL to a PRD table and copies this to the contiguous memory region.
P0407: - QUICKSPI Driver initializes the THC MMIO space for the write data buffer DMA engine PRD tables.
P0408: 
P0409: During runtime operations, writes are accomplished by copying data to be written to the write buffer, and then by setting the Start bit. SW can use interrupts or poll on the Start bit for completion.
P0410:  [IMAGE]
P0411: Figure 7: THC Write Buffer Initialization
P0412: 
P0413: ### RxDMA2 Initialization
P0414: This section and the diagram below describe the read DMA and circular buffer theory of operation and initialization requirements for the THC HW and driver. 
P0415: 
P0416: Circular Buffer Details:
P0417: The following description applies to CPU buffers.
P0418: - In most cases we expect the CPU to process data faster than it is sent by THC. In rare cases SW processing will take longer than the data transfer across THC, resulting in a buffer overrun or touch frame being dropped.
P0419: - To mitigate this possibility host SW will allocate multiple data buffers in host memory that are represented by the multiple PRD tables.
P0420: - In order for HW to know which buffer is free (and for SW to indicate which buffers are free) a circular buffer shall be implemented.
P0421: - The CB (circular buffer) read pointer is controlled by HW.
P0422: - The CB write buffer is controller by SW.
P0423: - SW increments the CB to the amount of free buffers and if the HW is armed, via the Start bit, HW DMAs all the free buffers.
P0424: - When HW detects the write and read pointer are the same value it stops DMA-ing data until the write pointer is greater than the read pointer.
P0425: - An overrun bit indicates when SW has wrapped the write point over the size of the CB.
P0426: 
P0427: Typical Circular Buffer HW Operation Example:
P0428: For this example, SW allocates 4 raw data buffers and 4 PRD tables. This is just an example, as seen below 16 buffers will be in use.
P0429: - The read and write pointers are initialized to 0x0, thus the DMA engine will not run.
P0430: - SW moves the CB write pointer to a value of 0x80. This tells the HW that all 4 buffers are free.
P0431: - SW sets the Start bit.
P0432: - HW DMAs to all 4 PRD tables/raw data buffers. After each DMA completes, HW increments the read pointer. When the HW reaches a value of 0x3 for the read buffer and increments it again, the value will be 0x80 due to an increment of the overflow bit.
P0433: - SW detects buffer 0 is free (but buffers 1-3 are still in use) and increments the write pointer to 0x1.
P0434: - HW begins DMA-ing to buffer 0.
P0435: 
P0436: RxDMA Engine Usage Requirements:
P0437: The following are read DMA buffer and read PRD table allocation requirements for the QUICKSPI Driver:
P0438: - The QUICKSPI driver shall allocate 16 buffers to receive read data from the TIC.
P0439: - Each of the 16 buffers shall be allocated to the max data size as reported by the TIC, aligned and rounded up to a multiple of 4KB. The THC can support up to a 1MB buffer.
P0440: - The driver shall allocate 16 PRD tables, sized to hold enough PRD entries for worst-case fragmentation for the read data buffers. For example, if each read data buffer is 32KB, the driver will allocate 16 PRD tables with 8 entries in each of them. This will lead to wasted PRD entries in the case any of the 16 buffers is not fully fragmented (see below).
P0441: - For example, a buffer may be fully fragmented requiring the driver to use all 8 entries, while some read buffers may have zero fragmentation, requiring the driver to use only 1 entry.
P0442: - The driver will request the OS to build SGLs for the 16 read data buffers and initialize each PRD entry with SGL information from the OS.
P0443: - If all entries are sized and aligned to 4KB, the unused entries shall be initialized to 0x00. This will allow the SW to detect frame babble (where TIC sends more data than it should) via the invalid PRD-Entry error in the HW. It's unlikely that the frame babble interrupt error cause bit won't be set because memory will not be fully fragmented in most cases.
P0444: 
P0445: Notes:
P0446: - After a read DMA, the HW will update the length of the PRD entries to reflect the length of the data transferred. After consuming a read-buffer, the driver shall update the length back to the original length initialized at boot.
P0447: - Up to 64 PRD tables can be allocated. The number of PRD tables equals the number of raw data buffers.
P0448: - Max OS memory fragmentation will be at a 4KB boundary, thus to address 1MB of virtually contiguous memory 128 PRD entries are required for a single PRD Table.
P0449: - It is expected that SW allocates all the raw data buffers and PRD tables at host initialization. Host SW will de-allocate the buffers and PRD during runtime only if the OS kernel requests the THC device to be disabled or stopped. Re-allocation of the buffers may occur again if the THC device is re-enabled. Buffer allocation and de-allocation shall only occur when the HW is completely quiesced.
P0450: 
P0451: Read DMA HW Initialization Basic Flow:
P0452: - QUICKSPI Driver determines the max size of a frame by reading the reading the device descriptor provided by the Touch IC. A larger value from wReportDescLength and wMaxInputLength fields is then rounded up to a 4KB multiple to determine the max size of a frame.
P0453: - QUICKSPI Driver allocates 16 (this number may change) non-pageable memory buffers for HID data. The frame data could comprise anything defined in the HIDSPI spec as “Input Report Type” except for Device Descriptor
P0454: - Driver allocates physically contiguous memory for 16 PRD tables.
P0455: - Driver requests the OS kernel to create an SGL for each raw data buffer.
P0456: - Driver converts each SGL to a PRD table and copies this to the PRD contiguous memory region.
P0457: - Driver initializes the THC space for the RxDMA2 PRD tables.
P0458: - Driver resets the circular buffer read and writes pointers.
P0459: - Driver initializes the write pointer to the number of PRD tables - 1.
P0460: - Driver sets the RxDMA2 engine’s Start bit to a 1.
P0461: 
P0462: The DMA engine is now armed and waiting for the THC engine to fetch data from the Touch IC.
P0463:  [IMAGE]
P0464: 
P0465: Figure 8: HIDSCx Read DMA Initialization
P0466: 
P0467: ### Software RxDMA 
P0468: 
P0469: THC supports a SW triggered RXDMA mode to read the RX touch data from TIC. This SW
RXDMA is the 3rd THC RXMA engine with the similar functionalities as the existing two
RXDMAs, except for:
1. SW trigger
2. "TIC" interrupt cause register is ignored, DMA follows the RXDMA Control register including
the DMA length defined in the PRD entries.
3. INT_SW_DMA_EN1/2 is ignored.
3. No GuC support
4. No Counter support
Before SW starts a SW RX DMA, it shall stop the 1st and 2nd RXDMA, clear pointer reset
TPCPR and quiesce the device interrupt THC_DEVINT_QUIESCE_HW_STS =1.
For SW DMA, a normal flow is as following:
1. SW programs a SW RXDMA PRD table and RXDMA control register
2. THC SW starts a SW RX DMA
3. THC HW reads a frame based on the info in the SW RXDMA control register and associated
PRD
4. once completed, THC HW asserts a SW RXDMA interrupt to SW
P0470: 
P0471: SWDMA allows QuickSpi driver to initiate DMA Read transaction instead of HW interrupt handling. The original motivation for SWDMA was for THC stack to support SPB (Simple Peripheral Bus) architecture. Since then, however, plans have changed and the SPB architecture is no longer being pursued. With the introduction of I2C support in LNL, SWDMA will be used to support certain commands defined by hidi2c protocol. Please refer to QuickI2C SwAS for details on SWDMA usage. 
P0472: 
P0473: ### Timing based Frame Coalescing
P0474: 
P0475: In order to match competitors (e.g. iPAD) capability on upstreaming (to SoC) multiple input
frames at a time depending on application needs (e.g. display frame refresh rate), THC HW
will coalesce the SW interrupts to only generate SWI (SW interrupt). When there is no touch/pen input, THC will generate SWI on first frame. 
P0476: 
P0477: During a touch/pen report sequence, SW driver will program THC to generate SWI in a desirable cadence (e.g. 60Hz). RXDMA will need to start before interrupt as specified by the count-down timer. It supports SW fine-tuning of the count down timer for staying in sync with vsync. On low power system, this feature prevents SWI storm from swarming low power CPU
operating under DC. For vertically integration system, this can be done in touch controller
end-point. For horizontal platform, like IA, this feature allows THC get the same interrupt
coalescing with minimal/none vendor enabling commit. Refer to THC HAS for additional details
P0478: 
P0479: ### SW Controlled Coalescing with Converged Sync Event (LNL+)
P0480: 
P0481: Starting from LNL, THC added several new changes (covered in this section) to improve the accuracy of display and touch synchronization. This is done by either using an incoming HW display VBLANK/VSYNC from TCON or a timer emulated sync signal to THC. The timer emulated sync signal can be programmed by SW to trigger at the same cadence as display refresh rate.,
P0482: 
P0483: THC supports programming of the Sync source to be external vsync from TCON or timer emulation based on driver policy setting. This is done by programming the DISP_SYNC_EVT_SRC register. THC also supports a programmable delay after receiving sync event before a Sync interrupt is sent or coalescing begins. SW can choose the receive the Sync Event either immediately or after the programmed delay.
P0484: The sync event delay can be programmed using DISP_SYNC_DELAY and enabled using DISP_SYNC_COAL_DELAY_EN registers.
P0485: 
P0486: THC also supports timestamping of the sync event (VSYNC from TCON + timer emulated sync) as well as timestamping of TIC input reports. The timestamp information will be passed to an upper level filter driver for value added features such as Smoothing of incoming touch data based on the sync event. Refer to Touch Smart Filter SwAS for details on this interface.
P0487: 
P0488: Refer to the section titled “SW Controlled Coalescing with Converged Sync Event” in THC HAS for additional details on register definition and HW FSM.
P0489: 
P0490: 
P0491: ### Interrupt Enable
P0492: Interrupt enable is sent by the OS to inform the QUICKSPI driver that it can enable interrupts. Interrupts need to be enabled in THC HW before the QUICKSPI starts resetting the HIDSPI device.
P0493: 
P0494: ### Global Interrupt Enable
P0495: 
P0496: THS supports MSI and Line Based interrupt schemes. From LNL and onward, a global enable/disable bit is supported to simplify interrupt handling in the driver.
P0497: Refer to THS HAS for details on Enable THC Interrupt (GBL_INT_EN) bit defined in the register THC Interrupt Enable Register (THC_M_PRT_INT_EN)
P0498: 
P0499: 
P0500: 
P0501: 
P0502: 
P0503: ## QUICKSPI Driver HID Operations
P0504: 
P0505:   {style: Plain Text}
P0506: Figure 9: QUICKSPI Driver HID Operations
P0507:   {style: Plain Text}
P0508: Once the QUICKSPI driver is up and running, OS HID stack initializes and does enumeration of the touch devices on its own. This process starts with a fetch of the device descriptor from the QUICKSPI Driver to determine the determine attributes, sizes of various input reports, output reports, max fragment length etc. Following this, the report descriptor is fetched by the Cx to determine enumerate all the HID top-level collections for Touch, Pen, Heatmap and any other HID devices etc.  {style: Plain Text}
P0509:   {style: Plain Text}
P0510: At this point the Class driver will submit its input report request via sending IRP_MJ_READ IOCTL request to the QUICKSPI Client driver’s InputQueue which arms the QUICKSPI driver and allows the HIDSCx to consume an input report. While HID reports will be returned asynchronously via to the class driver, Ouput Reports, Set Feature Reports and Get Feature Requests will be sent synchronously.  {style: Plain Text}
P0511: 
P0512: # QUICKSPI Driver Runtime Operations
P0513: 
P0514: ## QUICKSPI Read Data Flows
P0515: 
P0516: ### Input Report Data Flow
P0517: The following is the primary data flow with or without feedback data.
P0518: 
P0519: Basic Flow:
P0520: - Touch IC interrupts the THC Controller using an in-band THC interrupt.
P0521: - THC Sequencer reads the input report header by transmitting read approval as a signal to the TIC to prepare for host to read from the device. 
P0522: 
P0523: Read Approval and Input Report Header format shown below as defined in the HIDSPI spec. Note: Input Report Header Address is vendor specific and it is defined in ACPI _DSM method.
P0524:  [IMAGE]
P0525: 
P0526:  [IMAGE]
P0527: - THC Sequencer executes a Input Report Body Read operation corresponding to the value reflected in “Input Report Length” field of the Input Report Header.
P0528: - THC DMA engine begins fetching data from the THC Sequencer and writes to host memory at PRD entry 0 for the current CB PRD table entry. This process continues until the THC Sequencer signals all data has been read or the THC DMA Read Engine reaches the end of it's last PRD entry (or both).
P0529: - The THC Sequencer checks for the “Last Fragment Flag” bit in the Input Report Header. If it is clear, the THC Sequencer enters an idle state.
P0530: - If the “Last Fragment Flag” bit is enabled the THC Sequencer enters End-of-Frame Processing.
P0531: 
P0532: THC Sequencer End of Frame Processing:
P0533: - THC DMA engine increments the read pointer of the Read PRD CB, sets EOF interrupt status in RxDMA 2 register (THC_M_PRT_READ_DMA_INT_STS_2)
P0534: - If THC EOF interrupt is enabled by the driver in the control register (THC_M_PRT_READ_DMA_CNTRL_2), generates interrupt to software
P0535: 
P0536: Host Processing, Following EOF:
P0537: - QUICKSPI driver dequeues one of the “ping-pong” read (IRP_MJ_READ) requests that was forwarded to the Input Report Queue by the class extension 
P0538: - QUICKSPI driver copies the returned input report body from the PRD buffer to the output buffer of the read request and completes the read request. The information field of the request should be set to sizeof(HIDSCX_REPORT)+ReportContentLength
P0539: - QUICKSPI driver validates various fields of Input Report Header such as Input Report Length, Sync Constant, Last Fragment Flag etc. In case of any protocol or other transfer errors, QUICKSPI driver signals them to the Cx by completing pending read request with a failure status code. Cx may then call the QUICKSPI driver provided reset callback to reset the device
P0540: - After a read request gets completed by QUICKSPI driver, class extension will send another request to the input report queue
P0541: - QUICKSPI Driver increments the write pointer of the Read PRD CB.
P0542: 
P0543: ### Input Reports
P0544: Input Reports are unidirectional reports that are sent from Device to Host. Refer to the HIDSPI protocol specification for more details. Read request IRP_MJ_READ is the primary mechanism for the Windows HID stack to receive input reports from the Touch IC. The read requests are sent by the HIDSCx to the InputReportQueue in ping-pong fashion, utilizing a number of configurable buffers (specified by QUICKSPI Client driver in NumberOfInputReportRequestsToPend) to optimize data transfers. After a request is completed, another read request will be sent down to the device, allowing for continuous reporting of data. The read request is sent by the Cx to the QUICKSPI driver after the stack has initialized. When this actions occurs for the first time it is a signal from the Class driver that it is ready to receive input buffers. 
P0545: ### Output Reports
P0546: Output reports are unidirectional reports that are sent from Host to Device. Refer to the HIDSPI protocol specification for more details. When the Host (refers to the hid software stack above QUICKSPI Client driver) has data that needs to be sent to the Device, it sends output report to the QUICKSPI Client driver. The client driver will then write the output report to the Device’s Output Report Address specified in ACPI _DSM control method to either request data from the device or send a command to the device.  QUICKSPI driver uses write DMA operation to send the output reports to the Touch IC. 
P0547: 
P0548:  [IMAGE]
P0549: 
P0550:  [IMAGE]
P0551: Generic Output Report Flow:
P0552: - HIDSCx sends output request (IRP_MJ_WRITE) to the QUICKSPI client driver. Header of the output report buffer provided by Cx is shown as HIDSPICX_REPORT definition above. The first 4 bytes that include Opcode and Output Report Address constitute the output report header. 
P0553: - QUICKSPI client driver converts Cx provided data HIDSPICX_REPORT (starting from Output Report Type) into the output report body and copies it to THC’s write DMA buffer. 
P0554: Important Notes: 
P0555: - Content ID field shall be 0 for descriptor requests. It will contain Report ID for get feature, set feature, input and output reports. For commands, Content ID will contain a command opcode
P0556: - ContentLength: This field specifies the size of content field. It does not include the size of any other fields including Output Report Type, Content ID, or Content Length. 
P0557: - Pad Bytes: QUICKSPI driver adds 0-3 bytes to the end of the output report such that the total length of the output report is a multiple of 4 bytes
P0558: - QUICKSPI Driver sets the Start bit in the THC Write DMA Control register.
P0559: - THC TX-DMA HW sends output report header followed by output report body to the THC Core controller which starts sending data to vendor specific Output Report Address configured in ACPI _DSM control method.
P0560: - HW completes DMA, clears the Start bit, sets the completion status bit, and signals an interrupt to the SW. Unlike read DMA operations, write DMA only supports single PRD execution.
P0561: - QUICKSPI Driver reads the THC Write Interrupt Status register and clears the Status bit.
P0562: - Touch IC consumes the output report and asserts an interrupt within 1 second of consuming the bus transaction
P0563: - THC will process the interrupt as explained in the section “Input Report Data Flow”
P0564: - Note:
P0565: - By default, all Touch ICs are required to acknowledge output reports (except Set Power Sleep and Set Power Off commands). 
P0566: - Some Touch IC’s may set the “NoOutputReportAck” flag in the Device Descriptor, in which case the device does not acknowledge output reports (output report type=0x5).  This flag is only recommended for devices that require multiple output reports to be received during transmission of fragmented input report.
P0567: - For some output reports (get feature, device descriptor, report descriptor, commands), the host shall always expect an input report that contains data. For other output reports, the host expects an empty input report where the input report type indicates it is a response and Content field of input report body contains no data.
P0568: 
P0569: ### Commands
P0570: 
P0571: Commands are issued by the Cx as Output Reports with content type set to 0x7. Hence, the same output report processing flow applies to processing commands. Cx sets the content id field of the output report containing the command to the command ID specified in the list below. The device shall respond to a command (except Set Power SLEEP and Set Power OFF commands) by asserting the interrupt line and making available an input report of type 0x04. The Content ID field must match the content ID of the command sent by the host.
P0572: 
P0573:  [IMAGE]
P0574: ### Quiescing the THC
P0575: HIDSPI protocol requires the TIC vendors to support host writes between incoming fragments from the device. Therefore, unlike the IPTS protocol, there is no need to Quiesce the incoming interrupts before performing the write operation. Scenarios that require TIC interrupts to be quiesced are:  
P0576: 
P0577: - During Host Initiated Reset flow, before the TIC is fully powered up and has taken control of the interrupt line
P0578: - During runtime operations when the Read DMA buffers available for incoming interrupts are below the threshold
P0579: - During D0Exit flow, before THC enters into D3 state
P0580: - QuickSpi driver shall not use Quiesce_En within its ISR and DPC to serialize operations
P0581: 
P0582: Known Issue: On platforms prior to LNL, there is a known issue in THC HW where THC can process the interrupt edge transition twice, first before the interrupt is quiesced and later after the interrupt is unquiesced. This happens when the Device FW is slow in de-asserting the interrupt line. While this issue is being fixed in LNL THC, based on current assessment, the impact on existing platforms to currently supported IHVs is minimal. Specifically, with IHVs that have started their implementation with IPTS protocol, the Device FW generally de-asserts the interrupt line before the CS# de-assertion. Therefore, after a subsequent Unquiesce operation, THC notices the interrupt line is already high and doesn’t process the interrupts twice. There is another known issue that needs to be taken into consideration. Before the Touch IC is powered up and takes control of the interrupt line. During this time, the edge transitions on the interrupt line are unreliable as the interrupt line is not stable yet. To avoid misinterpreting these inaccurate edge transitions as interrupts, QuickSpi driver should configure the interrupts as Level triggered for the first interrupt, and then switch to edge triggered after the initial reset interrupt is received.
P0583: 
P0584: ### Raw Interrupt Status Behavior
P0585: Starting from LNL, THC supports the “THC Device Raw Interrupt Status” reporting feature. This requires software to enable the DEV_RAW_INT_EN register bit. When THC detects the external interrupt (i.e., level/edge, polarity etc.), it sets DEV_RAW_INT_STS register bit and sends an MSI to SW if the corresponding DEV_RAW_INT_EN bit. The setting of STS bit and sending MSI to SW is expected to be independent of where interrupts are quiesced or not (i.e., even if THC_DEVINT_QUIESCE_EN is set, Raw interrupt MSI should be sent to SW). 
P0586: 
P0587: Note: On LNL, there is an RTL issue that prevents MSI from being sent if external device interrupts are quiesced. The following workaround has been agreed on LNL and PTL.
P0588: - If Raw_INT_STS MSI is needed : Quiesce should be off
P0589: - If RAW_INT_STS MSI is not needed , just plan to read : hardware should come out of D0i2 and check interrupt and set RAW_INT_STS
P0590: - For line level-triggered interrupt, if TIC does not toggle the line interrupt between uframe/frames, this bit will not be set for the subsequent level interrupts even SW clears this bit.
P0591: 
P0592: ### HW/SW Interrupt Handling Behavior
P0593: The following flow chart pulls the HW Sequencer and DMA behavior into one diagram. As can be seen, all decision branches are based on Touch IC register reads of the Status and Frame Characteristics Registers. This diagram is informative and for details on the THC HW, please consult the HAS.
P0594: ### HW Sequencer Behavior
P0595:  [IMAGE]
P0596: Figure 10: HW Sequencer Flow Chart  
P0597: 
P0598: ### SW Interrupt Behavior
P0599: 
P0600:   [IMAGE]
P0601: Figure 11: SW Interrupt Processing Flow  
P0602: 
P0603: ### ISR Behavior
P0604: THC HW supports both MSI and Line Interrupts, however, QUICKSPI will enable MSI for hardware interrupts. THC HW and SW use handshaking (referred to as Per-Vector Masking in PCI express base specification) to co-ordinate exactly when new interrupt messages are generated. With per-vector masking, when the software interrupt service routine begins, it masks all the interrupt sources (i.e., disable interrupt enable bits) to avoid spurious interrupts. After the DPC processes all the interrupt conditions that it is aware of, it unmasks all the interrupt sources (i.e., re-enable the interrupt enable bits). If new interrupt conditions remain, THC HW is required to generate a new interrupt message, guaranteeing that no interrupt events are lost. Here is basic flow that works for both MSI and Line Interrupt  {style: No Spacing}
P0605:   {style: No Spacing}
P0606: Basic Flow:
P0607: - Check for THC Interrupt Source (RxDMA1\2 EOF, TxDMA CML, NonDMA Int, PIO TSS Done)
P0608: - Mask all interrupt sources via the Global Interrupt Enable bit. The driver also has the option of selectively masking interrupt sources using individual IE Bits to avoid additional interrupts from HW
P0609: - Queue DPC to process pending interrupts
P0610: ### DPC Behavior
P0611: Basic Flow:
P0612: - Read THC Read DMA Interrupt Status Register
P0613: - If error status is set quiesce DMA and process error (DMA should be stopped anyway)
P0614: - If EOF_INT_STS is set, the input report is complete so process it.
P0615: - If NONDMA_INT_STS is set, it's a non-data interrupt.
P0616: - Unmask all Interrupts sources via Global IE bit. Alternatively, unmask individual IE Bits. 
P0617: 
P0618: 
P0619: ### Interrupt Locks
P0620: Due to race condition that can be happened once IE are enabled in DPC, the race condition is that ISR clear the IE and DPC set them.
P0621: 
P0622: DPC acquired the ISR look (Wdf Interrupt Lock) before Enabling the IE bits and release it after all the bits are set. 
P0623: ### Interrupt Locks
P0624: 
P0625: 
P0626: ### Throttling
P0627: HIDSCx pends a number of input requests in Client driver’s Input Report Queue. Number of requests to pend will be configured by the QUICKSPI client driver during initialization phase by specifying it in the NumberOfInputReportQuestsToPend field. This value should match with the number of PRD ring buffers configured in THC, which is 16 at this time. If Touch IC is sending a larger burst of HID reports the OS might not able to catch up with this speed, therefore the QUICKSPI Driver will throttle if the free buffer are down to 8 (half size)
P0628: Then the QUICKSPI driver will Quiesce the THC Device, the until all buffers will be free. Every time QUICKSPI Driver will get a new input report request, the driver will perform a read from the THC PRD buffers.
P0629: 
P0630: ## Error Handling Operations
P0631: 
P0632: Figure 12: QUICKSPI Error Handling Operations
P0633:   {style: Plain Text}
P0634: This diagram illustrates the error handling specific to THC HW and Touch IC reported errors. Use-case specific errors are detailed in their respective sections.   {style: Plain Text}
P0635: Unused-errors - The following THC errors are not implemented by either the SW or HW:  {style: Plain Text}
P0636: - Write DMA errors
P0637: - Fatal Errors
P0638: 
P0639: QUICKSPI Driver interrogates the Interrupt Status transaction errors to acquire error information for the following error types:
P0640: - Invalid PRD Entry Error - This is a SW programming error which likely cannot be recovered from.
P0641: - Frame babble errors - This is a TIC error that can be recovered from. It indicates that the data size indicated in the input report header is larger than the PRD table size (max size of input report indicated in the device descriptor). As shown in the diagram, Frame Babble may manifest itself as an Invalid PRD error.
P0642: - Short Packet Protocol Errors (Invalid input report header) - This is a TIC error that can be recovered. Short packet errors occur when the host or device does not return number of bits identified in the HIDSPI protocol request or length field. Host checks for invalid data by checking sync field and other fields of input report and initiates a reset of the device.
P0643: - PRD RxBuffer Overrun Error - This is a system-SW level error that can be recovered from.
P0644: - THC Rx Buffer Overrun - This is an IOSF error generated when the fabric cannot keep up with the traffic from the TIC.
P0645: - SW Sequencing (AKA PIO) Error - This is a SW bug that likely cannot be recovered from.
P0646: - Protocol Errors – 
P0647: 
P0648: All the above errors shall be programmed by the QUICKSPI client driver to stop the DMA operations in the THC. All these events would result in a TIC Reset.
P0649: ### SW Sequencing (PIO) Error
P0650: A SW sequencing error occurs when SW sends B2B PIO operations before a previous PIO operation completed. This is an indication of a programming bug which likely cannot be recovered from. SW should log an error with the OS.
P0651: 
P0652: In response the QUICKSPI driver shall:
P0653: - Reset TIC to ensure it is in a clean state because Touch IC is in an unknown state.
P0654: - Cleanup, restart DMA
P0655: - Complete Cx input report request with a reset response
P0656: 
P0657: ### Read DMA Errors
P0658: Short Packet Protocol Errors (Invalid input report header):
P0659: - Occurs when the TIC places bad parameters in the input report header
P0660: - In response the QUICKSPI executes either no read operation or reads whatever data is on the bus
P0661: - QUICKSPI driver shall detect invalid fields of input report header and execute a reset of the TIC to resolve.
P0662: 
P0663: Frame Babble Error Interrupt:
P0664: - Occurs when the data to be read from the TIC is larger than the PRD receive buffer.
P0665: - The QUICKSPI driver will invoke Reset Flow
P0666: 
P0667: PRD Table Overflow:
P0668: - This occurs when the Read and Write Pointers for CB are the same, when a touch-read interrupt occurs.
P0669: - The sequencer requests the DMA to begin data transfer, but the DMA engine does not.
P0670: - The THC Controller will drain the data from the Touch IC but not DMA the data to the host.
P0671: - When the write pointer is moved by the host DMA resumes
P0672: - The QUICKSPI driver will invoke Reset Flow
P0673: 
P0674: THC Buffer Overrun:
P0675: - This occurs when the TIC sends data faster than the THC Controller/host can handle due to IOSF bottleneck, etc.
P0676: - The QUICKSPI driver will invoke Reset Flow
P0677: 
P0678: Invalid PRD Entry:
P0679: - This occurs when the length of the PRD entry is 0.
P0680: - This is a SW bug and cannot be recovered from.
P0681: 
P0682: 
P0683: Read DMA Engine reaches the end of the PRD entry list:
P0684: - DMA engine halts, interrupts with an error.
P0685: 
P0686: Write DMA Engine Write Length Error:
P0687: - Write Length field is greater than the PRD entries account for.
P0688: - Error interrupt is specified with specific error flagged in the Write DMA Error Register.
P0689: 
P0690: ## THC LTR settings
P0691: The Doze power state is used for optimizing system power when user is idle and system is running.   Touch IC should be lower user input scanning rate to conserve power (while meeting OS and OEM first input report latency requirements).   
P0692: 
P0693: ### Driver Init
P0694: - During Reset flow Active LTR Should be Set and Enabled and LP LTR should not be Enabled.
P0695: 
P0696: LTR default values are:
P0697: - Active 
P0698: - Value = 1 msec (can be override via ACPI _DSM control method). 
P0699: - Scale = 2
P0700: - Low Power (LP) 
P0701: - Not Enabled
P0702: ### THC D3
P0703: - When THC enters D3 either due to Monitor Off or other OS events , Touch IC will be placed in reset (except when Touch is placed into Wakeable mode) and Touch IC is not expected to generate any interrupts to Host. Therefore, Active and Low Power LTR can both be disabled in THC. 
P0704: 
P0705:   {style: No Spacing}
P0706: ## Tap to Wake
P0707: Tap to wake provide a mechanism to wake the device (Platform) from Modern Standby from the TIC, for example by tapping twice on the screen 
P0708: ### Tap to Wake (Wakeable Mode) Entry
P0709: in Wakeable mode the TIC is move to a special power state and it is NOT being reset:
P0710: - OS decided to enter to Modern Standby (MS)
P0711: - OS HID class stack send wake wait request to the QUICKSPI Driver.
P0712: - In Windows:
P0713: - If driver was able handle the Wait Wake IRP it should pass it down to the next level driver. If not, it should complete it with error.
P0714: - Windows Wait Wake IRP (https://docs.microsoft.com/en-us/windows-hardware/drivers/kernel/irp-mn-wait-wake) [LINKS: https://docs.microsoft.com/en-us/windows-hardware/drivers/kernel/irp-mn-wait-wake]
P0715: - https://docs.microsoft.com/en-us/windows-hardware/drivers/kernel/understanding-the-path-of-wait-wake-irps-through-a-device-tree [LINKS: https://docs.microsoft.com/en-us/windows-hardware/drivers/kernel/understanding-the-path-of-wait-wake-irps-through-a-device-tree]
P0716: - 
P0717: - One QUICKSPI Driver get the Wait Wake Request, QUICKSPI driver marks Driver Internal State as entering into Wakeable Mode
P0718: - Upon Cx receiving request, QUICKSPI client driver sends command (via Output Report) to Set TIC Power state to Sleep 
P0719: - OS moves QUICKSPI Driver to D3
P0720: - QUICKSPI driver completes D3 Entry Flow.
P0721: ### Tap to Wake (Wakeable Mode) Exit
P0722: - TIC send wake interrupt to THC HW
P0723: - ACPI and OS HID Class wake the platform from MS
P0724: - QUICKSPI driver receives D0 Entry and detects that it is in Wakeable mode 
P0725: - Upon Cx receiving request, QUICKSPI client driver sends command (via Output Report) to Set TIC Power state to ON 
P0726: - Then continue without doing any TIC reset flow. 
P0727: 
P0728: 
P0729: 
P0730: 
P0731: # QUICKSPI Driver Teardown Flows
P0732: 
P0733:   {style: Plain Text}
P0734: Figure13: QUICKSPI Driver Teardown Flows  {style: Plain Text}
P0735: 
P0736: The above diagram illustrates the driver teardown flow which is the inverse of the initialization flow. There are various reasons for invoking this entire flow (or a subset of this flow). Depending on the subset of the flow only a portion of the actions for teardown may be taken, or a complete teardown may occur. For example:  {style: Plain Text}
P0737: - When the driver is disabled in the Device Manager, interrupts will be disabled the device will enter Dx, and ReleaseHW will be called. 
P0738: - In all cases the TIC interrupts will will be quiesced by the QUICKSPI driver.
P0739: ## Full Quiesce Operation
P0740: A full quiesce operation occurs on driver teardown and consists of the following:
P0741: - QUICKSPI driver waits for the TIC to be quiesced.
P0742: - QUICKSPI driver waits for THC to be quiesced.
P0743: # QUICKSPI Driver Power Management
P0744:  [IMAGE]
P0745:   {style: Plain Text}
P0746: Figure 14: QUICKSPI Driver D3 Entry/Exit
P0747: The diagram illustrates the power flows managed by various entities for the THC:  {style: Plain Text}
P0748: BIOS:  {style: Plain Text}
P0749: - BIOS is responsible for initializing the THC HW when entering S0 from and Sx state.
P0750: 
P0751: PMC:
P0752: - The PMC is responsible for saving and restoring the THC MMIO space when entering and exiting modern standby.
P0753: 
P0754: QUICKSPI Driver:
P0755: - The QUICKSPI driver is responsible for all the D0 entry and exit flows that result from Sx or Modern standby entry and exit.
P0756: - The QUICKSPI Driver D0 entry and exit flows are defined in the initialization portion of this specification. In summary, these flows are related to DMA engine initialization, TIC initialization, etc.
P0757:  [IMAGE]  {style: Plain Text}
P0758: Figure 15: TIC and THC Power States
P0759: This state machine shows the power states for the THC which are separately defined from power states of the THC-TIC.   {style: Plain Text}
P0760:   {style: Plain Text}
P0761: THC Power States:  {style: Plain Text}
P0762: Controller D0/D0-Idle and Controller D0i2:  {style: Plain Text}
P0763: - The THC autonomously switches between D0 and D0i2 depending on usage
P0764: 
P0765: Controller D3:
P0766: - The QUICKSPI Driver is responsible for switching the THC between D0 and D3
P0767: 
P0768: Touch IC Power States:
P0769: Please see the HIDSPI protocol specification for information on Touch IC power states.
P0770: ## QUICKSPI Driver D0Exit
P0771: Upon receiving EvtDeviceD0Exitcallback from KMDF, THC driver would do the following:
P0772: - Quiesce TIC by sending Set Power OFF command upon output receiving the output report from HIDSCx class extension 
P0773: - Quiesce THC HW
P0774: - Clear RxDMA2 START bit and free-up PRD allocations.
P0775: - Disable Interrupts
P0776: - Place the THC into D3.
P0777: 
P0778: Note:
P0779: - Skip steps 1 through 3 if touch was already disabled (due to LID close or monitor off).
P0780: 
P0781: ## Idle support
P0782: In order to support Idle and Modern Standby flows in QUICKSPI Driver, the driver need to tell HIDClass to use Enhanced Power Management, this is done by adding “EnhancedPowerManagementEnabled” to the registry via INF. This causes the hidclass (power policy owner) of HID devices to transition the device into D3 state when the primary/internal monitor is turned off either explicitly or due to the system display timeout policy.
P0783: Furthermore, the following key “EnhancedPowerManagementUseMonitor” is used due to PMC bug, blocking from CPU to be in C8.
P0784: 
P0785: ## Driver Production Debug Features
P0786: 
P0787: ## Registry Keys
P0788: There are several registries that help debug and Workaround issues in production:
P0789: 
P0790: - IO_Mode_Override – Select between Single, Dual, and Quad (0, 1, 2)
P0791: - SPI_Frequency_Override – Override MAX_SPI_FREQUENCY_SUPPORTED value reported by TIC
P0792: - TxDMA_Override – If 1 then would use PIO instead of TxDMA.
P0793: 
P0794: 
P0795: 
P0796: 
P0797: # TO DO (Additional Sections)
P0798: - Enhancements to support Smart Filter driver
P0799: - Known failure modes and signatures
P0800: - Debug hooks
P0801: - Telemetry hooks
P0802: - KPIs metrics (ISR/DPC duration)
P0803: - Cross check IPTS swAS for any missing section (that need equivalent)
P0804: - R/W race condition expectation/handling
P0805: - No Doze support
P0806: 
P0807: # Appendix
P0808: 
P0809: ## Sample ASL
P0810: 
P0811: -   Name(_ADR, THC_ADR)
P0812: -   Name(RSTL, 0) // Reset SW lock
P0813: - 
P0814: -   // _DSM - Device-Specific Method
P0815: -   //
P0816: -   // Arg0:    UUID       Unique function identifier
P0817: -   // Arg1:    Integer    Revision Level - Will be 2 for HidSpi V1
P0818: -   // Arg2:    Integer    Function Index (0 = Return Supported Functions)
P0819: -   // Arg3:    Package    Parameters
P0820: -   //
P0821: -   Method (_DSM, 4, Serialized, 0, UnknownObj, {BuffObj, IntObj, IntObj, PkgObj}) {
P0822: -     If (PCIC(Arg0)) { Return(PCID(Arg0,Arg1,Arg2,Arg3)) }
P0823: -     If (LEqual (THC_MODE, 0x1)) {
P0824: -       If(LEqual(Arg0,ToUUID("6E2AC436-0FCF-41AF-A265-B32A220DCFAB"))) {
P0825: -         //
P0826: -         // Switch on the function index
P0827: -         //
P0828: -         switch(ToInteger(Arg2)) {
P0829: -           case(0) {
P0830: -             // Switch on the revision level
P0831: -             switch(ToInteger(Arg1)) {
P0832: -               case (2) {
P0833: -                 // HidSpi v1 : Functions 0-6 inclusive are supported (0b01111111)
P0834: -                 Return (Buffer() {0x7F})
P0835: -               }
P0836: -               default {
P0837: -                 // Unsupported revision
P0838: -                 Return(Buffer() {0x00})
P0839: -               }
P0840: -             }
P0841: -           } // End case0
P0842: -           case(1) {
P0843: -             ADBG ("THC THC_INPUT_REPORT_HEADER_ADDRESS")
P0844: -             Return (ToInteger (THC_INPUT_REPORT_HEADER_ADDRESS))
P0845: -           }
P0846: -           case(2) {
P0847: -             ADBG ("THC THC_INPUT_REPORT_BODY_ADDRESS")
P0848: -             Return (ToInteger (THC_INPUT_REPORT_BODY_ADDRESS))
P0849: -           }
P0850: -           case(3) {
P0851: -             ADBG ("THC THC_OUTPUT_REPORT_ADDRESS")
P0852: -             Return (ToInteger (THC_OUTPUT_REPORT_ADDRESS))
P0853: -           }
P0854: -           case(4) {
P0855: -             ADBG ("THC THC_READ_OPCODE")
P0856: -             Name(BUF4, Buffer(1) {})
P0857: -             Store(ToBuffer (THC_READ_OPCODE), Local0)
P0858: -             Store(DerefOf(Index(Local0, 0)), Index(BUF4,0))
P0859: -             Return (BUF4)
P0860: -           }
P0861: -           case(5) {
P0862: -             ADBG ("THC THC_WRITE_OPCODE")
P0863: -             Name(BUF5, Buffer(1) {})
P0864: -             Store(ToBuffer (THC_WRITE_OPCODE), Local1)
P0865: -             Store(DerefOf(Index(Local1, 0)), Index(BUF5,0))
P0866: -             Return (BUF5)
P0867: -           }
P0868: -           case(6) {
P0869: -             /*
P0870: -             Bit 0-12: Reserved
P0871: -             Bit 13: SPI Write Mode.
P0872: -              0b0 - Writes are carried in single SPI mode
P0873: -              0b1 - Writes are carried out in Multi-SPI mode as specified by bit 14-15
P0874: -             Bit 14-15: Multi-SPI Mode
P0875: -              0b00 - Single SPI Mode
P0876: -              0b01 - Dual SPI Mode
P0877: -              0b10 - Quad SPI Mode
P0878: -              0b11 - Reserved
P0879: -             */
P0880: -             ADBG ("THC THC_FLAGS")
P0881: -             Return (ToInteger (THC_FLAGS))
P0882: -           }
P0883: -           default {
P0884: -             // Unsupported function index
P0885: -             Return (Buffer() {0})
P0886: -           }
P0887: -         } //EndSwitch
P0888: -         //
P0889: -         // No functions are supported for this UUID.
P0890: -         //
P0891: -         Return (Buffer() {0})
P0892: -       } //EndIfUUID
P0893: -       If(LEqual(Arg0,ToUUID("300D35B7-AC20-413E-8E9C-92E4DAFD0AFE"))) {
P0894: -         switch(ToInteger(Arg2)) {
P0895: -           case(0) {
P0896: -             // Functions 1-3 inclusive are supported (0b00000111)
P0897: -             Return (Buffer() {0x7})
P0898: -           }
P0899: -           case(1) {
P0900: -             ADBG ("THC THC_FREQUENCY")
P0901: -             /*
P0902: -             Bit 0-2: SPI Frequency
P0903: -               011 - 40MHz (Default)
P0904: -               100 - 30MHz
P0905: -               101 - 24MHz
P0906: -               110 - 20MHz
P0907: -               111 - 17MHz
P0908: -               Others - Reserved
P0909: -             Bit 3: Reserved Zero
P0910: -             Bit 4-15: Reserved
P0911: -             */
P0912: -             //Bit3: LimitPacketSize - When set, limits SPI read & write packet size to 64B. Otherwise, THC uses max packet size of 2KB for SPI Read and Write ) PCH:RestrictedContent
P0913: -             Return (ToInteger (THC_FREQUENCY))
P0914: -           }
P0915: -           case(2) {
P0916: -             ADBG ("THC THC_LIMIT_PACKET_SIZE")
P0917: -             /*
P0918: -             Bit 0: LimitPacketSize
P0919: -               When set, limits SPI read & write packet size to 64B.
P0920: -               Otherwise, THC uses Max Soc packet size for SPI Read and Write
P0921: -               0 - Max Soc Packet Size
P0922: -               1 - 64 Bytes
P0923: -             Bit 1-31: Reserved
P0924: -             */
P0925: -             Return (ToInteger (THC_LIMIT_PACKET_SIZE))
P0926: -           }
P0927: -           case(3) {
P0928: -             ADBG ("THC THC_PERFORMANCE_LIMITATION")
P0929: -             /*
P0930: -             Bit 0-15: Performance Limitation
P0931: -               Minimum amount of delay the THC/QUICKSPI driver must wait between end of write operation
P0932: -               and begin of read operation. This value shall be in 10us multiples
P0933: -               0 - Disabled
P0934: -               1 - 65535 (0xFFFF) - up to 655350 us
P0935: -             Bit 16-31: Reserved
P0936: -             */
P0937: -             Return (ToInteger (THC_PERFORMANCE_LIMITATION))
P0938: -           }
P0939: -           default {
P0940: -             // Unsupported function index
P0941: -             Return (Buffer() {0})
P0942: -           }
P0943: -         } // End Switch
P0944: -       } // End UUID
P0945: -     } // End THC HID Mode
P0946: -     If(LEqual(Arg0,ToUUID("84005682-5B71-41A4-8D66-8130F787A138"))) {
P0947: -       switch(ToInteger(Arg2)) {
P0948: -         case(0) {
P0949: -           // Function 1/2 are supported (0b00000011)
P0950: -           Return (Buffer() {0x3})
P0951: -         }
P0952: -         case(1) {
P0953: -             ADBG ("THC THC_ACTIVE_LTR")
P0954: -           Return (ToInteger (THC_ACTIVE_LTR))
P0955: -         }
P0956: -         case(2) {
P0957: -             ADBG ("THC THC_IDLE_LTR")
P0958: -           Return (ToInteger (THC_IDLE_LTR))
P0959: -         }
P0960: -         default {
P0961: -           // Unsupported function index
P0962: -           Return (Buffer() {0})
P0963: -         }
P0964: -       } // End Switch
P0965: -     } // End UUID
P0966: -     Return(Buffer(){})
P0967: -   } // End _DSM
P0968: -   If (LNotEqual (THC_WAKE_INT, 0)) {
P0969: -     Name (_S0W, 3)
P0970: -   }
P0971: - 
P0972: -   //
P0973: -   // Expose THC Resources only when in HID mode or THC Wake is enabled
P0974: -   //
P0975: -   If (LOr (LNotEqual (THC_WAKE_INT, 0), LEqual (THC_MODE, 0x1))) {
P0976: -     Method(_CRS, 0x0, Serialized) {
P0977: -       ADBG ("THC _CRS")
P0978: -       Store (EMPTY_RESOURCE_TEMPLATE, Local0)
P0979: -       If (LEqual(THC_MODE, 0x1)) {
P0980: -         // GPIO Reset resource
P0981: -         Name(UBUF,ResourceTemplate () {
P0982: -           GpioIo(Exclusive, PullDefault, 0, 0, IoRestrictionOutputOnly, "\\_SB.PC00.GPI0",,,GRST) {0}
P0983: -         })
P0984: -         CreateWordField(UBUF,GRST._PIN,RPIN)
P0985: -         Store(GNUM(THC_RST_PAD),RPIN)
P0986: -         Store(UBUF, Local0)
P0987: -       }
P0988: -       If (LNotEqual (THC_WAKE_INT, 0)) {
P0989: -         ConcatenateResTemplate(Local0, TINT (THC_WAKE_INT), Local1)
P0990: -         Return (Local1)
P0991: -       }
P0992: -       Return (Local0)
P0993: -     }
P0994: -   }
P0995: -   If (LEqual (THC_MODE, 0x1)) {
P0996: -     Method(_INI) {
P0997: -       ADBG ("THC _INI")
P0998: -       // configure gpio pad in gpio driver mode
P0999: -       SHPO(THC_RST_PAD, 1)
P1000: -       // Make sure both pads are in GPIO mode
P1001: -       SPMV(THC_RST_PAD, 0)
P1002: -       // Put device in inital reset state
P1003: -       SPC0(THC_RST_PAD, Or (0x42000200, And(Not(And(THC_RST_TRIGGER,1)),1)))
P1004: -     }
P1005: -     Method (_RST, 0, Serialized) {
P1006: -       ADBG ("THC _RST")
P1007: -       // Wait until Lock is freed
P1008: -       // Note: Lock should be not required because Method is serialized
P1009: -       //       added to avoid race conditions
P1010: -       While(LEqual(RSTL, 1)) {
P1011: -         Sleep (10)
P1012: -       }
P1013: -       // Acquire Lock
P1014: -       Store (1, RSTL)
P1015: -       SGOV(THC_RST_PAD, And(THC_RST_TRIGGER,1))
P1016: -       Sleep (300)
P1017: -       SGOV(THC_RST_PAD, And(Not(And(THC_RST_TRIGGER,1)), 1))
P1018: -       // Release Lock
P1019: -       Store (0, RSTL)
P1020: -     }
P1021:   }
[FOOTER Section 0]: Intel Confidential 40	

=== DOCUMENT PROPERTIES ===
Title: 
Author: Paithara Balagangadhara, Sai Prasad
Last Modified By: Prasad, Ravi
Created: 2022-02-28 17:41:00+00:00
Modified: 2025-08-12 08:56:34+00:00
Revision: 36
Subject: 
Keywords: CTPClassification=CTP_NT
Category: 
Comments: 

# EXTRACTION STATS
# Paragraphs processed: 1022
# Tables processed: 6
# Total output lines: 1123