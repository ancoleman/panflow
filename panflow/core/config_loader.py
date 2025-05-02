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
    logger.info(f"Loading configuration file: {file_path}")
    
    if not os.path.exists(file_path):
        logger.error(f"Configuration file not found: {file_path}")
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
    try:
        # Parse the XML file
        logger.debug(f"Attempting to parse XML file: {file_path}")
        tree = etree.parse(file_path)
        root = tree.getroot()
        
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
    
    data = {}
    
    try:
        # Add attributes
        for key, value in element.attrib.items():
            data[key] = value
        
        # Add child elements
        for child in element:
            # Check if the child element has multiple "member" children
            members = child.xpath("./member")
            if members:
                # This is a list element
                member_values = [member.text for member in members if member.text]
                logger.debug(f"Extracted {len(member_values)} members from {child.tag}")
                data[child.tag] = member_values
            else:
                # Not a list, just a single value or nested element
                if len(child) == 0:
                    # Simple element with text
                    data[child.tag] = child.text
                else:
                    # Nested element, recursively extract data
                    logger.debug(f"Recursively extracting nested element: {child.tag}")
                    data[child.tag] = extract_element_data(child)
        
        return data
    except Exception as e:
        logger.error(f"Error extracting data from element {element_tag}[name='{element_name}']: {e}", exc_info=True)
        return data  # Return whatever data we managed to extract before the error

def detect_device_type(tree: etree._ElementTree) -> str:
    """
    Detect whether a configuration is from a firewall or Panorama.
    
    Args:
        tree: ElementTree containing the configuration
        
    Returns:
        str: "firewall" or "panorama"
    """
    logger.debug("Detecting device type from configuration")
    
    try:
        # Check for Panorama-specific elements
        panorama_elements = tree.xpath("/config/devices/entry[@name='localhost.localdomain']/device-group")
        template_elements = tree.xpath("/config/devices/entry[@name='localhost.localdomain']/template")
        
        if panorama_elements or template_elements:
            panorama_indicators = []
            if panorama_elements:
                panorama_indicators.append(f"{len(panorama_elements)} device groups")
            if template_elements:
                panorama_indicators.append(f"{len(template_elements)} templates")
                
            logger.info(f"Detected device type: panorama ({', '.join(panorama_indicators)})")
            return "panorama"
        else:
            # Check for firewall-specific elements
            vsys_elements = tree.xpath("/config/devices/entry[@name='localhost.localdomain']/vsys")
            if vsys_elements:
                logger.info(f"Detected device type: firewall ({len(vsys_elements)} vsys)")
            else:
                logger.info("Detected device type: firewall (default, no specific indicators)")
            return "firewall"
    except Exception as e:
        logger.warning(f"Error detecting device type, defaulting to firewall: {e}", exc_info=True)
        return "firewall"