"""
Reports module for PANFlow for PAN-OS XML utilities.

This module provides functions for generating reports on PAN-OS configurations,
such as unused objects, duplicate objects, security rule coverage, etc.
"""

import os
import json
from typing import Dict, Any, Optional, List, Tuple, Union
from lxml import etree
import logging

from ..core.config_loader import xpath_search, extract_element_data
from ..modules.objects import get_objects
from ..modules.policies import get_policies

logger = logging.getLogger("panflow")

def generate_unused_objects_report(
    tree: etree._ElementTree,
    device_type: str,
    context_type: str,
    version: str,
    output_file: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate report of unused objects.
    
    Args:
        tree: ElementTree containing the configuration
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        output_file: Output file for report (optional)
        **kwargs: Additional parameters (device_group, vsys)
        
    Returns:
        Dict: Report data
    """
    report_data = {"unused_objects": []}
    
    # Get address objects
    addr_objects = get_objects(tree, "address", device_type, context_type, version, **kwargs)
    
    # Get security rules to check for usage
    if device_type.lower() == "panorama":
        security_pre_rules = get_policies(tree, "security_pre_rules", device_type, context_type, version, **kwargs)
        security_post_rules = get_policies(tree, "security_post_rules", device_type, context_type, version, **kwargs)
        all_rules = {**security_pre_rules, **security_post_rules}
    else:  # firewall
        all_rules = get_policies(tree, "security_rules", device_type, context_type, version, **kwargs)
    
    # Also check address groups for usage
    addr_groups = get_objects(tree, "address_group", device_type, context_type, version, **kwargs)
    
    # Track used objects
    used_objects = set()
    
    # Check each rule for object usage
    for rule_name, rule in all_rules.items():
        # Check source and destination fields
        for field in ['source', 'destination']:
            if field in rule and isinstance(rule[field], list):
                for obj in rule[field]:
                    used_objects.add(obj)
    
    # Check each address group for object usage
    for group_name, group in addr_groups.items():
        if "static" in group and isinstance(group["static"], list):
            for obj in group["static"]:
                used_objects.add(obj)
    
    # Find unused objects
    unused_objects = []
    for obj_name in addr_objects:
        if obj_name not in used_objects:
            unused_objects.append({
                "name": obj_name,
                "properties": addr_objects[obj_name]
            })
    
    report_data['unused_objects'] = unused_objects
    logger.info(f"Found {len(unused_objects)} unused address objects out of {len(addr_objects)} total")
    
    # Save report to file if specified
    if output_file and report_data:
        try:
            with open(output_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            logger.info(f"Report saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving report: {e}")
    
    return report_data

def generate_duplicate_objects_report(
    tree: etree._ElementTree,
    device_type: str,
    context_type: str,
    version: str,
    output_file: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate report of duplicate objects.
    
    Args:
        tree: ElementTree containing the configuration
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        output_file: Output file for report (optional)
        **kwargs: Additional parameters (device_group, vsys)
        
    Returns:
        Dict: Report data
    """
    report_data = {"duplicate_objects": {}}
    
    # Get address objects
    addr_objects = get_objects(tree, "address", device_type, context_type, version, **kwargs)
    
    # Group by value
    objects_by_value = {}
    
    for name, obj in addr_objects.items():
        # Create a value key based on the object type and value
        if "ip-netmask" in obj:
            value_key = f"ip-netmask:{obj['ip-netmask']}"
        elif "ip-range" in obj:
            value_key = f"ip-range:{obj['ip-range']}"
        elif "fqdn" in obj:
            value_key = f"fqdn:{obj['fqdn']}"
        else:
            # Unknown type, use name as key
            value_key = f"unknown:{name}"
        
        if value_key not in objects_by_value:
            objects_by_value[value_key] = []
        
        objects_by_value[value_key].append(name)
    
    # Find duplicates (more than one object with the same value)
    duplicates = {}
    for value_key, names in objects_by_value.items():
        if len(names) > 1:
            duplicates[value_key] = names
    
    report_data['duplicate_objects'] = duplicates
    total_duplicates = sum(len(names) - 1 for names in duplicates.values())
    logger.info(f"Found {len(duplicates)} unique values with duplicates ({total_duplicates} duplicate objects)")
    
    # Save report to file if specified
    if output_file and report_data:
        try:
            with open(output_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            logger.info(f"Report saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving report: {e}")
    
    return report_data

def generate_security_rule_coverage_report(
    tree: etree._ElementTree,
    device_type: str,
    context_type: str,
    version: str,
    output_file: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate report of security rule coverage.
    
    Args:
        tree: ElementTree containing the configuration
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        output_file: Output file for report (optional)
        **kwargs: Additional parameters (device_group, vsys)
        
    Returns:
        Dict: Report data
    """
    report_data = {}
    
    # Get security rules
    if device_type.lower() == "panorama":
        security_pre_rules = get_policies(tree, "security_pre_rules", device_type, context_type, version, **kwargs)
        security_post_rules = get_policies(tree, "security_post_rules", device_type, context_type, version, **kwargs)
        all_rules = {**security_pre_rules, **security_post_rules}
    else:  # firewall
        all_rules = get_policies(tree, "security_rules", device_type, context_type, version, **kwargs)
    
    # Analyze rules
    analysis = {
        'total_rules': len(all_rules),
        'disabled_rules': [],
        'any_any_rules': [],
        'potential_shadowing': []
    }
    
    # Check each rule
    for rule_name, rule in all_rules.items():
        # Check if disabled
        if "disabled" in rule and rule["disabled"] == "yes":
            analysis['disabled_rules'].append(rule_name)
        
        # Check for "any any" rules (source and destination both "any")
        is_any_source = "source" in rule and isinstance(rule["source"], list) and "any" in rule["source"]
        is_any_dest = "destination" in rule and isinstance(rule["destination"], list) and "any" in rule["destination"]
        
        if is_any_source and is_any_dest:
            analysis['any_any_rules'].append({
                'name': rule_name,
                'action': rule.get("action", ""),
                'disabled': "disabled" in rule and rule["disabled"] == "yes"
            })
    
    # Basic shadowing detection (very simplified)
    # This is just a demonstration - real shadowing detection would need more complex logic
    # Group rules by source/destination/service for simplicity
    rule_patterns = {}
    for rule_name, rule in all_rules.items():
        # Skip disabled rules
        if "disabled" in rule and rule["disabled"] == "yes":
            continue
        
        src = tuple(sorted(rule.get("source", [])))
        dst = tuple(sorted(rule.get("destination", [])))
        svc = tuple(sorted(rule.get("service", [])))
        
        pattern = (src, dst, svc)
        
        if pattern in rule_patterns:
            # Check if actions differ
            existing_rule = rule_patterns[pattern]
            if rule.get("action", "") != existing_rule["action"]:
                analysis['potential_shadowing'].append({
                    'pattern': {
                        'source': list(src),
                        'destination': list(dst),
                        'service': list(svc)
                    },
                    'rules': [
                        {
                            'name': existing_rule["name"],
                            'action': existing_rule["action"]
                        },
                        {
                            'name': rule_name,
                            'action': rule.get("action", "")
                        }
                    ]
                })
        else:
            rule_patterns[pattern] = {
                'name': rule_name,
                'action': rule.get("action", "")
            }
    
    report_data['security_rule_analysis'] = analysis
    logger.info(f"Security Rule Analysis: {len(all_rules)} total rules, "
                   f"{len(analysis['disabled_rules'])} disabled, "
                   f"{len(analysis['any_any_rules'])} any-any rules, "
                   f"{len(analysis['potential_shadowing'])} potential shadowing cases")
    
    # Save report to file if specified
    if output_file and report_data:
        try:
            with open(output_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            logger.info(f"Report saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving report: {e}")
    
    return report_data

def generate_reference_check_report(
    tree: etree._ElementTree,
    object_name: str,
    object_type: str,
    device_type: str,
    context_type: str,
    version: str,
    output_file: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate report of references to an object.
    
    Args:
        tree: ElementTree containing the configuration
        object_name: Name of the object to check
        object_type: Type of object (address, service, etc.)
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        output_file: Output file for report (optional)
        **kwargs: Additional parameters (device_group, vsys)
        
    Returns:
        Dict: Report data
    """
    references = {
        "object_name": object_name,
        "object_type": object_type,
        "references": {
            "groups": {},
            "policies": {}
        }
    }
    
    # Check for references in groups
    group_types = {
        "address": "address_group",
        "service": "service_group",
        "application": "application_group"
    }
    
    if object_type in group_types:
        group_type = group_types[object_type]
        
        # Get all groups of this type
        groups = get_objects(tree, group_type, device_type, context_type, version, **kwargs)
        
        # Check each group for references
        for group_name, group_data in groups.items():
            if "static" in group_data and isinstance(group_data["static"], list) and object_name in group_data["static"]:
                if group_type not in references["references"]["groups"]:
                    references["references"]["groups"][group_type] = []
                references["references"]["groups"][group_type].append(group_name)
    
    # Check for references in policies
    # Determine policy types to check based on device type
    if device_type.lower() == "panorama":
        policy_types = [
            "security_pre_rules", "security_post_rules", "nat_pre_rules", 
            "nat_post_rules", "decryption_pre_rules", "decryption_post_rules", 
            "authentication_pre_rules", "authentication_post_rules"
        ]
    else:  # firewall
        policy_types = [
            "security_rules", "nat_rules", "decryption_rules", "authentication_rules"
        ]
    
    # Map object types to policy fields that might reference them
    field_mapping = {
        "address": ["source", "destination", "source-translation", "destination-translation"],
        "address_group": ["source", "destination", "source-translation", "destination-translation"],
        "service": ["service"],
        "service_group": ["service"],
        "application": ["application"],
        "application_group": ["application"],
        "security_profile_group": ["profile-setting", "group"],
        "antivirus_profile": ["virus", "profile-setting"],
        "antispyware_profile": ["spyware", "profile-setting"],
        "vulnerability_profile": ["vulnerability", "profile-setting"],
        "url_filtering_profile": ["url-filtering", "profile-setting"],
        "dns_security_profile": ["dns-security", "profile-setting"],
        "wildfire_profile": ["wildfire-analysis", "profile-setting"],
        "log_forwarding_profile": ["log-setting"]
    }
    
    # Get fields to check based on object type
    fields_to_check = field_mapping.get(object_type, [])
    
    # Check each policy type
    for policy_type in policy_types:
        # Get all policies of this type
        policies = get_policies(tree, policy_type, device_type, context_type, version, **kwargs)
        
        # Check each policy for references
        for policy_name, policy_data in policies.items():
            for field in fields_to_check:
                if field in policy_data and isinstance(policy_data[field], list) and object_name in policy_data[field]:
                    if policy_type not in references["references"]["policies"]:
                        references["references"]["policies"][policy_type] = []
                    # Add policy and field where reference was found
                    references["references"]["policies"][policy_type].append({
                        "name": policy_name,
                        "field": field
                    })
                # Check nested fields (e.g., profile-setting -> group)
                elif field in policy_data and isinstance(policy_data[field], dict):
                    # Check all nested fields
                    for nested_field, nested_value in policy_data[field].items():
                        if isinstance(nested_value, list) and object_name in nested_value:
                            if policy_type not in references["references"]["policies"]:
                                references["references"]["policies"][policy_type] = []
                            # Add policy and field where reference was found
                            references["references"]["policies"][policy_type].append({
                                "name": policy_name,
                                "field": f"{field}.{nested_field}"
                            })
    
    # Summarize results
    total_group_refs = sum(len(groups) for groups in references["references"]["groups"].values())
    total_policy_refs = sum(len(policies) for policies in references["references"]["policies"].values())
    
    logger.info(f"Found {total_group_refs} group references and {total_policy_refs} policy references to {object_type} '{object_name}'")
    
    # Save report to file if specified
    if output_file:
        try:
            with open(output_file, 'w') as f:
                json.dump(references, f, indent=2)
            logger.info(f"Report saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving report: {e}")
    
    return references

def generate_rule_hit_count_report(
    tree: etree._ElementTree,
    hit_count_data: Dict[str, Dict[str, int]],
    device_type: str,
    context_type: str,
    version: str,
    output_file: Optional[str] = None,
    days: int = 30,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate report of security rule hit counts.
    
    Args:
        tree: ElementTree containing the configuration
        hit_count_data: Dictionary mapping rule names to hit counts (from API)
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        output_file: Output file for report (optional)
        days: Number of days to consider
        **kwargs: Additional parameters (device_group, vsys)
        
    Returns:
        Dict: Report data
    """
    report_data = {
        "hit_count_summary": {
            "days": days,
            "zero_hit_rules": [],
            "low_hit_rules": [],
            "high_hit_rules": []
        }
    }
    
    # Get security rules
    if device_type.lower() == "panorama":
        security_pre_rules = get_policies(tree, "security_pre_rules", device_type, context_type, version, **kwargs)
        security_post_rules = get_policies(tree, "security_post_rules", device_type, context_type, version, **kwargs)
        all_rules = {**security_pre_rules, **security_post_rules}
    else:  # firewall
        all_rules = get_policies(tree, "security_rules", device_type, context_type, version, **kwargs)
    
    # Analyze hit counts
    for rule_name, rule in all_rules.items():
        # Skip disabled rules
        if "disabled" in rule and rule["disabled"] == "yes":
            continue
        
        # Get hit count for the rule
        hit_count = hit_count_data.get(rule_name, {}).get("hit_count", 0)
        
        # Categorize based on hit count
        if hit_count == 0:
            report_data["hit_count_summary"]["zero_hit_rules"].append({
                "name": rule_name,
                "hit_count": hit_count
            })
        elif hit_count < 10:  # Threshold for low hit count
            report_data["hit_count_summary"]["low_hit_rules"].append({
                "name": rule_name,
                "hit_count": hit_count
            })
        elif hit_count > 1000:  # Threshold for high hit count
            report_data["hit_count_summary"]["high_hit_rules"].append({
                "name": rule_name,
                "hit_count": hit_count
            })
    
    # Sort by hit count
    report_data["hit_count_summary"]["low_hit_rules"].sort(key=lambda x: x["hit_count"])
    report_data["hit_count_summary"]["high_hit_rules"].sort(key=lambda x: x["hit_count"], reverse=True)
    
    logger.info(f"Hit Count Analysis: {len(report_data['hit_count_summary']['zero_hit_rules'])} rules with zero hits, "
                   f"{len(report_data['hit_count_summary']['low_hit_rules'])} rules with low hits, "
                   f"{len(report_data['hit_count_summary']['high_hit_rules'])} rules with high hits")
    
    # Save report to file if specified
    if output_file:
        try:
            with open(output_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            logger.info(f"Report saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving report: {e}")
    
    return report_data