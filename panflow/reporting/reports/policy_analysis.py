"""
Security policy analysis report generator.

This module provides functionality for generating comprehensive analysis of
security policies in PAN-OS configurations.
"""

import datetime
import logging
from typing import Dict, Any, Optional, List, Union, Tuple, Set
from lxml import etree
from collections import Counter, defaultdict

from ...modules.policies import get_policies
from ...core.logging_utils import logger, log, log_structured


def generate_security_policy_analysis_data(
    tree: etree._ElementTree,
    device_type: str,
    context_type: str,
    version: str,
    policy_type: Optional[str] = None,
    include_hit_counts: bool = False,
    hit_count_data: Optional[Dict[str, Dict[str, int]]] = None,
    include_visualization: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """
    Generate raw data for comprehensive analysis of security policies.

    Args:
        tree: ElementTree containing the configuration
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        policy_type: Type of security policy to analyze (if None, determine based on device type)
        include_hit_counts: Whether to include hit count analysis
        hit_count_data: Dictionary of hit count data (if available)
        include_visualization: Whether to include visualization data
        **kwargs: Additional parameters (device_group, vsys)

    Returns:
        Dict: Report data
    """
    log_structured(
        "Generating security policy analysis",
        "info",
        device_type=device_type,
        context_type=context_type,
        include_hit_counts=include_hit_counts,
    )

    # Determine policy type if not specified
    if policy_type is None:
        if device_type.lower() == "panorama":
            policy_type = "security_pre_rules"
        else:
            policy_type = "security_rules"
        log("Using default policy type", "debug", {"policy_type": policy_type})

    # Get all policies of the specified type
    policies = get_policies(tree, policy_type, device_type, context_type, version, **kwargs)

    if not policies:
        log(f"No {policy_type} policies found", "warning")
        return {"error": f"No {policy_type} policies found"}

    log_structured(
        f"Analyzing policies", "info", policy_type=policy_type, policy_count=len(policies)
    )

    # Prepare analysis structure
    analysis = {
        "summary": {
            "total_policies": len(policies),
            "device_type": device_type,
            "context_type": context_type,
            "policy_type": policy_type,
            "generation_time": datetime.datetime.now().isoformat(),
            "version": version,
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
            "without_log_forwarding": [],
        },
        "statistics": {
            "actions": Counter(),
            "zones": {"source": Counter(), "destination": Counter()},
            "address_objects": {"source": Counter(), "destination": Counter()},
            "service_objects": Counter(),
            "application_objects": Counter(),
            "profile_groups": Counter(),
            "log_settings": Counter(),
        },
    }

    # Add hit count category if requested
    if include_hit_counts and hit_count_data:
        analysis["categories"]["by_hit_count"] = {"zero": [], "low": [], "medium": [], "high": []}
        analysis["statistics"]["hit_counts"] = {
            "min": 0,
            "max": 0,
            "avg": 0,
            "median": 0,
            "total": 0,
            "distribution": {},
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
            "zones": {"source": policy.get("from", []), "destination": policy.get("to", [])},
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
            count_range = str(_get_hit_count_range(hit_count))
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
    analysis["summary"]["with_profile_group_count"] = len(
        analysis["categories"]["with_profile_group"]
    )
    analysis["summary"]["without_profile_group_count"] = len(
        analysis["categories"]["without_profile_group"]
    )
    analysis["summary"]["with_log_forwarding_count"] = len(
        analysis["categories"]["with_log_forwarding"]
    )
    analysis["summary"]["without_log_forwarding_count"] = len(
        analysis["categories"]["without_log_forwarding"]
    )

    # Calculate hit count statistics if available
    if include_hit_counts and hit_count_data:
        hit_counts = [
            hit_count_data[name]["hit_count"] for name in policies if name in hit_count_data
        ]
        if hit_counts:
            analysis["statistics"]["hit_counts"]["min"] = min(hit_counts)
            analysis["statistics"]["hit_counts"]["max"] = max(hit_counts)
            analysis["statistics"]["hit_counts"]["avg"] = sum(hit_counts) / len(hit_counts)
            analysis["statistics"]["hit_counts"]["total"] = sum(hit_counts)

            # Calculate median
            sorted_counts = sorted(hit_counts)
            mid = len(sorted_counts) // 2
            if len(sorted_counts) % 2 == 0:
                analysis["statistics"]["hit_counts"]["median"] = (
                    sorted_counts[mid - 1] + sorted_counts[mid]
                ) / 2
            else:
                analysis["statistics"]["hit_counts"]["median"] = sorted_counts[mid]

    # Generate rule overlap analysis if requested
    if include_visualization:
        analysis["visualization"] = _generate_policy_visualization(policies)

    return analysis


def _get_hit_count_range(count: int) -> Tuple[int, int]:
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
        return (10000, float("inf"))


def _generate_policy_visualization(policies: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
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
        "overlap_graph": {"nodes": [], "links": []},
    }

    # Build policy matrix for source/destination visualization
    policy_names = list(policies.keys())

    # Add policies as nodes for the overlap graph
    for name in policy_names:
        visualization["overlap_graph"]["nodes"].append(
            {
                "id": name,
                "type": "policy",
                "disabled": policies[name].get("disabled", "no") == "yes",
                "action": policies[name].get("action", "allow"),
            }
        )

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
            overlap = _check_policy_overlap(policy1, policy2)

            if overlap["has_overlap"]:
                row["overlaps"].append(
                    {"policy": name2, "type": overlap["type"], "fields": overlap["fields"]}
                )

                # Add link to overlap graph
                visualization["overlap_graph"]["links"].append(
                    {
                        "source": name1,
                        "target": name2,
                        "type": overlap["type"],
                        "weight": len(overlap["fields"]),
                    }
                )

        visualization["policy_matrix"].append(row)

    return visualization


def _check_policy_overlap(policy1: Dict[str, Any], policy2: Dict[str, Any]) -> Dict[str, Any]:
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
