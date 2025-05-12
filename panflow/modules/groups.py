"""
Groups module for PANFlow for PAN-OS XML utilities.

This module provides functions for working with PAN-OS groups such as address groups,
service groups, and other group types.
"""

import os
from typing import Dict, Any, Optional, List, Tuple, Union
from lxml import etree
import logging

from ..core.xpath_resolver import get_object_xpath
from ..core.config_loader import xpath_search

logger = logging.getLogger("panflow")


def add_member_to_group(
    tree: etree._ElementTree,
    group_type: str,
    group_name: str,
    member_name: str,
    device_type: str,
    context_type: str,
    version: str,
    **kwargs,
) -> bool:
    """
    Add a member to a group.

    Args:
        tree: ElementTree containing the configuration
        group_type: Type of group (address_group, service_group, etc.)
        group_name: Name of the group
        member_name: Name of the member to add
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)

    Returns:
        bool: Success status
    """
    # Get the XPath for the group
    xpath = get_object_xpath(group_type, device_type, context_type, version, group_name, **kwargs)

    # Find the group element
    elements = xpath_search(tree, xpath)
    if not elements:
        logger.error(f"Group '{group_name}' not found")
        return False

    group_element = elements[0]

    # Check if it's a static or dynamic group
    static_element = group_element.find("./static")
    if static_element is not None:
        # Static group
        # Check if member already exists
        for member in static_element.xpath("./member"):
            if member.text == member_name:
                logger.warning(f"Member '{member_name}' already exists in group '{group_name}'")
                return False

        # Add new member
        member_element = etree.SubElement(static_element, "member")
        member_element.text = member_name
        logger.info(f"Added member '{member_name}' to static group '{group_name}'")
        return True
    else:
        # Not a static group, try to create it
        static_element = etree.SubElement(group_element, "static")
        member_element = etree.SubElement(static_element, "member")
        member_element.text = member_name
        logger.info(f"Created static group '{group_name}' with member '{member_name}'")
        return True


def remove_member_from_group(
    tree: etree._ElementTree,
    group_type: str,
    group_name: str,
    member_name: str,
    device_type: str,
    context_type: str,
    version: str,
    **kwargs,
) -> bool:
    """
    Remove a member from a group.

    Args:
        tree: ElementTree containing the configuration
        group_type: Type of group (address_group, service_group, etc.)
        group_name: Name of the group
        member_name: Name of the member to remove
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)

    Returns:
        bool: Success status
    """
    # Get the XPath for the group
    xpath = get_object_xpath(group_type, device_type, context_type, version, group_name, **kwargs)

    # Find the group element
    elements = xpath_search(tree, xpath)
    if not elements:
        logger.error(f"Group '{group_name}' not found")
        return False

    group_element = elements[0]

    # Check if it's a static group
    static_element = group_element.find("./static")
    if static_element is not None:
        # Static group
        # Find and remove the member
        for member in static_element.xpath("./member"):
            if member.text == member_name:
                static_element.remove(member)
                logger.info(f"Removed member '{member_name}' from static group '{group_name}'")
                return True

        logger.warning(f"Member '{member_name}' not found in group '{group_name}'")
        return False
    else:
        # Not a static group
        logger.error(f"Group '{group_name}' is not a static group")
        return False


def add_members_to_group(
    tree: etree._ElementTree,
    group_type: str,
    group_name: str,
    member_names: List[str],
    device_type: str,
    context_type: str,
    version: str,
    **kwargs,
) -> Tuple[int, int]:
    """
    Add multiple members to a group.

    Args:
        tree: ElementTree containing the configuration
        group_type: Type of group (address_group, service_group, etc.)
        group_name: Name of the group
        member_names: List of member names to add
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)

    Returns:
        Tuple[int, int]: (number of members added, total number of members attempted)
    """
    added_count = 0

    for member_name in member_names:
        if add_member_to_group(
            tree, group_type, group_name, member_name, device_type, context_type, version, **kwargs
        ):
            added_count += 1
            logger.debug(f"Added member '{member_name}' to {group_type} '{group_name}'")

    logger.info(
        f"Added {added_count} of {len(member_names)} members to {group_type} '{group_name}'"
    )
    return added_count, len(member_names)


