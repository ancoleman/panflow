"""
Policies module for PANFlow for PAN-OS XML utilities.

This module provides functions for working with PAN-OS policies such as security rules,
NAT rules, and other policy types.
"""

import os
from typing import Dict, Any, Optional, List, Tuple, Union
from lxml import etree
import logging

from ..core.xpath_resolver import get_policy_xpath
from ..core.config_loader import xpath_search, extract_element_data

logger = logging.getLogger("panflow")

def get_policies(
    tree: etree._ElementTree,
    policy_type: str,
    device_type: str,
    context_type: str,
    version: str,
    **kwargs
) -> Dict[str, Dict[str, Any]]:
    """
    Get all policies of a specific type in a specific context.
    
    Args:
        tree: ElementTree containing the configuration
        policy_type: Type of policy (security_pre_rules, nat_rules, etc.)
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)
        
    Returns:
        Dict: Dictionary of policies with name as key
    """
    # Build the XPath to search for
    xpath = get_policy_xpath(policy_type, device_type, context_type, version, **kwargs)
    
    logger.debug(f"Searching for policies with XPath: {xpath}")
    
    # Search for all elements matching the XPath
    elements = xpath_search(tree, xpath)
    # Process the results
    results = {}
    
    # Check if we got results
    if elements:
        # The XPath returns the container element (e.g., <rules>)
        # We need to process its children which are the actual rule entries
        container = elements[0]
        
        # Process each rule entry in the container
        for rule_entry in container:
            name = rule_entry.get("name")
            if name:
                # Extract all data from the rule entry
                data = extract_element_data(rule_entry)
                results[name] = data
    
    # Log details about found policies
    if results:
        logger.info(f"Found {len(results)} {policy_type} policies:")
        for name, policy in results.items():
            policy_info = []
            
            # Get action
            if "action" in policy:
                policy_info.append(f"action: {policy['action']}")
            
            # Get sources
            if "source" in policy and isinstance(policy["source"], list):
                src_count = len(policy["source"])
                src_preview = ", ".join(policy["source"][:3])
                if src_count > 3:
                    src_preview += f"... (+{src_count - 3} more)"
                policy_info.append(f"source: [{src_preview}]")
            
            # Get destinations
            if "destination" in policy and isinstance(policy["destination"], list):
                dst_count = len(policy["destination"])
                dst_preview = ", ".join(policy["destination"][:3])
                if dst_count > 3:
                    dst_preview += f"... (+{dst_count - 3} more)"
                policy_info.append(f"dest: [{dst_preview}]")
            
            # Get services
            if "service" in policy and isinstance(policy["service"], list):
                svc_count = len(policy["service"])
                svc_preview = ", ".join(policy["service"][:2])
                if svc_count > 2:
                    svc_preview += f"... (+{svc_count - 2} more)"
                policy_info.append(f"service: [{svc_preview}]")
            
            # Log policy details
            logger.info(f"  - {name}: {' | '.join(policy_info)}")
    else:
        logger.info(f"No {policy_type} policies found")
    
    return results
