"""
Policy merger for PAN-OS XML utilities.

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

logger = logging.getLogger("panflow")

class PolicyMerger:
    """
    Class for merging policies between PAN-OS configurations.
    
    Provides methods for copying policies from one configuration to another,
    with options to handle conflicts and dependencies.
    """
    
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
        self.source_tree = source_tree
        self.target_tree = target_tree if target_tree is not None else source_tree
        self.source_device_type = source_device_type.lower()
        self.target_device_type = target_device_type.lower() if target_device_type else source_device_type.lower()
        self.source_version = source_version
        self.target_version = target_version if target_version else source_version
        
        # Object references to track
        self.object_references = {
            "address": set(),
            "address_group": set(),
            "service": set(),
            "service_group": set(),
            "application_group": set(),
            "security_profile_group": set(),
            "tag": set()
        }
        
        # Track modifications
        self.merged_policies = []
        self.skipped_policies = []
        self.copied_objects = []
    
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
        **kwargs
    ) -> bool:
        """
        Copy a single policy from source to target.
        
        Args:
            policy_type: Type of policy (security_pre_rules, nat_rules, etc.)
            policy_name: Name of the policy to copy
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            skip_if_exists: Skip if policy already exists in target
            copy_references: Copy object references (address objects, etc.)
            position: Where to place the policy ("top", "bottom", "before", "after")
            ref_policy_name: Reference policy name for "before" and "after" positions
            **kwargs: Additional parameters (source_device_group, target_device_group, etc.)
            
        Returns:
            bool: Success status
        """
        # Extract context parameters
        source_params = self._extract_context_params(source_context_type, kwargs, 'source_')
        target_params = self._extract_context_params(target_context_type, kwargs, 'target_')
        
        # Get the source policy
        source_xpath = get_policy_xpath(
            policy_type, 
            self.source_device_type, 
            source_context_type, 
            self.source_version, 
            policy_name, 
            **source_params
        )
        
        source_elements = xpath_search(self.source_tree, source_xpath)
        if not source_elements:
            logger.error(f"Policy '{policy_name}' not found in source")
            self.skipped_policies.append((policy_name, "Not found in source"))
            return False
        
        source_policy = source_elements[0]
        
        # Check if policy exists in target
        target_xpath = get_policy_xpath(
            policy_type, 
            self.target_device_type, 
            target_context_type, 
            self.target_version, 
            policy_name, 
            **target_params
        )
        
        target_elements = xpath_search(self.target_tree, target_xpath)
        if target_elements:
            if skip_if_exists:
                logger.warning(f"Policy '{policy_name}' already exists in target, skipping")
                self.skipped_policies.append((policy_name, "Already exists in target"))
                return False
            else:
                # Remove existing policy
                parent = target_elements[0].getparent()
                parent.remove(target_elements[0])
                logger.info(f"Removed existing policy '{policy_name}' from target")
        
        # Get the target parent element
        target_parent_xpath = get_policy_xpath(
            policy_type, 
            self.target_device_type, 
            target_context_type, 
            self.target_version, 
            **target_params
        )
        
        target_parent_elements = xpath_search(self.target_tree, target_parent_xpath)
        if not target_parent_elements:
            logger.error(f"Target parent element not found for policy '{policy_name}'")
            self.skipped_policies.append((policy_name, "Target parent element not found"))
            return False
        
        target_parent = target_parent_elements[0]
        
        # Create a copy of the source policy
        new_policy = clone_element(source_policy)
        
        # Collect references before adding to target
        if copy_references:
            self._collect_policy_references(new_policy)
        
        # Add the policy to the target at the specified position
        self._add_policy_at_position(
            target_parent, 
            new_policy, 
            position, 
            ref_policy_name
        )
        
        # Copy referenced objects if requested
        if copy_references:
            self._copy_referenced_objects(target_context_type, source_context_type, **kwargs)
        
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
            skip_if_exists: Skip if policy already exists in target
            copy_references: Copy object references (address objects, etc.)
            **kwargs: Additional parameters (source_device_group, target_device_group, etc.)
            
        Returns:
            Tuple[int, int]: (number of policies copied, total number of policies attempted)
        """
        # Extract context parameters
        source_params = self._extract_context_params(source_context_type, kwargs, 'source_')
        
        # Get the source policies
        source_base_xpath = get_policy_xpath(
            policy_type, 
            self.source_device_type, 
            source_context_type, 
            self.source_version, 
            **source_params
        )
        
        source_policies = xpath_search(self.source_tree, source_base_xpath + "/entry")
        
        if not source_policies:
            logger.warning(f"No policies found in source matching the criteria")
            return 0, 0
        
        # Filter policies if needed
        policies_to_copy = []
        
        if policy_names:
            # Filter by name
            for policy in source_policies:
                name = policy.get("name")
                if name in policy_names:
                    policies_to_copy.append(policy)
            
            not_found = set(policy_names) - set(p.get("name") for p in policies_to_copy)
            for name in not_found:
                logger.warning(f"Policy '{name}' not found in source")
                self.skipped_policies.append((name, "Not found in source"))
                
        elif filter_criteria:
            # Filter by criteria
            for policy in source_policies:
                if self._matches_criteria(policy, filter_criteria):
                    policies_to_copy.append(policy)
        else:
            # Copy all policies
            policies_to_copy = source_policies
        
        # Copy each policy
        copied_count = 0
        total_count = len(policies_to_copy)
        
        for policy in policies_to_copy:
            name = policy.get("name")
            result = self.copy_policy(
                policy_type,
                name,
                source_context_type,
                target_context_type,
                skip_if_exists,
                copy_references,
                position="bottom",  # Default to adding at bottom
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
        **kwargs
    ) -> Dict[str, Tuple[int, int]]:
        """
        Merge all policies of specified types from source to target.
        
        Args:
            policy_types: List of policy types to merge
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            skip_if_exists: Skip if policy already exists in target
            copy_references: Copy object references (address objects, etc.)
            **kwargs: Additional parameters (source_device_group, target_device_group, etc.)
            
        Returns:
            Dict: Dictionary mapping policy types to (copied, total) counts
        """
        results = {}
        
        for policy_type in policy_types:
            copied, total = self.copy_policies(
                policy_type,
                source_context_type,
                target_context_type,
                None,  # No specific names, copy all
                None,  # No filter criteria
                skip_if_exists,
                copy_references,
                **kwargs
            )
            
            results[policy_type] = (copied, total)
        
        return results
    
    def _extract_context_params(self, context_type: str, kwargs: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
        """Extract context parameters from kwargs with optional prefix."""
        params = {}
        
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
        
        return params
    
    def _matches_criteria(self, element: etree._Element, criteria: Dict[str, Any]) -> bool:
        """Check if an element matches the criteria."""
        for key, value in criteria.items():
            # Handle XPath expressions in criteria
            if key.startswith('xpath:'):
                xpath = key[6:]  # Remove 'xpath:' prefix
                matches = element.xpath(xpath)
                if not matches:
                    return False
                continue
                
            # Handle standard field matching
            if key == 'name':
                if element.get('name') != value:
                    return False
            elif key == 'has-tag':
                tag_elements = element.xpath('./tag/member')
                tag_values = [tag.text for tag in tag_elements if tag.text]
                if value not in tag_values:
                    return False
            elif key in ['source', 'destination', 'service', 'application']:
                # These are typically lists in policies
                member_elements = element.xpath(f'./{key}/member')
                member_values = [m.text for m in member_elements if m.text]
                
                if isinstance(value, list):
                    # Check if any of the criteria values are in the member list
                    if not any(v in member_values for v in value):
                        return False
                else:
                    # Check if the criteria value is in the member list
                    if value not in member_values:
                        return False
            else:
                # For other fields, check if they exist as child elements
                child_elements = element.xpath(f'./{key}')
                if not child_elements:
                    return False
                
                # If child element has text content, check that too
                if child_elements[0].text and child_elements[0].text.strip() != str(value).strip():
                    return False
        
        return True
    
    def _add_policy_at_position(
        self,
        parent: etree._Element,
        policy: etree._Element,
        position: str,
        ref_policy_name: Optional[str] = None
    ) -> None:
        """Add a policy to a parent at the specified position."""
        if position == "top":
            # Insert at the beginning
            if len(parent) > 0:
                parent.insert(0, policy)
            else:
                parent.append(policy)
            logger.debug(f"Added policy '{policy.get('name')}' at the top")
            
        elif position == "bottom":
            # Append at the end
            parent.append(policy)
            logger.debug(f"Added policy '{policy.get('name')}' at the bottom")
            
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
                logger.debug(f"Added policy '{policy.get('name')}' before '{ref_policy_name}'")
            else:  # after
                parent.insert(ref_index + 1, policy)
                logger.debug(f"Added policy '{policy.get('name')}' after '{ref_policy_name}'")
                
        else:
            logger.warning(f"Invalid position '{position}', adding at bottom")
            parent.append(policy)
    
    def _collect_policy_references(self, policy: etree._Element) -> None:
        """Collect object references from a policy."""
        # Collect address objects and groups
        for source in policy.xpath('./source/member'):
            if source.text and source.text != 'any':
                self.object_references["address"].add(source.text)
                self.object_references["address_group"].add(source.text)
                
        for dest in policy.xpath('./destination/member'):
            if dest.text and dest.text != 'any':
                self.object_references["address"].add(dest.text)
                self.object_references["address_group"].add(dest.text)
                
        # Collect service objects and groups
        for service in policy.xpath('./service/member'):
            if service.text and service.text not in ['any', 'application-default']:
                self.object_references["service"].add(service.text)
                self.object_references["service_group"].add(service.text)
                
        # Collect application groups
        for app in policy.xpath('./application/member'):
            if app.text and app.text != 'any':
                self.object_references["application_group"].add(app.text)
                
        # Collect profile groups
        for profile in policy.xpath('./profile-setting/group/member'):
            if profile.text:
                self.object_references["security_profile_group"].add(profile.text)
                
        # Collect tags
        for tag in policy.xpath('./tag/member'):
            if tag.text:
                self.object_references["tag"].add(tag.text)
    
    def _copy_referenced_objects(
        self, 
        target_context_type: str, 
        source_context_type: str,
        **kwargs
    ) -> None:
        """Copy referenced objects to the target configuration."""
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
            "security_profile_group": "/profile-group/entry[@name='{0}']",
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
        
        # Process each object type
        for obj_type, xpath_pattern in object_types.items():
            # Skip if no references of this type
            if not self.object_references[obj_type]:
                continue
                
            # Create parent path in target if it doesn't exist
            target_parent_path = target_base + "/" + xpath_pattern.split("/")[1]
            target_parent_elements = xpath_search(self.target_tree, target_parent_path)
            
            if not target_parent_elements:
                # Need to create the parent element
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
            else:
                target_parent = target_parent_elements[0]
            
            # Copy each referenced object
            for obj_name in self.object_references[obj_type]:
                # Check if object exists in source
                source_xpath = source_base + xpath_pattern.format(obj_name)
                source_objs = xpath_search(self.source_tree, source_xpath)
                
                if not source_objs:
                    continue  # Object not found in source
                    
                source_obj = source_objs[0]
                
                # Check if object exists in target
                target_xpath = target_base + xpath_pattern.format(obj_name)
                target_objs = xpath_search(self.target_tree, target_xpath)
                
                if target_objs:
                    # Object already exists in target, skip
                    continue
                    
                # Copy object to target
                new_obj = clone_element(source_obj)
                target_parent.append(new_obj)
                
                self.copied_objects.append((obj_type, obj_name))
                logger.debug(f"Copied {obj_type} '{obj_name}' to target")
                
                # If this is a group, collect its members for recursive copying
                if obj_type.endswith('_group'):
                    for member in new_obj.xpath('./static/member'):
                        if member.text:
                            # Add group members to references
                            base_type = obj_type.replace('_group', '')
                            self.object_references[base_type].add(member.text)
                            # Groups can also refer to other groups
                            self.object_references[obj_type].add(member.text)
        
        # Recursively copy any new references
        if any(self.object_references.values()):
            # Create copies of the sets to avoid modification during iteration
            old_refs = {k: set(v) for k, v in self.object_references.items()}
            
            # Clear current references to avoid duplication
            for k in self.object_references:
                self.object_references[k].clear()
                
            # Recursively copy any new references we found
            self._copy_referenced_objects(target_context_type, source_context_type, **kwargs)
            
            # Restore any references we haven't processed yet
            for k, v in old_refs.items():
                self.object_references[k].update(v)