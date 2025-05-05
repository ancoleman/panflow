"""
Conflict resolver for PANFlow.

This module provides strategies for resolving conflicts when merging objects between
different PAN-OS configurations.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Set
from lxml import etree
from enum import Enum

from .xml_utils import find_element, find_elements, clone_element, merge_elements, element_exists

# Initialize logger
logger = logging.getLogger("panflow")

class ConflictStrategy(Enum):
    """
    Enumeration of possible conflict resolution strategies.
    """
    SKIP = "skip"                   # Skip if object exists in target (default)
    OVERWRITE = "overwrite"         # Always overwrite existing object
    MERGE = "merge"                 # Merge contents of source and target objects
    RENAME = "rename"               # Rename object to avoid conflict
    KEEP_NEWER = "keep_newer"       # Keep the newer object based on timestamp
    KEEP_TARGET = "keep_target"     # Always keep the target object
    KEEP_SOURCE = "keep_source"     # Always use the source object (like OVERWRITE)
    INTERACTIVE = "interactive"     # Ask user for resolution (not implemented)

class ConflictResolver:
    """
    Class for resolving conflicts when merging objects.
    
    Provides different strategies for handling cases where an object already
    exists in the target configuration.
    """
    
    def __init__(self, default_strategy: ConflictStrategy = ConflictStrategy.SKIP):
        """
        Initialize with a default conflict resolution strategy.
        
        Args:
            default_strategy: Default strategy to use when not specified
        """
        logger.debug(f"Initializing ConflictResolver with default strategy: {default_strategy.value}")
        self.default_strategy = default_strategy
        
    def resolve_conflict(
        self,
        source_object: etree._Element,
        target_object: etree._Element,
        object_type: str,
        object_name: str,
        strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> Tuple[bool, Optional[etree._Element], str]:
        """
        Resolve a conflict between source and target objects.
        
        This method applies the specified strategy to resolve conflicts when
        an object already exists in the target configuration.
        
        Args:
            source_object: Source object element
            target_object: Target object element that conflicts
            object_type: Type of the objects (address, service, etc.)
            object_name: Name of the objects
            strategy: Conflict resolution strategy to use (defaults to self.default_strategy)
            **kwargs: Additional parameters for specific strategies
            
        Returns:
            Tuple[bool, Optional[etree._Element], str]: (success, resolved_object, message)
        """
        strategy = strategy or self.default_strategy
        logger.info(f"Resolving conflict for {object_type} '{object_name}' using strategy: {strategy.value}")
        
        if strategy == ConflictStrategy.SKIP:
            return self._skip_strategy(source_object, target_object, object_type, object_name)
        elif strategy == ConflictStrategy.OVERWRITE or strategy == ConflictStrategy.KEEP_SOURCE:
            return self._overwrite_strategy(source_object, target_object, object_type, object_name)
        elif strategy == ConflictStrategy.MERGE:
            return self._merge_strategy(source_object, target_object, object_type, object_name)
        elif strategy == ConflictStrategy.RENAME:
            return self._rename_strategy(source_object, target_object, object_type, object_name, **kwargs)
        elif strategy == ConflictStrategy.KEEP_NEWER:
            return self._keep_newer_strategy(source_object, target_object, object_type, object_name)
        elif strategy == ConflictStrategy.KEEP_TARGET:
            return self._keep_target_strategy(source_object, target_object, object_type, object_name)
        elif strategy == ConflictStrategy.INTERACTIVE:
            logger.warning(f"Interactive conflict resolution not implemented, using {self.default_strategy.value} instead")
            return self.resolve_conflict(source_object, target_object, object_type, object_name, self.default_strategy)
        else:
            logger.error(f"Unknown conflict resolution strategy: {strategy}")
            return False, None, f"Unknown conflict resolution strategy: {strategy}"
    
    def _skip_strategy(
        self,
        source_object: etree._Element,
        target_object: etree._Element,
        object_type: str,
        object_name: str
    ) -> Tuple[bool, Optional[etree._Element], str]:
        """Skip the conflict and keep the target object."""
        logger.debug(f"Skipping {object_type} '{object_name}' as it already exists in target")
        return False, None, f"Object already exists in target, skipped"
    
    def _overwrite_strategy(
        self,
        source_object: etree._Element,
        target_object: etree._Element,
        object_type: str,
        object_name: str
    ) -> Tuple[bool, Optional[etree._Element], str]:
        """Overwrite the target object with the source object."""
        logger.debug(f"Overwriting existing {object_type} '{object_name}' with source object")
        return True, clone_element(source_object), f"Existing object overwritten with source"
    
    def _merge_strategy(
        self,
        source_object: etree._Element,
        target_object: etree._Element,
        object_type: str,
        object_name: str
    ) -> Tuple[bool, Optional[etree._Element], str]:
        """Merge source and target objects."""
        logger.debug(f"Merging {object_type} '{object_name}' with existing object")
        
        try:
            # Create a deep copy of the target object to modify
            merged_object = clone_element(target_object)
            
            # Apply object-specific merge logic
            if object_type in ["address-group", "address_group"]:
                self._merge_address_group(source_object, merged_object)
            elif object_type in ["service-group", "service_group"]:
                self._merge_service_group(source_object, merged_object)
            elif object_type in ["tag"]:
                self._merge_tag(source_object, merged_object)
            else:
                # For other object types, use a generic merge
                merged_object = merge_elements(target_object, source_object)
                
            return True, merged_object, f"Objects merged successfully"
            
        except Exception as e:
            logger.error(f"Error merging objects: {e}", exc_info=True)
            return False, None, f"Error merging objects: {str(e)}"
    
    def _rename_strategy(
        self,
        source_object: etree._Element,
        target_object: etree._Element,
        object_type: str,
        object_name: str,
        **kwargs
    ) -> Tuple[bool, Optional[etree._Element], str]:
        """Rename the source object to avoid conflict."""
        # Default suffix is "_imported" if not provided
        suffix = kwargs.get("suffix", "_imported")
        
        logger.debug(f"Renaming {object_type} '{object_name}' to avoid conflict")
        
        # Create a copy of the source object
        renamed_object = clone_element(source_object)
        
        # Change the name attribute
        new_name = f"{object_name}{suffix}"
        renamed_object.set("name", new_name)
        
        logger.info(f"Renamed {object_type} from '{object_name}' to '{new_name}'")
        return True, renamed_object, f"Object renamed to '{new_name}'"
    
    def _keep_newer_strategy(
        self,
        source_object: etree._Element,
        target_object: etree._Element,
        object_type: str,
        object_name: str
    ) -> Tuple[bool, Optional[etree._Element], str]:
        """Keep the newer object based on last-modified timestamp if available."""
        # Check for last-modified timestamps (these may not be available in all objects)
        source_timestamp = self._get_timestamp(source_object)
        target_timestamp = self._get_timestamp(target_object)
        
        if source_timestamp is None or target_timestamp is None:
            logger.warning(f"Cannot determine timestamps for {object_type} '{object_name}', falling back to overwrite strategy")
            return self._overwrite_strategy(source_object, target_object, object_type, object_name)
            
        if source_timestamp > target_timestamp:
            logger.debug(f"Source {object_type} '{object_name}' is newer, overwriting target")
            return True, clone_element(source_object), f"Source object is newer, target overwritten"
        else:
            logger.debug(f"Target {object_type} '{object_name}' is newer or same age, keeping target")
            return False, None, f"Target object is newer or same age, kept target"
    
    def _keep_target_strategy(
        self,
        source_object: etree._Element,
        target_object: etree._Element,
        object_type: str,
        object_name: str
    ) -> Tuple[bool, Optional[etree._Element], str]:
        """Always keep the target object."""
        logger.debug(f"Keeping existing {object_type} '{object_name}' in target")
        return False, None, f"Kept existing target object"
    
    def _merge_address_group(
        self,
        source_object: etree._Element,
        target_object: etree._Element
    ) -> None:
        """Merge address group objects."""
        # Handle static members
        source_static = find_element(source_object, './static')
        target_static = find_element(target_object, './static')
        
        if source_static is not None and target_static is not None:
            # Both groups are static, merge members
            self._merge_members(source_static, target_static)
        elif source_static is not None and target_static is None:
            # Source is static, target is dynamic - cannot merge incompatible types
            logger.warning(f"Cannot merge static address group with dynamic address group")
            # Maybe copy description or other attributes?
            self._copy_description(source_object, target_object)
        elif source_static is None and target_static is not None:
            # Source is dynamic, target is static - cannot merge incompatible types
            logger.warning(f"Cannot merge dynamic address group with static address group")
            # Maybe copy description or other attributes?
            self._copy_description(source_object, target_object)
        elif source_static is None and target_static is None:
            # Both groups are dynamic
            source_dynamic = find_element(source_object, './dynamic')
            target_dynamic = find_element(target_object, './dynamic')
            
            if source_dynamic is not None and target_dynamic is not None:
                # Copy description
                self._copy_description(source_object, target_object)
                
                # Merge filters (this is complex and might require a specialized filter parser)
                self._merge_filters(source_dynamic, target_dynamic)
    
    def _merge_service_group(
        self,
        source_object: etree._Element,
        target_object: etree._Element
    ) -> None:
        """Merge service group objects."""
        # Merge members
        source_members = find_element(source_object, './members')
        target_members = find_element(target_object, './members')
        
        if source_members is not None and target_members is not None:
            self._merge_members(source_members, target_members)
            
        # Copy description
        self._copy_description(source_object, target_object)
    
    def _merge_tag(
        self,
        source_object: etree._Element,
        target_object: etree._Element
    ) -> None:
        """Merge tag objects."""
        # For tags, we typically want to keep comments, colors, etc.
        # but there's not much to "merge" - so we'll just copy specific attributes
        
        # Copy color if target doesn't have one
        source_color = find_element(source_object, './color')
        target_color = find_element(target_object, './color')
        
        if source_color is not None and source_color.text and (target_color is None or not target_color.text):
            if target_color is None:
                target_color = etree.SubElement(target_object, 'color')
            target_color.text = source_color.text
            
        # Copy comments if target doesn't have them
        self._copy_element_if_empty(source_object, target_object, './comments')
    
    def _merge_members(
        self,
        source_elem: etree._Element,
        target_elem: etree._Element
    ) -> None:
        """Merge member elements from source to target."""
        source_members = find_elements(source_elem, './member')
        existing_members = set()
        
        # Collect existing members
        for member in find_elements(target_elem, './member'):
            if member.text:
                existing_members.add(member.text)
        
        # Add new members
        for member in source_members:
            if member.text and member.text not in existing_members:
                new_member = etree.SubElement(target_elem, 'member')
                new_member.text = member.text
                existing_members.add(member.text)
    
    def _merge_filters(
        self,
        source_dynamic: etree._Element,
        target_dynamic: etree._Element
    ) -> None:
        """Merge dynamic filters (for address groups)."""
        source_filter = find_element(source_dynamic, './filter')
        target_filter = find_element(target_dynamic, './filter')
        
        if source_filter is not None and source_filter.text and target_filter is not None and target_filter.text:
            # This is a simplified approach that just combines filters with "and"
            # A real implementation would parse and combine the filters more intelligently
            if source_filter.text != target_filter.text:
                new_filter = f"({target_filter.text}) and ({source_filter.text})"
                target_filter.text = new_filter
        elif source_filter is not None and source_filter.text and (target_filter is None or not target_filter.text):
            if target_filter is None:
                target_filter = etree.SubElement(target_dynamic, 'filter')
            target_filter.text = source_filter.text
    
    def _copy_description(
        self,
        source_object: etree._Element,
        target_object: etree._Element
    ) -> None:
        """Copy description from source to target if target doesn't have one."""
        self._copy_element_if_empty(source_object, target_object, './description')
    
    def _copy_element_if_empty(
        self,
        source_object: etree._Element,
        target_object: etree._Element,
        xpath: str
    ) -> None:
        """Copy an element from source to target if target doesn't have it or is empty."""
        source_elem = find_element(source_object, xpath)
        target_elem = find_element(target_object, xpath)
        
        if source_elem is not None and source_elem.text and (target_elem is None or not target_elem.text):
            element_name = xpath.lstrip('./').split('/')[0]
            
            if target_elem is None:
                target_elem = etree.SubElement(target_object, element_name)
            
            target_elem.text = source_elem.text
    
    def _get_timestamp(self, element: etree._Element) -> Optional[str]:
        """Get timestamp from an element if available."""
        # Many objects don't have timestamps in the XML, so this is a placeholder
        # You might have this information from a database or other source
        timestamp_elem = find_element(element, './last-modified')
        return timestamp_elem.text if timestamp_elem is not None else None