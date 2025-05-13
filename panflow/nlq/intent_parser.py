"""
Intent parsing module for PANFlow NLQ.

This module is responsible for identifying the intent behind a natural language query.
"""

import re
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger("panflow.nlq.intent")


class IntentParser:
    """
    Parser for identifying intents in natural language queries.

    This class uses pattern matching to identify the intent behind a query.
    """

    def __init__(self):
        """Initialize the intent parser with predefined patterns."""
        # Define intent patterns
        self.intent_patterns = {
            "cleanup_unused_objects": [
                r"(clean|remove|delete).*?(unused|not used|unreferenced).*object",
                r"(cleanup|clean up).*?unused.*object",
            ],
            "cleanup_duplicate_objects": [
                r"(clean|remove|delete).*?(duplicated?|duplicate).*object",
                r"(cleanup|clean up).*?(duplicated?|duplicate).*object",
                r"(deduplicate|dedupe|consolidate).*object",
                r"(clean|remove|delete|cleanup|clean up).*?all.*?(duplicated?|duplicate).*object",
            ],
            "cleanup_disabled_policies": [
                r"(clean|remove|delete).*?(disabled|inactive).*(?:policies|rules|policy|rule|security)",
                r"(cleanup|clean up).*?disabled.*(?:policies|rules|policy|rule|security)",
                r"(clean|remove|delete|cleanup|clean up).*?all.*?disabled.*(?:policies|rules|policy|rule|security)",
            ],
            "list_unused_objects": [
                r"(list|show|find|display|get).*?(unused|not used|unreferenced).*(?:object|group)",
                r"what.*?(unused|not used|unreferenced).*(?:object|group)",
                r"(show me|find me|identify).*?(unused|not used|unreferenced).*(?:object|group)",
            ],
            "list_disabled_policies": [
                r"(list|show|find|display|get).*?(disabled|inactive).*(?:policies|rules|policy|rule|security)",
                r"what.*?(disabled|inactive).*(?:policies|rules|policy|rule|security)",
                r"(show me|find me|identify).*?(disabled|inactive).*(?:policies|rules|policy|rule|security)",
            ],
            "list_objects": [
                r"^(list|show|find|display|get)(?!\s+(?:unused|duplicate|disabled)).*?(?:address|service|tag|application).*?(?:objects?|groups?)$",
                r"^(show me|find me|list me)(?!\s+(?:unused|duplicate|disabled)).*?(?:address|service|tag|application).*?(?:objects?|groups?)$",
                r"^(list|show|find|display|get)(?!\s+(?:unused|duplicate|disabled)).*?(?:address|service|tag|application)\-(?:objects?|groups?)$",
            ],
            "list_policies": [
                r"^(list|show|find|display|get)(?!\s+(?:unused|duplicate|disabled)).*?(?:policies|rules|policy|rule|security)$",
                r"^(show me|find me|list me)(?!\s+(?:unused|duplicate|disabled)).*?(?:policies|rules|policy|rule|security)$",
            ],
            "find_duplicates": [
                r"(find|identify|discover|locate|show|list|display|get).*duplicates",
                r"(find|identify|discover|locate|show|list|display|get).*duplicate.*object",
            ],
            "bulk_update_policies": [
                r"(update|change|modify|set|add).*?(?:tag|action|log|profile|security-profile).*?(?:policies|rules|policy|rule|security)",
                r"(update|change|modify|set|add).*?(?:tag|action|log|profile|security-profile).*?to.*?(?:policies|rules|policy|rule|security)",
                r"(enable|disable).*?(?:policies|rules|policy|rule|security)",
                r"(update|change|modify|set|add).*?tag.*?(?:policies|rules|policy|rule|security)",
                r"(update|change|modify|set|add).*?action.*?(?:policies|rules|policy|rule|security)",
                r"(enable|disable).*?logging.*?(?:policies|rules|policy|rule|security)",
            ],
            "help": [
                r"help",
                r"what can (you|this) do",
                r"what (commands|queries) (are supported|can I use)",
            ],
        }

    def parse(self, query: str) -> Tuple[str, float]:
        """
        Parse a natural language query to identify the intent.

        Args:
            query: The natural language query to parse

        Returns:
            Tuple of (intent, confidence)
        """
        # Normalize the query
        normalized_query = query.lower().strip()

        # Check for exact match with examples
        exact_match = self._check_exact_match(normalized_query)
        if exact_match:
            return exact_match, 1.0

        # Check against patterns
        best_intent = None
        best_score = 0.0

        for intent, patterns in self.intent_patterns.items():
            score = self._calculate_intent_score(normalized_query, patterns)
            logger.debug(f"Intent '{intent}' score: {score:.2f}")

            if score > best_score:
                best_intent = intent
                best_score = score

        # If we couldn't find a clear intent, default to help
        if best_intent is None or best_score < 0.3:
            return "help", 0.0

        return best_intent, best_score

    def _check_exact_match(self, query: str) -> Optional[str]:
        """
        Check if the query exactly matches any known examples.

        Args:
            query: The normalized query

        Returns:
            The matched intent or None
        """
        # Expanded exact matches with more examples
        exact_matches = {
            # Cleanup operations
            "cleanup unused objects": "cleanup_unused_objects",
            "remove unused objects": "cleanup_unused_objects",
            "delete unused objects": "cleanup_unused_objects",
            "cleanup unused address objects": "cleanup_unused_objects",
            "cleanup unused service objects": "cleanup_unused_objects",
            "cleanup unused address groups": "cleanup_unused_objects",
            "cleanup unused service groups": "cleanup_unused_objects",
            "remove unused address groups": "cleanup_unused_objects",
            "remove unused service groups": "cleanup_unused_objects",
            "delete unused address groups": "cleanup_unused_objects",
            "delete unused service groups": "cleanup_unused_objects",
            # Cleanup duplicate operations
            "cleanup duplicate objects": "cleanup_duplicate_objects",
            "cleanup duplicated objects": "cleanup_duplicate_objects",
            "remove duplicate objects": "cleanup_duplicate_objects",
            "delete duplicate objects": "cleanup_duplicate_objects",
            "deduplicate objects": "cleanup_duplicate_objects",
            "clean up duplicated service objects": "cleanup_duplicate_objects",
            "cleanup duplicate address objects": "cleanup_duplicate_objects",
            "cleanup duplicated service objects": "cleanup_duplicate_objects",
            "remove duplicate address objects": "cleanup_duplicate_objects",
            "delete duplicate service objects": "cleanup_duplicate_objects",
            "deduplicate address objects": "cleanup_duplicate_objects",
            "deduplicate service objects": "cleanup_duplicate_objects",
            # Policy operations
            "cleanup disabled policies": "cleanup_disabled_policies",
            "remove disabled rules": "cleanup_disabled_policies",
            "delete disabled policies": "cleanup_disabled_policies",
            "cleanup disabled security rules": "cleanup_disabled_policies",
            "cleanup all disabled security rules": "cleanup_disabled_policies",
            "cleanup all disabled security policy": "cleanup_disabled_policies",
            "cleanup disabled security policy": "cleanup_disabled_policies",
            # View operations
            "show unused objects": "list_unused_objects",
            "show me unused objects": "list_unused_objects",
            "list unused objects": "list_unused_objects",
            "find unused objects": "list_unused_objects",
            "display unused objects": "list_unused_objects",
            "show me all unused address objects": "list_unused_objects",
            "find unused service objects": "list_unused_objects",
            "show me all unused address groups": "list_unused_objects",
            "list all unused service groups": "list_unused_objects",
            "show unused address groups": "list_unused_objects",
            "show unused service groups": "list_unused_objects",
            "what unused objects do i have": "list_unused_objects",
            # Policy view operations
            "show disabled policies": "list_disabled_policies",
            "show me disabled rules": "list_disabled_policies",
            "list disabled policies": "list_disabled_policies",
            "find disabled rules": "list_disabled_policies",
            "display disabled security rules": "list_disabled_policies",
            "show disabled security policy": "list_disabled_policies",
            "show all disabled security policy": "list_disabled_policies",
            "show me all disabled security policy": "list_disabled_policies",
            "which policies are disabled": "list_disabled_policies",
            # List objects commands
            "list address objects": "list_objects",
            "show address objects": "list_objects",
            "list service objects": "list_objects",
            "show service objects": "list_objects",
            "list tag objects": "list_objects",
            "show tag objects": "list_objects",
            "list objects": "list_objects",
            "show objects": "list_objects",
            "list all address objects": "list_objects",
            "show me address objects": "list_objects",
            "show all address objects": "list_objects",
            "show me all address objects": "list_objects",
            "list all service objects": "list_objects",
            "show me service objects": "list_objects",
            "show all service objects": "list_objects",
            "show me all service objects": "list_objects",
            "list application objects": "list_objects",
            "show application objects": "list_objects",
            "list all application objects": "list_objects",
            "show me application objects": "list_objects",
            "show all application objects": "list_objects",
            "show me all application objects": "list_objects",
            "list address-groups": "list_objects",
            "show address-groups": "list_objects",
            "list service-groups": "list_objects",
            "show service-groups": "list_objects",
            "list application-groups": "list_objects",
            "show application-groups": "list_objects",
            # List policies commands
            "list policies": "list_policies",
            "show policies": "list_policies",
            "list security policies": "list_policies",
            "show security policies": "list_policies",
            "list rules": "list_policies",
            "show rules": "list_policies",
            "list security rules": "list_policies",
            "show security rules": "list_policies",
            "list all policies": "list_policies",
            "show me policies": "list_policies",
            "show all policies": "list_policies",
            "show me all policies": "list_policies",
            # Duplicates
            "find duplicates": "find_duplicates",
            "show duplicate objects": "find_duplicates",
            "list duplicate address objects": "find_duplicates",
            "find duplicate services": "find_duplicates",
            # Help
            "help": "help",
            "what can you do": "help",
            "how does this work": "help",
            # Bulk Update Operations
            "add tag to all policies": "bulk_update_policies",
            "add tag to security policies": "bulk_update_policies",
            "add tag to all security policies": "bulk_update_policies",
            "update tag for all policies": "bulk_update_policies",
            "set tag on all security policies": "bulk_update_policies",
            "change action for security policies": "bulk_update_policies",
            "set action to allow for all policies": "bulk_update_policies",
            "set action to deny for all security rules": "bulk_update_policies",
            "change action to allow": "bulk_update_policies",
            "change action to deny": "bulk_update_policies",
            "enable all security policies": "bulk_update_policies",
            "disable all security policies": "bulk_update_policies",
            "enable logging for all policies": "bulk_update_policies",
            "disable logging for all policies": "bulk_update_policies",
            "enable logging for security policies": "bulk_update_policies",
            "disable logging for security policies": "bulk_update_policies",
        }

        return exact_matches.get(query)

    def _calculate_intent_score(self, query: str, patterns: List[str]) -> float:
        """
        Calculate a score for how well the query matches the intent patterns.

        Args:
            query: The normalized query
            patterns: List of regex patterns for the intent

        Returns:
            Score between 0.0 and 1.0
        """
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                # Calculate a score based on how much of the query is matched
                match_length = match.end() - match.start()
                query_length = len(query)
                coverage = match_length / query_length

                # Higher score for patterns that cover more of the query
                return min(0.6 + (coverage * 0.4), 1.0)

        return 0.0
