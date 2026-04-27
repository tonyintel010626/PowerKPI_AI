> **Owner**: Chin, William Willy (`willychi`)

# QuickI2C Software Architecture Specification v1.0
# COMPLETE EXTRACTION — ZERO OMISSIONS
# Source: C:\QuickI2C SwAS v1.0.docx
# Total paragraphs: 920
# Total tables: 7
# Total sections: 1

P0000: # 
P0001: QuickI2C (HIDI2C over Touch Host Controller)  {style: DocTitle}
P0002: Software Architecture Specification (SwSAS)  {style: DocType}
P0003: Target Platforms: 
P0004: - POR
P0005: - 2024 Lunar Lake
P0006: - 2025 Panther Lake 
P0007: September 10, 2025
P0008: September 10, 2025
P0009: Revision 1.0 
P0010: Intel Confidential
P0011: 
P0012: 
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
P0042:   {style: Legal}
P0043:   {style: Legal}
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
P0062: INFORMATION IN THIS DOCUMENT IS PROVIDED IN CONNECTION WITH INTEL® PRODUCTS.  NO LICENSE, EXPRESS OR IMPLIED, BY ESTOPPEL OR OTHERWISE, TO ANY INTELLECTUAL PROPERTY RIGHTS IS GRANTED BY THIS DOCUMENT. EXCEPT AS PROVIDED IN INTEL’S TERMS AND CONDITIONS OF SALE FOR SUCH PRODUCTS, INTEL ASSUMES NO LIABILITY WHATSOEVER, AND INTEL DISCLAIMS ANY EXPRESS OR IMPLIED WARRANTY, RELATING TO SALE AND/OR USE OF INTEL PRODUCTS INCLUDING LIABILITY OR WARRANTIES RELATING TO FITNESS FOR A PARTICULAR PURPOSE, MERCHANTABILITY, OR INFRINGEMENT OF ANY PATENT, COPYRIGHT OR OTHER INTELLECTUAL PROPERTY RIGHT.   {style: Legal}
P0063: Recipients of this EDS (“Recipients”) are not obligated to provide Intel with ideas, comments or suggestions regarding the EDS (“Feedback”).  Intel has not agreed to and does not agree to treat as confidential any such Feedback.  Nothing in the EDS or in the parties’ dealings arising out of or related to it will restrict Intel’s right to use, profit from, disclose, publish, or otherwise exploit any Feedback, without compensation to Recipients, unless otherwise agreed in a writing executed by Intel.  {style: Legal}
P0064: Intel products are not intended for use in medical, life saving, or life sustaining applications.  {style: Legal}
P0065: Intel may make changes to specifications and product descriptions at any time, without notice.   {style: Legal}
P0066: Designers must not rely on the absence or characteristics of any features or instructions marked "reserved" or "undefined." Intel reserves these for future definition and shall have no responsibility whatsoever for conflicts or incompatibilities arising from future changes to them.  {style: Legal}
P0067: Intel® Integrated Touch may contain design defects or errors known as errata which may cause the product to deviate from published specifications. Current characterized errata are available on request.  {style: Legal}
P0068: Contact your local Intel sales office or your distributor to obtain the latest specifications and before placing your product order.  {style: Legal}
P0069: Intel and the Intel logo are trademarks or registered trademarks of Intel Corporation or its subsidiaries in the United States and other countries.  {style: Legal}
P0070: *Other names and brands may be claimed as the property of others.  {style: Legal}
P0071: Copyright © 2018, Intel Corporation. All rights reserved.  {style: Legal}
P0072: 
P0073:   {style: Title}
P0074: [TOC] Contents
P0075: Acknowledgments	7  {style: toc 1}
P0076: Reviewers / Stakeholders	8  {style: toc 1}
P0077: 1	Introduction	9  {style: toc 1}
P0078: 1.1	Document Scope	9  {style: toc 2}
P0079: 1.2	Terms and Abbreviations	9  {style: toc 2}
P0080: 1.3	REFERENCE DOCUMENTS	10  {style: toc 2}
P0081: 2	THC (Touch Host Controller) Architecture	10  {style: toc 1}
P0082: 2.1	Hardware Overview	10  {style: toc 2}
P0083: 3	HIDI2C over THC Architecture Overview	12  {style: toc 1}
P0084: 4	THC Initialization Flows	15  {style: toc 1}
P0085: 4.1.1	BIOS Initialization of the THC	15  {style: toc 3}
P0086: 4.1.2	Device ID mapping	15  {style: toc 3}
P0087: 4.1.3	ACPI Enumeration	16  {style: toc 3}
P0088: 4.1.4	ACPI RTD3 Consideration	23  {style: toc 2}
P0089: 4.2	QUICKI2C Driver Init Flows	24  {style: toc 2}
P0090: 4.2.1	QUICKI2C Driver	24  {style: toc 3}
P0091: 4.2.2	I2C Protocol/Mode Initialization	24  {style: toc 3}
P0092: 4.2.3	I2C Write followed by Read (using PIO)	26  {style: toc 3}
P0093: 4.2.4	I2C Write using TxDMA	27  {style: toc 3}
P0094: 4.2.5	I2C Write-Read using SwDMA	27  {style: toc 3}
P0095: 4.2.6	Timing based Frame Coalescing	28  {style: toc 3}
P0096: 4.2.7	SW Controlled Coalescing with Converged Sync Event (LNL+)	29  {style: toc 3}
P0097: 4.2.8	AddDevice	29  {style: toc 3}
P0098: 4.2.9	PrepareHw	30  {style: toc 3}
P0099: 4.2.10	QUICKI2C D0Entry	30  {style: toc 3}
P0100: 4.2.11	TIC Reset Exit Flow (i.e., Host Initiated Reset)	30  {style: toc 3}
P0101: 4.2.12	Read Device Descriptor	32  {style: toc 3}
P0102: 4.2.12.1	Write DMA Init	35  {style: toc 3}
P0103: 4.2.12.2	SW DMA Init	36  {style: toc 3}
P0104: 4.2.12.3	RxDMA2 Initialization	37  {style: toc 3}
P0105: 4.2.13	Interrupt Enable	40  {style: toc 3}
P0106: 4.2.13.1	Global Interrupt Enable	41  {style: toc 3}
P0107: 4.3	QUICKI2C Driver HID Operations	41  {style: toc 2}
P0108: 5	QUICKI2C Driver Runtime Operations	43  {style: toc 1}
P0109: 5.1	QUICKI2C Read Data Flows	43  {style: toc 2}
P0110: 5.1.1	Input Report Data Flow	43  {style: toc 3}
P0111: 5.1.1.1	Input Reports	44  {style: toc 3}
P0112: 5.1.1.2	Output Reports	44  {style: toc 3}
P0113: 5.1.1.3	Commands	46  {style: toc 3}
P0114: 5.1.1.4	Quiescing the THC	46  {style: toc 3}
P0115: 5.1.2	HW/SW Interrupt Handling Behavior	46  {style: toc 3}
P0116: 5.1.2.1	HW Sequencer Behavior	46  {style: toc 3}
P0117: 5.1.2.2	SW Interrupt Behavior	47  {style: toc 3}
P0118: 5.1.2.3	ISR Behavior	48  {style: toc 3}
P0119: 5.1.2.4	DPC Behavior	49  {style: toc 3}
P0120: 5.1.2.4.1	Interrupt Locks	49  {style: toc 3}
P0121: 5.2	Error Handling Operations	49  {style: toc 2}
P0122: 5.2.1	SW Sequencing (PIO) Error	51  {style: toc 3}
P0123: 5.2.2	Read DMA Errors	51  {style: toc 3}
P0124: 5.2.3	THC D3	52  {style: toc 3}
P0125: 5.3	Tap to Wake	53  {style: toc 2}
P0126: 5.3.1	Tap to Wake (Wakeable Mode) Entry	53  {style: toc 3}
P0127: 5.3.2	Tap to Wake (Wakeable Mode) Exit	54  {style: toc 3}
P0128: 5.4	Workaround Settings	54  {style: toc 2}
P0129: 5.4.1	HIDI2C Compliance	54  {style: toc 3}
P0130: 5.4.1.1	ECO fix workaround Configuration settings	55  {style: toc 3}
P0131: Registry Settings	55  {style: toc 4}
P0132: BIOS Settings	55  {style: toc 4}
P0133: Recommendations	56  {style: toc 3}
P0134: 5.4.1.2	Other Workaround Settings	56  {style: toc 3}
P0135:   {style: toc 2}
P0136: [TOC] Revision history

=== TABLE 1 (rows=9, cols=3) ===
  T1R000: Revision Number || Description || Revision Date
  T1R001: 0.3 || Initial release. Branch from QuickSpi SwSAS 0.8.   Change in direction to support HIDI2C protocol over THC || February 16, 2022
  T1R002: 0.5 || Updated first supoprted platform | Fixed minor errors in architecture block digram | Included Device ID mapping table | Added clarification around usage of TIC reset line  | Updated I2C Protocol/Mode Initialization description to set port type to I2C | Updated the Write followed by Read (using PIO) section: Set THC_SS_CMD register, Remove usage of RxDMA1 and added more clarity | Updated I2C Write-Read using SwDMA | Updated "Generic Output Report" flow to include IOCTL_HID_WRITE_REPORT and IOCTL_HID_SET_OUTPUT_REPORT || May 31, 2022
  T1R003: 0.8 || Updated several sections based on review feedback || September 5, 2022
  T1R004: 0.81 || Adding PTL Workaround settings || June 2025
  T1R005: 0.9 || Scrubbing comments || July 2025
  T1R006:  ||  || 
  T1R007:  ||  || 
  T1R008:  ||  || 
=== END TABLE 1 ===

P0137: 
P0138: 
P0139: Acknowledgments  {style: Header-PreSection}
P0140: Besides the authors and key contributors listed on the front page, additional thanks goes to the following individuals and groups for contributing to the architecture directly or indirectly at different times during the solution development.
P0141: 
P0142: - Anton Cheng
P0143: - Kruthi Murali
P0144: - Scott Webb
P0145: - Jason Gaston
P0146: - Mukesh Komalan
P0147: - Even Xu
P0148: - Adrian Sperber
P0149: - Tommy Choi
P0150: - Adrian Sperber
P0151: 
P0152: - 
P0153: 
P0154: Please contact Saiprasad Paithara if any names are missing from this list.
P0155: 
P0156: 
P0157: Reviewers / Stakeholders  {style: Header-PreSection}

=== TABLE 2 (rows=7, cols=3) ===
  T2R000: Name || Roles || Revision Sent / Acknowledged
  T2R001: Anton Cheng || CCG Architect - Human Input Domain Lead || 
  T2R002: Kevin Zhu || CIG HW Architect – THC-SPI lead || 
  T2R003: Kruthi Murali/Tommy Choi || CCG SW – HIDI2C SW Engineering || 
  T2R004: Scott Webb || CCG CCE –Enabling Lead, Enabling Guide Owner || 
  T2R005: Even Xu || IPG SW || 
  T2R006: Jason Gaston || CCG Validation --  Input Subsystem Validation Lead || 
=== END TABLE 2 ===

