"""
Unused objects report generator.

This module provides functionality for generating reports on unused objects
in PAN-OS configurations.
"""

import logging
from typing import Dict, Any, Optional, List, Set, Union
from lxml import etree

from ...modules.objects import get_objects
from ...modules.policies import get_policies
from ...core.logging_utils import logger


def generate_unused_objects_report_data(
    tree: etree._ElementTree,
    device_type: str,
    context_type: str,
    version: str,
    object_type: str = "address",
    **kwargs,
) -> Dict[str, Any]:
    """
    Generate raw data for a report of unused objects.

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
    report_data = {"unused_objects": []}

    # Get objects of the specified type in the current context
    objects = get_objects(tree, object_type, device_type, context_type, version, **kwargs)

    # Define policy types to check for object usage
    policy_types = []

    # Define base fields for each policy type (will be filtered based on object_type later)
    if device_type.lower() == "panorama":
        # Panorama policy types - both pre and post rulebases
        policy_types = [
            ("security_pre_rules", ["source", "destination", "service"]),
            ("security_post_rules", ["source", "destination", "service"]),
            (
                "nat_pre_rules",
                [
                    "source",
                    "destination",
                    "service",
                    "source-translation",
                    "destination-translation",
                    "service-translation",
                ],
            ),
            (
                "nat_post_rules",
                [
                    "source",
                    "destination",
                    "service",
                    "source-translation",
                    "destination-translation",
                    "service-translation",
                ],
            ),
            ("decryption_pre_rules", ["source", "destination", "service"]),
            ("decryption_post_rules", ["source", "destination", "service"]),
            ("qos_pre_rules", ["source", "destination", "service"]),
            ("qos_post_rules", ["source", "destination", "service"]),
            ("authentication_pre_rules", ["source", "destination", "service"]),
            ("authentication_post_rules", ["source", "destination", "service"]),
            ("pbf_pre_rules", ["source", "destination", "service"]),
            ("pbf_post_rules", ["source", "destination", "service"]),
            ("application_override_pre_rules", ["source", "destination", "service"]),
            ("application_override_post_rules", ["source", "destination", "service"]),
            ("dos_pre_rules", ["source", "destination"]),
            ("dos_post_rules", ["source", "destination"]),
        ]
    else:  # firewall
        # Firewall policy types - standard rulebase
        policy_types = [
            ("security_rules", ["source", "destination", "service"]),
            (
                "nat_rules",
                [
                    "source",
                    "destination",
                    "service",
                    "source-translation",
                    "destination-translation",
                    "service-translation",
                ],
            ),
            ("decryption_rules", ["source", "destination", "service"]),
            ("qos_rules", ["source", "destination", "service"]),
            ("authentication_rules", ["source", "destination", "service"]),
            ("pbf_rules", ["source", "destination", "service"]),
            ("application_override_rules", ["source", "destination", "service"]),
            ("dos_rules", ["source", "destination"]),
        ]

    # Determine which group type to check based on object type
    group_type = None
    fields_to_check_map = {
        "address": ["source", "destination", "source-translation", "destination-translation"],
        "service": ["service", "service-translation"],
        "application": ["application"],
        "tag": ["tag"],
    }

    # Determine the appropriate group type to check
    if object_type == "address":
        group_type = "address-group"
    elif object_type == "service":
        group_type = "service-group"
    elif object_type == "application":
        group_type = "application-group"

    # Get the appropriate group objects if needed
    groups = {}
    if group_type:
        groups = get_objects(tree, group_type, device_type, context_type, version, **kwargs)

    # Track used objects
    used_objects = set()

    # Define contexts to check
    contexts_to_check = []

    if device_type.lower() == "panorama":
        if context_type == "shared":
            # For shared objects, we need to check:
            # 1. Shared policies
            contexts_to_check.append(("shared", {}))

            # 2. All device groups
            # Find all device groups
            dg_xpath = "/config/devices/entry[@name='localhost.localdomain']/device-group/entry"
            dg_elements = tree.xpath(dg_xpath)
            for dg in dg_elements:
                dg_name = dg.get("name")
                if dg_name:
                    contexts_to_check.append(("device_group", {"device_group": dg_name}))

        elif context_type == "device_group":
            # For device group objects, we only need to check that specific device group
            contexts_to_check.append((context_type, kwargs))
    else:
        # For firewall, just check the current context
        contexts_to_check.append((context_type, kwargs))

    # Check each context for usage
    for ctx_type, ctx_kwargs in contexts_to_check:
        # Check policies for this context
        for policy_type, fields_to_check in policy_types:
            try:
                # Get policies of this type
                policies = get_policies(
                    tree, policy_type, device_type, ctx_type, version, **ctx_kwargs
                )

                # Check each policy for object usage
                for rule_name, rule in policies.items():
                    # Get the appropriate fields to check based on object type
                    relevant_fields = fields_to_check_map.get(object_type, fields_to_check)

                    # Check all relevant fields that might contain objects of the specified type
                    for field in relevant_fields:
                        if field in rule and isinstance(rule[field], list):
                            for obj in rule[field]:
                                used_objects.add(obj)
                        elif field in rule and isinstance(rule[field], dict):
                            # Handle nested fields like source-translation or service-translation
                            for subfield, value in rule[field].items():
                                if isinstance(value, list):
                                    for obj in value:
                                        used_objects.add(obj)
                                elif isinstance(value, str):
                                    used_objects.add(value)

                                # Special handling for service objects in service-translation
                                if object_type == "service" and field == "service-translation":
                                    # In some cases, the service name could be in the 'translated-service' field
                                    if subfield == "translated-service" and isinstance(value, str):
                                        used_objects.add(value)
                                    # Also check for protocol-specific fields that might reference service objects
                                    elif subfield in ["tcp", "udp"] and isinstance(value, dict):
                                        for proto_field, proto_value in value.items():
                                            if isinstance(proto_value, str):
                                                used_objects.add(proto_value)
            except Exception as e:
                # Log but continue if a policy type fails
                logger.warning(f"Error checking {policy_type} for object usage in {ctx_type}: {e}")
                continue

        # Check appropriate groups for this context
        if group_type:
            try:
                ctx_groups = get_objects(
                    tree, group_type, device_type, ctx_type, version, **ctx_kwargs
                )
                for group_name, group in ctx_groups.items():
                    if "static" in group and isinstance(group["static"], list):
                        for obj in group["static"]:
                            used_objects.add(obj)
                    # For service groups, also check "members" field
                    elif "members" in group and isinstance(group["members"], list):
                        for obj in group["members"]:
                            used_objects.add(obj)
            except Exception as e:
                # Log but continue if group check fails
                logger.warning(f"Error checking {group_type} for usage in {ctx_type}: {e}")
                continue

    # Find unused objects
    unused_objects = []
    for obj_name in objects:
        if obj_name not in used_objects:
            unused_objects.append({"name": obj_name, "properties": objects[obj_name]})

    report_data["unused_objects"] = unused_objects
    logger.info(
        f"Found {len(unused_objects)} unused {object_type} objects out of {len(objects)} total"
    )

    return report_data
