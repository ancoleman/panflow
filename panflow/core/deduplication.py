"""
Deduplication engine for PANFlow.

This module provides classes and functions to identify and merge duplicate objects
in PAN-OS configurations, with reference tracking to maintain configuration integrity.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Set
from lxml import etree

from .xpath_resolver import get_object_xpath
from .config_loader import xpath_search

# Initialize logger
logger = logging.getLogger("panflow")

class DeduplicationEngine:
    """
    Engine for finding and merging duplicate objects in PAN-OS configurations.
    
    This class provides methods to identify duplicate objects based on their values
    and merge them while updating all references.
    """
    
    def __init__(self, tree, device_type, context_type, version, **kwargs):
        """
        Initialize the deduplication engine.
        
        Args:
            tree: ElementTree containing the configuration
            device_type: Type of device ("firewall" or "panorama")
            context_type: Type of context (shared, device_group, vsys)
            version: PAN-OS version
            **kwargs: Additional parameters (device_group, vsys, etc.)
        """
        logger.info("Initializing DeduplicationEngine")
        self.tree = tree
        self.device_type = device_type
        self.context_type = context_type
        self.version = version
        self.context_kwargs = kwargs
        
        logger.debug(f"Configuration parameters: device_type={device_type}, context_type={context_type}, version={version}")
        logger.debug(f"Context parameters: {kwargs}")
        
    def find_duplicate_addresses(self, reference_tracking=True):
        """
        Find duplicate address objects based on their values.
        
        Args:
            reference_tracking: Whether to track references to objects (default: True)
            
        Returns:
            Tuple of (duplicates, references):
                - duplicates: Dictionary mapping values to lists of (name, element) tuples
                - references: Dictionary mapping object names to lists of references
        """
        logger.info("Finding duplicate address objects")
        logger.debug(f"Reference tracking: {reference_tracking}")
        
        # Get all address objects
        try:
            address_xpath = get_object_xpath('address', self.device_type, self.context_type, 
                                            self.version, **self.context_kwargs)
            
            logger.debug(f"Retrieving address objects using XPath: {address_xpath}")
            addresses = xpath_search(self.tree, address_xpath)
            
            logger.info(f"Found {len(addresses)} address objects to analyze")
            
        except Exception as e:
            logger.error(f"Error retrieving address objects: {e}", exc_info=True)
            return {}, {}
        
        # Group by value
        by_value = {}
        
        logger.debug("Grouping address objects by value")
        for addr in addresses:
            try:
                name = addr.get('name', '')
                if not name:
                    logger.warning(f"Skipping address object with no name attribute")
                    continue
                
                # Determine the key for grouping
                value_key = None
                ip_netmask = addr.find('./ip-netmask')
                if ip_netmask is not None and ip_netmask.text:
                    value_key = f"ip-netmask:{ip_netmask.text}"
                    logger.debug(f"Address '{name}' has ip-netmask value: {ip_netmask.text}")
                
                fqdn = addr.find('./fqdn')
                if fqdn is not None and fqdn.text:
                    value_key = f"fqdn:{fqdn.text}"
                    logger.debug(f"Address '{name}' has fqdn value: {fqdn.text}")
                
                ip_range = addr.find('./ip-range')
                if ip_range is not None and ip_range.text:
                    value_key = f"ip-range:{ip_range.text}"
                    logger.debug(f"Address '{name}' has ip-range value: {ip_range.text}")
                
                if value_key:
                    if value_key not in by_value:
                        by_value[value_key] = []
                    by_value[value_key].append((name, addr))
                else:
                    logger.warning(f"Address object '{name}' has no recognizable value, skipping")
            
            except Exception as e:
                logger.error(f"Error processing address object: {e}", exc_info=True)
                continue
        
        # Find duplicates (groups with more than one object)
        duplicates = {k: v for k, v in by_value.items() if len(v) > 1}
        
        duplicate_count = sum(len(v) - 1 for v in duplicates.values())
        unique_values_count = len(duplicates)
        
        if duplicates:
            logger.info(f"Found {duplicate_count} duplicate objects across {unique_values_count} unique values")
            for value, objects in duplicates.items():
                names = [name for name, _ in objects]
                logger.debug(f"Duplicates with value '{value}': {', '.join(names)}")
        else:
            logger.info("No duplicate address objects found")
        
        # If reference tracking is enabled, find all references
        references = {}
        if reference_tracking and duplicates:
            logger.info("Reference tracking enabled, looking for references to duplicate objects")
            try:
                references = self._find_references()
                reference_count = sum(len(refs) for refs in references.values())
                logger.info(f"Found {reference_count} references to objects")
            except Exception as e:
                logger.error(f"Error finding references: {e}", exc_info=True)
        
        return duplicates, references
    
    def _find_references(self):
        """
        Find all references to address objects in the configuration.
        
        Returns:
            Dictionary mapping object names to lists of (xpath, element) tuples
        """
        logger.debug("Finding references to address objects")
        references = {}
        
        # Search for references in address groups
        try:
            logger.debug("Searching for references in address groups")
            group_xpath = get_object_xpath('address_group', self.device_type, self.context_type, 
                                         self.version, **self.context_kwargs)
            
            address_groups = xpath_search(self.tree, group_xpath)
            logger.debug(f"Found {len(address_groups)} address groups to check")
            
            for group in address_groups:
                group_name = group.get('name', 'unknown')
                members = group.xpath('.//member')
                
                for member in members:
                    if member.text:
                        member_name = member.text
                        if member_name not in references:
                            references[member_name] = []
                        
                        ref_path = f"address-group:{group_name}"
                        references[member_name].append((ref_path, member))
                        logger.debug(f"Found reference to '{member_name}' in address group '{group_name}'")
        
        except Exception as e:
            logger.error(f"Error finding references in address groups: {e}", exc_info=True)
        
        # Search for references in security policies
        try:
            logger.debug("Searching for references in security policies")
            # Determine security policy XPath based on device type
            if self.device_type.lower() == 'panorama':
                policy_paths = [
                    ('pre-rulebase/security/rules/entry', 'pre-security'),
                    ('post-rulebase/security/rules/entry', 'post-security')
                ]
            else:
                policy_paths = [
                    ('rulebase/security/rules/entry', 'security')
                ]
            
            # Get context base path
            from .xpath_resolver import get_context_xpath
            base_path = get_context_xpath(self.device_type, self.context_type, 
                                         self.version, **self.context_kwargs)
            
            # Check each policy path
            for path_suffix, path_name in policy_paths:
                policy_xpath = f"{base_path}/{path_suffix}"
                policies = xpath_search(self.tree, policy_xpath)
                
                logger.debug(f"Found {len(policies)} {path_name} policies to check")
                
                # Check source and destination in each policy
                for policy in policies:
                    policy_name = policy.get('name', 'unknown')
                    
                    # Check source addresses
                    for source in policy.xpath('./source/member'):
                        if source.text and source.text != 'any':
                            source_name = source.text
                            if source_name not in references:
                                references[source_name] = []
                            
                            ref_path = f"{path_name}:{policy_name}:source"
                            references[source_name].append((ref_path, source))
                            logger.debug(f"Found reference to '{source_name}' in policy '{policy_name}' (source)")
                    
                    # Check destination addresses
                    for dest in policy.xpath('./destination/member'):
                        if dest.text and dest.text != 'any':
                            dest_name = dest.text
                            if dest_name not in references:
                                references[dest_name] = []
                            
                            ref_path = f"{path_name}:{policy_name}:destination"
                            references[dest_name].append((ref_path, dest))
                            logger.debug(f"Found reference to '{dest_name}' in policy '{policy_name}' (destination)")
        
        except Exception as e:
            logger.error(f"Error finding references in security policies: {e}", exc_info=True)
        
        # Log summary of references found
        ref_count = sum(len(refs) for refs in references.values())
        object_count = len(references)
        logger.info(f"Found {ref_count} references to {object_count} distinct objects")
        
        return references
    
    def merge_duplicates(self, duplicates, references, primary_name_strategy='first'):
        """
        Merge duplicate objects, keeping one and updating references.
        
        Args:
            duplicates: Dictionary of duplicate objects (from find_duplicate_addresses)
            references: Dictionary of references (from find_duplicate_addresses)
            primary_name_strategy: Strategy for choosing primary object 
                                ('first', 'shortest', 'longest', 'alphabetical')
            
        Returns:
            List of changes made (operation, name, element)
        """
        logger.info(f"Merging duplicate objects using strategy: {primary_name_strategy}")
        changes = []
        
        # Track processed objects to handle circular references
        processed_objects = set()
        
        # Validate inputs
        if not duplicates:
            logger.warning("No duplicates provided, nothing to merge")
            return changes
        
        duplicate_sets = len(duplicates)
        duplicate_count = sum(len(objects) - 1 for objects in duplicates.values())
        logger.info(f"Processing {duplicate_count} duplicates across {duplicate_sets} unique values")
        
        # Sort duplicate sets by dependency order
        # This helps ensure we process independent objects before their dependents
        dependency_order = self._sort_by_dependencies(duplicates, references)
        
        for value_key in dependency_order:
            objects = duplicates.get(value_key, [])
            logger.debug(f"Processing duplicates with value: {value_key}")
            
            # Skip if there's only one object
            if len(objects) <= 1:
                logger.warning(f"Skipping value {value_key} with only {len(objects)} object")
                continue
            
            # Determine which object to keep
            try:
                primary = self._select_primary_object(objects, primary_name_strategy)
                primary_name, primary_elem = primary
                
                # Skip if we've already processed this primary
                if primary_name in processed_objects:
                    logger.warning(f"Object {primary_name} already processed, skipping to avoid circular references")
                    continue
                    
                processed_objects.add(primary_name)
                
                logger.info(f"Selected primary object '{primary_name}' for value {value_key}")
                
                # Process each duplicate
                for name, obj in objects:
                    # Skip the primary object
                    if name == primary_name:
                        continue
                        
                    # Skip if we've already processed this object
                    if name in processed_objects:
                        logger.warning(f"Object {name} already processed, skipping to avoid circular references")
                        continue
                        
                    processed_objects.add(name)
                    logger.debug(f"Processing duplicate: {name}")
                    
                    # Update references to this object
                    if name in references:
                        ref_count = len(references[name])
                        logger.info(f"Updating {ref_count} references to '{name}'")
                        
                        for ref_path, ref_elem in references[name]:
                            try:
                                # Update the reference to point to primary_name
                                old_text = ref_elem.text
                                ref_elem.text = primary_name
                                changes.append(('update_reference', f"{ref_path}: {old_text} -> {primary_name}", ref_elem))
                                logger.debug(f"Updated reference in {ref_path}: {old_text} -> {primary_name}")
                            except Exception as e:
                                logger.error(f"Error updating reference to '{name}' in {ref_path}: {str(e)}")
                    else:
                        logger.debug(f"No references found for '{name}'")
                    
                    # Queue this object for deletion
                    logger.debug(f"Queueing object '{name}' for deletion")
                    changes.append(('delete', name, obj))
            
            except Exception as e:
                logger.error(f"Error processing duplicates for value {value_key}: {str(e)}")
                continue
    
        # Log changes summary
        delete_count = sum(1 for op, _, _ in changes if op == 'delete')
        ref_update_count = sum(1 for op, _, _ in changes if op == 'update_reference')
        
        logger.info(f"Changes to be made: {delete_count} objects to delete, {ref_update_count} references to update")
        
        return changes
    
    def _select_primary_object(self, objects, strategy):
        """
        Select the primary object to keep based on the specified strategy.
        
        Args:
            objects: List of (name, element) tuples
            strategy: Selection strategy ('first', 'shortest', etc.)
            
        Returns:
            Tuple of (name, element) for the selected primary object
        """
        logger.debug(f"Selecting primary object using strategy: {strategy}")
        
        if not objects:
            logger.error("No objects provided for primary selection")
            raise ValueError("No objects provided")
        
        if strategy == 'first':
            logger.debug("Using 'first' strategy - selecting first object")
            return objects[0]
        
        elif strategy == 'shortest':
            logger.debug("Using 'shortest' strategy - selecting object with shortest name")
            return min(objects, key=lambda x: len(x[0]))
        
        elif strategy == 'longest':
            logger.debug("Using 'longest' strategy - selecting object with longest name")
            return max(objects, key=lambda x: len(x[0]))
        
        elif strategy == 'alphabetical':
            logger.debug("Using 'alphabetical' strategy - selecting object with first alphabetical name")
            return min(objects, key=lambda x: x[0])
        
        else:
            logger.warning(f"Unknown strategy: {strategy}, falling back to 'first'")
            return objects[0]
        
    def _sort_by_dependencies(self, duplicates, references):
        """
        Sort duplicate sets based on their dependencies to avoid circular reference issues.
        
        Args:
            duplicates: Dictionary of duplicate objects
            references: Dictionary of references
            
        Returns:
            List of value_keys in dependency order
        """
        dependency_graph = {}
        value_key_to_names = {}
        
        # Build mapping of value_keys to object names
        for value_key, objects in duplicates.items():
            names = [name for name, _ in objects]
            value_key_to_names[value_key] = set(names)
            dependency_graph[value_key] = set()
        
        # Build dependency graph
        for value_key, objects in duplicates.items():
            names = value_key_to_names[value_key]
            
            # Find dependencies
            for dependent_value_key, dependent_names in value_key_to_names.items():
                if value_key == dependent_value_key:
                    continue
                
                # Check if any object in this set references any object in the dependent set
                for name in names:
                    if name in references:
                        for ref_path, _ in references[name]:
                            for dependent_name in dependent_names:
                                if dependent_name in ref_path:
                                    # This set depends on the dependent set
                                    dependency_graph[value_key].add(dependent_value_key)
        
        # Perform topological sort
        result = []
        visited = set()
        temp_mark = set()
        
        def visit(node):
            if node in visited:
                return
            if node in temp_mark:
                # Circular dependency detected, but we'll continue
                logger.warning(f"Circular dependency detected for value {node}")
                return
            
            temp_mark.add(node)
            
            for dep in dependency_graph[node]:
                visit(dep)
            
            temp_mark.remove(node)
            visited.add(node)
            result.append(node)
        
        for node in dependency_graph:
            if node not in visited:
                visit(node)
        
        # Return in reverse order (least dependent first)
        return result[::-1]