P0158: 
P0159: 
P0160: # Introduction
P0161: This document specifies the software architecture changes required to support HIDI2C specification on Intel’s Touch Host Controller (THC) subsystem starting from Lunar Lake M chipset.
P0162: ## Document Scope
P0163: This document was written to guide implementation of QUICKI2C Driver software component for Windows Cobalt OS on CCG platforms starting Lunar Lake M. This document will focus on the BIOS, ACPI and OS configuration of Touch Host Controller Subsystem to communicate with HIDI2C v1.0 compliant Touch Controller devices. The primary focus for SW operation is supporting the Windows 10 in-box driver frameworks for support of Touch and stylus peripherals connected directly to the THC controller.  
P0164: General BIOS configuration, requirements and architecture are listed in the references.
P0165: 
P0166: ## Terms and Abbreviations
P0167: - The terms and abbreviations listed in Table 1.1.1 are used as described in this document.
P0168: Table 1.1 – Terms and abbreviations  {style: Caption}

=== TABLE 3 (rows=18, cols=2) ===
  T3R000: Term || Description
  T3R001: CS || Connected Standby
  T3R002: I2C || Inter-Integrated Circuit  - in the LNL-M platform, I2C host bus controller is integrated into THC IP by utilizing the Synopsys I2C SubIP
  T3R003: SPI || Serial Peripheral Interface. Synchronous serial communication bus used to attach peripherals to motherboard. In the ADP-P and MTL chipset, there are two instances of THC-SPI host controllers.
  T3R004: GPIO || General Purpose Input/Output – in the chipset there is General Purpose Input/Output controller that fits within the definition of the ACPI 5.0 GPIO controller.
  T3R005: LTR || Latency Tolerance Reporting
  T3R006: Sideband interrupt || Interrupt from a peripheral direct to the host CPU without intervention of its associated host bus controller.
  T3R007: THC || Touch Host Controller within the chipset that supports SPI and I2C based host controller interface to touch devices
  T3R008: HidI2C || Microsoft defined specification  that defines the protocol, procedure and features for input devices to communicate using HID protocol over I2C interface
  T3R009: HidI2C.sys || Microsoft driver that implement HidI2c protocol on top of SPB (Simple Peripheral Bus) framework.   See QuickI2C for HIDI2C-over-THC driver.
  T3R010: QuickSPI || Name for the HID mini driver that implement HIDSPI protocol over THC-SPI (with HW accelerated interrupt handling).    Not to be confused with HIDSPI.sys that implements HIDSPI protocol on SPB framework.
  T3R011: QuickI2C || Name for the HID mini driver that implement HIDI2C protocol over THC (with HW accelerated interrupt handling).    Not to be confused with HIDI2C.sys that implements HIDI2C protocol on SPB framework.
  T3R012: ACPI || Advanced Configuration and Power Interface – for this specification we are assuming ACPI 5.0
  T3R013: PEP || Power Engine Plugin
  T3R014: RTD3 Power management || Run-time D3 Power Management
  T3R015: Simple Peripheral Buses || Microsoft defined term to refer to the classification of synchronous serial IO buses that can use clock signal to transmit consecutive data bits over the buses.  This classification includes I2C and SPI.
  T3R016: SoC || System on Chip
  T3R017: WDK || Windows Driver Kit
=== END TABLE 3 ===

P0169: 
P0170: ## REFERENCE DOCUMENTS
P0171: 
P0172: # THC (Touch Host Controller) Architecture
P0173: ## Hardware Overview
P0174:  [IMAGE]
P0175: 
P0176: Figure 1: THC Functional Block Diagram
P0177: 
P0178: 
P0179: The Touch Host Controller (THC) is a soft IP supporting a host controller interface to the HIDI2C device driver for data transfer from I2C based  HID (ex: touch, touchpad etc.) devices. This cluster has a single root space IOSF Primary interface that supports transactions to/from touch devices. Host driver configures and controls the touch devices over THC interface. THC provides high bandwidth DMA services to the HIDI2C driver and transfers the HID reports to host system main memory that is accessible by internal touch accelerator (host CPU), or host driver respectively.
P0180: The THC Controller has the following interfaces:  {style: BodyText}
P0181: - IOSF Primary Interface for DMA operation and register access  {style: BodyText}
P0182: - Minimum 100MHz 64 bit IOSF bandwidth  {style: BodyText}
P0183: - Dual port RAM interface for RX data buffering  {style: BodyText}
P0184: - Chassis DFT Interface  {style: BodyText}
P0185: - Chassis Clock/Reset (Not supported will instead use GPIO for Reset)/PM interfaces  {style: BodyText}
P0186: Hardware sequencer within the THC is responsible for transferring (via DMA) data from Touch IC into system memory.  A ring buffer is used to avoid data loss due to asynchronous nature of data consumption (by host) in relation to data production (by Touch IC via DMA). For each Touch IC, there is one ring buffer for CPU memory address space. 
P0187: 
P0188: Unaccelerated Reference HIDI2C Driver Stack 
P0189: HIDI2C protocol defines operational flows, data structures and bus characteristics that may be used by a HID compliant Touch controller (aka Touch IC) to communicate with Windows host computer over I2C bus. Typical SW implementations involve an OS inbox hidi2c driver communicating with Touch IC using an SPB compliant controller. The underlying assumptions are that the I2C bus is generic, unenlightened (i.e., non-accelerated) and the hidi2c driver can send raw bytes to the SPB client driver to be transferred to/from the Touch IC device. The hidi2c driver oversees handling of interrupts from the Touch IC and coordinates I2C transfers.   {style: Plain Text}
P0190:   {style: Plain Text}
P0191: 
P0192:  [IMAGE]
P0193: The HIDI2C device in this architecture is enumerated via ACPI and requires the following resources: Interrupt and SPB I2C serial bus resource.  {style: Plain Text}
P0194: 
P0195: # HIDI2C over THC Architecture Overview
P0196: 
P0197:  [IMAGE]
P0198: 
P0199: 
P0200:   {style: Plain Text}
P0201: Figure 2: THC HIDI2C System Architecture Diagram
P0202:   {style: Plain Text}
P0203:   {style: Plain Text}
P0204: This figure illustrates the high-level architecture of THC starting from LNL-M, which is fully capable of supporting Microsoft HIDI2C v1.0 protocol (focus of this document) in addition to Microsoft HIDSPI v1.0 protocol.   {style: Plain Text}
P0205:   {style: Plain Text}
P0206: Windows OS HIDClass framework allows hardware partners to build hardware implementations that are able to support HIDI2C protocol and can support higher throughput, as data interrupts are directly consumed by hardware, resulting in much lower latency to fetch input reports from the device. This requires adding a new hardware accelerator controller (aka QuickI2C) driver to the software stack using the Microsoft HID miniport driver model.  {style: Plain Text}
P0207:   {style: Plain Text}
P0208:   {style: Plain Text}
P0209: Hardware partners are required to build the HID Miniport driver instead of using inbox hidi2c driver. due to differences in underlying hardware (DMA, register map etc.).   {style: Plain Text}
P0210: 
P0211: Intel QUICKI2C (HIDI2C over THC) Software Overview:  {style: Plain Text}
P0212: 
P0213: In this architecture, QuickI2C driver is responsible to maintain the hidi2c protocol flow, track device state, communicate with OS HID stack and manage request/device queues. The driver also manages the underlying THC hardware, provides a way to reset the Touch IC device and manages PNP resources assigned by the platform.   {style: Plain Text}
P0214:   {style: Plain Text}
P0215: QuickI2C Driver main responsibilities:  {style: Plain Text}
P0216: - Manage resources needed by the Touch device using ACPI platform specific definitions
P0217: - Reading/Writing of HID reports. Provide incoming reports to HIDClass and write outgoing reports to the I2C bus as instructed by HIDClass
P0218: - Reset handling. Initiate a Touch IC device reset as specified in HIDI2C protocol document
P0219: - Power state transitions. Hidclass is the power policy owner for the device. QuickI2C driver will handle reset notifications and idle notification requests from hidclass. QuickI2C driver will rely on standard ACPI definitions within the platform BIOS to manage power to the Touch IC
P0220: - Report validation – QuickI2C driver is responsible for validating length and other fields of the input report header before passing the input reports to HIDClass.
P0221: - Verify IP configurations inherited from BIOS configuration are within the supported bound, including but not limited to LTR, I2C HCNT and LCNT values.
P0222:   {style: Plain Text}
P0223: In addition to the above responsibilities, the client driver is also responsible for maintaining a queue for interfacing with HIDClass and configuring HID device specific registry settings.  {style: Plain Text}
P0224:   {style: Plain Text}
P0225: 
P0226: Intel QUICKI2C driver supports discrete touch processing where the Touch IC sends pre-processed touch/stylus reports, as well as heatmap processing where the Touch IC sends HID reports containing heatmap data that are converted to Touch reports. QUICKI2C driver is responsible for controlling the flow of information between the THC Host Controller, Touch IC and the Window HID infrastructure (HIDClass and PnP etc.).   {style: Plain Text}
P0227:   {style: Plain Text}
P0228: THC Touch System Components:  {style: Plain Text}
P0229: - THC Touch IC: AKA the Touch AFE (analog front end). The discrete analog components that sense and transfer either discrete touch data or heatmap data in the form of HID reports over the I2C bus to the THC Controller on the host.
P0230: - THC Host Controller: The PCI device HBA (host bus adapter), integrated into the PCH, that serves as a bridge between the THC Touch ICs and the host.
P0231: - QUICKI2C Client Driver: The OS-based kernel mode driver that manages the THC Controller and the primary focus of this specification.
P0232: - HIDClass Driver: The kernel mode HID driver from the OSV. In Windows this driver exports a device object for every touch digitizer it detects as a result of receiving a Report Descriptor.
P0233: - BIOS (not shown): Contains a THC Host Driver component, likely implemented as a UEFI driver, to control the THC Controller for pre-OS touch operations. More importantly, BIOS is responsible for key THC configuration operations.
P0234: 
P0235: Single and Dual Touch Screen Support:
P0236: As shown in the above diagram, the THC exposes 2 PCI devices, each with a BAR dedicated for an individual I2C bus. In this configuration the PCI bus driver will enumerate 2 device objects for which 2 instances (FDOs) of the QUICKI2C driver loads.
P0237: 
P0238: THC can also to be used for a single touch IC and single touch screen. This is, by far, the most common configuration OEMs will have. In this, most common usage, BIOS shall disable the unused THC and therefore expose only 1 PCI BDF for the OS to load a single instance of the QUICKI2C client driver.
P0239: 
P0240: # THC Initialization Flows
P0241: 
P0242: ### BIOS Initialization of the THC
P0243: BIOS initialization of the THC HW:
P0244: Prior to OS boot BIOS is responsible for the following controller initialization (details can be found in the THC BIOS writers guide):
P0245: - Port initialization based on OEM configuration. Unused THC-I2C ports shall be disabled by BIOS.
P0246: - Assign Class-Code/SCC
P0247: - Device ID programming based on the protocol selected. Refer to Device ID mapping section below.
P0248: - PCI Configuration space initialization and BAR allocation.
P0249: - Cover management capabilities configuration such as clock gating, D0i2 enable disable, D0i2 entry latency,
P0250: - Note: SAI policies or any W/A in SAI have started to move within ChipsetInit. They are no longer in BIOS, however, captured here for the lack of another ChipsetInit specific section in this doc.
P0251: - LTR configuration/enabling
P0252: - Frame Coalescing and Display sync enabling
P0253: - GPIO/ACPI expectations 
P0254: - Power Up(if used by board design)
P0255: - RESET:  (if used by device and board design)
P0256: - Latencies such as Off duration, Power up to Reset delay, Post Reset Delay should be covered as well
P0257: - vGPIO for WoT: if WoT is used
P0258: -  	vGPIO for SPB-Workaround is not necessary (used during HIDSPI development, not relevant here)
P0259: - TIC Interrupt line should be configured as level-triggered (per HIDI2C spec). In addition, Active low or Active High definition is vendor specific
P0260: 
P0261: 
P0262: ### Device ID mapping
P0263: Reference: 
P0264: - https://docs.intel.com/documents/pch_doc/MTLS/HAS/Chap06_MTP-S_RegMaps/Chap06_MTP-S_RegMaps.html
P0265: - https://docs.intel.com/documents/ClientSilicon/LNL/global/LNL_SOC_South_Addr_BDF_DID_HAS/LNL_SOC_South_RegMaps.html
P0266: - https://docs.intel.com/documents/ClientSilicon/PTL/global/PTL_PCD_South_Addr_BDF_DID_HAS/PTL_PCD_South_RegMaps.html
P0267: 
P0268: 
P0269: 
P0270: 

