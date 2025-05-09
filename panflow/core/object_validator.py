"""
Object validator for PANFlow.

This module provides functionality for validating PAN-OS configuration objects.
"""

import logging
import re
import ipaddress
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from lxml import etree

from .xml.base import find_element, find_elements

# Initialize logger
logger = logging.getLogger("panflow")

class ObjectValidator:
    """
    Class for validating PAN-OS objects.
    
    Provides methods for validating different types of PAN-OS objects against
    known constraints and requirements.
    """
    
    def __init__(self, device_type: str = "panorama", version: str = "11.2"):
        """
        Initialize the validator.
        
        Args:
            device_type: Type of device ("firewall" or "panorama")
            version: PAN-OS version for validation rules
        """
        logger.debug(f"Initializing ObjectValidator for {device_type} (version {version})")
        self.device_type = device_type.lower()
        self.version = version
    
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