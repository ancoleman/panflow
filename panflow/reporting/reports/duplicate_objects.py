"""
Duplicate objects report generator.

This module provides functionality for generating reports on duplicate objects
in PAN-OS configurations.
"""

import logging
from typing import Dict, Any, Optional, List, Union
from lxml import etree

from ...modules.objects import get_objects
from ...core.logging_utils import logger


def generate_duplicate_objects_report_data(
    tree: etree._ElementTree,
    device_type: str,
    context_type: str,
    version: str,
    object_type: str = "address",
    **kwargs,
) -> Dict[str, Any]:
    """
    Generate raw data for a report of duplicate objects.

    Args:
        tree: ElementTree containing the configuration
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        object_type: Type of object to check (address, service, etc.)
        **kwargs: Additional parameters (device_group, vsys)

    Returns:
        Dict: Report data
    """
    report_data = {"duplicate_objects": {}}

    # Get objects of the specified type
    objects = get_objects(tree, object_type, device_type, context_type, version, **kwargs)

    # Group by value
    objects_by_value = {}

    # Handle different object types appropriately
    if object_type == "address":
        for name, obj in objects.items():
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

    elif object_type == "service":
        for name, obj in objects.items():
            # Create a value key based on protocol information
            if "protocol" in obj:
                protocol = obj["protocol"]
                if protocol == "tcp" or protocol == "udp":
                    # TCP/UDP services have port information
                    port_value = ""
                    if "port" in obj:
                        port_value = obj["port"]
                    elif "source-port" in obj and "dest-port" in obj:
                        port_value = f"{obj['source-port']}:{obj['dest-port']}"

                    value_key = f"{protocol}:{port_value}"
                else:
                    # Other protocols like icmp
                    value_key = f"{protocol}"
                    if "type" in obj:
                        value_key += f":{obj['type']}"
                    if "code" in obj:
                        value_key += f":{obj['code']}"
            else:
                # Unknown type, use name as key
                value_key = f"unknown:{name}"

            if value_key not in objects_by_value:
                objects_by_value[value_key] = []

            objects_by_value[value_key].append(name)

    else:
        # For other object types, use a simple string representation
        for name, obj in objects.items():
            # Create a simple string representation of the object properties
            value_str = str(sorted([(k, v) for k, v in obj.items()]))
            value_key = f"{object_type}:{value_str}"

            if value_key not in objects_by_value:
                objects_by_value[value_key] = []

            objects_by_value[value_key].append(name)

    # Find duplicates (more than one object with the same value)
    duplicates = {}
    for value_key, names in objects_by_value.items():
        if len(names) > 1:
            # Include context information for each duplicate object
            objects_with_context = []
            for name in names:
                # Create object data with context information
                obj_data = {
                    "name": name,
                    "context_type": context_type
                }
                
                # Add specific context details based on type
                if context_type == "device_group" and "device_group" in kwargs:
                    obj_data["context_name"] = kwargs["device_group"]
                elif context_type == "vsys" and "vsys" in kwargs:
                    obj_data["context_name"] = kwargs["vsys"]
                elif context_type == "shared":
                    obj_data["context_name"] = "Shared"
                
                objects_with_context.append(obj_data)
            
            duplicates[value_key] = objects_with_context

    report_data["duplicate_objects"] = duplicates
    total_duplicates = sum(len(names) - 1 for names in duplicates.values())
    logger.info(
        f"Found {len(duplicates)} unique values with duplicates ({total_duplicates} duplicate objects)"
    )

    return report_data
