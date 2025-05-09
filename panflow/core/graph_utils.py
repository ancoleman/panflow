"""
Graph utilities for PAN-OS configurations.

This module provides utilities for representing and querying PAN-OS configurations
as a graph data structure. It allows for complex queries and relationship traversal
of configuration objects.
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple, Union
import networkx as nx
from lxml import etree
from panflow.core.xml.base import get_xpath_element_value


# Set up logging
logger = logging.getLogger(__name__)


class ConfigGraph:
    """
    Graph representation of a PAN-OS configuration.
    
    This class builds and maintains a directed graph of configuration objects
    where nodes represent objects and edges represent relationships between them.
    """
    
    def __init__(self):
        """Initialize an empty configuration graph."""
        self.graph = nx.DiGraph()
        self.root_node = None
        
    def build_from_xml(self, xml_root: etree._Element):
        """
        Build a graph representation from an XML configuration.
        
        Args:
            xml_root: The root element of the PAN-OS XML configuration
        """
        self.graph.clear()
        self.root_node = "config_root"
        self.graph.add_node(self.root_node, type="root", xml=xml_root)
        
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
        
        logger.info(f"Built configuration graph with {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges")
    
    def _process_address_objects(self, xml_root: etree._Element):
        """Process all address objects in the configuration."""
        # Find all address objects in the config
        address_xpath = ".//address/entry"
        for addr in xml_root.xpath(address_xpath):
            name = addr.get("name")
            if not name:
                continue
                
            node_id = f"address:{name}"
            
            # Extract address properties
            props = {
                "type": "address",
                "name": name,
                "xml": addr
            }
            
            # Add specific address type and value
            for addr_type in ["ip-netmask", "ip-range", "fqdn"]:
                value = get_xpath_element_value(addr, f"./{addr_type}")
                if value:
                    props["addr_type"] = addr_type
                    props["value"] = value
                    break
            
            # Add node to graph
            self.graph.add_node(node_id, **props)
            self.graph.add_edge(self.root_node, node_id, relation="contains")
    
    def _process_address_groups(self, xml_root: etree._Element):
        """Process all address groups and their members."""
        # Find all address groups in the config
        group_xpath = ".//address-group/entry"
        for group in xml_root.xpath(group_xpath):
            name = group.get("name")
            if not name:
                continue
                
            node_id = f"address-group:{name}"
            
            # Add the group node
            self.graph.add_node(node_id, type="address-group", name=name, xml=group)
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
                        member_id, 
                        type="address", 
                        name=member_name, 
                        placeholder=True
                    )
                    logger.warning(f"Referenced undefined address object: {member_name}")
                
                # Add the membership edge
                self.graph.add_edge(node_id, member_id, relation="contains")
    
    def _process_service_objects(self, xml_root: etree._Element):
        """Process all service objects in the configuration."""
        # Find all service objects
        service_xpath = ".//service/entry"
        for svc in xml_root.xpath(service_xpath):
            name = svc.get("name")
            if not name:
                continue
                
            node_id = f"service:{name}"
            
            # Extract service properties
            props = {
                "type": "service",
                "name": name,
                "xml": svc
            }
            
            # Add protocol specific info
            for protocol in ["tcp", "udp"]:
                port = get_xpath_element_value(svc, f"./{protocol}/port")
                if port:
                    props["protocol"] = protocol
                    props["port"] = port
                    break
            
            # Add node to graph
            self.graph.add_node(node_id, **props)
            self.graph.add_edge(self.root_node, node_id, relation="contains")
    
    def _process_service_groups(self, xml_root: etree._Element):
        """Process all service groups and their members."""
        # Find all service groups
        group_xpath = ".//service-group/entry"
        for group in xml_root.xpath(group_xpath):
            name = group.get("name")
            if not name:
                continue
                
            node_id = f"service-group:{name}"
            
            # Add the group node
            self.graph.add_node(node_id, type="service-group", name=name, xml=group)
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
                        member_id, 
                        type="service", 
                        name=member_name, 
                        placeholder=True
                    )
                    logger.warning(f"Referenced undefined service: {member_name}")
                
                # Add the membership edge
                self.graph.add_edge(node_id, member_id, relation="contains")
    
    def _process_security_rules(self, xml_root: etree._Element):
        """Process all security rules and their object references."""
        # Find all security rules
        rules_xpath = ".//security/rules/entry"
        for rule in xml_root.xpath(rules_xpath):
            name = rule.get("name")
            if not name:
                continue
                
            rule_id = f"security-rule:{name}"
            
            # Add the rule node
            self.graph.add_node(rule_id, type="security-rule", name=name, xml=rule)
            self.graph.add_edge(self.root_node, rule_id, relation="contains")
            
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
                
            # Process source addresses
            self._process_rule_references(rule, rule_id, "source/member", "address", "uses-source")
            
            # Process destination addresses
            self._process_rule_references(rule, rule_id, "destination/member", "address", "uses-destination")
            
            # Process service references
            self._process_rule_references(rule, rule_id, "service/member", "service", "uses-service")
            
            # Process application references
            self._process_rule_references(rule, rule_id, "application/member", "application", "uses-application")
    
    def _process_nat_rules(self, xml_root: etree._Element):
        """Process all NAT rules and their object references."""
        # Find all NAT rules
        rules_xpath = ".//nat/rules/entry"
        for rule in xml_root.xpath(rules_xpath):
            name = rule.get("name")
            if not name:
                continue
                
            rule_id = f"nat-rule:{name}"
            
            # Add the rule node
            self.graph.add_node(rule_id, type="nat-rule", name=name, xml=rule)
            self.graph.add_edge(self.root_node, rule_id, relation="contains")
            
            # Process source addresses
            self._process_rule_references(rule, rule_id, "source/member", "address", "uses-source")
            
            # Process destination addresses
            self._process_rule_references(rule, rule_id, "destination/member", "address", "uses-destination")
            
            # Process service references
            self._process_rule_references(rule, rule_id, "service", "service", "uses-service")
    
    def _process_rule_references(self, rule: etree._Element, rule_id: str, xpath: str, ref_type: str, relation: str):
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
                self.graph.add_node(
                    member_id, 
                    type=ref_type, 
                    name=member_name, 
                    placeholder=True
                )
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
            
        # Add the node ID
        data["id"] = node_id
        
        # Add edge information
        edges_out = []
        for succ in self.graph.successors(node_id):
            edge_data = self.graph.get_edge_data(node_id, succ)
            edge_type = edge_data.get("relation", "unknown")
            edges_out.append({"target": succ, "type": edge_type})
        
        if edges_out:
            data["edges_out"] = edges_out
        
        edges_in = []
        for pred in self.graph.predecessors(node_id):
            edge_data = self.graph.get_edge_data(pred, node_id)
            edge_type = edge_data.get("relation", "unknown")
            edges_in.append({"source": pred, "type": edge_type})
        
        if edges_in:
            data["edges_in"] = edges_in
            
        return data
        
    def get_unused_objects(self, object_type: str = None) -> List[Dict]:
        """
        Find all objects of the specified type that are not referenced by any rules.
        
        Args:
            object_type: Optional type of objects to check ("address", "service", etc.)
                         If None, checks all object types
                         
        Returns:
            List of unused objects
        """
        unused = []
        
        for node_id, data in self.graph.nodes(data=True):
            # Skip non-object nodes and the root node
            if node_id == self.root_node:
                continue
                
            node_type = data.get("type", "")
            
            # If object_type is specified, filter by it
            if object_type and node_type != object_type:
                continue
                
            # Skip rule nodes
            if "rule" in node_type:
                continue
                
            # Check if this node has any predecessors other than the root
            has_refs = False
            for pred in self.graph.predecessors(node_id):
                if pred != self.root_node and "rule" in self.graph.nodes[pred].get("type", ""):
                    has_refs = True
                    break
                    
            if not has_refs:
                unused.append(self._node_to_dict(node_id))
                
        return unused