def get_policy(
    tree: etree._ElementTree,
    policy_type: str,
    name: str,
    device_type: str,
    context_type: str,
    version: str,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Get a specific policy by name.
    
    Args:
        tree: ElementTree containing the configuration
        policy_type: Type of policy (security_pre_rules, nat_rules, etc.)
        name: Name of the policy
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)
        
    Returns:
        Optional[Dict]: Policy data or None if not found
    """
    # Build the XPath to search for
    xpath = get_policy_xpath(policy_type, device_type, context_type, version, name, **kwargs)
    
    # Search for the element
    elements = xpath_search(tree, xpath)
    
    if not elements:
        logger.warning(f"Policy '{name}' not found")
        return None
    
    # Extract all data from the element
    data = extract_element_data(elements[0])
    
    return data

def add_policy(
    tree: etree._ElementTree,
    policy_type: str,
    name: str,
    properties: Dict[str, Any],
    device_type: str,
    context_type: str,
    version: str,
    **kwargs
) -> bool:
    """
    Add a new policy.
    
    Args:
        tree: ElementTree containing the configuration
        policy_type: Type of policy (security_pre_rules, nat_rules, etc.)
        name: Name of the policy
        properties: Dictionary of policy properties
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)
        
    Returns:
        bool: Success status
    """
    # Get the base XPath for the policy type
    base_xpath = get_policy_xpath(policy_type, device_type, context_type, version, **kwargs)
    parent_xpath = base_xpath.rsplit("/", 1)[0]
    
    # Check if the policy already exists
    existing = get_policy(tree, policy_type, name, device_type, context_type, version, **kwargs)
    
    if existing:
        logger.warning(f"Policy '{name}' already exists")
        return False
    
    # Find the parent element
    parent_elements = xpath_search(tree, parent_xpath)
    if not parent_elements:
        logger.error(f"Parent element not found for path: {parent_xpath}")
        return False
    
    # Create the new policy element
    new_policy = etree.SubElement(parent_elements[0], "entry", {"name": name})
    
    # Add properties to the policy
    add_properties_to_element(new_policy, properties)
    
    logger.info(f"Added {policy_type} policy '{name}'")
    return True

def update_policy(
    tree: etree._ElementTree,
    policy_type: str,
    name: str,
    properties: Dict[str, Any],
    device_type: str,
    context_type: str,
    version: str,
    **kwargs
) -> bool:
    """
    Update an existing policy.
    
    Args:
        tree: ElementTree containing the configuration
        policy_type: Type of policy (security_pre_rules, nat_rules, etc.)
        name: Name of the policy
        properties: Dictionary of policy properties to update
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)
        
    Returns:
        bool: Success status
    """
    # Get the XPath for the policy
    xpath = get_policy_xpath(
        policy_type, device_type, context_type, version, name, **kwargs
    )
    
    # Find the policy element
    elements = xpath_search(tree, xpath)
    if not elements:
        logger.error(f"Policy '{name}' not found")
        return False
    
    # Update the policy properties
    policy_element = elements[0]
    for key, value in properties.items():
        # Remove existing element with this tag
        for child in policy_element.xpath(f"./{key}"):
            policy_element.remove(child)
        
        # Add new element
        if isinstance(value, dict):
            # Nested element
            child = etree.SubElement(policy_element, key)
            add_properties_to_element(child, value)
        elif isinstance(value, list):
            # List element (typically members)
            child = etree.SubElement(policy_element, key)
            for item in value:
                member = etree.SubElement(child, "member")
                member.text = item
        else:
            # Simple element
            child = etree.SubElement(policy_element, key)
            child.text = str(value)
    
    logger.info(f"Updated {policy_type} policy '{name}'")
    return True

def delete_policy(
    tree: etree._ElementTree,
    policy_type: str,
    name: str,
    device_type: str,
    context_type: str,
    version: str,
    **kwargs
) -> bool:
    """
    Delete a policy.
    
    Args:
        tree: ElementTree containing the configuration
        policy_type: Type of policy (security_pre_rules, nat_rules, etc.)
        name: Name of the policy
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)
        
    Returns:
        bool: Success status
    """
    # Get the XPath for the policy
    xpath = get_policy_xpath(
        policy_type, device_type, context_type, version, name, **kwargs
    )
    parent_xpath = xpath.rsplit("/", 1)[0]
    
    # Find the parent element
    parent_elements = xpath_search(tree, parent_xpath)
    if not parent_elements:
        logger.error(f"Parent element not found for policy '{name}'")
        return False
    
    # Find the policy element
    for child in parent_elements[0]:
        if child.tag == "entry" and child.get("name") == name:
            parent_elements[0].remove(child)
            logger.info(f"Deleted {policy_type} policy '{name}'")
            return True
    
    logger.error(f"Policy '{name}' not found")
    return False

def filter_policies(
    tree: etree._ElementTree,
    policy_type: str,
    filter_criteria: Dict[str, Any],
    device_type: str,
    context_type: str,
    version: str,
    **kwargs
) -> Dict[str, Dict[str, Any]]:
    """
    Filter policies based on criteria.
    
    Args:
        tree: ElementTree containing the configuration
        policy_type: Type of policy (security_pre_rules, nat_rules, etc.)
        filter_criteria: Dictionary of criteria to filter policies
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)
        
    Returns:
        Dict: Dictionary of filtered policies with name as key
    """
    # Get all policies of this type
    all_policies = get_policies(
        tree, policy_type, device_type, context_type, version, **kwargs
    )
    
    # Filter policies based on criteria
    filtered_policies = {}
    
    for name, policy in all_policies.items():
        matches_all = True
        
        for key, value in filter_criteria.items():
            if key not in policy:
                matches_all = False
                break
            
            # If it's a list type field, check if any element matches
            if isinstance(policy[key], list) and isinstance(value, list):
                if not any(v in policy[key] for v in value):
                    matches_all = False
                    break
            # If it's a list type field but filter is a string, check if it's in the list
            elif isinstance(policy[key], list) and not isinstance(value, list):
                if value not in policy[key]:
                    matches_all = False
                    break
            # If it's a dictionary, check if it contains the filter values
            elif isinstance(policy[key], dict) and isinstance(value, dict):
                for subkey, subvalue in value.items():
                    if subkey not in policy[key] or policy[key][subkey] != subvalue:
                        matches_all = False
                        break
            # For everything else, check equality
            elif policy[key] != value:
                matches_all = False
                break
        
        if matches_all:
            filtered_policies[name] = policy
    
    logger.info(f"Filtered {len(all_policies)} policies down to {len(filtered_policies)} matching policies")
    return filtered_policies

def get_policy_position(
    tree: etree._ElementTree,
    policy_type: str,
    name: str,
    device_type: str,
    context_type: str,
    version: str,
    **kwargs
) -> Optional[int]:
    """
    Get the position of a policy in the rulebase.
    
    Args:
        tree: ElementTree containing the configuration
        policy_type: Type of policy (security_pre_rules, nat_rules, etc.)
        name: Name of the policy
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)
        
    Returns:
        Optional[int]: Position index (0-based) or None if not found
    """
    # Get the base XPath for the policies
    base_xpath = get_policy_xpath(policy_type, device_type, context_type, version, **kwargs)
    parent_xpath = base_xpath.rsplit("/", 1)[0]
    
    # Find all policies
    elements = xpath_search(tree, f"{parent_xpath}/entry")
    
    # Find the policy position
    for i, element in enumerate(elements):
        if element.get("name") == name:
            logger.debug(f"Policy '{name}' found at position {i}")
            return i
    
    logger.warning(f"Policy '{name}' not found")
    return None

def move_policy(
    tree: etree._ElementTree,
    policy_type: str,
    name: str,
    where: str,
    ref_name: Optional[str] = None,
    device_type: str = "firewall",
    context_type: str = "shared",
    version: str = "11.2",
    **kwargs
) -> bool:
    """
    Move a policy to a new position in the rulebase.
    
    Args:
        tree: ElementTree containing the configuration
        policy_type: Type of policy (security_pre_rules, nat_rules, etc.)
        name: Name of the policy to move
        where: Where to move ("top", "bottom", "before", "after")
        ref_name: Reference policy name (required for "before" and "after")
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)
        
    Returns:
        bool: Success status
    """
    # Get the base XPath for the policies
    base_xpath = get_policy_xpath(policy_type, device_type, context_type, version, **kwargs)
    parent_xpath = base_xpath.rsplit("/", 1)[0]
    
    # Find the parent element
    parent_elements = xpath_search(tree, parent_xpath)
    if not parent_elements:
        logger.error(f"Parent element not found for path: {parent_xpath}")
        return False
    
    parent = parent_elements[0]
    
    # Find the policy to move
    policy_elem = None
    for child in parent:
        if child.tag == "entry" and child.get("name") == name:
            policy_elem = child
            break
    
    if policy_elem is None:
        logger.error(f"Policy '{name}' not found")
        return False
    
    # Remove the policy from its current position
    parent.remove(policy_elem)
    
    # Move to the new position
    if where == "top":
        # Insert at the beginning
        if len(parent) > 0:
            parent.insert(0, policy_elem)
        else:
            parent.append(policy_elem)
        logger.info(f"Moved policy '{name}' to the top")
        return True
    
    elif where == "bottom":
        # Append at the end
        parent.append(policy_elem)
        logger.info(f"Moved policy '{name}' to the bottom")
        return True
    
    elif where in ("before", "after"):
        if not ref_name:
            logger.error(f"Reference policy name is required for '{where}' operation")
            return False
        
        # Find the reference policy
        ref_index = None
        for i, child in enumerate(parent):
            if child.tag == "entry" and child.get("name") == ref_name:
                ref_index = i
                break
        
        if ref_index is None:
            logger.error(f"Reference policy '{ref_name}' not found")
            # Re-add the policy at its original position (approximation)
            parent.append(policy_elem)
            return False
        
        # Insert before or after the reference policy
        if where == "before":
            parent.insert(ref_index, policy_elem)
            logger.info(f"Moved policy '{name}' before '{ref_name}'")
        else:  # after
            parent.insert(ref_index + 1, policy_elem)
            logger.info(f"Moved policy '{name}' after '{ref_name}'")
        
        return True
    
    else:
        logger.error(f"Invalid move operation: {where}")
        # Re-add the policy at its original position (approximation)
        parent.append(policy_elem)
        return False

def clone_policy(
    tree: etree._ElementTree,
    policy_type: str,
    name: str,
    new_name: str,
    device_type: str,
    context_type: str,
    version: str,
    **kwargs
) -> bool:
    """
    Clone a policy with a new name.
    
    Args:
        tree: ElementTree containing the configuration
        policy_type: Type of policy (security_pre_rules, nat_rules, etc.)
        name: Name of the policy to clone
        new_name: Name for the cloned policy
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)
        
    Returns:
        bool: Success status
    """
    # Get the policy to clone
    policy_data = get_policy(tree, policy_type, name, device_type, context_type, version, **kwargs)
    
    if not policy_data:
        logger.error(f"Policy '{name}' not found")
        return False
    
    # Check if the new policy already exists
    existing = get_policy(tree, policy_type, new_name, device_type, context_type, version, **kwargs)
    
    if existing:
        logger.warning(f"Policy '{new_name}' already exists")
        return False
    
    # Add the new policy with the same properties
    if add_policy(tree, policy_type, new_name, policy_data, device_type, context_type, version, **kwargs):
        logger.info(f"Cloned policy '{name}' to '{new_name}'")
        return True
    else:
        logger.error(f"Failed to clone policy '{name}'")
        return False

def add_properties_to_element(element: etree._Element, properties: Dict[str, Any]) -> None:
    """
    Add properties to an XML element.
    
    Args:
        element: XML element
        properties: Dictionary of properties to add
    """
    for key, value in properties.items():
        if isinstance(value, dict):
            # Nested element
            child = etree.SubElement(element, key)
            add_properties_to_element(child, value)
        elif isinstance(value, list):
            # List element (typically members)
            child = etree.SubElement(element, key)
            for item in value:
                member = etree.SubElement(child, "member")
                member.text = str(item)
        else:
            # Simple element
            child = etree.SubElement(element, key)
            child.text = str(value)