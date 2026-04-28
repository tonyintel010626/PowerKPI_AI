#!/usr/bin/env python3
"""
HSDES Sighting Query Module for Power Debugging with GENI and Co-DeSign MCP

This module uses GENI and Co-DeSign MCP to intelligently search for relevant sightings
based on power, IFWI, and SocWatch data from results.json. It bucketizes and ranks
sightings by relevance:
1. IFWI version match (exact → major → minor)
2. Workload type match (IDON, CMS, ICOB, etc.)
3. Power rail keyword match
4. C-state residency keyword match
5. Platform match

The agent will use this data to query GENI and Co-DeSign MCP for intelligent sighting search.

Author: PowerKPI_Validator
Date: 2026-04-09
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HSDESPowerDebugger:
    """
    Intelligently search for relevant HSDES sightings using GENI and Co-DeSign MCP.
    
    This class extracts power debug context from test results and generates structured
    search requests for the PowerKPI_Validator agent to query via GENI/Co-DeSign MCP.
    
    Ranking Criteria (Priority Order):
    1. IFWI version match (exact → major → minor)
    2. Workload type match (IDON, CMS, ICOB, etc.)
    3. Power rail keyword match (high power on specific rails)
    4. C-state residency keyword match (PC0 high, PC10 low)
    5. Platform match (NVL, PTL, LNL, etc.)
    """
    
    def __init__(self):
        """Initialize the HSDES debugger with MCP-based search."""
        logger.info("HSDES Power Debugger initialized for GENI/Co-DeSign MCP integration")
    
    def parse_power_value(self, value) -> float:
        """
        Parse power value from various formats to float.
        
        Handles:
        - String with units: "0.255246 ampere" → 0.255246
        - Quantity objects: Quantity(0.255246, 'ampere') → 0.255246
        - Float/int: 0.255246 → 0.255246
        
        Args:
            value: Power value in any format
            
        Returns:
            Float value
        """
        if isinstance(value, str):
            try:
                # Extract numeric part before the unit
                return float(value.split()[0])
            except (ValueError, IndexError):
                return 0.0
        elif hasattr(value, 'magnitude'):
            return float(value.magnitude)
        elif value is not None:
            return float(value)
        else:
            return 0.0
    
    def extract_debug_context_from_results(self, results_json_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive debugging context from results.json file.
        
        This extracts all relevant information needed for intelligent sighting search:
        - IFWI/BIOS version
        - Workload name and type
        - High power rails (with values)
        - SocWatch Package C-state residencies
        - Bad residency patterns
        - Platform information
        - Driver versions
        
        Args:
            results_json_path: Path to the results.json file
            
        Returns:
            Dictionary containing complete debug context
        """
        logger.info(f"Extracting debug context from: {results_json_path}")
        
        with open(results_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        context = {
            'workload_name': None,
            'workload_type': None,  # IDLE, CMS, ICOB, etc.
            'high_power_rails': [],
            'socwatch_metrics': {},
            'ifwi_version': None,
            'bios_version': None,
            'platform': None,
            'hostname': None,
            'socwatch_version': None,
            'bad_residency': [],
            'driver_versions': {},
            'pmc_version': None,
            'test_date': None
        }
        
        # Extract workload name
        hopper = data.get('hopper', {})
        context['workload_name'] = hopper.get('name', 'Unknown')
        
        # Infer workload type from folder name or workload name
        results_path = Path(results_json_path)
        folder_name = results_path.parent.name.upper()
        
        # Map common workload patterns
        if 'IDON' in folder_name or 'IDLE' in folder_name.upper():
            context['workload_type'] = 'IDON'
        elif 'CMS' in folder_name or 'STANDBY' in folder_name:
            context['workload_type'] = 'CMS'
        elif 'ICOB' in folder_name or 'CATAPULT' in folder_name:
            context['workload_type'] = 'ICOB'
        elif 'NETFLIX' in folder_name:
            context['workload_type'] = 'NETFLIX'
        elif 'YOUTUBE' in folder_name:
            context['workload_type'] = 'YOUTUBE'
        elif 'TEAMS' in folder_name or 'MS_TEAMS' in folder_name:
            context['workload_type'] = 'MS_TEAMS'
        else:
            context['workload_type'] = context['workload_name']
        
        # Extract test date from folder name (format: 20260409T030304)
        date_match = re.search(r'(\d{8})', folder_name)
        if date_match:
            context['test_date'] = date_match.group(1)
        
        # Extract power rail data from 'power' section (DAQ data)
        power = data.get('power', {})
        for rail_name, rail_data in power.items():
            if isinstance(rail_data, dict) and 'default' in rail_data:
                default_data = rail_data['default']
                mean_value = default_data.get('mean')
                unit = default_data.get('unit', '')
                
                if mean_value is not None:
                    context['high_power_rails'].append({
                        'name': rail_name,
                        'mean': mean_value,
                        'unit': unit,
                        'min': default_data.get('min'),
                        'max': default_data.get('max')
                    })
        
        # Sort power rails by mean value (descending)
        context['high_power_rails'] = sorted(
            context['high_power_rails'], 
            key=lambda x: x['mean'], 
            reverse=True
        )
        
        # Extract SocWatch C-state residency data
        hopper_subtests = hopper.get('subtests', [])
        for subtest in hopper_subtests:
            result_groups = subtest.get('result_groups', [])
            for group in result_groups:
                if group.get('name') == 'socwatch':
                    # Extract SocWatch version
                    config = group.get('configuration', {})
                    context['socwatch_version'] = config.get('version', 'Unknown')
                    
                    # Extract C-state residencies
                    results = group.get('results', [])
                    for result in results:
                        name = result.get('name', '')
                        value = result.get('value', '')
                        unit = result.get('unit', '')
                        
                        # Look for Package C-state residencies (%)
                        if 'Package Residency (%)' in name and 'PC' in name:
                            try:
                                residency_pct = float(value)
                                cstate = name.split(':')[0].strip()
                                context['socwatch_metrics'][cstate] = {
                                    'residency': residency_pct,
                                    'unit': unit
                                }
                                
                                # Flag bad residencies
                                # IDLE workloads: PC0 should be low (<30%), PC10 should be high (>50%)
                                if context['workload_type'] in ['IDON', 'IDLE']:
                                    if 'PC0' in cstate and residency_pct > 30.0:
                                        context['bad_residency'].append({
                                            'state': cstate,
                                            'residency': residency_pct,
                                            'issue': f'High PC0 residency: {residency_pct}% (expected <30% for IDLE)',
                                            'severity': 'HIGH'
                                        })
                                    elif 'PC10' in cstate and residency_pct < 50.0:
                                        context['bad_residency'].append({
                                            'state': cstate,
                                            'residency': residency_pct,
                                            'issue': f'Low PC10 residency: {residency_pct}% (expected >50% for IDLE)',
                                            'severity': 'HIGH'
                                        })
                                
                                # CMS workloads: Should enter PC10 during sleep
                                elif context['workload_type'] == 'CMS':
                                    if 'PC10' in cstate and residency_pct < 80.0:
                                        context['bad_residency'].append({
                                            'state': cstate,
                                            'residency': residency_pct,
                                            'issue': f'Low PC10 residency: {residency_pct}% (expected >80% for CMS)',
                                            'severity': 'HIGH'
                                        })
                                
                            except (ValueError, IndexError):
                                continue
        
        # Try to extract IFWI/BIOS version from log file
        log_files = list(results_path.parent.glob("*-log.txt"))
        if log_files:
            try:
                with open(log_files[0], 'r', encoding='utf-8', errors='ignore') as log:
                    log_content = log.read()
                    
                    # Search for IFWI version patterns
                    ifwi_patterns = [
                        r'IFWI[:\s]+([A-Z0-9._\-]+)',
                        r'BIOS[:\s]+([A-Z0-9._\-]+)',
                        r'Firmware[:\s]+([A-Z0-9._\-]+)'
                    ]
                    for pattern in ifwi_patterns:
                        match = re.search(pattern, log_content, re.IGNORECASE)
                        if match:
                            context['ifwi_version'] = match.group(1)
                            context['bios_version'] = match.group(1)
                            break
                    
                    # Search for platform/hostname
                    hostname_match = re.search(r'Hostname[:\s]+([A-Z0-9\-_]+)', log_content, re.IGNORECASE)
                    if hostname_match:
                        context['hostname'] = hostname_match.group(1)
                        
                        # Infer platform from hostname (e.g., PG16WVAW3087 → NVL)
                        hostname = context['hostname'].upper()
                        if 'NVL' in hostname or 'PG16' in hostname:
                            context['platform'] = 'NVL'
                        elif 'PTL' in hostname or 'PG17' in hostname:
                            context['platform'] = 'PTL'
                        elif 'LNL' in hostname or 'PG15' in hostname:
                            context['platform'] = 'LNL'
                        elif 'MTL' in hostname:
                            context['platform'] = 'MTL'
                        elif 'ARL' in hostname:
                            context['platform'] = 'ARL'
            
            except Exception as e:
                logger.warning(f"Could not extract IFWI/platform from log: {e}")
        
        logger.info(f"Extracted context: {context['workload_type']} on {context['platform']} "
                   f"with {len(context['high_power_rails'])} power rails, "
                   f"{len(context['bad_residency'])} residency issues")
        
        return context
    
    def classify_issue_type(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        FIRST STEP: Classify what type of issue this is.
        
        Determines root cause categories:
        - Driver causing high power (USB, Audio, GbE, etc.)
        - Driver causing bad Package C-state residency
        - Power spikes with specific IP blocks (Audio, Display, etc.)
        - BIOS/IFWI configuration issue
        - Hardware/platform issue
        
        Args:
            context: Debug context from extract_debug_context_from_results()
            
        Returns:
            List of issue classifications with confidence scores
        """
        issues = []
        
        # Analyze power rails to identify IP blocks with high power
        high_power_ips = []
        for rail in context.get('high_power_rails', [])[:10]:
            rail_name = rail['name'].upper()
            mean_value = self.parse_power_value(rail['mean'])
            
            # Map rail names to IP blocks
            if 'AUDIO' in rail_name or 'ACE' in rail_name or 'HDA' in rail_name:
                high_power_ips.append({'ip': 'Audio', 'rail': rail['name'], 'power': mean_value})
            elif 'USB' in rail_name or 'XHCI' in rail_name or 'TCSS' in rail_name:
                high_power_ips.append({'ip': 'USB/TCSS', 'rail': rail['name'], 'power': mean_value})
            elif 'GBE' in rail_name or 'ENET' in rail_name or 'LAN' in rail_name:
                high_power_ips.append({'ip': 'GbE/Ethernet', 'rail': rail['name'], 'power': mean_value})
            elif 'DISPLAY' in rail_name or 'GPU' in rail_name or 'GFX' in rail_name:
                high_power_ips.append({'ip': 'Display/GPU', 'rail': rail['name'], 'power': mean_value})
            elif 'VCCCORE' in rail_name or 'CORE' in rail_name:
                high_power_ips.append({'ip': 'CPU Core', 'rail': rail['name'], 'power': mean_value})
        
        # Issue 1: Driver causing high power
        if high_power_ips and context['workload_type'] in ['IDON', 'IDLE', 'CMS']:
            for ip_data in high_power_ips:
                issues.append({
                    'category': 'DRIVER_HIGH_POWER',
                    'description': f"{ip_data['ip']} driver may be causing high power consumption",
                    'evidence': f"{ip_data['rail']} shows {ip_data['power']:.4f}A during {context['workload_type']}",
                    'confidence': 'HIGH',
                    'keywords': [
                        f"{ip_data['ip']} driver",
                        f"{ip_data['ip']} high power",
                        f"{ip_data['rail']}",
                        'power consumption',
                        'driver issue'
                    ]
                })
        
        # Issue 2: Driver/IP causing bad Package C-state residency
        if context.get('bad_residency'):
            for issue in context['bad_residency']:
                if 'PC0' in issue['state'] and issue['residency'] > 30.0:
                    # High PC0 means CPU is not entering deep C-states
                    # This is often caused by driver activity or hardware blockers
                    issues.append({
                        'category': 'DRIVER_BAD_CSTATE',
                        'description': f"Driver or IP block preventing Package C-state entry (high PC0)",
                        'evidence': issue['issue'],
                        'confidence': 'HIGH',
                        'keywords': [
                            'Package C-state',
                            'PC0 high',
                            'C-state blocker',
                            'residency',
                            'driver preventing sleep',
                            f"{context['workload_type']} residency"
                        ]
                    })
                    
                    # Add specific IP keywords if we have high power from those IPs
                    for ip_data in high_power_ips:
                        issues[-1]['keywords'].extend([
                            f"{ip_data['ip']} blocking C-state",
                            f"{ip_data['ip']} preventing PC10"
                        ])
                
                elif 'PC10' in issue['state'] and issue['residency'] < 50.0:
                    # Low PC10 residency
                    issues.append({
                        'category': 'PC10_ENTRY_BLOCKED',
                        'description': f"Package not entering PC10 (low residency)",
                        'evidence': issue['issue'],
                        'confidence': 'HIGH',
                        'keywords': [
                            'PC10 low',
                            'PC10 entry blocked',
                            'Package C-state',
                            'deep C-state',
                            'S0ix blocked',
                            f"{context['workload_type']} PC10"
                        ]
                    })
        
        # Issue 3: Power spikes with specific IP blocks
        # Look for specific patterns in rail names
        audio_rails = [r for r in context.get('high_power_rails', []) if 'AUDIO' in r['name'].upper() or 'ACE' in r['name'].upper()]
        if audio_rails and self.parse_power_value(audio_rails[0]['mean']) > 0.05:  # Threshold for audio power spike
            mean_val = self.parse_power_value(audio_rails[0]['mean'])
            issues.append({
                'category': 'AUDIO_POWER_SPIKE',
                'description': f"Audio subsystem showing power spike",
                'evidence': f"{audio_rails[0]['name']} = {mean_val:.4f}A (unexpected for {context['workload_type']})",
                'confidence': 'MEDIUM',
                'keywords': [
                    'Audio power spike',
                    'Audio high power',
                    'ACE power',
                    'HDA power',
                    audio_rails[0]['name'],
                    f"Audio {context['workload_type']}"
                ]
            })
        
        display_rails = [r for r in context.get('high_power_rails', []) if 'DISPLAY' in r['name'].upper() or 'GPU' in r['name'].upper()]
        if display_rails and self.parse_power_value(display_rails[0]['mean']) > 0.1:
            mean_val = self.parse_power_value(display_rails[0]['mean'])
            issues.append({
                'category': 'DISPLAY_POWER_SPIKE',
                'description': f"Display/GPU subsystem showing power spike",
                'evidence': f"{display_rails[0]['name']} = {mean_val:.4f}A",
                'confidence': 'MEDIUM',
                'keywords': [
                    'Display power spike',
                    'GPU high power',
                    'Display power',
                    display_rails[0]['name'],
                    f"Display {context['workload_type']}"
                ]
            })
        
        usb_rails = [r for r in context.get('high_power_rails', []) if 'USB' in r['name'].upper() or 'TCSS' in r['name'].upper()]
        if usb_rails and self.parse_power_value(usb_rails[0]['mean']) > 0.05:
            mean_val = self.parse_power_value(usb_rails[0]['mean'])
            issues.append({
                'category': 'USB_POWER_SPIKE',
                'description': f"USB/TCSS subsystem showing power spike",
                'evidence': f"{usb_rails[0]['name']} = {mean_val:.4f}A",
                'confidence': 'MEDIUM',
                'keywords': [
                    'USB power spike',
                    'TCSS high power',
                    'USB high power',
                    usb_rails[0]['name'],
                    f"USB {context['workload_type']}"
                ]
            })
        
        # Issue 4: BIOS/IFWI configuration issue
        # If we have bad residency but no obvious high power IP
        if context.get('bad_residency') and not high_power_ips:
            issues.append({
                'category': 'BIOS_CONFIG_ISSUE',
                'description': f"Potential BIOS/IFWI configuration preventing proper C-states",
                'evidence': f"Bad residency with no obvious high-power IP block",
                'confidence': 'MEDIUM',
                'keywords': [
                    'BIOS configuration',
                    'IFWI issue',
                    'C-state configuration',
                    'Package C-state knob',
                    f"IFWI {context.get('ifwi_version', 'unknown')}"
                ]
            })
        
        # Issue 5: General high power with no specific blocker
        total_power = sum(self.parse_power_value(r['mean']) for r in context.get('high_power_rails', []))
        if total_power > 0.5 and context['workload_type'] in ['IDON', 'IDLE']:  # 500mA is high for idle
            issues.append({
                'category': 'GENERAL_HIGH_POWER',
                'description': f"Overall platform high power consumption",
                'evidence': f"Total power ~{total_power:.2f}A during {context['workload_type']}",
                'confidence': 'MEDIUM',
                'keywords': [
                    'high power',
                    'platform power',
                    f"{context['workload_type']} high power",
                    'power consumption',
                    f"{context.get('platform', 'unknown')} power"
                ]
            })
        
        return issues
    
    def build_mcp_search_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build structured search request for GENI/Co-DeSign MCP with ranking criteria.
        
        This creates a hierarchical search request that the agent can use to query
        GENI and Co-DeSign, with clear ranking priorities.
        
        Args:
            context: Debug context from extract_debug_context_from_results()
            
        Returns:
            Structured search request dictionary for MCP queries
        """
        # FIRST STEP: Classify the issue type
        issue_classifications = self.classify_issue_type(context)
        
        search_request = {
            'search_type': 'hsdes_sighting_power_debug',
            'issue_classifications': issue_classifications,  # NEW: Issue type classification
            'ranking_criteria': [
                'Issue type match',  # NEW: Highest priority
                'IFWI version match',
                'Workload type match',
                'Power rail keyword match',
                'C-state residency keyword match',
                'Platform match'
            ],
            'primary_filters': {
                'ifwi_version': context.get('ifwi_version'),
                'workload_type': context.get('workload_type'),
                'platform': context.get('platform')
            },
            'power_context': {
                'top_high_power_rails': [
                    {
                        'name': rail['name'],
                        'mean': rail['mean'],
                        'unit': rail['unit']
                    }
                    for rail in context.get('high_power_rails', [])[:5]
                ],
                'total_rails_analyzed': len(context.get('high_power_rails', []))
            },
            'residency_context': {
                'bad_residency_issues': context.get('bad_residency', []),
                'cstate_metrics': context.get('socwatch_metrics', {})
            },
            'keywords': {
                'tier1_mandatory': [],  # Must match
                'tier2_high_priority': [],  # Should match
                'tier3_contextual': []  # Nice to match
            },
            'metadata': {
                'test_date': context.get('test_date'),
                'hostname': context.get('hostname'),
                'socwatch_version': context.get('socwatch_version')
            }
        }
        
        # Build keyword tiers for search based on issue classifications
        
        # Tier 1: MANDATORY - workload type and issue category
        search_request['keywords']['tier1_mandatory'].append(context['workload_type'])
        
        # Add keywords from HIGH confidence issue classifications
        for issue in issue_classifications:
            if issue['confidence'] == 'HIGH':
                # Add first 3 keywords from this issue to Tier 1
                search_request['keywords']['tier1_mandatory'].extend(issue['keywords'][:3])
        
        # Tier 2: HIGH PRIORITY - specific issues and IP blocks
        # Add remaining keywords from HIGH confidence issues
        for issue in issue_classifications:
            if issue['confidence'] == 'HIGH':
                search_request['keywords']['tier2_high_priority'].extend(issue['keywords'][3:])
        
        # Add keywords from MEDIUM confidence issues to Tier 2
        for issue in issue_classifications:
            if issue['confidence'] == 'MEDIUM':
                search_request['keywords']['tier2_high_priority'].extend(issue['keywords'][:5])
        
        # Add specific C-state residency keywords
        for issue in context.get('bad_residency', []):
            search_request['keywords']['tier2_high_priority'].append(issue['state'])
            if 'PC0' in issue['state']:
                search_request['keywords']['tier2_high_priority'].extend([
                    'PC0 high', 'PC0 residency', 'Package C0'
                ])
            elif 'PC10' in issue['state']:
                search_request['keywords']['tier2_high_priority'].extend([
                    'PC10 low', 'PC10 residency', 'PC10 entry'
                ])
        
        # Add top 3 high power rail names with context
        for rail in context.get('high_power_rails', [])[:3]:
            search_request['keywords']['tier2_high_priority'].extend([
                rail['name'],
                f"{rail['name']} high power"
            ])
        
        # Tier 3: CONTEXTUAL - platform, versions, and general terms
        if context.get('platform'):
            search_request['keywords']['tier3_contextual'].extend([
                context['platform'],
                f"{context['platform']} power",
                f"{context['platform']} C-state"
            ])
        
        if context.get('ifwi_version'):
            search_request['keywords']['tier3_contextual'].append(f"IFWI {context['ifwi_version']}")
        
        if context.get('socwatch_version'):
            search_request['keywords']['tier3_contextual'].append(f"SocWatch {context['socwatch_version']}")
        
        # Add generic power and residency keywords
        search_request['keywords']['tier3_contextual'].extend([
            'power consumption',
            'idle power',
            'residency',
            'Package C-state',
            'C-state blocker',
            'driver issue',
            'power spike'
        ])
        
        # Remove duplicates while preserving order
        for tier in ['tier1_mandatory', 'tier2_high_priority', 'tier3_contextual']:
            seen = set()
            unique_keywords = []
            for kw in search_request['keywords'][tier]:
                if kw.lower() not in seen:
                    seen.add(kw.lower())
                    unique_keywords.append(kw)
            search_request['keywords'][tier] = unique_keywords
        
        return search_request
    
    def generate_mcp_query_prompt(self, search_request: Dict[str, Any]) -> str:
        """
        Generate natural language prompt for GENI/Co-DeSign MCP query.
        
        This creates a structured prompt that the agent can use to query GENI
        and Co-DeSign for relevant sightings.
        
        Args:
            search_request: Structured search request from build_mcp_search_request()
            
        Returns:
            Natural language prompt for MCP query
        """
        primary = search_request['primary_filters']
        power = search_request['power_context']
        residency = search_request['residency_context']
        keywords = search_request['keywords']
        
        prompt_lines = []
        
        prompt_lines.append("=== HSDES Sighting Search Request for Power Debugging ===\n")
        prompt_lines.append("Please search for HSDES sightings related to the following power issue:\n")
        
        # Issue Classification (FIRST STEP - What is the issue?)
        if search_request.get('issue_classifications'):
            prompt_lines.append("## ISSUE CLASSIFICATION (What is the problem?)")
            prompt_lines.append("Based on power and residency analysis, the following issues were identified:\n")
            
            for i, issue in enumerate(search_request['issue_classifications'], 1):
                confidence_icon = "🔴" if issue['confidence'] == 'HIGH' else "🟡"
                prompt_lines.append(f"{i}. [{confidence_icon} {issue['confidence']}] **{issue['category']}**")
                prompt_lines.append(f"   - Description: {issue['description']}")
                prompt_lines.append(f"   - Evidence: {issue['evidence']}")
                prompt_lines.append(f"   - Keywords: {', '.join(issue['keywords'][:5])}")
                prompt_lines.append("")
            
            prompt_lines.append("**Search Priority**: Focus on sightings matching these issue types first.\n")
        
        # Primary context
        prompt_lines.append("## PRIMARY CONTEXT (Highest Priority Matching)")
        if primary.get('workload_type'):
            prompt_lines.append(f"- Workload Type: **{primary['workload_type']}**")
        if primary.get('platform'):
            prompt_lines.append(f"- Platform: **{primary['platform']}**")
        if primary.get('ifwi_version'):
            prompt_lines.append(f"- IFWI/BIOS Version: **{primary['ifwi_version']}**")
        prompt_lines.append("")
        
        # Power issues
        if power['top_high_power_rails']:
            prompt_lines.append("## POWER CONSUMPTION ISSUES")
            prompt_lines.append(f"Analyzed {power['total_rails_analyzed']} power rails. Top high power rails:")
            for i, rail in enumerate(power['top_high_power_rails'], 1):
                mean_val = self.parse_power_value(rail['mean'])
                prompt_lines.append(f"  {i}. **{rail['name']}**: {mean_val:.4f} {rail['unit']}")
            prompt_lines.append("")
        
        # Residency issues
        if residency['bad_residency_issues']:
            prompt_lines.append("## PACKAGE C-STATE RESIDENCY ISSUES")
            for issue in residency['bad_residency_issues']:
                severity = issue.get('severity', 'MEDIUM')
                prompt_lines.append(f"  [{severity}] {issue['issue']}")
            prompt_lines.append("")
        
        # Search criteria
        prompt_lines.append("## SEARCH CRITERIA (Ranked by Priority)")
        prompt_lines.append("\n### Tier 1: MANDATORY Keywords (Must Match)")
        for kw in keywords['tier1_mandatory']:
            prompt_lines.append(f"  - {kw}")
        
        prompt_lines.append("\n### Tier 2: HIGH PRIORITY Keywords (Should Match)")
        for kw in keywords['tier2_high_priority'][:10]:  # Limit to top 10
            prompt_lines.append(f"  - {kw}")
        
        prompt_lines.append("\n### Tier 3: CONTEXTUAL Keywords (Nice to Match)")
        for kw in keywords['tier3_contextual'][:8]:  # Limit to top 8
            prompt_lines.append(f"  - {kw}")
        
        prompt_lines.append("\n" + "="*70)
        prompt_lines.append("\n## INSTRUCTIONS FOR AGENT")
        prompt_lines.append("Please perform the following:")
        prompt_lines.append("1. Query GENI (Focus Mode 12 - VE Wiki or Mode 5 - Debug Assistant) for related sightings")
        prompt_lines.append("2. Query Co-DeSign for architecture-level known issues and errata")
        prompt_lines.append("3. Rank results by:")
        prompt_lines.append("   a) **Issue type match** (e.g., 'Audio driver high power' > 'General high power')")
        prompt_lines.append("   b) IFWI version match (exact match > major version match)")
        prompt_lines.append("   c) Workload type match")
        prompt_lines.append("   d) Power rail keyword match (e.g., I_VCCCORE, I_V1P8A_PCH)")
        prompt_lines.append("   e) Package C-state keyword match (e.g., PC0 high, PC10 low)")
        prompt_lines.append("   f) Platform match")
        prompt_lines.append("4. For each sighting found, provide:")
        prompt_lines.append("   - HSDES ID and title")
        prompt_lines.append("   - Match score (0-100%)")
        prompt_lines.append("   - Match reasons (which criteria matched)")
        prompt_lines.append("   - Status (open/closed)")
        prompt_lines.append("   - Root cause (if available)")
        prompt_lines.append("   - Recommended actions")
        prompt_lines.append("\n5. Bucketize results into:")
        prompt_lines.append("   - **EXACT MATCH (90-100%)**: Same issue type + IFWI + workload")
        prompt_lines.append("   - **HIGH RELEVANCE (70-89%)**: Same issue type + workload + similar keywords")
        prompt_lines.append("   - **MEDIUM RELEVANCE (50-69%)**: Same platform + similar issue type")
        prompt_lines.append("   - **LOW RELEVANCE (30-49%)**: Related keywords only")
        prompt_lines.append("\n6. **IMPORTANT**: Include power, residency, and Package C-state keywords in the search")
        prompt_lines.append("   - For power issues: Look for 'high power', 'power consumption', 'power spike', specific rail names")
        prompt_lines.append("   - For residency issues: Look for 'PC0 high', 'PC10 low', 'residency', 'C-state blocker'")
        prompt_lines.append("   - For Package C-state: Look for 'Package C-state', 'PC2', 'PC6', 'PC10', 'S0ix'")
        prompt_lines.append("   - For driver issues: Look for specific driver names + 'high power' or 'blocking C-state'")
        
        return "\n".join(prompt_lines)
    
    def generate_debug_report(self, results_json_path: str,
                             project_release: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive debug report with MCP search request.
        
        This is the main entry point. It extracts context, builds the search request,
        and generates a prompt for the agent to query GENI/Co-DeSign MCP.
        
        Args:
            results_json_path: Path to results.json file
            project_release: Optional project release filter (e.g., 'NVL-2026.1')
            
        Returns:
            Debug report dictionary with MCP search request
        """
        logger.info("=== Generating Power Debug Report with MCP Search ===")
        
        # Extract context
        context = self.extract_debug_context_from_results(results_json_path)
        
        # Build MCP search request
        search_request = self.build_mcp_search_request(context)
        if project_release:
            search_request['primary_filters']['project_release'] = project_release
        
        # Generate natural language prompt for MCP
        mcp_prompt = self.generate_mcp_query_prompt(search_request)
        
        report = {
            'results_file': str(results_json_path),
            'workload': context['workload_name'],
            'workload_type': context['workload_type'],
            'platform': context['platform'],
            'ifwi_version': context['ifwi_version'],
            'debug_context': context,
            'search_request': search_request,
            'mcp_query_prompt': mcp_prompt,
            'project_release': project_release,
            'requires_agent_action': True,
            'agent_instructions': (
                "This report requires the PowerKPI_Validator agent to query GENI and Co-DeSign MCP. "
                "Use the 'mcp_query_prompt' field to perform intelligent sighting search with ranking."
            )
        }
        
        logger.info(f"Debug report generated for {context['workload_type']} on {context['platform']}")
        logger.info(f"Found {len(context['bad_residency'])} residency issues and {len(context['high_power_rails'])} power rails")
        
        return report


def main():
    """Main function for standalone execution."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate MCP search request for HSDES power sighting query'
    )
    parser.add_argument('results_json', help='Path to results.json file')
    parser.add_argument('--project-release', help='Project release filter (e.g., NVL-2026.1)')
    parser.add_argument('--output', help='Output JSON file for report')
    parser.add_argument('--prompt-only', action='store_true', 
                       help='Output only the MCP query prompt')
    
    args = parser.parse_args()
    
    debugger = HSDESPowerDebugger()
    
    # Generate full debug report with MCP search request
    report = debugger.generate_debug_report(args.results_json, args.project_release)
    
    if args.prompt_only:
        # Output only the prompt for agent use
        print(report['mcp_query_prompt'])
    else:
        # Output full report
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            print(f"Report saved to: {args.output}")
        else:
            print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
