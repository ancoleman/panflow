"""
Object merger for PANFlow.

This module provides functionality for merging objects between different configurations,
device groups, or virtual systems.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Set
from lxml import etree
import copy
import re

from .xpath_resolver import get_object_xpath, get_context_xpath
from .config_loader import xpath_search
from .xml_utils import clone_element, merge_elements, find_elements, find_element, element_exists
from .object_validator import ObjectValidator
from .conflict_resolver import ConflictResolver, ConflictStrategy

# Initialize logger
logger = logging.getLogger("panflow")

class ObjectMerger:
    """
    Class for merging objects between PAN-OS configurations.
    
    Provides methods for copying objects from one configuration to another,
    with options to handle conflicts and dependencies.
    """
    
    # Dictionary defining version-specific attributes for each object type
    # Format: object_type -> {attribute -> {version: required}}
    VERSION_SPECIFIC_ATTRIBUTES = {
        "address": {
            "ip-netmask": {"10.1": True, "10.2": True, "11.2": True},
            "fqdn": {"10.1": True, "10.2": True, "11.2": True},
            "ip-range": {"10.1": True, "10.2": True, "11.2": True},
            "ip-wildcard": {"10.1": True, "10.2": True, "11.2": True},
            "description": {"10.1": False, "10.2": False, "11.2": False},
            "tag": {"10.1": False, "10.2": False, "11.2": False},
            "color": {"10.2": False, "11.2": False},  # Added in 10.2+
        },
        "address-group": {
            "static": {"10.1": False, "10.2": False, "11.2": False},
            "dynamic": {"10.1": False, "10.2": False, "11.2": False},
            "description": {"10.1": False, "10.2": False, "11.2": False},
            "tag": {"10.1": False, "10.2": False, "11.2": False},
            "color": {"10.2": False, "11.2": False},  # Added in 10.2+
        },
        "service": {
            "protocol": {"10.1": True, "10.2": True, "11.2": True},
            "description": {"10.1": False, "10.2": False, "11.2": False},
            "tag": {"10.1": False, "10.2": False, "11.2": False},
            "color": {"10.2": False, "11.2": False},  # Added in 10.2+
        },
        "tag": {
            "color": {"10.1": False, "10.2": False, "11.2": False},
            "comments": {"10.1": False, "10.2": False, "11.2": False},
        },
        "external-list": {
            "type": {"10.1": True, "10.2": True, "11.2": True},
            "recurring": {"10.1": False, "10.2": False, "11.2": False},
            "description": {"10.1": False, "10.2": False, "11.2": False},
            "certificate-profile": {"10.1": False, "10.2": False, "11.2": False},
            "tag": {"10.1": False, "10.2": False, "11.2": False},
        },
        "region": {  # Added in 10.2+
            "address": {"10.2": False, "11.2": False},
            "description": {"10.2": False, "11.2": False},
            "tag": {"10.2": False, "11.2": False},
        },
        "dynamic-user-group": {  # Added in 10.2+
            "filter": {"10.2": True, "11.2": True},
            "description": {"10.2": False, "11.2": False},
            "tag": {"10.2": False, "11.2": False},
        },
        # Security Profile Types
        "security_profile_group": {
            "description": {"10.1": False, "10.2": False, "11.2": False},
            "virus": {"10.1": False, "10.2": False, "11.2": False},
            "spyware": {"10.1": False, "10.2": False, "11.2": False},
            "vulnerability": {"10.1": False, "10.2": False, "11.2": False},
            "url-filtering": {"10.1": False, "10.2": False, "11.2": False},
            "file-blocking": {"10.1": False, "10.2": False, "11.2": False},
            "wildfire-analysis": {"10.1": False, "10.2": False, "11.2": False},
            "data-filtering": {"10.1": False, "10.2": False, "11.2": False},
            "dns-security": {"10.2": False, "11.2": False},  # Added in 10.2+
        },
        "virus": {  # Antivirus Profiles
            "description": {"10.1": False, "10.2": False, "11.2": False},
            "decoder": {"10.1": True, "10.2": True, "11.2": True},
            "mlav-engine-url-db-version": {"11.2": False},  # Added in 11.0+
            "mlav-engine-minimum-version": {"11.2": False},  # Added in 11.0+
            "packet-capture": {"10.1": False, "10.2": False, "11.2": False},
            "application-exception": {"10.1": False, "10.2": False, "11.2": False},
            "machine-learning-model": {"11.2": False},  # Added in 11.0+
            "machine-learning-threshold-levels": {"11.2": False},  # Added in 11.0+
        },
        "spyware": {  # Anti-Spyware Profiles
            "description": {"10.1": False, "10.2": False, "11.2": False},
            "rules": {"10.1": True, "10.2": True, "11.2": True},
            "botnet-domains": {"10.1": False, "10.2": False, "11.2": False},
            "packet-capture": {"10.1": False, "10.2": False, "11.2": False},
            "threat-exception": {"10.1": False, "10.2": False, "11.2": False},
            "cloud-inline-analysis": {"10.2": False, "11.2": False},  # Added in 10.2+
        },
        "vulnerability": {  # Vulnerability Protection Profiles
            "description": {"10.1": False, "10.2": False, "11.2": False},
            "rules": {"10.1": True, "10.2": True, "11.2": True},
            "packet-capture": {"10.1": False, "10.2": False, "11.2": False},
            "threat-exception": {"10.1": False, "10.2": False, "11.2": False},
        },
        "url-filtering": {  # URL Filtering Profiles
            "description": {"10.1": False, "10.2": False, "11.2": False},
            "block": {"10.1": False, "10.2": False, "11.2": False},
            "alert": {"10.1": False, "10.2": False, "11.2": False},
            "allow": {"10.1": False, "10.2": False, "11.2": False},
            "continue": {"10.1": False, "10.2": False, "11.2": False},
            "override": {"10.1": False, "10.2": False, "11.2": False},
            "credential-enforcement": {"10.1": False, "10.2": False, "11.2": False},
            "log-container-page-only": {"10.1": False, "10.2": False, "11.2": False},
            "safe-search-enforcement": {"10.1": False, "10.2": False, "11.2": False},
            "block-list": {"10.1": False, "10.2": False, "11.2": False},
            "allow-list": {"10.1": False, "10.2": False, "11.2": False},
            "cache-size": {"10.1": False, "10.2": False, "11.2": False},
            "extended-log": {"10.2": False, "11.2": False},  # Added in 10.2+
            "http-header-insertion": {"10.2": False, "11.2": False},  # Added in 10.2+
            "machine-learning-model": {"11.2": False},  # Added in 11.0+
        },
        "file-blocking": {  # File Blocking Profiles
            "description": {"10.1": False, "10.2": False, "11.2": False},
            "rules": {"10.1": True, "10.2": True, "11.2": True},
        },
        "wildfire-analysis": {  # WildFire Analysis Profiles
            "description": {"10.1": False, "10.2": False, "11.2": False},
            "rules": {"10.1": True, "10.2": True, "11.2": True},
            "application-exception": {"10.1": False, "10.2": False, "11.2": False},
            "analysis-setting": {"10.1": False, "10.2": False, "11.2": False},
            "report-benign-file": {"10.1": False, "10.2": False, "11.2": False},
            "report-grayware-file": {"10.1": False, "10.2": False, "11.2": False},
            "report-malicious-file": {"10.1": False, "10.2": False, "11.2": False},
            "report-phishing-file": {"10.2": False, "11.2": False},  # Added in 10.2+
        },
        "dns-security": {  # DNS Security Profiles
            "description": {"10.1": False, "10.2": False, "11.2": False},
            "botnet-domains": {"10.1": False, "10.2": False, "11.2": False},
            "packet-capture": {"10.1": False, "10.2": False, "11.2": False},
            "threat-exception": {"10.1": False, "10.2": False, "11.2": False},
            "cloud-inline-analysis": {"10.2": False, "11.2": False},  # Added in 10.2+
        },
        "decryption": {  # Decryption Profiles
            "description": {"10.1": False, "10.2": False, "11.2": False},
            "ssl-protocol-settings": {"10.1": True, "10.2": True, "11.2": True},
            "ssl-certificate-verification": {"10.1": False, "10.2": False, "11.2": False},
            "ssl-decryption-exclusion": {"10.2": False, "11.2": False},  # Added in 10.2+
        },
        "schedule": {  # Schedule Objects
            "description": {"10.1": False, "10.2": False, "11.2": False},
            "recurring": {"10.1": False, "10.2": False, "11.2": False},
            "non-recurring": {"10.1": False, "10.2": False, "11.2": False},
        },
        "custom-url-category": {  # Custom URL Categories
            "description": {"10.1": False, "10.2": False, "11.2": False},
            "type": {"10.1": True, "10.2": True, "11.2": True},
            "members": {"10.1": False, "10.2": False, "11.2": False},
            "list": {"10.1": False, "10.2": False, "11.2": False},
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
        
        # Initialize the object validator
        self.validator = ObjectValidator(self.source_device_type, self.source_version)
        
        # Initialize the conflict resolver
        self.conflict_resolver = ConflictResolver(ConflictStrategy.SKIP)
    
    def copy_object(
        self,
        object_type: str,
        object_name: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        copy_references: bool = True,
        validate: bool = False,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> bool:
        """
        Copy a single object from source to target.
        
        Args:
            object_type: Type of object (address, service, etc.)
            object_name: Name of the object to copy
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            skip_if_exists: Skip if object already exists in target (deprecated, use conflict_strategy instead)
            copy_references: Copy object references (e.g., address group members)
            validate: Whether to validate the object before copying
            conflict_strategy: Strategy to use when resolving conflicts with existing objects
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
            
            # Validate the object if requested
            if validate:
                logger.info(f"Validating {object_type} object '{object_name}' before copying")
                is_valid, validation_errors = self.validate_object(source_object, object_type)
                if not is_valid:
                    logger.warning(f"Validation failed for {object_type} object '{object_name}'")
                    for error in validation_errors:
                        logger.warning(f"  - {error}")
                    self.skipped_objects.append((object_type, object_name, f"Validation failed: {validation_errors}"))
                    return False
                logger.debug(f"Validation successful for {object_type} object '{object_name}'")
            
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
                # Handle conflict using conflict resolution strategy
                if conflict_strategy is None:
                    # Use skip_if_exists for backward compatibility
                    if skip_if_exists:
                        conflict_strategy = ConflictStrategy.SKIP
                    else:
                        conflict_strategy = ConflictStrategy.OVERWRITE
                
                # Resolve the conflict
                success, resolved_object, message = self.conflict_resolver.resolve_conflict(
                    source_object, target_elements[0], object_type, object_name, conflict_strategy, **kwargs
                )
                
                if not success:
                    logger.warning(f"Object '{object_name}' conflict resolution: {message}")
                    self.skipped_objects.append((object_type, object_name, message))
                    return False
                
                # Remove the existing object
                parent = target_elements[0].getparent()
                if parent is not None:
                    logger.info(f"Removing existing object '{object_name}' from target")
                    parent.remove(target_elements[0])
                    
                    # If the conflict strategy provided a new object, we'll use that instead
                    # of the original source object later
                    if resolved_object is not None:
                        source_object = resolved_object
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
            
            # Handle version-specific attribute differences if source and target versions differ
            if self.source_version != self.target_version:
                logger.debug(f"Handling version-specific attributes for {object_type} '{object_name}'")
                new_object = self._handle_version_specific_attributes(new_object, object_type)
            
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
        
        # Copy related tags if present
        try:
            logger.debug(f"Checking for tags in object '{object_name}'")
            self._copy_related_tags(
                source_object,
                source_context_type,
                target_context_type,
                skip_if_exists,
                **kwargs
            )
        except Exception as e:
            logger.warning(f"Error copying tags for '{object_name}': {e}", exc_info=True)
            # Continue since the main object was copied successfully
        
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
                
        # Special handling for dynamic address groups (copy matching tags)
        if copy_references and object_type == "address_group":
            if find_element(source_object, './dynamic/filter'):
                try:
                    logger.debug(f"Processing dynamic address group '{object_name}'")
                    self._handle_dynamic_address_group(
                        source_object,
                        source_context_type,
                        target_context_type,
                        skip_if_exists,
                        **kwargs
                    )
                except Exception as e:
                    logger.warning(f"Error handling dynamic address group '{object_name}': {e}", exc_info=True)
                    
        # Special handling for service objects
        if copy_references and object_type == "service":
            try:
                logger.debug(f"Processing service object '{object_name}' for complex configurations")
                self._handle_complex_service_object(
                    source_object,
                    source_context_type,
                    target_context_type,
                    skip_if_exists,
                    conflict_strategy,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"Error handling complex service object '{object_name}': {e}", exc_info=True)
                
        # Special handling for service groups
        if copy_references and object_type == "service_group":
            try:
                logger.debug(f"Processing service group '{object_name}'")
                self._handle_service_group(
                    source_object,
                    source_context_type,
                    target_context_type,
                    skip_if_exists,
                    conflict_strategy,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"Error handling service group '{object_name}': {e}", exc_info=True)
                
        # Special handling for security profile groups
        if copy_references and object_type in ["security_profile_group", "security-profile-group", "profile-group"]:
            try:
                logger.debug(f"Processing security profile group '{object_name}'")
                self._handle_security_profile_group(
                    source_object,
                    source_context_type,
                    target_context_type,
                    skip_if_exists,
                    conflict_strategy,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"Error handling security profile group '{object_name}': {e}", exc_info=True)
                
        # Special handling for security profiles
        if copy_references and object_type in ["virus", "spyware", "vulnerability", 
                                             "url-filtering", "file-blocking", 
                                             "wildfire-analysis", "dns-security"]:
            try:
                logger.debug(f"Processing security profile '{object_name}'")
                self._handle_security_profile(
                    source_object,
                    object_type,
                    source_context_type,
                    target_context_type,
                    skip_if_exists,
                    conflict_strategy,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"Error handling security profile '{object_name}': {e}", exc_info=True)
                
        # Special handling for security rules (extract and copy referenced security profiles)
        if copy_references and object_type in ["security_rule", "security-rule", "security_policy"]:
            try:
                logger.debug(f"Processing security rule '{object_name}' for security profile references")
                self._handle_security_profiles_in_rules(
                    source_object,
                    object_name,
                    source_context_type,
                    target_context_type,
                    skip_if_exists,
                    conflict_strategy,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"Error handling security profiles in rule '{object_name}': {e}", exc_info=True)
                
        # Special handling for schedule objects
        if copy_references and object_type in ["schedule"]:
            try:
                logger.debug(f"Processing schedule object '{object_name}'")
                self._handle_schedule(
                    source_object,
                    object_name,
                    source_context_type,
                    target_context_type,
                    skip_if_exists,
                    conflict_strategy,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"Error handling schedule object '{object_name}': {e}", exc_info=True)
                
        # Special handling for custom URL categories
        if copy_references and object_type in ["custom-url-category", "url-category"]:
            try:
                logger.debug(f"Processing custom URL category '{object_name}'")
                self._handle_custom_url_category(
                    source_object,
                    object_name,
                    source_context_type,
                    target_context_type,
                    skip_if_exists,
                    conflict_strategy,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"Error handling custom URL category '{object_name}': {e}", exc_info=True)
            
        return True
  
    
    def copy_object_with_dependencies(
        self,
        object_type: str,
        object_name: str,
        source_context_type: str,
        target_context_type: str,
        include_referenced_by: bool = False,
        include_policies: bool = False,
        skip_if_exists: bool = True,
        validate: bool = False,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> Tuple[bool, Dict[str, List[Tuple[str, str]]]]:
        """
        Copy an object and all of its dependencies.
        
        This method analyzes the dependencies of an object and copies both the object
        and all objects it depends on to the target configuration, ensuring that the
        object will work correctly in the target context.
        
        Args:
            object_type: Type of object (address, service, etc.)
            object_name: Name of the object to copy
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            include_referenced_by: Also copy objects that reference this object
            include_policies: Copy policy rules that reference this object
            skip_if_exists: Skip if object already exists in target (deprecated, use conflict_strategy instead)
            validate: Whether to validate objects before copying
            conflict_strategy: Strategy to use when resolving conflicts with existing objects
            **kwargs: Additional parameters (source_device_group, target_device_group, etc.)
            
        Returns:
            Tuple: (Success status, Dictionary of copied dependencies)
        """
        logger.info(f"Copying {object_type} '{object_name}' with dependencies")
        
        # Analyze dependencies
        source_kwargs = {}
        for k, v in kwargs.items():
            if k.startswith('target_'):
                source_key = k.replace('target_', 'source_')
                if source_key in kwargs:
                    source_kwargs[source_key] = kwargs[source_key]
            elif k.startswith('source_'):
                source_kwargs[k] = v
                
        dependencies = self.analyze_dependencies(
            object_type,
            object_name,
            source_context_type,
            include_policies,
            **source_kwargs
        )
        
        # Create a tracking set for objects we've already copied or attempted to copy
        processed_objects = set()
        
        # Copy all objects that this object depends on first
        for dep_type, dep_name in dependencies["depends_on"]:
            if (dep_type, dep_name) not in processed_objects:
                logger.info(f"Copying dependency: {dep_type} '{dep_name}'")
                success = self.copy_object(
                    dep_type, 
                    dep_name, 
                    source_context_type, 
                    target_context_type, 
                    skip_if_exists, 
                    False,  # Don't recursively copy references again
                    validate,
                    conflict_strategy,
                    **kwargs
                )
                processed_objects.add((dep_type, dep_name))
                if not success:
                    logger.warning(f"Failed to copy dependency: {dep_type} '{dep_name}'")
        
        # Copy the object itself
        main_result = self.copy_object(
            object_type,
            object_name,
            source_context_type,
            target_context_type,
            skip_if_exists,
            False,  # Don't copy references again since we've already done it
            validate,
            conflict_strategy,
            **kwargs
        )
        
        # Copy objects that reference this object if requested
        if include_referenced_by:
            for ref_type, ref_name in dependencies["referenced_by"]:
                # Skip policy references if policies are not included
                if not include_policies and any(ref_type.endswith(policy_type) for policy_type in ["rule", "policy"]):
                    continue
                    
                if (ref_type, ref_name) not in processed_objects:
                    logger.info(f"Copying referencing object: {ref_type} '{ref_name}'")
                    success = self.copy_object(
                        ref_type,
                        ref_name,
                        source_context_type,
                        target_context_type,
                        skip_if_exists,
                        False,  # Don't recursively copy references
                        validate,
                        conflict_strategy,
                        **kwargs
                    )
                    processed_objects.add((ref_type, ref_name))
                    if not success:
                        logger.warning(f"Failed to copy referencing object: {ref_type} '{ref_name}'")
        
        return main_result, dependencies

    def copy_objects(
        self,
        object_type: str,
        source_context_type: str,
        target_context_type: str,
        object_names: Optional[List[str]] = None,
        filter_criteria: Optional[Dict[str, Any]] = None,
        skip_if_exists: bool = True,
        copy_references: bool = True,
        copy_with_dependencies: bool = False,
        include_referenced_by: bool = False,
        include_policies: bool = False,
        validate: bool = False,
        conflict_strategy: Optional[ConflictStrategy] = None,
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
            skip_if_exists: Skip if object already exists in target (deprecated, use conflict_strategy instead)
            copy_references: Copy object references (e.g., address group members)
            copy_with_dependencies: Analyze and copy all dependencies recursively
            include_referenced_by: Also copy objects that reference the ones being copied
            include_policies: Include policy references in dependency analysis
            validate: Whether to validate objects before copying
            conflict_strategy: Strategy to use when resolving conflicts with existing objects
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
            
            # Choose copy method based on whether we need dependency analysis
            if copy_with_dependencies:
                logger.info(f"Using comprehensive dependency analysis for {object_type} '{name}'")
                result, dependencies = self.copy_object_with_dependencies(
                    object_type,
                    name,
                    source_context_type,
                    target_context_type,
                    include_referenced_by,
                    include_policies,
                    skip_if_exists,
                    **kwargs
                )
                
                if dependencies:
                    dep_count = len(dependencies["depends_on"])
                    ref_count = len(dependencies["referenced_by"])
                    logger.info(f"Dependency analysis for '{name}': {dep_count} dependencies, {ref_count} references")
            else:
                result = self.copy_object(
                    object_type,
                    name,
                    source_context_type,
                    target_context_type,
                    skip_if_exists,
                    copy_references,
                    validate,
                    conflict_strategy,
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
        copy_with_dependencies: bool = False,
        include_referenced_by: bool = False,
        include_policies: bool = False,
        validate: bool = False,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> Dict[str, Tuple[int, int]]:
        """
        Merge all objects of specified types from source to target.
        
        Args:
            object_types: List of object types to merge
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            skip_if_exists: Skip if object already exists in target (deprecated, use conflict_strategy instead)
            copy_references: Copy object references (e.g., address group members)
            copy_with_dependencies: Analyze and copy all dependencies recursively
            include_referenced_by: Also copy objects that reference the ones being copied
            include_policies: Include policy references in dependency analysis
            validate: Whether to validate objects before copying
            conflict_strategy: Strategy to use when resolving conflicts with existing objects
            **kwargs: Additional parameters (source_device_group, target_device_group, etc.)
            
        Returns:
            Dict: Dictionary mapping object types to (copied, total) counts
        """
        logger.info(f"Merging multiple object types from {source_context_type} to {target_context_type}")
        logger.debug(f"Object types to merge: {object_types}")
        
        results = {}
        
        # Process dependency-analyzed objects first if using dependencies
        # This is because objects with dependencies might reference other object types
        # in the list, and we want to ensure correct ordering
        if copy_with_dependencies:
            logger.info("Using comprehensive dependency analysis for object merging")
        
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
                copy_with_dependencies,
                include_referenced_by,
                include_policies,
                validate,
                conflict_strategy,
                **kwargs
            )
            
            results[object_type] = (copied, total)
        
        # Log summary
        total_copied = sum(copied for copied, _ in results.values())
        total_objects = sum(total for _, total in results.values())
        logger.info(f"Merged a total of {total_copied} objects out of {total_objects} across all types")
        
        return results
        
    def _handle_complex_service_object(
        self,
        service_element: etree._Element,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle complex service objects with protocol-specific configurations.
        
        Args:
            service_element: The XML element of the service object
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            skip_if_exists: Skip if tag already exists in target
            conflict_strategy: Strategy to use when resolving conflicts
            **kwargs: Additional context parameters
        """
        service_name = service_element.get("name", "unknown")
        logger.debug(f"Processing complex service object '{service_name}'")
        
        # Get the protocol type
        protocol_elem = find_element(service_element, './protocol')
        if not protocol_elem or not protocol_elem.text:
            logger.debug(f"Service '{service_name}' has no protocol defined, skipping complex handling")
            return
            
        protocol = protocol_elem.text
        
        # Handle protocol-specific dependencies or related objects
        if protocol == "tcp" or protocol == "udp":
            # TCP/UDP services might have application overrides
            self._handle_service_application_overrides(
                service_element, service_name, protocol, source_context_type, target_context_type, 
                skip_if_exists, conflict_strategy, **kwargs
            )
        elif protocol == "sctp":
            # SCTP services might have specific configurations
            self._handle_sctp_service(
                service_element, service_name, source_context_type, target_context_type, 
                skip_if_exists, conflict_strategy, **kwargs
            )
        elif protocol == "icmp" or protocol == "icmp6":
            # ICMP services might need special handling for type/code
            self._handle_icmp_service(
                service_element, service_name, protocol, source_context_type, target_context_type, 
                skip_if_exists, conflict_strategy, **kwargs
            )
        
    def _handle_service_application_overrides(
        self,
        service_element: etree._Element,
        service_name: str,
        protocol: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True, 
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle TCP/UDP service application overrides.
        
        Some services may have application-override rules associated with them.
        This method identifies and copies those dependencies.
        
        Args:
            service_element: The service XML element
            service_name: Name of the service
            protocol: Service protocol (tcp or udp)
            source_context_type: Type of source context
            target_context_type: Type of target context
            skip_if_exists: Skip if exists in target
            conflict_strategy: Strategy for conflict resolution
            **kwargs: Additional context parameters
        """
        logger.debug(f"Checking for application overrides for {protocol} service '{service_name}'")
        
        # First, check if this is already a complex service with application specifics
        override_elem = find_element(service_element, './override')
        if override_elem is not None:
            logger.debug(f"Service '{service_name}' has application overrides, ensuring applications exist")
            
            # Find all application references
            app_refs = find_elements(override_elem, './/application/member')
            
            if not app_refs:
                logger.debug(f"No application references found in override for service '{service_name}'")
                return
                
            # Copy each referenced application
            for app_ref in app_refs:
                if app_ref.text:
                    app_name = app_ref.text
                    logger.debug(f"Found application reference: {app_name}")
                    
                    # Copy the application (if it exists and is a custom application)
                    try:
                        self.copy_object(
                            "application",
                            app_name,
                            source_context_type,
                            target_context_type,
                            skip_if_exists,
                            True,  # copy references
                            False,  # don't validate
                            conflict_strategy,
                            **kwargs
                        )
                    except Exception as e:
                        logger.warning(f"Error copying application '{app_name}': {e}")
                        # Continue with other applications
                        
    def _handle_sctp_service(
        self,
        service_element: etree._Element,
        service_name: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle SCTP service specific configurations.
        
        SCTP services may have specific attributes or dependencies.
        
        Args:
            service_element: The service XML element
            service_name: Name of the service
            source_context_type: Type of source context
            target_context_type: Type of target context
            skip_if_exists: Skip if exists in target
            conflict_strategy: Strategy for conflict resolution
            **kwargs: Additional context parameters
        """
        logger.debug(f"Processing SCTP service '{service_name}'")
        
        # SCTP services are similar to TCP/UDP but might have specific features
        # that need handling in the future. For now, we just log it.
        
    def _handle_icmp_service(
        self,
        service_element: etree._Element,
        service_name: str,
        protocol: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle ICMP/ICMP6 service specific configurations.
        
        ICMP services might need special handling for their type/code values.
        
        Args:
            service_element: The service XML element
            service_name: Name of the service
            protocol: Service protocol (icmp or icmp6)
            source_context_type: Type of source context
            target_context_type: Type of target context
            skip_if_exists: Skip if exists in target
            conflict_strategy: Strategy for conflict resolution
            **kwargs: Additional context parameters
        """
        logger.debug(f"Processing {protocol} service '{service_name}'")
        
        # For future versions: If ICMP types/codes need to be handled specially,
        # for example if they need to be adjusted for different PAN-OS versions,
        # that logic would go here.
        
    def _handle_security_profile_group(
        self,
        profile_group_element: etree._Element,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle security profile group references.
        
        Security profile groups contain references to various security profiles
        like AV, anti-spyware, URL filtering, etc. This method ensures that all
        referenced profiles are copied to the target context.
        
        Args:
            profile_group_element: The security profile group XML element
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            skip_if_exists: Skip if profile already exists in target
            conflict_strategy: Strategy for conflict resolution
            **kwargs: Additional context parameters
        """
        group_name = profile_group_element.get("name", "unknown")
        logger.debug(f"Processing security profile group '{group_name}'")
        
        # Define the profile types to check for
        profile_types = [
            ("virus", "virus"),
            ("spyware", "spyware"),
            ("vulnerability", "vulnerability"),
            ("url-filtering", "url-filtering"),
            ("file-blocking", "file-blocking"),
            ("wildfire-analysis", "wildfire-analysis"),
            ("data-filtering", "data-filtering"),
            ("dns-security", "dns-security")
        ]
        
        # Process each profile type
        for profile_elem_name, profile_type in profile_types:
            profile_ref = find_element(profile_group_element, f'./{profile_elem_name}')
            if profile_ref is not None and profile_ref.text:
                profile_name = profile_ref.text
                logger.debug(f"Found {profile_type} profile reference: {profile_name}")
                
                # Copy the referenced profile
                try:
                    self.copy_object(
                        profile_type,
                        profile_name,
                        source_context_type,
                        target_context_type,
                        skip_if_exists,
                        True,  # copy references
                        False,  # don't validate
                        conflict_strategy,
                        **kwargs
                    )
                except Exception as e:
                    logger.warning(f"Error copying {profile_type} profile '{profile_name}': {e}")
                    # Continue with other profiles
                    
    def _handle_security_profile(
        self,
        profile_element: etree._Element,
        profile_type: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Generic handler for security profiles.
        
        This method processes security profiles and handles any references they contain.
        Different types of security profiles have different structures and references,
        so this method dispatches to type-specific handlers.
        
        Args:
            profile_element: The security profile XML element
            profile_type: Type of security profile (virus, spyware, etc.)
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            skip_if_exists: Skip if profile already exists in target
            conflict_strategy: Strategy for conflict resolution
            **kwargs: Additional context parameters
        """
        profile_name = profile_element.get("name", "unknown")
        logger.debug(f"Processing {profile_type} profile '{profile_name}'")
        
        # Dispatch to specific handlers based on profile type
        if profile_type == "virus":
            self._handle_antivirus_profile(profile_element, profile_name, source_context_type, 
                                         target_context_type, skip_if_exists, conflict_strategy, **kwargs)
        elif profile_type == "spyware":
            self._handle_antispyware_profile(profile_element, profile_name, source_context_type, 
                                           target_context_type, skip_if_exists, conflict_strategy, **kwargs)
        elif profile_type == "vulnerability":
            self._handle_vulnerability_profile(profile_element, profile_name, source_context_type, 
                                            target_context_type, skip_if_exists, conflict_strategy, **kwargs)
        elif profile_type == "url-filtering":
            self._handle_url_filtering_profile(profile_element, profile_name, source_context_type, 
                                             target_context_type, skip_if_exists, conflict_strategy, **kwargs)
        elif profile_type == "file-blocking":
            self._handle_file_blocking_profile(profile_element, profile_name, source_context_type, 
                                             target_context_type, skip_if_exists, conflict_strategy, **kwargs)
        elif profile_type == "wildfire-analysis":
            self._handle_wildfire_profile(profile_element, profile_name, source_context_type, 
                                         target_context_type, skip_if_exists, conflict_strategy, **kwargs)
        elif profile_type == "dns-security":
            self._handle_dns_security_profile(profile_element, profile_name, source_context_type, 
                                           target_context_type, skip_if_exists, conflict_strategy, **kwargs)
        else:
            logger.debug(f"No specific handler for {profile_type} profile type")
            
    def _handle_antivirus_profile(
        self,
        profile_element: etree._Element,
        profile_name: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle antivirus profile specific elements.
        
        Args:
            profile_element: The antivirus profile XML element
            profile_name: Name of the profile
            source_context_type: Type of source context
            target_context_type: Type of target context
            skip_if_exists: Skip if exists in target
            conflict_strategy: Strategy for conflict resolution
            **kwargs: Additional context parameters
        """
        logger.debug(f"Processing antivirus profile '{profile_name}'")
        
        # Extract and handle application exceptions
        app_exceptions = find_elements(profile_element, './/application-exception/entry')
        
        for app_exception in app_exceptions:
            app_name = app_exception.get("name")
            if app_name:
                logger.debug(f"Found application exception for '{app_name}'")
                
                # Ensure the application exists in target config
                try:
                    self.copy_object(
                        "application",
                        app_name,
                        source_context_type,
                        target_context_type,
                        skip_if_exists,
                        True,  # copy references
                        False,  # don't validate
                        conflict_strategy,
                        **kwargs
                    )
                except Exception as e:
                    logger.warning(f"Error copying application '{app_name}': {e}")
                    
        # Handle version-specific element differences
        if self.source_version != self.target_version:
            # Handle ML-AV elements introduced in PAN-OS 11.0+
            if self.source_version >= "11.0" and self.target_version < "11.0":
                ml_elements = [
                    "mlav-engine-url-db-version",
                    "mlav-engine-minimum-version",
                    "machine-learning-model",
                    "machine-learning-threshold-levels"
                ]
                
                for ml_elem in ml_elements:
                    elements = find_elements(profile_element, f'.//{ml_elem}')
                    for elem in elements:
                        logger.debug(f"Removing newer element '{ml_elem}' from antivirus profile '{profile_name}'")
                        if elem.getparent() is not None:
                            elem.getparent().remove(elem)
                            
    def _handle_antispyware_profile(
        self,
        profile_element: etree._Element,
        profile_name: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle anti-spyware profile specific elements.
        
        Args:
            profile_element: The anti-spyware profile XML element
            profile_name: Name of the profile
            source_context_type: Type of source context
            target_context_type: Type of target context
            skip_if_exists: Skip if exists in target
            conflict_strategy: Strategy for conflict resolution
            **kwargs: Additional context parameters
        """
        logger.debug(f"Processing anti-spyware profile '{profile_name}'")
        
        # Process threat exceptions
        threat_exceptions = find_elements(profile_element, './/threat-exception/entry')
        
        for exception in threat_exceptions:
            # Extract any referenced objects from exceptions
            # For now, we just log it for future implementation
            exception_name = exception.get("name")
            if exception_name:
                logger.debug(f"Found threat exception for '{exception_name}'")
        
        # Handle cloud inline analysis (added in 10.2+)
        if self.source_version >= "10.2" and self.target_version < "10.2":
            cloud_analysis_elem = find_element(profile_element, './/cloud-inline-analysis')
            if cloud_analysis_elem is not None and cloud_analysis_elem.getparent() is not None:
                logger.debug(f"Removing newer element 'cloud-inline-analysis' from anti-spyware profile '{profile_name}'")
                cloud_analysis_elem.getparent().remove(cloud_analysis_elem)
                
    def _handle_vulnerability_profile(
        self,
        profile_element: etree._Element,
        profile_name: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle vulnerability profile specific elements.
        
        Args:
            profile_element: The vulnerability profile XML element
            profile_name: Name of the profile
            source_context_type: Type of source context
            target_context_type: Type of target context
            skip_if_exists: Skip if exists in target
            conflict_strategy: Strategy for conflict resolution
            **kwargs: Additional context parameters
        """
        logger.debug(f"Processing vulnerability profile '{profile_name}'")
        
        # Process threat exceptions
        threat_exceptions = find_elements(profile_element, './/threat-exception/entry')
        
        for exception in threat_exceptions:
            # Extract any referenced objects from exceptions
            # For now, we just log it for future implementation
            exception_name = exception.get("name")
            if exception_name:
                logger.debug(f"Found threat exception for '{exception_name}'")
                
    def _handle_url_filtering_profile(
        self,
        profile_element: etree._Element,
        profile_name: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle URL filtering profile specific elements.
        
        Args:
            profile_element: The URL filtering profile XML element
            profile_name: Name of the profile
            source_context_type: Type of source context
            target_context_type: Type of target context
            skip_if_exists: Skip if exists in target
            conflict_strategy: Strategy for conflict resolution
            **kwargs: Additional context parameters
        """
        logger.debug(f"Processing URL filtering profile '{profile_name}'")
        
        # Handle custom URL categories
        custom_categories = find_elements(profile_element, './/override/member')
        for category in custom_categories:
            if category.text:
                category_name = category.text
                logger.debug(f"Found custom URL category reference: {category_name}")
                
                # Copy the custom URL category
                try:
                    self.copy_object(
                        "custom-url-category",
                        category_name,
                        source_context_type,
                        target_context_type,
                        skip_if_exists,
                        True,  # copy references
                        False,  # don't validate
                        conflict_strategy,
                        **kwargs
                    )
                except Exception as e:
                    logger.warning(f"Error copying custom URL category '{category_name}': {e}")
                    
        # Handle version-specific elements
        if self.source_version != self.target_version:
            # Handle elements added in PAN-OS 10.2+
            if self.source_version >= "10.2" and self.target_version < "10.2":
                newer_elements = ["extended-log", "http-header-insertion"]
                for elem_name in newer_elements:
                    elem = find_element(profile_element, f'.//{elem_name}')
                    if elem is not None and elem.getparent() is not None:
                        logger.debug(f"Removing newer element '{elem_name}' from URL filtering profile '{profile_name}'")
                        elem.getparent().remove(elem)
                        
            # Handle elements added in PAN-OS 11.0+
            if self.source_version >= "11.0" and self.target_version < "11.0":
                ml_elem = find_element(profile_element, './/machine-learning-model')
                if ml_elem is not None and ml_elem.getparent() is not None:
                    logger.debug(f"Removing newer element 'machine-learning-model' from URL filtering profile '{profile_name}'")
                    ml_elem.getparent().remove(ml_elem)
                    
    def _handle_file_blocking_profile(
        self,
        profile_element: etree._Element,
        profile_name: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle file blocking profile specific elements.
        
        Args:
            profile_element: The file blocking profile XML element
            profile_name: Name of the profile
            source_context_type: Type of source context
            target_context_type: Type of target context
            skip_if_exists: Skip if exists in target
            conflict_strategy: Strategy for conflict resolution
            **kwargs: Additional context parameters
        """
        logger.debug(f"Processing file blocking profile '{profile_name}'")
        
        # File blocking profiles are relatively simple and don't typically
        # have references to other objects. The rules define file types and actions.
        # This method is included for completeness and future extensibility.
                    
    def _handle_wildfire_profile(
        self,
        profile_element: etree._Element,
        profile_name: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle WildFire analysis profile specific elements.
        
        Args:
            profile_element: The WildFire profile XML element
            profile_name: Name of the profile
            source_context_type: Type of source context
            target_context_type: Type of target context
            skip_if_exists: Skip if exists in target
            conflict_strategy: Strategy for conflict resolution
            **kwargs: Additional context parameters
        """
        logger.debug(f"Processing WildFire profile '{profile_name}'")
        
        # Extract and handle application exceptions
        app_exceptions = find_elements(profile_element, './/application-exception/entry')
        
        for app_exception in app_exceptions:
            app_name = app_exception.get("name")
            if app_name:
                logger.debug(f"Found application exception for '{app_name}'")
                
                # Ensure the application exists in target config
                try:
                    self.copy_object(
                        "application",
                        app_name,
                        source_context_type,
                        target_context_type,
                        skip_if_exists,
                        True,  # copy references
                        False,  # don't validate
                        conflict_strategy,
                        **kwargs
                    )
                except Exception as e:
                    logger.warning(f"Error copying application '{app_name}': {e}")
                    
        # Handle version-specific element differences
        if self.source_version != self.target_version:
            # Handle 'report-phishing-file' element added in PAN-OS 10.2+
            if self.source_version >= "10.2" and self.target_version < "10.2":
                phishing_elem = find_element(profile_element, './/report-phishing-file')
                if phishing_elem is not None and phishing_elem.getparent() is not None:
                    logger.debug(f"Removing newer element 'report-phishing-file' from WildFire profile '{profile_name}'")
                    phishing_elem.getparent().remove(phishing_elem)
                    
    def _handle_dns_security_profile(
        self,
        profile_element: etree._Element,
        profile_name: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle DNS security profile specific elements.
        
        Args:
            profile_element: The DNS security profile XML element
            profile_name: Name of the profile
            source_context_type: Type of source context
            target_context_type: Type of target context
            skip_if_exists: Skip if exists in target
            conflict_strategy: Strategy for conflict resolution
            **kwargs: Additional context parameters
        """
        logger.debug(f"Processing DNS security profile '{profile_name}'")
        
        # Process threat exceptions
        threat_exceptions = find_elements(profile_element, './/threat-exception/entry')
        
        for exception in threat_exceptions:
            # Extract any referenced objects from exceptions
            # For now, we just log it for future implementation
            exception_name = exception.get("name")
            if exception_name:
                logger.debug(f"Found threat exception for '{exception_name}'")
        
        # Handle version-specific elements
        if self.source_version != self.target_version:
            # Handle cloud inline analysis (added in 10.2+)
            if self.source_version >= "10.2" and self.target_version < "10.2":
                cloud_analysis_elem = find_element(profile_element, './/cloud-inline-analysis')
                if cloud_analysis_elem is not None and cloud_analysis_elem.getparent() is not None:
                    logger.debug(f"Removing newer element 'cloud-inline-analysis' from DNS security profile '{profile_name}'")
                    cloud_analysis_elem.getparent().remove(cloud_analysis_elem)
                    
    def _handle_schedule(
        self,
        schedule_element: etree._Element,
        schedule_name: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle schedule object references and version-specific elements.
        
        Schedule objects define time periods for various security policies
        and can be referenced by security rules or other policy objects.
        
        Args:
            schedule_element: The schedule XML element
            schedule_name: Name of the schedule
            source_context_type: Type of source context
            target_context_type: Type of target context
            skip_if_exists: Skip if exists in target
            conflict_strategy: Strategy for conflict resolution
            **kwargs: Additional context parameters
        """
        logger.debug(f"Processing schedule object '{schedule_name}'")
        
        # The schedule object is fairly simple and doesn't reference other objects
        # It primarily defines time periods with start/end times and dates
        
        # Handle version-specific changes if needed in the future
        if self.source_version != self.target_version:
            # Currently, schedules are fairly consistent across PAN-OS versions,
            # but this is a placeholder for future version-specific handling
            pass
            
    def _handle_custom_url_category(
        self,
        category_element: etree._Element,
        category_name: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle custom URL category references and version-specific elements.
        
        Custom URL categories define lists of URLs or domains that can be used
        in URL filtering profiles for web access control.
        
        Args:
            category_element: The custom URL category XML element
            category_name: Name of the category
            source_context_type: Type of source context
            target_context_type: Type of target context
            skip_if_exists: Skip if exists in target
            conflict_strategy: Strategy for conflict resolution
            **kwargs: Additional context parameters
        """
        logger.debug(f"Processing custom URL category '{category_name}'")
        
        # Handle version-specific changes if needed
        if self.source_version != self.target_version:
            # Check for type attribute changes between versions
            # Currently, both "URL List" and "Category Match" types are supported in 10.x and 11.x
            pass
            
        # Custom URL categories can reference external dynamic lists (EDLs)
        list_elem = find_element(category_element, './list')
        if list_elem is not None:
            external_lists = find_elements(list_elem, './external-list')
            
            for ext_list in external_lists:
                if ext_list.text:
                    edl_name = ext_list.text
                    logger.debug(f"Found external list reference: {edl_name}")
                    
                    # Copy the referenced EDL
                    try:
                        self.copy_object(
                            "external-list",
                            edl_name,
                            source_context_type,
                            target_context_type,
                            skip_if_exists,
                            True,  # copy references
                            False,  # don't validate
                            conflict_strategy,
                            **kwargs
                        )
                    except Exception as e:
                        logger.warning(f"Error copying external list '{edl_name}': {e}")
                        
        # Check for references to URL filtering security profiles
        # This is a bit of a reverse lookup - we need to find URL filtering profiles
        # that reference this custom URL category
        try:
            object_xpath = get_object_xpath(
                "url-filtering", 
                self.source_device_type, 
                source_context_type, 
                self.source_version, 
                **kwargs
            )
            
            # Split to get parent path
            parent_parts = object_xpath.rsplit('/', 1)
            if len(parent_parts) >= 2:
                parent_xpath = parent_parts[0]
                
                # Find all URL filtering profiles
                profiles = xpath_search(self.source_tree, f"{parent_xpath}/entry")
                
                # Look for references to this category in the profiles
                for profile in profiles:
                    profile_name = profile.get("name", "unknown")
                    
                    # Check all category action lists (block, alert, allow, etc.)
                    for action in ["block", "alert", "allow", "continue", "override"]:
                        members = find_elements(profile, f'./{action}/member')
                        for member in members:
                            if member.text == category_name:
                                logger.debug(f"Found reference to custom URL category '{category_name}' in URL filtering profile '{profile_name}'")
                                
                                # Suggest copying the URL filtering profile
                                logger.info(f"URL filtering profile '{profile_name}' references this custom URL category. You may want to copy it as well.")
        except Exception as e:
            logger.warning(f"Error checking for URL filtering profile references: {e}")
            
    def _handle_security_profiles_in_rules(
        self,
        rule_element: etree._Element,
        rule_name: str,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle security profile references in security rules.
        
        This method finds all security profiles and profile groups referenced
        in a security rule and ensures they are copied to the target context.
        
        Args:
            rule_element: The XML element of the security rule
            rule_name: Name of the rule
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            skip_if_exists: Skip if profile already exists in target
            conflict_strategy: Strategy for conflict resolution
            **kwargs: Additional context parameters
        """
        logger.debug(f"Processing security profiles in rule '{rule_name}'")
        
        # Check for schedule reference first
        schedule_elem = find_element(rule_element, './schedule')
        if schedule_elem is not None and schedule_elem.text:
            schedule_name = schedule_elem.text
            logger.debug(f"Found schedule reference: {schedule_name}")
            
            # Copy the schedule
            try:
                self.copy_object(
                    "schedule",
                    schedule_name,
                    source_context_type,
                    target_context_type,
                    skip_if_exists,
                    True,  # copy references
                    False,  # don't validate
                    conflict_strategy,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"Error copying schedule '{schedule_name}': {e}")
        
        # Check for profile-setting element
        profile_setting = find_element(rule_element, './profile-setting')
        if profile_setting is None:
            logger.debug(f"No profile settings found in rule '{rule_name}'")
            return
            
        # Check for profile group reference
        group_ref = find_element(profile_setting, './group')
        if group_ref is not None and group_ref.text:
            group_name = group_ref.text
            logger.debug(f"Found security profile group reference: {group_name}")
            
            # Copy the profile group and all profiles it references
            try:
                self.copy_object(
                    "security_profile_group",
                    group_name,
                    source_context_type,
                    target_context_type,
                    skip_if_exists,
                    True,  # copy references
                    False,  # don't validate
                    conflict_strategy,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"Error copying security profile group '{group_name}': {e}")
                
        # Check for individual profile references
        profiles = find_element(profile_setting, './profiles')
        if profiles is not None:
            profile_types = [
                ("virus", "virus"),
                ("spyware", "spyware"),
                ("vulnerability", "vulnerability"),
                ("url-filtering", "url-filtering"),
                ("file-blocking", "file-blocking"),
                ("wildfire-analysis", "wildfire-analysis"),
                ("data-filtering", "data-filtering"),
                ("dns-security", "dns-security")
            ]
            
            for elem_name, profile_type in profile_types:
                profile_ref = find_element(profiles, f'./{elem_name}')
                if profile_ref is not None and profile_ref.text:
                    profile_name = profile_ref.text
                    logger.debug(f"Found {profile_type} profile reference: {profile_name}")
                    
                    # Copy the profile
                    try:
                        self.copy_object(
                            profile_type,
                            profile_name,
                            source_context_type,
                            target_context_type,
                            skip_if_exists,
                            True,  # copy references
                            False,  # don't validate
                            conflict_strategy,
                            **kwargs
                        )
                    except Exception as e:
                        logger.warning(f"Error copying {profile_type} profile '{profile_name}': {e}")
    
    def _handle_service_group(
        self,
        group_element: etree._Element,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle service group objects.
        
        Service groups can contain references to both services and other service groups,
        creating complex dependencies that need special handling.
        
        Args:
            group_element: The XML element of the service group
            source_context_type: Type of source context
            target_context_type: Type of target context
            skip_if_exists: Skip if service already exists in target
            conflict_strategy: Strategy for conflict resolution
            **kwargs: Additional context parameters
        """
        group_name = group_element.get("name", "unknown")
        logger.debug(f"Processing service group '{group_name}'")
        
        # Get all member references
        members = find_elements(group_element, './members/member')
        
        if not members:
            logger.debug(f"No members found in service group '{group_name}'")
            return
            
        logger.debug(f"Found {len(members)} members in service group '{group_name}'")
        
        # Process each member
        for member in members:
            if member.text:
                member_name = member.text
                logger.debug(f"Processing service group member: {member_name}")
                
                # First try to copy it as a service
                try:
                    success = self.copy_object(
                        "service",
                        member_name,
                        source_context_type,
                        target_context_type,
                        skip_if_exists,
                        True,  # copy references
                        False,  # don't validate
                        conflict_strategy,
                        **kwargs
                    )
                    
                    if success:
                        logger.debug(f"Successfully copied service '{member_name}'")
                        continue
                except Exception as e:
                    logger.debug(f"Error copying service '{member_name}': {e}")
                    # Falls through to try as a service group
                
                # If not found as a service, try as a service group
                try:
                    success = self.copy_object(
                        "service_group",
                        member_name,
                        source_context_type,
                        target_context_type,
                        skip_if_exists,
                        True,  # copy references
                        False,  # don't validate
                        conflict_strategy,
                        **kwargs
                    )
                    
                    if success:
                        logger.debug(f"Successfully copied service group '{member_name}'")
                    else:
                        logger.warning(f"Failed to copy service group member '{member_name}'")
                except Exception as e:
                    logger.warning(f"Error copying service group '{member_name}': {e}")
                    
    def _handle_dynamic_address_group(
        self,
        group_element: etree._Element,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        conflict_strategy: Optional[ConflictStrategy] = None,
        **kwargs
    ) -> None:
        """
        Handle dynamic address group filters and ensure referenced tags exist in target.
        
        Args:
            group_element: The XML element of the dynamic address group
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            skip_if_exists: Skip if tag already exists in target (deprecated, use conflict_strategy instead)
            conflict_strategy: Strategy to use when resolving conflicts
            **kwargs: Additional context parameters
        """
        group_name = group_element.get("name", "unknown")
        filter_element = find_element(group_element, './dynamic/filter')
        
        if not filter_element or not filter_element.text:
            logger.debug(f"No filter found in dynamic address group '{group_name}'")
            return
            
        filter_text = filter_element.text
        logger.debug(f"Processing dynamic address group filter: {filter_text}")
        
        # Extract tag names from the filter
        # This is a simple extraction that handles basic tag expressions like 'tag1' or 'tag1 and tag2'
        # A more comprehensive parser would be needed for complex expressions
        import re
        tag_pattern = r"'([^']+)'|\"([^\"]+)\""
        tag_matches = re.findall(tag_pattern, filter_text)
        
        # Flatten the matches (each match is a tuple of two groups)
        tag_names = [m[0] or m[1] for m in tag_matches]
        
        if not tag_names:
            logger.debug(f"No tag references found in filter: {filter_text}")
            return
            
        logger.debug(f"Found {len(tag_names)} tag references in filter: {', '.join(tag_names)}")
        
        # Extract source parameters
        source_params = self._extract_context_params(source_context_type, kwargs, 'source_')
        
        # For each tag referenced, check if it exists in target and copy if needed
        for tag_name in tag_names:
            logger.debug(f"Processing tag from filter: {tag_name}")
            
            # Try to find the tag in the source configuration
            try:
                tag_xpath = get_object_xpath(
                    "tag", 
                    self.source_device_type, 
                    source_context_type, 
                    self.source_version, 
                    tag_name, 
                    **source_params
                )
                
                logger.debug(f"Looking for tag using XPath: {tag_xpath}")
                source_tag_elements = xpath_search(self.source_tree, tag_xpath)
                
                if source_tag_elements:
                    logger.debug(f"Found tag '{tag_name}' in source, copying to target")
                    # Copy the tag to the target
                    self.copy_object(
                        "tag",
                        tag_name,
                        source_context_type,
                        target_context_type,
                        skip_if_exists,
                        False,  # No need to copy references for tags
                        **kwargs
                    )
                else:
                    logger.debug(f"Tag '{tag_name}' not found in source, may be a built-in tag")
                
            except Exception as e:
                logger.warning(f"Error copying tag '{tag_name}' from filter: {e}")
                # Continue with next tag

    def _copy_related_tags(
        self,
        object_element: etree._Element,
        source_context_type: str,
        target_context_type: str,
        skip_if_exists: bool = True,
        **kwargs
    ) -> None:
        """
        Copy tags related to an object, ensuring they exist in the target configuration.
        
        Args:
            object_element: The XML element of the object being copied
            source_context_type: Type of source context (shared, device_group, vsys)
            target_context_type: Type of target context (shared, device_group, vsys)
            skip_if_exists: Skip if tag already exists in target
            **kwargs: Additional context parameters
        """
        # Find tag references in the object
        tag_elements = find_elements(object_element, './/tag/member')
        
        if not tag_elements:
            logger.debug("No tags found in object")
            return
            
        logger.debug(f"Found {len(tag_elements)} tag references in object")
        
        # Extract source parameters
        source_params = self._extract_context_params(source_context_type, kwargs, 'source_')
        
        # For each tag referenced, check if it exists in target and copy if needed
        for tag_element in tag_elements:
            if tag_element.text:
                tag_name = tag_element.text
                logger.debug(f"Processing tag: {tag_name}")
                
                # Try to find the tag in the source configuration
                try:
                    tag_xpath = get_object_xpath(
                        "tag", 
                        self.source_device_type, 
                        source_context_type, 
                        self.source_version, 
                        tag_name, 
                        **source_params
                    )
                    
                    logger.debug(f"Looking for tag using XPath: {tag_xpath}")
                    source_tag_elements = xpath_search(self.source_tree, tag_xpath)
                    
                    if source_tag_elements:
                        logger.debug(f"Found tag '{tag_name}' in source, copying to target")
                        # Copy the tag to the target
                        self.copy_object(
                            "tag",
                            tag_name,
                            source_context_type,
                            target_context_type,
                            skip_if_exists,
                            False,  # No need to copy references for tags
                            **kwargs
                        )
                    else:
                        logger.debug(f"Tag '{tag_name}' not found in source, may be a built-in tag")
                    
                except Exception as e:
                    logger.warning(f"Error copying tag '{tag_name}': {e}")
                    # Continue with next tag
    
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
            
    def _handle_version_specific_attributes(
        self,
        object_element: etree._Element,
        object_type: str
    ) -> etree._Element:
        """
        Handle version-specific attributes for objects being copied between different PAN-OS versions.
        
        This method checks for attributes that may be available in the source version but not in
        the target version, or vice versa. It modifies the object as needed to ensure compatibility
        with the target version.
        
        Args:
            object_element: The XML element of the object being copied
            object_type: The type of object (address, service, etc.)
            
        Returns:
            etree._Element: The modified element compatible with the target version
        """
        # Skip if source and target versions are the same
        if self.source_version == self.target_version:
            logger.debug(f"Source and target versions are the same ({self.source_version}), no attribute transformation needed")
            return object_element
            
        object_name = object_element.get("name", "unknown")
        logger.debug(f"Handling version-specific attributes for {object_type} '{object_name}'")
        logger.debug(f"Converting from version {self.source_version} to {self.target_version}")
        
        # Get a normalized version of the object type (some types have hyphens in the XML but not in our mapping)
        normalized_type = object_type.replace("_", "-").replace(" ", "-")
        
        # Check if we have version-specific information for this object type
        if normalized_type not in self.VERSION_SPECIFIC_ATTRIBUTES:
            logger.debug(f"No version-specific attribute information available for {normalized_type}")
            return object_element
            
        # Get the attribute definitions
        attr_defs = self.VERSION_SPECIFIC_ATTRIBUTES[normalized_type]
        
        # Create a copy of the element to modify
        modified_element = copy.deepcopy(object_element)
        
        # Process each attribute
        for attr_name, version_info in attr_defs.items():
            source_required = version_info.get(self.source_version, False)
            target_required = version_info.get(self.target_version, False)
            
            # Check if the attribute exists in the source version but not in the target version
            if self.source_version in version_info and self.target_version not in version_info:
                logger.debug(f"Attribute '{attr_name}' exists in source version {self.source_version} but not in target version {self.target_version}")
                
                # Remove the attribute if it exists in the object
                attr_elements = modified_element.xpath(f'./{attr_name}')
                if attr_elements:
                    logger.debug(f"Removing attribute '{attr_name}' from {object_type} '{object_name}'")
                    for elem in attr_elements:
                        elem.getparent().remove(elem)
            
            # Check if the attribute is required in the target but not in the source
            elif not source_required and target_required:
                logger.debug(f"Attribute '{attr_name}' is required in target version {self.target_version} but not in source version {self.source_version}")
                
                # Check if the attribute exists in the object
                attr_elements = modified_element.xpath(f'./{attr_name}')
                if not attr_elements:
                    logger.warning(f"Required attribute '{attr_name}' for target version {self.target_version} is missing in {object_type} '{object_name}'")
                    # We can't add the attribute because we don't know what value to use
                    # This is likely to cause an error when the object is saved to the target
            
            # Color attribute special handling (format changed between versions)
            if attr_name == "color" and self.source_version != self.target_version:
                color_elements = modified_element.xpath(f'./{attr_name}')
                if color_elements:
                    # PAN-OS color formats may differ between versions
                    # In newer versions, colors can have names or color codes
                    # In older versions, only color codes might be supported
                    # This is a simplistic adaptation - a real implementation would need to map color names to codes
                    color_element = color_elements[0]
                    if color_element.text and not color_element.text.isdigit():
                        # If it's a named color and we're going to an older version, use a default color code
                        if self.source_version > self.target_version:
                            logger.debug(f"Converting named color '{color_element.text}' to default color code '1'")
                            color_element.text = "1"  # Default color code
        
        # Handle specific object types that changed significantly between versions
        if normalized_type == "address":
            self._handle_address_version_changes(modified_element, object_name)
        elif normalized_type == "external-list":
            self._handle_edl_version_changes(modified_element, object_name)
            
        return modified_element
    
    def _handle_address_version_changes(self, address_element: etree._Element, address_name: str) -> None:
        """Handle specific version changes for address objects."""
        # In some versions, the "ip-netmask" format might be different
        # For example, in newer versions, an address object might support additional attributes
        # like "enable-override" or "override-session-timeout" that don't exist in older versions
        
        # Check for newer attributes not supported in older versions
        if self.source_version > self.target_version:
            newer_attrs = ["enable-override", "override-session-timeout", "whitelist"]
            for attr in newer_attrs:
                attr_elements = address_element.xpath(f'./{attr}')
                if attr_elements:
                    logger.debug(f"Removing newer attribute '{attr}' from address '{address_name}'")
                    for elem in attr_elements:
                        elem.getparent().remove(elem)
    
    def _handle_edl_version_changes(self, edl_element: etree._Element, edl_name: str) -> None:
        """Handle specific version changes for external dynamic list objects."""
        # External dynamic lists (EDLs) can have different attributes in different versions
        # For example, in newer versions, an EDL might support additional attributes
        # like "certificate-profile" or specific recurring options
        
        # Check for newer attributes not supported in older versions
        if self.source_version > self.target_version:
            if self.target_version.startswith("10.1"):
                # Check for attributes added in 10.2+
                newer_attrs = ["auth", "client-cert", "client-key", "certificate-profile"]
                for attr in newer_attrs:
                    attr_elements = edl_element.xpath(f'./{attr}')
                    if attr_elements:
                        logger.debug(f"Removing newer attribute '{attr}' from EDL '{edl_name}'")
                        for elem in attr_elements:
                            elem.getparent().remove(elem)
                            
    def validate_object(
        self,
        object_element: etree._Element,
        object_type: str,
        **kwargs
    ) -> Tuple[bool, List[str]]:
        """
        Validate a PAN-OS object for correctness and integrity.
        
        This method examines an object and checks for common issues such as:
        - Missing required attributes
        - Invalid values for attributes
        - Referenced objects that don't exist
        - Other constraints specific to the object type
        
        Args:
            object_element: The XML element of the object to validate
            object_type: The type of object (address, service, etc.)
            **kwargs: Additional validation parameters
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list of validation error messages)
        """
        object_name = object_element.get("name", "unknown")
        logger.info(f"Validating {object_type} object '{object_name}'")
        
        # List to collect validation error messages
        validation_errors = []
        
        # Use the appropriate validation method for the object type
        if object_type in ["address", "address-object"]:
            self._validate_address_object(object_element, object_name, validation_errors)
        elif object_type in ["address-group", "address_group"]:
            self._validate_address_group(object_element, object_name, validation_errors)
        elif object_type in ["service", "service-object"]:
            self._validate_service_object(object_element, object_name, validation_errors)
        elif object_type in ["service-group", "service_group"]:
            self._validate_service_group(object_element, object_name, validation_errors)
        elif object_type in ["tag"]:
            self._validate_tag(object_element, object_name, validation_errors)
        elif object_type in ["external-list", "external_dynamic_list", "edl"]:
            self._validate_edl(object_element, object_name, validation_errors)
        elif object_type in ["schedule"]:
            self._validate_schedule(object_element, object_name, validation_errors)
        # Security profile validation
        elif object_type in ["security_profile_group", "security-profile-group", "profile-group"]:
            self._validate_security_profile_group(object_element, object_name, validation_errors)
        elif object_type in ["virus", "antivirus", "virus-profile"]:
            self._validate_antivirus_profile(object_element, object_name, validation_errors)
        elif object_type in ["spyware", "antispyware", "spyware-profile"]:
            self._validate_antispyware_profile(object_element, object_name, validation_errors)
        elif object_type in ["vulnerability", "vulnerability-profile"]:
            self._validate_vulnerability_profile(object_element, object_name, validation_errors)
        elif object_type in ["url-filtering", "url-filtering-profile"]:
            self._validate_url_filtering_profile(object_element, object_name, validation_errors)
        elif object_type in ["file-blocking", "file-blocking-profile"]:
            self._validate_file_blocking_profile(object_element, object_name, validation_errors)
        elif object_type in ["wildfire-analysis", "wildfire-profile"]:
            self._validate_wildfire_profile(object_element, object_name, validation_errors)
        elif object_type in ["dns-security", "dns-security-profile"]:
            self._validate_dns_security_profile(object_element, object_name, validation_errors)
        elif object_type in ["custom-url-category", "url-category"]:
            self._validate_custom_url_category(object_element, object_name, validation_errors)
        else:
            logger.warning(f"No specific validation rules for object type: {object_type}")
            # Perform generic validation
            self._validate_generic_object(object_element, object_name, object_type, validation_errors)
        
        # Additional validation for common elements
        self._validate_common_elements(object_element, object_name, validation_errors)
        
        # Log results
        is_valid = len(validation_errors) == 0
        if is_valid:
            logger.info(f"Validation successful for {object_type} object '{object_name}'")
        else:
            logger.warning(f"Validation failed for {object_type} object '{object_name}' with {len(validation_errors)} errors")
            for error in validation_errors:
                logger.warning(f"  - {error}")
        
        return is_valid, validation_errors
    
    def _validate_common_elements(
        self,
        object_element: etree._Element,
        object_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate common elements that can appear in any object."""
        
        # Check for empty name
        if not object_name or object_name == "unknown":
            validation_errors.append(f"Object has missing or invalid name attribute")
            
        # Check description length
        description_elem = find_element(object_element, './description')
        if description_elem is not None and description_elem.text:
            if len(description_elem.text) > 1024:  # PAN-OS typically has a limit around 1024 chars
                validation_errors.append(f"Description exceeds maximum length (1024 characters)")
                
        # Check tag references
        tag_elems = find_elements(object_element, './/tag/member')
        for tag_elem in tag_elems:
            if not tag_elem.text or tag_elem.text.strip() == "":
                validation_errors.append(f"Empty tag reference found")
    
    def _validate_address_object(
        self,
        address_element: etree._Element,
        address_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate an address object."""
        
        # Check for required address type
        address_types = ['ip-netmask', 'ip-range', 'fqdn', 'ip-wildcard']
        found_type = False
        
        for addr_type in address_types:
            type_elem = find_element(address_element, f'./{addr_type}')
            if type_elem is not None:
                found_type = True
                
                # Validate the specific address type
                if addr_type == 'ip-netmask':
                    if not type_elem.text or not self._is_valid_ip_netmask(type_elem.text):
                        validation_errors.append(f"Invalid IP netmask format: {type_elem.text}")
                        
                elif addr_type == 'ip-range':
                    if not type_elem.text or not self._is_valid_ip_range(type_elem.text):
                        validation_errors.append(f"Invalid IP range format: {type_elem.text}")
                        
                elif addr_type == 'fqdn':
                    if not type_elem.text or not self._is_valid_fqdn(type_elem.text):
                        validation_errors.append(f"Invalid FQDN format: {type_elem.text}")
                        
                elif addr_type == 'ip-wildcard':
                    if not type_elem.text or not self._is_valid_ip_wildcard(type_elem.text):
                        validation_errors.append(f"Invalid IP wildcard format: {type_elem.text}")
        
        if not found_type:
            validation_errors.append(f"Address object must have one of these types: {', '.join(address_types)}")
    
    def _validate_address_group(
        self,
        group_element: etree._Element,
        group_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate an address group object."""
        
        # Check for either static or dynamic type
        static_elem = find_element(group_element, './static')
        dynamic_elem = find_element(group_element, './dynamic')
        
        if not static_elem and not dynamic_elem:
            validation_errors.append(f"Address group must be either static or dynamic")
            return
            
        if static_elem and dynamic_elem:
            validation_errors.append(f"Address group cannot be both static and dynamic")
            
        # Validate static group
        if static_elem:
            members = find_elements(static_elem, './member')
            if not members:
                validation_errors.append(f"Static address group has no members")
            
            for member in members:
                if not member.text or member.text.strip() == "":
                    validation_errors.append(f"Empty member in static address group")
        
        # Validate dynamic group
        if dynamic_elem:
            filter_elem = find_element(dynamic_elem, './filter')
            if not filter_elem or not filter_elem.text or filter_elem.text.strip() == "":
                validation_errors.append(f"Dynamic address group has empty filter expression")
            elif filter_elem.text:
                if not self._is_valid_dynamic_filter(filter_elem.text):
                    validation_errors.append(f"Invalid dynamic filter expression: {filter_elem.text}")
    
    def _validate_service_object(
        self,
        service_element: etree._Element,
        service_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate a service object."""
        
        # Check for protocol
        protocol_elem = find_element(service_element, './protocol')
        if not protocol_elem:
            validation_errors.append(f"Service object missing protocol element")
            return
            
        protocol = protocol_elem.text if protocol_elem.text else ""
        
        # Validate based on protocol type
        if protocol == "tcp" or protocol == "udp":
            # Check for source port
            source_port_elem = find_element(service_element, './source-port')
            if source_port_elem is not None and source_port_elem.text:
                if not self._is_valid_port_range(source_port_elem.text):
                    validation_errors.append(f"Invalid source port range: {source_port_elem.text}")
            
            # Check for destination port (required)
            dest_port_elem = find_element(service_element, './port')
            if not dest_port_elem or not dest_port_elem.text:
                validation_errors.append(f"Service object missing port element for {protocol} protocol")
            elif not self._is_valid_port_range(dest_port_elem.text):
                validation_errors.append(f"Invalid destination port range: {dest_port_elem.text}")
                
        elif protocol == "sctp":
            # Similar to TCP/UDP
            dest_port_elem = find_element(service_element, './port')
            if not dest_port_elem or not dest_port_elem.text:
                validation_errors.append(f"Service object missing port element for {protocol} protocol")
            elif not self._is_valid_port_range(dest_port_elem.text):
                validation_errors.append(f"Invalid destination port range: {dest_port_elem.text}")
                
        elif protocol == "icmp" or protocol == "icmp6":
            # Check for ICMP type and code
            icmp_type_elem = find_element(service_element, './icmp-type')
            icmp_code_elem = find_element(service_element, './icmp-code')
            
            if icmp_type_elem is not None and icmp_type_elem.text:
                try:
                    icmp_type = int(icmp_type_elem.text)
                    if icmp_type < 0 or icmp_type > 255:
                        validation_errors.append(f"Invalid ICMP type: {icmp_type} (must be 0-255)")
                except ValueError:
                    validation_errors.append(f"Invalid ICMP type: {icmp_type_elem.text} (must be a number)")
                    
            if icmp_code_elem is not None and icmp_code_elem.text:
                try:
                    icmp_code = int(icmp_code_elem.text)
                    if icmp_code < 0 or icmp_code > 255:
                        validation_errors.append(f"Invalid ICMP code: {icmp_code} (must be 0-255)")
                except ValueError:
                    validation_errors.append(f"Invalid ICMP code: {icmp_code_elem.text} (must be a number)")
        else:
            validation_errors.append(f"Unsupported protocol: {protocol}")
    
    def _validate_service_group(
        self,
        group_element: etree._Element,
        group_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate a service group object."""
        
        # Check for members
        members_elem = find_element(group_element, './members')
        if not members_elem:
            validation_errors.append(f"Service group missing members element")
            return
            
        members = find_elements(members_elem, './member')
        if not members:
            validation_errors.append(f"Service group has no members")
            
        for member in members:
            if not member.text or member.text.strip() == "":
                validation_errors.append(f"Empty member in service group")
    
    def _validate_tag(
        self,
        tag_element: etree._Element,
        tag_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate a tag object."""
        
        # Tags don't have many constraints
        # Check for color (optional)
        color_elem = find_element(tag_element, './color')
        if color_elem is not None and color_elem.text:
            try:
                color_value = int(color_elem.text)
                if color_value < 1 or color_value > 32:  # PAN-OS typically has 1-32 colors
                    validation_errors.append(f"Invalid color value: {color_value} (must be 1-32)")
            except ValueError:
                # In newer versions, color can also be a named color
                valid_color_names = [
                    "red", "green", "blue", "yellow", "copper", "orange", "purple",
                    "gray", "light-green", "cyan", "light-gray", "blue-gray", "lime",
                    "black", "gold", "brown", "olive", "maroon", "red-orange", "yellow-orange",
                    "forest-green", "turquoise-blue", "azure-blue", "cerulean-blue",
                    "midnight-blue", "medium-blue", "cobalt-blue", "violet-blue",
                    "blue-violet", "medium-violet", "medium-rose", "lavender",
                    "orchid", "thistle", "plum", "raspberry", "crimson", "rose", "magenta"
                ]
                
                if color_elem.text.lower() not in valid_color_names:
                    validation_errors.append(f"Invalid color name: {color_elem.text}")
    
    def _validate_edl(
        self,
        edl_element: etree._Element,
        edl_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate an external dynamic list object."""
        
        # Check for required type
        type_elem = find_element(edl_element, './type')
        if not type_elem or not type_elem.text:
            validation_errors.append(f"EDL missing type element")
            return
            
        edl_type = type_elem.text
        valid_types = ["ip", "domain", "url", "predefined-ip", "predefined-url"]
        if edl_type not in valid_types:
            validation_errors.append(f"Invalid EDL type: {edl_type} (must be one of {', '.join(valid_types)})")
            
        # Check for source URL (for non-predefined types)
        if edl_type in ["ip", "domain", "url"]:
            url_elem = find_element(edl_element, './url')
            if not url_elem or not url_elem.text:
                validation_errors.append(f"EDL missing URL for type '{edl_type}'")
            elif url_elem.text:
                # Very basic URL validation
                if not url_elem.text.startswith(("http://", "https://", "s3://")):
                    validation_errors.append(f"Invalid EDL URL format: {url_elem.text}")
                    
        # Check recurring settings if present
        recurring_elem = find_element(edl_element, './recurring')
        if recurring_elem is not None:
            # Validate recurring interval
            interval_elem = find_element(recurring_elem, './daily')
            interval_elem = interval_elem or find_element(recurring_elem, './weekly')
            interval_elem = interval_elem or find_element(recurring_elem, './monthly')
            interval_elem = interval_elem or find_element(recurring_elem, './hourly')
            interval_elem = interval_elem or find_element(recurring_elem, './five-minute')
            
            if not interval_elem:
                validation_errors.append(f"EDL recurring schedule missing interval type")
    
    def _validate_schedule(
        self,
        schedule_element: etree._Element,
        schedule_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate a schedule object."""
        
        # Check for either recurring or non-recurring type
        recurring_elem = find_element(schedule_element, './recurring')
        non_recurring_elem = find_element(schedule_element, './non-recurring')
        
        if not recurring_elem and not non_recurring_elem:
            validation_errors.append(f"Schedule must be either recurring or non-recurring")
            return
            
        if recurring_elem and non_recurring_elem:
            validation_errors.append(f"Schedule cannot be both recurring and non-recurring")
            
        # Validate non-recurring schedule
        if non_recurring_elem:
            start_elem = find_element(non_recurring_elem, './start')
            end_elem = find_element(non_recurring_elem, './end')
            
            if not start_elem or not start_elem.text:
                validation_errors.append(f"Non-recurring schedule missing start date")
                
            if not end_elem or not end_elem.text:
                validation_errors.append(f"Non-recurring schedule missing end date")
                
            # Validate date format and range
            if start_elem and start_elem.text and end_elem and end_elem.text:
                try:
                    start_date = datetime.strptime(start_elem.text, '%Y/%m/%d %H:%M:%S')
                    end_date = datetime.strptime(end_elem.text, '%Y/%m/%d %H:%M:%S')
                    
                    if start_date >= end_date:
                        validation_errors.append(f"Schedule end date must be after start date")
                        
                except ValueError:
                    validation_errors.append(f"Invalid date format (must be YYYY/MM/DD HH:MM:SS)")
        
        # Validate recurring schedule
        if recurring_elem:
            # Validate at least one day is selected
            days = []
            day_elems = find_elements(recurring_elem, './daily/member')
            for day_elem in day_elems:
                if day_elem.text:
                    days.append(day_elem.text)
                    
            if not days:
                validation_errors.append(f"Recurring schedule must have at least one day selected")
                
            # Validate time range
            start_time_elem = find_element(recurring_elem, './start-time')
            end_time_elem = find_element(recurring_elem, './end-time')
            
            if not start_time_elem or not start_time_elem.text:
                validation_errors.append(f"Recurring schedule missing start time")
                
            if not end_time_elem or not end_time_elem.text:
                validation_errors.append(f"Recurring schedule missing end time")
                
            # Validate time format
            if start_time_elem and start_time_elem.text and end_time_elem and end_time_elem.text:
                try:
                    start_time = datetime.strptime(start_time_elem.text, '%H:%M:%S')
                    end_time = datetime.strptime(end_time_elem.text, '%H:%M:%S')
                    
                    if start_time == end_time:
                        validation_errors.append(f"Schedule start time and end time cannot be the same")
                        
                except ValueError:
                    validation_errors.append(f"Invalid time format (must be HH:MM:SS)")
    
    def _validate_security_profile_group(
        self,
        profile_group_element: etree._Element,
        profile_group_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate a security profile group object."""
        
        # Define profile reference elements to check
        profile_refs = [
            "virus", "spyware", "vulnerability", "url-filtering",
            "file-blocking", "wildfire-analysis", "data-filtering",
            "dns-security"
        ]
        
        # Check if at least one profile is specified
        has_profile = False
        for ref_name in profile_refs:
            profile_ref = find_element(profile_group_element, f'./{ref_name}')
            if profile_ref is not None and profile_ref.text:
                has_profile = True
                break
        
        if not has_profile:
            validation_errors.append(f"Security profile group does not reference any security profiles")
    
    def _validate_antivirus_profile(
        self,
        profile_element: etree._Element,
        profile_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate an antivirus profile object."""
        
        # Check for decoder elements
        decoder_elements = find_elements(profile_element, './decoder')
        if not decoder_elements:
            validation_errors.append(f"Antivirus profile missing decoder configuration")
        
        # Check for invalid application exceptions
        app_exceptions = find_elements(profile_element, './/application-exception/entry')
        for app_exception in app_exceptions:
            app_name = app_exception.get("name")
            if not app_name or app_name.strip() == "":
                validation_errors.append(f"Antivirus profile has an application exception with empty application name")
    
    def _validate_antispyware_profile(
        self,
        profile_element: etree._Element,
        profile_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate an anti-spyware profile object."""
        
        # Check for rules
        rules = find_elements(profile_element, './rules/entry')
        if not rules:
            validation_errors.append(f"Anti-spyware profile has no rules defined")
    
    def _validate_vulnerability_profile(
        self,
        profile_element: etree._Element,
        profile_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate a vulnerability profile object."""
        
        # Check for rules
        rules = find_elements(profile_element, './rules/entry')
        if not rules:
            validation_errors.append(f"Vulnerability profile has no rules defined")
    
    def _validate_url_filtering_profile(
        self,
        profile_element: etree._Element,
        profile_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate a URL filtering profile object."""
        
        # Check for category actions (at least one category should be defined)
        action_elements = ['block', 'alert', 'allow', 'continue', 'override']
        has_categories = False
        
        for action in action_elements:
            categories = find_elements(profile_element, f'./{action}/member')
            if categories:
                has_categories = True
                break
        
        if not has_categories:
            validation_errors.append(f"URL filtering profile doesn't define any category actions")
    
    def _validate_file_blocking_profile(
        self,
        profile_element: etree._Element,
        profile_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate a file blocking profile object."""
        
        # Check for rules
        rules = find_elements(profile_element, './rules/entry')
        if not rules:
            validation_errors.append(f"File blocking profile has no rules defined")
    
    def _validate_wildfire_profile(
        self,
        profile_element: etree._Element,
        profile_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate a WildFire analysis profile object."""
        
        # Check for rules
        rules = find_elements(profile_element, './rules/entry')
        if not rules:
            validation_errors.append(f"WildFire analysis profile has no rules defined")
    
    def _validate_dns_security_profile(
        self,
        profile_element: etree._Element,
        profile_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate a DNS security profile object."""
        
        # No specific validation requirements for DNS security profiles
        # This method is included for completeness and future extensibility
        
    def _validate_custom_url_category(
        self,
        category_element: etree._Element,
        category_name: str,
        validation_errors: List[str]
    ) -> None:
        """Validate a custom URL category object."""
        
        # Check for type element
        type_elem = find_element(category_element, './type')
        if type_elem is None or not type_elem.text:
            validation_errors.append(f"Custom URL category missing required type element")
        elif type_elem.text not in ["URL List", "Category Match"]:
            validation_errors.append(f"Invalid custom URL category type: {type_elem.text}")
            
        # For URL List type, check that it has a valid list
        if type_elem is not None and type_elem.text == "URL List":
            list_elem = find_element(category_element, './list')
            if list_elem is None:
                validation_errors.append(f"URL List custom category missing list element")
            else:
                # Check if it has members or external-list references
                members = find_elements(list_elem, './member')
                external_lists = find_elements(list_elem, './external-list')
                
                if not members and not external_lists:
                    validation_errors.append(f"URL List custom category has empty list (no members or external lists)")
                    
                # Check for malformed URLs in members
                for member in members:
                    if member.text:
                        url = member.text.strip()
                        
                        # Basic URL validation - could be enhanced in the future
                        if not url.startswith(("http://", "https://", "ftp://")) and not "." in url:
                            validation_errors.append(f"Potentially invalid URL format in member: {url}")
                            
        # For Category Match type, check that it has valid categories
        if type_elem is not None and type_elem.text == "Category Match":
            category_elem = find_element(category_element, './category')
            if category_elem is None:
                validation_errors.append(f"Category Match custom category missing category element")
            else:
                categories = find_elements(category_elem, './member')
                if not categories:
                    validation_errors.append(f"Category Match custom category has no category members")
    
    def _validate_generic_object(
        self,
        object_element: etree._Element,
        object_name: str,
        object_type: str,
        validation_errors: List[str]
    ) -> None:
        """Generic validation for object types without specific validation rules."""
        
        # Check for empty element
        if len(object_element) == 0:
            validation_errors.append(f"Object has no elements")
            return
            
        # Check for name attribute
        if not object_name or object_name == "unknown":
            validation_errors.append(f"Object has missing or invalid name attribute")
    
    def _is_valid_ip_netmask(self, value: str) -> bool:
        """Validate IP netmask format (e.g., 192.168.1.0/24)."""
        try:
            # Handle special cases
            if value == "0.0.0.0/0":
                return True
                
            # Validate as CIDR
            ipaddress.ip_network(value, strict=False)
            return True
        except ValueError:
            return False
    
    def _is_valid_ip_range(self, value: str) -> bool:
        """Validate IP range format (e.g., 192.168.1.1-192.168.1.10)."""
        try:
            parts = value.split('-')
            if len(parts) != 2:
                return False
                
            # Validate start and end IPs
            start_ip = ipaddress.ip_address(parts[0])
            end_ip = ipaddress.ip_address(parts[1])
            
            # Ensure start is less than or equal to end
            return start_ip <= end_ip
        except ValueError:
            return False
    
    def _is_valid_fqdn(self, value: str) -> bool:
        """Validate FQDN format."""
        # Basic FQDN validation - more comprehensive validation possible
        if not value:
            return False
            
        # Wildcard format
        if value.startswith('*.'):
            value = value[2:]
            
        parts = value.split('.')
        if len(parts) < 2:
            return False
            
        for part in parts:
            if not part or not re.match(r'^[a-zA-Z0-9-]+$', part):
                return False
                
        # Last part should be a TLD
        return re.match(r'^[a-zA-Z]{2,}$', parts[-1])
    
    def _is_valid_ip_wildcard(self, value: str) -> bool:
        """Validate IP wildcard format (e.g., 10.0.0.0/8.*)."""
        # Basic validation for wildcard format
        parts = value.split('/')
        if len(parts) != 2:
            return False
            
        # Check if the base part is a valid IP
        try:
            ipaddress.ip_address(parts[0])
        except ValueError:
            return False
            
        # Check wildcard part
        mask_part = parts[1]
        return re.match(r'^[0-9]+(\.[*])*$', mask_part)
    
    def _is_valid_port_range(self, value: str) -> bool:
        """Validate port range format (e.g., 80, 1-1024, etc.)."""
        try:
            parts = value.split('-')
            
            if len(parts) == 1:
                # Single port
                port = int(parts[0])
                return 0 <= port <= 65535
            elif len(parts) == 2:
                # Port range
                start_port = int(parts[0])
                end_port = int(parts[1])
                return 0 <= start_port <= end_port <= 65535
            else:
                return False
        except ValueError:
            return False
    
    def _is_valid_dynamic_filter(self, filter_text: str) -> bool:
        """
        Validate dynamic filter expression syntax.
        
        This is a basic validation that checks for common issues:
        - Balanced quotes
        - Valid operators (and, or, not)
        - Basic syntax structure
        """
        # Check for balanced quotes
        single_quotes = filter_text.count("'")
        double_quotes = filter_text.count('"')
        
        if single_quotes % 2 != 0 or double_quotes % 2 != 0:
            return False
            
        # Check for valid operators
        operators = ['and', 'or', 'not']
        tokens = re.findall(r'[a-zA-Z0-9_-]+', filter_text)
        
        # Remove quoted sections to avoid confusing tag names with operators
        clean_text = re.sub(r'[\'"][^\'"]*[\'"]', '', filter_text)
        
        # Check remaining tokens
        remaining_tokens = re.findall(r'[a-zA-Z0-9_-]+', clean_text)
        
        for token in remaining_tokens:
            if token not in operators and not token.startswith('tag.'):
                # Found unexpected token
                return False
                
        return True
        
    def analyze_dependencies(
        self,
        object_type: str,
        object_name: str,
        context_type: str,
        include_policies: bool = False,
        **kwargs
    ) -> Dict[str, List[Tuple[str, str]]]:
        """
        Analyze all dependencies for a given object.
        
        This method performs a comprehensive dependency analysis for an object,
        identifying all other objects that depend on it, as well as objects that 
        it depends on (references).
        
        Args:
            object_type: Type of object (address, service, etc.)
            object_name: Name of the object to analyze
            context_type: Type of context (shared, device_group, vsys)
            include_policies: Whether to include policy references
            **kwargs: Additional parameters (device_group, vsys, etc.)
            
        Returns:
            Dict: Dictionary with keys 'depends_on' and 'referenced_by', each containing
                  a list of tuples (object_type, object_name)
        """
        logger.info(f"Analyzing dependencies for {object_type} '{object_name}' in {context_type}")
        
        result = {
            "depends_on": [],      # Objects that this object references
            "referenced_by": []    # Objects that reference this object
        }
        
        # Get the object
        try:
            context_params = self._extract_context_params(context_type, kwargs)
            
            object_xpath = get_object_xpath(
                object_type, 
                self.source_device_type, 
                context_type, 
                self.source_version, 
                object_name, 
                **context_params
            )
            
            logger.debug(f"Looking for object using XPath: {object_xpath}")
            object_elements = xpath_search(self.source_tree, object_xpath)
            
            if not object_elements:
                logger.warning(f"Object '{object_name}' not found in {context_type}")
                return result
                
            object_element = object_elements[0]
            logger.debug(f"Found object: {object_type} '{object_name}'")
            
        except Exception as e:
            logger.error(f"Error retrieving object '{object_name}': {e}", exc_info=True)
            return result
            
        # Analyze what this object depends on
        if object_type in ["address_group", "address-group"]:
            self._analyze_address_group_dependencies(object_element, object_name, result)
        elif object_type in ["service_group", "service-group"]:
            self._analyze_service_group_dependencies(object_element, object_name, result)
        elif object_type in ["application_group", "application-group"]:
            self._analyze_application_group_dependencies(object_element, object_name, result)
        elif object_type in ["security_profile_group", "profile_group", "profile-group", "security-profile-group"]:
            self._analyze_profile_group_dependencies(object_element, object_name, result)
            
        # Find objects that reference this object
        self._find_object_references(object_type, object_name, context_type, result, include_policies, **kwargs)
        
        # Log summary
        logger.info(f"Dependency analysis results for {object_type} '{object_name}':")
        logger.info(f"  - Depends on: {len(result['depends_on'])} objects")
        logger.info(f"  - Referenced by: {len(result['referenced_by'])} objects")
        
        return result
        
    def _analyze_address_group_dependencies(
        self, 
        group_element: etree._Element, 
        group_name: str, 
        result: Dict[str, List[Tuple[str, str]]]
    ) -> None:
        """Find all dependencies of an address group."""
        logger.debug(f"Analyzing dependencies for address group '{group_name}'")
        
        # Check static members
        static_members = find_elements(group_element, './static/member')
        for member in static_members:
            if member.text:
                logger.debug(f"Found static member reference: {member.text}")
                # It could be an address or another address group
                result["depends_on"].append(("address", member.text))
                result["depends_on"].append(("address_group", member.text))
                
        # Check dynamic filter for tag references
        filter_element = find_element(group_element, './dynamic/filter')
        if filter_element is not None and filter_element.text:
            logger.debug(f"Found dynamic filter: {filter_element.text}")
            # Extract tags from filter string
            tag_refs = self._extract_tags_from_filter(filter_element.text)
            for tag in tag_refs:
                logger.debug(f"Found tag reference in filter: {tag}")
                result["depends_on"].append(("tag", tag))
                
    def _analyze_service_group_dependencies(
        self, 
        group_element: etree._Element, 
        group_name: str, 
        result: Dict[str, List[Tuple[str, str]]]
    ) -> None:
        """Find all dependencies of a service group."""
        logger.debug(f"Analyzing dependencies for service group '{group_name}'")
        
        # Check members
        members = find_elements(group_element, './members/member')
        for member in members:
            if member.text:
                logger.debug(f"Found member reference: {member.text}")
                # It could be a service or another service group
                result["depends_on"].append(("service", member.text))
                result["depends_on"].append(("service_group", member.text))
                
    def _analyze_application_group_dependencies(
        self, 
        group_element: etree._Element, 
        group_name: str, 
        result: Dict[str, List[Tuple[str, str]]]
    ) -> None:
        """Find all dependencies of an application group."""
        logger.debug(f"Analyzing dependencies for application group '{group_name}'")
        
        # Check members
        members = find_elements(group_element, './members/member')
        for member in members:
            if member.text:
                logger.debug(f"Found member reference: {member.text}")
                # It could be an application or another application group
                result["depends_on"].append(("application", member.text))
                result["depends_on"].append(("application_group", member.text))
                
    def _analyze_profile_group_dependencies(
        self, 
        group_element: etree._Element, 
        group_name: str, 
        result: Dict[str, List[Tuple[str, str]]]
    ) -> None:
        """Find all dependencies of a security profile group."""
        logger.debug(f"Analyzing dependencies for profile group '{group_name}'")
        
        # Check all profile types
        profile_types = [
            ("virus", "av-profile"),
            ("spyware", "as-profile"),
            ("vulnerability", "vp-profile"),
            ("url-filtering", "url_filtering_profile"),
            ("file-blocking", "file_blocking_profile"),
            ("wildfire-analysis", "wf-profile"),
            ("data-filtering", "data_filtering_profile"),
            ("dns-security", "dnssec_profile")
        ]
        
        for xml_type, object_type in profile_types:
            profile_refs = find_elements(group_element, f'./{xml_type}/member')
            for profile_ref in profile_refs:
                if profile_ref.text:
                    logger.debug(f"Found {object_type} reference: {profile_ref.text}")
                    result["depends_on"].append((object_type, profile_ref.text))
                    
    def _find_object_references(
        self,
        object_type: str,
        object_name: str,
        context_type: str,
        result: Dict[str, List[Tuple[str, str]]],
        include_policies: bool = False,
        **kwargs
    ) -> None:
        """Find all objects that reference this object."""
        logger.debug(f"Finding references to {object_type} '{object_name}'")
        
        # Determine what objects might reference this type of object
        referencing_objects = []
        
        if object_type in ["address", "address-object"]:
            referencing_objects = [
                ("address_group", "./static/member"),
                # Security rules can also reference addresses, but handled separately if include_policies
            ]
        elif object_type in ["service", "service-object"]:
            referencing_objects = [
                ("service_group", "./members/member"),
                # Security rules can also reference services, but handled separately if include_policies
            ]
        elif object_type in ["tag"]:
            referencing_objects = [
                ("address", "./tag/member"),
                ("address_group", "./tag/member"),
                ("service", "./tag/member"),
                # Many other object types can have tags, but these are the most common
            ]
            
            # For tags, also check dynamic address groups
            self._find_tag_in_dynamic_filters(object_name, result)
            
        elif object_type in ["application", "application-object"]:
            referencing_objects = [
                ("application_group", "./members/member"),
                # Security rules can also reference applications, but handled separately if include_policies
            ]
            
        # Find references in objects
        for ref_type, xpath_pattern in referencing_objects:
            self._find_references_in_objects(ref_type, xpath_pattern, object_name, context_type, result, **kwargs)
            
        # Include policy references if requested
        if include_policies:
            self._find_policy_references(object_type, object_name, context_type, result, **kwargs)
            
    def _find_references_in_objects(
        self,
        ref_object_type: str,
        xpath_pattern: str,
        object_name: str,
        context_type: str,
        result: Dict[str, List[Tuple[str, str]]],
        **kwargs
    ) -> None:
        """Find references to an object in other objects of a specific type."""
        logger.debug(f"Looking for references to '{object_name}' in {ref_object_type} objects")
        
        try:
            context_params = self._extract_context_params(context_type, kwargs)
            
            # Get the base path for this type of object
            ref_base_xpath = get_object_xpath(
                ref_object_type, 
                self.source_device_type, 
                context_type, 
                self.source_version, 
                **context_params
            )
            
            # Split to get parent path
            parent_parts = ref_base_xpath.rsplit('/', 1)
            if len(parent_parts) < 2:
                logger.warning(f"Invalid reference base path: {ref_base_xpath}")
                return
                
            ref_base_xpath = parent_parts[0]
            logger.debug(f"Base XPath for references: {ref_base_xpath}/entry")
            
            # Find all objects of this type
            ref_objects = xpath_search(self.source_tree, f"{ref_base_xpath}/entry")
            
            if not ref_objects:
                logger.debug(f"No {ref_object_type} objects found in {context_type}")
                return
                
            logger.debug(f"Found {len(ref_objects)} {ref_object_type} objects to check")
            
            for ref_obj in ref_objects:
                ref_name = ref_obj.get("name", "unknown")
                
                # Look for references using the specified XPath pattern
                ref_elements = find_elements(ref_obj, xpath_pattern)
                
                for ref_elem in ref_elements:
                    if ref_elem.text == object_name:
                        logger.debug(f"Found reference in {ref_object_type} '{ref_name}'")
                        result["referenced_by"].append((ref_object_type, ref_name))
                        
        except Exception as e:
            logger.warning(f"Error finding references in {ref_object_type} objects: {e}", exc_info=True)
            
    def _find_tag_in_dynamic_filters(
        self,
        tag_name: str,
        result: Dict[str, List[Tuple[str, str]]]
    ) -> None:
        """Find dynamic address groups that reference a tag in their filters."""
        logger.debug(f"Looking for tag '{tag_name}' in dynamic address group filters")
        
        try:
            # This is a more complex search that requires looking at all dynamic address groups
            # across all contexts (shared, device groups, vsys)
            
            # Check shared context first
            shared_xpath = "/config/shared/address-group/entry/dynamic/filter"
            self._check_filters_for_tag(shared_xpath, tag_name, "shared", result)
            
            # Check device groups if Panorama
            if self.source_device_type == "panorama":
                dg_xpath = "/config/devices/entry[@name='localhost.localdomain']/device-group/entry"
                device_groups = xpath_search(self.source_tree, dg_xpath)
                
                for dg in device_groups:
                    dg_name = dg.get("name", "unknown")
                    filter_xpath = f"{dg_xpath}[@name='{dg_name}']/address-group/entry/dynamic/filter"
                    self._check_filters_for_tag(filter_xpath, tag_name, f"device_group {dg_name}", result)
            
            # Check vsys if firewall
            if self.source_device_type == "firewall":
                vsys_xpath = "/config/devices/entry[@name='localhost.localdomain']/vsys/entry"
                vsys_entries = xpath_search(self.source_tree, vsys_xpath)
                
                for vsys in vsys_entries:
                    vsys_name = vsys.get("name", "unknown")
                    filter_xpath = f"{vsys_xpath}[@name='{vsys_name}']/address-group/entry/dynamic/filter"
                    self._check_filters_for_tag(filter_xpath, tag_name, f"vsys {vsys_name}", result)
                    
        except Exception as e:
            logger.warning(f"Error finding tag references in dynamic filters: {e}", exc_info=True)
            
    def _check_filters_for_tag(
        self,
        filter_xpath: str,
        tag_name: str,
        context_desc: str,
        result: Dict[str, List[Tuple[str, str]]]
    ) -> None:
        """Check dynamic address group filters for references to a specific tag."""
        try:
            filter_elements = xpath_search(self.source_tree, filter_xpath)
            
            if not filter_elements:
                logger.debug(f"No dynamic filters found in {context_desc}")
                return
                
            logger.debug(f"Found {len(filter_elements)} filters to check in {context_desc}")
            
            for filter_elem in filter_elements:
                if filter_elem.text and tag_name in filter_elem.text:
                    # Extract the address group name
                    parent_entry = filter_elem.getparent().getparent()
                    if parent_entry is not None and parent_entry.tag == "entry":
                        group_name = parent_entry.get("name", "unknown")
                        
                        # Make sure it's actually a reference to this tag by checking quotes
                        # e.g. "tag1" should not match "tag10"
                        filter_text = filter_elem.text
                        tag_pattern = fr"'({tag_name})'|\"({tag_name})\""
                        if re.search(tag_pattern, filter_text):
                            logger.debug(f"Found tag reference in address group '{group_name}' filter")
                            result["referenced_by"].append(("address_group", group_name))
                            
        except Exception as e:
            logger.warning(f"Error checking filters in {context_desc}: {e}", exc_info=True)
            
    def _extract_tags_from_filter(self, filter_text: str) -> List[str]:
        """Extract tags referenced in a dynamic address group filter."""
        if not filter_text:
            return []
            
        # Find all quoted strings, which are presumably tag names
        # e.g. "tag1 or tag2" or "tag1 and 'tag2'"
        tag_pattern = r"'([^']+)'|\"([^\"]+)\""
        tag_matches = re.findall(tag_pattern, filter_text)
        
        # Flatten the matches
        tags = [m[0] or m[1] for m in tag_matches]
        
        logger.debug(f"Extracted {len(tags)} tags from filter: {tags}")
        return tags
        
    def validate_object(
        self,
        object_element: etree._Element,
        object_type: str,
        **kwargs
    ) -> Tuple[bool, List[str]]:
        """
        Validate an object for correctness and integrity.
        
        This method uses the ObjectValidator to check the object against known
        constraints and requirements for the object type.
        
        Args:
            object_element: The XML element of the object to validate
            object_type: The type of object (address, service, etc.)
            **kwargs: Additional validation parameters
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list of validation error messages)
        """
        return self.validator.validate_object(object_element, object_type, **kwargs)
        
    def _find_policy_references(
        self,
        object_type: str,
        object_name: str,
        context_type: str,
        result: Dict[str, List[Tuple[str, str]]],
        **kwargs
    ) -> None:
        """Find references to an object in policies (security rules, NAT, etc.)."""
        logger.debug(f"Looking for references to {object_type} '{object_name}' in policies")
        
        # Map object types to the XPath patterns to check in rules
        policy_ref_map = {
            "address": ["./source/member", "./destination/member"],
            "address-group": ["./source/member", "./destination/member"],
            "service": ["./service/member"],
            "service-group": ["./service/member"],
            "application": ["./application/member"],
            "application-group": ["./application/member"],
            "tag": ["./tag/member"],
            "security_profile_group": ["./profile-setting/group/member"],
            "schedule": ["./schedule"],
            "url-category": ["./category/member"]
        }
        
        # If this object type is not referenceable in rules, skip
        normalized_type = object_type.replace("_", "-")
        if normalized_type not in policy_ref_map:
            logger.debug(f"Object type {normalized_type} not directly referenceable in policies")
            return
            
        xpath_patterns = policy_ref_map[normalized_type]
        
        # Determine which rule types to check
        rule_types = []
        
        if self.source_device_type == "panorama":
            if context_type == "device_group":
                # Check pre-rulebase and post-rulebase for device groups
                device_group = kwargs.get("device_group", "")
                if not device_group:
                    logger.warning("Missing device_group parameter for policy reference check")
                    return
                    
                dg_xpath = f"/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='{device_group}']"
                
                # Different rule bases to check
                rule_types = [
                    (f"{dg_xpath}/pre-rulebase/security/rules/entry", "pre-security rule"),
                    (f"{dg_xpath}/post-rulebase/security/rules/entry", "post-security rule"),
                    (f"{dg_xpath}/pre-rulebase/nat/rules/entry", "pre-NAT rule"),
                    (f"{dg_xpath}/post-rulebase/nat/rules/entry", "post-NAT rule"),
                    (f"{dg_xpath}/pre-rulebase/pbf/rules/entry", "pre-PBF rule"),
                    (f"{dg_xpath}/post-rulebase/pbf/rules/entry", "post-PBF rule"),
                    (f"{dg_xpath}/pre-rulebase/decryption/rules/entry", "pre-Decryption rule"),
                    (f"{dg_xpath}/post-rulebase/decryption/rules/entry", "post-Decryption rule")
                ]
                
        elif self.source_device_type == "firewall":
            if context_type == "vsys":
                # Check rulebase for vsys
                vsys = kwargs.get("vsys", "")
                if not vsys:
                    logger.warning("Missing vsys parameter for policy reference check")
                    return
                    
                vsys_xpath = f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{vsys}']"
                
                rule_types = [
                    (f"{vsys_xpath}/rulebase/security/rules/entry", "security rule"),
                    (f"{vsys_xpath}/rulebase/nat/rules/entry", "NAT rule"),
                    (f"{vsys_xpath}/rulebase/pbf/rules/entry", "PBF rule"),
                    (f"{vsys_xpath}/rulebase/decryption/rules/entry", "Decryption rule")
                ]
                
        # Check each rule type for references
        for rule_xpath, rule_desc in rule_types:
            try:
                rules = xpath_search(self.source_tree, rule_xpath)
                
                if not rules:
                    logger.debug(f"No {rule_desc} rules found")
                    continue
                    
                logger.debug(f"Found {len(rules)} {rule_desc} rules to check")
                
                for rule in rules:
                    rule_name = rule.get("name", "unknown")
                    found_reference = False
                    
                    for pattern in xpath_patterns:
                        ref_elements = find_elements(rule, pattern)
                        
                        for ref_elem in ref_elements:
                            if ref_elem.text and ref_elem.text == object_name:
                                logger.debug(f"Found reference in {rule_desc} '{rule_name}'")
                                result["referenced_by"].append((rule_desc, rule_name))
                                found_reference = True
                                break
                                
                        if found_reference:
                            break
                            
            except Exception as e:
                logger.warning(f"Error checking {rule_desc} rules: {e}", exc_info=True)