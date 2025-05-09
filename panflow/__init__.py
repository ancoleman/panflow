"""
PANFlow for PAN-OS XML

A comprehensive set of utilities for working with PAN-OS XML configurations.
"""

# Define object type aliases for CLI usage
OBJECT_TYPE_ALIASES = {
    "profile-group": "security_profile_group"
}

import os
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from lxml import etree

# Import core exceptions
from .core.exceptions import (
    PANFlowError, ConfigError, ValidationError, ParseError, 
    XPathError, ContextError, ObjectError, ObjectNotFoundError,
    ObjectExistsError, PolicyError, PolicyNotFoundError,
    PolicyExistsError, MergeError, ConflictError, VersionError,
    FileOperationError, BulkOperationError, SecurityError
)

# Import core modules
from .core.config_loader import (
    load_config_from_file, load_config_from_string, save_config,
    xpath_search, extract_element_data, detect_device_type
)
from .core.xpath_resolver import (
    get_context_xpath, get_object_xpath, get_policy_xpath,
    get_all_versions, determine_version_from_config
)

# Use consolidated XML package
from .core.xml.base import (
    create_element, delete_element, get_element_text, set_element_text,
    element_exists, clone_element
)
from .core.xml.builder import XmlBuilder
from .core.xml.cache import cached_xpath, clear_xpath_cache
from .core.xml.query import XmlQuery
from .core.xml.diff import XmlDiff

from .core.policy_merger import PolicyMerger
from .core.object_merger import ObjectMerger
from .core.deduplication import DeduplicationEngine
from .core.bulk_operations import ConfigQuery, ConfigUpdater
from .core.conflict_resolver import ConflictStrategy
from .core.object_finder import (
    find_objects_by_name, find_objects_by_value, find_all_locations,
    find_duplicate_names, find_duplicate_values, ObjectLocation
)

# Import functional modules
from .modules.objects import (
    get_objects, get_object, add_object, update_object, 
    delete_object, filter_objects
)
from .modules.groups import (
    add_member_to_group, remove_member_from_group, add_members_to_group,
    create_group, get_group_members, get_group_filter
)
from .modules.policies import (
    get_policies, get_policy, add_policy, update_policy,
    delete_policy, filter_policies
)

# Import consolidated reporting functionality
from .reporting import (
    generate_unused_objects_report, generate_duplicate_objects_report,
    generate_security_rule_coverage_report, generate_reference_check_report,
    generate_rule_hit_count_report, ReportingEngine
)

# Set up logging
logger = logging.getLogger("panflow")

