"""
Policy merger for PANFlow.

This module provides functionality for merging policies between different configurations,
device groups, or virtual systems.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Set
from lxml import etree
import copy

from .xpath_resolver import get_policy_xpath
from .config_loader import xpath_search
from .xml_utils import clone_element, merge_elements
from .conflict_resolver import ConflictResolver, ConflictStrategy

# Initialize logger
logger = logging.getLogger("panflow")

class PolicyMerger:
    """
    Class for merging policies between PAN-OS configurations.
    
    Provides methods for copying policies from one configuration to another,
    with options to handle conflicts and dependencies.
    """
    
    # Dictionary defining version-specific attributes for each policy type
    # Format: policy_type -> {attribute -> {version: required}}
    VERSION_SPECIFIC_ATTRIBUTES = {
        "security": {  # Security rules
            "source": {"10.1": True, "10.2": True, "11.2": True},
            "destination": {"10.1": True, "10.2": True, "11.2": True},
            "service": {"10.1": True, "10.2": True, "11.2": True},
            "application": {"10.1": True, "10.2": True, "11.2": True},
            "action": {"10.1": True, "10.2": True, "11.2": True},
            "source-user": {"10.1": False, "10.2": False, "11.2": False},
            "category": {"10.1": False, "10.2": False, "11.2": False},
            "profile-setting": {"10.1": False, "10.2": False, "11.2": False},
            "tag": {"10.1": False, "10.2": False, "11.2": False},
            "negate-source": {"10.1": False, "10.2": False, "11.2": False},
            "negate-destination": {"10.1": False, "10.2": False, "11.2": False},
            "source-hip": {"10.1": False, "10.2": False, "11.2": False},
            "destination-hip": {"10.1": False, "10.2": False, "11.2": False},
            "source-address-translation": {"10.1": False, "10.2": False, "11.2": False},
            "destination-address-translation": {"10.1": False, "10.2": False, "11.2": False},
            "schedule": {"10.1": False, "10.2": False, "11.2": False},
            "disable-server-response-inspection": {"10.2": False, "11.2": False},  # Added in 10.2+
            "ssl-decrypt-mirror": {"11.2": False},  # Added in 11.0+
            "url-category-match": {"11.2": False},  # Added in 11.0+
            "rule-type": {"11.2": False},  # Added in 11.0+
        },
        "nat": {  # NAT rules
            "source": {"10.1": True, "10.2": True, "11.2": True},
            "destination": {"10.1": True, "10.2": True, "11.2": True},
            "service": {"10.1": True, "10.2": True, "11.2": True},
            "to": {"10.1": True, "10.2": True, "11.2": True},
            "source-translation": {"10.1": False, "10.2": False, "11.2": False},
            "destination-translation": {"10.1": False, "10.2": False, "11.2": False},
            "tag": {"10.1": False, "10.2": False, "11.2": False},
            "disabled": {"10.1": False, "10.2": False, "11.2": False},
            "nat-type": {"10.1": False, "10.2": False, "11.2": False},
            "fallback": {"10.2": True, "11.2": True},  # Changed to required in 10.2+
            "source-address-translation": {"10.1": False, "10.2": False, "11.2": False},
            "destination-address-translation": {"10.1": False, "10.2": False, "11.2": False},
        },
        "pbf": {  # Policy-based forwarding rules
            "source": {"10.1": True, "10.2": True, "11.2": True},
            "destination": {"10.1": True, "10.2": True, "11.2": True},
            "service": {"10.1": True, "10.2": True, "11.2": True},
            "forwarding": {"10.1": True, "10.2": True, "11.2": True},
            "tag": {"10.1": False, "10.2": False, "11.2": False},
            "disabled": {"10.1": False, "10.2": False, "11.2": False},
            "enforce-symmetric-return": {"10.1": False, "10.2": False, "11.2": False},
            "symmetric-return-addresses": {"10.2": False, "11.2": False},  # Added in 10.2+
        },
        "decryption": {  # SSL Decryption rules
            "source": {"10.1": True, "10.2": True, "11.2": True},
            "destination": {"10.1": True, "10.2": True, "11.2": True},
            "service": {"10.1": True, "10.2": True, "11.2": True},
            "category": {"10.1": False, "10.2": False, "11.2": False},
            "tag": {"10.1": False, "10.2": False, "11.2": False},
            "disabled": {"10.1": False, "10.2": False, "11.2": False},
            "type": {"10.1": True, "10.2": True, "11.2": True},
            "decryption-profile": {"10.1": False, "10.2": False, "11.2": False},
            "ssl-certificate": {"10.1": False, "10.2": False, "11.2": False},
            "ssl-forward-proxy": {"10.1": False, "10.2": False, "11.2": False},
            "ssl-inbound-inspection": {"10.1": False, "10.2": False, "11.2": False},
            "ssl-protocol-version-min": {"10.2": False, "11.2": False},  # Added in 10.2+
            "tls13-action": {"11.2": False},  # Added in 11.0+
        },
    }
    
    def __init__(
        self,
        source_tree: etree._ElementTree,
        target_tree: Optional[etree._ElementTree] = None,
        source_device_type: str = "panorama",
        target_device_type: Optional[str] = None,
        source_version: str = "11.2",
        target_version: Optional[str] = None
    ):
        """
        Initialize with source and target configurations.
        
        Args:
            source_tree: Source ElementTree containing policies to copy
            target_tree: Target ElementTree to merge policies into (can be the same as source_tree)
            source_device_type: Type of source device ("firewall" or "panorama")
            target_device_type: Type of target device (defaults to source_device_type)
            source_version: PAN-OS version of source configuration
            target_version: PAN-OS version of target configuration (defaults to source_version)
        """
        logger.debug("Initializing PolicyMerger")
        self.source_tree = source_tree
        self.target_tree = target_tree if target_tree is not None else source_tree
        self.source_device_type = source_device_type.lower()
        self.target_device_type = target_device_type.lower() if target_device_type else source_device_type.lower()
        self.source_version = source_version
        self.target_version = target_version if target_version else source_version
        
        # Track modifications
        self.merged_policies = []
        self.skipped_policies = []
        self.copied_objects = []
        
        # Initialize conflict resolver
        self.conflict_resolver = ConflictResolver(ConflictStrategy.SKIP)
        
        # Object references to track
        self.object_references = {
            "address": set(),
            "address_group": set(),
            "service": set(),
            "service_group": set(),
            "application_group": set(),
            "security_profile_group": set(),
            "virus": set(),              # Antivirus profiles
            "spyware": set(),            # Anti-spyware profiles
            "vulnerability": set(),      # Vulnerability profiles
            "url-filtering": set(),      # URL filtering profiles
            "file-blocking": set(),      # File blocking profiles
            "wildfire-analysis": set(),  # WildFire Analysis profiles
            "dns-security": set(),       # DNS Security profiles
            "data-filtering": set(),     # Data filtering profiles
            "schedule": set(),           # Schedule objects
            "custom-url-category": set(),# Custom URL categories
            "tag": set()
        }
        
        logger.info(f"PolicyMerger initialized: source={self.source_device_type} (v{self.source_version}), target={self.target_device_type} (v{self.target_version})")
    
    def copy_policy(
        self,
        policy_type: str,
        policy_name: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        copy_references: bool = True,
        position: str = "bottom",
        ref_policy_name: Optional[str] = None,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> bool:
        """
        Copy a single policy from source to target.
        
        Args:
            policy_type: Type of policy (security_pre_rules, nat_rules, etc.)
            policy_name: Name of the policy to copy
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            skip_if_exists: Skip if policy already exists in target (deprecated, use conflict_strategy instead)
            copy_references: Copy object references (address objects, etc.)
            position: Where to place the policy ("top", "bottom", "before", "after")
            ref_policy_name: Reference policy name for "before" and "after" positions
            conflict_strategy: Strategy to use when resolving conflicts with existing policies
            **kwargs: Additional parameters (source_device_group, target_device_group, etc.)
            
        Returns:
            bool: Success status
        """
        logger.info(f"Copying policy: {policy_type}/{policy_name} from {source_context_type} to {target_context_type}")
        logger.debug(f"Copy parameters: skip_if_exists={skip_if_exists}, copy_references={copy_references}, "
                    f"position={position}, ref_policy={ref_policy_name}")
        
        # Extract context parameters
        source_params = self._extract_context_params(source_context_type, kwargs, 'source_')
        target_params = self._extract_context_params(target_context_type, kwargs, 'target_')
        logger.debug(f"Source context parameters: {source_params}")
        logger.debug(f"Target context parameters: {target_params}")
        
        # Get the source policy
        source_xpath = get_policy_xpath(
            policy_type, 
            self.source_device_type, 
            source_context_type, 
            self.source_version, 
            policy_name, 
            **source_params
        )
        logger.debug(f"Source policy XPath: {source_xpath}")
        
        source_elements = xpath_search(self.source_tree, source_xpath)
        if not source_elements:
            logger.error(f"Policy '{policy_name}' not found in source")
            self.skipped_policies.append((policy_name, "Not found in source"))
            return False
        
        source_policy = source_elements[0]
        logger.debug(f"Found source policy: {policy_name}")
        
        # Check if policy exists in target
        target_xpath = get_policy_xpath(
            policy_type, 
            self.target_device_type, 
            target_context_type, 
            self.target_version, 
            policy_name, 
            **target_params
        )
        logger.debug(f"Target policy XPath: {target_xpath}")
        
        target_elements = xpath_search(self.target_tree, target_xpath)
        if target_elements:
            # Handle conflict using conflict resolution strategy
            if conflict_strategy is None:
                # Use skip_if_exists for backward compatibility
                if skip_if_exists:
                    conflict_strategy = ConflictStrategy.SKIP
                else:
                    conflict_strategy = ConflictStrategy.OVERWRITE
            
            # Resolve the conflict
            success, resolved_policy, message = self.conflict_resolver.resolve_conflict(
                source_policy, target_elements[0], policy_type, policy_name, conflict_strategy, **kwargs
            )
            
            if not success:
                logger.warning(f"Policy '{policy_name}' conflict resolution: {message}")
                self.skipped_policies.append((policy_name, message))
                return False
            
            # Remove the existing policy
            parent = target_elements[0].getparent()
            if parent is not None:
                logger.info(f"Removing existing policy '{policy_name}' from target")
                parent.remove(target_elements[0])
                
                # If the conflict strategy provided a new policy, use that
                if resolved_policy is not None:
                    source_policy = resolved_policy
            else:
                logger.error(f"Cannot remove existing policy '{policy_name}' - parent element not found")
                self.skipped_policies.append((policy_name, "Cannot remove existing policy"))
                return False
        
        # Get the target parent element
        target_parent_xpath = get_policy_xpath(
            policy_type, 
            self.target_device_type, 
            target_context_type, 
            self.target_version, 
            **target_params
        )
        logger.debug(f"Target parent XPath: {target_parent_xpath}")
        
        target_parent_elements = xpath_search(self.target_tree, target_parent_xpath)
        if not target_parent_elements:
            logger.error(f"Target parent element not found for policy '{policy_name}'")
            self.skipped_policies.append((policy_name, "Target parent element not found"))
            return False
        
        target_parent = target_parent_elements[0]
        
        # Create a copy of the source policy
        try:
            logger.debug(f"Cloning policy element: {policy_name}")
            new_policy = clone_element(source_policy)
            
            # Handle version-specific attribute differences if source and target versions differ
            if self.source_version != self.target_version:
                logger.debug(f"Handling version-specific attributes for {policy_type} '{policy_name}'")
                new_policy = self._handle_version_specific_attributes(new_policy, policy_type)
        except Exception as e:
            logger.error(f"Failed to clone policy '{policy_name}': {e}", exc_info=True)
            self.skipped_policies.append((policy_name, f"Cloning failed: {str(e)}"))
            return False
        
        # Collect references before adding to target
        if copy_references:
            logger.debug(f"Collecting references from policy '{policy_name}'")
            self._collect_policy_references(new_policy)
        
        # Add the policy to the target at the specified position
        try:
            logger.debug(f"Adding policy '{policy_name}' to target at position '{position}'")
            self._add_policy_at_position(
                target_parent, 
                new_policy, 
                position, 
                ref_policy_name
            )
        except Exception as e:
            logger.error(f"Failed to add policy '{policy_name}' to target: {e}", exc_info=True)
            self.skipped_policies.append((policy_name, f"Adding to target failed: {str(e)}"))
            return False
        
        # Copy referenced objects if requested
        if copy_references:
            logger.info(f"Copying referenced objects for policy '{policy_name}'")
            try:
                self._copy_referenced_objects(target_context_type, source_context_type, **kwargs)
            except Exception as e:
                logger.warning(f"Error copying some referenced objects: {e}")
                # Continue since the policy itself was copied successfully
        
        self.merged_policies.append(policy_name)
        logger.info(f"Successfully copied policy '{policy_name}' to target")
        return True
    
    def copy_policies(
        self,
        policy_type: str,
        source_context_type: str,
        target_context_type: str,
        policy_names: Optional[List[str]] = None,
        filter_criteria: Optional[Dict[str, Any]] = None,
        skip_if_exists: bool = True,
        copy_references: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> Tuple[int, int]:
        """
        Copy multiple policies from source to target.
        
        Args:
            policy_type: Type of policy (security_pre_rules, nat_rules, etc.)
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            policy_names: List of policy names to copy (if None, use filter_criteria)
            filter_criteria: Dictionary of criteria to select policies
            skip_if_exists: Skip if policy already exists in target (deprecated, use conflict_strategy instead)
            copy_references: Copy object references (address objects, etc.)
            conflict_strategy: Strategy to use when resolving conflicts with existing policies
            **kwargs: Additional parameters (source_device_group, target_device_group, etc.)
            
        Returns:
            Tuple[int, int]: (number of policies copied, total number of policies attempted)
        """
        logger.info(f"Copying multiple policies of type {policy_type} from {source_context_type} to {target_context_type}")
        
        if policy_names:
            logger.info(f"Using specified list of {len(policy_names)} policy names")
        elif filter_criteria:
            logger.info(f"Using filter criteria: {filter_criteria}")
        else:
            logger.info("No policy names or filter criteria specified, will copy all policies")
        
        # Extract context parameters
        source_params = self._extract_context_params(source_context_type, kwargs, 'source_')
        logger.debug(f"Source context parameters: {source_params}")
        
        # Get the source policies
        source_base_xpath = get_policy_xpath(
            policy_type, 
            self.source_device_type, 
            source_context_type, 
            self.source_version, 
            **source_params
        )
        logger.debug(f"Source base XPath: {source_base_xpath}")
        
        source_policies = xpath_search(self.source_tree, f"{source_base_xpath}/entry")
        
        if not source_policies:
            logger.warning(f"No policies found in source matching the criteria")
            return 0, 0
        
        logger.info(f"Found {len(source_policies)} source policies to process")
        
        # Filter policies if needed
        policies_to_copy = []
        
        if policy_names:
            # Filter by name
            for policy in source_policies:
                name = policy.get("name")
                if name in policy_names:
                    policies_to_copy.append(policy)
            
            not_found = set(policy_names) - set(policy.get("name") for policy in policies_to_copy)
            for name in not_found:
                logger.warning(f"Policy '{name}' not found in source")
                self.skipped_policies.append((name, "Not found in source"))
                
        elif filter_criteria:
            # Filter by criteria
            for policy in source_policies:
                if self._matches_criteria(policy, filter_criteria):
                    policies_to_copy.append(policy)
            logger.info(f"Filter criteria matched {len(policies_to_copy)} policies")
        else:
            # Copy all policies
            policies_to_copy = source_policies
        
        # Copy each policy
        copied_count = 0
        total_count = len(policies_to_copy)
        
        logger.info(f"Attempting to copy {total_count} policies")
        
        for policy in policies_to_copy:
            name = policy.get("name")
            logger.debug(f"Processing policy: {name}")
            
            result = self.copy_policy(
                policy_type,
                name,
                source_context_type,
                target_context_type,
                skip_if_exists,
                copy_references,
                position="bottom",  # Default to adding at bottom
                conflict_strategy=conflict_strategy,
                **kwargs
            )
            
            if result:
                copied_count += 1
        
        logger.info(f"Copied {copied_count} of {total_count} policies")
        return copied_count, total_count
    
    def merge_all_policies(
        self,
        policy_types: List[str],
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        copy_references: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> Dict[str, Tuple[int, int]]:
        """
        Merge all policies of specified types from source to target.
        
        Args:
            policy_types: List of policy types to merge
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            skip_if_exists: Skip if policy already exists in target (deprecated, use conflict_strategy instead)
            copy_references: Copy object references (address objects, etc.)
            conflict_strategy: Strategy to use when resolving conflicts with existing policies
            **kwargs: Additional parameters (source_device_group, target_device_group, etc.)
            
        Returns:
            Dict: Dictionary mapping policy types to (copied, total) counts
        """
        logger.info(f"Merging all policies of types {policy_types} from {source_context_type} to {target_context_type}")
        
        results = {}
        
        for policy_type in policy_types:
            logger.info(f"Processing policy type: {policy_type}")
            
            copied, total = self.copy_policies(
                policy_type,
                source_context_type,
                target_context_type,
                None,  # No specific names, copy all
                None,  # No filter criteria
                skip_if_exists,
                copy_references,
                conflict_strategy=conflict_strategy,
                **kwargs
            )
            
            results[policy_type] = (copied, total)
            logger.info(f"Completed policy type {policy_type}: copied {copied} of {total}")
        
        # Calculate totals
        total_copied = sum(copied for copied, _ in results.values())
        total_attempted = sum(total for _, total in results.values())
        logger.info(f"Overall merge complete: copied {total_copied} of {total_attempted} policies across all types")
        
        return results
    
    def _extract_context_params(self, context_type: str, kwargs: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
        """Extract context parameters from kwargs with optional prefix."""
        params = {}
        
        try:
            if context_type == "device_group":
                key = f"{prefix}device_group"
                if key in kwargs:
                    params["device_group"] = kwargs[key]
                elif "device_group" in kwargs and not prefix:
                    params["device_group"] = kwargs["device_group"]
                    
            elif context_type == "vsys":
                key = f"{prefix}vsys"
                if key in kwargs:
                    params["vsys"] = kwargs[key]
                elif "vsys" in kwargs and not prefix:
                    params["vsys"] = kwargs["vsys"]
                    
            elif context_type == "template":
                key = f"{prefix}template"
                if key in kwargs:
                    params["template"] = kwargs[key]
                elif "template" in kwargs and not prefix:
                    params["template"] = kwargs["template"]
            
            logger.debug(f"Extracted context parameters for {context_type} with prefix '{prefix}': {params}")
            return params
        except Exception as e:
            logger.error(f"Error extracting context parameters for {context_type}: {e}", exc_info=True)
            return params
    
    def _matches_criteria(self, element: etree._Element, criteria: Dict[str, Any]) -> bool:
        """Check if an element matches the criteria."""
        try:
            element_name = element.get("name", "unknown")
            logger.debug(f"Checking if element '{element_name}' matches criteria")
            
            for key, value in criteria.items():
                # Handle XPath expressions in criteria
                if key.startswith('xpath:'):
                    xpath = key[6:]  # Remove 'xpath:' prefix
                    matches = element.xpath(xpath)
                    if not matches:
                        logger.debug(f"Element '{element_name}' does not match XPath criteria: {xpath}")
                        return False
                    continue
                    
                # Handle standard field matching
                if key == 'name':
                    if element.get('name') != value:
                        logger.debug(f"Element name mismatch: {element.get('name')} != {value}")
                        return False
                elif key == 'has-tag':
                    tag_elements = element.xpath('./tag/member')
                    tag_values = [tag.text for tag in tag_elements if tag.text]
                    if value not in tag_values:
                        logger.debug(f"Element '{element_name}' does not have required tag: {value}")
                        return False
                elif key in ['source', 'destination', 'service', 'application']:
                    # These are typically lists in policies
                    member_elements = element.xpath(f'./{key}/member')
                    member_values = [m.text for m in member_elements if m.text]
                    
                    if isinstance(value, list):
                        # Check if any of the criteria values are in the member list
                        if not any(v in member_values for v in value):
                            logger.debug(f"Element '{element_name}' {key} does not contain any of: {value}")
                            return False
                    else:
                        # Check if the criteria value is in the member list
                        if value not in member_values:
                            logger.debug(f"Element '{element_name}' {key} does not contain: {value}")
                            return False
                else:
                    # For other fields, check if they exist as child elements
                    child_elements = element.xpath(f'./{key}')
                    if not child_elements:
                        logger.debug(f"Element '{element_name}' does not have child element: {key}")
                        return False
                    
                    # If child element has text content, check that too
                    if child_elements[0].text and child_elements[0].text.strip() != str(value).strip():
                        logger.debug(f"Element '{element_name}' child {key} text mismatch: {child_elements[0].text} != {value}")
                        return False
            
            logger.debug(f"Element '{element_name}' matches all criteria")
            return True
        except Exception as e:
            logger.error(f"Error matching criteria: {e}", exc_info=True)
            return False
    
    def _add_policy_at_position(
        self,
        parent: etree._Element,
        policy: etree._Element,
        position: str,
        ref_policy_name: Optional[str] = None
    ) -> None:
        """Add a policy to a parent at the specified position."""
        policy_name = policy.get('name', 'unknown')
        
        try:
            if position == "top":
                # Insert at the beginning
                if len(parent) > 0:
                    parent.insert(0, policy)
                else:
                    parent.append(policy)
                logger.debug(f"Added policy '{policy_name}' at the top")
                
            elif position == "bottom":
                # Append at the end
                parent.append(policy)
                logger.debug(f"Added policy '{policy_name}' at the bottom")
                
            elif position in ("before", "after"):
                if not ref_policy_name:
                    logger.warning(f"Reference policy name is required for '{position}' operation, adding at bottom")
                    parent.append(policy)
                    return
                
                # Find the reference policy
                ref_index = None
                for i, child in enumerate(parent):
                    if child.tag == "entry" and child.get("name") == ref_policy_name:
                        ref_index = i
                        break
                
                if ref_index is None:
                    logger.warning(f"Reference policy '{ref_policy_name}' not found, adding at bottom")
                    parent.append(policy)
                    return
                
                # Insert before or after the reference policy
                if position == "before":
                    parent.insert(ref_index, policy)
                    logger.debug(f"Added policy '{policy_name}' before '{ref_policy_name}'")
                else:  # after
                    parent.insert(ref_index + 1, policy)
                    logger.debug(f"Added policy '{policy_name}' after '{ref_policy_name}'")
                    
            else:
                logger.warning(f"Invalid position '{position}', adding at bottom")
                parent.append(policy)
        except Exception as e:
            logger.error(f"Error adding policy '{policy_name}' at position {position}: {e}", exc_info=True)
            # Re-raise to allow caller to handle
            raise
    
    def _collect_policy_references(self, policy: etree._Element) -> None:
        """Collect object references from a policy."""
        policy_name = policy.get('name', 'unknown')
        logger.debug(f"Collecting references from policy: {policy_name}")
        
        try:
            # Collect address objects and groups
            for source in policy.xpath('./source/member'):
                if source.text and source.text != 'any':
                    self.object_references["address"].add(source.text)
                    self.object_references["address_group"].add(source.text)
                    logger.debug(f"Added source reference: {source.text}")
                    
            for dest in policy.xpath('./destination/member'):
                if dest.text and dest.text != 'any':
                    self.object_references["address"].add(dest.text)
                    self.object_references["address_group"].add(dest.text)
                    logger.debug(f"Added destination reference: {dest.text}")
                    
            # Collect service objects and groups
            for service in policy.xpath('./service/member'):
                if service.text and service.text not in ['any', 'application-default']:
                    self.object_references["service"].add(service.text)
                    self.object_references["service_group"].add(service.text)
                    logger.debug(f"Added service reference: {service.text}")
                    
            # Collect application groups
            for app in policy.xpath('./application/member'):
                if app.text and app.text != 'any':
                    self.object_references["application_group"].add(app.text)
                    logger.debug(f"Added application reference: {app.text}")
                    
            # Collect profile groups
            for profile in policy.xpath('./profile-setting/group/member'):
                if profile.text:
                    self.object_references["security_profile_group"].add(profile.text)
                    logger.debug(f"Added profile group reference: {profile.text}")
                    
            # Collect individual security profiles
            profile_setting = policy.find('./profile-setting')
            if profile_setting is not None:
                profiles_elem = profile_setting.find('./profiles')
                if profiles_elem is not None:
                    # Check for each security profile type
                    security_profile_types = [
                        "virus", "spyware", "vulnerability", "url-filtering", 
                        "file-blocking", "wildfire-analysis", "dns-security", "data-filtering"
                    ]
                    
                    for profile_type in security_profile_types:
                        profile_elem = profiles_elem.find(f'./{profile_type}')
                        if profile_elem is not None and profile_elem.text:
                            self.object_references[profile_type].add(profile_elem.text)
                            logger.debug(f"Added {profile_type} profile reference: {profile_elem.text}")
                            
            # Collect schedule reference
            schedule_elem = policy.find('./schedule')
            if schedule_elem is not None and schedule_elem.text:
                schedule_name = schedule_elem.text
                self.object_references["schedule"].add(schedule_name)
                logger.debug(f"Added schedule reference: {schedule_name}")
            
            # Collect URL category references
            for category in policy.xpath('./category/member'):
                if category.text:
                    self.object_references["custom-url-category"].add(category.text)
                    logger.debug(f"Added URL category reference: {category.text}")
                    
            # Collect tags
            for tag in policy.xpath('./tag/member'):
                if tag.text:
                    self.object_references["tag"].add(tag.text)
                    logger.debug(f"Added tag reference: {tag.text}")
            
            # Log summary of references
            reference_counts = {k: len(v) for k, v in self.object_references.items() if v}
            logger.debug(f"Collected references from policy '{policy_name}': {reference_counts}")
        except Exception as e:
            logger.error(f"Error collecting references from policy '{policy_name}': {e}", exc_info=True)
    
    def _copy_referenced_objects(
        self, 
        target_context_type: str, 
        source_context_type: str,
        **kwargs
    ) -> None:
        """Copy referenced objects to the target configuration."""
        logger.info("Copying referenced objects to target configuration")
        
        # Extract context parameters
        source_params = self._extract_context_params(source_context_type, kwargs, 'source_')
        target_params = self._extract_context_params(target_context_type, kwargs, 'target_')
        
        # Object types to copy
        object_types = {
            "address": "/address/entry[@name='{0}']",
            "address_group": "/address-group/entry[@name='{0}']",
            "service": "/service/entry[@name='{0}']",
            "service_group": "/service-group/entry[@name='{0}']",
            "application_group": "/application-group/entry[@name='{0}']",
            "security_profile_group": "/profile-group/entry[@name='{0}']",  # Using XML path 'profile-group' for backwards compatibility
            "virus": "/profiles/virus/entry[@name='{0}']",
            "spyware": "/profiles/spyware/entry[@name='{0}']",
            "vulnerability": "/profiles/vulnerability/entry[@name='{0}']",
            "url-filtering": "/profiles/url-filtering/entry[@name='{0}']",
            "file-blocking": "/profiles/file-blocking/entry[@name='{0}']",
            "wildfire-analysis": "/profiles/wildfire-analysis/entry[@name='{0}']",
            "dns-security": "/profiles/dns-security/entry[@name='{0}']",
            "data-filtering": "/profiles/data-filtering/entry[@name='{0}']",
            "schedule": "/schedule/entry[@name='{0}']",
            "custom-url-category": "/profiles/custom-url-category/entry[@name='{0}']",
            "tag": "/tag/entry[@name='{0}']"
        }
        
        # Get base XPaths
        from .xpath_resolver import get_context_xpath
        
        source_base = get_context_xpath(
            self.source_device_type,
            source_context_type,
            self.source_version,
            **source_params
        )
        
        target_base = get_context_xpath(
            self.target_device_type,
            target_context_type,
            self.target_version,
            **target_params
        )
        
        logger.debug(f"Source base path: {source_base}")
        logger.debug(f"Target base path: {target_base}")
        
        # Process each object type
        for obj_type, xpath_pattern in object_types.items():
            # Skip if no references of this type
            if not self.object_references[obj_type]:
                logger.debug(f"No references of type {obj_type} to copy")
                continue
                
            logger.info(f"Processing {len(self.object_references[obj_type])} references of type {obj_type}")
                
            # Create parent path in target if it doesn't exist
            target_parent_path = target_base + "/" + xpath_pattern.split("/")[1]
            target_parent_elements = xpath_search(self.target_tree, target_parent_path)
            
            if not target_parent_elements:
                # Need to create the parent element
                logger.debug(f"Creating parent element at {target_parent_path}")
                try:
                    parent_parts = target_parent_path.strip('/').split('/')
                    current = self.target_tree.getroot()
                    
                    for part in parent_parts:
                        # Check if element exists
                        child = None
                        for c in current:
                            if c.tag == part.split('[')[0]:  # Handle predicates
                                child = c
                                break
                                
                        if child is None:
                            # Create new element
                            child = etree.SubElement(current, part.split('[')[0])
                            
                        current = child
                        
                    target_parent = current
                except Exception as e:
                    logger.error(f"Failed to create parent path {target_parent_path}: {e}", exc_info=True)
                    continue
            else:
                target_parent = target_parent_elements[0]
            
            # Copy each referenced object
            for obj_name in self.object_references[obj_type]:
                # Check if object exists in source
                source_xpath = source_base + xpath_pattern.format(obj_name)
                source_objs = xpath_search(self.source_tree, source_xpath)
                
                if not source_objs:
                    logger.warning(f"{obj_type} '{obj_name}' not found in source")
                    continue
                    
                source_obj = source_objs[0]
                
                # Check if object exists in target
                target_xpath = target_base + xpath_pattern.format(obj_name)
                target_objs = xpath_search(self.target_tree, target_xpath)
                
                if target_objs:
                    logger.debug(f"{obj_type} '{obj_name}' already exists in target, skipping")
                    continue
                    
                # Copy object to target
                try:
                    new_obj = clone_element(source_obj)
                    target_parent.append(new_obj)
                    
                    self.copied_objects.append((obj_type, obj_name))
                    logger.info(f"Copied {obj_type} '{obj_name}' to target")
                    
                    # If this is a group, collect its members for recursive copying
                    if obj_type.endswith('_group'):
                        for member in new_obj.xpath('./static/member'):
                            if member.text:
                                # Add group members to references
                                base_type = obj_type.replace('_group', '')
                                self.object_references[base_type].add(member.text)
                                logger.debug(f"Added member reference from group: {member.text}")
                                # Groups can also refer to other groups
                                self.object_references[obj_type].add(member.text)
                except Exception as e:
                    logger.error(f"Error copying {obj_type} '{obj_name}': {e}", exc_info=True)
        
        # Recursively copy any new references
        new_references = False
        for ref_set in self.object_references.values():
            if ref_set:
                new_references = True
                break
                
        if new_references:
            # Create copies of the sets to avoid modification during iteration
            old_refs = {k: set(v) for k, v in self.object_references.items()}
            
            # Clear current references to avoid duplication
            for k in self.object_references:
                self.object_references[k].clear()
                
            # Recursively copy any new references we found
            logger.debug("Recursively copying newly discovered references")
            self._copy_referenced_objects(target_context_type, source_context_type, **kwargs)
            
            # Restore any references we haven't processed yet
            for k, v in old_refs.items():
                self.object_references[k].update(v)
                
    def _handle_version_specific_attributes(
        self,
        policy_element: etree._Element,
        policy_type: str
    ) -> etree._Element:
        """
        Handle version-specific attributes for policies being copied between different PAN-OS versions.
        
        This method checks for attributes that may be available in the source version but not in
        the target version, or vice versa. It modifies the policy as needed to ensure compatibility
        with the target version.
        
        Args:
            policy_element: The XML element of the policy to process
            policy_type: The type of policy (security, nat, etc.)
            
        Returns:
            etree._Element: The modified policy element
        """
        policy_name = policy_element.get("name", "unknown")
        logger.debug(f"Handling version-specific attributes for {policy_type} policy '{policy_name}'")
        
        # Normalize policy type to match keys in VERSION_SPECIFIC_ATTRIBUTES
        if policy_type == "security_pre_rules" or policy_type == "security_post_rules" or policy_type == "security_rules":
            policy_type_normalized = "security"
        elif policy_type == "nat_pre_rules" or policy_type == "nat_post_rules" or policy_type == "nat_rules":
            policy_type_normalized = "nat"
        elif policy_type == "pbf_pre_rules" or policy_type == "pbf_post_rules" or policy_type == "pbf_rules":
            policy_type_normalized = "pbf"
        elif policy_type == "decryption_pre_rules" or policy_type == "decryption_post_rules" or policy_type == "decryption_rules":
            policy_type_normalized = "decryption"
        else:
            logger.warning(f"Unknown policy type '{policy_type}', applying default handling")
            policy_type_normalized = "security"  # Default to security rules
        
        # If we have version-specific definitions for this policy type
        if policy_type_normalized in self.VERSION_SPECIFIC_ATTRIBUTES:
            attributes = self.VERSION_SPECIFIC_ATTRIBUTES[policy_type_normalized]
            
            # When copying from newer to older version, remove attributes not supported in target version
            if self.source_version > self.target_version:
                # Go through all attributes defined for this policy type
                for attr_name, attr_versions in attributes.items():
                    # Check if attribute is supported in newer (source) but not in older (target) version
                    if (self.source_version in attr_versions and attr_versions[self.source_version] is not None and
                        (self.target_version not in attr_versions or attr_versions[self.target_version] is None)):
                        
                        # Find all elements with this attribute name
                        attr_elements = policy_element.findall(f'./{attr_name}')
                        for elem in attr_elements:
                            if elem is not None and elem.getparent() is not None:
                                logger.debug(f"Removing newer attribute '{attr_name}' from {policy_type} '{policy_name}'")
                                elem.getparent().remove(elem)
            
            # Handle specific version transitions
            if self.source_version == "11.2" and self.target_version == "10.2":
                self._handle_11_2_to_10_2_changes(policy_element, policy_type_normalized)
            elif self.source_version == "11.2" and self.target_version == "10.1":
                self._handle_11_2_to_10_1_changes(policy_element, policy_type_normalized)
            elif self.source_version == "10.2" and self.target_version == "10.1":
                self._handle_10_2_to_10_1_changes(policy_element, policy_type_normalized)
        
        return policy_element
    
    def _handle_11_2_to_10_2_changes(self, policy_element: etree._Element, policy_type: str) -> None:
        """Handle specific changes when going from PAN-OS 11.2 to 10.2."""
        policy_name = policy_element.get("name", "unknown")
        
        if policy_type == "security":
            # Remove elements specific to 11.x
            for element_name in ["ssl-decrypt-mirror", "url-category-match", "rule-type"]:
                elem = policy_element.find(f'./{element_name}')
                if elem is not None and elem.getparent() is not None:
                    logger.debug(f"Removing 11.x element '{element_name}' from security rule '{policy_name}'")
                    elem.getparent().remove(elem)
        
        elif policy_type == "decryption":
            # Remove elements specific to 11.x
            elem = policy_element.find('./tls13-action')
            if elem is not None and elem.getparent() is not None:
                logger.debug(f"Removing 11.x element 'tls13-action' from decryption rule '{policy_name}'")
                elem.getparent().remove(elem)
    
    def _handle_11_2_to_10_1_changes(self, policy_element: etree._Element, policy_type: str) -> None:
        """Handle specific changes when going from PAN-OS 11.2 to 10.1."""
        policy_name = policy_element.get("name", "unknown")
        
        # First apply 11.2 to 10.2 changes
        self._handle_11_2_to_10_2_changes(policy_element, policy_type)
        
        # Then apply additional changes specific to 10.1
        if policy_type == "security":
            # Remove elements specific to 10.2+
            elem = policy_element.find('./disable-server-response-inspection')
            if elem is not None and elem.getparent() is not None:
                logger.debug(f"Removing 10.2+ element 'disable-server-response-inspection' from security rule '{policy_name}'")
                elem.getparent().remove(elem)
        
        elif policy_type == "nat":
            # Handle fallback which became required in 10.2+
            fallback_elem = policy_element.find('./fallback')
            if fallback_elem is None:
                logger.debug(f"Adding required 'fallback' element for NAT rule '{policy_name}' in 10.1")
                fallback = etree.SubElement(policy_element, "fallback")
                fallback.text = "none"
                
        elif policy_type == "pbf":
            # Remove elements specific to 10.2+
            elem = policy_element.find('./symmetric-return-addresses')
            if elem is not None and elem.getparent() is not None:
                logger.debug(f"Removing 10.2+ element 'symmetric-return-addresses' from PBF rule '{policy_name}'")
                elem.getparent().remove(elem)
                
        elif policy_type == "decryption":
            # Remove elements specific to 10.2+
            elem = policy_element.find('./ssl-protocol-version-min')
            if elem is not None and elem.getparent() is not None:
                logger.debug(f"Removing 10.2+ element 'ssl-protocol-version-min' from decryption rule '{policy_name}'")
                elem.getparent().remove(elem)
    
    def _handle_10_2_to_10_1_changes(self, policy_element: etree._Element, policy_type: str) -> None:
        """Handle specific changes when going from PAN-OS 10.2 to 10.1."""
        policy_name = policy_element.get("name", "unknown")
        
        if policy_type == "security":
            # Remove elements specific to 10.2+
            elem = policy_element.find('./disable-server-response-inspection')
            if elem is not None and elem.getparent() is not None:
                logger.debug(f"Removing 10.2+ element 'disable-server-response-inspection' from security rule '{policy_name}'")
                elem.getparent().remove(elem)
        
        elif policy_type == "nat":
            # Handle fallback which became required in 10.2+
            fallback_elem = policy_element.find('./fallback')
            if fallback_elem is None:
                logger.debug(f"Adding required 'fallback' element for NAT rule '{policy_name}' in 10.1")
                fallback = etree.SubElement(policy_element, "fallback")
                fallback.text = "none"
                
        elif policy_type == "pbf":
            # Remove elements specific to 10.2+
            elem = policy_element.find('./symmetric-return-addresses')
            if elem is not None and elem.getparent() is not None:
                logger.debug(f"Removing 10.2+ element 'symmetric-return-addresses' from PBF rule '{policy_name}'")
                elem.getparent().remove(elem)
                
        elif policy_type == "decryption":
            # Remove elements specific to 10.2+
            elem = policy_element.find('./ssl-protocol-version-min')
            if elem is not None and elem.getparent() is not None:
                logger.debug(f"Removing 10.2+ element 'ssl-protocol-version-min' from decryption rule '{policy_name}'")
                elem.getparent().remove(elem)