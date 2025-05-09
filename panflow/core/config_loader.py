"""
Configuration loader for PANFlow.

This module provides functions to load and parse PAN-OS XML configurations.
"""

import os
from typing import Optional, Dict, Any, List, Tuple, Union
from lxml import etree
import logging
from .xpath_resolver import determine_version_from_config

# Initialize logger for this module
logger = logging.getLogger("panflow")

def load_config_from_file(file_path: str, version: Optional[str] = None, validate: bool = False) -> Tuple[etree._ElementTree, str]:
    """
    Load XML configuration from a file and return the element tree and detected version.
    
    Args:
        file_path: Path to XML configuration file
        version: User-specified PAN-OS version (optional)
        validate: Whether to validate the XML structure
        
    Returns:
        Tuple containing (ElementTree, PAN-OS version)
        
    Raises:
        FileNotFoundError: If the configuration file does not exist
        etree.XMLSyntaxError: If the XML is malformed
        ValueError: If the XML doesn't appear to be a valid PAN-OS configuration
    """
    logger.info(f"Loading configuration file: {file_path}")
    
    if not os.path.exists(file_path):
        logger.error(f"Configuration file not found: {file_path}")
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
    try:
        # Parse the XML file
        logger.debug(f"Attempting to parse XML file: {file_path}")
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(file_path, parser)
        root = tree.getroot()
        
        # Basic validation of PAN-OS configuration structure
        if validate:
            if root.tag != "config":
                logger.error("XML root element is not 'config' - not a valid PAN-OS configuration")
                raise ValueError("XML root element is not 'config' - not a valid PAN-OS configuration")
            
            # Check for essential PAN-OS configuration elements
            essential_elements = [
                "/config/devices",
                "/config/devices/entry[@name='localhost.localdomain']"
            ]
            
            for xpath in essential_elements:
                elements = tree.xpath(xpath)
                if not elements:
                    logger.error(f"Missing essential PAN-OS configuration element: {xpath}")
                    raise ValueError(f"Missing essential PAN-OS configuration element: {xpath}")
            
            logger.debug("Basic PAN-OS configuration structure validation passed")
        
        # Use user-specified version if provided, otherwise detect from config
        logger.debug("Detecting configuration version")
        detected_version = determine_version_from_config(etree.tostring(root, encoding="utf-8").decode())
        final_version = version or detected_version
        
        logger.info(f"Successfully loaded configuration from {file_path} (PAN-OS {final_version})")
        return tree, final_version
    except etree.XMLSyntaxError as e:
        logger.error(f"Error parsing XML configuration: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading configuration: {e}", exc_info=True)
        raise

def load_config_from_string(xml_string: str) -> Tuple[etree._ElementTree, str]:
    """
    Load XML configuration from a string and return the element tree and detected version.
    
    Args:
        xml_string: XML configuration as string
        
    Returns:
        Tuple containing (ElementTree, PAN-OS version)
        
    Raises:
        etree.XMLSyntaxError: If the XML is malformed
    """
    logger.info("Loading configuration from string")
    
    try:
        # Parse the XML string
        logger.debug("Attempting to parse XML string")
        root = etree.fromstring(xml_string.encode('utf-8'))
        tree = etree.ElementTree(root)
        
        # Detect PAN-OS version from the configuration
        logger.debug("Detecting configuration version")
        version = determine_version_from_config(xml_string)
        
        logger.info(f"Successfully loaded configuration from string (PAN-OS {version})")
        return tree, version
    except etree.XMLSyntaxError as e:
        logger.error(f"Error parsing XML configuration string: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading configuration from string: {e}", exc_info=True)
        raise

