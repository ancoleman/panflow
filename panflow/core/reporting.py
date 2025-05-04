"""
Enhanced reporting module for PANFlow.

This module provides advanced reporting capabilities for PAN-OS XML configurations,
including policy analysis, visualization, object usage statistics, and custom report generation.
"""

import os
import json
import logging
import csv
import datetime
from typing import Dict, Any, Optional, List, Tuple, Union, Set
from lxml import etree
from collections import Counter, defaultdict

from ..core.config_loader import xpath_search, extract_element_data
from ..core.xpath_resolver import get_object_xpath, get_policy_xpath
from ..modules.objects import get_objects
from ..modules.policies import get_policies
from ..core.bulk_operations import ConfigQuery

# Initialize logger
logger = logging.getLogger("panflow")

class EnhancedReportingEngine:
    """
    Engine for generating enhanced reports on PAN-OS configurations.
    
    This class provides methods for comprehensive configuration analysis,
    visualization, and reporting.
    """
    
    def __init__(
        self,
        tree: etree._ElementTree,
        device_type: str,
        context_type: str,
        version: str,
        **kwargs
    ):
        """
        Initialize the reporting engine.
        
        Args:
            tree: ElementTree containing the configuration
            device_type: Device type (firewall or panorama)
            context_type: Context type (shared, device_group, vsys)
            version: PAN-OS version
            **kwargs: Additional context parameters (device_group, vsys, etc.)
        """
        self.tree = tree
        self.device_type = device_type
        self.context_type = context_type
        self.version = version
        self.context_kwargs = kwargs
        self.query = ConfigQuery(tree, device_type, context_type, version, **kwargs)
        
        logger.debug(f"Initialized EnhancedReportingEngine: {device_type}/{context_type} v{version}")
    
    def generate_security_policy_analysis(
        self,
        policy_type: str = None,
        include_hit_counts: bool = False,
        hit_count_data: Optional[Dict[str, Dict[str, int]]] = None,
        output_file: Optional[str] = None,
        output_format: str = "json",
        include_visualization: bool = False
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analysis of security policies.
        
        Args:
            policy_type: Type of security policy to analyze (if None, determine based on device type)
            include_hit_counts: Whether to include hit count analysis
            hit_count_data: Dictionary of hit count data (if available)
            output_file: File to write the report to
            output_format: Output format ('json', 'csv', 'html')
            include_visualization: Whether to include visualization data
            
        Returns:
            Dictionary containing the analysis results
        """
        logger.info("Generating enhanced security policy analysis")
        
        # Determine policy type if not specified
        if policy_type is None:
            if self.device_type.lower() == "panorama":
                policy_type = "security_pre_rules"
            else:
                policy_type = "security_rules"
            logger.debug(f"Using default policy type: {policy_type}")
        
        # Get all policies of the specified type
        policies = get_policies(self.tree, policy_type, self.device_type, 
                                self.context_type, self.version, **self.context_kwargs)
        
        if not policies:
            logger.warning(f"No {policy_type} policies found")
            return {"error": f"No {policy_type} policies found"}
        
        logger.info(f"Analyzing {len(policies)} {policy_type} policies")
        
        # Prepare analysis structure
        analysis = {
            "summary": {
                "total_policies": len(policies),
                "device_type": self.device_type,
                "context_type": self.context_type,
                "policy_type": policy_type,
                "generation_time": datetime.datetime.now().isoformat(),
                "version": self.version
            },
            "policies": {},
            "categories": {
                "by_action": defaultdict(list),
                "by_source": defaultdict(list),
                "by_destination": defaultdict(list),
                "by_application": defaultdict(list),
                "by_service": defaultdict(list),
                "by_profile": defaultdict(list),
                "by_log_setting": defaultdict(list),
                "disabled": [],
                "enabled": [],
                "any_source": [],
                "any_destination": [],
                "any_application": [],
                "any_service": [],
                "with_profile_group": [],
                "without_profile_group": [],
                "with_log_forwarding": [],
                "without_log_forwarding": []
            },
            "statistics": {
                "actions": Counter(),
                "zones": {
                    "source": Counter(),
                    "destination": Counter()
                },
                "address_objects": {
                    "source": Counter(),
                    "destination": Counter()
                },
                "service_objects": Counter(),
                "application_objects": Counter(),
                "profile_groups": Counter(),
                "log_settings": Counter()
            }
        }
        
        # Add hit count category if requested
        if include_hit_counts and hit_count_data:
            analysis["categories"]["by_hit_count"] = {
                "zero": [],
                "low": [],
                "medium": [],
                "high": []
            }
            analysis["statistics"]["hit_counts"] = {
                "min": 0,
                "max": 0,
                "avg": 0,
                "median": 0,
                "total": 0,
                "distribution": {}
            }
        
        # Analyze each policy
        for name, policy in policies.items():
            # Store basic policy info
            policy_info = {
                "name": name,
                "action": policy.get("action", "N/A"),
                "disabled": policy.get("disabled", "no") == "yes",
                "source_count": len(policy.get("source", [])),
                "destination_count": len(policy.get("destination", [])),
                "service_count": len(policy.get("service", [])),
                "application_count": len(policy.get("application", [])),
                "has_profile_group": False,
                "has_log_forwarding": False,
                "zones": {
                    "source": policy.get("from", []),
                    "destination": policy.get("to", [])
                }
            }
            
            # Check for profile group
            if "profile-setting" in policy:
                if "group" in policy["profile-setting"]:
                    policy_info["has_profile_group"] = True
                    policy_info["profile_groups"] = policy["profile-setting"]["group"]
                    
                    # Update statistics
                    for profile in policy["profile-setting"]["group"]:
                        analysis["statistics"]["profile_groups"][profile] += 1
                    
                    # Add to category
                    analysis["categories"]["by_profile"].extend([name])
                    analysis["categories"]["with_profile_group"].append(name)
                else:
                    policy_info["has_profile_group"] = False
                    analysis["categories"]["without_profile_group"].append(name)
            else:
                policy_info["has_profile_group"] = False
                analysis["categories"]["without_profile_group"].append(name)
            
            # Check for log forwarding
            if "log-setting" in policy:
                policy_info["has_log_forwarding"] = True
                policy_info["log_setting"] = policy["log-setting"]
                
                # Update statistics
                analysis["statistics"]["log_settings"][policy["log-setting"]] += 1
                
                # Add to category
                analysis["categories"]["by_log_setting"][policy["log-setting"]].append(name)
                analysis["categories"]["with_log_forwarding"].append(name)
            else:
                policy_info["has_log_forwarding"] = False
                analysis["categories"]["without_log_forwarding"].append(name)
            
            # Add to action category
            action = policy.get("action", "N/A")
            analysis["categories"]["by_action"][action].append(name)
            analysis["statistics"]["actions"][action] += 1
            
            # Check for any source/destination/application/service
            if "any" in policy.get("source", []):
                policy_info["has_any_source"] = True
                analysis["categories"]["any_source"].append(name)
            else:
                policy_info["has_any_source"] = False
            
            if "any" in policy.get("destination", []):
                policy_info["has_any_destination"] = True
                analysis["categories"]["any_destination"].append(name)
            else:
                policy_info["has_any_destination"] = False
            
            if "any" in policy.get("application", []):
                policy_info["has_any_application"] = True
                analysis["categories"]["any_application"].append(name)
            else:
                policy_info["has_any_application"] = False
            
            if "any" in policy.get("service", []):
                policy_info["has_any_service"] = True
                analysis["categories"]["any_service"].append(name)
            else:
                policy_info["has_any_service"] = False
            
            # Add to enabled/disabled category
            if policy_info["disabled"]:
                analysis["categories"]["disabled"].append(name)
            else:
                analysis["categories"]["enabled"].append(name)
            
            # Update source/destination statistics
            for src in policy.get("source", []):
                if src != "any":
                    analysis["statistics"]["address_objects"]["source"][src] += 1
                    if src not in analysis["categories"]["by_source"]:
                        analysis["categories"]["by_source"][src] = []
                    analysis["categories"]["by_source"][src].append(name)
            
            for dst in policy.get("destination", []):
                if dst != "any":
                    analysis["statistics"]["address_objects"]["destination"][dst] += 1
                    if dst not in analysis["categories"]["by_destination"]:
                        analysis["categories"]["by_destination"][dst] = []
                    analysis["categories"]["by_destination"][dst].append(name)
            
            # Update service statistics
            for svc in policy.get("service", []):
                if svc != "any" and svc != "application-default":
                    analysis["statistics"]["service_objects"][svc] += 1
                    if svc not in analysis["categories"]["by_service"]:
                        analysis["categories"]["by_service"][svc] = []
                    analysis["categories"]["by_service"][svc].append(name)
            
            # Update application statistics
            for app in policy.get("application", []):
                if app != "any":
                    analysis["statistics"]["application_objects"][app] += 1
                    if app not in analysis["categories"]["by_application"]:
                        analysis["categories"]["by_application"][app] = []
                    analysis["categories"]["by_application"][app].append(name)
            
            # Update zone statistics
            for src_zone in policy.get("from", []):
                analysis["statistics"]["zones"]["source"][src_zone] += 1
            
            for dst_zone in policy.get("to", []):
                analysis["statistics"]["zones"]["destination"][dst_zone] += 1
            
            # Add hit count info if available
            if include_hit_counts and hit_count_data and name in hit_count_data:
                hit_count = hit_count_data[name]["hit_count"]
                policy_info["hit_count"] = hit_count
                
                # Categorize by hit count
                if hit_count == 0:
                    analysis["categories"]["by_hit_count"]["zero"].append(name)
                elif hit_count < 100:
                    analysis["categories"]["by_hit_count"]["low"].append(name)
                elif hit_count < 1000:
                    analysis["categories"]["by_hit_count"]["medium"].append(name)
                else:
                    analysis["categories"]["by_hit_count"]["high"].append(name)
                
                # Update distribution
                count_range = str(self._get_hit_count_range(hit_count))
                if count_range not in analysis["statistics"]["hit_counts"]["distribution"]:
                    analysis["statistics"]["hit_counts"]["distribution"][count_range] = 0
                analysis["statistics"]["hit_counts"]["distribution"][count_range] += 1
            
            # Store the policy info
            analysis["policies"][name] = policy_info
        
        # Update summary statistics
        analysis["summary"]["disabled_count"] = len(analysis["categories"]["disabled"])
        analysis["summary"]["enabled_count"] = len(analysis["categories"]["enabled"])
        analysis["summary"]["any_source_count"] = len(analysis["categories"]["any_source"])
        analysis["summary"]["any_destination_count"] = len(analysis["categories"]["any_destination"])
        analysis["summary"]["any_application_count"] = len(analysis["categories"]["any_application"])
        analysis["summary"]["any_service_count"] = len(analysis["categories"]["any_service"])
        analysis["summary"]["with_profile_group_count"] = len(analysis["categories"]["with_profile_group"])
        analysis["summary"]["without_profile_group_count"] = len(analysis["categories"]["without_profile_group"])
        analysis["summary"]["with_log_forwarding_count"] = len(analysis["categories"]["with_log_forwarding"])
        analysis["summary"]["without_log_forwarding_count"] = len(analysis["categories"]["without_log_forwarding"])
        
        # Calculate hit count statistics if available
        if include_hit_counts and hit_count_data:
            hit_counts = [hit_count_data[name]["hit_count"] for name in policies if name in hit_count_data]
            if hit_counts:
                analysis["statistics"]["hit_counts"]["min"] = min(hit_counts)
                analysis["statistics"]["hit_counts"]["max"] = max(hit_counts)
                analysis["statistics"]["hit_counts"]["avg"] = sum(hit_counts) / len(hit_counts)
                analysis["statistics"]["hit_counts"]["total"] = sum(hit_counts)
                
                # Calculate median
                sorted_counts = sorted(hit_counts)
                mid = len(sorted_counts) // 2
                if len(sorted_counts) % 2 == 0:
                    analysis["statistics"]["hit_counts"]["median"] = (sorted_counts[mid-1] + sorted_counts[mid]) / 2
                else:
                    analysis["statistics"]["hit_counts"]["median"] = sorted_counts[mid]
        
        # Generate rule overlap analysis if requested
        if include_visualization:
            analysis["visualization"] = self._generate_policy_visualization(policies)
        
        # Write the report to a file if requested
        if output_file:
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
                
                if output_format.lower() == 'json':
                    with open(output_file, 'w') as f:
                        json.dump(analysis, f, indent=2)
                    logger.info(f"Security policy analysis report saved to {output_file} (JSON format)")
                
                elif output_format.lower() == 'csv':
                    # Write policy details to CSV
                    with open(output_file, 'w', newline='') as f:
                        writer = csv.writer(f)
                        # Write header
                        header = ["Policy Name", "Action", "Disabled", "Source Count", "Destination Count",
                                 "Service Count", "Application Count", "Has Profile Group", "Has Log Forwarding"]
                        if include_hit_counts:
                            header.append("Hit Count")
                        writer.writerow(header)
                        
                        # Write rows
                        for name, policy_info in analysis["policies"].items():
                            row = [
                                name,
                                policy_info["action"],
                                policy_info["disabled"],
                                policy_info["source_count"],
                                policy_info["destination_count"],
                                policy_info["service_count"],
                                policy_info["application_count"],
                                policy_info["has_profile_group"],
                                policy_info["has_log_forwarding"]
                            ]
                            if include_hit_counts and hit_count_data and name in hit_count_data:
                                row.append(hit_count_data[name]["hit_count"])
                            elif include_hit_counts:
                                row.append("N/A")
                            writer.writerow(row)
                    logger.info(f"Security policy analysis report saved to {output_file} (CSV format)")
                
                elif output_format.lower() == 'html':
                    # Generate HTML report
                    html_report = self._generate_html_report(analysis, include_hit_counts)
                    with open(output_file, 'w') as f:
                        f.write(html_report)
                    logger.info(f"Security policy analysis report saved to {output_file} (HTML format)")
                
                else:
                    logger.error(f"Unsupported output format: {output_format}")
            
            except Exception as e:
                logger.error(f"Error saving report to {output_file}: {e}")
        
        return analysis
    
    def _get_hit_count_range(self, count: int) -> Tuple[int, int]:
        """Get the range for a hit count value."""
        if count == 0:
            return (0, 0)
        elif count < 10:
            return (1, 10)
        elif count < 100:
            return (10, 100)
        elif count < 1000:
            return (100, 1000)
        elif count < 10000:
            return (1000, 10000)
        else:
            return (10000, float('inf'))
    
    def _generate_policy_visualization(self, policies: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate visualization data for policy analysis.
        
        Args:
            policies: Dictionary of policies
            
        Returns:
            Dictionary containing visualization data
        """
        logger.debug("Generating policy visualization data")
        
        # Prepare visualization data
        visualization = {
            "policy_matrix": [],
            "zone_matrix": [],
            "overlap_graph": {
                "nodes": [],
                "links": []
            }
        }
        
        # Build policy matrix for source/destination visualization
        policy_names = list(policies.keys())
        
        # Add policies as nodes for the overlap graph
        for name in policy_names:
            visualization["overlap_graph"]["nodes"].append({
                "id": name,
                "type": "policy",
                "disabled": policies[name].get("disabled", "no") == "yes",
                "action": policies[name].get("action", "allow")
            })
        
        # Analyze policy overlaps
        for i, (name1, policy1) in enumerate(policies.items()):
            row = {"name": name1, "overlaps": []}
            
            # Skip disabled policies for overlap analysis
            if policy1.get("disabled", "no") == "yes":
                continue
            
            for j, (name2, policy2) in enumerate(policies.items()):
                # Skip self and disabled policies
                if name1 == name2 or policy2.get("disabled", "no") == "yes":
                    continue
                
                # Check for potential overlaps
                overlap = self._check_policy_overlap(policy1, policy2)
                
                if overlap["has_overlap"]:
                    row["overlaps"].append({
                        "policy": name2,
                        "type": overlap["type"],
                        "fields": overlap["fields"]
                    })
                    
                    # Add link to overlap graph
                    visualization["overlap_graph"]["links"].append({
                        "source": name1,
                        "target": name2,
                        "type": overlap["type"],
                        "weight": len(overlap["fields"])
                    })
            
            visualization["policy_matrix"].append(row)
        
        return visualization
    
    def _check_policy_overlap(self, policy1: Dict[str, Any], policy2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if two policies have overlapping rules.
        
        Args:
            policy1: First policy
            policy2: Second policy
            
        Returns:
            Dictionary with overlap information
        """
        # Fields to check for overlaps
        fields = ["source", "destination", "service", "application", "from", "to"]
        overlapping_fields = []
        
        # Helper to check if lists overlap
        def lists_overlap(list1, list2):
            # Special case for 'any'
            if "any" in list1 or "any" in list2:
                return True
            
            # Check for common elements
            return bool(set(list1) & set(list2))
        
        # Check each field for overlaps
        for field in fields:
            if field in policy1 and field in policy2:
                if isinstance(policy1[field], list) and isinstance(policy2[field], list):
                    if lists_overlap(policy1[field], policy2[field]):
                        overlapping_fields.append(field)
        
        # Determine overlap type
        if not overlapping_fields:
            return {"has_overlap": False, "type": "none", "fields": []}
        elif len(overlapping_fields) == len(fields):
            # If actions are different, this is a potential conflict
            if policy1.get("action", "") != policy2.get("action", ""):
                return {"has_overlap": True, "type": "conflict", "fields": overlapping_fields}
            else:
                return {"has_overlap": True, "type": "duplicate", "fields": overlapping_fields}
        else:
            return {"has_overlap": True, "type": "partial", "fields": overlapping_fields}
    
    def _generate_html_report(self, analysis: Dict[str, Any], include_hit_counts: bool) -> str:
        """
        Generate an HTML report from the analysis data.
        
        Args:
            analysis: Analysis data
            include_hit_counts: Whether hit count data is included
            
        Returns:
            HTML report as a string
        """
        # Create HTML template with Bootstrap
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Policy Analysis Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js"></script>
    <style>
        body {{ padding: 20px; }}
        .card {{ margin-bottom: 20px; }}
        .summary-item {{ font-size: 16px; margin: 5px 0; }}
        .chart-container {{ position: relative; height: 300px; margin-bottom: 20px; }}
        .table-responsive {{ margin-bottom: 20px; }}
        .policy-row:hover {{ background-color: #f8f9fa; }}
        .policy-enabled {{ background-color: #d1e7dd; }}
        .policy-disabled {{ background-color: #f8d7da; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1 class="mb-4">Security Policy Analysis Report</h1>
        <p class="text-muted">
            Generated on {analysis["summary"]["generation_time"]} for 
            {analysis["summary"]["device_type"]}/{analysis["summary"]["context_type"]} 
            ({analysis["summary"]["policy_type"]})
        </p>
        
        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">Summary</h5>
                    </div>
                    <div class="card-body">
                        <div class="summary-item"><strong>Total Policies:</strong> {analysis["summary"]["total_policies"]}</div>
                        <div class="summary-item"><strong>Enabled:</strong> {analysis["summary"]["enabled_count"]}</div>
                        <div class="summary-item"><strong>Disabled:</strong> {analysis["summary"]["disabled_count"]}</div>
                        <div class="summary-item"><strong>Any Source:</strong> {analysis["summary"]["any_source_count"]}</div>
                        <div class="summary-item"><strong>Any Destination:</strong> {analysis["summary"]["any_destination_count"]}</div>
                        <div class="summary-item"><strong>Any Application:</strong> {analysis["summary"]["any_application_count"]}</div>
                        <div class="summary-item"><strong>Any Service:</strong> {analysis["summary"]["any_service_count"]}</div>
                        <div class="summary-item"><strong>With Profile Group:</strong> {analysis["summary"]["with_profile_group_count"]}</div>
                        <div class="summary-item"><strong>Without Profile Group:</strong> {analysis["summary"]["without_profile_group_count"]}</div>
                        <div class="summary-item"><strong>With Log Forwarding:</strong> {analysis["summary"]["with_log_forwarding_count"]}</div>
                        <div class="summary-item"><strong>Without Log Forwarding:</strong> {analysis["summary"]["without_log_forwarding_count"]}</div>
                    </div>
                </div>
            </div>"""
        
        # Add hit count summary if available
        if include_hit_counts and "statistics" in analysis and "hit_counts" in analysis["statistics"]:
            html += f"""
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header bg-info text-white">
                        <h5 class="mb-0">Hit Count Statistics</h5>
                    </div>
                    <div class="card-body">
                        <div class="summary-item"><strong>Min:</strong> {analysis["statistics"]["hit_counts"]["min"]}</div>
                        <div class="summary-item"><strong>Max:</strong> {analysis["statistics"]["hit_counts"]["max"]}</div>
                        <div class="summary-item"><strong>Average:</strong> {analysis["statistics"]["hit_counts"]["avg"]:.2f}</div>
                        <div class="summary-item"><strong>Median:</strong> {analysis["statistics"]["hit_counts"]["median"]}</div>
                        <div class="summary-item"><strong>Total:</strong> {analysis["statistics"]["hit_counts"]["total"]}</div>
                    </div>
                </div>
            </div>"""
        
        # Add action distribution chart
        html += f"""
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header bg-success text-white">
                        <h5 class="mb-0">Action Distribution</h5>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="actionChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header bg-dark text-white">
                        <h5 class="mb-0">Policy Details</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead>
                                    <tr>
                                        <th>Name</th>
                                        <th>Action</th>
                                        <th>Status</th>
                                        <th>Source</th>
                                        <th>Destination</th>
                                        <th>Service</th>
                                        <th>Application</th>
                                        <th>Security Profiles</th>
                                        <th>Logging</th>"""
        
        # Add hit count column if available
        if include_hit_counts:
            html += """
                                        <th>Hit Count</th>"""
        
        html += """
                                    </tr>
                                </thead>
                                <tbody>"""
        
        # Add policy rows
        for name, policy_info in analysis["policies"].items():
            css_class = "policy-disabled" if policy_info["disabled"] else "policy-enabled"
            
            # Create the policy row
            html += f"""
                                    <tr class="policy-row {css_class}">
                                        <td>{name}</td>
                                        <td>{policy_info["action"]}</td>
                                        <td>{"Disabled" if policy_info["disabled"] else "Enabled"}</td>
                                        <td>{policy_info["source_count"]} {"(any)" if policy_info.get("has_any_source", False) else ""}</td>
                                        <td>{policy_info["destination_count"]} {"(any)" if policy_info.get("has_any_destination", False) else ""}</td>
                                        <td>{policy_info["service_count"]} {"(any)" if policy_info.get("has_any_service", False) else ""}</td>
                                        <td>{policy_info["application_count"]} {"(any)" if policy_info.get("has_any_application", False) else ""}</td>
                                        <td>{"Yes" if policy_info["has_profile_group"] else "No"}</td>
                                        <td>{"Yes" if policy_info["has_log_forwarding"] else "No"}</td>"""
            
            # Add hit count cell if available
            if include_hit_counts:
                hit_count = policy_info.get("hit_count", "N/A")
                html += f"""
                                        <td>{hit_count}</td>"""
            
            html += """
                                    </tr>"""
        
        html += """
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>"""
        
        # Add JavaScript for charts
        html += """
        <script>
            // Action distribution chart
            document.addEventListener('DOMContentLoaded', function() {
                const actionCtx = document.getElementById('actionChart').getContext('2d');
                const actionChart = new Chart(actionCtx, {
                    type: 'pie',
                    data: {
                        labels: ["""
        
        # Add action labels
        labels = []
        data = []
        for action, count in analysis["statistics"]["actions"].items():
            labels.append(f"'{action}'")
            data.append(str(count))
        
        html += ", ".join(labels)
        
        html += """],
                        datasets: [{
                            data: ["""
        
        # Add action data
        html += ", ".join(data)
        
        html += """],
                            backgroundColor: [
                                'rgba(75, 192, 192, 0.6)',
                                'rgba(255, 99, 132, 0.6)',
                                'rgba(54, 162, 235, 0.6)',
                                'rgba(255, 206, 86, 0.6)',
                                'rgba(153, 102, 255, 0.6)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'right'
                            }
                        }
                    }
                });
            });
        </script>
    </div>
</body>
</html>"""
        
        return html
    
    def generate_object_usage_report(
        self,
        object_type: str,
        output_file: Optional[str] = None,
        output_format: str = "json",
        include_visualization: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a report on object usage and relationships.
        
        Args:
            object_type: Type of object to analyze
            output_file: File to write the report to
            output_format: Output format ('json', 'csv', 'html')
            include_visualization: Whether to include visualization data
            
        Returns:
            Dictionary containing the analysis results
        """
        logger.info(f"Generating object usage report for {object_type}")
        
        # Get all objects of the specified type
        objects = get_objects(self.tree, object_type, self.device_type, 
                             self.context_type, self.version, **self.context_kwargs)
        
        if not objects:
            logger.warning(f"No {object_type} objects found")
            return {"error": f"No {object_type} objects found"}
        
        logger.info(f"Analyzing {len(objects)} {object_type} objects")
        
        # Prepare analysis structure
        analysis = {
            "summary": {
                "total_objects": len(objects),
                "device_type": self.device_type,
                "context_type": self.context_type,
                "object_type": object_type,
                "generation_time": datetime.datetime.now().isoformat(),
                "version": self.version
            },
            "objects": {},
            "usage": {
                "used": [],
                "unused": [],
                "used_in_policies": {},
                "used_in_groups": {}
            },
            "statistics": {
                "usage_count": {},
                "reference_types": Counter()
            }
        }
        
        # Handle specific object types
        if object_type == "address":
            analysis["categories"] = {
                "by_type": {
                    "ip-netmask": [],
                    "ip-range": [],
                    "fqdn": []
                }
            }
        elif object_type.endswith("_group"):
            analysis["categories"] = {
                "by_type": {
                    "static": [],
                    "dynamic": []
                },
                "by_member_count": {
                    "0": [],
                    "1-5": [],
                    "6-20": [],
                    "21+": []
                }
            }
        
        # Generate reference data - policies that use these objects
        # This depends on the object type
        policy_references = {}
        group_references = {}
        
        # Get security policies to check for usage
        policy_types = []
        if self.device_type.lower() == "panorama":
            policy_types = ["security_pre_rules", "security_post_rules", "nat_pre_rules", "nat_post_rules"]
        else:
            policy_types = ["security_rules", "nat_rules"]
        
        # Check policies for references
        for policy_type in policy_types:
            policies = get_policies(self.tree, policy_type, self.device_type, 
                                   self.context_type, self.version, **self.context_kwargs)
            
            for policy_name, policy in policies.items():
                # Check fields that might reference this object type
                if object_type == "address" or object_type == "address_group":
                    fields = ["source", "destination"]
                elif object_type == "service" or object_type == "service_group":
                    fields = ["service"]
                elif object_type == "application" or object_type == "application_group":
                    fields = ["application"]
                elif "profile" in object_type:
                    if "profile-setting" in policy:
                        if "group" in policy["profile-setting"]:
                            fields = ["profile-setting/group"]
                else:
                    fields = []
                
                # Check each field for references
                for field in fields:
                    if '/' in field:
                        # Handle nested fields
                        parent, child = field.split('/')
                        if parent in policy and child in policy[parent]:
                            for ref in policy[parent][child]:
                                if ref in objects:
                                    if ref not in policy_references:
                                        policy_references[ref] = []
                                    
                                    policy_references[ref].append({
                                        "policy_type": policy_type,
                                        "policy_name": policy_name,
                                        "field": field
                                    })
                    else:
                        # Handle simple fields
                        if field in policy:
                            for ref in policy[field]:
                                if ref in objects:
                                    if ref not in policy_references:
                                        policy_references[ref] = []
                                    
                                    policy_references[ref].append({
                                        "policy_type": policy_type,
                                        "policy_name": policy_name,
                                        "field": field
                                    })
        
        # Check group references if this is a base object type
        if not object_type.endswith("_group"):
            group_type = f"{object_type}_group"
            
            try:
                groups = get_objects(self.tree, group_type, self.device_type, 
                                    self.context_type, self.version, **self.context_kwargs)
                
                for group_name, group in groups.items():
                    # Check static members
                    if "static" in group:
                        for member in group["static"]:
                            if member in objects:
                                if member not in group_references:
                                    group_references[member] = []
                                
                                group_references[member].append({
                                    "group_type": group_type,
                                    "group_name": group_name
                                })
            except Exception as e:
                logger.debug(f"Error checking group references: {e}")
        
        # Analyze each object
        for name, obj in objects.items():
            # Store basic object info
            object_info = {
                "name": name,
                "references": {
                    "policies": policy_references.get(name, []),
                    "groups": group_references.get(name, [])
                }
            }
            
            # Count references
            policy_count = len(policy_references.get(name, []))
            group_count = len(group_references.get(name, []))
            total_count = policy_count + group_count
            
            # Determine usage status
            if total_count > 0:
                object_info["used"] = True
                analysis["usage"]["used"].append(name)
                
                # Add to used_in_policies
                for ref in policy_references.get(name, []):
                    policy_name = ref["policy_name"]
                    if policy_name not in analysis["usage"]["used_in_policies"]:
                        analysis["usage"]["used_in_policies"][policy_name] = []
                    analysis["usage"]["used_in_policies"][policy_name].append(name)
                
                # Add to used_in_groups
                for ref in group_references.get(name, []):
                    group_name = ref["group_name"]
                    if group_name not in analysis["usage"]["used_in_groups"]:
                        analysis["usage"]["used_in_groups"][group_name] = []
                    analysis["usage"]["used_in_groups"][group_name].append(name)
            else:
                object_info["used"] = False
                analysis["usage"]["unused"].append(name)
            
            # Track usage count statistics
            if total_count not in analysis["statistics"]["usage_count"]:
                analysis["statistics"]["usage_count"][total_count] = 0
            analysis["statistics"]["usage_count"][total_count] += 1
            
            # Update reference type statistics
            if policy_count > 0:
                analysis["statistics"]["reference_types"]["policies"] += 1
            if group_count > 0:
                analysis["statistics"]["reference_types"]["groups"] += 1
            if total_count == 0:
                analysis["statistics"]["reference_types"]["unused"] += 1
            
            # Handle specific object types
            if object_type == "address":
                if "ip-netmask" in obj:
                    object_info["type"] = "ip-netmask"
                    object_info["value"] = obj["ip-netmask"]
                    analysis["categories"]["by_type"]["ip-netmask"].append(name)
                elif "ip-range" in obj:
                    object_info["type"] = "ip-range"
                    object_info["value"] = obj["ip-range"]
                    analysis["categories"]["by_type"]["ip-range"].append(name)
                elif "fqdn" in obj:
                    object_info["type"] = "fqdn"
                    object_info["value"] = obj["fqdn"]
                    analysis["categories"]["by_type"]["fqdn"].append(name)
                else:
                    object_info["type"] = "unknown"
            
            elif object_type.endswith("_group"):
                if "static" in obj:
                    object_info["type"] = "static"
                    object_info["members"] = obj["static"]
                    analysis["categories"]["by_type"]["static"].append(name)
                    
                    # Categorize by member count
                    member_count = len(obj["static"])
                    if member_count == 0:
                        analysis["categories"]["by_member_count"]["0"].append(name)
                    elif member_count <= 5:
                        analysis["categories"]["by_member_count"]["1-5"].append(name)
                    elif member_count <= 20:
                        analysis["categories"]["by_member_count"]["6-20"].append(name)
                    else:
                        analysis["categories"]["by_member_count"]["21+"].append(name)
                    
                elif "dynamic" in obj:
                    object_info["type"] = "dynamic"
                    if "filter" in obj["dynamic"]:
                        object_info["filter"] = obj["dynamic"]["filter"]
                    analysis["categories"]["by_type"]["dynamic"].append(name)
                    analysis["categories"]["by_member_count"]["0"].append(name)  # Dynamic groups don't have static members
            
            # Store the object info
            analysis["objects"][name] = object_info
        
        # Update summary statistics
        analysis["summary"]["used_count"] = len(analysis["usage"]["used"])
        analysis["summary"]["unused_count"] = len(analysis["usage"]["unused"])
        analysis["summary"]["used_percentage"] = (analysis["summary"]["used_count"] / analysis["summary"]["total_objects"]) * 100 if analysis["summary"]["total_objects"] > 0 else 0
        
        # Add type-specific summary statistics
        if object_type == "address":
            analysis["summary"]["ip_netmask_count"] = len(analysis["categories"]["by_type"]["ip-netmask"])
            analysis["summary"]["ip_range_count"] = len(analysis["categories"]["by_type"]["ip-range"])
            analysis["summary"]["fqdn_count"] = len(analysis["categories"]["by_type"]["fqdn"])
        elif object_type.endswith("_group"):
            analysis["summary"]["static_count"] = len(analysis["categories"]["by_type"]["static"])
            analysis["summary"]["dynamic_count"] = len(analysis["categories"]["by_type"]["dynamic"])
            
            analysis["summary"]["empty_count"] = len(analysis["categories"]["by_member_count"]["0"])
            analysis["summary"]["small_count"] = len(analysis["categories"]["by_member_count"]["1-5"])
            analysis["summary"]["medium_count"] = len(analysis["categories"]["by_member_count"]["6-20"])
            analysis["summary"]["large_count"] = len(analysis["categories"]["by_member_count"]["21+"])
        
        # Generate object relationship visualization if requested
        if include_visualization:
            analysis["visualization"] = self._generate_object_visualization(
                objects, policy_references, group_references
            )
        
        # Write the report to a file if requested
        if output_file:
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
                
                if output_format.lower() == 'json':
                    with open(output_file, 'w') as f:
                        json.dump(analysis, f, indent=2)
                    logger.info(f"Object usage report saved to {output_file} (JSON format)")
                
                elif output_format.lower() == 'csv':
                    # Write object details to CSV
                    with open(output_file, 'w', newline='') as f:
                        writer = csv.writer(f)
                        # Write header
                        header = ["Object Name", "Used", "Policy References", "Group References"]
                        
                        # Add type-specific fields
                        if object_type == "address":
                            header.extend(["Type", "Value"])
                        elif object_type.endswith("_group"):
                            header.extend(["Type", "Member Count"])
                        
                        writer.writerow(header)
                        
                        # Write rows
                        for name, obj_info in analysis["objects"].items():
                            row = [
                                name,
                                obj_info["used"],
                                len(obj_info["references"]["policies"]),
                                len(obj_info["references"]["groups"])
                            ]
                            
                            # Add type-specific fields
                            if object_type == "address":
                                if "type" in obj_info:
                                    row.append(obj_info["type"])
                                    if "value" in obj_info:
                                        row.append(obj_info["value"])
                                    else:
                                        row.append("")
                                else:
                                    row.extend(["", ""])
                            elif object_type.endswith("_group"):
                                if "type" in obj_info:
                                    row.append(obj_info["type"])
                                    if "members" in obj_info:
                                        row.append(len(obj_info["members"]))
                                    else:
                                        row.append(0)
                                else:
                                    row.extend(["", 0])
                            
                            writer.writerow(row)
                    logger.info(f"Object usage report saved to {output_file} (CSV format)")
                
                elif output_format.lower() == 'html':
                    # Generate HTML report
                    html_report = self._generate_object_html_report(analysis, object_type)
                    with open(output_file, 'w') as f:
                        f.write(html_report)
                    logger.info(f"Object usage report saved to {output_file} (HTML format)")
                
                else:
                    logger.error(f"Unsupported output format: {output_format}")
            
            except Exception as e:
                logger.error(f"Error saving report to {output_file}: {e}")
        
        return analysis
    
    def _generate_object_visualization(
        self,
        objects: Dict[str, Dict[str, Any]],
        policy_references: Dict[str, List[Dict[str, Any]]],
        group_references: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Generate visualization data for object relationships.
        
        Args:
            objects: Dictionary of objects
            policy_references: Object references in policies
            group_references: Object references in groups
            
        Returns:
            Dictionary containing visualization data
        """
        logger.debug("Generating object relationship visualization data")
        
        # Prepare visualization data
        visualization = {
            "relationship_graph": {
                "nodes": [],
                "links": []
            },
            "usage_distribution": {}
        }
        
        # Add objects as nodes
        for name in objects:
            # Determine node type
            policy_count = len(policy_references.get(name, []))
            group_count = len(group_references.get(name, []))
            
            node_type = "unused" if policy_count + group_count == 0 else "used"
            
            # Add node
            visualization["relationship_graph"]["nodes"].append({
                "id": name,
                "type": "object",
                "usage": node_type,
                "policy_count": policy_count,
                "group_count": group_count
            })
        
        # Add policies that reference these objects as nodes
        policies_added = set()
        for name, refs in policy_references.items():
            for ref in refs:
                policy_name = ref["policy_name"]
                if policy_name not in policies_added:
                    policies_added.add(policy_name)
                    
                    visualization["relationship_graph"]["nodes"].append({
                        "id": policy_name,
                        "type": "policy",
                        "policy_type": ref["policy_type"]
                    })
                
                # Add link between object and policy
                visualization["relationship_graph"]["links"].append({
                    "source": name,
                    "target": policy_name,
                    "type": "policy_reference",
                    "field": ref["field"]
                })
        
        # Add groups that reference these objects as nodes
        groups_added = set()
        for name, refs in group_references.items():
            for ref in refs:
                group_name = ref["group_name"]
                if group_name not in groups_added:
                    groups_added.add(group_name)
                    
                    visualization["relationship_graph"]["nodes"].append({
                        "id": group_name,
                        "type": "group",
                        "group_type": ref["group_type"]
                    })
                
                # Add link between object and group
                visualization["relationship_graph"]["links"].append({
                    "source": name,
                    "target": group_name,
                    "type": "group_reference"
                })
        
        # Calculate usage distribution
        usage_counts = [len(policy_references.get(name, [])) + len(group_references.get(name, [])) for name in objects]
        
        if usage_counts:
            # Group by ranges
            ranges = [(0, 0), (1, 1), (2, 5), (6, 10), (11, 20), (21, float('inf'))]
            distribution = {}
            
            for start, end in ranges:
                if end == float('inf'):
                    key = f"{start}+"
                elif start == end:
                    key = str(start)
                else:
                    key = f"{start}-{end}"
                
                count = sum(1 for c in usage_counts if start <= c <= end)
                distribution[key] = count
            
            visualization["usage_distribution"] = distribution
        
        return visualization
    
    def _generate_object_html_report(self, analysis: Dict[str, Any], object_type: str) -> str:
        """
        Generate an HTML report from the object analysis data.
        
        Args:
            analysis: Analysis data
            object_type: Type of object analyzed
            
        Returns:
            HTML report as a string
        """
        # Create HTML template with Bootstrap
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{object_type.capitalize()} Usage Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js"></script>
    <style>
        body {{ padding: 20px; }}
        .card {{ margin-bottom: 20px; }}
        .summary-item {{ font-size: 16px; margin: 5px 0; }}
        .chart-container {{ position: relative; height: 300px; margin-bottom: 20px; }}
        .table-responsive {{ margin-bottom: 20px; }}
        .object-row:hover {{ background-color: #f8f9fa; }}
        .object-used {{ background-color: #d1e7dd; }}
        .object-unused {{ background-color: #f8d7da; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1 class="mb-4">{object_type.capitalize()} Usage Report</h1>
        <p class="text-muted">
            Generated on {analysis["summary"]["generation_time"]} for 
            {analysis["summary"]["device_type"]}/{analysis["summary"]["context_type"]} 
            ({analysis["summary"]["object_type"]})
        </p>
        
        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">Summary</h5>
                    </div>
                    <div class="card-body">
                        <div class="summary-item"><strong>Total Objects:</strong> {analysis["summary"]["total_objects"]}</div>
                        <div class="summary-item"><strong>Used:</strong> {analysis["summary"]["used_count"]} ({analysis["summary"]["used_percentage"]:.1f}%)</div>
                        <div class="summary-item"><strong>Unused:</strong> {analysis["summary"]["unused_count"]}</div>"""
        
        # Add type-specific summary statistics
        if object_type == "address":
            html += f"""
                        <div class="summary-item"><strong>IP-Netmask:</strong> {analysis["summary"]["ip_netmask_count"]}</div>
                        <div class="summary-item"><strong>IP-Range:</strong> {analysis["summary"]["ip_range_count"]}</div>
                        <div class="summary-item"><strong>FQDN:</strong> {analysis["summary"]["fqdn_count"]}</div>"""
        elif object_type.endswith("_group"):
            html += f"""
                        <div class="summary-item"><strong>Static Groups:</strong> {analysis["summary"]["static_count"]}</div>
                        <div class="summary-item"><strong>Dynamic Groups:</strong> {analysis["summary"]["dynamic_count"]}</div>
                        <div class="summary-item"><strong>Empty Groups:</strong> {analysis["summary"]["empty_count"]}</div>
                        <div class="summary-item"><strong>Small Groups (1-5):</strong> {analysis["summary"]["small_count"]}</div>
                        <div class="summary-item"><strong>Medium Groups (6-20):</strong> {analysis["summary"]["medium_count"]}</div>
                        <div class="summary-item"><strong>Large Groups (21+):</strong> {analysis["summary"]["large_count"]}</div>"""
        
        html += """
                    </div>
                </div>
            </div>
            
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header bg-success text-white">
                        <h5 class="mb-0">Usage Distribution</h5>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="usageChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header bg-info text-white">
                        <h5 class="mb-0">Reference Types</h5>
                    </div>
                    <div class="card-body">
                        <div class="chart-container">
                            <canvas id="refTypeChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header bg-dark text-white">
                        <h5 class="mb-0">Object Details</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead>
                                    <tr>
                                        <th>Name</th>
                                        <th>Used</th>
                                        <th>Policy References</th>
                                        <th>Group References</th>"""
        
        # Add type-specific columns
        if object_type == "address":
            html += """
                                        <th>Type</th>
                                        <th>Value</th>"""
        elif object_type.endswith("_group"):
            html += """
                                        <th>Type</th>
                                        <th>Member Count</th>"""
        
        html += """
                                    </tr>
                                </thead>
                                <tbody>"""
        
        # Add object rows
        for name, obj_info in analysis["objects"].items():
            css_class = "object-used" if obj_info["used"] else "object-unused"
            
            # Create the object row
            html += f"""
                                    <tr class="object-row {css_class}">
                                        <td>{name}</td>
                                        <td>{"Yes" if obj_info["used"] else "No"}</td>
                                        <td>{len(obj_info["references"]["policies"])}</td>
                                        <td>{len(obj_info["references"]["groups"])}</td>"""
            
            # Add type-specific cells
            if object_type == "address":
                if "type" in obj_info:
                    html += f"""
                                        <td>{obj_info.get("type", "")}</td>
                                        <td>{obj_info.get("value", "")}</td>"""
                else:
                    html += """
                                        <td></td>
                                        <td></td>"""
            elif object_type.endswith("_group"):
                if "type" in obj_info:
                    member_count = len(obj_info.get("members", []))
                    html += f"""
                                        <td>{obj_info.get("type", "")}</td>
                                        <td>{member_count}</td>"""
                else:
                    html += """
                                        <td></td>
                                        <td>0</td>"""
            
            html += """
                                    </tr>"""
        
        html += """
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>"""
        
        # Add JavaScript for charts
        html += """
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                // Usage distribution chart
                const usageCtx = document.getElementById('usageChart').getContext('2d');
                const usageChart = new Chart(usageCtx, {
                    type: 'pie',
                    data: {
                        labels: ['Used', 'Unused'],
                        datasets: [{
                            data: ["""
        
        # Add usage data
        html += f"{analysis['summary']['used_count']}, {analysis['summary']['unused_count']}"
        
        html += """],
                            backgroundColor: [
                                'rgba(75, 192, 192, 0.6)',
                                'rgba(255, 99, 132, 0.6)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'right'
                            }
                        }
                    }
                });
                
                // Reference type chart
                const refCtx = document.getElementById('refTypeChart').getContext('2d');
                const refChart = new Chart(refCtx, {
                    type: 'bar',
                    data: {
                        labels: ["""
        
        # Add reference type labels
        ref_types = list(analysis["statistics"]["reference_types"].keys())
        labels = [f"'{ref_type}'" for ref_type in ref_types]
        html += ", ".join(labels)
        
        html += """],
                        datasets: [{
                            label: 'Objects',
                            data: ["""
        
        # Add reference type data
        data = [str(analysis["statistics"]["reference_types"][ref_type]) for ref_type in ref_types]
        html += ", ".join(data)
        
        html += """],
                            backgroundColor: [
                                'rgba(54, 162, 235, 0.6)',
                                'rgba(75, 192, 192, 0.6)',
                                'rgba(255, 99, 132, 0.6)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true
                            }
                        }
                    }
                });
            });
        </script>
    </div>
</body>
</html>"""
        
        return html
    
    def generate_custom_report(
        self,
        report_config: Dict[str, Any],
        output_file: Optional[str] = None,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Generate a custom report based on the provided configuration.
        
        Args:
            report_config: Configuration for the custom report
            output_file: File to write the report to
            output_format: Output format ('json', 'csv', 'html')
            
        Returns:
            Dictionary containing the report results
        """
        logger.info("Generating custom report")
        
        # Check required configuration parameters
        required_params = ["name", "sections"]
        for param in required_params:
            if param not in report_config:
                logger.error(f"Missing required parameter '{param}' in report configuration")
                return {"error": f"Missing required parameter '{param}' in report configuration"}
        
        # Prepare report structure
        report = {
            "name": report_config["name"],
            "description": report_config.get("description", "Custom report"),
            "generation_time": datetime.datetime.now().isoformat(),
            "device_type": self.device_type,
            "context_type": self.context_type,
            "version": self.version,
            "sections": {}
        }
        
        # Process each section
        for section_config in report_config["sections"]:
            # Check required section parameters
            if "name" not in section_config or "type" not in section_config:
                logger.warning(f"Skipping section with missing name or type")
                continue
            
            section_name = section_config["name"]
            section_type = section_config["type"]
            
            logger.info(f"Processing section '{section_name}' of type '{section_type}'")
            
            # Process different section types
            if section_type == "policy_summary":
                report["sections"][section_name] = self._generate_policy_summary_section(section_config)
            elif section_type == "object_summary":
                report["sections"][section_name] = self._generate_object_summary_section(section_config)
            elif section_type == "rule_coverage":
                report["sections"][section_name] = self._generate_rule_coverage_section(section_config)
            elif section_type == "unused_objects":
                report["sections"][section_name] = self._generate_unused_objects_section(section_config)
            elif section_type == "duplicate_objects":
                report["sections"][section_name] = self._generate_duplicate_objects_section(section_config)
            elif section_type == "hit_count_analysis":
                if "hit_count_data" not in section_config:
                    logger.warning(f"Skipping section '{section_name}' due to missing hit count data")
                    continue
                
                report["sections"][section_name] = self._generate_hit_count_section(
                    section_config["hit_count_data"], section_config
                )
            elif section_type == "policy_filter":
                report["sections"][section_name] = self._generate_policy_filter_section(section_config)
            elif section_type == "object_filter":
                report["sections"][section_name] = self._generate_object_filter_section(section_config)
            else:
                logger.warning(f"Unknown section type: {section_type}")
                report["sections"][section_name] = {
                    "error": f"Unknown section type: {section_type}"
                }
        
        # Write the report to a file if requested
        if output_file:
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
                
                if output_format.lower() == 'json':
                    with open(output_file, 'w') as f:
                        json.dump(report, f, indent=2)
                    logger.info(f"Custom report saved to {output_file} (JSON format)")
                
                elif output_format.lower() == 'html':
                    # Generate HTML report
                    html_report = self._generate_custom_html_report(report)
                    with open(output_file, 'w') as f:
                        f.write(html_report)
                    logger.info(f"Custom report saved to {output_file} (HTML format)")
                
                else:
                    logger.error(f"Unsupported output format: {output_format}")
            
            except Exception as e:
                logger.error(f"Error saving report to {output_file}: {e}")
        
        return report
    
    def _generate_policy_summary_section(self, section_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a policy summary section for the custom report.
        
        Args:
            section_config: Configuration for the section
            
        Returns:
            Dictionary containing the section data
        """
        logger.debug("Generating policy summary section")
        
        # Get policy type from configuration
        policy_type = section_config.get("policy_type")
        
        # If policy type is not specified, determine based on device type
        if not policy_type:
            if self.device_type.lower() == "panorama":
                policy_type = "security_pre_rules"
            else:
                policy_type = "security_rules"
            logger.debug(f"Using default policy type: {policy_type}")
        
        # Get all policies of the specified type
        policies = get_policies(self.tree, policy_type, self.device_type, 
                               self.context_type, self.version, **self.context_kwargs)
        
        if not policies:
            logger.warning(f"No {policy_type} policies found")
            return {"error": f"No {policy_type} policies found"}
        
        # Prepare section data
        section_data = {
            "policy_type": policy_type,
            "total_count": len(policies),
            "disabled_count": 0,
            "action_distribution": Counter(),
            "source_zone_distribution": Counter(),
            "destination_zone_distribution": Counter(),
            "policies_with_any_source": 0,
            "policies_with_any_destination": 0,
            "policies_with_any_service": 0,
            "policies_with_any_application": 0,
            "policies_with_profile_group": 0,
            "policies_with_log_forwarding": 0
        }
        
        # Process each policy
        for name, policy in policies.items():
            # Check if disabled
            if policy.get("disabled", "no") == "yes":
                section_data["disabled_count"] += 1
            
            # Check action
            action = policy.get("action", "unknown")
            section_data["action_distribution"][action] += 1
            
            # Check zones
            for zone in policy.get("from", []):
                section_data["source_zone_distribution"][zone] += 1
            
            for zone in policy.get("to", []):
                section_data["destination_zone_distribution"][zone] += 1
            
            # Check for 'any' values
            if "source" in policy and "any" in policy["source"]:
                section_data["policies_with_any_source"] += 1
            
            if "destination" in policy and "any" in policy["destination"]:
                section_data["policies_with_any_destination"] += 1
            
            if "service" in policy and "any" in policy["service"]:
                section_data["policies_with_any_service"] += 1
            
            if "application" in policy and "any" in policy["application"]:
                section_data["policies_with_any_application"] += 1
            
            # Check for profile group
            if "profile-setting" in policy and "group" in policy["profile-setting"]:
                section_data["policies_with_profile_group"] += 1
            
            # Check for log forwarding
            if "log-setting" in policy:
                section_data["policies_with_log_forwarding"] += 1
        
        # Convert Counter objects to dictionaries for JSON serialization
        section_data["action_distribution"] = dict(section_data["action_distribution"])
        section_data["source_zone_distribution"] = dict(section_data["source_zone_distribution"])
        section_data["destination_zone_distribution"] = dict(section_data["destination_zone_distribution"])
        
        # Calculate percentages
        section_data["disabled_percentage"] = (section_data["disabled_count"] / section_data["total_count"]) * 100 if section_data["total_count"] > 0 else 0
        section_data["any_source_percentage"] = (section_data["policies_with_any_source"] / section_data["total_count"]) * 100 if section_data["total_count"] > 0 else 0
        section_data["any_destination_percentage"] = (section_data["policies_with_any_destination"] / section_data["total_count"]) * 100 if section_data["total_count"] > 0 else 0
        section_data["any_service_percentage"] = (section_data["policies_with_any_service"] / section_data["total_count"]) * 100 if section_data["total_count"] > 0 else 0
        section_data["any_application_percentage"] = (section_data["policies_with_any_application"] / section_data["total_count"]) * 100 if section_data["total_count"] > 0 else 0
        section_data["profile_group_percentage"] = (section_data["policies_with_profile_group"] / section_data["total_count"]) * 100 if section_data["total_count"] > 0 else 0
        section_data["log_forwarding_percentage"] = (section_data["policies_with_log_forwarding"] / section_data["total_count"]) * 100 if section_data["total_count"] > 0 else 0
        
        return section_data
    
    def _generate_object_summary_section(self, section_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an object summary section for the custom report.
        
        Args:
            section_config: Configuration for the section
            
        Returns:
            Dictionary containing the section data
        """
        logger.debug("Generating object summary section")
        
        # Get object type from configuration
        object_type = section_config.get("object_type", "address")
        
        # Get all objects of the specified type
        objects = get_objects(self.tree, object_type, self.device_type, 
                             self.context_type, self.version, **self.context_kwargs)
        
        if not objects:
            logger.warning(f"No {object_type} objects found")
            return {"error": f"No {object_type} objects found"}
        
        # Prepare section data
        section_data = {
            "object_type": object_type,
            "total_count": len(objects)
        }
        
        # Add type-specific data
        if object_type == "address":
            section_data["type_distribution"] = {
                "ip-netmask": 0,
                "ip-range": 0,
                "fqdn": 0,
                "other": 0
            }
            
            # Process each address object
            for name, obj in objects.items():
                if "ip-netmask" in obj:
                    section_data["type_distribution"]["ip-netmask"] += 1
                elif "ip-range" in obj:
                    section_data["type_distribution"]["ip-range"] += 1
                elif "fqdn" in obj:
                    section_data["type_distribution"]["fqdn"] += 1
                else:
                    section_data["type_distribution"]["other"] += 1
        
        elif object_type.endswith("_group"):
            section_data["type_distribution"] = {
                "static": 0,
                "dynamic": 0
            }
            
            section_data["member_count_distribution"] = {
                "0": 0,
                "1-5": 0,
                "6-20": 0,
                "21+": 0
            }
            
            # Process each group object
            for name, obj in objects.items():
                if "static" in obj:
                    section_data["type_distribution"]["static"] += 1
                    
                    # Count members
                    member_count = len(obj["static"]) if isinstance(obj["static"], list) else 0
                    
                    if member_count == 0:
                        section_data["member_count_distribution"]["0"] += 1
                    elif member_count <= 5:
                        section_data["member_count_distribution"]["1-5"] += 1
                    elif member_count <= 20:
                        section_data["member_count_distribution"]["6-20"] += 1
                    else:
                        section_data["member_count_distribution"]["21+"] += 1
                else:
                    section_data["type_distribution"]["dynamic"] += 1
                    section_data["member_count_distribution"]["0"] += 1  # Dynamic groups don't have static members
        
        # Include sample objects if requested
        if section_config.get("include_samples", False):
            max_samples = section_config.get("max_samples", 5)
            sample_keys = list(objects.keys())[:max_samples]
            
            section_data["samples"] = {}
            for key in sample_keys:
                section_data["samples"][key] = objects[key]
        
        return section_data
    
    def _generate_rule_coverage_section(self, section_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a rule coverage section for the custom report.
        
        Args:
            section_config: Configuration for the section
            
        Returns:
            Dictionary containing the section data
        """
        logger.debug("Generating rule coverage section")
        
        # Prepare section data
        section_data = {
            "potential_shadowing": [],
            "any_any_rules": [],
            "disabled_rules": []
        }
        
        # Get policy type from configuration
        policy_type = section_config.get("policy_type")
        
        # If policy type is not specified, determine based on device type
        if not policy_type:
            if self.device_type.lower() == "panorama":
                policy_type = "security_pre_rules"
            else:
                policy_type = "security_rules"
        
        # Get all policies of the specified type
        policies = get_policies(self.tree, policy_type, self.device_type, 
                               self.context_type, self.version, **self.context_kwargs)
        
        if not policies:
            logger.warning(f"No {policy_type} policies found")
            return {"error": f"No {policy_type} policies found"}
        
        # Check for any-any rules
        for name, policy in policies.items():
            # Check if disabled
            if policy.get("disabled", "no") == "yes":
                section_data["disabled_rules"].append({
                    "name": name,
                    "action": policy.get("action", "unknown")
                })
                continue  # Skip further checks for disabled rules
            
            # Check for any-any rules
            is_any_source = "source" in policy and "any" in policy["source"]
            is_any_dest = "destination" in policy and "any" in policy["destination"]
            is_any_service = "service" in policy and "any" in policy["service"]
            is_any_app = "application" in policy and "any" in policy["application"]
            
            if is_any_source and is_any_dest:
                section_data["any_any_rules"].append({
                    "name": name,
                    "action": policy.get("action", "unknown"),
                    "any_service": is_any_service,
                    "any_application": is_any_app
                })
        
        # Check for potential shadowing (overlapping rules with different actions)
        policy_list = []
        for name, policy in policies.items():
            if policy.get("disabled", "no") != "yes":  # Skip disabled rules
                policy_list.append((name, policy))
        
        # Sort policies by index (assuming they are in order in the configuration)
        # This is important for shadowing analysis
        policy_list.sort(key=lambda p: list(policies.keys()).index(p[0]))
        
        # Check each pair of policies for shadowing
        for i in range(len(policy_list) - 1):
            name1, policy1 = policy_list[i]
            
            for j in range(i + 1, len(policy_list)):
                name2, policy2 = policy_list[j]
                
                # Check if policies can shadow each other
                overlap = self._check_policy_overlap(policy1, policy2)
                
                if overlap["has_overlap"] and policy1.get("action", "") != policy2.get("action", ""):
                    section_data["potential_shadowing"].append({
                        "first_rule": name1,
                        "first_action": policy1.get("action", "unknown"),
                        "second_rule": name2,
                        "second_action": policy2.get("action", "unknown"),
                        "overlap_fields": overlap["fields"]
                    })
        
        # Add summary counts
        section_data["any_any_count"] = len(section_data["any_any_rules"])
        section_data["disabled_count"] = len(section_data["disabled_rules"])
        section_data["shadowing_count"] = len(section_data["potential_shadowing"])
        section_data["total_count"] = len(policies)
        
        # Calculate percentages
        section_data["any_any_percentage"] = (section_data["any_any_count"] / section_data["total_count"]) * 100 if section_data["total_count"] > 0 else 0
        section_data["disabled_percentage"] = (section_data["disabled_count"] / section_data["total_count"]) * 100 if section_data["total_count"] > 0 else 0
        
        return section_data
    
    def _generate_unused_objects_section(self, section_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an unused objects section for the custom report.
        
        Args:
            section_config: Configuration for the section
            
        Returns:
            Dictionary containing the section data
        """
        logger.debug("Generating unused objects section")
        
        # Get object type from configuration
        object_type = section_config.get("object_type", "address")
        
        # Use the built-in unused objects report function
        from ..modules.reports import generate_unused_objects_report
        
        report_data = generate_unused_objects_report(
            self.tree, self.device_type, self.context_type, self.version, 
            None, **self.context_kwargs
        )
        
        # Extract and format the unused objects data
        section_data = {
            "object_type": object_type,
            "unused_objects": []
        }
        
        if "unused_objects" in report_data:
            for obj in report_data["unused_objects"]:
                section_data["unused_objects"].append({
                    "name": obj["name"],
                    "properties": obj["properties"]
                })
        
        # Add summary counts
        section_data["unused_count"] = len(section_data["unused_objects"])
        
        # Get total objects count for percentage calculation
        objects = get_objects(self.tree, object_type, self.device_type, 
                             self.context_type, self.version, **self.context_kwargs)
        
        section_data["total_count"] = len(objects) if objects else 0
        
        # Calculate percentage
        section_data["unused_percentage"] = (section_data["unused_count"] / section_data["total_count"]) * 100 if section_data["total_count"] > 0 else 0
        
        return section_data
    
    def _generate_duplicate_objects_section(self, section_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a duplicate objects section for the custom report.
        
        Args:
            section_config: Configuration for the section
            
        Returns:
            Dictionary containing the section data
        """
        logger.debug("Generating duplicate objects section")
        
        # Get object type from configuration
        object_type = section_config.get("object_type", "address")
        
        # Use the built-in duplicate objects report function
        from ..modules.reports import generate_duplicate_objects_report
        
        report_data = generate_duplicate_objects_report(
            self.tree, self.device_type, self.context_type, self.version, 
            None, **self.context_kwargs
        )
        
        # Extract and format the duplicate objects data
        section_data = {
            "object_type": object_type,
            "duplicate_objects": []
        }
        
        if "duplicate_objects" in report_data:
            duplicate_sets = report_data["duplicate_objects"]
            
            for value_key, names in duplicate_sets.items():
                section_data["duplicate_objects"].append({
                    "value": value_key,
                    "objects": names
                })
        
        # Add summary counts
        section_data["duplicate_set_count"] = len(section_data["duplicate_objects"])
        duplicate_object_count = sum(len(dupe_set["objects"]) - 1 for dupe_set in section_data["duplicate_objects"])
        section_data["duplicate_object_count"] = duplicate_object_count
        
        # Get total objects count for percentage calculation
        objects = get_objects(self.tree, object_type, self.device_type, 
                             self.context_type, self.version, **self.context_kwargs)
        
        section_data["total_count"] = len(objects) if objects else 0
        
        # Calculate percentage
        section_data["duplicate_percentage"] = (duplicate_object_count / section_data["total_count"]) * 100 if section_data["total_count"] > 0 else 0
        
        return section_data
    
    def _generate_hit_count_section(
        self,
        hit_count_data: Dict[str, Dict[str, int]],
        section_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a hit count analysis section for the custom report.
        
        Args:
            hit_count_data: Hit count data for policies
            section_config: Configuration for the section
            
        Returns:
            Dictionary containing the section data
        """
        logger.debug("Generating hit count analysis section")
        
        # Get policy type from configuration
        policy_type = section_config.get("policy_type")
        
        # If policy type is not specified, determine based on device type
        if not policy_type:
            if self.device_type.lower() == "panorama":
                policy_type = "security_pre_rules"
            else:
                policy_type = "security_rules"
        
        # Get all policies of the specified type
        policies = get_policies(self.tree, policy_type, self.device_type, 
                               self.context_type, self.version, **self.context_kwargs)
        
        if not policies:
            logger.warning(f"No {policy_type} policies found")
            return {"error": f"No {policy_type} policies found"}
        
        # Prepare section data
        section_data = {
            "policy_type": policy_type,
            "total_count": len(policies),
            "zero_hit_count": 0,
            "low_hit_count": 0,
            "medium_hit_count": 0,
            "high_hit_count": 0,
            "zero_hit_policies": [],
            "low_hit_policies": [],
            "high_hit_policies": []
        }
        
        # Process each policy
        hit_counts = []
        
        for name, policy in policies.items():
            # Skip disabled policies
            if policy.get("disabled", "no") == "yes":
                continue
            
            # Get hit count for this policy
            if name in hit_count_data:
                hit_count = hit_count_data[name]["hit_count"]
                hit_counts.append(hit_count)
                
                # Categorize by hit count
                if hit_count == 0:
                    section_data["zero_hit_count"] += 1
                    section_data["zero_hit_policies"].append({
                        "name": name,
                        "action": policy.get("action", "unknown")
                    })
                elif hit_count < 100:
                    section_data["low_hit_count"] += 1
                    if len(section_data["low_hit_policies"]) < 10:  # Limit to 10 examples
                        section_data["low_hit_policies"].append({
                            "name": name,
                            "hit_count": hit_count,
                            "action": policy.get("action", "unknown")
                        })
                elif hit_count < 1000:
                    section_data["medium_hit_count"] += 1
                else:
                    section_data["high_hit_count"] += 1
                    if len(section_data["high_hit_policies"]) < 10:  # Limit to 10 examples
                        section_data["high_hit_policies"].append({
                            "name": name,
                            "hit_count": hit_count,
                            "action": policy.get("action", "unknown")
                        })
        
        # Calculate statistics
        if hit_counts:
            section_data["hit_count_stats"] = {
                "min": min(hit_counts),
                "max": max(hit_counts),
                "avg": sum(hit_counts) / len(hit_counts),
                "total": sum(hit_counts)
            }
            
            # Calculate median
            sorted_counts = sorted(hit_counts)
            mid = len(sorted_counts) // 2
            if len(sorted_counts) % 2 == 0:
                section_data["hit_count_stats"]["median"] = (sorted_counts[mid-1] + sorted_counts[mid]) / 2
            else:
                section_data["hit_count_stats"]["median"] = sorted_counts[mid]
        
        # Calculate percentages
        active_policies = len(policies) - section_data.get("disabled_count", 0)
        if active_policies > 0:
            section_data["zero_hit_percentage"] = (section_data["zero_hit_count"] / active_policies) * 100
            section_data["low_hit_percentage"] = (section_data["low_hit_count"] / active_policies) * 100
            section_data["medium_hit_percentage"] = (section_data["medium_hit_count"] / active_policies) * 100
            section_data["high_hit_percentage"] = (section_data["high_hit_count"] / active_policies) * 100
        
        return section_data
    
    def _generate_policy_filter_section(self, section_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a policy filter section for the custom report.
        
        Args:
            section_config: Configuration for the section
            
        Returns:
            Dictionary containing the section data
        """
        logger.debug("Generating policy filter section")
        
        # Get policy type and criteria from configuration
        policy_type = section_config.get("policy_type")
        criteria = section_config.get("criteria", {})
        
        # If policy type is not specified, determine based on device type
        if not policy_type:
            if self.device_type.lower() == "panorama":
                policy_type = "security_pre_rules"
            else:
                policy_type = "security_rules"
        
        # Use the ConfigQuery to select policies matching criteria
        selected_policies = self.query.select_policies(policy_type, criteria)
        
        if not selected_policies:
            logger.warning(f"No {policy_type} policies match the filter criteria")
            return {
                "policy_type": policy_type,
                "criteria": criteria,
                "filtered_count": 0,
                "filtered_policies": []
            }
        
        # Format the results
        section_data = {
            "policy_type": policy_type,
            "criteria": criteria,
            "filtered_count": len(selected_policies),
            "filtered_policies": []
        }
        
        # Get all policies to determine the total count
        all_policies = get_policies(self.tree, policy_type, self.device_type, 
                                  self.context_type, self.version, **self.context_kwargs)
        
        section_data["total_count"] = len(all_policies) if all_policies else 0
        
        # Add selected policies to the results
        for policy in selected_policies:
            policy_data = {
                "name": policy.get("name", "unknown"),
                "data": {}
            }
            
            # Extract key properties
            for key in ["action", "disabled", "from", "to", "source", "destination", "service", "application"]:
                if key in policy.attrib:
                    policy_data["data"][key] = policy.attrib[key]
            
            section_data["filtered_policies"].append(policy_data)
        
        # Calculate percentage
        section_data["filtered_percentage"] = (section_data["filtered_count"] / section_data["total_count"]) * 100 if section_data["total_count"] > 0 else 0
        
        return section_data
    
    def _generate_object_filter_section(self, section_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an object filter section for the custom report.
        
        Args:
            section_config: Configuration for the section
            
        Returns:
            Dictionary containing the section data
        """
        logger.debug("Generating object filter section")
        
        # Get object type and criteria from configuration
        object_type = section_config.get("object_type", "address")
        criteria = section_config.get("criteria", {})
        
        # Use the ConfigQuery to select objects matching criteria
        selected_objects = self.query.select_objects(object_type, criteria)
        
        if not selected_objects:
            logger.warning(f"No {object_type} objects match the filter criteria")
            return {
                "object_type": object_type,
                "criteria": criteria,
                "filtered_count": 0,
                "filtered_objects": []
            }
        
        # Format the results
        section_data = {
            "object_type": object_type,
            "criteria": criteria,
            "filtered_count": len(selected_objects),
            "filtered_objects": []
        }
        
        # Get all objects to determine the total count
        all_objects = get_objects(self.tree, object_type, self.device_type, 
                                self.context_type, self.version, **self.context_kwargs)
        
        section_data["total_count"] = len(all_objects) if all_objects else 0
        
        # Add selected objects to the results
        for obj in selected_objects:
            obj_data = {
                "name": obj.get("name", "unknown"),
                "data": {}
            }
            
            # Extract object data
            if object_type == "address":
                for key in ["ip-netmask", "ip-range", "fqdn"]:
                    elem = obj.find(f"./{key}")
                    if elem is not None and elem.text:
                        obj_data["data"][key] = elem.text
            elif object_type.endswith("_group"):
                static = obj.find("./static")
                if static is not None:
                    members = static.findall("./member")
                    obj_data["data"]["type"] = "static"
                    obj_data["data"]["members"] = [m.text for m in members if m.text]
                else:
                    dynamic = obj.find("./dynamic")
                    if dynamic is not None:
                        filter_elem = dynamic.find("./filter")
                        obj_data["data"]["type"] = "dynamic"
                        if filter_elem is not None and filter_elem.text:
                            obj_data["data"]["filter"] = filter_elem.text
            
            section_data["filtered_objects"].append(obj_data)
        
        # Calculate percentage
        section_data["filtered_percentage"] = (section_data["filtered_count"] / section_data["total_count"]) * 100 if section_data["total_count"] > 0 else 0
        
        return section_data
    
    def _generate_custom_html_report(self, report: Dict[str, Any]) -> str:
        """
        Generate an HTML report from the custom report data.
        
        Args:
            report: Report data
            
        Returns:
            HTML report as a string
        """
        # Create HTML template with Bootstrap
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report["name"]}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js"></script>
    <style>
        body {{ padding: 20px; }}
        .card {{ margin-bottom: 20px; }}
        .section {{ margin-bottom: 40px; }}
        .summary-item {{ font-size: 16px; margin: 5px 0; }}
        .chart-container {{ position: relative; height: 300px; margin-bottom: 20px; }}
        .table-responsive {{ margin-bottom: 20px; }}
        .object-row:hover, .policy-row:hover {{ background-color: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1 class="mb-4">{report["name"]}</h1>
        <p class="text-muted">
            {report["description"]} - Generated on {report["generation_time"]} for 
            {report["device_type"]}/{report["context_type"]}
        </p>
        
        <div class="row">"""
        
        # Add sections
        for section_name, section_data in report["sections"].items():
            html += f"""
            <div class="col-12 section">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">{section_name}</h5>
                    </div>
                    <div class="card-body">"""
            
            # Add section-specific content
            if "policy_type" in section_data:
                # This is a policy-related section
                html += self._generate_policy_section_html(section_data)
            elif "object_type" in section_data:
                # This is an object-related section
                html += self._generate_object_section_html(section_data)
            else:
                # Generic section
                html += f"""
                        <pre>{json.dumps(section_data, indent=2)}</pre>"""
            
            html += """
                    </div>
                </div>
            </div>"""
        
        html += """
        </div>
    </div>
    <script>
        // Initialize charts on page load
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize all chart elements
            const chartElements = document.querySelectorAll('[id^="chart-"]');
            chartElements.forEach(function(element) {
                if (element.dataset.type === 'pie') {
                    createPieChart(element.id, 
                                  JSON.parse(element.dataset.labels), 
                                  JSON.parse(element.dataset.values));
                } else if (element.dataset.type === 'bar') {
                    createBarChart(element.id, 
                                  JSON.parse(element.dataset.labels), 
                                  JSON.parse(element.dataset.values));
                }
            });
        });
        
        // Create a pie chart
        function createPieChart(elementId, labels, values) {
            const ctx = document.getElementById(elementId).getContext('2d');
            new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: [
                            'rgba(75, 192, 192, 0.6)',
                            'rgba(255, 99, 132, 0.6)',
                            'rgba(54, 162, 235, 0.6)',
                            'rgba(255, 206, 86, 0.6)',
                            'rgba(153, 102, 255, 0.6)',
                            'rgba(255, 159, 64, 0.6)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right'
                        }
                    }
                }
            });
        }
        
        // Create a bar chart
        function createBarChart(elementId, labels, values) {
            const ctx = document.getElementById(elementId).getContext('2d');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Count',
                        data: values,
                        backgroundColor: 'rgba(54, 162, 235, 0.6)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    </script>
</body>
</html>"""
        
        return html
    
    def _generate_policy_section_html(self, section_data: Dict[str, Any]) -> str:
        """
        Generate HTML content for a policy-related section.
        
        Args:
            section_data: Section data
            
        Returns:
            HTML content as a string
        """
        html = ""
        
        # Check section type
        if "action_distribution" in section_data:
            # Policy summary section
            html += f"""
            <div class="row">
                <div class="col-md-6">
                    <h6>Summary</h6>
                    <div class="summary-item"><strong>Policy Type:</strong> {section_data["policy_type"]}</div>
                    <div class="summary-item"><strong>Total Count:</strong> {section_data["total_count"]}</div>
                    <div class="summary-item"><strong>Disabled Count:</strong> {section_data["disabled_count"]} ({section_data.get("disabled_percentage", 0):.1f}%)</div>
                    <div class="summary-item"><strong>Policies with 'Any' Source:</strong> {section_data["policies_with_any_source"]} ({section_data.get("any_source_percentage", 0):.1f}%)</div>
                    <div class="summary-item"><strong>Policies with 'Any' Destination:</strong> {section_data["policies_with_any_destination"]} ({section_data.get("any_destination_percentage", 0):.1f}%)</div>
                    <div class="summary-item"><strong>Policies with Profile Group:</strong> {section_data["policies_with_profile_group"]} ({section_data.get("profile_group_percentage", 0):.1f}%)</div>
                    <div class="summary-item"><strong>Policies with Log Forwarding:</strong> {section_data["policies_with_log_forwarding"]} ({section_data.get("log_forwarding_percentage", 0):.1f}%)</div>
                </div>
                <div class="col-md-6">
                    <h6>Action Distribution</h6>
                    <div class="chart-container">
                        <canvas id="chart-action-dist" 
                                data-type="pie" 
                                data-labels='{json.dumps(list(section_data["action_distribution"].keys()))}' 
                                data-values='{json.dumps(list(section_data["action_distribution"].values()))}'>
                        </canvas>
                    </div>
                </div>
            </div>"""
            
            # Add zone distribution if available
            if section_data.get("source_zone_distribution"):
                source_zones = list(section_data["source_zone_distribution"].keys())
                source_counts = list(section_data["source_zone_distribution"].values())
                
                destination_zones = list(section_data.get("destination_zone_distribution", {}).keys())
                destination_counts = list(section_data.get("destination_zone_distribution", {}).values())
                
                html += f"""
                <div class="row">
                    <div class="col-md-6">
                        <h6>Source Zone Distribution</h6>
                        <div class="chart-container">
                            <canvas id="chart-source-zone" 
                                    data-type="bar" 
                                    data-labels='{json.dumps(source_zones)}' 
                                    data-values='{json.dumps(source_counts)}'>
                            </canvas>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <h6>Destination Zone Distribution</h6>
                        <div class="chart-container">
                            <canvas id="chart-dest-zone" 
                                    data-type="bar" 
                                    data-labels='{json.dumps(destination_zones)}' 
                                    data-values='{json.dumps(destination_counts)}'>
                            </canvas>
                        </div>
                    </div>
                </div>"""
        
        elif "any_any_rules" in section_data:
            # Rule coverage section
            html += f"""
            <div class="row">
                <div class="col-md-6">
                    <h6>Summary</h6>
                    <div class="summary-item"><strong>Total Rules:</strong> {section_data["total_count"]}</div>
                    <div class="summary-item"><strong>Disabled Rules:</strong> {section_data["disabled_count"]} ({section_data.get("disabled_percentage", 0):.1f}%)</div>
                    <div class="summary-item"><strong>Any-Any Rules:</strong> {section_data["any_any_count"]} ({section_data.get("any_any_percentage", 0):.1f}%)</div>
                    <div class="summary-item"><strong>Potential Shadowing Cases:</strong> {section_data["shadowing_count"]}</div>
                </div>
                <div class="col-md-6">
                    <h6>Distribution</h6>
                    <div class="chart-container">
                        <canvas id="chart-rule-types" 
                                data-type="pie" 
                                data-labels='{json.dumps(["Any-Any Rules", "Other Rules", "Disabled Rules"])}' 
                                data-values='{json.dumps([
                                    section_data["any_any_count"], 
                                    section_data["total_count"] - section_data["any_any_count"] - section_data["disabled_count"],
                                    section_data["disabled_count"]
                                ])}'>
                        </canvas>
                    </div>
                </div>
            </div>"""
            
            # Add any-any rules table
            if section_data["any_any_count"] > 0:
                html += """
                <div class="row mt-3">
                    <div class="col-12">
                        <h6>Any-Any Rules</h6>
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead>
                                    <tr>
                                        <th>Rule Name</th>
                                        <th>Action</th>
                                        <th>Any Service</th>
                                        <th>Any Application</th>
                                    </tr>
                                </thead>
                                <tbody>"""
                
                for rule in section_data["any_any_rules"]:
                    html += f"""
                                    <tr class="policy-row">
                                        <td>{rule["name"]}</td>
                                        <td>{rule["action"]}</td>
                                        <td>{"Yes" if rule.get("any_service", False) else "No"}</td>
                                        <td>{"Yes" if rule.get("any_application", False) else "No"}</td>
                                    </tr>"""
                
                html += """
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>"""
            
            # Add shadowing table
            if section_data["shadowing_count"] > 0:
                html += """
                <div class="row mt-3">
                    <div class="col-12">
                        <h6>Potential Shadowing</h6>
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead>
                                    <tr>
                                        <th>First Rule</th>
                                        <th>First Action</th>
                                        <th>Second Rule</th>
                                        <th>Second Action</th>
                                        <th>Overlapping Fields</th>
                                    </tr>
                                </thead>
                                <tbody>"""
                
                for shadow in section_data["potential_shadowing"]:
                    html += f"""
                                    <tr class="policy-row">
                                        <td>{shadow["first_rule"]}</td>
                                        <td>{shadow["first_action"]}</td>
                                        <td>{shadow["second_rule"]}</td>
                                        <td>{shadow["second_action"]}</td>
                                        <td>{", ".join(shadow["overlap_fields"])}</td>
                                    </tr>"""
                
                html += """
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>"""
                
        elif "hit_count_stats" in section_data:
            # Hit count section
            html += f"""
            <div class="row">
                <div class="col-md-6">
                    <h6>Summary</h6>
                    <div class="summary-item"><strong>Policy Type:</strong> {section_data["policy_type"]}</div>
                    <div class="summary-item"><strong>Total Policies:</strong> {section_data["total_count"]}</div>
                    <div class="summary-item"><strong>Zero Hits:</strong> {section_data["zero_hit_count"]} ({section_data.get("zero_hit_percentage", 0):.1f}%)</div>
                    <div class="summary-item"><strong>Low Hits (&lt;100):</strong> {section_data["low_hit_count"]} ({section_data.get("low_hit_percentage", 0):.1f}%)</div>
                    <div class="summary-item"><strong>Medium Hits (100-999):</strong> {section_data["medium_hit_count"]} ({section_data.get("medium_hit_percentage", 0):.1f}%)</div>
                    <div class="summary-item"><strong>High Hits (1000+):</strong> {section_data["high_hit_count"]} ({section_data.get("high_hit_percentage", 0):.1f}%)</div>
                </div>
                <div class="col-md-6">
                    <h6>Hit Count Statistics</h6>
                    <div class="summary-item"><strong>Min Hits:</strong> {section_data["hit_count_stats"]["min"]}</div>
                    <div class="summary-item"><strong>Max Hits:</strong> {section_data["hit_count_stats"]["max"]}</div>
                    <div class="summary-item"><strong>Average Hits:</strong> {section_data["hit_count_stats"]["avg"]:.2f}</div>
                    <div class="summary-item"><strong>Median Hits:</strong> {section_data["hit_count_stats"]["median"]}</div>
                    <div class="summary-item"><strong>Total Hits:</strong> {section_data["hit_count_stats"]["total"]}</div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-12">
                    <h6>Hit Count Distribution</h6>
                    <div class="chart-container">
                        <canvas id="chart-hit-dist" 
                                data-type="pie" 
                                data-labels='{json.dumps(["Zero Hits", "Low Hits (<100)", "Medium Hits (100-999)", "High Hits (1000+)"])}' 
                                data-values='{json.dumps([
                                    section_data["zero_hit_count"], 
                                    section_data["low_hit_count"],
                                    section_data["medium_hit_count"],
                                    section_data["high_hit_count"]
                                ])}'>
                        </canvas>
                    </div>
                </div>
            </div>"""
            
            # Add zero hit policies table
            if section_data["zero_hit_count"] > 0:
                html += """
                <div class="row mt-3">
                    <div class="col-12">
                        <h6>Zero Hit Policies</h6>
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead>
                                    <tr>
                                        <th>Policy Name</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody>"""
                
                for policy in section_data["zero_hit_policies"]:
                    html += f"""
                                    <tr class="policy-row">
                                        <td>{policy["name"]}</td>
                                        <td>{policy["action"]}</td>
                                    </tr>"""
                
                html += """
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>"""
        
        elif "filtered_policies" in section_data:
            # Policy filter section
            html += f"""
            <div class="row">
                <div class="col-12">
                    <h6>Filter Summary</h6>
                    <div class="summary-item"><strong>Policy Type:</strong> {section_data["policy_type"]}</div>
                    <div class="summary-item"><strong>Filter Criteria:</strong> {json.dumps(section_data["criteria"])}</div>
                    <div class="summary-item"><strong>Matching Policies:</strong> {section_data["filtered_count"]} of {section_data["total_count"]} ({section_data.get("filtered_percentage", 0):.1f}%)</div>
                </div>
            </div>"""
            
            # Add filtered policies table
            if section_data["filtered_count"] > 0:
                html += """
                <div class="row mt-3">
                    <div class="col-12">
                        <h6>Matching Policies</h6>
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead>
                                    <tr>
                                        <th>Policy Name</th>
                                        <th>Details</th>
                                    </tr>
                                </thead>
                                <tbody>"""
                
                for policy in section_data["filtered_policies"]:
                    html += f"""
                                    <tr class="policy-row">
                                        <td>{policy["name"]}</td>
                                        <td>{json.dumps(policy.get("data", {}))}</td>
                                    </tr>"""
                
                html += """
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>"""
        
        return html
    
    def _generate_object_section_html(self, section_data: Dict[str, Any]) -> str:
        """
        Generate HTML content for an object-related section.
        
        Args:
            section_data: Section data
            
        Returns:
            HTML content as a string
        """
        html = ""
        
        # Check section type
        if "type_distribution" in section_data:
            # Object summary section
            html += f"""
            <div class="row">
                <div class="col-md-6">
                    <h6>Summary</h6>
                    <div class="summary-item"><strong>Object Type:</strong> {section_data["object_type"]}</div>
                    <div class="summary-item"><strong>Total Count:</strong> {section_data["total_count"]}</div>"""
            
            # Add type-specific summary items
            if section_data["object_type"] == "address":
                html += f"""
                    <div class="summary-item"><strong>IP-Netmask:</strong> {section_data["type_distribution"]["ip-netmask"]}</div>
                    <div class="summary-item"><strong>IP-Range:</strong> {section_data["type_distribution"]["ip-range"]}</div>
                    <div class="summary-item"><strong>FQDN:</strong> {section_data["type_distribution"]["fqdn"]}</div>
                    <div class="summary-item"><strong>Other:</strong> {section_data["type_distribution"]["other"]}</div>"""
            elif section_data["object_type"].endswith("_group"):
                html += f"""
                    <div class="summary-item"><strong>Static Groups:</strong> {section_data["type_distribution"]["static"]}</div>
                    <div class="summary-item"><strong>Dynamic Groups:</strong> {section_data["type_distribution"]["dynamic"]}</div>
                    <div class="summary-item"><strong>Empty Groups:</strong> {section_data["member_count_distribution"]["0"]}</div>
                    <div class="summary-item"><strong>Small Groups (1-5):</strong> {section_data["member_count_distribution"]["1-5"]}</div>
                    <div class="summary-item"><strong>Medium Groups (6-20):</strong> {section_data["member_count_distribution"]["6-20"]}</div>
                    <div class="summary-item"><strong>Large Groups (21+):</strong> {section_data["member_count_distribution"]["21+"]}</div>"""
            
            html += """
                </div>
                <div class="col-md-6">
                    <h6>Type Distribution</h6>
                    <div class="chart-container">"""
            
            # Add type distribution chart
            if section_data["object_type"] == "address":
                html += f"""
                        <canvas id="chart-type-dist" 
                                data-type="pie" 
                                data-labels='{json.dumps(["IP-Netmask", "IP-Range", "FQDN", "Other"])}' 
                                data-values='{json.dumps([
                                    section_data["type_distribution"]["ip-netmask"],
                                    section_data["type_distribution"]["ip-range"],
                                    section_data["type_distribution"]["fqdn"],
                                    section_data["type_distribution"]["other"]
                                ])}'>
                        </canvas>"""
            elif section_data["object_type"].endswith("_group"):
                html += f"""
                        <canvas id="chart-type-dist" 
                                data-type="pie" 
                                data-labels='{json.dumps(["Static", "Dynamic"])}' 
                                data-values='{json.dumps([
                                    section_data["type_distribution"]["static"],
                                    section_data["type_distribution"]["dynamic"]
                                ])}'>
                        </canvas>"""
            
            html += """
                    </div>
                </div>
            </div>"""
            
            # Add member count distribution chart for groups
            if section_data["object_type"].endswith("_group"):
                html += f"""
                <div class="row">
                    <div class="col-12">
                        <h6>Member Count Distribution</h6>
                        <div class="chart-container">
                            <canvas id="chart-member-dist" 
                                    data-type="bar" 
                                    data-labels='{json.dumps(["Empty (0)", "Small (1-5)", "Medium (6-20)", "Large (21+)"])}' 
                                    data-values='{json.dumps([
                                        section_data["member_count_distribution"]["0"],
                                        section_data["member_count_distribution"]["1-5"],
                                        section_data["member_count_distribution"]["6-20"],
                                        section_data["member_count_distribution"]["21+"]
                                    ])}'>
                            </canvas>
                        </div>
                    </div>
                </div>"""
            
            # Add sample objects if available
            if "samples" in section_data:
                html += """
                <div class="row mt-3">
                    <div class="col-12">
                        <h6>Sample Objects</h6>
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead>
                                    <tr>
                                        <th>Object Name</th>
                                        <th>Properties</th>
                                    </tr>
                                </thead>
                                <tbody>"""
                
                for name, obj in section_data["samples"].items():
                    html += f"""
                                    <tr class="object-row">
                                        <td>{name}</td>
                                        <td>{json.dumps(obj)}</td>
                                    </tr>"""
                
                html += """
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>"""
        
        elif "unused_objects" in section_data:
            # Unused objects section
            html += f"""
            <div class="row">
                <div class="col-md-6">
                    <h6>Summary</h6>
                    <div class="summary-item"><strong>Object Type:</strong> {section_data["object_type"]}</div>
                    <div class="summary-item"><strong>Total Objects:</strong> {section_data["total_count"]}</div>
                    <div class="summary-item"><strong>Unused Objects:</strong> {section_data["unused_count"]} ({section_data.get("unused_percentage", 0):.1f}%)</div>
                </div>
                <div class="col-md-6">
                    <h6>Usage Distribution</h6>
                    <div class="chart-container">
                        <canvas id="chart-usage-dist" 
                                data-type="pie" 
                                data-labels='{json.dumps(["Used", "Unused"])}' 
                                data-values='{json.dumps([
                                    section_data["total_count"] - section_data["unused_count"],
                                    section_data["unused_count"]
                                ])}'>
                        </canvas>
                    </div>
                </div>
            </div>"""
            
            # Add unused objects table
            if section_data["unused_count"] > 0:
                html += """
                <div class="row mt-3">
                    <div class="col-12">
                        <h6>Unused Objects</h6>
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead>
                                    <tr>
                                        <th>Object Name</th>
                                        <th>Properties</th>
                                    </tr>
                                </thead>
                                <tbody>"""
                
                for obj in section_data["unused_objects"]:
                    html += f"""
                                    <tr class="object-row">
                                        <td>{obj["name"]}</td>
                                        <td>{json.dumps(obj["properties"])}</td>
                                    </tr>"""
                
                html += """
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>"""
        
        elif "duplicate_objects" in section_data:
            # Duplicate objects section
            html += f"""
            <div class="row">
                <div class="col-md-6">
                    <h6>Summary</h6>
                    <div class="summary-item"><strong>Object Type:</strong> {section_data["object_type"]}</div>
                    <div class="summary-item"><strong>Total Objects:</strong> {section_data["total_count"]}</div>
                    <div class="summary-item"><strong>Duplicate Objects:</strong> {section_data["duplicate_object_count"]} ({section_data.get("duplicate_percentage", 0):.1f}%)</div>
                    <div class="summary-item"><strong>Duplicate Sets:</strong> {section_data["duplicate_set_count"]}</div>
                </div>
                <div class="col-md-6">
                    <h6>Duplication Distribution</h6>
                    <div class="chart-container">
                        <canvas id="chart-dup-dist" 
                                data-type="pie" 
                                data-labels='{json.dumps(["Unique", "Duplicate"])}' 
                                data-values='{json.dumps([
                                    section_data["total_count"] - section_data["duplicate_object_count"],
                                    section_data["duplicate_object_count"]
                                ])}'>
                        </canvas>
                    </div>
                </div>
            </div>"""
            
            # Add duplicate objects table
            if section_data["duplicate_set_count"] > 0:
                html += """
                <div class="row mt-3">
                    <div class="col-12">
                        <h6>Duplicate Object Sets</h6>
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead>
                                    <tr>
                                        <th>Value</th>
                                        <th>Objects</th>
                                    </tr>
                                </thead>
                                <tbody>"""
                
                for dupe_set in section_data["duplicate_objects"]:
                    html += f"""
                                    <tr class="object-row">
                                        <td>{dupe_set["value"]}</td>
                                        <td>{", ".join(dupe_set["objects"])}</td>
                                    </tr>"""
                
                html += """
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>"""
        
        elif "filtered_objects" in section_data:
            # Object filter section
            html += f"""
            <div class="row">
                <div class="col-12">
                    <h6>Filter Summary</h6>
                    <div class="summary-item"><strong>Object Type:</strong> {section_data["object_type"]}</div>
                    <div class="summary-item"><strong>Filter Criteria:</strong> {json.dumps(section_data["criteria"])}</div>
                    <div class="summary-item"><strong>Matching Objects:</strong> {section_data["filtered_count"]} of {section_data["total_count"]} ({section_data.get("filtered_percentage", 0):.1f}%)</div>
                </div>
            </div>"""
            
            # Add filtered objects table
            if section_data["filtered_count"] > 0:
                html += """
                <div class="row mt-3">
                    <div class="col-12">
                        <h6>Matching Objects</h6>
                        <div class="table-responsive">
                            <table class="table table-striped table-hover">
                                <thead>
                                    <tr>
                                        <th>Object Name</th>
                                        <th>Details</th>
                                    </tr>
                                </thead>
                                <tbody>"""
                
                for obj in section_data["filtered_objects"]:
                    html += f"""
                                    <tr class="object-row">
                                        <td>{obj["name"]}</td>
                                        <td>{json.dumps(obj.get("data", {}))}</td>
                                    </tr>"""
                
                html += """
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>"""
        
        return html

# Enhanced analysis functions to supplement the existing reports
# def generate_hit_count_analysis_report(
#     tree: etree._ElementTree,
#     hit_count_data: Dict[str, Dict[str, int]],
#     device_type