def create_group(
    tree: etree._ElementTree,
    group_type: str,
    group_name: str,
    members: Optional[List[str]] = None,
    dynamic_filter: Optional[str] = None,
    device_type: str = "firewall",
    context_type: str = "shared",
    version: str = "11.2",
    **kwargs,
) -> bool:
    """
    Create a new group (static or dynamic).

    Args:
        tree: ElementTree containing the configuration
        group_type: Type of group (address_group, service_group, etc.)
        group_name: Name of the group
        members: List of member names for static groups (optional)
        dynamic_filter: Filter expression for dynamic groups (optional)
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)

    Returns:
        bool: Success status
    """
    # Get the base XPath for the group type
    base_xpath = get_object_xpath(group_type, device_type, context_type, version, **kwargs)
    parent_xpath = base_xpath.rsplit("/", 1)[0]

    # Check if the group already exists
    xpath = get_object_xpath(group_type, device_type, context_type, version, group_name, **kwargs)
    existing_elements = xpath_search(tree, xpath)

    if existing_elements:
        logger.warning(f"Group '{group_name}' already exists")
        return False

    # Find the parent element
    parent_elements = xpath_search(tree, parent_xpath)
    if not parent_elements:
        logger.error(f"Parent element not found for path: {parent_xpath}")
        return False

    # Create the new group element
    group_element = etree.SubElement(parent_elements[0], "entry", {"name": group_name})

    if members is not None:
        # Static group
        static_element = etree.SubElement(group_element, "static")
        for member_name in members:
            member_element = etree.SubElement(static_element, "member")
            member_element.text = member_name
        logger.info(f"Created static {group_type} '{group_name}' with {len(members)} members")
    elif dynamic_filter is not None:
        # Dynamic group
        dynamic_element = etree.SubElement(group_element, "dynamic")
        filter_element = etree.SubElement(dynamic_element, "filter")
        filter_element.text = dynamic_filter
        logger.info(f"Created dynamic {group_type} '{group_name}' with filter: {dynamic_filter}")
    else:
        # Empty static group
        static_element = etree.SubElement(group_element, "static")
        logger.info(f"Created empty static {group_type} '{group_name}'")

    return True


def get_group_members(
    tree: etree._ElementTree,
    group_type: str,
    group_name: str,
    device_type: str,
    context_type: str,
    version: str,
    **kwargs,
) -> Optional[List[str]]:
    """
    Get the members of a group.

    Args:
        tree: ElementTree containing the configuration
        group_type: Type of group (address_group, service_group, etc.)
        group_name: Name of the group
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)

    Returns:
        Optional[List[str]]: List of member names or None if not found or not a static group
    """
    # Get the XPath for the group
    xpath = get_object_xpath(group_type, device_type, context_type, version, group_name, **kwargs)

    # Find the group element
    elements = xpath_search(tree, xpath)
    if not elements:
        logger.error(f"Group '{group_name}' not found")
        return None

    group_element = elements[0]

    # Check if it's a static group
    static_element = group_element.find("./static")
    if static_element is not None:
        # Static group - get members
        members = []
        for member in static_element.xpath("./member"):
            if member.text:
                members.append(member.text)

        logger.info(f"Found {len(members)} members in {group_type} '{group_name}'")
        return members
    else:
        # Not a static group
        logger.warning(f"Group '{group_name}' is not a static group")
        return None


def get_group_filter(
    tree: etree._ElementTree,
    group_type: str,
    group_name: str,
    device_type: str,
    context_type: str,
    version: str,
    **kwargs,
) -> Optional[str]:
    """
    Get the filter of a dynamic group.

    Args:
        tree: ElementTree containing the configuration
        group_type: Type of group (address_group, service_group, etc.)
        group_name: Name of the group
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)

    Returns:
        Optional[str]: Filter expression or None if not found or not a dynamic group
    """
    # Get the XPath for the group
    xpath = get_object_xpath(group_type, device_type, context_type, version, group_name, **kwargs)

    # Find the group element
    elements = xpath_search(tree, xpath)
    if not elements:
        logger.error(f"Group '{group_name}' not found")
        return None

    group_element = elements[0]

    # Check if it's a dynamic group
    dynamic_element = group_element.find("./dynamic")
    if dynamic_element is not None:
        # Dynamic group - get filter
        filter_element = dynamic_element.find("./filter")
        if filter_element is not None and filter_element.text:
            logger.info(f"Found filter for dynamic {group_type} '{group_name}'")
            return filter_element.text

    # Not a dynamic group or no filter
    logger.warning(f"Group '{group_name}' is not a dynamic group or has no filter")
    return None