=== TABLE 4 (rows=7, cols=8) ===
  T4R000:  ||  || MTP-S || MTL SIMICS & P/M || LNL-M || PTL PCD-H || WCL
  T4R001: HIDSPI || Port #0 || 7F59 || 7E49 || A849 || E349 || 4D49 || 
  T4R002:  || Port #1 || 7F5B || 7E4B || A84B || E34B || 4D4B || 
  T4R003: IPTS || Port #0 || 7F58 || 7E48 || NA || NA || NA || 
  T4R004:  || Port #1 || 7F5A || 7E4A || NA || NA || NA || 
  T4R005: HIDI2C || Port #0 || NA || NA || A848 || E348 || 4D48
  T4R006: HIDI2C || Port #1 || NA || NA || A84A || E34A || 4D4A
=== END TABLE 4 ===

P0271: - 
P0272: - MTL/ARL:
P0273: - Lower DID:  IPTS INF
P0274: - Higher DID: QuickSPI INF
P0275: - 
P0276: - LNL/ PTL/WCL:
P0277: - Lower DID Quick I2C INF
P0278: - Higher DID: QuickSPI INF
P0279: 
P0280: ### ACPI Enumeration
P0281: 
P0282: - ACPI device objects for THC 0 and THC 1 shall be added by BIOS
P0283: - _ADR specifies the PCI Bus/Device/Function address 
P0284: - Configure the THC PCI Device ID for QUICKI2C mode
P0285: - TIC Interrupt line (outside of ACPI scope) shall be configured by the driver in THC registers as active-low level triggered interrupt as defined in HIDI2C spec (section 7.4 – Interrupt line management)
P0286: - Virtual interrupt will be defined in _CRS for wake. This wakeable interrupt shall match with the configuration of function interrupt (i.e., active-low level triggered) as defined in HIDI2C spec
P0287: - _RST method is not required to the reset the device per HIDI2C specification. BIOS and OS drivers shall instead use the Reset command defined in the HIDI2C protocol to reset the device. However, platform may optionally implement ACPI _RST method to control TIC reset line. Additionally, an optional _INI method me be implemented to initialize the device in reset state.
P0288: - RVP BIOS menu shall define policy via BIOS Init and ACPI to switch between HIDI2C and HIDSPI protocol. Dual DID
P0289: - BIOS shall define policy/setup menu for the following settings:
P0290: - Vendor specific _DSM settings defined in HIDI2C spec
P0291: - _DSD settings defined for THC (setting is both device and  platform specific)
P0292: - Including interrupt servicing delay (fixed 1ms on PTL, variable on NVL)
P0293: - Maximum packet size (fixed to 1 value on PTL, variable on NVL)
P0294: - 
P0295: 
P0296: 
P0297:    {style: Normal (Web)}
P0298:   {style: Normal (Web)}

=== TABLE 5 (rows=10, cols=6) ===
  T5R000: Field || Value || Mandatory | /Optional (M/O) || ACPI Object || Format || Comments
  T5R001: THC PCI Device Address || Platform specific || M || _ADR || Integer || Returns address of THC device on its parent bus (PCI).  | High word–Device #, Low word–Function #  | Example: Device 3, Function 2 is 0x00030002
  T5R002: Current Resource Settings || Platform specific || O || _CRS || Byte Stream || -GpoInt (virtual Gpio Interrupt) for wake | Level triggered, Active  Low, ExclusiveAndWake | Example: GpioInt(Level, ActiveLow, ExclusiveAndWake,PullUp 0, “\\_SB.GPI2”)
  T5R003: Device Specific Data || Vendor specific. GUID defined by HIDI2C spec. || M || _DSM ||  || This GUID defines a structure that contains device specific  | information as defined by HIDI2C spec. | Arg0 (DSM UUID for HIDI2C):  | 3CDFF6F7-4267-4555-AD05-B30A3D8938DE
  T5R004:  || Vendor specific. GUID defined by THC.  | {41C1B4AF-E89A-44B5-AAB0-039D4B5BFF61} || M || _DSD (DeviceSpecificData) ||  || {41C1B4AF-E89A-44B5-AAB0-039D4B5BFF61} |  | This GUID defines a structure that contains device specific data information  | (which is normally defined under _CRS in HIDI2C spec)
  T5R005:  || Platform specific. GUID defined by THC.  |  {B38B028B-AB16-45C3-92FB-758686BBC3A4} || O || _DSD ||  || {B38B028B-AB16-45C3-92FB-758686BBC3A4} |  | This GUID defines a structure that contains platform specific configuration needed for THC or the underlying I2C SubIP.
  T5R006:  || Platform specific. GUID defined by THC.  | [300D35B7-AC20-413E-8E9C-92E4DAFD0AFE] || O || _DSM ||  || This GUID defines a structure that contains platform specific configuration or  | workarounds needed for THC. |  | Default LTR will be considered as infinite when _DSM returns the Active and Idle functions as unsupported. Any required Workarounds for Active LTR and Idle LTR values shall be supported via BIOS policy options.
  T5R007:  ||  ||  ||  ||  || 
  T5R008: Device Reset Method ||  || M || _RST ||  || (Optional) QuickI2C driver does not invoke _RST directly.  OSPM does per ACPI specification.  Use this method if DEVICE needs it.  Otherwise, it is not needed. |  | Reference: ACPI 6.0 Section 7.3.25 compliant device reset method, to be called by the HOST  | OS as an ACPI FLDR (function-level device reset) to reset the touch controller. |  | Refer to ACPI spec for details on reset line behavior. |  | If Reset GPIO pin is needed by DEVICE, the GPIO pad will be owned by BIOS and no longer be in native THC mode. |   | Example, _RST allows BIOS to meet the reset hold time so that some DEVICE needs to successfully complete reset sequence.
  T5R009:  ||  ||  ||  ||  || Wake support | _S0W - This is needed, These are platform specific: _PS0/_PS3/_PRW | GPIOInt (Needed) - ExclusiveAndWake - sample code |     If (LNotEqual (THC_WAKE_INT0, 0)) { |       Name (_S0W, 3) |       Method (_CRS) { Return (TINT (THC_WAKE_INT0)) } |     }
=== END TABLE 5 ===

P0299: 
P0300: ## ACPI RTD3 Consideration
P0301: There are a few limitations in Windows ACPI implementation that make RTD3 for DEVICE connected to THC tricky.
P0302: - PRW on ACPI device with GPIO crashes on Windows
P0303: - On Linux, there is a kernel fix, but as far as we can tell is not supported in Windows:
P0304: - https://lore.kernel.org/lkml/20220921155205.1332614-1-rrangel@chromium.org/T/ [LINKS: https://lore.kernel.org/lkml/20220921155205.1332614-1-rrangel@chromium.org/T/]
P0305: - https://patchew.org/linux/20220921155205.1332614-1-rrangel@chromium.org/20220921094736.v5.8.I7d9202463f08373feccd6e8fd87482c4f40ece5d@changeid/ [LINKS: https://patchew.org/linux/20220921155205.1332614-1-rrangel@chromium.org/20220921094736.v5.8.I7d9202463f08373feccd6e8fd87482c4f40ece5d@changeid/]
P0306: - 
P0307: - [PATCH v5 08/13] ACPI: PM: Take wake IRQ into consideration when entering suspend-to-idle 
P0308: - 
P0309: 
P0310: The workaround is not to use Power Resource in ACPI for THC DEVICE RTD3.   Instead, ACPI code has to satisfy any power dependencies (THC DEVICE on the same power resource with other device) via _PS0, __PS3, and _DSW methods.    Realistically, it means dedicated power resource is needed to avoid complicated testing and debug.
P0311: 
P0312: For DEVICE that has no wake capability, the RTD3 solution is:
P0313: - THC ACPI exposes D3cold support.   _S0w is set as 0 (not wake from lower power state). Power gating is handling in _PR0/_PR3 on the power resource that reference by the THC ACPI object.
P0314: 
P0315: For DEVICE that needs wake support, the RTD3 solution is:
P0316: - THC ACPI does not expose D3cold support.   Power gating is handling in _PS0/_PS3, with _S0w set as 3 to allow wake from D3.   _DSW will modify the _PS3 behavior based on whether OS arms the device for wake or not.
P0317: 
P0318: 
P0319: ## QUICKI2C Driver Init Flows
P0320: 
P0321: ### QUICKI2C Driver
P0322: Installed via primary INF using new PCI SIG Class/Sub-class code. BIOS is responsible to expose the correct Device ID based on the mode selection – QuickSPI vs QuickI2C. Please refer to “Device ID mapping” section
P0323: ### I2C Protocol/Mode Initialization
P0324: I2C protocol initialization steps are listed below (note: all these steps go through PIO). Before programming the SubIP registers listed below, Port type in THC register (THC_M_PRT_CONTROL.PORT_TYPE) needs to be set to I2C (0x01). Please refer to the subIP datasheet Chap. 6 “Programming the DW_apb_i2c” for the SW programming details.  {style: BodyText}
P0325: Updates to the SubIP registers follow the pattern of PIO Read, Set/Clear the required bits, and then PIO Write.  {style: BodyText}
P0326: - Read IC_ENABLE register, set Enable (BIT 0) to 0 and write modified register value back to IC_ENABLE register to disable I2C operations
P0327: - Program IC_CON register fields as required:
P0328: - Set MASTER_MODE to 1 – Enable Master mode
P0329: - Set IC_SLAVE_DISABLE to 1 (Read/Modify/Write) – Target Device disabled
P0330: - Set IC_RESTART_EN to 1 – Enable restart mode
P0331: - Set IC_10BITADDR_MASTER to 0 – 7-bit addressing
P0332: - Set IC_10BITADDR_SLAVE to 0 – 7-bit addressing
P0333: - Set IC_MAX_SPEED_MODE to desired mode (refer to ACPI Enumeration for platform configuration). Ex: 1 – Standard mode (Standard = 1, Fast = 2, High = 3)
P0334: - Set TX_EMPTY_CTRL to 1 to update TX_EMPTY field (in IC_RAW_INTR_STAT) when transmit buffer is at or below threshold value (IC_TX_TL).
P0335: - Set RX_FIFO_FULL_HLD_CTRL to 1 so that SubIP can hold the I2C bus when the Rx FIFO is full to RX_BUFFER_DEPTH 
P0336: - Program STOP_DET_IF_MASTER_ACTIVE so that SubIP can detect Stop conditions, set corresponding STOP_DET bit in IC_RAW_INTR_STAT and generate interrupt to SW. 
P0337: - Set address of target device by writing it to TAR (refer to ACPI _DSM Enumeration for platform configuration).
P0338: - Write to IC_SS/FS/HS_HCNT to set HIGH period of SCL depending on the I2C speed mode (refer to ACPI Enumeration for platform configuration).
P0339: - Write to IC_SS/FS/HS_LCNT to set LOW period of SCL depending on the I2C speed mode (refer to ACPI Enumeration for platform configuration).
P0340: - Program the IC_SDA_HOLD/SETUP based on the touch panel/platform timing. Note: These values will be tuned Post-Si, refer to ACPI Enumeration to configurate SoC specific timing parameters
P0341: - Program the IC_FS/HS_SPKLEN based on the touch panel/platform timing, if required. (refer to ACPI Enumeration for platform configuration).
P0342: - Write to IC_INTR_MASK to enable all interrupts
P0343: - Reinitialize the value of IC_RX_TL to set Rx FIFO threshold level
P0344: - Write to IC_TX_TL to set Tx FIFO threshold level
P0345: - Write to IC_DMA_CR to enable transmit/receive FIFO DMA channel
P0346: - Write to IC_DMA_TDLR/RDLR to set Transmit/Receive Data Level for DMA requests
P0347: - Optionally program the SCL/SDA_STUCK_LOW_TIMEOUT value so that master can abort the transmit if SDA is stuck at low for longer than specified timeout value
P0348: - Write to IC_ENABLE to enable I2C protocol IO before initiating any I2C bus cycles.
P0349: After these steps, I2C asserts dma_tx_req to the THC when Tx FIFO level is below IC_DMA_TDLR. THC responds by writing to I2C TX FIFO and asserting dma_ack; I2C transfer begins when a command is available in Tx FIFO. THC SW uses the existing PIO, RX DMA, TX DMA and the SW DMA to access the I2C device similar to HIDSPI flow.  {style: BodyText}
P0350: Recommended settings for RX_TL, TXL_TL, DMA_TDLR and DMA_RDLR are below. Except RDLR, other settings are more suggestive. RDLR has dependency on internal THC architecture. It needs a condition of <=7
P0351: 
P0352: 

