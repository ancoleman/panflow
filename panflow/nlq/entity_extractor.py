"""
Entity extraction module for PANFlow NLQ.

This module is responsible for extracting entities from natural language queries,
such as object types, policy types, contexts, etc.
"""

import re
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger("panflow.nlq.entity")


class EntityExtractor:
    """
    Extractor for identifying entities in natural language queries.

    This class uses pattern matching to extract entities from queries.
    """

    def __init__(self):
        """Initialize the entity extractor with entity patterns."""
        # Define entity extraction patterns
        self.entity_patterns = {
            "object_type": {
                "all": [r"all\s+objects", r"any\s+objects?", r"every\s+objects?", r"objects\s+all", r"just\s+objects"],
                "address": [r"address(?:\s+object)?s?", r"ip\s+address"],
                "service": [r"service(?:\s+object)?s?"],
                "tag": [r"tags?"],
                "address-group": [r"address\s+groups?", r"address\-groups?"],
                "service-group": [r"service\s+groups?", r"service\-groups?"],
                "application": [r"application(?:\s+object)?s?"],
                "application-group": [r"application\s+groups?", r"application\-groups?"],
            },
            "policy_type": {
                "security_rules": [r"security\s+(?:policies|rules)", r"security"],
                "nat_rules": [r"nat\s+(?:policies|rules)", r"nat"],
                "security_pre_rules": [
                    r"(?:pre|pre-rulebase)\s+security\s+(?:policies|rules)",
                    r"pre\s+security",
                ],
                "security_post_rules": [
                    r"(?:post|post-rulebase)\s+security\s+(?:policies|rules)",
                    r"post\s+security",
                ],
                "nat_pre_rules": [r"(?:pre|pre-rulebase)\s+nat\s+(?:policies|rules)", r"pre\s+nat"],
                "nat_post_rules": [
                    r"(?:post|post-rulebase)\s+nat\s+(?:policies|rules)",
                    r"post\s+nat",
                ],
            },
            "context": {
                "shared": [r"shared", r"common"],
                "device_group": [r"device\s+groups?", r"device\-groups?", r"dg"],
                "vsys": [r"vsys"],
                "template": [r"templates?"],
            },
            "device_type": {
                "firewall": [r"firewall", r"fw"],
                "panorama": [r"panorama", r"pano"],
            },
        }

        # Define specific entity patterns for named entities
        self.named_entity_patterns = {
            "device_group": r"device\s+group\s+(?:called|named)?\s+[\'\"]?([a-zA-Z0-9\-_]+)[\'\"]?",
            "vsys": r"vsys\s+(?:called|named)?\s+[\'\"]?([a-zA-Z0-9\-_]+)[\'\"]?",
        }

        # Common defaults
        self.defaults = {
            "object_type": "address",
            "policy_type": "security_rules",
            "context": "vsys",
            "device_type": "firewall",
            "vsys": "vsys1",
        }

        # Bulk update operation patterns
        # Order is important - more specific operations should come first
        self.bulk_operations = {
            # More specific operations first
            "enable_logging": [
                r"enable\s+log(?:ging|s)(?:\s+.*)?$",
                r"turn\s+on\s+log(?:ging|s)(?:\s+.*)?$",
                r"add\s+log(?:ging|s)(?:\s+.*)?$"
            ],
            "disable_logging": [
                r"disable\s+log(?:ging|s)(?:\s+.*)?$",
                r"turn\s+off\s+log(?:ging|s)(?:\s+.*)?$",
                r"remove\s+log(?:ging|s)(?:\s+.*)?$"
            ],
            "add_tag": [
                r"add\s+tags?\s+['\"]?([^'\"]+)['\"]?",
                r"set\s+tags?\s+['\"]?([^'\"]+)['\"]?",
                r"apply\s+tags?\s+['\"]?([^'\"]+)['\"]?",
                r"tag\s+with\s+['\"]?([^'\"]+)['\"]?"
            ],
            "set_action": [
                r"(?:set|change|update|modify)\s+action\s+to\s+([a-z]+)",
                r"make\s+(?:action|rule)\s+([a-z]+)",
                r"set\s+to\s+([a-z]+)"
            ],
            # General operations last
            "enable": [
                r"enable\s+.*?(?:policy|policies|rule|rules)",
                r"activate\s+.*?(?:policy|policies|rule|rules)"
            ],
            "disable": [
                r"disable\s+.*?(?:policy|policies|rule|rules)",
                r"deactivate\s+.*?(?:policy|policies|rule|rules)"
            ]
        }

    def extract(self, query: str) -> Dict[str, Any]:
        """
        Extract entities from a natural language query.

        Args:
            query: The natural language query

        Returns:
            Dictionary of extracted entities
        """
        # Normalize the query
        normalized_query = query.lower().strip()

        # Check if this is explicitly a request for "all objects"
        all_objects_patterns = [
            r"all\s+(?:duplicated?\s+)?objects",
            r"every\s+object",
            r"all\s+types\s+of\s+objects",
            r"any\s+(?:duplicated?\s+)?objects?"
        ]

        # Check if this is a request for "all policies"
        all_policies_patterns = [
            r"all\s+(?:disabled\s+)?(?:policies|policy|rules|security policies|security rules)",
            r"every\s+(?:disabled\s+)?(?:policy|rule)",
            r"all\s+types\s+of\s+(?:policies|rules)",
            r"any\s+(?:disabled\s+)?(?:policies|rules)"
        ]

        is_all_objects_request = any(re.search(pattern, normalized_query) for pattern in all_objects_patterns)
        is_all_policies_request = any(re.search(pattern, normalized_query) for pattern in all_policies_patterns)

        # Debug the pattern matching
        logger.debug(f"Checking for all policies in query: '{normalized_query}'")
        for pattern in all_policies_patterns:
            match = re.search(pattern, normalized_query)
            if match:
                logger.debug(f"Found match for all_policies with pattern: '{pattern}'")
                break

        # Initialize entities with defaults for CLI parameters
        entities = {
            "config": None,  # Will be filled in by command mapper
            "output": None,  # Will be filled in by command mapper
            "dry_run": self._extract_dry_run(normalized_query),
            "object_type": "all" if is_all_objects_request else "address",  # Default to "all" for "all objects" queries
            "policy_type": "all" if is_all_policies_request else "security_rules",  # Set policy type to "all" for "all policies" queries, default to security_rules
            "show_duplicates": self._extract_duplicates_request(normalized_query),
        }

        # Log the entity extraction for debugging
        logger.debug(f"Initial entities: {entities}")

        # Extract entity types
        for entity_type, entity_dict in self.entity_patterns.items():
            for entity_value, patterns in entity_dict.items():
                for pattern in patterns:
                    if re.search(pattern, normalized_query):
                        entities[entity_type] = entity_value
                        break

        # Extract named entities
        for entity_name, pattern in self.named_entity_patterns.items():
            match = re.search(pattern, normalized_query)
            if match and match.group(1):
                entities[entity_name] = match.group(1)

        # Handle special cases for group objects
        if (
            "object_type" in entities
            and entities["object_type"] == "address"
            and any(
                phrase in normalized_query
                for phrase in ["address-group", "address group", "address-groups", "address groups"]
            )
        ):
            entities["object_type"] = "address-group"

        if (
            "object_type" in entities
            and entities["object_type"] == "service"
            and any(
                phrase in normalized_query
                for phrase in ["service-group", "service group", "service-groups", "service groups"]
            )
        ):
            entities["object_type"] = "service-group"

        # Handle special case for policy types
        if "policy_type" in entities:
            device_type = entities.get("device_type", "firewall")

            # Special handling for "nat policies" and variations
            if entities["policy_type"] == "nat_rules" and not any(
                pre_post in normalized_query for pre_post in ["pre", "post"]
            ):
                # Check if we need to detect device type for proper policy type
                if device_type.lower() == "panorama":
                    entities["policy_type"] = "nat_pre_rules"  # Default to pre-rules for Panorama

            # Special handling for security policies
            if entities["policy_type"] == "security_rules" and device_type.lower() == "panorama":
                # Adjust for Panorama - need pre/post specification
                if "post" in normalized_query:
                    entities["policy_type"] = "security_post_rules"
                else:
                    entities["policy_type"] = "security_pre_rules"  # Default to pre-rules for Panorama

            # Special handling for "security policies" and variations
            if entities["policy_type"] == "security_rules" and not any(
                pre_post in normalized_query for pre_post in ["pre", "post"]
            ):
                device_type = entities.get("device_type", "firewall")
                if device_type.lower() == "panorama":
                    entities[
                        "policy_type"
                    ] = "security_pre_rules"  # Default to pre-rules for Panorama

        # TODO: Add more special case handling as needed

        # Extract bulk operation entities
        bulk_operation = self._extract_bulk_operation(normalized_query)
        if bulk_operation:
            logger.info(f"Extracted bulk operation: {bulk_operation}")
            entities.update(bulk_operation)

        return entities

    def _extract_dry_run(self, query: str) -> bool:
        """
        Determine if this is a dry run request.

        Args:
            query: The normalized query

        Returns:
            True if this is a dry run, False otherwise
        """
        dry_run_patterns = [
            r"dry\s+run",
            r"preview",
            r"simulate",
            r"(?:without|don't)\s+(?:making|apply|applying)\s+changes",
            r"just\s+(?:show|tell)",
        ]

        for pattern in dry_run_patterns:
            if re.search(pattern, query):
                return True

        return False

    def _extract_duplicates_request(self, query: str) -> bool:
        """
        Determine if this is a request for duplicated objects.

        Args:
            query: The normalized query

        Returns:
            True if this is a request for duplicates, False otherwise
        """
        duplicate_patterns = [
            r"duplicated?\s+(?:object|address|service|tag|application|all)",
            r"(?:object|address|service|tag|application)s?\s+(?:that\s+(?:are|is)\s+)?duplicated",
            r"duplicate(?:d)?\s+(?:object|address|service|tag|application|all)s?",
            r"find\s+duplicates?",
            r"show(?:\s+me)?\s+duplicates?",
            r"list\s+duplicates?",
            r"identical\s+(?:object|address|service|tag|application)s?",
            r"same\s+(?:object|address|service|tag|application)s?",
            r"find\s+all\s+duplicated?\s+objects?",
            r"all\s+duplicated?\s+objects",
            r"duplicated?\s+all\s+objects",
        ]

        for pattern in duplicate_patterns:
            if re.search(pattern, query):
                return True

        return False

    def _extract_bulk_operation(self, query: str) -> Dict[str, Any]:
        """
        Extract bulk operation type and value from a query.

        Args:
            query: The normalized query

        Returns:
            Dictionary with operation and value if found, empty dict otherwise
        """
        result = {}

        # Add debug logging
        logger.debug(f"Extracting bulk operation from query: '{query}'")

        # Check for each operation type
        for operation_type, patterns in self.bulk_operations.items():
            for pattern in patterns:
                logger.debug(f"Trying pattern for {operation_type}: '{pattern}'")
                match = re.search(pattern, query)
                if match:
                    logger.debug(f"Found match for operation: {operation_type}")
                    result["operation"] = operation_type

                    # For operations that need a value from the regex
                    if operation_type in ["add_tag", "set_action"]:
                        if match.groups() and match.group(1):
                            if operation_type == "add_tag":
                                result["value"] = match.group(1)
                                logger.debug(f"Extracted tag value: {result['value']}")
                            elif operation_type == "set_action":
                                action = match.group(1).lower()
                                result["value"] = action
                                logger.debug(f"Extracted action value: {result['value']}")
                    elif operation_type in ["enable", "disable", "enable_logging", "disable_logging"]:
                        # These operations just need a "yes" value
                        result["value"] = "yes"
                        logger.debug(f"Set value 'yes' for {operation_type}")

                    return result

        logger.debug("No bulk operation match found")
        return result