class PANFlowConfig:
    """
    Simple class wrapper for working with PAN-OS XML configurations.
    This provides a more object-oriented interface if desired, while still
    using the functional core underneath.
    """
    
    def __init__(
        self, 
        config_file: Optional[str] = None,
        config_string: Optional[str] = None,
        device_type: Optional[str] = None,
        version: Optional[str] = None
    ):
        """
        Initialize with a configuration file or string.
        
        Args:
            config_file: Path to XML configuration file (optional)
            config_string: XML configuration as string (optional)
            device_type: Type of device ("firewall" or "panorama") (optional, auto-detected if not provided)
            version: PAN-OS version (optional, auto-detected if not provided)
        
        Raises:
            ValueError: If neither config_file nor config_string is provided
        """
        if config_file:
            # Load from file
            self.tree, detected_version = load_config_from_file(config_file)
            self.version = version or detected_version
            self.device_type = device_type or detect_device_type(self.tree)
        elif config_string:
            # Load from string
            self.tree, detected_version = load_config_from_string(config_string)
            self.version = version or detected_version
            self.device_type = device_type or detect_device_type(self.tree)
        else:
            raise ValueError("Either config_file or config_string must be provided")
        
        self.root = self.tree.getroot()
    
    def save(self, output_file: str) -> bool:
        """Save configuration to file"""
        return save_config(self.tree, output_file)
    
    def xpath_search(self, xpath: str) -> List[etree._Element]:
        """Search for elements using XPath"""
        return xpath_search(self.tree, xpath)
    
    # Object-related methods
    def get_objects(self, object_type: str, context_type: str, **kwargs) -> Dict[str, Dict[str, Any]]:
        """Get all objects of a specific type"""
        return get_objects(self.tree, object_type, self.device_type, context_type, self.version, **kwargs)
    
    def get_object(self, object_type: str, name: str, context_type: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Get a specific object by name"""
        return get_object(self.tree, object_type, name, self.device_type, context_type, self.version, **kwargs)
    
    def add_object(self, object_type: str, name: str, properties: Dict[str, Any], context_type: str, **kwargs) -> bool:
        """Add a new object"""
        return add_object(self.tree, object_type, name, properties, self.device_type, context_type, self.version, **kwargs)
    
    def update_object(self, object_type: str, name: str, properties: Dict[str, Any], context_type: str, **kwargs) -> bool:
        """Update an existing object"""
        return update_object(self.tree, object_type, name, properties, self.device_type, context_type, self.version, **kwargs)
    
    def delete_object(self, object_type: str, name: str, context_type: str, **kwargs) -> bool:
        """Delete an object"""
        return delete_object(self.tree, object_type, name, self.device_type, context_type, self.version, **kwargs)
    
    def filter_objects(self, object_type: str, filter_criteria: Dict[str, Any], context_type: str, **kwargs) -> Dict[str, Dict[str, Any]]:
        """Filter objects based on criteria"""
        return filter_objects(self.tree, object_type, filter_criteria, self.device_type, context_type, self.version, **kwargs)
    
    # Group-related methods
    def add_member_to_group(self, group_type: str, group_name: str, member_name: str, context_type: str, **kwargs) -> bool:
        """Add a member to a group"""
        return add_member_to_group(self.tree, group_type, group_name, member_name, self.device_type, context_type, self.version, **kwargs)
    
    def remove_member_from_group(self, group_type: str, group_name: str, member_name: str, context_type: str, **kwargs) -> bool:
        """Remove a member from a group"""
        return remove_member_from_group(self.tree, group_type, group_name, member_name, self.device_type, context_type, self.version, **kwargs)
    
    def add_members_to_group(self, group_type: str, group_name: str, member_names: List[str], context_type: str, **kwargs) -> Tuple[int, int]:
        """Add multiple members to a group"""
        return add_members_to_group(self.tree, group_type, group_name, member_names, self.device_type, context_type, self.version, **kwargs)
    
    def create_group(self, group_type: str, group_name: str, members: Optional[List[str]], dynamic_filter: Optional[str], context_type: str, **kwargs) -> bool:
        """Create a new group"""
        return create_group(self.tree, group_type, group_name, members, dynamic_filter, self.device_type, context_type, self.version, **kwargs)
    
    # Policy-related methods
    def get_policies(self, policy_type: str, context_type: str, **kwargs) -> Dict[str, Dict[str, Any]]:
        """Get all policies of a specific type"""
        return get_policies(self.tree, policy_type, self.device_type, context_type, self.version, **kwargs)
    
    def get_policy(self, policy_type: str, name: str, context_type: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Get a specific policy by name"""
        return get_policy(self.tree, policy_type, name, self.device_type, context_type, self.version, **kwargs)
    
    def add_policy(self, policy_type: str, name: str, properties: Dict[str, Any], context_type: str, **kwargs) -> bool:
        """Add a new policy"""
        return add_policy(self.tree, policy_type, name, properties, self.device_type, context_type, self.version, **kwargs)
    
    def update_policy(self, policy_type: str, name: str, properties: Dict[str, Any], context_type: str, **kwargs) -> bool:
        """Update an existing policy"""
        return update_policy(self.tree, policy_type, name, properties, self.device_type, context_type, self.version, **kwargs)
    
    def delete_policy(self, policy_type: str, name: str, context_type: str, **kwargs) -> bool:
        """Delete a policy"""
        return delete_policy(self.tree, policy_type, name, self.device_type, context_type, self.version, **kwargs)
    
    # Report-related methods
    def generate_unused_objects_report(self, context_type: str, output_file: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate report of unused objects"""
        return generate_unused_objects_report(self.tree, self.device_type, context_type, self.version, output_file, **kwargs)
    
    def generate_duplicate_objects_report(self, context_type: str, output_file: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate report of duplicate objects"""
        return generate_duplicate_objects_report(self.tree, self.device_type, context_type, self.version, output_file, **kwargs)
    
    def generate_security_rule_coverage_report(self, context_type: str, output_file: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate report of security rule coverage"""
        return generate_security_rule_coverage_report(self.tree, self.device_type, context_type, self.version, output_file, **kwargs)
    
    def generate_reference_check_report(self, object_name: str, object_type: str, context_type: str, output_file: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate report of references to an object"""
        return generate_reference_check_report(self.tree, object_name, object_type, self.device_type, context_type, self.version, output_file, **kwargs)

    def merge_policy(
        self, 
        target_config,
        policy_type,
        policy_name,
        source_context_type,
        target_context_type,
        skip_if_exists=True,
        copy_references=True,
        position="bottom",
        ref_policy_name=None,
        conflict_strategy=None,
        **kwargs
    ):
        """
        Merge a policy with another configuration.
        
        Args:
            target_config: Target PANFlowConfig object or path to target configuration file
            policy_type: Type of policy to merge
            policy_name: Name of the policy to merge
            source_context_type: Source context type (shared, device_group, vsys)
            target_context_type: Target context type (shared, device_group, vsys)
            skip_if_exists: Skip if policy already exists in target
            copy_references: Copy object references (address objects, etc.)
            position: Where to place the policy ("top", "bottom", "before", "after")
            ref_policy_name: Reference policy name for "before" and "after" positions
            conflict_strategy: Strategy for handling conflicts (overrides skip_if_exists)
            **kwargs: Additional parameters (source_device_group, target_device_group, etc.)
            
        Returns:
            bool: Success status
        """
        # Handle target_config as file path or PANFlowConfig object
        if isinstance(target_config, str):
            from .core.config_loader import load_config_from_file
            target_tree, target_version = load_config_from_file(target_config)
            target_device_type = detect_device_type(target_tree)
        else:
            target_tree = target_config.tree
            target_version = target_config.version
            target_device_type = target_config.device_type
        
        # Create merger
        merger = PolicyMerger(
            self.tree,
            target_tree,
            self.device_type,
            target_device_type,
            self.version,
            target_version
        )
        
        # Merge policy
        return merger.copy_policy(
            policy_type,
            policy_name,
            source_context_type,
            target_context_type,
            skip_if_exists,
            copy_references,
            position,
            ref_policy_name,
            conflict_strategy=conflict_strategy,
            **kwargs
        )
    
    def merge_object(
        self, 
        target_config,
        object_type,
        object_name,
        source_context_type,
        target_context_type,
        skip_if_exists=True,
        copy_references=True,
        conflict_strategy=None,
        **kwargs
    ):
        """
        Merge an object with another configuration.
        
        Args:
            target_config: Target PANFlowConfig object or path to target configuration file
            object_type: Type of object to merge (address, service, etc.)
            object_name: Name of the object to merge
            source_context_type: Source context type (shared, device_group, vsys)
            target_context_type: Target context type (shared, device_group, vsys)
            skip_if_exists: Skip if object already exists in target
            copy_references: Copy object references (e.g., address group members)
            conflict_strategy: Strategy for handling conflicts (overrides skip_if_exists)
            **kwargs: Additional parameters (source_device_group, target_device_group, etc.)
            
        Returns:
            bool: Success status
        """
        # Handle target_config as file path or PANFlowConfig object
        if isinstance(target_config, str):
            from .core.config_loader import load_config_from_file, detect_device_type
            target_tree, target_version = load_config_from_file(target_config)
            target_device_type = detect_device_type(target_tree)
        else:
            target_tree = target_config.tree
            target_version = target_config.version
            target_device_type = target_config.device_type
        
        # Create merger
        merger = ObjectMerger(
            self.tree,
            target_tree,
            self.device_type,
            target_device_type,
            self.version,
            target_version
        )
        
        # Merge object
        return merger.copy_object(
            object_type,
            object_name,
            source_context_type,
            target_context_type,
            skip_if_exists,
            copy_references,
            conflict_strategy=conflict_strategy,
            **kwargs
        )
        
    def bulk_merge_objects(
        self,
        target_config,
        object_type,
        source_context_type,
        target_context_type,
        criteria=None,
        skip_if_exists=True,
        copy_references=True,
        conflict_strategy=None,
        **kwargs
    ) -> Tuple[int, int]:
        """
        Bulk merge objects matching criteria from this configuration to target.
        
        Args:
            target_config: Target PANFlowConfig object or path to target configuration file
            object_type: Type of object to merge (address, service, etc.)
            source_context_type: Source context type (shared, device_group, vsys)
            target_context_type: Target context type (shared, device_group, vsys)
            criteria: Dictionary of criteria for selecting objects to merge
            skip_if_exists: Skip if object already exists in target
            copy_references: Copy object references (e.g., address group members)
            conflict_strategy: Strategy for handling conflicts (overrides skip_if_exists)
            **kwargs: Additional parameters (source_device_group, target_device_group, etc.)
            
        Returns:
            Tuple[int, int]: (number of objects merged, total number of objects attempted)
        """
        # Handle target_config as file path or PANFlowConfig object
        if isinstance(target_config, str):
            from .core.config_loader import load_config_from_file, detect_device_type
            target_tree, target_version = load_config_from_file(target_config)
            target_device_type = detect_device_type(target_tree)
        else:
            target_tree = target_config.tree
            target_version = target_config.version
            target_device_type = target_config.device_type
        
        # Create updater for target configuration
        updater = ConfigUpdater(
            target_tree,
            target_device_type,
            target_context_type,
            target_version,
            **{k: v for k, v in kwargs.items() if k.startswith('target_')}
        )
        
        # Extract source parameters
        source_params = {k: v for k, v in kwargs.items() if k.startswith('source_')}
        
        # Perform bulk merge
        return updater.bulk_merge_objects(
            self.tree,
            object_type,
            criteria,
            source_context_type,
            target_context_type,
            self.device_type,
            self.version,
            skip_if_exists,
            copy_references,
            conflict_strategy,
            **{**source_params, **{k: v for k, v in kwargs.items() if k.startswith('target_')}}
        )
    
    def merge_objects_by_type(
        self,
        target_config,
        object_types,
        source_context_type,
        target_context_type,
        criteria=None,
        skip_if_exists=True,
        copy_references=True,
        conflict_strategy=None,
        **kwargs
    ) -> Dict[str, Tuple[int, int]]:
        """
        Merge multiple object types from this configuration to target.
        
        Args:
            target_config: Target PANFlowConfig object or path to target configuration file
            object_types: List of object types to merge (address, service, etc.)
            source_context_type: Source context type (shared, device_group, vsys)
            target_context_type: Target context type (shared, device_group, vsys)
            criteria: Dictionary of criteria for selecting objects to merge
            skip_if_exists: Skip if object already exists in target
            copy_references: Copy object references (e.g., address group members)
            conflict_strategy: Strategy for handling conflicts (overrides skip_if_exists)
            **kwargs: Additional parameters (source_device_group, target_device_group, etc.)
            
        Returns:
            Dict[str, Tuple[int, int]]: Dictionary mapping object types to (copied, total) counts
        """
        results = {}
        
        for object_type in object_types:
            merged, total = self.bulk_merge_objects(
                target_config,
                object_type,
                source_context_type,
                target_context_type,
                criteria,
                skip_if_exists,
                copy_references,
                conflict_strategy,
                **kwargs
            )
            results[object_type] = (merged, total)
        
        return results
    
    def deduplicate_objects(
        self,
        object_type,
        context_type,
        criteria=None,
        primary_name_strategy="shortest",
        dry_run=False,
        **kwargs
    ) -> Tuple[Dict[str, Dict[str, Any]], int]:
        """
        Find and merge duplicate objects in the configuration.
        
        Args:
            object_type: Type of object to deduplicate (address, service, tag)
            context_type: Context type (shared, device_group, vsys)
            criteria: Optional criteria to filter objects before deduplication
            primary_name_strategy: Strategy for selecting primary object name
                                  ("first", "shortest", "longest", "alphabetical")
            dry_run: If True, only identify duplicates but don't merge them
            **kwargs: Additional context parameters (device_group, vsys, etc.)
            
        Returns:
            Tuple: (
                Dictionary containing details of the changes made,
                Number of duplicate objects merged
            )
        """
        # Create updater for this configuration
        updater = ConfigUpdater(
            self.tree,
            self.device_type,
            context_type,
            self.version,
            **kwargs
        )
        
        # Perform deduplication
        return updater.bulk_deduplicate_objects(
            object_type,
            criteria,
            primary_name_strategy,
            dry_run,
            **kwargs
        )
    
    def deduplicate_all_object_types(
        self,
        context_type,
        object_types=None,
        criteria=None,
        primary_name_strategy="shortest",
        dry_run=False,
        **kwargs
    ) -> Dict[str, Tuple[Dict[str, Dict[str, Any]], int]]:
        """
        Find and merge duplicate objects of multiple types in the configuration.
        
        Args:
            context_type: Context type (shared, device_group, vsys)
            object_types: List of object types to deduplicate (address, service, tag)
                         If None, defaults to ["address", "service", "tag"]
            criteria: Optional criteria to filter objects before deduplication
            primary_name_strategy: Strategy for selecting primary object name
                                  ("first", "shortest", "longest", "alphabetical")
            dry_run: If True, only identify duplicates but don't merge them
            **kwargs: Additional context parameters (device_group, vsys, etc.)
            
        Returns:
            Dict: Dictionary mapping object types to (changes, merged_count) tuples
        """
        if object_types is None:
            object_types = ["address", "service", "tag"]
        
        results = {}
        
        for object_type in object_types:
            changes, merged_count = self.deduplicate_objects(
                object_type,
                context_type,
                criteria,
                primary_name_strategy,
                dry_run,
                **kwargs
            )
            results[object_type] = (changes, merged_count)
        
        return results
    
    # Global object finder methods
    def find_objects_by_name(
        self,
        object_type: str,
        object_name: str,
        use_regex: bool = False
    ) -> List[ObjectLocation]:
        """
        Find all objects with a specific name throughout the configuration.
        
        This method searches across all contexts (shared, device groups, vsys, templates)
        to find objects with the given name, regardless of where they are located.
        
        Args:
            object_type: Type of object to find (address, service, etc.)
            object_name: Name of the object to find (exact match or regex pattern)
            use_regex: If True, treat object_name as a regex pattern for partial matching
            
        Returns:
            List of ObjectLocation objects representing all matching objects
        """
        return find_objects_by_name(
            self.tree,
            object_type,
            object_name,
            self.device_type,
            self.version,
            use_regex
        )
    
    def find_objects_by_value(
        self,
        object_type: str,
        value_criteria: Dict[str, Any]
    ) -> List[ObjectLocation]:
        """
        Find all objects matching specific value criteria throughout the configuration.
        
        This method searches across all contexts (shared, device groups, vsys, templates)
        to find objects with matching values, regardless of where they are located.
        
        Args:
            object_type: Type of object to find (address, service, etc.)
            value_criteria: Dictionary of criteria to match against object values
                Example for address: {"ip-netmask": "10.0.0.0/24"}
                Example for service: {"protocol": "tcp", "port": "8080"}
                Example for tag: {"color": "red"}
            
        Returns:
            List of ObjectLocation objects representing all matching objects
        """
        return find_objects_by_value(
            self.tree,
            object_type,
            value_criteria,
            self.device_type,
            self.version
        )
    
    def find_all_object_locations(self) -> Dict[str, Dict[str, List[ObjectLocation]]]:
        """
        Find the locations of all objects in the configuration.
        
        This method creates a comprehensive map of all objects in the configuration,
        organized by object type and name, with each object potentially having
        multiple locations across different contexts.
        
        Returns:
            Dict mapping object types to dicts mapping object names to lists of locations
        """
        return find_all_locations(
            self.tree,
            self.device_type,
            self.version
        )
    
    def find_duplicate_object_names(self) -> Dict[str, Dict[str, List[ObjectLocation]]]:
        """
        Find objects with the same name across different contexts.
        
        This is useful for identifying objects that have the same name but
        potentially different definitions in different device groups, templates,
        or vsys.
        
        Returns:
            Dict mapping object types to dicts mapping duplicate names to lists of locations
        """
        return find_duplicate_names(
            self.tree,
            self.device_type,
            self.version
        )
    
    def find_duplicate_object_values(
        self,
        object_type: str
    ) -> Dict[str, List[ObjectLocation]]:
        """
        Find objects with the same value but different names.
        
        This is useful for identifying redundant objects that define the same values
        but have different names, which could be consolidated to simplify the configuration.
        
        This method works best with address, service, and tag objects which have
        clear value definitions.
        
        Args:
            object_type: Type of object to find duplicates for
            
        Returns:
            Dict mapping values to lists of locations
        """
        return find_duplicate_values(
            self.tree,
            object_type,
            self.device_type,
            self.version
        )

# Function to configure logging
def configure_logging(
    level: str = "info",
    log_file: Optional[str] = None,
    quiet: bool = False,
    verbose: bool = False
) -> None:
    """Configure the logging system"""
    # Import logging configuration from panos_logging module
    from .core.logging_utils import configure_logging as configure_logging_impl
    configure_logging_impl(level, log_file, quiet, verbose)