=== TABLE 6 (rows=5, cols=4) ===
  T6R000: Reg || Description || Value || Reason
  T6R001: RX_TL || RX FIFO data above this will give RXFIFO_FULL interrupt || 62 || FIFO_DEPTH - 2
  T6R002: TX_TL || TX FIFO data below this will give TXFIFO_EMPTY interrupt || 0 || 
  T6R003: DMA_TDLR || Dma_tx_req given if #commands in TXFIFO less than this value. || >=3  | Suggested 7 || >=3 to avoid TXFIFO_EMPTY interrupt coming often. | Can use same as LPSS if above condition met
  T6R004: DMA_RDLR || DMA_rx_req is given if data in RXFIFO ia above this value || >=1  <= 7 | Suggested 7 || If any data available can start reading. | But in case of THC RF memory full, internal temp buffer can store max 8 bytes. | To avoid overflow suggested 7.
=== END TABLE 6 ===

P0353: 
P0354: 
P0355: Except RDLR other are more suggestive and can be used same as LPSS.
P0356: RDLR has dependency on internal THC architecture. It needs a condition of <=7
P0357: 
P0358: ### I2C Write followed by Read (using PIO)
P0359: 
P0360: QuickI2C driver follows the below sequence for PIO Write followed by Repeated Start and then Read from the HIDI2C device
P0361: 
P0362: - Clear THC_SS_ERR and TSSDONE bits from thc_m_prt_sw_seq_sts to clear status of previous PIO requests
P0363: - Set THC_PIO_I2C_WBC field in thc_m_prt_sw_seq_cntrl register to the desired write byte count
P0364: - Set THC_SS_BC field in thc_m_prt_sw_seq_cntrl register to the number of bytes to be read from the device
P0365: - Set THC_SW_SEQ_DATA0_ADDR field in thc_m_prt_sw_seq_data0_addr register to the HIDI2C register address (ex: device descriptor register, command register etc.)
P0366: - Set THC_SS_CD_IE field in thc_m_prt_sw_seq_cntrl register to receive PIO completion interrupts
P0367: - Set THC_I2C_RW_PIO_EN field in thc_m_prt_sw_seq_i2c_wr_cntrl to enable I2C write followed by Read transaction
P0368: - THC_SS_CMD should be set as per SubIP PIO Spec as follow.
P0369: ReadSubIpCommand = 0x12, //PIO command to read TH	C internal I2C SubIP registers
P0370: WriteSubIpCommand = 0x13, //PIO command to write THC internal I2C SubIP registers
P0371: ReadDeviceCommand = 0x14, //Read I2C device
P0372: WriteDeviceCommand = 0x18, //Write I2C device
P0373: WriteReadCommand = 0x1C, //Write then Read I2C device
P0374: - Set TSSGO field in thc_m_prt_sw_seq_cntrl to start the PIO operation
P0375: - THC HW sets TSSDONE bit in thc_m_prt_sw_seq_sts which causes interrupt to be sent to the driver
P0376: - Read the data returned by the HIDI2C device or I2C SubIP starting at thc_m_prt_sw_seq_data[0] for the expected number of bytes specified previously in THC_SS_BC
P0377: - Clear THC_SS_ERR and TSSDONE bits from thc_m_prt_sw_seq_sts to clear status of previous PIO requests
P0378: ### I2C Write using TxDMA
P0379: 
P0380: QuickI2C driver follows the below sequence for Write to I2c device using Write DMA (aka TxDMA)
P0381: 
P0382: - Write Command Register to the write data buffer. Command Register is vendor specific and returned by Touch IC in HID device descriptor
P0383: - Write the command specific data to the write buffer (ex: Set Power, Reset etc.)
P0384: - Copy PRD Entries from Driver PRD to THC HW PRD
P0385: - Clear THC_WRDMA_CMPL_STATUS from thc_m_prt_write_int_sts register
P0386: - Enable interrupts on Write DMA completion by setting THC_WRDMA_IE_IOC_DMACPL in thc_m_prt_write_dma_cntrl register
P0387: - Set THC_WRDMA_START bit in thc_m_prt_write_dma_cntrl register to start Write DMA
P0388: - Wait for Write completion using Write DMA completion interrupt from THC or poll until THC_WRDMA_CMPL_STATUS is set with a timeout. Registry key shall be used to switch between Polling vs Write DMA Completion interrupts. 
P0389: Clear THC_WRDMA_CMPL_STATUS after handling write completion interrupt
P0390: ### I2C Write-Read using SwDMA
P0391: 
P0392: QuickI2C driver follows the below sequence for SwDMA – i.e., Write followed by Repeated Start and then Read from the HIDI2C device
P0393: 
P0394: - Pause RxDMA2 by clearing start bit in thc_m_prt_read_dma_cntrl_2 register. Wait until ACTIVE bit is clear in thc_m_prt_read_dma_int_sts_2 register
P0395: - Reset RxDMA2 CB pointer by setting TPCPR in thc_m_prt_read_dma_cntrl_2 register.
P0396: - Quiesce Interrupts from the TIC by setting THC_DEVINT_QUIESCE_EN in thc_m_prt_control register. Wait until THC_DEVINT_QUIESCE_HW_STS is clear
P0397: - Allocate and Initialize Sw DMA buffers (see SW DMA Init section)
P0398: - Reset Sw DMA read and Write pointers. Set write pointer to wrap around value of 0x80
P0399: - Enable the following fields in thc_m_prt_read_dma_cntrl_sw register: IE_DMACPL, IE_IOC, SOO
P0400: - Set length of HIDI2C Read from THC_M_PRT_SW_DMA_PRD_TABLE_LEN field in thc_m_prt_sw_dma_prd_table_len register
P0401: - Set the following fields in thc_m_prt_rprd_cntrl_sw: THC_SWDMA_I2C_WBC to 0x02 indicating length of command register (2 bytes). 
P0402: - Set THC_SWDMA_I2C_WBC as following:
P0403: - Size configured here could be fixed (e.g. sizeof reportdescriptor address) or a variable (e.g. get_report - in which case it would be size of commandregister + sizeof get_request + sizeof dataregister + 1 [optional byte])
P0404: - Set THC_SWDMA_I2C_RX_DLEN_EN as following:
P0405: - If the driver already knows the read length from device descriptor table(ex: Report Descriptor), Set THC_SWDMA_I2C_RX_DLEN_EN to 0 and thc_m_prt_sw_dma_prd_table_len set to read length.
P0406: - In case the read length is from the incoming packet (i.e., length is part of the first 2 bytes of the data register) from the device(Get Feature) then set THC_SWDMA_I2C_RX_DLEN_EN to 1
P0407: - Program the desired HIDI2C register (ex: Command Register) in THC_SW_SEQ_DATA0_ADDR field of thc_m_prt_sw_seq_data0_addr register. These PIO data registers are used by the HW for write operation of SWDMA sequence.
P0408: - Clear THC_SS_ERR and TSSDONE bits in thc_m_prt_sw_seq_sts register
P0409: - Set Start bit in thc_m_prt_read_dma_cntrl_sw register
P0410: - Wait for interrupt from HW with DMACPL_STS bit set in thc_m_prt_read_dma_int_sts_sw register
P0411: - Get the data returned by HIDI2C device from SW DMA PRD Read Buffers
P0412: - Clear DMACPL_STS bit
P0413: - Complete the SWDMA operation by doing the following:
P0414: 
P0415: - Pause SWDMA by setting thc_m_prt_read_dma_cntrl_sw.fields.START to 0
P0416: - Reset SWDMA by setting: mmio->thc_m_prt_read_dma_cntrl_sw.fields.TPCPR = 1; //reset SWDMA read pointers
P0417: - Restart RXDMA2 paused during SWDMA start
P0418: - Unquiesce device interrupt quiesced during SWDMA start

