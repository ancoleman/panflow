"""
Configuration loader for PANFlow a PAN-OS XML utility.

This module provides functions to load and parse PAN-OS XML configurations.
"""

import os
from typing import Optional, Dict, Any, List, Tuple, Union
from lxml import etree
import logging
from .xpath_resolver import determine_version_from_config

logger = logging.getLogger("panflow")

def load_config_from_file(file_path: str, version: Optional[str] = None) -> Tuple[etree._ElementTree, str]:
    """
    Load XML configuration from a file and return the element tree and detected version.
    
    Args:
        file_path: Path to XML configuration file
        version: User-specified PAN-OS version (optional)
        
    Returns:
        Tuple containing (ElementTree, PAN-OS version)
        
    Raises:
        FileNotFoundError: If the configuration file does not exist
        etree.XMLSyntaxError: If the XML is malformed
    """
    if not os.path.exists(file_path):
        logger.error(f"Configuration file not found: {file_path}")
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
    try:
        # Parse the XML file
        tree = etree.parse(file_path)
        root = tree.getroot()
        
        # Use user-specified version if provided, otherwise detect from config
        detected_version = determine_version_from_config(etree.tostring(root, encoding="utf-8").decode())
        final_version = version or detected_version
        
        logger.info(f"Loaded configuration from {file_path} (PAN-OS {final_version})")
        return tree, final_version
    except etree.XMLSyntaxError as e:
        logger.error(f"Error parsing XML configuration: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
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
    try:
        # Parse the XML string
        root = etree.fromstring(xml_string.encode('utf-8'))
        tree = etree.ElementTree(root)
        
        # Detect PAN-OS version from the configuration
        version = determine_version_from_config(xml_string)
        
        logger.info("Loaded configuration from string (PAN-OS {version})")
        return tree, version
    except etree.XMLSyntaxError as e:
        logger.error(f"Error parsing XML configuration: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
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
    try:
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        
        # Write the configuration to file
        tree.write(output_file, encoding='utf-8', xml_declaration=True, pretty_print=True)
        logger.info(f"Saved configuration to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
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
    try:
        # Find all elements matching the xpath
        elements = tree.xpath(xpath, namespaces=namespaces)
        logger.debug(f"XPath search '{xpath}' found {len(elements)} elements")
        return elements
    except Exception as e:
        logger.error(f"Error performing XPath search: {e}")
        return []

def extract_element_data(element: etree._Element) -> Dict[str, Any]:
    """
    Extract all data from an XML element.
    
    Args:
        element: XML element
        
    Returns:
        Dictionary of element data
    """
    data = {}
    
    # Add attributes
    for key, value in element.attrib.items():
        data[key] = value
    
    # Add child elements
    for child in element:
        # Check if the child element has multiple "member" children
        members = child.xpath("./member")
        if members:
            # This is a list element
            data[child.tag] = [member.text for member in members if member.text]
        else:
            # Not a list, just a single value or nested element
            if len(child) == 0:
                # Simple element with text
                data[child.tag] = child.text
            else:
                # Nested element, recursively extract data
                data[child.tag] = extract_element_data(child)
    
    return data

def detect_device_type(tree: etree._ElementTree) -> str:
    """
    Detect whether a configuration is from a firewall or Panorama.
    
    Args:
        tree: ElementTree containing the configuration
        
    Returns:
        str: "firewall" or "panorama"
    """
    # Check for Panorama-specific elements
    panorama_elements = tree.xpath("/config/devices/entry[@name='localhost.localdomain']/device-group")
    template_elements = tree.xpath("/config/devices/entry[@name='localhost.localdomain']/template")
    
    if panorama_elements or template_elements:
        return "panorama"
    else:
        return "firewall"