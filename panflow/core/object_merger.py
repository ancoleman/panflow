"""
Object merger for PAN-OS XML utilities.

This module provides functionality for merging objects between different configurations,
device groups, or virtual systems.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Set
from lxml import etree
import copy

from .xpath_resolver import get_object_xpath, get_context_xpath
from .config_loader import xpath_search
from .xml_utils import clone_element, merge_elements

logger = logging.getLogger("panflow")

class ObjectMerger:
    """
    Class for merging objects between PAN-OS configurations.
    
    Provides methods for copying objects from one configuration to another,
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
            source_tree: Source ElementTree containing objects to copy
            target_tree: Target ElementTree to merge objects into (can be the same as source_tree)
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
        
        # Track modifications
        self.merged_objects = []
        self.skipped_objects = []
        self.referenced_objects = []
    
    def copy_object(
        self,
        object_type: str,
        object_name: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        copy_references: bool = True,
        **kwargs
    ) -> bool:
        """
        Copy a single object from source to target.
        
        Args:
            object_type: Type of object (address, service, etc.)
            object_name: Name of the object to copy
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            skip_if_exists: Skip if object already exists in target
            copy_references: Copy object references (e.g., address group members)
            **kwargs: Additional parameters (source_device_group, target_device_group, etc.)
            
        Returns:
            bool: Success status
        """
        # Extract context parameters
        source_params = self._extract_context_params(source_context_type, kwargs, 'source_')
        target_params = self._extract_context_params(target_context_type, kwargs, 'target_')
        
        # Get the source object
        source_xpath = get_object_xpath(
            object_type, 
            self.source_device_type, 
            source_context_type, 
            self.source_version, 
            object_name, 
            **source_params
        )
        
        source_elements = xpath_search(self.source_tree, source_xpath)
        if not source_elements:
            logger.error(f"Object '{object_name}' not found in source")
            self.skipped_objects.append((object_type, object_name, "Not found in source"))
            return False
        
        source_object = source_elements[0]
        
        # Check if object exists in target
        target_xpath = get_object_xpath(
            object_type, 
            self.target_device_type, 
            target_context_type, 
            self.target_version, 
            object_name, 
            **target_params
        )
        
        target_elements = xpath_search(self.target_tree, target_xpath)
        if target_elements:
            if skip_if_exists:
                logger.warning(f"Object '{object_name}' already exists in target, skipping")
                self.skipped_objects.append((object_type, object_name, "Already exists in target"))
                return False
            else:
                # Remove existing object
                parent = target_elements[0].getparent()
                parent.remove(target_elements[0])
                logger.info(f"Removed existing object '{object_name}' from target")
        
        # Get the target parent element
        target_parent_xpath = get_object_xpath(
            object_type, 
            self.target_device_type, 
            target_context_type, 
            self.target_version, 
            **target_params
        )
        
        # Split to get parent path
        parent_parts = target_parent_xpath.rsplit('/', 1)
        if len(parent_parts) < 2:
            logger.error(f"Invalid target parent path: {target_parent_xpath}")
            self.skipped_objects.append((object_type, object_name, "Invalid target parent path"))
            return False
            
        target_parent_xpath = parent_parts[0]
        
        target_parent_elements = xpath_search(self.target_tree, target_parent_xpath)
        if not target_parent_elements:
            # Try to create the parent structure
            logger.info(f"Target parent element not found, attempting to create it")
            target_parent = self._create_parent_path(target_parent_xpath)
            if target_parent is None:
                logger.error(f"Failed to create target parent path for object '{object_name}'")
                self.skipped_objects.append((object_type, object_name, "Failed to create target parent path"))
                return False
        else:
            target_parent = target_parent_elements[0]
        
        # Create a copy of the source object
        new_object = clone_element(source_object)
        
        # Add the object to the target
        target_parent.append(new_object)
        
        # Add to merged objects list
        self.merged_objects.append((object_type, object_name))
        logger.info(f"Successfully copied {object_type} object '{object_name}' to target")
        
        # Collect and copy references if requested
        if copy_references and object_type.endswith('_group'):
            self._copy_group_members(
                new_object, 
                object_type, 
                source_context_type, 
                target_context_type, 
                skip_if_exists, 
                **kwargs
            )
        
        return True
    
    def copy_objects(
        self,
        object_type: str,
        source_context_type: str,
        target_context_type: str,
        object_names: Optional[List[str]] = None,
        filter_criteria: Optional[Dict[str, Any]] = None,
        skip_if_exists: bool = True,
        copy_references: bool = True,
        **kwargs
    ) -> Tuple[int, int]:
        """
        Copy multiple objects from source to target.
        
        Args:
            object_type: Type of object (address, service, etc.)
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            object_names: List of object names to copy (if None, use filter_criteria)
            filter_criteria: Dictionary of criteria to select objects
            skip_if_exists: Skip if object already exists in target
            copy_references: Copy object references (e.g., address group members)
            **kwargs: Additional parameters (source_device_group, target_device_group, etc.)
            
        Returns:
            Tuple[int, int]: (number of objects copied, total number of objects attempted)
        """
        # Extract context parameters
        source_params = self._extract_context_params(source_context_type, kwargs, 'source_')
        
        # Get the source objects
        source_base_xpath = get_object_xpath(
            object_type, 
            self.source_device_type, 
            source_context_type, 
            self.source_version, 
            **source_params
        )
        
        source_objects = xpath_search(self.source_tree, source_base_xpath + "/entry")
        
        if not source_objects:
            logger.warning(f"No {object_type} objects found in source matching the criteria")
            return 0, 0
        
        # Filter objects if needed
        objects_to_copy = []
        
        if object_names:
            # Filter by name
            for obj in source_objects:
                name = obj.get("name")
                if name in object_names:
                    objects_to_copy.append(obj)
            
            not_found = set(object_names) - set(obj.get("name") for obj in objects_to_copy)
            for name in not_found:
                logger.warning(f"{object_type} object '{name}' not found in source")
                self.skipped_objects.append((object_type, name, "Not found in source"))
                
        elif filter_criteria:
            # Filter by criteria
            for obj in source_objects:
                if self._matches_criteria(obj, filter_criteria):
                    objects_to_copy.append(obj)
        else:
            # Copy all objects
            objects_to_copy = source_objects
        
        # Copy each object
        copied_count = 0
        total_count = len(objects_to_copy)
        
        for obj in objects_to_copy:
            name = obj.get("name")
            result = self.copy_object(
                object_type,
                name,
                source_context_type,
                target_context_type,
                skip_if_exists,
                copy_references,
                **kwargs
            )
            
            if result:
                copied_count += 1
        
        logger.info(f"Copied {copied_count} of {total_count} {object_type} objects")
        return copied_count, total_count
    
    def merge_all_objects(
        self,
        object_types: List[str],
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        copy_references: bool = True,
        **kwargs
    ) -> Dict[str, Tuple[int, int]]:
        """
        Merge all objects of specified types from source to target.
        
        Args:
            object_types: List of object types to merge
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            skip_if_exists: Skip if object already exists in target
            copy_references: Copy object references (e.g., address group members)
            **kwargs: Additional parameters (source_device_group, target_device_group, etc.)
            
        Returns:
            Dict: Dictionary mapping object types to (copied, total) counts
        """
        results = {}
        
        for object_type in object_types:
            copied, total = self.copy_objects(
                object_type,
                source_context_type,
                target_context_type,
                None,  # No specific names, copy all
                None,  # No filter criteria
                skip_if_exists,
                copy_references,
                **kwargs
            )
            
            results[object_type] = (copied, total)
        
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
            elif key == 'type':
                # Check specific object types
                if key == 'ip-netmask' and not element.xpath('./ip-netmask'):
                    return False
                if key == 'fqdn' and not element.xpath('./fqdn'):
                    return False
                if key == 'ip-range' and not element.xpath('./ip-range'):
                    return False
            elif key == 'value':
                # Match object value (ip, fqdn, etc.)
                for value_key in ['ip-netmask', 'fqdn', 'ip-range']:
                    elements = element.xpath(f'./{value_key}')
                    if elements and elements[0].text:
                        if elements[0].text != value:
                            return False
                        break
            else:
                # For other fields, check if they exist as child elements
                child_elements = element.xpath(f'./{key}')
                if not child_elements:
                    return False
                
                # If child element has text content, check that too
                if value is not None and child_elements[0].text and child_elements[0].text.strip() != str(value).strip():
                    return False
        
        return True
    
    def _create_parent_path(self, path: str) -> Optional[etree._Element]:
        """Create the parent path in the target configuration if it doesn't exist."""
        parts = path.strip('/').split('/')
        current = self.target_tree.getroot()
        
        for i, part in enumerate(parts):
            # Parse the tag and predicates
            if '[' in part:
                tag = part.split('[')[0]
                predicate = part[part.index('['):]
            else:
                tag = part
                predicate = ""
            
            # See if the element already exists
            xpath = "/" + "/".join(parts[:i+1])
            elements = xpath_search(self.target_tree, xpath)
            
            if elements:
                current = elements[0]
            else:
                # Need to create this element
                # If it has a predicate with name, extract it
                name = None
                if predicate and "[@name=" in predicate:
                    # Extract name from [@name='value']
                    name_start = predicate.index("'") + 1
                    name_end = predicate.rindex("'")
                    name = predicate[name_start:name_end]
                
                # Create the element
                if name:
                    new_elem = etree.SubElement(current, tag, {"name": name})
                else:
                    new_elem = etree.SubElement(current, tag)
                
                current = new_elem
        
        return current
    
    def _copy_group_members(
        self,
        group_element: etree._Element,
        group_type: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool,
        **kwargs
    ) -> None:
        """Copy members of a group object."""
        # Determine the base object type from the group type
        if group_type == "address_group":
            member_type = "address"
        elif group_type == "service_group":
            member_type = "service"
        elif group_type == "application_group":
            member_type = "application"
        else:
            logger.warning(f"Unsupported group type for member copying: {group_type}")
            return
        
        # For static groups, copy the members
        static_elements = group_element.xpath('./static/member')
        if static_elements:
            for member_elem in static_elements:
                if member_elem.text:
                    member_name = member_elem.text
                    
                    # Avoid infinite recursion by checking if we've already copied this object
                    if (member_type, member_name) not in self.merged_objects and (member_type, member_name) not in self.referenced_objects:
                        # Track this reference
                        self.referenced_objects.append((member_type, member_name))
                        
                        # Try to copy the member object
                        self.copy_object(
                            member_type,
                            member_name,
                            source_context_type,
                            target_context_type,
                            skip_if_exists,
                            True,  # copy_references
                            **kwargs
                        )
                        
                        # Also check for groups (the member might be a group)
                        self.copy_object(
                            f"{member_type}_group",
                            member_name,
                            source_context_type,
                            target_context_type,
                            skip_if_exists,
                            True,  # copy_references
                            **kwargs
                        )