def save_config(tree: etree._ElementTree, output_file: str) -> bool:
    """
    Save an XML configuration to a file.
    
    Args:
        tree: ElementTree containing the configuration
        output_file: Path to save the configuration file
        
    Returns:
        bool: Success status
    """
    logger.info(f"Saving configuration to: {output_file}")
    
    try:
        # Ensure the output directory exists
        output_dir = os.path.dirname(os.path.abspath(output_file))
        if output_dir:
            logger.debug(f"Ensuring output directory exists: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
        
        # Write the configuration to file
        logger.debug("Writing configuration to file")
        tree.write(output_file, encoding='utf-8', xml_declaration=True, pretty_print=True)
        logger.info(f"Successfully saved configuration to {output_file}")
        return True
    except PermissionError as e:
        logger.error(f"Permission denied when saving configuration to {output_file}: {e}", exc_info=True)
        return False
    except IOError as e:
        logger.error(f"I/O error when saving configuration to {output_file}: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Unexpected error saving configuration to {output_file}: {e}", exc_info=True)
        return False

def xpath_search(tree: etree._ElementTree, xpath: str, namespaces: Optional[Dict[str, str]] = None) -> List[etree._Element]:
    """
    Search for elements using XPath.
    
    Args:
        tree: ElementTree to search
        xpath: XPath expression
        namespaces: Optional namespace mappings
        
    Returns:
        List of matching elements
    """
    logger.debug(f"Executing XPath search: {xpath}")
    
    try:
        # Find all elements matching the xpath
        elements = tree.xpath(xpath, namespaces=namespaces)
        element_count = len(elements)
        
        if element_count > 0:
            logger.debug(f"XPath search '{xpath}' found {element_count} elements")
        else:
            logger.debug(f"XPath search '{xpath}' found no elements")
            
        return elements
    except etree.XPathSyntaxError as e:
        logger.error(f"XPath syntax error in '{xpath}': {e}", exc_info=True)
        return []
    except etree.XPathEvalError as e:
        logger.error(f"XPath evaluation error in '{xpath}': {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Unexpected error performing XPath search '{xpath}': {e}", exc_info=True)
        return []

def extract_element_data(element: etree._Element) -> Dict[str, Any]:
    """
    Extract all data from an XML element.
    
    Args:
        element: XML element
        
    Returns:
        Dictionary of element data
    """
    element_tag = element.tag
    element_name = element.get('name', 'unknown')
    logger.debug(f"Extracting data from element: {element_tag}[name='{element_name}']")
    
    # Use the compatibility function from xml.base
    from .xml.base import compat_element_to_dict
    
    try:
        data = compat_element_to_dict(element)
        return data
    except Exception as e:
        logger.error(f"Error extracting data from element {element_tag}[name='{element_name}']: {e}", exc_info=True)
        return {}  # Return empty dict on error

def detect_device_type(tree: etree._ElementTree) -> str:
    """
    Detect whether a configuration is from a firewall or Panorama.
    
    This function uses a confidence scoring system to determine the device type
    based on characteristic XML elements found in Panorama vs Firewall configurations.
    
    Args:
        tree: ElementTree containing the configuration
        
    Returns:
        str: "firewall" or "panorama"
    """
    logger.debug("Detecting device type from configuration")
    
    try:
        # Initialize confidence scores
        panorama_score = 0
        firewall_score = 0
        
        # Define marker XPaths with their confidence weights
        panorama_markers = {
            # Definitive Panorama markers
            "/config/devices/entry[@name='localhost.localdomain']/device-group": 10,
            "/config/devices/entry[@name='localhost.localdomain']/template": 10,
            "/config/devices/entry[@name='localhost.localdomain']/log-settings/panorama": 10,
            "/config/panorama": 15,
            "/config/shared": 8,
            
            # Strong Panorama indicators
            "/config/devices/entry[@name='localhost.localdomain']/device-config": 7,
            "/config/devices/entry[@name='localhost.localdomain']/template-stack": 7,
            "/config/devices/entry[@name='localhost.localdomain']/collector-group": 7,
            "/config/readonly/devices/localhost.localdomain/platform": 5  # Panorama platform info
        }
        
        firewall_markers = {
            # Definitive Firewall markers
            "/config/devices/entry[@name='localhost.localdomain']/vsys": 10,
            "/config/devices/entry[@name='localhost.localdomain']/network/interface": 9,
            "/config/devices/entry[@name='localhost.localdomain']/network/virtual-router": 8,
            "/config/devices/entry[@name='localhost.localdomain']/network/profiles": 7,
            
            # Strong Firewall indicators
            "/config/devices/entry[@name='localhost.localdomain']/vsys/entry/zone": 8,
            "/config/devices/entry[@name='localhost.localdomain']/vsys/entry/rulebase": 8,
            "/config/devices/entry[@name='localhost.localdomain']/network/ike": 6,
            "/config/devices/entry[@name='localhost.localdomain']/network/qos": 6,
            "/config/devices/entry[@name='localhost.localdomain']/network/tunnel": 6,
            "/config/devices/entry[@name='localhost.localdomain']/network/vlan": 5
        }
        
        # Collect indicators for detailed logging
        panorama_indicators = []
        firewall_indicators = []
        
        # Check Panorama markers
        for xpath, weight in panorama_markers.items():
            elements = tree.xpath(xpath)
            if elements:
                count = len(elements)
                panorama_score += weight
                panorama_indicators.append(f"{xpath.split('/')[-1]}: {count}")
        
        # Check Firewall markers
        for xpath, weight in firewall_markers.items():
            elements = tree.xpath(xpath)
            if elements:
                count = len(elements)
                firewall_score += weight
                firewall_indicators.append(f"{xpath.split('/')[-1]}: {count}")
        
        # Special check for local interface presence
        if tree.xpath("//network/interface/ethernet"):
            firewall_score += 5
            firewall_indicators.append("local-interface")
        
        # Special check for panorama server mode
        if tree.xpath("//setting/panorama-server"):
            panorama_score += 2
            firewall_score += 5  # Firewalls generally have panorama-server settings
            firewall_indicators.append("panorama-server")
        
        # Special check for log-collector-group (only firewalls have it)
        if tree.xpath("//setting/log-collector-group"):
            firewall_score += 4
            firewall_indicators.append("log-collector-group")
        
        # Check hostname - "Panorama" in hostname is a clue
        hostname_elements = tree.xpath("//hostname")
        if hostname_elements and len(hostname_elements) > 0:
            hostname = hostname_elements[0].text
            if hostname and "panorama" in hostname.lower():
                panorama_score += 3
                panorama_indicators.append(f"hostname: {hostname}")
        
        # Log detection details at debug level
        logger.debug(f"Panorama score: {panorama_score}, indicators: {', '.join(panorama_indicators) if panorama_indicators else 'none'}")
        logger.debug(f"Firewall score: {firewall_score}, indicators: {', '.join(firewall_indicators) if firewall_indicators else 'none'}")
        
        # Determine result based on scores
        if panorama_score > firewall_score:
            logger.info(f"Detected device type: panorama (confidence score: {panorama_score})")
            return "panorama"
        elif firewall_score > panorama_score:
            logger.info(f"Detected device type: firewall (confidence score: {firewall_score})")
            return "firewall"
        else:
            # In case of a tie, default to firewall 
            # This is safer as most commands work with firewall context by default
            logger.info(f"No clear device type detected (tied scores: {panorama_score}), defaulting to firewall")
            return "firewall"
            
    except Exception as e:
        logger.warning(f"Error detecting device type, defaulting to firewall: {e}", exc_info=True)
        return "firewall"