P0419: 
P0420: ### Timing based Frame Coalescing
P0421: 
P0422: In order to match competitors (e.g. iPAD) capability on upstreaming (to SoC) multiple input
frames at a time depending on application needs (e.g. display frame refresh rate), THC HW
will coalesce the SW interrupts to only generate SWI (SW interrupt). When there is no touch/pen input, THC will generate SWI on first frame. 
P0423: 
P0424: During a touch/pen report sequence, SW driver will program THC to generate SWI in a desirable cadence (e.g. 60Hz). RXDMA will need to start before interrupt as specified by the count-down timer. It supports SW fine-tuning of the count down timer for staying in sync with vsync. On low power system, this feature prevents SWI storm from swarming low power CPU
operating under DC. For vertically integration system, this can be done in touch controller
end-point. For horizontal platform, like IA, this feature allows THC get the same interrupt
coalescing with minimal/none vendor enabling commit. Refer to THC HAS for additional details
P0425: 
P0426: ### SW Controlled Coalescing with Converged Sync Event (LNL+)
P0427: 
P0428: Starting from LNL, THC added several new changes (covered in this section) to improve the accuracy of display and touch synchronization. This is done by either using an incoming HW display VBLANK/VSYNC from TCON or a timer emulated sync signal to THC. The timer emulated sync signal can be programmed by SW to trigger at the same cadence as display refresh rate.,
P0429: 
P0430: THC supports programming of the Sync source to be external vsync from TCON or timer emulation based on driver policy setting. This is done by programming the DISP_SYNC_EVT_SRC register. THC also supports a programmable delay after receiving sync event before a Sync interrupt is sent or coalescing begins. SW can choose the receive the Sync Event either immediately or after the programmed delay.
P0431: The sync event delay can be programmed using DISP_SYNC_DELAY and enabled using DISP_SYNC_COAL_DELAY_EN registers.
P0432: 
P0433: THC also supports timestamping of the sync event (VSYNC from TCON + timer emulated sync) as well as timestamping of TIC input reports. The timestamp information will be passed to an upper level filter driver for value added features such as Smoothing of incoming touch data based on the sync event. Refer to Touch Smart Filter SwAS for details on this interface.
P0434: 
P0435: Refer to the section titled “SW Controlled Coalescing with Converged Sync Event” in THC HAS for additional details on register definition and HW FSM.
P0436: 
P0437: 
P0438: ### AddDevice
P0439: 
P0440: As specified by KMDF and hidclass requirements QUICKI2C driver shall perform the basic driver tasks:
P0441: - Create and Initialize device context for HAL, DMA, HID etc. 
P0442: - Read configuration settings from registry and initialize driver internal state
P0443: - Create WDF Device Object
P0444: - Register PnP and Power event callbacks
P0445: - Register callback to pre-process Wait/Wake IRP and set internal flags which are used to send Set Power Sleep command to the Touch IC  during D0Exit.
P0446: - Create WdfQueue object to receive IOCTLs from hidclass.  Choose Dispatch type for this queue as parallel. 
P0447: - Create Manuel Queue object for Pending IOCTL requests (Read Reports, Get Feature etc.)
P0448: - Create Device Interface (GUID)
P0449: ### PrepareHw
P0450: PrepareHw is called by the KMDF infrastructure as a result of device resources being established. This could be the result of an initial system enumeration event or a resource re-balancing. While most initialization operations are contained in the D0Entry API, in PrepareHW the base driver maps its resources including the THC MMIO BAR and registers ISR and DPC to receive interrupts (i.e., MSI) from THC, though interrupts are not enabled at this time. In addition, the driver selects Port Type field in THC_M_PRT_CONTROL register as I2C (by setting value of 1). When Wake is enabled in BIOS (see _CRS wake resource definition in ACPI enumeration), an additional wake interrupt is passed to the driver in PrepareHardware. The KMDF framework automatically passes the Wait/Wake request down the stack and ACPI driver handles the wake completion. 
P0451: ### QUICKI2C D0Entry
P0452: At its most basic level D0Entry requires to the driver to bring the controller from D3 into a D0 state. For THC, there are specific bits in which SW uses to go between D0 and D3 to do this (please refer to the HAS).  However, additional initialization operations also occur at this time such as:
P0453: - I2C Protocol/Mode Initialization (section 4.2.2) 
P0454: - Read HID Device descriptor by using PIO Write-followed by-Read operation (HID Descriptor register number stored in ACPI). SWDMA option is also supported by HW to read HID descriptor.
P0455: - Allocating Read DMA, SW DMA and Write DMA buffers. Initialize the corresponding PRD tables
P0456: - Send Set Power ON command by issuing a PIO Write or TxDMA to the CommandRegister
P0457: - Send Reset command by issuing a PIO Write or TxDMA to initialize the device. Process reset interrupt by reading reset response 2Bytes (0000h) from the device using RxDMA. Reset command can be sent once per boot.
P0458: 
P0459: 
P0460: ### TIC Reset Exit Flow (i.e., Host Initiated Reset)
P0461: 
P0462: QUICKI2C Driver Initialization Operations:
P0463: QUICKI2C Driver initialization occurs in 2 stages: TIC initialization and DMA buffer allocation with associated DMA MMIO configuration. TIC initialization is described in the following section. In order to execute the TIC initialization the THC driver must execute PIO operations to the TIC Command register (defined in HIDI2C spec). As long as PCI enumeration is complete, with the BAR programmed the THC driver can execute PIO operations. None of the THC sequencer or DMA engines need to be programmed to for the TIC reset/initialization stage.
P0464: 
P0465: Pre-Conditions:
P0466: THC is in D0, MMIO BAR has been mapped.
P0467: Platform BIOS has successfully powered up the HIDI2C device and pulled it out of reset
P0468: 
P0469: Touch ICs that are compliant with HIDI2C protocol are not required to implement a dedicated reset line. However, device vendors may support a reset line, in which case, Host Platform BIOS shall support RTD3 to power up and drive the reset line to bring the device out of reset. Touch IC implementations typically need some delay after power up before they can take control of the reset line. This delay needs to be comprehended in BIOS RTD3 implementation. It is also worth noting that QuickI2C driver does not directly evaluate ACPI reset method.
P0470: 
P0471: Sequence of initialization steps in BIOS and QuickI2C driver that occur as part of the reset flow are:
P0472: - OS uses ACPI power management to start the D0 Entry flow
P0473: - In response, platform BIOS shall power up the device, wait for power-up-to-reset-assertion delay (vendor specific), drive the reset line high to bring the device out of reset. Note: Powering up of device should always be followed up by driving the Reset Line. In certain flows, for example, device resume due to a wake event, the device may not have been powered down. In such cases, the OSPM may not trigger the ACPI D0Entry flow.
P0474: - QUICKI2C driver ensures the THC is in D0 and the I2C protocol/mode initialization is complete
P0475: - Start by configuring interrupt mode as level triggered in THC, las specified in HIDI2C specification)
P0476: - Retrieve HID descriptor from the device. i.e., Write HID descriptor address and Read HID Descriptor
P0477: - Write SET_POWER command to the device
P0478: - Write HIDI2C Reset command (defined by the HIDI2C protocol) after first initialization to the TIC using PIO or TxDMA. See sections on I2C Write using PIO or TxDMA. This should initialize and prepare the device for usage. Note: After the first initialization, sending reset command from host to the device is optional. However, Host can send reset command as part of error handling at any time, for example, unable to retrieve report descriptor.
P0479: - Within 5 seconds, the device signals an interrupt to the host. In response, THC reads the reset response, DMA’s the reset response and sends  a data interrupt to QUICKI2C driver
P0480: - QUICKI2C driver processes the reset response from PRD buffer and validates that the reset response has input data length of 0x0000. 
P0481: - Any other input report received from the device before receiving the reset report should be discarded
P0482: - QuickI2C driver may issue the reset request either during the first device initialization or in response to any errors. The device should discard all previous states and initialize itself to start from scratch
P0483: 
P0484:  [IMAGE]
P0485: 
P0486:  [IMAGE]
P0487: 
P0488: ### Read Device Descriptor
P0489: 
P0490: Sequence of steps to read device descriptor:
P0491: - QUICKI2C driver reads the HID descriptor register (aka Device descriptor address) from ACPI table using _DSM method
P0492: - QuickI2C driver issues a PIO write followed by Read (see section on I2C Write followed by Read using PIO) to the HIDI2C device’s HID descriptor register 
P0493: - The following parameters need to be passed: Write size of 2 bytes with HID descriptor register, Read buffer with size of 30 bytes to hold the device descriptor response
P0494: - Complete the IOCTL_HID_GET_DEVICE_DESCRIPTOR with data from Read buffer, set the appropriate status to indicate success along with request information field set to size of output buffer or indicate failure status.
P0495:   [IMAGE]
P0496: 
P0497:   [IMAGE]
P0498: 
P0499: 
P0500: D0 entry is called for the following system states:
P0501: Standard boot Flow:
P0502: - Prior to this flow, BIOS initialized the controller into a D0 state.
P0503: - Prior to the D0Entry entry-point, PrepareHW would have been called where TIC enumeration and MMIO setup occurs. Therefore, the THC must be in a D0-State.
P0504: - Architectural Requirement --> must ensure the controller is in D0. Port_type must be set to I2C (0x01).
P0505: - This flow also includes where the driver is disabled, removed or re-installed because the stack will be torn down in this event.
P0506: 
P0507: Resume flow:
P0508: - The system is exiting Sx or Modern Standby (S0iX).
P0509: - The previous driver state was D0Exit and the controller is in D3.
P0510: - For details on the behavior in the D0Entry following D0Exit please see the THC Driver Power Management section.
P0511: 
P0512: Subsequent sections describes the main THC HW capabilities which the QUICKI2C driver interacts with and initializes the THC HW. The below items are done for each TIC (up to 
P0513: two) on the platform.
P0514: 
P0515: QUICKI2C driver Read DMA Buffers Initialization and Usage:
P0516: The QUICKI2C driver allocates read data buffers to receive various types of input report data (except device descriptor response) from the TIC. Most of the input report body read requests from the Touch IC including data, reset response, command response, get feature response, report descriptor, set feature response, set output report response, get input report response fall into this category.
P0517: 
P0518: QUICKI2C client driver’s use of RxDMA1 and RxDMA2:
P0519: In the QUICKI2C architecture, RxDMA1 engine is no longer used. RxDMA2 is associated with HID data and the THC HW has a read DMA engine and circular buffer dedicated for this engine. Vendor proprietary raw data format, unlike previous generation IPTS protocol, is not used in QUICKI2C implementation. 
P0520: 
P0521: QUICKI2C driver will automatically allocate buffers and a PRD table for RxDMA2 on its own during the initialization flow, immediately after reading device descriptor response. 
P0522: 
P0523: QUICKI2C driver Use of the Circular Buffer
P0524: The THC HW circular buffer allows the THC RxDMA engines to determine the next free read buffer and begin DMA-ing to that buffer without SW interaction. It is the responsibility of the QUICKI2C driver to initialize the circular buffer and advance the circular buffer write pointers once the driver has consumed the read buffer. The THC HW advances the read pointer once a read DMA is complete.
P0525: 
P0526: QUICKI2C Client driver Write DMA Usage and Initialization
P0527: The QUICKI2C driver automatically initializes the write DMA HW in this sequence. The QUICKI2C driver uses the Write DMA engine to write HIDI2C requests such as Reset, Output Report, Set Power, Set Protocol, Set Idle, Set Report etc. to the TIC. As write operations are synchronous requests from SW, no circular buffer exists to support the write DMA engine. The driver must manually start a write DMA operation and either poll for completion or wait for an interrupt. 
P0528:   {style: No Spacing}
P0529: ### Write DMA Init
P0530: The diagram below illustrates the write DMA registers and PRD structure. Unlike with the read DMA engines, the write DMA engine does not contain a circular buffer. The reason for this is that write DMAs are not executed via the HW sequencer. Rather, the write DMA operations are manually invoked via the QUICKI2C driver as a result of being requested by hidclass to write to to the TIC. Therefore, there is a single write DMA buffer associated with a single write DMA PRD.
P0531: 
P0532: Write DMA HW Initialization:
P0533: - QUICKI2C Driver determines the max write size based on wMaxOutputLength field of the Device Descriptor reported by Touch IC 
P0534: - QUICKI2C Driver allocates non-pageable virtual memory for the write buffer.
P0535: - QUICKI2C Driver requests the OS kernel to create an SGL (scatter-gather list) for the output buffer.
P0536: - QUICKI2C Driver allocates a physically contiguous memory buffer for the PRD table.
P0537: - QUICKI2C Driver converts the OS SGL to a PRD table and copies this to the contiguous memory region.
P0538: - QUICKI2C Driver initializes the THC MMIO space for the write data buffer DMA engine PRD tables.
P0539: 
P0540: During runtime operations, writes are accomplished by copying data to be written to the write buffer, and then by setting the Start bit. SW can use interrupts or poll on the Start bit for completion.
P0541:  [IMAGE]
P0542: Figure 7: THC Write Buffer Initialization
P0543: 
P0544: ### SW DMA Init
P0545: This section and the diagram below describe the Sw DMA theory of operation and initialization requirements for the THC HW and driver. Unlike with the read DMA engines, the Sw DMA engine does not contain a circular buffer. The reason for this is that SW DMAs are not executed via the HW sequencer. Rather, the SW DMA operations are manually invoked via the QUICKI2C driver as a result of being requested by hidclass to either retrieve read_report_descriptor or send Get_Report, Get_Idle, Get_Protocol  requests to the TIC. Therefore, there is a single Read DMA buffer associated with a single Read DMA PRD. Note: Get_Idle and Get_Protocol requests are optional on both Host and Device side.
P0546: 
P0547: 
P0548: Buffer Details:
P0549: The following description applies to CPU buffers.
P0550: - SW determines the max read size based on maximum of the following fields in device descriptor: wReportDescLength, wMaxInputLength (wMaxInputLength is for the case if we need to read any feature report and Report Descriptor using SwDMA) 
P0551: - QuickI2C driver allocates single SW DMA data buffer (non-pageable virtual memory) in host memory that is represented by a single PRD table. 
P0552: - SW requests the OS kernel to create an SGL (scatter-gather list) for the SW DMA Read buffer.
P0553: - SW allocates a physically contiguous memory buffer for the PRD table.
P0554: - SW converts the OS SGL to a PRD table and copies this to the contiguous memory region.
P0555: - SW initializes the THC MMIO space for the read data buffer DMA engine PRD tables.
P0556: - In order for HW to know which buffer is free (and for SW to indicate which buffers are free) a circular buffer shall be implemented.
P0557: - The CB (circular buffer) read pointer is controlled by HW.
P0558: - The CB write buffer is controller by SW.
P0559: - SW increments the CB to the amount of free buffers and if the HW is armed, via the Start bit, HW DMAs all the free buffers.
P0560: - When HW detects the write and read pointer are the same value it stops DMA-ing data until the write pointer is greater than the read pointer.
P0561: - An overrun bit indicates when SW has wrapped the write point over the size of the CB.
P0562: 
P0563: ### RxDMA2 Initialization
P0564: This section and the diagram below describe the read DMA and circular buffer theory of operation and initialization requirements for the THC HW and driver. 
P0565: 
P0566: Circular Buffer Details:
P0567: The following description applies to CPU buffers.
P0568: - In most cases we expect the CPU to process data faster than it is sent by THC. In rare cases SW processing will take longer than the data transfer across THC, resulting in a buffer overrun or touch frame being dropped.
P0569: - To mitigate this possibility host SW will allocate multiple data buffers in host memory that are represented by the multiple PRD tables.
P0570: - In order for HW to know which buffer is free (and for SW to indicate which buffers are free) a circular buffer shall be implemented.
P0571: - The CB (circular buffer) read pointer is controlled by HW.
P0572: - The CB write buffer is controller by SW.
P0573: - SW increments the CB to the amount of free buffers and if the HW is armed, via the Start bit, HW DMAs all the free buffers.
P0574: - When HW detects the write and read pointer are the same value it stops DMA-ing data until the write pointer is greater than the read pointer.
P0575: - An overrun bit indicates when SW has wrapped the write point over the size of the CB.
P0576: 
P0577: Typical Circular Buffer HW Operation Example:
P0578: For this example, SW allocates 4 raw data buffers and 4 PRD tables. This is just an example, as seen below 16 buffers will be in use.
P0579: - The read and write pointers are initialized to 0x0, thus the DMA engine will not run.
P0580: - SW moves the CB write pointer to a value of 0x80. This tells the HW that all 4 buffers are free.
P0581: - SW sets the Start bit.
P0582: - HW DMAs to all 4 PRD tables/raw data buffers. After each DMA completes, HW increments the read pointer. When the HW reaches a value of 0x3 for the read buffer and increments it again, the value will be 0x80 due to an increment of the overflow bit.
P0583: - SW detects buffer 0 is free (but buffers 1-3 are still in use) and increments the write pointer to 0x1.
P0584: - HW begins DMA-ing to buffer 0.
P0585: 
P0586: RxDMA Engine Usage Requirements:
P0587: The following are read DMA buffer and read PRD table allocation requirements for the QUICKI2C Driver:
P0588: - The QUICKI2C driver shall allocate 16 buffers to receive read data from the TIC.
P0589: - Each of the 16 buffers shall be allocated to the max data size as reported by the TIC, aligned and rounded up to a multiple of 4KB. The THC can support up to a 1MB buffer.
P0590: - The driver shall allocate 16 PRD tables, sized to hold enough PRD entries for worst-case fragmentation for the read data buffers. For example, if each read data buffer is 32KB, the driver will allocate 16 PRD tables with 8 entries in each of them. This will lead to wasted PRD entries in the case any of the 16 buffers is not fully fragmented (see below).
P0591: - For example, a buffer may be fully fragmented requiring the driver to use all 8 entries, while some read buffers may have zero fragmentation, requiring the driver to use only 1 entry.
P0592: - The driver will request the OS to build SGLs for the 16 read data buffers and initialize each PRD entry with SGL information from the OS.
P0593: - If all entries ar.e sized and aligned to 4KB, the unused entries shall be initialized to 0x00. This will allow the SW to detect frame babble (where TIC sends more data than it should) via the invalid PRD-Entry error in the HW. It's unlikely that the frame babble interrupt error cause bit won't be set because memory will not be fully fragmented in most cases.
P0594: 
P0595: Notes:
P0596: - After a read DMA, the HW will update the length of the PRD entries to reflect the length of the data transferred. After consuming a read-buffer, the driver shall update the length back to the original length initialized at boot.
P0597: - Up to 64 PRD tables can be allocated. The number of PRD tables equals the number of raw data buffers.
P0598: - Max OS memory fragmentation will be at a 4KB boundary, thus to address 1MB of virtually contiguous memory 256 PRD entries are required for a single PRD Table.
P0599: - It is expected that SW allocates all the raw data buffers and PRD tables at host initialization. Host SW will de-allocate the buffers and PRD during runtime only if the OS kernel requests the THC device to be disabled or stopped. Re-allocation of the buffers may occur again if the THC device is re-enabled. Buffer allocation and de-allocation shall only occur when the HW is completely quiesced.
P0600: 
P0601: Read DMA HW Initialization Basic Flow:
P0602: - QUICKI2C Driver determines the max size of a frame by reading the device descriptor provided by the Touch IC. wMaxInputLength fields is then rounded up to a 4KB multiple to determine the max size of a frame.
P0603: - QUICKI2C Driver allocates 16 (this number may change) non-pageable memory buffers for HID data. 
P0604: - Driver allocates physically contiguous memory for 16 PRD tables.
P0605: - Driver requests the OS kernel to create an SGL for each raw data buffer.
P0606: - Driver converts each SGL to a PRD table and copies this to the PRD contiguous memory region.
P0607: - Driver initializes the THC space for the RxDMA2 PRD tables.
P0608: - Driver resets the circular buffer read and writes pointers.
P0609: - Driver initializes the write pointer to the number of PRD tables - 1.
P0610: - Driver sets the RxDMA2 engine’s Start bit to a 1.
P0611: 
P0612: The DMA engine is now armed and waiting for the THC engine to fetch data from the Touch IC.
P0613:  [IMAGE]
P0614: 
P0615: Figure 8: HIDSCx Read DMA Initialization
P0616: 
P0617: ### Interrupt Enable
P0618: Interrupt enable is sent by the OS to inform the QUICKI2C driver that it can enable interrupts. Interrupts need to be enabled in THC HW before the QUICKI2C driver starts initializing the HIDI2C device.
P0619: 
P0620: ### Global Interrupt Enable
P0621: 
P0622: THS supports MSI and Line Based interrupt schemes. From LNL and onward, a global enable/disable bit is supported to simplify interrupt handling in the driver.
P0623: Refer to THS HAS for details on Enable THC Interrupt (GBL_INT_EN) bit defined in the register THC Interrupt Enable Register (THC_M_PRT_INT_EN)
P0624: 
P0625: 
P0626: 
P0627: 
P0628: 
P0629: ## QUICKI2C Driver HID Operations
P0630:  
P0631:   {style: Plain Text}
P0632: Figure 9: QUICKI2C Driver HID Operations
P0633:   {style: Plain Text}
P0634: Once the QUICKI2C driver is up and running, OS HID stack initializes and does enumeration of the touch devices on its own. This process starts with a fetch of the device descriptor from the QUICKI2C Driver to determine the determine attributes, sizes of various input reports, output reports, max input report length etc. Following this, the report descriptor is fetched by the hidclass to enumerate all the HID top-level collections for Touch, Pen, Heatmap and any other HID devices etc.  {style: Plain Text}
P0635:   {style: Plain Text}
P0636: At this point the Class driver will submit its input report request via sending IOCTL_HID_READ_REPORT  request to the QUICKI2C Client driver’s default queue which arms the QUICKI2C driver and allows the hidclass to consume an input report. While HID reports will be returned asynchronously to the class driver, Ouput Reports, Set Feature Reports and Get Feature Requests etc. will be sent synchronously.  {style: Plain Text}
P0637: 
P0638: # QUICKI2C Driver Runtime Operations
P0639: 
P0640: ## QUICKI2C Read Data Flows
P0641: 
P0642: ### Input Report Data Flow
P0643: The following is the primary data flow with or without feedback data.
P0644: 
P0645: Basic Flow:
P0646: - Touch IC asserts the interrupt indicating that it has an interrupt to send to HOST
P0647: THC Sequencer issues a READ request over the I2C bus. The HIDI2C device returns the first 2 bytes from the HIDI2C device which contains the length of the received data
P0648: - THC Sequencer continues the Read operation as per the size of data indicated in the length field
P0649: - THC DMA engine begins fetching data from the THC Sequencer and writes to host memory at PRD entry 0 for the current CB PRD table entry. THC writes 2Bytes for length field plus the remaining data to RxDMA buffer. This process continues until the THC Sequencer signals all data has been read or the THC DMA Read Engine reaches the end of it's last PRD entry (or both).
P0650: - THC Sequencer enters End-of-Input Report Processing.
P0651: - If the device has no more input reports to send to the host, it de-asserts the interrupt line. For any additional input reports, device keeps the interrupt line asserted and steps 1 through 4 in the flow are repeated.
P0652: 
P0653: THC Sequencer End of Input Report Processing:
P0654: - THC DMA engine increments the read pointer of the Read PRD CB, sets EOF interrupt status in RxDMA 2 register (THC_M_PRT_READ_DMA_INT_STS_2)
P0655: - If THC EOF interrupt is enabled by the driver in the control register (THC_M_PRT_READ_DMA_CNTRL_2), generates interrupt to software
P0656: 
P0657: Host Processing, Following End of Input Report:
P0658: - QUICKI2C driver dequeues one of the “ping-pong” read (IOCTL_HID_READ_REPORT) requests that was forwarded to the Input Report Queue by hidclass 
P0659: - QUICKI2C driver copies the input report from the PRD buffer to the output buffer of the read request and completes the read request. The information field of the request should be set to sizeof(Report ID)+ReportContentLength
P0660: - QUICKI2C driver validates Input Report Length and in case of any protocol or other transfer errors, QUICKI2C driver may reset the device to recover from errors
P0661: - After a read request gets completed by QUICKI2C driver, hidclass will send another request to the input report queue
P0662: - QUICKI2C Driver increments the write pointer of the Read PRD CB.
P0663: 
P0664: ### Input Reports
P0665: Input Reports are unidirectional reports that are sent from Device to Host. Refer to the HIDI2C protocol specification for more details. Read request IRP_MJ_READ is the primary mechanism for the Windows HID stack to receive input reports from the Touch IC. The read requests are sent by the hidclass to the InputReportQueue in ping-pong fashion. After a request is completed, another read request will be sent down to the device, allowing for continuous reporting of data. The read request is sent by the hidclass to the QUICKI2C driver after the stack has initialized. When this actions occurs for the first time it is a signal from the Class driver that it is ready to receive input buffers. 
P0666: ### Output Reports
P0667: Output reports are unidirectional reports that are sent from Host to Device. Refer to the HIDI2C protocol specification for more details. When the Host (refers to the hid software stack above QUICKI2C driver) has data that needs to be sent to the Device, it sends output report to the QUICKI2C driver. 
P0668: 
P0669: 
P0670: The driver write the SET_REPORT command to the command register as following:
P0671: 
P0672: 
P0673: 
P0674:   [IMAGE]
P0675: 
P0676: The driver then writes the report data to the data register as following:
P0677: - Length of report (2 bytes)
P0678: - Report including Report ID 
P0679: 
P0680: 
P0681: 
P0682: Generic Output Report Flow:
P0683: - HIDCLASS sends output request (IOCTL_HID_WRITE_REPORT  or IOCTL_HID_SET_OUTPUT_REPORT ) to the QUICKI2C driver. 
P0684: - SW uses PIO or TXDMA to write a SET_REPORT request to the command register as shown above. Report type in SET_REPORT should be set to Output.
P0685: - SW programs TxDMA buffer with TX Data to be written to the data register. As shown above, the first 2 bytes should indicate the length of the report followed by the report contents including Report ID. 
P0686: 
P0687: Important Notes: 
P0688: - Length field should always be greater than 3 bytes for a valid output report
P0689: - QUICKI2C Driver sets the Start bit in the THC Write DMA Control register.
P0690: - THC writes the TX DMA data to IC_DATA_CMD register of I2C SubIP one byte at a time. SW is not involved in the runtime low level IC_DATA_CMD operations. Output Register shown above is part of the HID device descriptor retrieved from the HIDI2C device.
P0691: - HW completes DMA, clears the Start bit, sets the completion status bit, and signals an interrupt to the SW. Unlike read DMA operations, write DMA only supports single PRD execution.
P0692: - QUICKI2C Driver reads the THC Write Interrupt Status register and clears the Status bit.
P0693: - Touch IC consumes the output report. There is no interrupt expected from the device for Output reports.
P0694: 
P0695: ### Commands
P0696: 
P0697: In addition to input and output reports, HIDI2C protocol supports commands that are unidirectional write commands as well as bi-directional Write-Read commands. 
P0698: 
P0699: Unidirectional write commands include Set_Report, Set_Idle, Set_Protocol, Set_Power, HIR (phase 1). These commands can be sent to the HIDI2C device using either TxDMA or PIO write operations. Refer to the I2C write sections in chapter 4.
P0700: 
P0701: Bi-directional commands involve sending a write followed by a repeated start and read to the HIDI2C device in a single transaction. Examples of these commands include: HID Descriptor retrieval, Report Descriptor retrieval, Get_report, Get_Idle, Get_protocol etc. 
P0702: These commands can be generated using either SWDMA or RW PIO. Refer to sections on SWDMA and I2C Write-Read using PIO in chapter 4.
P0703: 
P0704: ### Quiescing the THC
P0705: During system boot, TIC interrupts are quiesced by default when THC HW comes out of D3. In HIDI2C mode, QuickI2C driver doesn’t need to control the reset line directly. Similar to LPSS HIDI2C solution, control of power and reset line is expected to be handled by the platform BIOS. QuickI2C driver needs to send a reset command as specified in HIDI2C protocol to initialize the device. By the time the driver sends reset command, it is expected that the TIC is powered up and reset/initialization timings have been met. Therefore, there is no need to quiesce the TIC interrupts during D0Entry. However, there are other scenarios where touch interrupt may need to be quiesced. For example, before any change can be made to I2C protocol settings for PIO, SW DMA, RxDMA and TxDMA, touch device interrupts need to be quiesced. In addition, before starting SwDMA, QuickI2C driver needs to stop RxDMA and quiesce touch interrupts. Refer to section on SW DMA Init in chapter 4 to see the complete flow. 
P0706: ### HW/SW Interrupt Handling Behavior
P0707: The following flow chart pulls the HW Sequencer and DMA behavior into one diagram. As can be seen, all decision branches are based on Touch IC register reads of the Status and Frame Characteristics Registers. This diagram is informative and for details on the THC HW, please consult the HAS.
P0708: ### HW Sequencer Behavior
P0709:  [IMAGE]
P0710: Figure 10: HW Sequencer Flow Chart  
P0711: 
P0712: ### SW Interrupt Behavior
P0713: 
P0714:  
P0715: Figure 11: SW Interrupt Processing Flow  
P0716: 
P0717: ### ISR Behavior
P0718: THC HW supports both MSI and Line Interrupts, however, QUICKI2C will enable MSI for hardware interrupts. THC HW and SW use handshaking (referred to as Per-Vector Masking in PCI express base specification) to co-ordinate exactly when new interrupt messages are generated. With per-vector masking, when the software interrupt service routine begins, it masks all the interrupt sources (i.e., disable interrupt enable bits) to avoid spurious interrupts. After the DPC processes all the interrupt conditions that it is aware of, it unmasks all the interrupt sources (i.e., re-enable the interrupt enable bits). If new interrupt conditions remain, THC HW is required to generate a new interrupt message, guaranteeing that no interrupt events are lost. Here is basic flow that works for both MSI and Line Interrupt  {style: No Spacing}
P0719:   {style: No Spacing}
P0720: Basic Flow:
P0721: - Check for THC Interrupt Source (RxDMA1\2 EOF, TxDMA CMPL, NonDMA Int, PIO TSS Done), pending I2C subIP interrupts
P0722: - Mask all interrupt sources via the Global Interrupt Enable bit. The driver also has the option of selectively masking interrupt sources using individual IE Bits to avoid additional interrupts from HW
P0723: - Queue DPC to process pending interrupts
P0724: 
P0725: Workaround for potential race condition when using SWDMA
P0726: While handling SWDMA, make sure to not handling (accepting HW MSI for RxDMA for HID input).
P0727: ### DPC Behavior
P0728: Basic Flow:
P0729: - Read THC Read DMA Interrupt Status Register
P0730: - If error status is set, quiesce DMA and process error (DMA should be stopped anyway)
P0731: - If RxDMA EOF_INT_STS is set, the input report is complete so process it.
P0732: - If NONDMA_INT_STS is set, it's a non-data interrupt.
P0733: - Is PIO status is set, signal to the PIO Read/Write completion handler
P0734: - If DMACPL_STS is set in thc_m_prt_read_dma_int_sts_sw, continue to process the SwDMA request
P0735: - Unmask all Interrupts sources via Global IE bit. Alternatively, unmask individual IE Bits. 
P0736: 
P0737: Note: Refer to THC IP programming for I2C Sub-IP programming requirements
P0738: 
P0739: 
P0740: 
P0741: ### Interrupt Locks
P0742: Due to race condition that can be happened once IE are enabled in DPC, the race condition is that ISR clear the IE and DPC set them.
P0743: 
P0744: DPC acquired the ISR look (Wdf Interrupt Lock) before Enabling the IE bits and release it after all the bits are set. 
P0745: 
P0746: 
P0747: 
P0748: ## Error Handling Operations
P0749: 
P0750: Figure 12: QUICKI2C Error Handling Operations
P0751:   {style: Plain Text}
P0752: This diagram illustrates the error handling specific to THC HW and Touch IC reported errors. Use-case specific errors are detailed in their respective sections.   {style: Plain Text}
P0753: Unused-errors - The following THC errors are not implemented by either the SW or HW:  {style: Plain Text}
P0754: - Write DMA errors
P0755: - Fatal Errors
P0756: - PIO Errors
P0757: - I2C subIP Errors
P0758: 
P0759: QUICKI2C Driver examines the Interrupt Status transaction errors to acquire error information for the following error types:
P0760: - Invalid PRD Entry Error - This is a SW programming error which likely cannot be recovered from.
P0761: - Frame babble errors - This is a TIC error that can be recovered from. It indicates that the data size indicated in the input report length is larger than the PRD table size (max size of input report indicated in the device descriptor). As shown in the diagram, Frame Babble may manifest itself as an Invalid PRD error.
P0762: - PRD RxBuffer Overrun Error - This is a system-SW level error that can be recovered from.
P0763: - THC Rx Buffer Overrun - This is an IOSF error generated when the fabric cannot keep up with the traffic from the TIC.
P0764: - SW Sequencing (AKA PIO) Error - This is a SW bug that likely cannot be recovered from.
P0765: - Protocol Errors – Rely on HID class level to handle.
P0766: - NVLD_DEV_ENTRY error (one of the types of transaction errors). This error might occur due to invalid length field of incoming data – Rely on HID class level to handle.   Use Max input size (see workaround settings) to avoid delay of large read.
P0767: 
P0768: All the above errors shall be programmed by the QUICKI2C driver to stop the DMA operations in the THC. All these events would result in a TIC Reset.
P0769: 
P0770: Notes: 
P0771: From the THC HAS: · THC supports the bus clear feature that provides graceful recovery of data (SDA) and clock (SCL) lines during unlikely events in which either the clock or data line is stuck at LOW. SW can follow the steps described in the DW_apb_i2c datasheet section 2.11 Bus Clear Feature to recover from the bus errors.
P0772: 
P0773: ### SW Sequencing (PIO) Error
P0774: A SW sequencing error occurs when SW sends B2B PIO operations before a previous PIO operation completed. This is an indication of a programming bug which likely cannot be recovered from. SW should log an error with the OS.
P0775: 
P0776: In response the QUICKI2C driver shall:
P0777: - Reset TIC to ensure it is in a clean state because Touch IC is in an unknown state.
P0778: - Cleanup, restart DMA
P0779: - Complete the Reset response in HID Reset pending IOCTL
P0780: ### Read DMA Errors
P0781: Frame Babble Error Interrupt:
P0782: - Occurs when the data to be read from the TIC is larger than the PRD receive buffer.
P0783: - The QUICKI2C driver will invoke Reset Flow
P0784: 
P0785: PRD Table Overflow (i.e., Stall Error):
P0786: - This occurs when the Read and Write Pointers for CB are the same, when a touch-read interrupt occurs.
P0787: - The sequencer requests the DMA to begin data transfer, but the DMA engine does not.
P0788: - The THC Controller will drain the data from the Touch IC but not DMA the data to the host.
P0789: - When the write pointer is moved by the host DMA resumes
P0790: - On LNL and later, [PCR: https://hsdes.intel.com/appstore/article/#/14011950004] If the bit
THC_STALL_READ_EN_1/2=0, in the event that a TIC device touch data interrupt is received
while the PRD table is empty, HW shall temporarily stop reading the TIC device data frames
and resume reading TIC data when the PRD table is not empty
P0791: - THC_STALL_READ_EN_1/2=1, HW does not stop reading data from TIC in this scenario and will trigger a STALL event and start dropping frames(SOO=0) or stop RXDMA(SOO=1) until the PRD table is not empty.
P0792: - The QUICKI2c driver handles this error by invoking Reset Flow
P0793: 
P0794: THC Buffer Overrun:
P0795: - This occurs when the TIC sends data faster than the THC Controller/host can handle due to IOSF bottleneck, etc.
P0796: - The QUICKI2C driver will invoke Reset Flow
P0797: 
P0798: Invalid PRD Entry:
P0799: - This occurs when the length of the PRD entry is 0.
P0800: - This is a SW bug and cannot be recovered from.
P0801: 
P0802: 
P0803: Read DMA Engine reaches the end of the PRD entry list:
P0804: - DMA engine halts, interrupts with an error.
P0805: 
P0806: Write DMA Engine Write Length Error:
P0807: - Write Length field is greater than the PRD entries account for.
P0808: - Error interrupt is specified with specific error flagged in the Write DMA Error Register.
P0809: 
P0810: ### THC D3
P0811: - When THC enters D3 either due to Monitor Off or other OS events , Touch IC will be placed in reset (except when Touch is placed into Wakeable mode) and Touch IC is not expected to generate any interrupts to Host. Therefore, Active and Low Power LTR can both be disabled in THC. 
P0812: 
P0813:   {style: No Spacing}
P0814: ## Tap to Wake
P0815: Tap to wake provide a mechanism to wake the device (Platform) from Modern Standby from the TIC, for example by tapping twice on the screen. Refer to the Wake-on-Touch implementation guide on Windows: https://docs.microsoft.com/en-us/windows-hardware/design/component-guidelines/wake-on-touch-implementation-guide#device-posture [LINKS: https://docs.microsoft.com/en-us/windows-hardware/design/component-guidelines/wake-on-touch-implementation-guide#device-posture]
P0816: 
P0817: As described in the Microsoft requirements to enable Wake on Touch with a custom HID mini driver, QuickI2C driver needs to add the following entries in its INF file:
P0818: 
P0819: Include = input.inf
P0820: Needs = WakeScreenOnTouch.HW
P0821: 
P0822: We need to make sure that this key is added only for Touch screen endpoints. If the endpoint is Touch Pad , this key should not be added which will have undesired effects . This key is usually added as part of an extension INF 
P0823: ### Tap to Wake (Wakeable Mode) Entry
P0824: In Wakeable mode the TIC is move to a special Sleep power state and it is not put into Off state:
P0825: - OS decided to enter to Modern Standby (MS)
P0826: - OS HID class stack send wake wait request to the QUICKI2C Driver.
P0827: - In Windows:
P0828: - If driver was able handle the Wait Wake IRP it should pass it down to the next level driver. If not, it should complete it with error.
P0829: - Windows Wait Wake IRP (https://docs.microsoft.com/en-us/windows-hardware/drivers/kernel/irp-mn-wait-wake) [LINKS: https://docs.microsoft.com/en-us/windows-hardware/drivers/kernel/irp-mn-wait-wake]
P0830: - https://docs.microsoft.com/en-us/windows-hardware/drivers/kernel/understanding-the-path-of-wait-wake-irps-through-a-device-tree [LINKS: https://docs.microsoft.com/en-us/windows-hardware/drivers/kernel/understanding-the-path-of-wait-wake-irps-through-a-device-tree]
P0831: - 
P0832: - Once QUICKI2C Driver get the Wait Wake Request, QUICKI2C driver marks Driver Internal State as entering into Wakeable Mode
P0833: - Upon receiving D0Exit request, QUICKI2c driver sends SET_POWER (sleep) command (via TxDMA or PIO Write) to the TIC 
P0834: - OS moves QUICKI2C device to D3
P0835: - QUICKI2C driver completes D3 Entry Flow.
P0836: 
P0837: Platform/OS dependencies for Wake on Touch:
P0838: - “Touch the screen to wake” is enabled in the OS under “Bluetooth & devices -> Touch” settings page (see the Microsoft link above)
P0839: - SoC supports Virtual GPIOs for THC
P0840: - THC virtual GPIO interrupt (Platform/SoC specific designated) exposed as “ExclusiveAndWake” resource in ACPI _CRS method under respective THC device scope
P0841: - BIOS configures the Virtual GPIO in GPIO Mode
P0842: - GPIO Controller driver uses the correct offset for the Virtual GPIO to enable the interrupt when requested by ACPI driver (during processing of Wait/Wake IRP)
P0843: - QUICKI2C driver completes D3 Entry Flow.
P0844: - Refer to the BKM attached in this email 
P0845: - 
P0846: 
P0847: ### Tap to Wake (Wakeable Mode) Exit
P0848: - TIC send wake interrupt to THC HW
P0849: - ACPI and OS HID Class wake the platform from MS
P0850: - QUICKI2C driver receives D0 Entry and detects that it is in Wakeable mode. QUICKI2C client driver sends command (via TxDMA or PIO Write) SET_POWER (ON) to the TIC 
P0851: - Then continue without sending any Reset command
P0852: 
P0853: 
P0854: 
P0855: ## Workaround Settings
P0856: 
P0857: ### HIDI2C Compliance 
P0858: 
P0859: During the process of enabling the CCG HIDI2C protocol for a specific touch panel (Elan), it was identified that the panel exhibits two behaviors that are out of specification with HIDI2C. To support this vendor effectively, the following changes are proposed:
P0860: 
P0861: - HIDI2C Max Frame Size Adjustment:
P0862: - Implement a maximum frame size to handle cases where the panel indicates an incorrect frame length.
P0863: - Programmable Interrupt Quiescing Delay:
P0864: - Introduce a delay from the end of the current I2C frame before checking the interrupt again. This adjustment applies specifically to I2C level interrupts.
P0865: More details can be found
P0866: 22018840877 - Out of HIDI2C Spec low cost volume touch panel support [LINKS: 22018840877 - Out of HIDI2C Spec , low cost,  volume touch panel support]
P0867: PTL Workaround Settings are summarized below

P0868: 
P0869: ### ECO fix workaround Configuration settings
P0870: This document provides an overview of the I2C configuration settings available through both registry and BIOS options. By default, all settings are disabled, meaning the workaround is idle unless explicitly enabled.
P0871: #### Registry Settings
P0872: - I2C_Max_Frame_Size_Enable
P0873: - Controls whether the maximum frame size feature is enabled.
P0874: - I2C_Max_Frame_Size
P0875: - Specifies the maximum frame size value. The supported range is from 128 to 255, with 255 being the maximum value.
P0876: - I2C_Int_Delay_Enable
P0877: - Controls whether the interrupt delay feature is enabled.
P0878: - I2C_Int_Delay
P0879: - Specifies the interrupt delay value. For PTL and WCL platforms, if enabled, the delay defaults to 1ms regardless of user input. For upcoming platforms, the delay should be set as a multiple of 10 microseconds (uS).
P0880: #### BIOS Settings
P0881: - I2C Max Frame Size
P0882: - Options: Enabled/Disabled
P0883: - When enabled, allows configuration of the maximum frame size.
P0884: - I2C Max Frame Size Value
P0885: - Accepts values between 128 and 255, with 255 being the maximum supported value.
P0886: - I2C Interrupt Delay
P0887: - Options: Enabled/Disabled
P0888: - When enabled, allows configuration of the interrupt delay.
P0889: - I2C Interrupt Delay Value
P0890: - For PTL and WCL platforms, the delay defaults to 1ms if enabled, regardless of user input.
P0891: - For upcoming platforms, the delay should be set as a multiple of 10 microseconds (uS). For example, a value of 100 results in a delay of 1000uS (1ms).
P0892: ### Recommendations
P0893: - I2C Max Frame Size Value: It is recommended to set this value between 128 and 255 for optimal performance.
P0894: - I2C Interrupt Delay Value: For upcoming platforms, ensure the delay value is a multiple of 10uS to achieve the desired delay in microseconds.
P0895: This documentation serves as a guide for configuring I2C settings to optimize performance and compatibility across different platforms.
P0896: Note that the valid value of all max frame size and quiescing delay (supported by THC HW) is implementation specific. 
P0897: ### Other Workaround Settings
P0898: 
P0899: Workaround for Reset Request Handling in Touch Panels
P0900: 
P0901: In certain touch panels, it has been observed that sending a reset request does not elicit a response. Despite this lack of response, the LPSS driver continues to advance the state machine. To replicate this behavior, a new configuration key has been introduced:
P0902: 
P0903: - Key: DoNotWaitForResetResponse
P0904: - Default Value: 0
P0905: - Description: By default, the system waits for a response after sending a reset request.
P0906: - Value if Set to 1:
P0907: - Description: When set to 1, the system sends the reset request but does not wait for a response before proceeding. This allows the state machine to continue without delay, mimicking the behavior observed in some panels.
P0908: 
P0909: 
P0910: Other work arounds :

=== TABLE 7 (rows=7, cols=3) ===
  T7R000: Registry Entry || Default value || Optional
  T7R001: "EnEdgeTriggeredINT" || 0 (Level triggered interrupts) || 1 (Edge triggered interrupts)
  T7R002: "TimeStampEnable" || 1 (Timestamp enabled by default) || 
  T7R003: "ResetRequiredByDriver" || 0 (default always 0, as I2C doesnt need to be reset by signal on reset line) || 1 (To be enabled when using FPGA)
  T7R004: "ISRDPCProfilingEn" || 0 || 1 (To be used while measuring ISR to DPC delay)
  T7R005: "EnResetPollingWA" || 1 (enabled default) | It will read Reset response by polling and enable interrupts only after reading report descriptor || 0 (If want to disable this work around and read reset response using interrupt method)
  T7R006: "EnableFWFlashWABOM36" || 0 (disabled default) || 1 (enable if faced FW flash on BOM36. | Either this WA or "I2C_Int_Delay_Enable" and "I2C_Int_Delay" | Need tonenable
=== END TABLE 7 ===

P0911: 
P0912: 
P0913: 
P0914: 
P0915: 
P0916: 
P0917: 
P0918: 
P0919: 
[FOOTER Section 0]: Intel Confidential 40	

=== DOCUMENT PROPERTIES ===
Title: 
Author: Paithara Balagangadhara, Sai Prasad
Last Modified By: Cheng, Anton
Created: 2025-09-11 03:17:00+00:00
Modified: 2026-01-30 17:06:00+00:00
Revision: 4
Subject: 
Keywords: CTPClassification=CTP_NT
Category: 
Comments: 

# EXTRACTION STATS
# Paragraphs processed: 920
# Tables processed: 7
# Total output lines: 1035