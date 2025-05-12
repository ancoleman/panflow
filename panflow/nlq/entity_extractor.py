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

        # Initialize entities with defaults for CLI parameters
        entities = {
            "config": None,  # Will be filled in by command mapper
            "output": None,  # Will be filled in by command mapper
            "dry_run": self._extract_dry_run(normalized_query),
            "object_type": "address",  # Default object type is address
            "show_duplicates": self._extract_duplicates_request(normalized_query),
        }

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
            # Special handling for "nat policies" and variations
            if entities["policy_type"] == "nat_rules" and not any(
                pre_post in normalized_query for pre_post in ["pre", "post"]
            ):
                # Check if we need to detect device type for proper policy type
                device_type = entities.get("device_type", "firewall")
                if device_type.lower() == "panorama":
                    entities["policy_type"] = "nat_pre_rules"  # Default to pre-rules for Panorama

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
            r"duplicated?\s+(?:object|address|service|tag|application)",
            r"(?:object|address|service|tag|application)s?\s+(?:that\s+(?:are|is)\s+)?duplicated",
            r"duplicate(?:d)?\s+(?:object|address|service|tag|application)s?",
            r"find\s+duplicates?",
            r"show(?:\s+me)?\s+duplicates?",
            r"list\s+duplicates?",
            r"identical\s+(?:object|address|service|tag|application)s?",
            r"same\s+(?:object|address|service|tag|application)s?",
        ]

        for pattern in duplicate_patterns:
            if re.search(pattern, query):
                return True

        return False
