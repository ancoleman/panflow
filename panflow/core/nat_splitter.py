"""
NAT rule splitter for PANFlow.

This module provides functionality for splitting bidirectional NAT rules into separate
unidirectional rules. This is particularly useful when converting from other vendors'
configurations where bidirectional NAT is implicit but in PAN-OS requires explicit 
configuration due to security zones.
"""

import logging
import copy
from typing import Dict, Any, Optional, List, Tuple, Union
from lxml import etree

from .xpath_resolver import get_policy_xpath
from .config_loader import xpath_search
from .xml_utils import clone_element

# Initialize logger
logger = logging.getLogger("panflow")

class NATRuleSplitter:
    """
    Class for splitting bidirectional NAT rules into separate unidirectional rules.
    
    This functionality is valuable when migrating from other vendors' configurations
    where bidirectional NAT rules are implicit, but PAN-OS handles directionality
    differently due to security zones.
    """
    
    def __init__(
        self,
        tree: etree._ElementTree,
        device_type: str = "firewall",
        context_type: str = "vsys",
        version: str = "10.2",
        **kwargs
    ):
        """
        Initialize the NAT rule splitter.
        
        Args:
            tree: ElementTree containing the configuration
            device_type: Type of device ("firewall" or "panorama")
            context_type: Type of context (shared, device_group, vsys)
            version: PAN-OS version
            **kwargs: Additional context parameters (device_group, vsys, etc.)
        """
        logger.debug("Initializing NATRuleSplitter")
        self.tree = tree
        self.device_type = device_type
        self.context_type = context_type
        self.version = version
        self.context_kwargs = kwargs
        
        logger.info(f"NATRuleSplitter initialized: device_type={device_type}, context_type={context_type}, version={version}")
    
    def split_bidirectional_rule(
        self, 
        rule_name: str,
        policy_type: str = "nat_rules",
        reverse_name_suffix: str = "-reverse",
        zone_swap: bool = True,
        address_swap: bool = True,
        disable_orig_bidirectional: bool = True,
        return_rule_any_any: bool = False
    ) -> Dict[str, bool]:
        """
        Split a bidirectional NAT rule into two unidirectional rules.
        
        Args:
            rule_name: Name of the bidirectional NAT rule to split
            policy_type: Type of NAT policy ("nat_rules", "nat_pre_rules", "nat_post_rules")
            reverse_name_suffix: Suffix to add to the name of the reverse rule
            zone_swap: Whether to swap source and destination zones in the reverse rule
            address_swap: Whether to swap source and destination addresses in the reverse rule
            disable_orig_bidirectional: Whether to disable bidirectional flag on the original rule
            return_rule_any_any: If True, use "any" for source zone and address in the return rule
            
        Returns:
            Dict: Status information about the operation
        """
        # Find the NAT rule
        logger.info(f"Splitting bidirectional NAT rule: {rule_name}")
        
        xpath = get_policy_xpath(
            policy_type,
            self.device_type,
            self.context_type,
            self.version,
            rule_name,
            **self.context_kwargs
        )
        
        rule_elements = xpath_search(self.tree, xpath)
        if not rule_elements:
            logger.error(f"NAT rule '{rule_name}' not found")
            return {"success": False, "error": f"Rule '{rule_name}' not found"}
        
        rule = rule_elements[0]
        
        # Check if the rule is bidirectional
        bidirectional = rule.find("./bi-directional")
        if bidirectional is None or bidirectional.text != 'yes':
            logger.warning(f"NAT rule '{rule_name}' is not bidirectional")
            return {"success": False, "error": "Rule is not bidirectional"}
        
        # Create the reverse rule name
        reverse_rule_name = f"{rule_name}{reverse_name_suffix}"
        
        # Check if the reverse rule already exists
        reverse_xpath = get_policy_xpath(
            policy_type,
            self.device_type,
            self.context_type,
            self.version,
            reverse_rule_name,
            **self.context_kwargs
        )
        
        reverse_elements = xpath_search(self.tree, reverse_xpath)
        if reverse_elements:
            logger.warning(f"Reverse NAT rule '{reverse_rule_name}' already exists")
            return {"success": False, "error": f"Reverse rule '{reverse_rule_name}' already exists"}
        
        # Create the reverse rule
        try:
            parent_xpath = xpath.rsplit("/entry", 1)[0]
            parent_elements = xpath_search(self.tree, parent_xpath)
            if not parent_elements:
                logger.error(f"Parent element not found for rule '{rule_name}'")
                return {"success": False, "error": "Parent element not found"}
            
            parent = parent_elements[0]
            
            # Clone the original rule
            reverse_rule = clone_element(rule)
            reverse_rule.set("name", reverse_rule_name)
            
            # Modify the reverse rule
            self._configure_reverse_rule(
                reverse_rule,
                zone_swap=zone_swap,
                address_swap=address_swap,
                return_rule_any_any=return_rule_any_any
            )
            
            # Add the reverse rule after the original rule
            position = self._find_rule_position(parent, rule_name)
            if position is not None:
                parent.insert(position + 1, reverse_rule)
            else:
                # Fallback if position can't be determined
                parent.append(reverse_rule)
                
            logger.info(f"Added reverse NAT rule '{reverse_rule_name}'")
            
            # Disable bidirectional on the original rule if requested
            if disable_orig_bidirectional:
                bidirectional.getparent().remove(bidirectional)
                logger.info(f"Disabled bidirectional flag on original rule '{rule_name}'")
            
            return {
                "success": True, 
                "original_rule": rule_name, 
                "reverse_rule": reverse_rule_name,
                "bidirectional_disabled": disable_orig_bidirectional
            }
            
        except Exception as e:
            logger.error(f"Error splitting bidirectional NAT rule '{rule_name}': {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def split_all_bidirectional_rules(
        self,
        policy_type: str = "nat_rules",
        reverse_name_suffix: str = "-reverse",
        zone_swap: bool = True,
        address_swap: bool = True,
        disable_orig_bidirectional: bool = True,
        return_rule_any_any: bool = False,
        name_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Split all bidirectional NAT rules in the configuration.
        
        Args:
            policy_type: Type of NAT policy ("nat_rules", "nat_pre_rules", "nat_post_rules")
            reverse_name_suffix: Suffix to add to the name of the reverse rule
            zone_swap: Whether to swap source and destination zones in the reverse rule
            address_swap: Whether to swap source and destination addresses in the reverse rule
            disable_orig_bidirectional: Whether to disable bidirectional flag on the original rule
            return_rule_any_any: If True, use "any" for source zone and address in the return rule
            name_filter: Optional string to filter rule names (only process rules containing this string)
            
        Returns:
            Dict: Summary of split operations with success and failure counts
        """
        logger.info(f"Splitting all bidirectional NAT rules of type {policy_type}")
        
        # Get the base XPath for the NAT rules
        base_xpath = get_policy_xpath(
            policy_type,
            self.device_type,
            self.context_type,
            self.version,
            **self.context_kwargs
        )
        
        # Find all bidirectional NAT rules
        if name_filter:
            rule_xpath = f"{base_xpath}/entry[bi-directional='yes' and contains(@name, '{name_filter}')]"
        else:
            rule_xpath = f"{base_xpath}/entry[bi-directional='yes']"
            
        bidirectional_rules = xpath_search(self.tree, rule_xpath)
        
        if not bidirectional_rules:
            logger.info("No bidirectional NAT rules found")
            return {"success": True, "processed": 0, "succeeded": 0, "failed": 0, "details": []}
        
        logger.info(f"Found {len(bidirectional_rules)} bidirectional NAT rules")
        
        # Process each rule
        results = {
            "success": True,
            "processed": len(bidirectional_rules),
            "succeeded": 0,
            "failed": 0,
            "details": []
        }
        
        for rule in bidirectional_rules:
            rule_name = rule.get("name", "unknown")
            logger.debug(f"Processing bidirectional NAT rule: {rule_name}")
            
            result = self.split_bidirectional_rule(
                rule_name,
                policy_type,
                reverse_name_suffix,
                zone_swap,
                address_swap,
                disable_orig_bidirectional,
                return_rule_any_any
            )
            
            results["details"].append({
                "rule_name": rule_name,
                "result": result
            })
            
            if result["success"]:
                results["succeeded"] += 1
            else:
                results["failed"] += 1
        
        logger.info(f"Bidirectional NAT rule splitting complete: {results['succeeded']} succeeded, {results['failed']} failed")
        return results
    
    def _configure_reverse_rule(
        self,
        rule: etree._Element,
        zone_swap: bool = True,
        address_swap: bool = True,
        return_rule_any_any: bool = False
    ) -> None:
        """
        Configure a reverse NAT rule by modifying the cloned original rule.
        
        Args:
            rule: The NAT rule XML element to configure as reverse rule
            zone_swap: Whether to swap source and destination zones
            address_swap: Whether to swap source and destination addresses
            return_rule_any_any: If True, use "any" for source zone and address
        """
        rule_name = rule.get("name", "unknown")
        logger.debug(f"Configuring reverse NAT rule: {rule_name}")
        
        # Remove bidirectional flag
        bidirectional = rule.find("./bi-directional")
        if bidirectional is not None:
            bidirectional.getparent().remove(bidirectional)
            logger.debug(f"Removed bidirectional flag from reverse rule '{rule_name}'")
        
        if return_rule_any_any:
            # Use "any" for source zone and address
            self._set_elements_to_any(rule, "source")
            self._set_elements_to_any(rule, "from")
            logger.debug(f"Set source zone and address to 'any' for reverse rule '{rule_name}'")
        elif zone_swap or address_swap:
            # Swap source and destination
            if zone_swap:
                self._swap_elements(rule, "from", "to")
                logger.debug(f"Swapped source and destination zones for reverse rule '{rule_name}'")
            
            if address_swap:
                self._swap_elements(rule, "source", "destination")
                logger.debug(f"Swapped source and destination addresses for reverse rule '{rule_name}'")
        
        # Update nat-type if it exists
        nat_type = rule.find("./nat-type")
        if nat_type is not None:
            nat_type.text = "ipv4"  # Ensure it's set to IPv4 (not bidirectional)
            logger.debug(f"Set nat-type to 'ipv4' for reverse rule '{rule_name}'")
        
        # Handle source and destination translation elements
        src_translation = rule.find("./source-translation")
        dst_translation = rule.find("./destination-translation")
        
        if src_translation is not None and dst_translation is not None:
            # If both source and destination translation exist, swap them for the reverse rule
            if address_swap:
                self._swap_translation_elements(rule)
                logger.debug(f"Swapped source and destination translation for reverse rule '{rule_name}'")
        elif src_translation is not None:
            # If only source translation exists, create destination translation with its values
            if address_swap:
                self._convert_src_to_dst_translation(rule)
                logger.debug(f"Converted source translation to destination translation for reverse rule '{rule_name}'")
        elif dst_translation is not None:
            # If only destination translation exists, create source translation with its values
            if address_swap:
                self._convert_dst_to_src_translation(rule)
                logger.debug(f"Converted destination translation to source translation for reverse rule '{rule_name}'")
    
    def _swap_elements(self, rule: etree._Element, elem1_name: str, elem2_name: str) -> None:
        """
        Swap two elements in a rule.
        
        Args:
            rule: The NAT rule XML element
            elem1_name: Name of the first element
            elem2_name: Name of the second element
        """
        elem1 = rule.find(f"./{elem1_name}")
        elem2 = rule.find(f"./{elem2_name}")
        
        if elem1 is not None and elem2 is not None:
            # Backup the elements
            elem1_copy = copy.deepcopy(elem1)
            elem2_copy = copy.deepcopy(elem2)
            
            # Remove original elements
            elem1.getparent().remove(elem1)
            elem2.getparent().remove(elem2)
            
            # Create new elements with swapped content
            new_elem1 = etree.SubElement(rule, elem1_name)
            for child in elem2_copy:
                new_elem1.append(copy.deepcopy(child))
                
            new_elem2 = etree.SubElement(rule, elem2_name)
            for child in elem1_copy:
                new_elem2.append(copy.deepcopy(child))
    
    def _set_elements_to_any(self, rule: etree._Element, elem_name: str) -> None:
        """
        Set an element's members to "any".
        
        Args:
            rule: The NAT rule XML element
            elem_name: Name of the element to modify
        """
        elem = rule.find(f"./{elem_name}")
        if elem is not None:
            # Clear all existing members
            for child in list(elem):
                elem.remove(child)
            
            # Add "any" member
            member = etree.SubElement(elem, "member")
            member.text = "any"
    
    def _swap_translation_elements(self, rule: etree._Element) -> None:
        """
        Swap source and destination translation elements in a rule.
        
        Args:
            rule: The NAT rule XML element
        """
        src_trans = rule.find("./source-translation")
        dst_trans = rule.find("./destination-translation")
        
        if src_trans is not None and dst_trans is not None:
            # Backup the elements
            src_trans_copy = copy.deepcopy(src_trans)
            dst_trans_copy = copy.deepcopy(dst_trans)
            
            # Remove original elements
            src_trans.getparent().remove(src_trans)
            dst_trans.getparent().remove(dst_trans)
            
            # Create new elements with swapped content
            # Note: The internal structure is different for src and dst translation,
            # so we need to adapt the content accordingly
            self._create_adapted_translation(rule, "source-translation", dst_trans_copy)
            self._create_adapted_translation(rule, "destination-translation", src_trans_copy)
    
    def _convert_src_to_dst_translation(self, rule: etree._Element) -> None:
        """
        Convert source translation to destination translation.
        
        Args:
            rule: The NAT rule XML element
        """
        src_trans = rule.find("./source-translation")
        if src_trans is not None:
            # Create a new destination translation based on source translation
            self._create_adapted_translation(rule, "destination-translation", src_trans)
            
            # Remove the source translation
            src_trans.getparent().remove(src_trans)
    
    def _convert_dst_to_src_translation(self, rule: etree._Element) -> None:
        """
        Convert destination translation to source translation.
        
        Args:
            rule: The NAT rule XML element
        """
        dst_trans = rule.find("./destination-translation")
        if dst_trans is not None:
            # Create a new source translation based on destination translation
            self._create_adapted_translation(rule, "source-translation", dst_trans)
            
            # Remove the destination translation
            dst_trans.getparent().remove(dst_trans)
    
    def _create_adapted_translation(
        self, 
        rule: etree._Element, 
        target_type: str, 
        source_elem: etree._Element
    ) -> None:
        """
        Create a new translation element adapted from another type.
        
        Args:
            rule: The NAT rule XML element
            target_type: Target translation type ("source-translation" or "destination-translation")
            source_elem: Source translation element to adapt from
        """
        if target_type == "source-translation":
            # Creating source translation from destination translation
            new_trans = etree.SubElement(rule, "source-translation")
            
            # Check for translated address
            translated_addr = source_elem.find("./translated-address")
            if translated_addr is not None and translated_addr.text:
                # For source translation, we need dynamic-ip-and-port or static-ip
                # Check if there's a translated port to determine which to use
                translated_port = source_elem.find("./translated-port")
                
                if translated_port is not None and translated_port.text:
                    # Use static-ip with port, similar to destination translation with port
                    static_ip = etree.SubElement(new_trans, "static-ip")
                    translated_address = etree.SubElement(static_ip, "translated-address")
                    translated_address.text = translated_addr.text
                    
                    # Copy port information
                    static_port = etree.SubElement(new_trans, "static-port")
                    static_port.text = "yes"
                else:
                    # Use static-ip without port
                    static_ip = etree.SubElement(new_trans, "static-ip")
                    translated_address = etree.SubElement(static_ip, "translated-address")
                    translated_address.text = translated_addr.text
            else:
                # No translated address found, use dynamic-ip fallback
                dynamic_ip = etree.SubElement(new_trans, "dynamic-ip-and-port")
                translated_address = etree.SubElement(dynamic_ip, "translated-address")
                interface_addr = etree.SubElement(translated_address, "interface-address")
                ip = etree.SubElement(interface_addr, "ip")
                ip.text = "0.0.0.0"  # Default fallback, should be replaced with actual interface
        
        elif target_type == "destination-translation":
            # Creating destination translation from source translation
            new_trans = etree.SubElement(rule, "destination-translation")
            
            # Look for translated address in source translation
            # This could be in different places depending on the type
            translated_addr = None
            
            # Check static-ip
            static_ip = source_elem.find("./static-ip")
            if static_ip is not None:
                translated_addr = static_ip.find("./translated-address")
            
            # Check dynamic-ip
            if translated_addr is None:
                dynamic_ip = source_elem.find("./dynamic-ip")
                if dynamic_ip is not None:
                    translated_addr = dynamic_ip.find("./translated-address")
            
            # Check dynamic-ip-and-port
            if translated_addr is None:
                dynamic_ip_port = source_elem.find("./dynamic-ip-and-port")
                if dynamic_ip_port is not None:
                    # This could be an interface address or translated address
                    translated_addr = dynamic_ip_port.find(".//ip")  # Get the first IP found
            
            # Set the translated address
            if translated_addr is not None and translated_addr.text:
                new_addr = etree.SubElement(new_trans, "translated-address")
                new_addr.text = translated_addr.text
            else:
                # Fallback
                new_addr = etree.SubElement(new_trans, "translated-address")
                new_addr.text = "0.0.0.0"  # Default fallback
            
            # Check for port translation
            static_port = source_elem.find("./static-port")
            if static_port is not None and static_port.text == "yes":
                new_port = etree.SubElement(new_trans, "translated-port")
                new_port.text = "0"  # Default fallback, should be replaced
    
    def _find_rule_position(self, parent: etree._Element, rule_name: str) -> Optional[int]:
        """
        Find the position of a rule in the parent element.
        
        Args:
            parent: Parent XML element containing the rules
            rule_name: Name of the rule to find
            
        Returns:
            Optional[int]: Index of the rule or None if not found
        """
        for i, child in enumerate(parent):
            if child.tag == "entry" and child.get("name") == rule_name:
                return i
        return None