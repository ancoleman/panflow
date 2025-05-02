"""
PANFlow for PAN-OS XML

A comprehensive set of utilities for working with PAN-OS XML configurations.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from lxml import etree

# Import core modules
from .core.config_loader import (
    load_config_from_file, load_config_from_string, save_config,
    xpath_search, extract_element_data, detect_device_type
)
from .core.xpath_resolver import (
    get_context_xpath, get_object_xpath, get_policy_xpath,
    get_all_versions, determine_version_from_config
)

from .core.policy_merger import PolicyMerger
from .core.object_merger import ObjectMerger

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
from .modules.reports import (
    generate_unused_objects_report, generate_duplicate_objects_report,
    generate_security_rule_coverage_report, generate_reference_check_report
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
            **kwargs
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