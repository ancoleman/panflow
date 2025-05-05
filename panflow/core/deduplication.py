"""
Deduplication engine for PANFlow.

This module provides classes and functions to identify and merge duplicate objects
in PAN-OS configurations, with reference tracking to maintain configuration integrity.

Supported object types:
- address: IP addresses, FQDNs, and IP ranges
- service: TCP/UDP service objects
- tag: Tag objects
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Set
from lxml import etree

from .xpath_resolver import get_object_xpath
from .config_loader import xpath_search

# Initialize logger
logger = logging.getLogger("panflow")

class DeduplicationEngine:
    """
    Engine for finding and merging duplicate objects in PAN-OS configurations.
    
    This class provides methods to identify duplicate objects based on their values
    and merge them while updating all references.
    """
    
    def __init__(self, tree, device_type, context_type, version, **kwargs):
        """
        Initialize the deduplication engine.
        
        Args:
            tree: ElementTree containing the configuration
            device_type: Type of device ("firewall" or "panorama")
            context_type: Type of context (shared, device_group, vsys)
            version: PAN-OS version
            **kwargs: Additional parameters (device_group, vsys, etc.)
        """
        logger.info("Initializing DeduplicationEngine")
        self.tree = tree
        self.device_type = device_type
        self.context_type = context_type
        self.version = version
        self.context_kwargs = kwargs
        
        logger.debug(f"Configuration parameters: device_type={device_type}, context_type={context_type}, version={version}")
        logger.debug(f"Context parameters: {kwargs}")
        
    def find_duplicates(self, object_type, reference_tracking=True):
        """
        Find duplicate objects of the specified type.
        
        Args:
            object_type: Type of object to find duplicates for (address, service, tag)
            reference_tracking: Whether to track references to objects (default: True)
            
        Returns:
            Tuple of (duplicates, references):
                - duplicates: Dictionary mapping values to lists of (name, element) tuples
                - references: Dictionary mapping object names to lists of references
        """
        logger.info(f"Finding duplicate {object_type} objects")
        
        # Map to the appropriate method based on object type
        if object_type.lower() in ['address', 'addresses']:
            return self.find_duplicate_addresses(reference_tracking)
        elif object_type.lower() in ['service', 'services']:
            return self.find_duplicate_services(reference_tracking)
        elif object_type.lower() in ['tag', 'tags']:
            return self.find_duplicate_tags(reference_tracking)
        else:
            logger.error(f"Unsupported object type for deduplication: {object_type}")
            logger.info("Supported types: address, service, tag")
            return {}, {}
        
    def find_duplicate_addresses(self, reference_tracking=True):
        """
        Find duplicate address objects based on their values.
        
        Args:
            reference_tracking: Whether to track references to objects (default: True)
            
        Returns:
            Tuple of (duplicates, references):
                - duplicates: Dictionary mapping values to lists of (name, element) tuples
                - references: Dictionary mapping object names to lists of references
        """
        logger.info("Finding duplicate address objects")
        logger.debug(f"Reference tracking: {reference_tracking}")
        
        # Get all address objects
        try:
            address_xpath = get_object_xpath('address', self.device_type, self.context_type, 
                                            self.version, **self.context_kwargs)
            
            logger.debug(f"Retrieving address objects using XPath: {address_xpath}")
            addresses = xpath_search(self.tree, address_xpath)
            
            logger.info(f"Found {len(addresses)} address objects to analyze")
            
        except Exception as e:
            logger.error(f"Error retrieving address objects: {e}", exc_info=True)
            return {}, {}
        
        # Group by value
        by_value = {}
        
        logger.debug("Grouping address objects by value")
        for addr in addresses:
            try:
                name = addr.get('name', '')
                if not name:
                    logger.warning(f"Skipping address object with no name attribute")
                    continue
                
                # Determine the key for grouping
                value_key = None
                ip_netmask = addr.find('./ip-netmask')
                if ip_netmask is not None and ip_netmask.text:
                    value_key = f"ip-netmask:{ip_netmask.text}"
                    logger.debug(f"Address '{name}' has ip-netmask value: {ip_netmask.text}")
                
                fqdn = addr.find('./fqdn')
                if fqdn is not None and fqdn.text:
                    value_key = f"fqdn:{fqdn.text}"
                    logger.debug(f"Address '{name}' has fqdn value: {fqdn.text}")
                
                ip_range = addr.find('./ip-range')
                if ip_range is not None and ip_range.text:
                    value_key = f"ip-range:{ip_range.text}"
                    logger.debug(f"Address '{name}' has ip-range value: {ip_range.text}")
                
                if value_key:
                    if value_key not in by_value:
                        by_value[value_key] = []
                    by_value[value_key].append((name, addr))
                else:
                    logger.warning(f"Address object '{name}' has no recognizable value, skipping")
            
            except Exception as e:
                logger.error(f"Error processing address object: {e}", exc_info=True)
                continue
        
        # Find duplicates (groups with more than one object)
        duplicates = {k: v for k, v in by_value.items() if len(v) > 1}
        
        duplicate_count = sum(len(v) - 1 for v in duplicates.values())
        unique_values_count = len(duplicates)
        
        if duplicates:
            logger.info(f"Found {duplicate_count} duplicate objects across {unique_values_count} unique values")
            for value, objects in duplicates.items():
                names = [name for name, _ in objects]
                logger.debug(f"Duplicates with value '{value}': {', '.join(names)}")
        else:
            logger.info("No duplicate address objects found")
        
        # If reference tracking is enabled, find all references
        references = {}
        if reference_tracking and duplicates:
            logger.info("Reference tracking enabled, looking for references to duplicate objects")
            try:
                references = self._find_references('address')
                reference_count = sum(len(refs) for refs in references.values())
                logger.info(f"Found {reference_count} references to objects")
            except Exception as e:
                logger.error(f"Error finding references: {e}", exc_info=True)
        
        return duplicates, references
        
    def find_duplicate_services(self, reference_tracking=True):
        """
        Find duplicate service objects based on their values.
        
        Args:
            reference_tracking: Whether to track references to objects (default: True)
            
        Returns:
            Tuple of (duplicates, references):
                - duplicates: Dictionary mapping values to lists of (name, element) tuples
                - references: Dictionary mapping object names to lists of references
        """
        logger.info("Finding duplicate service objects")
        logger.debug(f"Reference tracking: {reference_tracking}")
        
        # Get all service objects
        try:
            service_xpath = get_object_xpath('service', self.device_type, self.context_type, 
                                           self.version, **self.context_kwargs)
            
            logger.debug(f"Retrieving service objects using XPath: {service_xpath}")
            services = xpath_search(self.tree, service_xpath)
            
            logger.info(f"Found {len(services)} service objects to analyze")
            
        except Exception as e:
            logger.error(f"Error retrieving service objects: {e}", exc_info=True)
            return {}, {}
        
        # Group by value
        by_value = {}
        
        logger.debug("Grouping service objects by value")
        for svc in services:
            try:
                name = svc.get('name', '')
                if not name:
                    logger.warning(f"Skipping service object with no name attribute")
                    continue
                
                # Build a value key based on protocol, ports, and source ports
                protocol = svc.find('./protocol')
                if protocol is None:
                    logger.warning(f"Service '{name}' has no protocol element, skipping")
                    continue
                    
                protocol_type = None
                port = None
                source_port = None
                
                # Check TCP
                tcp = protocol.find('./tcp')
                if tcp is not None:
                    protocol_type = 'tcp'
                    port_elem = tcp.find('./port')
                    if port_elem is not None and port_elem.text:
                        port = port_elem.text
                    source_port_elem = tcp.find('./source-port')
                    if source_port_elem is not None and source_port_elem.text:
                        source_port = source_port_elem.text
                
                # Check UDP
                udp = protocol.find('./udp')
                if udp is not None:
                    protocol_type = 'udp'
                    port_elem = udp.find('./port')
                    if port_elem is not None and port_elem.text:
                        port = port_elem.text
                    source_port_elem = udp.find('./source-port')
                    if source_port_elem is not None and source_port_elem.text:
                        source_port = source_port_elem.text
                
                # Check other protocols (e.g., icmp, sctp)
                if protocol_type is None:
                    for proto_type in ['icmp', 'sctp', 'icmp6']:
                        proto_elem = protocol.find(f'./{proto_type}')
                        if proto_elem is not None:
                            protocol_type = proto_type
                            # Handle protocol-specific attributes
                            if proto_type in ['icmp', 'icmp6']:
                                type_elem = proto_elem.find('./type')
                                code_elem = proto_elem.find('./code')
                                if type_elem is not None and type_elem.text:
                                    port = f"type:{type_elem.text}"
                                if code_elem is not None and code_elem.text:
                                    source_port = f"code:{code_elem.text}"
                            break
                
                if protocol_type:
                    value_parts = [f"protocol:{protocol_type}"]
                    if port:
                        value_parts.append(f"port:{port}")
                    if source_port:
                        value_parts.append(f"source-port:{source_port}")
                    
                    value_key = ";".join(value_parts)
                    
                    if value_key not in by_value:
                        by_value[value_key] = []
                    by_value[value_key].append((name, svc))
                    logger.debug(f"Service '{name}' has value: {value_key}")
                else:
                    logger.warning(f"Service '{name}' has no recognizable protocol, skipping")
            
            except Exception as e:
                logger.error(f"Error processing service object: {e}", exc_info=True)
                continue
        
        # Find duplicates (groups with more than one object)
        duplicates = {k: v for k, v in by_value.items() if len(v) > 1}
        
        duplicate_count = sum(len(v) - 1 for v in duplicates.values())
        unique_values_count = len(duplicates)
        
        if duplicates:
            logger.info(f"Found {duplicate_count} duplicate service objects across {unique_values_count} unique values")
            for value, objects in duplicates.items():
                names = [name for name, _ in objects]
                logger.debug(f"Duplicates with value '{value}': {', '.join(names)}")
        else:
            logger.info("No duplicate service objects found")
        
        # If reference tracking is enabled, find all references
        references = {}
        if reference_tracking and duplicates:
            logger.info("Reference tracking enabled, looking for references to service objects")
            try:
                references = self._find_references('service')
                reference_count = sum(len(refs) for refs in references.values())
                logger.info(f"Found {reference_count} references to service objects")
            except Exception as e:
                logger.error(f"Error finding references: {e}", exc_info=True)
        
        return duplicates, references
        
    def find_duplicate_tags(self, reference_tracking=True):
        """
        Find duplicate tag objects based on their values.
        
        Args:
            reference_tracking: Whether to track references to objects (default: True)
            
        Returns:
            Tuple of (duplicates, references):
                - duplicates: Dictionary mapping values to lists of (name, element) tuples
                - references: Dictionary mapping object names to lists of references
        """
        logger.info("Finding duplicate tag objects")
        logger.debug(f"Reference tracking: {reference_tracking}")
        
        # Get all tag objects
        try:
            tag_xpath = get_object_xpath('tag', self.device_type, self.context_type, 
                                       self.version, **self.context_kwargs)
            
            logger.debug(f"Retrieving tag objects using XPath: {tag_xpath}")
            tags = xpath_search(self.tree, tag_xpath)
            
            logger.info(f"Found {len(tags)} tag objects to analyze")
            
        except Exception as e:
            logger.error(f"Error retrieving tag objects: {e}", exc_info=True)
            return {}, {}
        
        # Group by value (color and comments)
        by_value = {}
        
        logger.debug("Grouping tag objects by value")
        for tag in tags:
            try:
                name = tag.get('name', '')
                if not name:
                    logger.warning(f"Skipping tag object with no name attribute")
                    continue
                
                # Build a value key based on color and comments
                color = tag.find('./color')
                color_value = color.text if color is not None and color.text else 'none'
                
                comments = tag.find('./comments')
                comments_value = comments.text if comments is not None and comments.text else ''
                
                value_key = f"color:{color_value};comments:{comments_value}"
                
                if value_key not in by_value:
                    by_value[value_key] = []
                by_value[value_key].append((name, tag))
                logger.debug(f"Tag '{name}' has value: {value_key}")
            
            except Exception as e:
                logger.error(f"Error processing tag object: {e}", exc_info=True)
                continue
        
        # Find duplicates (groups with more than one object)
        duplicates = {k: v for k, v in by_value.items() if len(v) > 1}
        
        duplicate_count = sum(len(v) - 1 for v in duplicates.values())
        unique_values_count = len(duplicates)
        
        if duplicates:
            logger.info(f"Found {duplicate_count} duplicate tag objects across {unique_values_count} unique values")
            for value, objects in duplicates.items():
                names = [name for name, _ in objects]
                logger.debug(f"Duplicates with value '{value}': {', '.join(names)}")
        else:
            logger.info("No duplicate tag objects found")
        
        # If reference tracking is enabled, find all references
        references = {}
        if reference_tracking and duplicates:
            logger.info("Reference tracking enabled, looking for references to tag objects")
            try:
                references = self._find_references('tag')
                reference_count = sum(len(refs) for refs in references.values())
                logger.info(f"Found {reference_count} references to tag objects")
            except Exception as e:
                logger.error(f"Error finding references: {e}", exc_info=True)
        
        return duplicates, references
    
    def _find_references(self, object_type='address'):
        """
        Find all references to objects in the configuration.
        
        Args:
            object_type: Type of object to find references for (address, service, tag)
            
        Returns:
            Dictionary mapping object names to lists of (xpath, element) tuples
        """
        logger.debug(f"Finding references to {object_type} objects")
        references = {}
        
        if object_type == 'address':
            # Search for references in address groups
            try:
                logger.debug("Searching for references in address groups")
                group_xpath = get_object_xpath('address_group', self.device_type, self.context_type, 
                                             self.version, **self.context_kwargs)
                
                address_groups = xpath_search(self.tree, group_xpath)
                logger.debug(f"Found {len(address_groups)} address groups to check")
                
                for group in address_groups:
                    group_name = group.get('name', 'unknown')
                    members = group.xpath('.//member')
                    
                    for member in members:
                        if member.text:
                            member_name = member.text
                            if member_name not in references:
                                references[member_name] = []
                            
                            ref_path = f"address-group:{group_name}"
                            references[member_name].append((ref_path, member))
                            logger.debug(f"Found reference to '{member_name}' in address group '{group_name}'")
            
            except Exception as e:
                logger.error(f"Error finding references in address groups: {e}", exc_info=True)
            
            # Search for references in security policies
            try:
                logger.debug("Searching for references in security policies")
                # Determine security policy XPath based on device type
                if self.device_type.lower() == 'panorama':
                    policy_paths = [
                        ('pre-rulebase/security/rules/entry', 'pre-security'),
                        ('post-rulebase/security/rules/entry', 'post-security')
                    ]
                else:
                    policy_paths = [
                        ('rulebase/security/rules/entry', 'security')
                    ]
                
                # Get context base path
                from .xpath_resolver import get_context_xpath
                base_path = get_context_xpath(self.device_type, self.context_type, 
                                            self.version, **self.context_kwargs)
                
                # Check each policy path
                for path_suffix, path_name in policy_paths:
                    policy_xpath = f"{base_path}/{path_suffix}"
                    policies = xpath_search(self.tree, policy_xpath)
                    
                    logger.debug(f"Found {len(policies)} {path_name} policies to check")
                    
                    # Check source and destination in each policy
                    for policy in policies:
                        policy_name = policy.get('name', 'unknown')
                        
                        # Check source addresses
                        for source in policy.xpath('./source/member'):
                            if source.text and source.text != 'any':
                                source_name = source.text
                                if source_name not in references:
                                    references[source_name] = []
                                
                                ref_path = f"{path_name}:{policy_name}:source"
                                references[source_name].append((ref_path, source))
                                logger.debug(f"Found reference to '{source_name}' in policy '{policy_name}' (source)")
                        
                        # Check destination addresses
                        for dest in policy.xpath('./destination/member'):
                            if dest.text and dest.text != 'any':
                                dest_name = dest.text
                                if dest_name not in references:
                                    references[dest_name] = []
                                
                                ref_path = f"{path_name}:{policy_name}:destination"
                                references[dest_name].append((ref_path, dest))
                                logger.debug(f"Found reference to '{dest_name}' in policy '{policy_name}' (destination)")
                
                # Check NAT policies as well
                if self.device_type.lower() == 'panorama':
                    nat_paths = [
                        ('pre-rulebase/nat/rules/entry', 'pre-nat'),
                        ('post-rulebase/nat/rules/entry', 'post-nat')
                    ]
                else:
                    nat_paths = [
                        ('rulebase/nat/rules/entry', 'nat')
                    ]
                
                for path_suffix, path_name in nat_paths:
                    policy_xpath = f"{base_path}/{path_suffix}"
                    policies = xpath_search(self.tree, policy_xpath)
                    
                    logger.debug(f"Found {len(policies)} {path_name} policies to check")
                    
                    for policy in policies:
                        policy_name = policy.get('name', 'unknown')
                        
                        # Check source and destination translation addresses
                        for src_elem in policy.xpath('.//source-translation//translated-address'):
                            if src_elem.text and src_elem.text != 'any':
                                if src_elem.text not in references:
                                    references[src_elem.text] = []
                                ref_path = f"{path_name}:{policy_name}:source-translation"
                                references[src_elem.text].append((ref_path, src_elem))
                        
                        for dst_elem in policy.xpath('.//destination-translation/translated-address'):
                            if dst_elem.text and dst_elem.text != 'any':
                                if dst_elem.text not in references:
                                    references[dst_elem.text] = []
                                ref_path = f"{path_name}:{policy_name}:destination-translation"
                                references[dst_elem.text].append((ref_path, dst_elem))
            
            except Exception as e:
                logger.error(f"Error finding references in security policies: {e}", exc_info=True)
                
        elif object_type == 'service':
            # Search for references in service groups
            try:
                logger.debug("Searching for references in service groups")
                group_xpath = get_object_xpath('service_group', self.device_type, self.context_type, 
                                             self.version, **self.context_kwargs)
                
                service_groups = xpath_search(self.tree, group_xpath)
                logger.debug(f"Found {len(service_groups)} service groups to check")
                
                for group in service_groups:
                    group_name = group.get('name', 'unknown')
                    members = group.xpath('.//member')
                    
                    for member in members:
                        if member.text:
                            member_name = member.text
                            if member_name not in references:
                                references[member_name] = []
                            
                            ref_path = f"service-group:{group_name}"
                            references[member_name].append((ref_path, member))
                            logger.debug(f"Found reference to '{member_name}' in service group '{group_name}'")
            
            except Exception as e:
                logger.error(f"Error finding references in service groups: {e}", exc_info=True)
                
            # Search for references in security policies
            try:
                logger.debug("Searching for references in security policies")
                # Determine security policy XPath based on device type
                if self.device_type.lower() == 'panorama':
                    policy_paths = [
                        ('pre-rulebase/security/rules/entry', 'pre-security'),
                        ('post-rulebase/security/rules/entry', 'post-security')
                    ]
                else:
                    policy_paths = [
                        ('rulebase/security/rules/entry', 'security')
                    ]
                
                # Get context base path
                from .xpath_resolver import get_context_xpath
                base_path = get_context_xpath(self.device_type, self.context_type, 
                                            self.version, **self.context_kwargs)
                
                # Check each policy path
                for path_suffix, path_name in policy_paths:
                    policy_xpath = f"{base_path}/{path_suffix}"
                    policies = xpath_search(self.tree, policy_xpath)
                    
                    logger.debug(f"Found {len(policies)} {path_name} policies to check")
                    
                    # Check service in each policy
                    for policy in policies:
                        policy_name = policy.get('name', 'unknown')
                        
                        # Check service field
                        for service in policy.xpath('./service/member'):
                            if service.text and service.text != 'any':
                                service_name = service.text
                                if service_name not in references:
                                    references[service_name] = []
                                
                                ref_path = f"{path_name}:{policy_name}:service"
                                references[service_name].append((ref_path, service))
                                logger.debug(f"Found reference to '{service_name}' in policy '{policy_name}' (service)")
                
                # Check NAT policies as well
                if self.device_type.lower() == 'panorama':
                    nat_paths = [
                        ('pre-rulebase/nat/rules/entry', 'pre-nat'),
                        ('post-rulebase/nat/rules/entry', 'post-nat')
                    ]
                else:
                    nat_paths = [
                        ('rulebase/nat/rules/entry', 'nat')
                    ]
                
                for path_suffix, path_name in nat_paths:
                    policy_xpath = f"{base_path}/{path_suffix}"
                    policies = xpath_search(self.tree, policy_xpath)
                    
                    logger.debug(f"Found {len(policies)} {path_name} policies to check")
                    
                    for policy in policies:
                        policy_name = policy.get('name', 'unknown')
                        
                        # Check service and translated service
                        for svc_elem in policy.xpath('.//service'):
                            if svc_elem.text and svc_elem.text != 'any':
                                if svc_elem.text not in references:
                                    references[svc_elem.text] = []
                                ref_path = f"{path_name}:{policy_name}:service"
                                references[svc_elem.text].append((ref_path, svc_elem))
                        
                        for svc_elem in policy.xpath('.//destination-translation/translated-service'):
                            if svc_elem.text and svc_elem.text != 'any':
                                if svc_elem.text not in references:
                                    references[svc_elem.text] = []
                                ref_path = f"{path_name}:{policy_name}:translated-service"
                                references[svc_elem.text].append((ref_path, svc_elem))
            
            except Exception as e:
                logger.error(f"Error finding references to services in policies: {e}", exc_info=True)
                
        elif object_type == 'tag':
            # Find references to tags in various objects
            object_types = [
                ('address', 'address'),
                ('address_group', 'address group'),
                ('service', 'service'),
                ('service_group', 'service group')
            ]
            
            for obj_type, obj_desc in object_types:
                try:
                    logger.debug(f"Searching for tag references in {obj_desc} objects")
                    obj_xpath = get_object_xpath(obj_type, self.device_type, self.context_type, 
                                                self.version, **self.context_kwargs)
                    
                    objects = xpath_search(self.tree, obj_xpath)
                    logger.debug(f"Found {len(objects)} {obj_desc} objects to check")
                    
                    for obj in objects:
                        obj_name = obj.get('name', 'unknown')
                        tag_elements = obj.xpath('.//tag/member')
                        
                        for tag_elem in tag_elements:
                            if tag_elem.text:
                                tag_name = tag_elem.text
                                if tag_name not in references:
                                    references[tag_name] = []
                                
                                ref_path = f"{obj_desc}:{obj_name}:tag"
                                references[tag_name].append((ref_path, tag_elem))
                                logger.debug(f"Found reference to tag '{tag_name}' in {obj_desc} '{obj_name}'")
                
                except Exception as e:
                    logger.error(f"Error finding tag references in {obj_desc} objects: {e}", exc_info=True)
            
            # Check policies for tag references
            try:
                logger.debug("Searching for tag references in security policies")
                from .xpath_resolver import get_context_xpath
                base_path = get_context_xpath(self.device_type, self.context_type, 
                                            self.version, **self.context_kwargs)
                
                # Determine security policy XPath based on device type
                if self.device_type.lower() == 'panorama':
                    policy_paths = [
                        ('pre-rulebase/security/rules/entry', 'pre-security'),
                        ('post-rulebase/security/rules/entry', 'post-security')
                    ]
                else:
                    policy_paths = [
                        ('rulebase/security/rules/entry', 'security')
                    ]
                
                for path_suffix, path_name in policy_paths:
                    policy_xpath = f"{base_path}/{path_suffix}"
                    policies = xpath_search(self.tree, policy_xpath)
                    
                    logger.debug(f"Found {len(policies)} {path_name} policies to check for tags")
                    
                    for policy in policies:
                        policy_name = policy.get('name', 'unknown')
                        
                        # Check tags in the policy
                        tag_elements = policy.xpath('.//tag/member')
                        for tag_elem in tag_elements:
                            if tag_elem.text:
                                tag_name = tag_elem.text
                                if tag_name not in references:
                                    references[tag_name] = []
                                
                                ref_path = f"{path_name}:{policy_name}:tag"
                                references[tag_name].append((ref_path, tag_elem))
                                logger.debug(f"Found reference to tag '{tag_name}' in policy '{policy_name}'")
            
            except Exception as e:
                logger.error(f"Error finding tag references in policies: {e}", exc_info=True)
        
        # Log summary of references found
        ref_count = sum(len(refs) for refs in references.values())
        object_count = len(references)
        logger.info(f"Found {ref_count} references to {object_count} distinct {object_type} objects")
        
        return references
    
    def merge_duplicates(self, duplicates, references, primary_name_strategy='first'):
        """
        Merge duplicate objects, keeping one and updating references.
        
        Args:
            duplicates: Dictionary of duplicate objects (from find_duplicate_addresses)
            references: Dictionary of references (from find_duplicate_addresses)
            primary_name_strategy: Strategy for choosing primary object 
                                ('first', 'shortest', 'longest', 'alphabetical')
            
        Returns:
            List of changes made (operation, name, element)
        """
        logger.info(f"Merging duplicate objects using strategy: {primary_name_strategy}")
        changes = []
        
        # Track processed objects to handle circular references
        processed_objects = set()
        
        # Validate inputs
        if not duplicates:
            logger.warning("No duplicates provided, nothing to merge")
            return changes
        
        duplicate_sets = len(duplicates)
        duplicate_count = sum(len(objects) - 1 for objects in duplicates.values())
        logger.info(f"Processing {duplicate_count} duplicates across {duplicate_sets} unique values")
        
        # Sort duplicate sets by dependency order
        # This helps ensure we process independent objects before their dependents
        dependency_order = self._sort_by_dependencies(duplicates, references)
        
        for value_key in dependency_order:
            objects = duplicates.get(value_key, [])
            logger.debug(f"Processing duplicates with value: {value_key}")
            
            # Skip if there's only one object
            if len(objects) <= 1:
                logger.warning(f"Skipping value {value_key} with only {len(objects)} object")
                continue
            
            # Determine which object to keep
            try:
                primary = self._select_primary_object(objects, primary_name_strategy)
                primary_name, primary_elem = primary
                
                # Skip if we've already processed this primary
                if primary_name in processed_objects:
                    logger.warning(f"Object {primary_name} already processed, skipping to avoid circular references")
                    continue
                    
                processed_objects.add(primary_name)
                
                logger.info(f"Selected primary object '{primary_name}' for value {value_key}")
                
                # Process each duplicate
                for name, obj in objects:
                    # Skip the primary object
                    if name == primary_name:
                        continue
                        
                    # Skip if we've already processed this object
                    if name in processed_objects:
                        logger.warning(f"Object {name} already processed, skipping to avoid circular references")
                        continue
                        
                    processed_objects.add(name)
                    logger.debug(f"Processing duplicate: {name}")
                    
                    # Update references to this object
                    if name in references:
                        ref_count = len(references[name])
                        logger.info(f"Updating {ref_count} references to '{name}'")
                        
                        for ref_path, ref_elem in references[name]:
                            try:
                                # Update the reference to point to primary_name
                                old_text = ref_elem.text
                                ref_elem.text = primary_name
                                changes.append(('update_reference', f"{ref_path}: {old_text} -> {primary_name}", ref_elem))
                                logger.debug(f"Updated reference in {ref_path}: {old_text} -> {primary_name}")
                            except Exception as e:
                                logger.error(f"Error updating reference to '{name}' in {ref_path}: {str(e)}")
                    else:
                        logger.debug(f"No references found for '{name}'")
                    
                    # Queue this object for deletion
                    logger.debug(f"Queueing object '{name}' for deletion")
                    changes.append(('delete', name, obj))
            
            except Exception as e:
                logger.error(f"Error processing duplicates for value {value_key}: {str(e)}")
                continue
    
        # Log changes summary
        delete_count = sum(1 for op, _, _ in changes if op == 'delete')
        ref_update_count = sum(1 for op, _, _ in changes if op == 'update_reference')
        
        logger.info(f"Changes to be made: {delete_count} objects to delete, {ref_update_count} references to update")
        
        return changes
    
    def _select_primary_object(self, objects, strategy):
        """
        Select the primary object to keep based on the specified strategy.
        
        Args:
            objects: List of (name, element) tuples
            strategy: Selection strategy ('first', 'shortest', etc.)
            
        Returns:
            Tuple of (name, element) for the selected primary object
        """
        logger.debug(f"Selecting primary object using strategy: {strategy}")
        
        if not objects:
            logger.error("No objects provided for primary selection")
            raise ValueError("No objects provided")
        
        if strategy == 'first':
            logger.debug("Using 'first' strategy - selecting first object")
            return objects[0]
        
        elif strategy == 'shortest':
            logger.debug("Using 'shortest' strategy - selecting object with shortest name")
            return min(objects, key=lambda x: len(x[0]))
        
        elif strategy == 'longest':
            logger.debug("Using 'longest' strategy - selecting object with longest name")
            return max(objects, key=lambda x: len(x[0]))
        
        elif strategy == 'alphabetical':
            logger.debug("Using 'alphabetical' strategy - selecting object with first alphabetical name")
            return min(objects, key=lambda x: x[0])
        
        else:
            logger.warning(f"Unknown strategy: {strategy}, falling back to 'first'")
            return objects[0]
        
    def _sort_by_dependencies(self, duplicates, references):
        """
        Sort duplicate sets based on their dependencies to avoid circular reference issues.
        
        Args:
            duplicates: Dictionary of duplicate objects
            references: Dictionary of references
            
        Returns:
            List of value_keys in dependency order
        """
        dependency_graph = {}
        value_key_to_names = {}
        
        # Build mapping of value_keys to object names
        for value_key, objects in duplicates.items():
            names = [name for name, _ in objects]
            value_key_to_names[value_key] = set(names)
            dependency_graph[value_key] = set()
        
        # Build dependency graph
        for value_key, objects in duplicates.items():
            names = value_key_to_names[value_key]
            
            # Find dependencies
            for dependent_value_key, dependent_names in value_key_to_names.items():
                if value_key == dependent_value_key:
                    continue
                
                # Check if any object in this set references any object in the dependent set
                for name in names:
                    if name in references:
                        for ref_path, _ in references[name]:
                            for dependent_name in dependent_names:
                                if dependent_name in ref_path:
                                    # This set depends on the dependent set
                                    dependency_graph[value_key].add(dependent_value_key)
        
        # Perform topological sort
        result = []
        visited = set()
        temp_mark = set()
        
        def visit(node):
            if node in visited:
                return
            if node in temp_mark:
                # Circular dependency detected, but we'll continue
                logger.warning(f"Circular dependency detected for value {node}")
                return
            
            temp_mark.add(node)
            
            for dep in dependency_graph[node]:
                visit(dep)
            
            temp_mark.remove(node)
            visited.add(node)
            result.append(node)
        
        for node in dependency_graph:
            if node not in visited:
                visit(node)
        
        # Return in reverse order (least dependent first)
        return result[::-1]