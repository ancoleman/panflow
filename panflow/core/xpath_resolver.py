"""
XPath resolver for PANFlow.

This module provides functions to load and resolve XPath expressions for different
PAN-OS versions, ensuring that the correct XPath is used for each version.
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, Tuple, List

# Package constants
DEFAULT_VERSION = "11.2"  # Newest version as default
XPATH_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "xpath_mappings")

# Initialize logger
logger = logging.getLogger("panflow")

# Cache for loaded XPath mappings
_xpath_cache: Dict[str, Dict[str, Any]] = {}

def load_xpath_mappings(version: str) -> Dict[str, Any]:
    """
    Load XPath mappings for a specific PAN-OS version.
    
    Args:
        version: PAN-OS version (e.g., "10.1", "11.0")
        
    Returns:
        Dictionary of XPath mappings
    
    Raises:
        ValueError: If the mapping file cannot be found or loaded
    """
    logger.debug(f"Loading XPath mappings for PAN-OS version {version}")
    
    # Return cached mappings if available
    if version in _xpath_cache:
        logger.debug(f"Using cached XPath mappings for version {version}")
        return _xpath_cache[version]
        
    # Normalize version format
    normalized_version = version.replace(".", "_")
    
    # Look for exact version mapping file
    file_path = os.path.join(XPATH_DIR, f"panos_{normalized_version}.yaml")
    
    if not os.path.exists(file_path):
        # If exact version not found, use the default
        if version != DEFAULT_VERSION:
            logger.debug(f"XPath mapping file not found for PAN-OS version {version}, using default version {DEFAULT_VERSION}")
        version = DEFAULT_VERSION
        normalized_version = version.replace(".", "_")
        file_path = os.path.join(XPATH_DIR, f"panos_{normalized_version}.yaml")
        
        if not os.path.exists(file_path):
            error_msg = f"XPath mapping file not found for PAN-OS version {version}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    # Load YAML file
    try:
        logger.debug(f"Reading XPath mappings from file: {file_path}")
        with open(file_path, 'r') as f:
            mappings = yaml.safe_load(f)
        
        logger.debug(f"Successfully loaded XPath mappings for PAN-OS version {version}")
        
        # Cache the mappings
        _xpath_cache[version] = mappings
        logger.debug(f"Cached XPath mappings for version {version}")
        
        return mappings
    except yaml.YAMLError as e:
        error_msg = f"Error parsing YAML in XPath mapping file for version {version}: {e}"
        logger.error(error_msg, exc_info=True)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error loading XPath mappings for version {version}: {e}"
        logger.error(error_msg, exc_info=True)
        raise ValueError(error_msg)

def get_context_xpath(
    device_type: str,
    context_type: str,
    version: str = DEFAULT_VERSION,
    **kwargs
) -> str:
    """
    Get the base XPath for a specific context.
    
    Args:
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, template, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, template, vsys)
            
    Returns:
        str: Base XPath for the context
        
    Raises:
        ValueError: If the device type or context type is invalid
    """
    logger.debug(f"Getting context XPath for {device_type}/{context_type} (version {version})")
    
    # Load XPath mappings for the specified version
    try:
        mappings = load_xpath_mappings(version)
    except ValueError as e:
        logger.error(f"Failed to load XPath mappings: {e}")
        raise
    
    # Get context mappings for the device type
    device_type_lower = device_type.lower()
    if device_type_lower not in mappings["contexts"]:
        error_msg = f"Invalid device type: {device_type}"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    contexts = mappings["contexts"][device_type_lower]
    
    # Get the XPath template for the context type
    if context_type not in contexts:
        error_msg = f"Invalid context type for {device_type}: {context_type}"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    xpath_template = contexts[context_type]
    
    # Format the XPath with the provided parameters
    try:
        if context_type == "device_group" and "device_group" in kwargs:
            device_group = kwargs["device_group"]
            xpath = xpath_template.format(device_group=device_group)
            logger.debug(f"Generated context XPath for {device_type}/{context_type} (device_group={device_group}): {xpath}")
            return xpath
        elif context_type == "template" and "template" in kwargs:
            template = kwargs["template"]
            xpath = xpath_template.format(template=template)
            logger.debug(f"Generated context XPath for {device_type}/{context_type} (template={template}): {xpath}")
            return xpath
        elif context_type == "vsys":
            vsys = kwargs.get("vsys", "vsys1")
            xpath = xpath_template.format(vsys=vsys)
            logger.debug(f"Generated context XPath for {device_type}/{context_type} (vsys={vsys}): {xpath}")
            return xpath
        else:
            logger.debug(f"Generated context XPath for {device_type}/{context_type}: {xpath_template}")
            return xpath_template
    except KeyError as e:
        error_msg = f"Missing required parameter for {context_type} context: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Error generating context XPath: {e}"
        logger.error(error_msg, exc_info=True)
        raise ValueError(error_msg)

def get_object_xpath(
    object_type: str,
    device_type: str,
    context_type: str,
    version: str = DEFAULT_VERSION,
    name: Optional[str] = None,
    **kwargs
) -> str:
    """
    Get the XPath for a specific object type in a specific context.
    
    Args:
        object_type: Type of object (address, service, etc.)
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        name: Name of the object (optional)
        **kwargs: Additional parameters (device_group, vsys)
            
    Returns:
        str: XPath for the object type
        
    Raises:
        ValueError: If the object type is invalid
    """
    logger.debug(f"Getting object XPath for {object_type} in {device_type}/{context_type} (version {version})")
    
    # Load XPath mappings for the specified version
    try:
        mappings = load_xpath_mappings(version)
    except ValueError as e:
        logger.error(f"Failed to load XPath mappings: {e}")
        raise
    
    # Get the base context path
    try:
        base_path = get_context_xpath(device_type, context_type, version, **kwargs)
    except ValueError as e:
        logger.error(f"Failed to get context XPath: {e}")
        raise
    
    # Get the object XPath template
    if object_type not in mappings["objects"]:
        # Check version-specific overrides
        if ("version_specific" in mappings and
            device_type.lower() in mappings["version_specific"] and
            object_type in mappings["version_specific"][device_type.lower()]):
            
            xpath_template = mappings["version_specific"][device_type.lower()][object_type]
            logger.debug(f"Using version-specific XPath for {object_type}")
            
            # If it's a full path, use it directly
            if xpath_template.startswith("/config"):
                if name:
                    xpath = xpath_template.format(name=name, **kwargs)
                    logger.debug(f"Generated object XPath: {xpath}")
                    return xpath
                else:
                    # Return path to all objects of this type without removing the entry part
                    path = xpath_template.format(name="", **kwargs)
                    # Replace the [@name=''] with just empty brackets or remove it entirely
                    xpath = path.replace("[@name='']", "")
                    logger.debug(f"Generated object XPath: {xpath}")
                    return xpath
        else:
            error_msg = f"Invalid object type: {object_type}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    else:
        xpath_template = mappings["objects"][object_type]

    # Format the XPath with the provided parameters
    try:
        if name:
            xpath = xpath_template.format(base_path=base_path, name=name)
            logger.debug(f"Generated object XPath for {object_type} '{name}': {xpath}")
            return xpath
        else:
            # Return path to all objects of this type without removing the entry part
            path = xpath_template.format(base_path=base_path, name="")
            # Replace the [@name=''] with just empty brackets or remove it entirely
            xpath = path.replace("[@name='']", "")
            logger.debug(f"Generated object XPath for all {object_type} objects: {xpath}")
            return xpath
    except KeyError as e:
        error_msg = f"Missing required parameter for object XPath: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Error generating object XPath: {e}"
        logger.error(error_msg, exc_info=True)
        raise ValueError(error_msg)

def get_policy_xpath(
    policy_type: str,
    device_type: str,
    context_type: str,
    version: str = DEFAULT_VERSION,
    name: Optional[str] = None,
    **kwargs
) -> str:
    """
    Get the XPath for a specific policy type in a specific context.
    
    Args:
        policy_type: Type of policy (security_pre_rules, nat_rules, etc.)
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        name: Name of the policy (optional)
        **kwargs: Additional parameters (device_group, vsys)
            
    Returns:
        str: XPath for the policy type
        
    Raises:
        ValueError: If the policy type is invalid for the device type
    """
    logger.debug(f"Getting policy XPath for {policy_type} in {device_type}/{context_type} (version {version})")
    
    # Load XPath mappings for the specified version
    try:
        mappings = load_xpath_mappings(version)
    except ValueError as e:
        logger.error(f"Failed to load XPath mappings: {e}")
        raise
    
    # Get the base context path
    try:
        base_path = get_context_xpath(device_type, context_type, version, **kwargs)
    except ValueError as e:
        logger.error(f"Failed to get context XPath: {e}")
        raise
    
    # Get policy mappings for the device type
    device_type_lower = device_type.lower()
    if device_type_lower not in mappings["policies"]:
        error_msg = f"Invalid device type for policies: {device_type}"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    policies = mappings["policies"][device_type_lower]
    
    # Convert panorama policy types to firewall types if needed
    if device_type_lower == "firewall":
        if policy_type.startswith("security_"):
            policy_type_key = "security_rules"
        elif policy_type.startswith("nat_"):
            policy_type_key = "nat_rules"
        elif policy_type.startswith("decryption_"):
            policy_type_key = "decryption_rules"
        elif policy_type.startswith("authentication_"):
            policy_type_key = "authentication_rules"
        else:
            policy_type_key = policy_type
    else:
        policy_type_key = policy_type
    
    # Get the policy XPath template
    if policy_type_key not in policies:
        # Check version-specific overrides
        if ("version_specific" in mappings and
            device_type_lower in mappings["version_specific"] and
            policy_type_key in mappings["version_specific"][device_type_lower]):
            
            xpath_template = mappings["version_specific"][device_type_lower][policy_type_key]
            logger.debug(f"Using version-specific XPath for {policy_type}")
            
            # If it's a full path, use it directly
            if xpath_template.startswith("/config"):
                if name:
                    xpath = xpath_template.format(name=name, **kwargs)
                    logger.debug(f"Generated policy XPath: {xpath}")
                    return xpath
                else:
                    # Return path to all policies of this type (remove the [@name=''] part)
                    xpath = xpath_template.format(name="").rsplit("/", 1)[0]
                    logger.debug(f"Generated policy XPath: {xpath}")
                    return xpath
        else:
            error_msg = f"Invalid policy type for {device_type}: {policy_type}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    else:
        xpath_template = policies[policy_type_key]

    # Format the XPath with the provided parameters
    try:
        if name:
            xpath = xpath_template.format(base_path=base_path, name=name)
            logger.debug(f"Generated policy XPath for {policy_type} '{name}': {xpath}")
            return xpath
        else:
            # Return path to all policies of this type (remove the [@name=''] part)
            xpath = xpath_template.format(base_path=base_path, name="").rsplit("/", 1)[0]
            logger.debug(f"Generated policy XPath for all {policy_type} policies: {xpath}")
            return xpath
    except KeyError as e:
        error_msg = f"Missing required parameter for policy XPath: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Error generating policy XPath: {e}"
        logger.error(error_msg, exc_info=True)
        raise ValueError(error_msg)

def get_all_versions() -> List[str]:
    """
    Get all available PAN-OS versions with XPath mappings.
    
    Returns:
        List of available PAN-OS versions
    """
    logger.debug("Getting all available PAN-OS versions")
    versions = []
    
    # Scan the XPath mappings directory
    try:
        for filename in os.listdir(XPATH_DIR):
            if filename.startswith("panos_") and filename.endswith(".yaml"):
                # Extract and normalize version number
                version = filename[6:-5].replace("_", ".")
                versions.append(version)
        
        logger.debug(f"Found {len(versions)} available PAN-OS versions: {', '.join(versions)}")
        return sorted(versions)
    except FileNotFoundError:
        logger.error(f"XPath mappings directory not found: {XPATH_DIR}")
        return [DEFAULT_VERSION]
    except PermissionError:
        logger.error(f"Permission denied when reading XPath mappings directory: {XPATH_DIR}")
        return [DEFAULT_VERSION]
    except Exception as e:
        logger.error(f"Error scanning for available PAN-OS versions: {e}", exc_info=True)
        return [DEFAULT_VERSION]

def determine_version_from_config(config_xml: str) -> str:
    """
    Try to determine the PAN-OS version from a configuration file.
    
    Args:
        config_xml: XML configuration content
        
    Returns:
        PAN-OS version or DEFAULT_VERSION if not found
    """
    logger.debug("Attempting to determine PAN-OS version from configuration")
    
    try:
        from lxml import etree
        
        # Parse the XML content
        if isinstance(config_xml, str):
            root = etree.fromstring(config_xml.encode('utf-8'))
        else:
            root = etree.fromstring(config_xml)
        
        # Look for version attribute in the config element
        version_attr = root.get('version')
        if version_attr:
            # Extract major.minor version (e.g., from "10.2.0" to "10.2")
            parts = version_attr.split('.')
            if len(parts) >= 2:
                version = f"{parts[0]}.{parts[1]}"
                logger.info(f"Detected PAN-OS version {version} from configuration")
                return version
        
        logger.warning(f"Could not determine PAN-OS version from configuration, using default version {DEFAULT_VERSION}")
        return DEFAULT_VERSION
    except etree.XMLSyntaxError as e:
        logger.warning(f"XML syntax error when detecting PAN-OS version: {e}")
        logger.warning(f"Using default version {DEFAULT_VERSION}")
        return DEFAULT_VERSION
    except Exception as e:
        logger.warning(f"Error detecting PAN-OS version from configuration: {e}", exc_info=True)
        logger.warning(f"Using default version {DEFAULT_VERSION}")
        return DEFAULT_VERSION