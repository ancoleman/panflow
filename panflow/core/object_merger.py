"""
Object merger for PANFlow.

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

# Initialize logger
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
        logger.info("Initializing ObjectMerger")
        self.source_tree = source_tree
        self.target_tree = target_tree if target_tree is not None else source_tree
        self.source_device_type = source_device_type.lower()
        self.target_device_type = target_device_type.lower() if target_device_type else source_device_type.lower()
        self.source_version = source_version
        self.target_version = target_version if target_version else source_version
        
        logger.debug(f"Source: {self.source_device_type} (version {self.source_version})")
        logger.debug(f"Target: {self.target_device_type} (version {self.target_version})")
        logger.debug(f"Using same tree for source and target: {self.source_tree is self.target_tree}")
        
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
        # Validate required parameters
        if not object_type:
            logger.error("Object type cannot be empty")
            self.skipped_objects.append((object_type, object_name, "Invalid object type"))
            return False
            
        if not object_name:
            logger.error("Object name cannot be empty")
            self.skipped_objects.append((object_type, object_name, "Invalid object name"))
            return False
        
        # Validate context types
        valid_contexts = ["shared", "device_group", "vsys", "template"]
        if source_context_type not in valid_contexts:
            logger.error(f"Invalid source context type: {source_context_type}")
            self.skipped_objects.append((object_type, object_name, f"Invalid source context: {source_context_type}"))
            return False
            
        if target_context_type not in valid_contexts:
            logger.error(f"Invalid target context type: {target_context_type}")
            self.skipped_objects.append((object_type, object_name, f"Invalid target context: {target_context_type}"))
            return False
        
        # Validate context parameters
        if source_context_type == "device_group" and "source_device_group" not in kwargs:
            logger.error("source_device_group parameter is required for device_group context")
            self.skipped_objects.append((object_type, object_name, "Missing source_device_group parameter"))
            return False
            
        if target_context_type == "device_group" and "target_device_group" not in kwargs:
            logger.error("target_device_group parameter is required for device_group context")
            self.skipped_objects.append((object_type, object_name, "Missing target_device_group parameter"))
            return False
        
        logger.info(f"Copying {object_type} object '{object_name}' from {source_context_type} to {target_context_type}")
        logger.debug(f"Copy parameters: skip_if_exists={skip_if_exists}, copy_references={copy_references}")
        
        # Extract context parameters
        source_params = self._extract_context_params(source_context_type, kwargs, 'source_')
        target_params = self._extract_context_params(target_context_type, kwargs, 'target_')
        
        logger.debug(f"Source parameters: {source_params}")
        logger.debug(f"Target parameters: {target_params}")
        
        # Get the source object
        try:
            source_xpath = get_object_xpath(
                object_type, 
                self.source_device_type, 
                source_context_type, 
                self.source_version, 
                object_name, 
                **source_params
            )
            
            logger.debug(f"Looking for source object using XPath: {source_xpath}")
            source_elements = xpath_search(self.source_tree, source_xpath)
            
            if not source_elements:
                error_msg = f"Object '{object_name}' not found in source"
                logger.error(error_msg)
                self.skipped_objects.append((object_type, object_name, "Not found in source"))
                return False
            
            source_object = source_elements[0]
            logger.debug(f"Found source object: {object_type} '{object_name}'")
            
        except Exception as e:
            error_msg = f"Error retrieving source object '{object_name}': {e}"
            logger.error(error_msg, exc_info=True)
            self.skipped_objects.append((object_type, object_name, f"Error: {str(e)}"))
            return False
        
        # Check if object exists in target
        try:
            target_xpath = get_object_xpath(
                object_type, 
                self.target_device_type, 
                target_context_type, 
                self.target_version, 
                object_name, 
                **target_params
            )
            
            logger.debug(f"Checking if object exists in target using XPath: {target_xpath}")
            target_elements = xpath_search(self.target_tree, target_xpath)
            
            if target_elements:
                if skip_if_exists:
                    logger.warning(f"Object '{object_name}' already exists in target, skipping")
                    self.skipped_objects.append((object_type, object_name, "Already exists in target"))
                    return False
                else:
                    # Remove existing object
                    parent = target_elements[0].getparent()
                    if parent is not None:
                        logger.info(f"Removing existing object '{object_name}' from target")
                        parent.remove(target_elements[0])
                    else:
                        logger.error(f"Cannot remove existing object '{object_name}' - parent element not found")
                        self.skipped_objects.append((object_type, object_name, "Cannot remove existing object"))
                        return False
            
        except Exception as e:
            error_msg = f"Error checking target for object '{object_name}': {e}"
            logger.error(error_msg, exc_info=True)
            self.skipped_objects.append((object_type, object_name, f"Error: {str(e)}"))
            return False
        
        # Get the target parent element
        try:
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
                error_msg = f"Invalid target parent path: {target_parent_xpath}"
                logger.error(error_msg)
                self.skipped_objects.append((object_type, object_name, "Invalid target parent path"))
                return False
                
            target_parent_xpath = parent_parts[0]
            logger.debug(f"Target parent XPath: {target_parent_xpath}")
            
            target_parent_elements = xpath_search(self.target_tree, target_parent_xpath)
            
            if not target_parent_elements:
                # Try to create the parent structure
                logger.info(f"Target parent element not found, attempting to create it")
                target_parent = self._create_parent_path(target_parent_xpath)
                if target_parent is None:
                    error_msg = f"Failed to create target parent path for object '{object_name}'"
                    logger.error(error_msg)
                    self.skipped_objects.append((object_type, object_name, "Failed to create target parent path"))
                    return False
            else:
                logger.debug(f"Found target parent element")
                target_parent = target_parent_elements[0]
            
        except Exception as e:
            error_msg = f"Error getting target parent for object '{object_name}': {e}"
            logger.error(error_msg, exc_info=True)
            self.skipped_objects.append((object_type, object_name, f"Error: {str(e)}"))
            return False
        
        # Create a copy of the source object and add to target
        try:
            logger.debug(f"Cloning source object")
            new_object = clone_element(source_object)
            
            # Add the object to the target
            logger.debug(f"Adding object to target parent")
            target_parent.append(new_object)
            
            # Add to merged objects list
            self.merged_objects.append((object_type, object_name))
            logger.info(f"Successfully copied {object_type} object '{object_name}' to target")
            
        except Exception as e:
            error_msg = f"Error copying object '{object_name}' to target: {e}"
            logger.error(error_msg, exc_info=True)
            self.skipped_objects.append((object_type, object_name, f"Error: {str(e)}"))
            return False
        
        # Collect and copy references if requested
        if copy_references and object_type.endswith('_group'):
            try:
                logger.debug(f"Copying references for group object '{object_name}'")
                self._copy_group_members(
                    new_object, 
                    object_type, 
                    source_context_type, 
                    target_context_type, 
                    skip_if_exists, 
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"Error copying group members for '{object_name}': {e}", exc_info=True)
                # Continue since the main object was copied successfully
        
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
        logger.info(f"Copying multiple {object_type} objects from {source_context_type} to {target_context_type}")
        
        if object_names:
            logger.debug(f"Using explicit list of {len(object_names)} object names")
        elif filter_criteria:
            logger.debug(f"Using filter criteria: {filter_criteria}")
        else:
            logger.warning("No object names or filter criteria specified, will attempt to copy all objects")
        
        # Extract context parameters
        source_params = self._extract_context_params(source_context_type, kwargs, 'source_')
        
        # Get the source objects
        try:
            source_base_xpath = get_object_xpath(
                object_type, 
                self.source_device_type, 
                source_context_type, 
                self.source_version, 
                **source_params
            )
            
            logger.debug(f"Searching for source objects using XPath: {source_base_xpath}/entry")
            source_objects = xpath_search(self.source_tree, source_base_xpath + "/entry")
            
            if not source_objects:
                logger.warning(f"No {object_type} objects found in source matching the criteria")
                return 0, 0
                
            logger.debug(f"Found {len(source_objects)} candidate objects in source")
            
        except Exception as e:
            logger.error(f"Error retrieving source objects: {e}", exc_info=True)
            return 0, 0
        
        # Filter objects if needed
        objects_to_copy = []
        
        if object_names:
            # Filter by name
            logger.debug(f"Filtering objects by name")
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
            logger.debug(f"Filtering objects by criteria")
            for obj in source_objects:
                if self._matches_criteria(obj, filter_criteria):
                    objects_to_copy.append(obj)
            
            logger.debug(f"Found {len(objects_to_copy)} objects matching criteria")
                
        else:
            # Copy all objects
            logger.debug(f"No filter applied, copying all {len(source_objects)} objects")
            objects_to_copy = source_objects
        
        # Copy each object
        copied_count = 0
        total_count = len(objects_to_copy)
        
        logger.info(f"Attempting to copy {total_count} objects")
        
        for obj in objects_to_copy:
            name = obj.get("name")
            if not name:
                logger.warning(f"Skipping object with no name attribute")
                continue
                
            logger.debug(f"Copying object: {name}")
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
        logger.info(f"Merging multiple object types from {source_context_type} to {target_context_type}")
        logger.debug(f"Object types to merge: {object_types}")
        
        results = {}
        
        for object_type in object_types:
            logger.info(f"Processing object type: {object_type}")
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
        
        # Log summary
        total_copied = sum(copied for copied, _ in results.values())
        total_objects = sum(total for _, total in results.values())
        logger.info(f"Merged a total of {total_copied} objects out of {total_objects} across all types")
        
        return results
    
    def _extract_context_params(self, context_type: str, kwargs: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
        """Extract context parameters from kwargs with optional prefix."""
        params = {}
        
        logger.debug(f"Extracting context parameters for {context_type} with prefix '{prefix}'")
        
        if context_type == "device_group":
            key = f"{prefix}device_group"
            if key in kwargs:
                params["device_group"] = kwargs[key]
                logger.debug(f"Found device_group parameter: {kwargs[key]}")
            elif "device_group" in kwargs and not prefix:
                params["device_group"] = kwargs["device_group"]
                logger.debug(f"Using default device_group parameter: {kwargs['device_group']}")
                
        elif context_type == "vsys":
            key = f"{prefix}vsys"
            if key in kwargs:
                params["vsys"] = kwargs[key]
                logger.debug(f"Found vsys parameter: {kwargs[key]}")
            elif "vsys" in kwargs and not prefix:
                params["vsys"] = kwargs["vsys"]
                logger.debug(f"Using default vsys parameter: {kwargs['vsys']}")
                
        elif context_type == "template":
            key = f"{prefix}template"
            if key in kwargs:
                params["template"] = kwargs[key]
                logger.debug(f"Found template parameter: {kwargs[key]}")
            elif "template" in kwargs and not prefix:
                params["template"] = kwargs["template"]
                logger.debug(f"Using default template parameter: {kwargs['template']}")
        
        return params
    
    def _matches_criteria(self, element: etree._Element, criteria: Dict[str, Any]) -> bool:
        """Check if an element matches the criteria."""
        logger.debug(f"Checking if element '{element.get('name', '')}' matches criteria")
        
        for key, value in criteria.items():
            # Handle XPath expressions in criteria
            if key.startswith('xpath:'):
                xpath = key[6:]  # Remove 'xpath:' prefix
                logger.debug(f"Evaluating XPath criteria: {xpath}")
                matches = element.xpath(xpath)
                if not matches:
                    logger.debug(f"Element doesn't match XPath criteria: {xpath}")
                    return False
                continue
                
            # Handle standard field matching
            if key == 'name':
                if element.get('name') != value:
                    logger.debug(f"Name mismatch: {element.get('name')} != {value}")
                    return False
            elif key == 'type':
                # Check specific object types
                if key == 'ip-netmask' and not element.xpath('./ip-netmask'):
                    logger.debug(f"Element doesn't have ip-netmask type")
                    return False
                if key == 'fqdn' and not element.xpath('./fqdn'):
                    logger.debug(f"Element doesn't have fqdn type")
                    return False
                if key == 'ip-range' and not element.xpath('./ip-range'):
                    logger.debug(f"Element doesn't have ip-range type")
                    return False
            elif key == 'value':
                # Match object value (ip, fqdn, etc.)
                matched = False
                for value_key in ['ip-netmask', 'fqdn', 'ip-range']:
                    elements = element.xpath(f'./{value_key}')
                    if elements and elements[0].text:
                        if elements[0].text != value:
                            logger.debug(f"Value mismatch for {value_key}: {elements[0].text} != {value}")
                            return False
                        matched = True
                        break
                if not matched:
                    logger.debug(f"No value match found")
                    return False
            else:
                # For other fields, check if they exist as child elements
                child_elements = element.xpath(f'./{key}')
                if not child_elements:
                    logger.debug(f"Element doesn't have child element: {key}")
                    return False
                
                # If child element has text content, check that too
                if value is not None and child_elements[0].text and child_elements[0].text.strip() != str(value).strip():
                    logger.debug(f"Child element text mismatch: {child_elements[0].text} != {value}")
                    return False
        
        logger.debug(f"Element matches all criteria")
        return True
    
    def _create_parent_path(self, path: str) -> Optional[etree._Element]:
        """Create the parent path in the target configuration if it doesn't exist."""
        logger.debug(f"Creating parent path: {path}")
        
        parts = path.strip('/').split('/')
        current = self.target_tree.getroot()
        
        for i, part in enumerate(parts):
            # Parse the tag and predicates
            if '[' in part:
                tag = part.split('[')[0]
                predicate = part[part.index('['):]
                logger.debug(f"Parsed part {i}: tag={tag}, predicate={predicate}")
            else:
                tag = part
                predicate = ""
                logger.debug(f"Parsed part {i}: tag={tag}, no predicate")
            
            # See if the element already exists
            xpath = "/" + "/".join(parts[:i+1])
            logger.debug(f"Checking if element exists: {xpath}")
            elements = xpath_search(self.target_tree, xpath)
            
            if elements:
                logger.debug(f"Element already exists")
                current = elements[0]
            else:
                logger.debug(f"Element doesn't exist, creating it")
                # Need to create this element
                # If it has a predicate with name, extract it
                name = None
                if predicate and "[@name=" in predicate:
                    # Extract name from [@name='value']
                    name_start = predicate.index("'") + 1
                    name_end = predicate.rindex("'")
                    name = predicate[name_start:name_end]
                    logger.debug(f"Extracted name from predicate: {name}")
                
                # Create the element
                try:
                    if name:
                        logger.debug(f"Creating element with name: {tag}[@name='{name}']")
                        new_elem = etree.SubElement(current, tag, {"name": name})
                    else:
                        logger.debug(f"Creating element without name: {tag}")
                        new_elem = etree.SubElement(current, tag)
                    
                    current = new_elem
                except Exception as e:
                    logger.error(f"Error creating element {tag}: {e}", exc_info=True)
                    return None
        
        logger.info(f"Successfully created parent path: {path}")
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
        group_name = group_element.get("name", "unknown")
        logger.debug(f"Copying members of {group_type} '{group_name}'")
        
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
            member_count = len(static_elements)
            logger.debug(f"Found {member_count} members in static group")
            
            for member_elem in static_elements:
                if member_elem.text:
                    member_name = member_elem.text
                    logger.debug(f"Processing member: {member_name}")
                    
                    # Avoid infinite recursion by checking if we've already copied this object
                    if (member_type, member_name) not in self.merged_objects and (member_type, member_name) not in self.referenced_objects:
                        # Track this reference
                        logger.debug(f"Adding to referenced objects list: {member_type} '{member_name}'")
                        self.referenced_objects.append((member_type, member_name))
                        
                        # Try to copy the member object
                        logger.debug(f"Attempting to copy member object: {member_type} '{member_name}'")
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
                        logger.debug(f"Checking if member is a group: {member_name}")
                        self.copy_object(
                            f"{member_type}_group",
                            member_name,
                            source_context_type,
                            target_context_type,
                            skip_if_exists,
                            True,  # copy_references
                            **kwargs
                        )
                    else:
                        logger.debug(f"Skipping already processed member: {member_name}")
            
            logger.info(f"Finished processing {member_count} members of {group_type} '{group_name}'")
        else:
            logger.debug(f"No static members found in {group_type} '{group_name}'")