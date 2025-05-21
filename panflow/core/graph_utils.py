"""
Graph utilities for PANFlow.

This module provides functions to build and work with a graph representation of a PAN-OS configuration.
"""

import logging
import networkx as nx
from typing import Dict, Any, Optional, List
from lxml import etree

# Initialize logger
logger = logging.getLogger("panflow")


def get_xpath_element_value(elem, xpath):
    """Get the text value from an XPath."""
    elements = elem.xpath(xpath)
    if elements and hasattr(elements[0], "text"):
        return elements[0].text
    return None


class ConfigGraph:
    """Graph representation of a PAN-OS configuration."""

    def __init__(self, device_type=None, context_type=None, **context_kwargs):
        """
        Initialize a ConfigGraph.
        
        Args:
            device_type: Type of device ("firewall" or "panorama")
            context_type: Type of context ("shared", "device_group", "vsys")
            **context_kwargs: Additional context parameters (device_group, vsys, etc.)
        """
        self.graph = nx.DiGraph()
        self.root_node = None
        self.device_type = device_type
        self.context_type = context_type
        self.context_kwargs = context_kwargs

    def build_from_xml(self, xml_root: etree._Element):
        """
        Build a graph representation from an XML configuration.

        Args:
            xml_root: The root element of the PAN-OS XML configuration
        """
        self.graph.clear()
        self.root_node = "config_root"
        self.graph.add_node(self.root_node, type="root", xml=xml_root)
        
        # Store context info in the root node for reference
        if self.device_type:
            self.graph.nodes[self.root_node]["device_type"] = self.device_type
        if self.context_type:
            self.graph.nodes[self.root_node]["context_type"] = self.context_type
        for key, value in self.context_kwargs.items():
            self.graph.nodes[self.root_node][key] = value

        # Process address objects
        self._process_address_objects(xml_root)

        # Process address groups and their members
        self._process_address_groups(xml_root)

        # Process service objects
        self._process_service_objects(xml_root)

        # Process service groups and their members
        self._process_service_groups(xml_root)

        # Process security rules and their references
        self._process_security_rules(xml_root)

        # Process NAT rules and their references
        self._process_nat_rules(xml_root)

        logger.info(
            f"Built configuration graph with {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges"
        )

    def _process_address_objects(self, xml_root: etree._Element):
        """Process all address objects in the configuration."""
        # Find all address objects in the config, respecting context
        from panflow.core.xpath_resolver import get_object_xpath
        
        address_xpath = ".//address/entry"
        if self.device_type and self.context_type:
            try:
                # Get context-aware xpath for addresses
                address_xpath = get_object_xpath(
                    "address", 
                    self.device_type, 
                    self.context_type, 
                    "10.1",  # Use a default version if not provided
                    **self.context_kwargs
                )
                logger.debug(f"Using context-specific address xpath: {address_xpath}")
            except Exception as e:
                logger.warning(f"Failed to get context-specific xpath: {e}. Using default.")
                
        for addr in xml_root.xpath(address_xpath):
            name = addr.get("name")
            if not name:
                continue

            node_id = f"address:{name}"

            # Extract address properties
            props = {"type": "address", "name": name, "xml": addr}

            # Add specific address type and value
            for addr_type in ["ip-netmask", "ip-range", "fqdn"]:
                value = get_xpath_element_value(addr, f"./{addr_type}")
                if value:
                    props["addr_type"] = addr_type
                    props["value"] = value
                    break

            # Determine device group context by looking at the XML path
            if self.device_type == "panorama":
                device_group = self._get_device_group_from_element(addr)
                if device_group:
                    props["device_group"] = device_group
                else:
                    props["device_group"] = "shared"

            # Add node to graph
            self.graph.add_node(node_id, **props)
            self.graph.add_edge(self.root_node, node_id, relation="contains")

    def _process_address_groups(self, xml_root: etree._Element):
        """Process all address groups and their members."""
        # Find all address groups in the config, respecting context
        from panflow.core.xpath_resolver import get_object_xpath
        
        group_xpath = ".//address-group/entry"
        if self.device_type and self.context_type:
            try:
                # Get context-aware xpath for address groups
                group_xpath = get_object_xpath(
                    "address-group", 
                    self.device_type, 
                    self.context_type, 
                    "10.1",  # Use a default version if not provided
                    **self.context_kwargs
                )
                logger.debug(f"Using context-specific address-group xpath: {group_xpath}")
            except Exception as e:
                logger.warning(f"Failed to get context-specific xpath: {e}. Using default.")
                
        for group in xml_root.xpath(group_xpath):
            name = group.get("name")
            if not name:
                continue

            node_id = f"address-group:{name}"

            # Extract group properties
            props = {"type": "address-group", "name": name, "xml": group}
            
            # Determine device group context by looking at the XML path
            if self.device_type == "panorama":
                device_group = self._get_device_group_from_element(group)
                if device_group:
                    props["device_group"] = device_group
                else:
                    props["device_group"] = "shared"

            # Add the group node
            self.graph.add_node(node_id, **props)
            self.graph.add_edge(self.root_node, node_id, relation="contains")

            # Process static members
            members_xpath = "./static/member"
            for member in group.xpath(members_xpath):
                member_name = member.text
                if not member_name:
                    continue

                member_id = f"address:{member_name}"

                # If member doesn't exist as node yet (referenced but not defined),
                # add a placeholder node
                if member_id not in self.graph:
                    self.graph.add_node(
                        member_id, type="address", name=member_name, placeholder=True
                    )
                    logger.warning(f"Referenced undefined address object: {member_name}")

                # Add the membership edge
                self.graph.add_edge(node_id, member_id, relation="contains")

    def _process_service_objects(self, xml_root: etree._Element):
        """Process all service objects in the configuration."""
        # Find all service objects, respecting context
        from panflow.core.xpath_resolver import get_object_xpath
        
        service_xpath = ".//service/entry"
        if self.device_type and self.context_type:
            try:
                # Get context-aware xpath for services
                service_xpath = get_object_xpath(
                    "service", 
                    self.device_type, 
                    self.context_type, 
                    "10.1",  # Use a default version if not provided
                    **self.context_kwargs
                )
                logger.debug(f"Using context-specific service xpath: {service_xpath}")
            except Exception as e:
                logger.warning(f"Failed to get context-specific xpath: {e}. Using default.")
                
        for svc in xml_root.xpath(service_xpath):
            name = svc.get("name")
            if not name:
                continue

            node_id = f"service:{name}"

            # Extract service properties
            props = {"type": "service", "name": name, "xml": svc}

            # Add protocol specific info
            for protocol in ["tcp", "udp"]:
                port = get_xpath_element_value(svc, f"./protocol/{protocol}/port")
                if port:
                    props["protocol"] = protocol
                    props["port"] = port
                    break

            # Determine device group context by looking at the XML path
            if self.device_type == "panorama":
                device_group = self._get_device_group_from_element(svc)
                if device_group:
                    props["device_group"] = device_group
                else:
                    props["device_group"] = "shared"

            # Add node to graph
            self.graph.add_node(node_id, **props)
            self.graph.add_edge(self.root_node, node_id, relation="contains")

    def _process_service_groups(self, xml_root: etree._Element):
        """Process all service groups and their members."""
        # Find all service groups, respecting context
        from panflow.core.xpath_resolver import get_object_xpath
        
        group_xpath = ".//service-group/entry"
        if self.device_type and self.context_type:
            try:
                # Get context-aware xpath for service groups
                group_xpath = get_object_xpath(
                    "service-group", 
                    self.device_type, 
                    self.context_type, 
                    "10.1",  # Use a default version if not provided
                    **self.context_kwargs
                )
                logger.debug(f"Using context-specific service-group xpath: {group_xpath}")
            except Exception as e:
                logger.warning(f"Failed to get context-specific xpath: {e}. Using default.")
                
        for group in xml_root.xpath(group_xpath):
            name = group.get("name")
            if not name:
                continue

            node_id = f"service-group:{name}"

            # Extract group properties
            props = {"type": "service-group", "name": name, "xml": group}
            
            # Determine device group context by looking at the XML path
            if self.device_type == "panorama":
                device_group = self._get_device_group_from_element(group)
                if device_group:
                    props["device_group"] = device_group
                else:
                    props["device_group"] = "shared"

            # Add the group node
            self.graph.add_node(node_id, **props)
            self.graph.add_edge(self.root_node, node_id, relation="contains")

            # Process members
            members_xpath = "./members/member"
            for member in group.xpath(members_xpath):
                member_name = member.text
                if not member_name:
                    continue

                member_id = f"service:{member_name}"

                # If member doesn't exist yet (referenced but not defined),
                # add a placeholder node
                if member_id not in self.graph:
                    self.graph.add_node(
                        member_id, type="service", name=member_name, placeholder=True
                    )
                    logger.warning(f"Referenced undefined service: {member_name}")

                # Add the membership edge
                self.graph.add_edge(node_id, member_id, relation="contains")

    def _process_security_rules(self, xml_root: etree._Element):
        """Process all security rules and their object references."""
        # Find all security rules, respecting context
        from panflow.core.xpath_resolver import get_policy_xpath
        
        # Start with a default path
        rules_xpath = ".//security/rules/entry"
        
        # Special handling for Panorama device groups
        device_group = None
        if self.device_type == "panorama" and self.context_type == "device_group":
            device_group = self.context_kwargs.get("device_group")
            logger.debug(f"Processing security rules for device group: {device_group}")
        
        if self.device_type and self.context_type:
            try:
                # For Panorama, use the correct policy type based on context
                policy_type = "security_pre_rules" if self.device_type == "panorama" else "security_rules"
                
                # Get context-aware xpath for security rules
                rules_xpath = get_policy_xpath(
                    policy_type, 
                    self.device_type, 
                    self.context_type, 
                    "10.1",  # Use a default version if not provided
                    **self.context_kwargs
                )
                
                # Add extensive debug logging
                logger.debug(f"Device type: {self.device_type}, Context type: {self.context_type}")
                logger.debug(f"Context kwargs: {self.context_kwargs}")
                logger.debug(f"Using policy type: {policy_type}")
                logger.debug(f"Generated xpath: {rules_xpath}")
                logger.debug(f"Using context-specific security rules xpath: {rules_xpath}")
            except Exception as e:
                logger.warning(f"Failed to get context-specific xpath: {e}. Using default.")
        
        # For Panorama, process each device group separately if no specific device group context is provided
        # This happens when context_type is "shared" or None (auto-detect mode)
        if self.device_type == "panorama" and device_group is None and (self.context_type == "shared" or self.context_type is None):
            # Find all device groups
            device_groups = xml_root.xpath("/config/devices/entry/device-group/entry")
            for dg in device_groups:
                dg_name = dg.get("name")
                if not dg_name:
                    continue
                
                # Process security rules in this device group
                self._process_device_group_rules(dg, dg_name)
        else:
            # Process rules in the specified context
            # The XPath returns the 'rules' element, not the 'entry' elements
            # We need to append '/entry' to get the actual rule entries
            rule_entries_xpath = f"{rules_xpath}/entry"
            logger.debug(f"Looking for security rule entries with xpath: {rule_entries_xpath}")
            
            for rule in xml_root.xpath(rule_entries_xpath):
                name = rule.get("name")
                if not name:
                    logger.debug(f"Security rule has no name attribute: {etree.tostring(rule)[:100]}")
                    continue

                rule_id = f"security-rule:{name}"
                
                # Add the rule node with device group information if applicable
                props = {
                    "type": "security-rule", 
                    "labels": ["security_rule"],  # Add security_rule label for easier querying
                    "name": name, 
                    "xml": rule
                }
                
                # Include device group information for Panorama
                if device_group:
                    props["device_group"] = device_group
                
                self.graph.add_node(rule_id, **props)
                self.graph.add_edge(self.root_node, rule_id, relation="contains")
                
                # Process rule properties and references
                self._process_rule_properties(rule, rule_id)
    
    def _process_device_group_rules(self, device_group_elem, device_group_name):
        """Process security rules for a specific device group in Panorama."""
        # Find pre-rulebase security rules
        rules = device_group_elem.xpath("./pre-rulebase/security/rules/entry")
        
        for rule in rules:
            name = rule.get("name")
            if not name:
                continue
            
            rule_id = f"security-rule:{name}"
            
            # Add the rule node with device group information
            self.graph.add_node(
                rule_id, 
                type="security-rule", 
                name=name, 
                device_group=device_group_name,
                xml=rule
            )
            self.graph.add_edge(self.root_node, rule_id, relation="contains")
            
            # Process rule properties and references
            self._process_rule_properties(rule, rule_id)
        
        # Also find post-rulebase security rules
        post_rules = device_group_elem.xpath("./post-rulebase/security/rules/entry")
        
        for rule in post_rules:
            name = rule.get("name")
            if not name:
                continue
            
            rule_id = f"security-rule:{name}"
            
            # Add the rule node with device group information
            self.graph.add_node(
                rule_id, 
                type="security-rule", 
                name=name, 
                device_group=device_group_name,
                is_post_rule=True,
                xml=rule
            )
            self.graph.add_edge(self.root_node, rule_id, relation="contains")
            
            # Process rule properties and references
            self._process_rule_properties(rule, rule_id)
            
    def _process_rule_properties(self, rule, rule_id):
        """Process properties and references for a security rule."""
        # Process additional rule properties
        from_zone = rule.xpath("./from/member")
        if from_zone and from_zone[0].text:
            self.graph.nodes[rule_id]["from"] = from_zone[0].text

        to_zone = rule.xpath("./to/member")
        if to_zone and to_zone[0].text:
            self.graph.nodes[rule_id]["to"] = to_zone[0].text

        action = get_xpath_element_value(rule, "./action")
        if action:
            self.graph.nodes[rule_id]["action"] = action
            
        # Process disabled status
        disabled = get_xpath_element_value(rule, "./disabled")
        if disabled:
            self.graph.nodes[rule_id]["disabled"] = disabled

        # Process log settings if present
        log_setting = get_xpath_element_value(rule, "./log-setting")
        if log_setting:
            self.graph.nodes[rule_id]["log_setting"] = log_setting

        # Process source addresses
        self._process_rule_references(rule, rule_id, "source/member", "address", "uses-source")

        # Process destination addresses
        self._process_rule_references(
            rule, rule_id, "destination/member", "address", "uses-destination"
        )

        # Process service references
        self._process_rule_references(
            rule, rule_id, "service/member", "service", "uses-service"
        )

        # Process application references
        self._process_rule_references(
            rule, rule_id, "application/member", "application", "uses-application"
        )

    def _process_nat_rules(self, xml_root: etree._Element):
        """Process all NAT rules and their object references."""
        # Find all NAT rules, respecting context
        from panflow.core.xpath_resolver import get_policy_xpath
        
        # Start with a default path
        rules_xpath = ".//nat/rules/entry"
        
        # Special handling for Panorama device groups
        device_group = None
        if self.device_type == "panorama" and self.context_type == "device_group":
            device_group = self.context_kwargs.get("device_group")
            logger.debug(f"Processing NAT rules for device group: {device_group}")
        
        if self.device_type and self.context_type:
            try:
                # Get context-aware xpath for NAT rules
                rules_xpath = get_policy_xpath(
                    "nat_rules", 
                    self.device_type, 
                    self.context_type, 
                    "10.1",  # Use a default version if not provided
                    **self.context_kwargs
                )
                logger.debug(f"Using context-specific NAT rules xpath: {rules_xpath}")
            except Exception as e:
                logger.warning(f"Failed to get context-specific xpath: {e}. Using default.")
        
        # Process rules in the specified context
        # The XPath returns the 'rules' element, not the 'entry' elements
        # We need to append '/entry' to get the actual rule entries
        rule_entries_xpath = f"{rules_xpath}/entry"
        logger.debug(f"Looking for rule entries with xpath: {rule_entries_xpath}")
        
        for rule in xml_root.xpath(rule_entries_xpath):
            name = rule.get("name")
            if not name:
                logger.debug(f"Rule has no name attribute: {etree.tostring(rule)[:100]}")
                continue

            rule_id = f"nat-rule:{name}"
            
            # Add the rule node with device group information if applicable
            props = {
                "type": "nat-rule", 
                "labels": ["nat_rule"],  # Add nat_rule label for easier querying
                "name": name, 
                "xml": rule
            }
            
            # Include device group information for Panorama
            if device_group:
                props["device_group"] = device_group
            
            self.graph.add_node(rule_id, **props)
            self.graph.add_edge(self.root_node, rule_id, relation="contains")

            # Process source addresses
            self._process_rule_references(rule, rule_id, "source/member", "address", "uses-source")

            # Process destination addresses
            self._process_rule_references(
                rule, rule_id, "destination/member", "address", "uses-destination"
            )

            # Process service references
            self._process_rule_references(rule, rule_id, "service", "service", "uses-service")
            
        # For Panorama, also process NAT rules in device groups if not already targeting a specific group
        if self.device_type == "panorama" and device_group is None and (self.context_type == "shared" or self.context_type is None):
            # Find all device groups
            device_groups = xml_root.xpath("/config/devices/entry/device-group/entry")
            for dg in device_groups:
                dg_name = dg.get("name")
                if not dg_name:
                    continue
                
                # Process pre-rulebase NAT rules
                pre_rules = dg.xpath("./pre-rulebase/nat/rules/entry")
                for rule in pre_rules:
                    name = rule.get("name")
                    if not name:
                        continue
                    
                    rule_id = f"nat-rule:{name}"
                    
                    self.graph.add_node(
                        rule_id, 
                        type="nat-rule", 
                        name=name, 
                        device_group=dg_name,
                        xml=rule
                    )
                    self.graph.add_edge(self.root_node, rule_id, relation="contains")
                    
                    # Process source addresses
                    self._process_rule_references(rule, rule_id, "source/member", "address", "uses-source")

                    # Process destination addresses
                    self._process_rule_references(
                        rule, rule_id, "destination/member", "address", "uses-destination"
                    )

                    # Process service references
                    self._process_rule_references(rule, rule_id, "service", "service", "uses-service")
                
                # Process post-rulebase NAT rules
                post_rules = dg.xpath("./post-rulebase/nat/rules/entry")
                for rule in post_rules:
                    name = rule.get("name")
                    if not name:
                        continue
                    
                    rule_id = f"nat-rule:{name}"
                    
                    self.graph.add_node(
                        rule_id, 
                        type="nat-rule", 
                        name=name, 
                        device_group=dg_name,
                        is_post_rule=True,
                        xml=rule
                    )
                    self.graph.add_edge(self.root_node, rule_id, relation="contains")
                    
                    # Process source addresses
                    self._process_rule_references(rule, rule_id, "source/member", "address", "uses-source")

                    # Process destination addresses
                    self._process_rule_references(
                        rule, rule_id, "destination/member", "address", "uses-destination"
                    )

                    # Process service references
                    self._process_rule_references(rule, rule_id, "service", "service", "uses-service")

    def _process_rule_references(
        self, rule: etree._Element, rule_id: str, xpath: str, ref_type: str, relation: str
    ):
        """
        Process references from a rule to other objects.

        Args:
            rule: The rule XML element
            rule_id: The ID of the rule node in the graph
            xpath: XPath to find referenced object members
            ref_type: Type of the referenced objects
            relation: Type of relationship to create
        """
        for member in rule.xpath(xpath):
            member_name = member.text
            if not member_name:
                continue

            # Handle special values like "any"
            if member_name.lower() in ["any", "application-default"]:
                continue

            # Check if this could be an address group
            if ref_type == "address":
                address_group_id = f"address-group:{member_name}"
                if address_group_id in self.graph:
                    # This is an address group, not an address
                    self.graph.add_edge(rule_id, address_group_id, relation=relation)
                    continue

            member_id = f"{ref_type}:{member_name}"

            # If referenced object doesn't exist yet, add a placeholder
            if member_id not in self.graph:
                self.graph.add_node(member_id, type=ref_type, name=member_name, placeholder=True)
                logger.warning(f"Rule {rule_id} references undefined {ref_type}: {member_name}")

            # Add the reference edge
            self.graph.add_edge(rule_id, member_id, relation=relation)

    def query(self, query_str: str) -> List[Dict]:
        """
        Execute a graph query and return matching nodes.

        Args:
            query_str: The query string to execute

        Returns:
            List of matching nodes with their properties
        """
        # This is a placeholder for the actual query implementation
        # It will be replaced with a real query engine in the next iteration
        logger.warning("Graph query engine not fully implemented yet")
        return []

    def get_node_by_name(self, node_type: str, name: str) -> Optional[Dict]:
        """
        Get a node by its type and name.

        Args:
            node_type: Type of the node (e.g., "address", "service", etc.)
            name: Name of the node

        Returns:
            Node data if found, None otherwise
        """
        node_id = f"{node_type}:{name}"
        if node_id in self.graph:
            return self._node_to_dict(node_id)
        return None

    def get_references_to(self, node_type: str, name: str) -> List[Dict]:
        """
        Find all nodes that reference the specified node.

        Args:
            node_type: Type of the referenced node
            name: Name of the referenced node

        Returns:
            List of nodes referencing the specified node
        """
        node_id = f"{node_type}:{name}"
        if node_id not in self.graph:
            return []

        # Find all predecessors (nodes that have edges pointing to this node)
        refs = []
        for pred_id in self.graph.predecessors(node_id):
            # Skip the root node
            if pred_id == self.root_node:
                continue

            refs.append(self._node_to_dict(pred_id))

        return refs

    def get_referenced_by(self, node_type: str, name: str) -> List[Dict]:
        """
        Find all nodes that are referenced by the specified node.

        Args:
            node_type: Type of the node
            name: Name of the node

        Returns:
            List of nodes referenced by the specified node
        """
        node_id = f"{node_type}:{name}"
        if node_id not in self.graph:
            return []

        # Find all successors (nodes that this node has edges pointing to)
        refs = []
        for succ_id in self.graph.successors(node_id):
            refs.append(self._node_to_dict(succ_id))

        return refs

    def _node_to_dict(self, node_id: str) -> Dict:
        """Convert a node to a dictionary representation."""
        data = dict(self.graph.nodes[node_id])

        # Remove the XML element to make the result serializable
        if "xml" in data:
            del data["xml"]

        return data

    def _get_device_group_from_element(self, element: etree._Element) -> Optional[str]:
        """
        Determine the device group name from an XML element's path.
        
        Args:
            element: XML element to check
            
        Returns:
            Device group name if the element is in a device group, None if in shared
        """
        # Walk up the parent hierarchy to find device-group
        current = element
        while current is not None:
            if current.tag == "entry" and current.getparent() is not None:
                parent = current.getparent()
                if parent.tag == "device-group":
                    return current.get("name")
            current = current.getparent()
        
        return None