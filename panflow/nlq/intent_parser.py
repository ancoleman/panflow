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
            "cleanup_disabled_policies": [
                r"(clean|remove|delete).*?(disabled|inactive).*(?:policies|rules|policy|rule|security)",
                r"(cleanup|clean up).*?disabled.*(?:policies|rules|policy|rule|security)",
                r"(clean|remove|delete|cleanup|clean up).*?all.*?disabled.*(?:policies|rules|policy|rule|security)",
            ],
            "list_unused_objects": [
                r"(list|show|find|display|get).*?(unused|not used|unreferenced).*object",
                r"what.*?(unused|not used|unreferenced).*object",
                r"(show me|find me|identify).*?(unused|not used|unreferenced).*object",
            ],
            "list_disabled_policies": [
                r"(list|show|find|display|get).*?(disabled|inactive).*(?:policies|rules|policy|rule|security)",
                r"what.*?(disabled|inactive).*(?:policies|rules|policy|rule|security)",
                r"(show me|find me|identify).*?(disabled|inactive).*(?:policies|rules|policy|rule|security)",
            ],
            "find_duplicates": [
                r"(find|identify|discover|locate|show|list|display|get).*duplicates",
                r"(find|identify|discover|locate|show|list|display|get).*duplicate.*object",
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
            
            # Duplicates
            "find duplicates": "find_duplicates",
            "show duplicate objects": "find_duplicates",
            "list duplicate address objects": "find_duplicates",
            "find duplicate services": "find_duplicates",
            
            # Help
            "help": "help",
            "what can you do": "help",
            "how does this work": "help",
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