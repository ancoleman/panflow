"""
Bulk operations for PANFlow.

This module provides functionality for performing operations on multiple configuration
elements simultaneously, such as bulk policy updates, object modifications, and more.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Set
from lxml import etree

from .xpath_resolver import get_object_xpath, get_policy_xpath
from .config_loader import xpath_search
from .object_merger import ObjectMerger
from .deduplication import DeduplicationEngine
from .conflict_resolver import ConflictStrategy

# Get module logger
logger = logging.getLogger("panflow")

class ConfigQuery:
    """
    Class for selecting configuration elements based on criteria.
    
    This class provides methods to search for and select policies or objects
    that match specific filtering criteria.
    """
    
    def __init__(self, tree, device_type, context_type, version, **kwargs):
        """
        Initialize a ConfigQuery instance.
        
        Args:
            tree: ElementTree containing the configuration
            device_type: Type of device ("firewall" or "panorama")
            context_type: Type of context (shared, device_group, vsys)
            version: PAN-OS version
            **kwargs: Additional context parameters (device_group, vsys, etc.)
        """
        self.tree = tree
        self.device_type = device_type
        self.context_type = context_type
        self.version = version
        self.context_kwargs = kwargs
        
        logger.debug(f"Initialized ConfigQuery: device_type={device_type}, context_type={context_type}, "
                    f"version={version}, context_kwargs={kwargs}")
        
    def select_policies(self, policy_type, criteria=None):
        """
        Select policies matching the criteria with enhanced filtering capabilities.
        
        Args:
            policy_type: Type of policy to select (security_pre_rules, nat_rules, etc.)
            criteria: Dictionary of criteria to filter policies. Enhanced criteria include:
                - 'field_exists': Check if a field exists
                - 'field_missing': Check if a field is missing
                - 'text_contains': Check if text contains a substring
                - 'regex_match': Use regular expressions for matching
                - 'has_profile_type': Check for specific security profile types
                - 'date_before'/'date_after': Filter by modification date
                
        Returns:
            List of matching policy elements
        """
        logger.info(f"Selecting {policy_type} policies with criteria: {criteria}")
        
        # Get base XPath for the policy type
        try:
            base_xpath = get_policy_xpath(policy_type, self.device_type, self.context_type, 
                                        self.version, **self.context_kwargs)
            
            logger.debug(f"Generated base XPath: {base_xpath}")
            
            # Start with all policies of this type
            results = xpath_search(self.tree, base_xpath)
            initial_count = len(results)
            logger.info(f"Found {initial_count} {policy_type} policies before filtering")
            
            # Apply filters if criteria is provided
            if criteria and results:
                logger.debug(f"Applying filtering criteria: {criteria}")
                filtered_results = []
                
                for policy in results:
                    if self._matches_enhanced_criteria(policy, criteria):
                        policy_name = policy.get('name', 'unknown')
                        filtered_results.append(policy)
                        logger.debug(f"Policy '{policy_name}' matches criteria")
                    
                logger.info(f"Filtered down to {len(filtered_results)} matching policies")
                return filtered_results
            
            return results
            
        except Exception as e:
            logger.error(f"Error selecting policies: {str(e)}", exc_info=True)
            return []
    
    def _matches_enhanced_criteria(self, element, criteria):
        """
        Check if an element matches the enhanced criteria.
        
        Args:
            element: XML element to check
            criteria: Dictionary of enhanced criteria
            
        Returns:
            bool: True if the element matches all criteria, False otherwise
        """
        import re
        from datetime import datetime
        
        element_name = element.get('name', 'unknown')
        logger.debug(f"Evaluating enhanced criteria for element '{element_name}'")
        
        try:
            for key, value in criteria.items():
                # Handle enhanced criteria types
                if key == 'field_exists':
                    for field in value if isinstance(value, list) else [value]:
                        if not element.xpath(f'./{field}'):
                            logger.debug(f"Element '{element_name}' is missing required field: {field}")
                            return False
                
                elif key == 'field_missing':
                    for field in value if isinstance(value, list) else [value]:
                        if element.xpath(f'./{field}'):
                            logger.debug(f"Element '{element_name}' has field that should be missing: {field}")
                            return False
                
                elif key == 'text_contains':
                    field_path, substring = value.get('field', ''), value.get('text', '')
                    field_elements = element.xpath(f'./{field_path}')
                    if not field_elements or not any(substring in (elem.text or '') for elem in field_elements):
                        logger.debug(f"Element '{element_name}' does not contain text: {substring}")
                        return False
                
                elif key == 'regex_match':
                    field_path, pattern = value.get('field', ''), value.get('pattern', '')
                    field_elements = element.xpath(f'./{field_path}')
                    if not field_elements or not any(re.search(pattern, (elem.text or '')) for elem in field_elements):
                        logger.debug(f"Element '{element_name}' does not match regex pattern: {pattern}")
                        return False
                
                elif key == 'has_profile_type':
                    profile_type = value
                    profile_elements = element.xpath(f'.//profile-setting//{profile_type}')
                    if not profile_elements:
                        logger.debug(f"Element '{element_name}' does not have profile type: {profile_type}")
                        return False
                
                elif key == 'date_before' or key == 'date_after':
                    # This assumes a 'last-modified' attribute or element
                    date_str = element.get('last-modified', '')
                    if not date_str:
                        mod_elem = element.find('./last-modified')
                        date_str = mod_elem.text if mod_elem is not None else ''
                    
                    if date_str:
                        try:
                            mod_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                            compare_date = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                            
                            if key == 'date_before' and mod_date >= compare_date:
                                logger.debug(f"Element '{element_name}' modification date {mod_date} is not before {compare_date}")
                                return False
                            elif key == 'date_after' and mod_date <= compare_date:
                                logger.debug(f"Element '{element_name}' modification date {mod_date} is not after {compare_date}")
                                return False
                        except ValueError:
                            logger.warning(f"Invalid date format in element '{element_name}' or criteria")
                
                # Handle standard field matching (as in the original method)
                elif key == 'name':
                    if element.get('name') != value:
                        logger.debug(f"Element '{element_name}' name does not match {value}")
                        return False
                elif key == 'has-tag':
                    tag_elements = element.xpath('./tag/member')
                    tag_values = [tag.text for tag in tag_elements if tag.text]
                    if value not in tag_values:
                        logger.debug(f"Element '{element_name}' does not have tag: {value}")
                        return False
                elif key in ['source', 'destination', 'application', 'service']:
                    member_elements = element.xpath(f'./{key}/member')
                    member_values = [m.text for m in member_elements if m.text]
                    
                    if isinstance(value, list):
                        if not any(v in member_values for v in value):
                            logger.debug(f"Element '{element_name}' {key} values {member_values} don't match any in {value}")
                            return False
                    else:
                        if value not in member_values:
                            logger.debug(f"Element '{element_name}' {key} values {member_values} don't include {value}")
                            return False
                else:
                    child_elements = element.xpath(f'./{key}')
                    if not child_elements:
                        logger.debug(f"Element '{element_name}' has no child element: {key}")
                        return False
                    
                    if value is not None and child_elements[0].text and child_elements[0].text.strip() != str(value).strip():
                        logger.debug(f"Element '{element_name}' {key} value '{child_elements[0].text}' doesn't match '{value}'")
                        return False
            
            logger.debug(f"Element '{element_name}' matches all criteria")
            return True
        except Exception as e:
            logger.error(f"Error matching criteria for element '{element_name}': {str(e)}", exc_info=True)
            return False
        
    def select_objects(self, object_type, criteria=None):
        """
        Select objects matching the criteria.
        
        Args:
            object_type: Type of object to select (address, service, etc.)
            criteria: Dictionary of criteria to filter objects
            
        Returns:
            List of matching object elements
        """
        logger.info(f"Selecting {object_type} objects with criteria: {criteria}")
        
        try:
            # Get base XPath for the object type
            base_xpath = get_object_xpath(object_type, self.device_type, self.context_type, 
                                         self.version, **self.context_kwargs)
            
            logger.debug(f"Generated base XPath: {base_xpath}")
            
            # Start with all objects of this type
            results = xpath_search(self.tree, base_xpath)
            initial_count = len(results)
            logger.info(f"Found {initial_count} {object_type} objects before filtering")
            
            # Apply filters if criteria is provided
            if criteria and results:
                logger.debug(f"Applying filtering criteria: {criteria}")
                filtered_results = []
                
                for obj in results:
                    if self._matches_criteria(obj, criteria):
                        obj_name = obj.get('name', 'unknown')
                        filtered_results.append(obj)
                        logger.debug(f"Object '{obj_name}' matches criteria")
                
                logger.info(f"Filtered down to {len(filtered_results)} matching objects")
                return filtered_results
            
            return results
            
        except Exception as e:
            logger.error(f"Error selecting objects: {str(e)}", exc_info=True)
            return []
    
    def _matches_criteria(self, element, criteria):
        """
        Check if an element matches the provided criteria.
        
        This internal method evaluates whether an XML element matches the
        given filter criteria.
        
        Args:
            element: XML element to check
            criteria: Dictionary of criteria to match
            
        Returns:
            bool: True if the element matches all criteria, False otherwise
        """
        element_name = element.get('name', 'unknown')
        logger.debug(f"Evaluating criteria for element '{element_name}'")
        
        try:
            for key, value in criteria.items():
                # Handle XPath expressions in criteria
                if key.startswith('xpath:'):
                    xpath = key[6:]  # Remove 'xpath:' prefix
                    logger.debug(f"Evaluating XPath criterion: {xpath}")
                    matches = element.xpath(xpath)
                    if not matches:
                        logger.debug(f"Element '{element_name}' does not match XPath: {xpath}")
                        return False
                    continue
                    
                # Handle standard field matching
                if key == 'name':
                    if element.get('name') != value:
                        logger.debug(f"Element '{element_name}' name does not match {value}")
                        return False
                elif key == 'has-tag':
                    tag_elements = element.xpath('./tag/member')
                    tag_values = [tag.text for tag in tag_elements if tag.text]
                    if value not in tag_values:
                        logger.debug(f"Element '{element_name}' does not have tag: {value}")
                        return False
                    else:
                        logger.debug(f"Element '{element_name}' has tag: {value}")
                elif key in ['source', 'destination', 'application', 'service']:
                    # Handle list-type fields (e.g., source, destination, service)
                    member_elements = element.xpath(f'./{key}/member')
                    member_values = [m.text for m in member_elements if m.text]
                    
                    if isinstance(value, list):
                        # Check if any of the criteria values are in the member list
                        matches = any(v in member_values for v in value)
                        if not matches:
                            logger.debug(f"Element '{element_name}' {key} values {member_values} don't match any in {value}")
                            return False
                    else:
                        # Check if the criteria value is in the member list
                        if value not in member_values:
                            logger.debug(f"Element '{element_name}' {key} values {member_values} don't include {value}")
                            return False
                else:
                    # For other fields, check if they exist as child elements
                    child_elements = element.xpath(f'./{key}')
                    if not child_elements:
                        logger.debug(f"Element '{element_name}' has no child element: {key}")
                        return False
                    
                    # If child element has text content, check that too
                    if child_elements[0].text and value is not None:
                        text_value = child_elements[0].text.strip()
                        expected_value = str(value).strip()
                        if text_value != expected_value:
                            logger.debug(f"Element '{element_name}' {key} value '{text_value}' doesn't match '{expected_value}'")
                            return False
            
            logger.debug(f"Element '{element_name}' matches all criteria")
            return True
            
        except Exception as e:
            logger.error(f"Error matching criteria for element '{element_name}': {str(e)}", exc_info=True)
            return False


class ConfigUpdater:
    """
    Class for applying bulk updates to configuration elements.
    
    This class provides methods to apply operations to multiple configuration
    elements that match specific criteria.
    """
    
    def __init__(self, tree, device_type, context_type, version, **kwargs):
        """
        Initialize a ConfigUpdater instance.
        
        Args:
            tree: ElementTree containing the configuration
            device_type: Type of device ("firewall" or "panorama")
            context_type: Type of context (shared, device_group, vsys)
            version: PAN-OS version
            **kwargs: Additional context parameters (device_group, vsys, etc.)
        """
        self.tree = tree
        self.device_type = device_type
        self.context_type = context_type
        self.version = version
        self.context_kwargs = kwargs
        self.query = ConfigQuery(tree, device_type, context_type, version, **kwargs)
        
        logger.debug(f"Initialized ConfigUpdater: device_type={device_type}, context_type={context_type}, "
                   f"version={version}, context_kwargs={kwargs}")
        
    def bulk_update_policies(self, policy_type, criteria, update_operations):
        """
        Update all policies matching criteria with specified operations.
        
        Args:
            policy_type: Type of policy to update (security_pre_rules, nat_rules, etc.)
            criteria: Dictionary of criteria to select policies
            update_operations: Dictionary of operations to apply
            
        Returns:
            int: Number of policies updated
        """
        logger.info(f"Starting bulk update of {policy_type} policies")
        logger.info(f"Selection criteria: {criteria}")
        logger.info(f"Update operations: {update_operations}")
        
        try:
            # Select matching policies
            policies = self.query.select_policies(policy_type, criteria)
            
            if not policies:
                logger.warning("No policies found matching the criteria")
                return 0
            
            logger.info(f"Found {len(policies)} matching policies to update")
            
            updated_count = 0
            for policy in policies:
                policy_name = policy.get('name', 'unknown')
                logger.info(f"Updating policy: {policy_name}")
                
                if self._apply_updates(policy, update_operations):
                    updated_count += 1
                    logger.info(f"Successfully updated policy: {policy_name}")
                else:
                    logger.warning(f"No changes applied to policy: {policy_name}")
            
            logger.info(f"Bulk update completed: {updated_count} of {len(policies)} policies updated")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error during bulk policy update: {str(e)}", exc_info=True)
            return 0
    
    def bulk_update_objects(self, object_type, criteria, update_operations):
        """
        Update all objects matching criteria with specified operations.
        
        Args:
            object_type: Type of object to update (address, service, etc.)
            criteria: Dictionary of criteria to select objects
            update_operations: Dictionary of operations to apply
            
        Returns:
            int: Number of objects updated
        """
        logger.info(f"Starting bulk update of {object_type} objects")
        logger.info(f"Selection criteria: {criteria}")
        logger.info(f"Update operations: {update_operations}")
        
        try:
            # Select matching objects
            objects = self.query.select_objects(object_type, criteria)
            
            if not objects:
                logger.warning("No objects found matching the criteria")
                return 0
            
            logger.info(f"Found {len(objects)} matching objects to update")
            
            updated_count = 0
            for obj in objects:
                obj_name = obj.get('name', 'unknown')
                logger.info(f"Updating object: {obj_name}")
                
                if self._apply_updates(obj, update_operations):
                    updated_count += 1
                    logger.info(f"Successfully updated object: {obj_name}")
                else:
                    logger.warning(f"No changes applied to object: {obj_name}")
            
            logger.info(f"Bulk update completed: {updated_count} of {len(objects)} objects updated")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error during bulk object update: {str(e)}", exc_info=True)
            return 0
    
    def bulk_delete_policies(self, policy_type, criteria):
        """
        Delete all policies matching criteria.
        
        Args:
            policy_type: Type of policy to delete (security_pre_rules, nat_rules, etc.)
            criteria: Dictionary of criteria to select policies
            
        Returns:
            int: Number of policies deleted
        """
        logger.info(f"Starting bulk deletion of {policy_type} policies")
        logger.info(f"Deletion criteria: {criteria}")
        
        try:
            # Select matching policies
            policies = self.query.select_policies(policy_type, criteria)
            
            if not policies:
                logger.warning("No policies found matching the criteria")
                return 0
            
            logger.info(f"Found {len(policies)} matching policies to delete")
            
            deleted_count = 0
            for policy in policies:
                policy_name = policy.get('name', 'unknown')
                logger.info(f"Deleting policy: {policy_name}")
                
                try:
                    parent = policy.getparent()
                    if parent is not None:
                        parent.remove(policy)
                        deleted_count += 1
                        logger.info(f"Successfully deleted policy: {policy_name}")
                    else:
                        logger.warning(f"Could not delete policy '{policy_name}': parent element not found")
                except Exception as e:
                    logger.error(f"Error deleting policy '{policy_name}': {str(e)}", exc_info=True)
            
            logger.info(f"Bulk deletion completed: {deleted_count} of {len(policies)} policies deleted")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during bulk policy deletion: {str(e)}", exc_info=True)
            return 0
    
    def bulk_delete_objects(self, object_type, criteria):
        """
        Delete all objects matching criteria.
        
        Args:
            object_type: Type of object to delete (address, service, etc.)
            criteria: Dictionary of criteria to select objects
            
        Returns:
            int: Number of objects deleted
        """
        logger.info(f"Starting bulk deletion of {object_type} objects")
        logger.info(f"Deletion criteria: {criteria}")
        
        try:
            # Select matching objects
            objects = self.query.select_objects(object_type, criteria)
            
            if not objects:
                logger.warning("No objects found matching the criteria")
                return 0
            
            logger.info(f"Found {len(objects)} matching objects to delete")
            
            deleted_count = 0
            for obj in objects:
                obj_name = obj.get('name', 'unknown')
                logger.info(f"Deleting object: {obj_name}")
                
                try:
                    parent = obj.getparent()
                    if parent is not None:
                        parent.remove(obj)
                        deleted_count += 1
                        logger.info(f"Successfully deleted object: {obj_name}")
                    else:
                        logger.warning(f"Could not delete object '{obj_name}': parent element not found")
                except Exception as e:
                    logger.error(f"Error deleting object '{obj_name}': {str(e)}", exc_info=True)
            
            logger.info(f"Bulk deletion completed: {deleted_count} of {len(objects)} objects deleted")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during bulk object deletion: {str(e)}", exc_info=True)
            return 0
    
    def _apply_updates(self, element, operations):
        """
        Apply update operations to an element.
        
        This internal method applies the specified operations to an XML element.
        
        Args:
            element: XML element to update
            operations: Dictionary of operations to apply
            
        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get('name', 'unknown')
        logger.debug(f"Applying updates to element: {element_name}")
        
        try:
            modified = False
            
            for operation, params in operations.items():
                logger.debug(f"Applying operation '{operation}' with params: {params}")
                
                if operation == 'add-profile':
                    # Add log forwarding profile or security profile
                    modified |= self._add_profile(element, params)
                
                elif operation == 'add-tag':
                    # Add tag to the element
                    modified |= self._add_tag(element, params)
                
                elif operation == 'add-zone':
                    # Add zone to the element (for policies)
                    modified |= self._add_zone(element, params)
                
                elif operation == 'change-action':
                    # Change policy action
                    modified |= self._change_action(element, params)
                
                elif operation == 'add-object':
                    # Add address or service object to source/destination/service
                    modified |= self._add_object(element, params)
                
                elif operation == 'remove-object':
                    # Remove address or service object from source/destination/service
                    modified |= self._remove_object(element, params)
                
                elif operation == 'update-description':
                    # Update description field
                    modified |= self._update_description(element, params)
                
                elif operation == 'enable-disable':
                    # Enable or disable the element
                    modified |= self._enable_disable(element, params)
                
                elif operation == 'update-logging':
                    # Update logging options
                    modified |= self._update_logging(element, params)
                
                elif operation == 'update-ip-address':
                    # Update IP address for address objects
                    modified |= self._update_ip_address(element, params)
                
                else:
                    logger.warning(f"Unknown operation: {operation}")
            
            return modified
            
        except Exception as e:
            logger.error(f"Error applying updates to element '{element_name}': {str(e)}", exc_info=True)
            return False
    
    def _add_profile(self, element, params):
        """
        Add a profile to an element.
        
        Args:
            element: XML element to update
            params: Parameters for the operation
            
        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get('name', 'unknown')
        profile_type = params.get('type')
        profile_name = params.get('name')
        
        if not profile_type or not profile_name:
            logger.warning(f"Missing type or name in add-profile operation for element '{element_name}'")
            return False
        
        logger.debug(f"Adding profile of type '{profile_type}' named '{profile_name}' to element '{element_name}'")
        
        try:
            # Check if profile-setting exists
            profile_setting = element.find('./profile-setting')
            if profile_setting is None:
                logger.debug(f"Creating new profile-setting element for '{element_name}'")
                profile_setting = etree.SubElement(element, 'profile-setting')
            
            if profile_type == 'log-forwarding':
                # Set log-forwarding profile
                log_setting = profile_setting.find('./log-setting')
                if log_setting is not None:
                    old_value = log_setting.text
                    log_setting.text = profile_name
                    logger.info(f"Updated log-forwarding profile from '{old_value}' to '{profile_name}'")
                else:
                    log_setting = etree.SubElement(profile_setting, 'log-setting')
                    log_setting.text = profile_name
                    logger.info(f"Added log-forwarding profile '{profile_name}'")
                
                return True
                
            elif profile_type in ['group', 'virus', 'spyware', 'vulnerability', 'url-filtering', 'wildfire-analysis', 'data-filtering', 'file-blocking', 'dns-security']:
                # Add security profile or group
                profile_elem = profile_setting.find(f'./{profile_type}')
                if profile_elem is None:
                    logger.debug(f"Creating new {profile_type} element")
                    profile_elem = etree.SubElement(profile_setting, profile_type)
                
                # Add as member if it's not already there
                members = profile_elem.xpath('./member')
                member_values = [m.text for m in members if m.text]
                
                if profile_name not in member_values:
                    member = etree.SubElement(profile_elem, 'member')
                    member.text = profile_name
                    logger.info(f"Added {profile_type} profile '{profile_name}'")
                    return True
                else:
                    logger.debug(f"Profile '{profile_name}' already exists in {profile_type}")
                    return False
            else:
                logger.warning(f"Unsupported profile type: {profile_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding profile to element '{element_name}': {str(e)}", exc_info=True)
            return False
    
    def _add_tag(self, element, params):
        """
        Add a tag to an element.
        
        Args:
            element: XML element to update
            params: Parameters for the operation
            
        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get('name', 'unknown')
        tag_name = params.get('name')
        
        if not tag_name:
            logger.warning(f"Missing tag name in add-tag operation for element '{element_name}'")
            return False
        
        logger.debug(f"Adding tag '{tag_name}' to element '{element_name}'")
        
        try:
            # Check if tag element exists
            tags = element.find('./tag')
            if tags is None:
                logger.debug(f"Creating new tag element for '{element_name}'")
                tags = etree.SubElement(element, 'tag')
            
            # Check if this tag is already present
            members = tags.xpath('./member')
            member_values = [m.text for m in members if m.text]
            
            if tag_name not in member_values:
                member = etree.SubElement(tags, 'member')
                member.text = tag_name
                logger.info(f"Added tag '{tag_name}' to element '{element_name}'")
                return True
            else:
                logger.debug(f"Tag '{tag_name}' already exists for element '{element_name}'")
                return False
                
        except Exception as e:
            logger.error(f"Error adding tag to element '{element_name}': {str(e)}", exc_info=True)
            return False
    
    def _add_zone(self, element, params):
        """
        Add a zone to a policy element.
        
        Args:
            element: XML element to update
            params: Parameters for the operation
            
        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get('name', 'unknown')
        zone_name = params.get('name')
        location = params.get('location', 'to')  # Default to 'to' if not specified
        
        if not zone_name:
            logger.warning(f"Missing zone name in add-zone operation for policy '{element_name}'")
            return False
        
        logger.debug(f"Adding zone '{zone_name}' to '{location}' section of policy '{element_name}'")
        
        try:
            # Ensure location is valid ('from', 'to', or 'both')
            locations = []
            if location == 'both':
                locations = ['from', 'to']
            else:
                locations = [location]
            
            modified = False
            
            for loc in locations:
                # Check if the location element exists
                loc_elem = element.find(f'./{loc}')
                if loc_elem is None:
                    logger.debug(f"Creating new {loc} element for policy '{element_name}'")
                    loc_elem = etree.SubElement(element, loc)
                
                # Check if this zone is already present
                members = loc_elem.xpath('./member')
                member_values = [m.text for m in members if m.text]
                
                if zone_name not in member_values:
                    member = etree.SubElement(loc_elem, 'member')
                    member.text = zone_name
                    logger.info(f"Added zone '{zone_name}' to {loc} section of policy '{element_name}'")
                    modified = True
                else:
                    logger.debug(f"Zone '{zone_name}' already exists in {loc} section of policy '{element_name}'")
            
            return modified
                
        except Exception as e:
            logger.error(f"Error adding zone to policy '{element_name}': {str(e)}", exc_info=True)
            return False
    
    def _change_action(self, element, params):
        """
        Change the action of a policy.
        
        Args:
            element: XML element to update
            params: Parameters for the operation
            
        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get('name', 'unknown')
        action = params.get('action')
        
        if not action:
            logger.warning(f"Missing action in change-action operation for policy '{element_name}'")
            return False
        
        logger.debug(f"Changing action of policy '{element_name}' to '{action}'")
        
        try:
            # Find the action element
            action_elem = element.find('./action')
            
            if action_elem is not None:
                old_action = action_elem.text
                if old_action != action:
                    action_elem.text = action
                    logger.info(f"Changed action of policy '{element_name}' from '{old_action}' to '{action}'")
                    return True
                else:
                    logger.debug(f"Policy '{element_name}' already has action '{action}'")
                    return False
            else:
                # Create new action element
                action_elem = etree.SubElement(element, 'action')
                action_elem.text = action
                logger.info(f"Added action '{action}' to policy '{element_name}'")
                return True
                
        except Exception as e:
            logger.error(f"Error changing action of policy '{element_name}': {str(e)}", exc_info=True)
            return False
    
    def _add_object(self, element, params):
        """
        Add an object to a policy's source, destination, or service field.
        
        Args:
            element: XML element to update
            params: Parameters for the operation
            
        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get('name', 'unknown')
        object_name = params.get('name')
        field = params.get('field')  # 'source', 'destination', 'service', 'application'
        
        if not object_name or not field:
            logger.warning(f"Missing name or field in add-object operation for element '{element_name}'")
            return False
        
        logger.debug(f"Adding object '{object_name}' to {field} section of element '{element_name}'")
        
        try:
            # Check if the field element exists
            field_elem = element.find(f'./{field}')
            if field_elem is None:
                logger.debug(f"Creating new {field} element for '{element_name}'")
                field_elem = etree.SubElement(element, field)
            
            # Check if this object is already present
            members = field_elem.xpath('./member')
            member_values = [m.text for m in members if m.text]
            
            if object_name not in member_values:
                member = etree.SubElement(field_elem, 'member')
                member.text = object_name
                logger.info(f"Added object '{object_name}' to {field} section of element '{element_name}'")
                return True
            else:
                logger.debug(f"Object '{object_name}' already exists in {field} section of element '{element_name}'")
                return False
                
        except Exception as e:
            logger.error(f"Error adding object to element '{element_name}': {str(e)}", exc_info=True)
            return False
    
    def _remove_object(self, element, params):
        """
        Remove an object from a policy's source, destination, or service field.
        
        Args:
            element: XML element to update
            params: Parameters for the operation
            
        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get('name', 'unknown')
        object_name = params.get('name')
        field = params.get('field')  # 'source', 'destination', 'service', 'application'
        
        if not object_name or not field:
            logger.warning(f"Missing name or field in remove-object operation for element '{element_name}'")
            return False
        
        logger.debug(f"Removing object '{object_name}' from {field} section of element '{element_name}'")
        
        try:
            # Find the field element
            field_elem = element.find(f'./{field}')
            if field_elem is None:
                logger.warning(f"Field {field} not found in element '{element_name}'")
                return False
            
            # Find the member element to remove
            for member in field_elem.xpath('./member'):
                if member.text == object_name:
                    field_elem.remove(member)
                    logger.info(f"Removed object '{object_name}' from {field} section of element '{element_name}'")
                    return True
            
            logger.debug(f"Object '{object_name}' not found in {field} section of element '{element_name}'")
            return False
                
        except Exception as e:
            logger.error(f"Error removing object from element '{element_name}': {str(e)}", exc_info=True)
            return False
    
    def _update_description(self, element, params):
        """
        Update the description of an element.
        
        Args:
            element: XML element to update
            params: Parameters for the operation
            
        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get('name', 'unknown')
        description = params.get('text')
        mode = params.get('mode', 'replace')  # 'replace', 'append', or 'prepend'
        
        if description is None:  # Allow empty string as a valid value to clear description
            logger.warning(f"Missing description text in update-description operation for element '{element_name}'")
            return False
        
        logger.debug(f"Updating description of element '{element_name}' with mode '{mode}'")
        
        try:
            # Find the description element
            desc_elem = element.find('./description')
            
            # Different behavior based on mode
            if mode == 'replace' or desc_elem is None:
                if desc_elem is not None:
                    old_desc = desc_elem.text or ""
                    desc_elem.text = description
                    logger.info(f"Replaced description of element '{element_name}': '{old_desc}' -> '{description}'")
                else:
                    desc_elem = etree.SubElement(element, 'description')
                    desc_elem.text = description
                    logger.info(f"Added description to element '{element_name}': '{description}'")
                return True
                
            elif mode == 'append':
                old_desc = desc_elem.text or ""
                new_desc = old_desc + description
                desc_elem.text = new_desc
                logger.info(f"Appended to description of element '{element_name}': '{old_desc}' -> '{new_desc}'")
                return True
                
            elif mode == 'prepend':
                old_desc = desc_elem.text or ""
                new_desc = description + old_desc
                desc_elem.text = new_desc
                logger.info(f"Prepended to description of element '{element_name}': '{old_desc}' -> '{new_desc}'")
                return True
                
            else:
                logger.warning(f"Unsupported description update mode: {mode}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating description of element '{element_name}': {str(e)}", exc_info=True)
            return False
    
    def _enable_disable(self, element, params):
        """
        Enable or disable an element.
        
        Args:
            element: XML element to update
            params: Parameters for the operation
            
        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get('name', 'unknown')
        action = params.get('action')  # 'enable' or 'disable'
        
        if not action or action not in ['enable', 'disable']:
            logger.warning(f"Invalid action in enable-disable operation for element '{element_name}': {action}")
            return False
        
        logger.debug(f"{action.capitalize()}ing element '{element_name}'")
        
        try:
            # Find the disabled element
            disabled_elem = element.find('./disabled')
            
            if action == 'disable':
                # Disable the element
                if disabled_elem is not None:
                    if disabled_elem.text != 'yes':
                        disabled_elem.text = 'yes'
                        logger.info(f"Disabled element '{element_name}'")
                        return True
                    else:
                        logger.debug(f"Element '{element_name}' is already disabled")
                        return False
                else:
                    disabled_elem = etree.SubElement(element, 'disabled')
                    disabled_elem.text = 'yes'
                    logger.info(f"Disabled element '{element_name}'")
                    return True
            else:
                # Enable the element
                if disabled_elem is not None:
                    if disabled_elem.text == 'yes':
                        element.remove(disabled_elem)
                        logger.info(f"Enabled element '{element_name}'")
                        return True
                    else:
                        logger.debug(f"Element '{element_name}' is already enabled")
                        return False
                else:
                    logger.debug(f"Element '{element_name}' is already enabled (no disabled tag)")
                    return False
                
        except Exception as e:
            logger.error(f"Error {action}ing element '{element_name}': {str(e)}", exc_info=True)
            return False
    
    def _update_logging(self, element, params):
        """
        Update logging options for a policy.
        
        Args:
            element: XML element to update
            params: Parameters for the operation
            
        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get('name', 'unknown')
        log_setting = params.get('setting')  # 'log-start', 'log-end', 'log-both', 'log-none'
        
        if not log_setting:
            logger.warning(f"Missing log setting in update-logging operation for policy '{element_name}'")
            return False
        
        logger.debug(f"Updating logging options for policy '{element_name}' to '{log_setting}'")
        
        try:
            # Different log settings require different elements
            modified = False
            
            # First remove any existing log settings
            log_start = element.find('./log-start')
            log_end = element.find('./log-end')
            
            if log_start is not None:
                element.remove(log_start)
                modified = True
                
            if log_end is not None:
                element.remove(log_end)
                modified = True
            
            # Then add the new log setting
            if log_setting == 'log-start':
                etree.SubElement(element, 'log-start')
                logger.info(f"Set log-start for policy '{element_name}'")
                modified = True
                
            elif log_setting == 'log-end':
                etree.SubElement(element, 'log-end')
                logger.info(f"Set log-end for policy '{element_name}'")
                modified = True
                
            elif log_setting == 'log-both':
                etree.SubElement(element, 'log-start')
                etree.SubElement(element, 'log-end')
                logger.info(f"Set log-both (log-start and log-end) for policy '{element_name}'")
                modified = True
                
            elif log_setting == 'log-none':
                # Just removing existing log settings is sufficient
                if modified:
                    logger.info(f"Set log-none for policy '{element_name}'")
                else:
                    logger.debug(f"Policy '{element_name}' already has log-none (no logging tags)")
            else:
                logger.warning(f"Unsupported log setting: {log_setting}")
                return False
            
            return modified
                
        except Exception as e:
            logger.error(f"Error updating logging for policy '{element_name}': {str(e)}", exc_info=True)
            return False
    
    def _update_ip_address(self, element, params):
        """
        Update the IP address of an address object.
        
        Args:
            element: XML element to update
            params: Parameters for the operation
            
        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get('name', 'unknown')
        ip_type = params.get('type')  # 'ip-netmask', 'ip-range', 'fqdn'
        value = params.get('value')
        
        if not ip_type or not value:
            logger.warning(f"Missing type or value in update-ip-address operation for object '{element_name}'")
            return False
        
        logger.debug(f"Updating {ip_type} of address object '{element_name}' to '{value}'")
        
        try:
            # First, remove any existing IP address elements
            for type_name in ['ip-netmask', 'ip-range', 'fqdn']:
                elem = element.find(f'./{type_name}')
                if elem is not None:
                    element.remove(elem)
            
            # Add the new IP address element
            new_elem = etree.SubElement(element, ip_type)
            new_elem.text = value
            logger.info(f"Updated address object '{element_name}' with {ip_type}='{value}'")
            return True
                
        except Exception as e:
            logger.error(f"Error updating IP address of object '{element_name}': {str(e)}", exc_info=True)
            return False
            
    def bulk_merge_objects(
        self,
        source_tree: etree._ElementTree,
        object_type: str,
        criteria: Optional[Dict[str, Any]],
        source_context_type: str,
        target_context_type: str,
        source_device_type: Optional[str] = None,
        source_version: Optional[str] = None,
        skip_if_exists: bool = True,
        copy_references: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> Tuple[int, int]:
        """
        Merge objects from a source tree to the target tree based on criteria.
        
        This method combines the ConfigQuery functionality with ObjectMerger to 
        perform bulk merging of objects from one configuration to another.
        
        Args:
            source_tree: Source ElementTree containing objects to merge from
            object_type: Type of object to merge (address, service, etc.)
            criteria: Dictionary of criteria to select objects to merge
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            source_device_type: Type of source device ("firewall" or "panorama")
            source_version: PAN-OS version of source configuration
            skip_if_exists: Skip if object already exists in target (deprecated, use conflict_strategy instead)
            copy_references: Copy object references (e.g., address group members)
            conflict_strategy: Strategy to use when resolving conflicts with existing objects
            **kwargs: Additional parameters like source_device_group, target_device_group, etc.
            
        Returns:
            Tuple[int, int]: (number of objects merged, total number of objects attempted)
        """
        logger.info(f"Performing bulk merge of {object_type} objects from {source_context_type} to {target_context_type}")
        logger.debug(f"Merge criteria: {criteria}")
        
        # Set default source device type and version if not provided
        source_device_type = source_device_type or self.device_type
        source_version = source_version or self.version
        
        # Extract source context parameters
        source_params = {}
        for k, v in kwargs.items():
            if k.startswith('source_'):
                source_params[k] = v
        
        # Create a query object for the source tree
        source_query = ConfigQuery(
            source_tree, 
            source_device_type, 
            source_context_type, 
            source_version, 
            **source_params
        )
        
        # Select objects to merge
        objects_to_merge = source_query.select_objects(object_type, criteria)
        
        if not objects_to_merge:
            logger.warning("No objects found in source matching the criteria")
            return 0, 0
            
        logger.info(f"Found {len(objects_to_merge)} objects in source matching the criteria")
        
        # Create the merger
        merger = ObjectMerger(
            source_tree,
            self.tree,
            source_device_type,
            self.device_type,
            source_version,
            self.version
        )
        
        # Merge each object
        merged_count = 0
        for obj in objects_to_merge:
            name = obj.get('name')
            if not name:
                logger.warning("Skipping object with no name attribute")
                continue
                
            logger.info(f"Merging {object_type} object '{name}'")
            
            # Extract target context parameters
            target_params = {}
            for k, v in kwargs.items():
                if k.startswith('target_'):
                    target_params[k] = v
            
            try:
                success = merger.copy_object(
                    object_type,
                    name,
                    source_context_type,
                    target_context_type,
                    skip_if_exists,
                    copy_references,
                    conflict_strategy=conflict_strategy,
                    **{**source_params, **target_params}
                )
                
                if success:
                    merged_count += 1
                    logger.info(f"Successfully merged {object_type} object '{name}'")
                else:
                    logger.warning(f"Failed to merge {object_type} object '{name}'")
                    
            except Exception as e:
                logger.error(f"Error merging {object_type} object '{name}': {str(e)}", exc_info=True)
        
        logger.info(f"Bulk merge completed: {merged_count} of {len(objects_to_merge)} objects merged")
        return merged_count, len(objects_to_merge)
        
    def bulk_deduplicate_objects(
        self,
        object_type: str,
        criteria: Optional[Dict[str, Any]] = None,
        primary_name_strategy: str = "shortest",
        dry_run: bool = False,
        **kwargs
    ) -> Tuple[Dict[str, Dict[str, Any]], int]:
        """
        Find and merge duplicate objects in the configuration.
        
        This method integrates with the DeduplicationEngine to find and merge 
        duplicate objects based on their values.
        
        Args:
            object_type: Type of object to deduplicate (address, service, tag)
            criteria: Optional criteria to filter objects before deduplication
            primary_name_strategy: Strategy for selecting primary object name 
                                  ("first", "shortest", "longest", "alphabetical")
            dry_run: If True, only identify duplicates but don't merge them
            **kwargs: Additional context parameters
            
        Returns:
            Tuple: (
                Dictionary containing details of the changes made,
                Number of duplicate objects merged
            )
        """
        logger.info(f"Performing bulk deduplication of {object_type} objects")
        
        # If criteria is provided, first filter objects
        if criteria:
            logger.info(f"Pre-filtering objects using criteria: {criteria}")
            objects = self.query.select_objects(object_type, criteria)
            
            if not objects:
                logger.warning(f"No {object_type} objects found matching the criteria")
                return {}, 0
                
            logger.info(f"Found {len(objects)} objects matching criteria for deduplication")
            
            # We need to use these specific objects for deduplication
            # Currently we don't have a way to pass specific objects to the deduplication engine
            # This would require enhancing the deduplication engine to accept a list of objects
            logger.warning("Criteria-based filtering for deduplication is not fully implemented yet")
            # For now, we'll proceed with deduplicating all objects of this type
        
        # Create the deduplication engine
        dedup_engine = DeduplicationEngine(
            self.tree, 
            self.device_type, 
            self.context_type, 
            self.version, 
            **self.context_kwargs
        )
        
        # Find duplicate objects
        logger.info(f"Finding duplicate {object_type} objects")
        duplicates, references = dedup_engine.find_duplicates(object_type)
        
        if not duplicates:
            logger.info(f"No duplicate {object_type} objects found")
            return {}, 0
        
        total_duplicates = sum(len(group) - 1 for group in duplicates.values())
        logger.info(f"Found {total_duplicates} duplicate objects across {len(duplicates)} unique values")
        
        # If dry run, just return the duplicates without merging
        if dry_run:
            logger.info("Dry run mode, not merging duplicates")
            changes = {}
            
            for value, objects in duplicates.items():
                object_names = [name for name, _ in objects]
                primary = object_names[0]  # Just use first as example
                
                changes[value] = {
                    "primary": primary,
                    "merged": object_names[1:],
                    "references_updated": []
                }
            
            return changes, 0
        
        # Merge the duplicate objects
        logger.info(f"Merging duplicate {object_type} objects using '{primary_name_strategy}' strategy")
        changes = dedup_engine.merge_duplicates(duplicates, references, primary_name_strategy)
        
        merged_count = sum(len(info["merged"]) for info in changes.values())
        reference_count = sum(len(info["references_updated"]) for info in changes.values())
        
        logger.info(f"Deduplication complete: merged {merged_count} objects and updated {reference_count} references")
        
        return changes, merged_count