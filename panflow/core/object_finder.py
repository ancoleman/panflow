"""
Global object finder for PANFlow.

This module provides functionality to find objects throughout a PAN-OS configuration
regardless of context (shared, device group, template, vsys).
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Set
from lxml import etree
import re

from .xpath_resolver import get_object_xpath
from .config_loader import xpath_search

# Initialize logger
logger = logging.getLogger("panflow")

class ObjectLocation:
    """Class to store information about where an object is located."""
    
    def __init__(
        self,
        object_type: str,
        object_name: str,
        context_type: str,
        element: etree._Element,
        **context_params
    ):
        """
        Initialize an ObjectLocation.
        
        Args:
            object_type: Type of object (address, service, etc.)
            object_name: Name of the object
            context_type: Type of context (shared, device_group, vsys, template)
            element: XML element of the object
            **context_params: Additional context parameters (device_group, vsys, etc.)
        """
        self.object_type = object_type
        self.object_name = object_name
        self.context_type = context_type
        self.element = element
        self.context_params = context_params
        
        # Store the object's properties
        self.properties = {}
        self._extract_properties()
    
    def _extract_properties(self):
        """Extract object properties from the XML element."""
        for child in self.element:
            if child.tag != 'entry':
                tag = child.tag
                if len(child) == 0:  # Simple text element
                    self.properties[tag] = child.text
                else:
                    # For complex elements, store the element itself for now
                    # Could be enhanced to extract more structured data
                    self.properties[tag] = child
    
    def get_xpath(self) -> str:
        """Get the full XPath to this object."""
        return self.element.getroottree().getpath(self.element)
    
    def get_context_display(self) -> str:
        """Get a human-readable string describing the context."""
        if self.context_type == 'shared':
            return 'shared'
        elif self.context_type == 'device_group':
            return f"device group '{self.context_params.get('device_group', '?')}'"
        elif self.context_type == 'vsys':
            return f"vsys '{self.context_params.get('vsys', '?')}'"
        elif self.context_type == 'template':
            return f"template '{self.context_params.get('template', '?')}'"
        else:
            return self.context_type
    
    def __str__(self) -> str:
        """String representation."""
        return (f"{self.object_type} '{self.object_name}' in {self.get_context_display()}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            'object_type': self.object_type,
            'object_name': self.object_name,
            'context_type': self.context_type,
            'context_params': self.context_params,
            'properties': {},
            'xpath': self.get_xpath()
        }
        
        # Convert properties to serializable format
        for key, value in self.properties.items():
            if isinstance(value, etree._Element):
                # For XML elements, convert to string representation
                result['properties'][key] = etree.tostring(value, encoding='unicode')
            else:
                result['properties'][key] = value
                
        return result


def find_objects_by_name(
    tree: etree._ElementTree,
    object_type: str,
    object_name: str,
    device_type: str,
    version: str,
    use_regex: bool = False
) -> List[ObjectLocation]:
    """
    Find all objects with a specific name throughout the configuration.
    
    Args:
        tree: ElementTree containing the configuration
        object_type: Type of object to find (address, service, etc.)
        object_name: Name of the object to find (exact match or regex pattern)
        device_type: Type of device ("firewall" or "panorama")
        version: PAN-OS version
        use_regex: If True, treat object_name as a regex pattern for partial matching
        
    Returns:
        List of ObjectLocation objects representing all matching objects
    """
    if use_regex:
        logger.info(f"Finding {object_type} objects with names matching pattern '{object_name}' throughout the configuration")
        # Compile the regex pattern with case-insensitive flag
        pattern = re.compile(object_name, re.IGNORECASE)
    else:
        logger.info(f"Finding {object_type} objects named '{object_name}' throughout the configuration")
    
    results = []
    
    # Define all possible contexts to search
    contexts = []
    
    if device_type.lower() == 'panorama':
        # For Panorama, search shared and all device groups
        contexts.append(('shared', {}))
        
        # Find all device groups
        dg_xpath = "/config/devices/entry[@name='localhost.localdomain']/device-group/entry"
        device_groups = xpath_search(tree, dg_xpath)
        
        for dg in device_groups:
            dg_name = dg.get('name')
            if dg_name:
                contexts.append(('device_group', {'device_group': dg_name}))
                
        # Find all templates
        tmpl_xpath = "/config/devices/entry[@name='localhost.localdomain']/template/entry"
        templates = xpath_search(tree, tmpl_xpath)
        
        for tmpl in templates:
            tmpl_name = tmpl.get('name')
            if tmpl_name:
                contexts.append(('template', {'template': tmpl_name}))
    else:
        # For firewall, search all vsys
        vsys_xpath = "/config/devices/entry[@name='localhost.localdomain']/vsys/entry"
        vsys_entries = xpath_search(tree, vsys_xpath)
        
        if vsys_entries:
            for vsys in vsys_entries:
                vsys_name = vsys.get('name')
                if vsys_name:
                    contexts.append(('vsys', {'vsys': vsys_name}))
        else:
            # Default to vsys1 if no vsys found
            contexts.append(('vsys', {'vsys': 'vsys1'}))
    
    # Search for the object in each context
    for context_type, context_params in contexts:
        try:
            # Get the XPath for this object in this context
            xpath = get_object_xpath(
                object_type,
                device_type,
                context_type,
                version,
                object_name,
                **context_params
            )
            
            # For exact name match
            if not use_regex:
                # Search for the object
                elements = xpath_search(tree, xpath)
                
                if elements:
                    for element in elements:
                        obj_loc = ObjectLocation(
                            object_type,
                            object_name,
                            context_type,
                            element,
                            **context_params
                        )
                        results.append(obj_loc)
                        logger.debug(f"Found {obj_loc}")
            else:
                # For regex matching, we need to get all objects of this type and filter by name
                all_elements_xpath = get_object_xpath(
                    object_type,
                    device_type,
                    context_type,
                    version,
                    **context_params
                )
                # The xpath already includes '/entry' (it's the path to all entries of this type)
                elements = xpath_search(tree, all_elements_xpath)
                
                logger.debug(f"Found {len(elements)} elements to check in {context_type}")
                if elements:
                    for element in elements:
                        name = element.get("name", "")
                        logger.debug(f"Checking element with name: '{name}'")
                        if name and pattern.search(name):
                            logger.debug(f"Pattern matched for '{name}'")
                            obj_loc = ObjectLocation(
                                object_type,
                                name,
                                context_type,
                                element,
                                **context_params
                            )
                            results.append(obj_loc)
                            logger.debug(f"Found matching {obj_loc}")
                        elif name:
                            logger.debug(f"Pattern did not match for '{name}'")
                    
        except Exception as e:
            logger.warning(f"Error searching for {object_type} '{object_name}' in {context_type}: {e}")
    
    logger.info(f"Found {len(results)} instance(s) of {object_type} '{object_name}'")
    return results


def find_objects_by_value(
    tree: etree._ElementTree,
    object_type: str,
    value_criteria: Dict[str, Any],
    device_type: str,
    version: str
) -> List[ObjectLocation]:
    """
    Find all objects matching specific value criteria throughout the configuration.
    
    Args:
        tree: ElementTree containing the configuration
        object_type: Type of object to find (address, service, etc.)
        value_criteria: Dictionary of criteria to match against object values
        device_type: Type of device ("firewall" or "panorama")
        version: PAN-OS version
        
    Returns:
        List of ObjectLocation objects representing all matching objects
    """
    logger.info(f"Finding {object_type} objects matching criteria {value_criteria} throughout the configuration")
    results = []
    
    # Define all possible contexts to search
    contexts = []
    
    if device_type.lower() == 'panorama':
        # For Panorama, search shared and all device groups
        contexts.append(('shared', {}))
        
        # Find all device groups
        dg_xpath = "/config/devices/entry[@name='localhost.localdomain']/device-group/entry"
        device_groups = xpath_search(tree, dg_xpath)
        
        for dg in device_groups:
            dg_name = dg.get('name')
            if dg_name:
                contexts.append(('device_group', {'device_group': dg_name}))
                
        # Find all templates
        tmpl_xpath = "/config/devices/entry[@name='localhost.localdomain']/template/entry"
        templates = xpath_search(tree, tmpl_xpath)
        
        for tmpl in templates:
            tmpl_name = tmpl.get('name')
            if tmpl_name:
                contexts.append(('template', {'template': tmpl_name}))
    else:
        # For firewall, search all vsys
        vsys_xpath = "/config/devices/entry[@name='localhost.localdomain']/vsys/entry"
        vsys_entries = xpath_search(tree, vsys_xpath)
        
        if vsys_entries:
            for vsys in vsys_entries:
                vsys_name = vsys.get('name')
                if vsys_name:
                    contexts.append(('vsys', {'vsys': vsys_name}))
        else:
            # Default to vsys1 if no vsys found
            contexts.append(('vsys', {'vsys': 'vsys1'}))
    
    # Search for objects in each context
    for context_type, context_params in contexts:
        try:
            # Get the base XPath for this object type in this context
            xpath_base = get_object_xpath(
                object_type,
                device_type,
                context_type,
                version,
                **context_params
            )
            
            # Get all objects of this type in this context
            # Use xpath_base directly as it already includes the /entry part
            xpath = xpath_base
            elements = xpath_search(tree, xpath)
            
            # Filter elements based on value criteria
            for element in elements:
                if _matches_criteria(element, value_criteria):
                    obj_name = element.get('name')
                    if obj_name:
                        obj_loc = ObjectLocation(
                            object_type,
                            obj_name,
                            context_type,
                            element,
                            **context_params
                        )
                        results.append(obj_loc)
                        logger.debug(f"Found matching {obj_loc}")
                    
        except Exception as e:
            logger.warning(f"Error searching for {object_type} with criteria {value_criteria} in {context_type}: {e}")
    
    logger.info(f"Found {len(results)} matching {object_type} objects")
    return results


def _matches_criteria(element: etree._Element, criteria: Dict[str, Any]) -> bool:
    """
    Check if an element matches the provided criteria.
    
    Args:
        element: XML element to check
        criteria: Dictionary of criteria to match
        
    Returns:
        bool: True if the element matches the criteria, False otherwise
    """
    for key, value in criteria.items():
        if key == 'name':
            # Check the name attribute
            if element.get('name') != value:
                return False
                
        elif key == 'has-tag':
            # Check if the element has a specific tag
            tag_elements = element.xpath('./tag/member')
            tag_values = [tag.text for tag in tag_elements if tag.text]
            if value not in tag_values:
                return False
                
        elif key.startswith('xpath:'):
            # Support for XPath expressions
            xpath = key[6:]  # Remove 'xpath:' prefix
            matches = element.xpath(xpath)
            if not matches:
                return False
                
        elif key == 'ip-netmask' or key == 'ip-range' or key == 'fqdn':
            # Special handling for address object value types
            child = element.find(f'./{key}')
            if child is None or child.text != value:
                return False
                
        elif key == 'protocol':
            # Special handling for service object protocol
            protocol = element.find('./protocol')
            if protocol is None:
                return False
            
            if protocol.find(f'./{value}') is None:
                return False
                
        elif key == 'port':
            # Search for port in any protocol
            port_found = False
            for protocol in ['tcp', 'udp', 'sctp']:
                port_elem = element.find(f'./protocol/{protocol}/port')
                if port_elem is not None and port_elem.text == value:
                    port_found = True
                    break
            if not port_found:
                return False
                
        else:
            # For other keys, look for a direct child element
            child = element.find(f'./{key}')
            if child is None:
                return False
                
            # If a value is specified, check the text content
            if value is not None and child.text and child.text.strip() != str(value).strip():
                return False
    
    # If all criteria passed, the element matches
    return True


def find_all_locations(
    tree: etree._ElementTree,
    device_type: str,
    version: str,
    specific_object_type: Optional[str] = None
) -> Dict[str, Dict[str, List[ObjectLocation]]]:
    """
    Find the locations of all objects in the configuration.
    
    Args:
        tree: ElementTree containing the configuration
        device_type: Type of device ("firewall" or "panorama")
        version: PAN-OS version
        specific_object_type: Optional specific object type to search for (if None, search all types)
        
    Returns:
        Dict mapping object types to dicts mapping object names to lists of locations
    """
    if specific_object_type:
        logger.info(f"Finding all {specific_object_type} object locations in the configuration")
    else:
        logger.info(f"Finding all object locations in the configuration")
    
    # Define object types to search for
    default_object_types = [
        "address", "address-group", "service", "service-group", 
        "tag", "application-filter", "application-group",
        "security-profile-group", "schedule", "region",
        # Using correct naming from YAML object definition keys:
        "dynamic_user_group"  # Changed from "dynamic-user-group" to match YAML
        # Note: In the YAML, the key is "dynamic_user_group" (with underscores)
        # but the actual path is "/dynamic-user-group/" (with hyphens)
        # Removed "url-category" as it's not defined in YAML mappings
        # Removed "application-override" as it's a policy type, not an object type
    ]
    
    # Use specific type if provided, otherwise use all types
    object_types = [specific_object_type] if specific_object_type else default_object_types
    
    # Build result structure
    results = {}
    
    # Define all possible contexts to search
    contexts = []
    
    if device_type.lower() == 'panorama':
        # For Panorama, search shared and all device groups
        contexts.append(('shared', {}))
        
        # Find all device groups
        dg_xpath = "/config/devices/entry[@name='localhost.localdomain']/device-group/entry"
        device_groups = xpath_search(tree, dg_xpath)
        
        for dg in device_groups:
            dg_name = dg.get('name')
            if dg_name:
                contexts.append(('device_group', {'device_group': dg_name}))
                
        # Find all templates
        tmpl_xpath = "/config/devices/entry[@name='localhost.localdomain']/template/entry"
        templates = xpath_search(tree, tmpl_xpath)
        
        for tmpl in templates:
            tmpl_name = tmpl.get('name')
            if tmpl_name:
                contexts.append(('template', {'template': tmpl_name}))
    else:
        # For firewall, search all vsys
        vsys_xpath = "/config/devices/entry[@name='localhost.localdomain']/vsys/entry"
        vsys_entries = xpath_search(tree, vsys_xpath)
        
        if vsys_entries:
            for vsys in vsys_entries:
                vsys_name = vsys.get('name')
                if vsys_name:
                    contexts.append(('vsys', {'vsys': vsys_name}))
        else:
            # Default to vsys1 if no vsys found
            contexts.append(('vsys', {'vsys': 'vsys1'}))
    
    # Create a mapping of object type to found objects to avoid double entries
    found_objects = {}
    
    # Search for all object types in all contexts
    for object_type in object_types:
        found_objects[object_type] = {}
        results[object_type] = {}
        
        for context_type, context_params in contexts:
            try:
                # Get the base XPath for this object type in this context
                xpath_base = get_object_xpath(
                    object_type,
                    device_type,
                    context_type,
                    version,
                    **context_params
                )
                
                # Get all objects of this type in this context
                # Use xpath_base directly as it already includes the /entry part
                xpath = xpath_base
                elements = xpath_search(tree, xpath)
                
                for element in elements:
                    obj_name = element.get('name')
                    if obj_name:
                        # Create the object location
                        obj_loc = ObjectLocation(
                            object_type,
                            obj_name,
                            context_type,
                            element,
                            **context_params
                        )
                        
                        # Add to results
                        if obj_name not in results[object_type]:
                            results[object_type][obj_name] = []
                        
                        results[object_type][obj_name].append(obj_loc)
                        
                        logger.debug(f"Found {obj_loc}")
                    
            except Exception as e:
                logger.warning(f"Error searching for {object_type} objects in {context_type}: {e}")
    
    # Count the total objects found
    total_locations = sum(len(locations) for obj_dict in results.values() for locations in obj_dict.values())
    total_unique = sum(len(obj_dict) for obj_dict in results.values())
    
    logger.info(f"Found {total_locations} object locations for {total_unique} unique object names")
    return results


def find_duplicate_names(
    tree: etree._ElementTree,
    device_type: str,
    version: str
) -> Dict[str, Dict[str, List[ObjectLocation]]]:
    """
    Find objects with the same name across different contexts.
    
    Args:
        tree: ElementTree containing the configuration
        device_type: Type of device ("firewall" or "panorama")
        version: PAN-OS version
        
    Returns:
        Dict mapping object types to dicts mapping duplicate names to lists of locations
    """
    logger.info(f"Finding objects with duplicate names across different contexts")
    
    # Get all object locations for all object types
    # For duplicate names, we need to check all object types
    all_locations = find_all_locations(tree, device_type, version)
    
    # Filter to only include objects with multiple locations
    duplicates = {}
    
    for object_type, objects in all_locations.items():
        type_duplicates = {}
        
        for obj_name, locations in objects.items():
            if len(locations) > 1:
                # Check if they're in different contexts
                contexts = set()
                for loc in locations:
                    context_key = (loc.context_type, tuple(sorted(loc.context_params.items())))
                    contexts.add(context_key)
                
                # Only count as duplicate if in different contexts
                if len(contexts) > 1:
                    type_duplicates[obj_name] = locations
        
        if type_duplicates:
            duplicates[object_type] = type_duplicates
    
    # Count duplicates
    total_duplicates = sum(len(dup_dict) for dup_dict in duplicates.values())
    logger.info(f"Found {total_duplicates} object names with duplicates across different contexts")
    
    return duplicates


def find_duplicate_values(
    tree: etree._ElementTree,
    object_type: str,
    device_type: str,
    version: str
) -> Dict[str, List[ObjectLocation]]:
    """
    Find objects with the same value but different names.
    
    This is a specialized function that works for address, service, and tag objects
    which have clear value definitions.
    
    Args:
        tree: ElementTree containing the configuration
        object_type: Type of object to find duplicates for
        device_type: Type of device ("firewall" or "panorama")
        version: PAN-OS version
        
    Returns:
        Dict mapping values to lists of locations
    """
    logger.info(f"Finding {object_type} objects with duplicate values but different names")
    
    # Get all object locations for the specified object type
    all_locations = find_all_locations(tree, device_type, version, specific_object_type=object_type)
    
    # Get locations for the specific object type
    if object_type not in all_locations:
        logger.warning(f"No {object_type} objects found in the configuration")
        return {}
    
    object_locations = []
    for locations in all_locations[object_type].values():
        object_locations.extend(locations)
    
    # Group by value based on object type
    by_value = {}
    
    for obj_loc in object_locations:
        value_key = None
        
        if object_type == 'address':
            # For address objects, check ip-netmask, fqdn, ip-range
            for key in ['ip-netmask', 'fqdn', 'ip-range']:
                if key in obj_loc.properties:
                    value_key = f"{key}:{obj_loc.properties[key]}"
                    break
        
        elif object_type == 'service':
            # For service objects, check protocol and port
            protocol = None
            port = None
            
            # Check for protocol element references in properties
            for protocol_type in ['tcp', 'udp', 'sctp']:
                if protocol_type in obj_loc.properties:
                    protocol = protocol_type
                    # Extract port if available
                    protocol_elem = obj_loc.properties[protocol_type]
                    if isinstance(protocol_elem, etree._Element):
                        port_elem = protocol_elem.find('./port')
                        if port_elem is not None and port_elem.text:
                            port = port_elem.text
                    break
            
            if protocol and port:
                value_key = f"{protocol}-port:{port}"
        
        elif object_type == 'tag':
            # For tag objects, check color
            if 'color' in obj_loc.properties:
                value_key = f"color:{obj_loc.properties['color']}"
        
        # Add to the appropriate value group if a key was determined
        if value_key:
            if value_key not in by_value:
                by_value[value_key] = []
            by_value[value_key].append(obj_loc)
    
    # Filter to only include values with multiple object locations
    duplicates = {
        value: locations for value, locations in by_value.items() 
        if len(set(loc.object_name for loc in locations)) > 1
    }
    
    # Count duplicates
    logger.info(f"Found {len(duplicates)} unique values with multiple {object_type} objects")
    
    return duplicates