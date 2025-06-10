"""
Factory classes for creating test objects and mocks.

This module provides factory classes that generate consistent test data
and mock objects, reducing duplication in test setup.
"""

from unittest.mock import MagicMock, Mock, patch
from lxml import etree
from typing import Dict, List, Any, Optional
import json


class ConfigFactory:
    """Factory for creating test configurations."""
    
    @staticmethod
    def minimal_firewall() -> etree._ElementTree:
        """Create a minimal firewall configuration."""
        from .fixtures import FIREWALL_CONFIG_MINIMAL
        return etree.ElementTree(etree.fromstring(FIREWALL_CONFIG_MINIMAL))
    
    @staticmethod
    def minimal_panorama() -> etree._ElementTree:
        """Create a minimal Panorama configuration."""
        from .fixtures import PANORAMA_CONFIG_MINIMAL
        return etree.ElementTree(etree.fromstring(PANORAMA_CONFIG_MINIMAL))
    
    @staticmethod
    def panorama_with_hierarchy() -> etree._ElementTree:
        """Create a Panorama config with device group hierarchy."""
        xml = """
        <config version="10.2.0">
            <devices>
                <entry name="localhost.localdomain">
                    <device-group>
                        <entry name="Parent-DG">
                            <device-group>
                                <entry name="Child-DG-1"/>
                                <entry name="Child-DG-2">
                                    <device-group>
                                        <entry name="Grandchild-DG"/>
                                    </device-group>
                                </entry>
                            </device-group>
                        </entry>
                        <entry name="Standalone-DG"/>
                    </device-group>
                </entry>
            </devices>
        </config>
        """
        return etree.ElementTree(etree.fromstring(xml))
    
    @staticmethod
    def firewall_with_vsys(vsys_names: List[str] = None) -> etree._ElementTree:
        """Create a firewall config with multiple vsys."""
        if vsys_names is None:
            vsys_names = ["vsys1", "vsys2", "vsys3"]
        
        vsys_entries = ""
        for vsys in vsys_names:
            vsys_entries += f"""
                <entry name="{vsys}">
                    <address/>
                    <address-group/>
                    <service/>
                    <service-group/>
                    <rulebase>
                        <security><rules/></security>
                        <nat><rules/></nat>
                    </rulebase>
                </entry>
            """
        
        xml = f"""
        <config version="10.2.0">
            <devices>
                <entry name="localhost.localdomain">
                    <vsys>
                        {vsys_entries}
                    </vsys>
                </entry>
            </devices>
        </config>
        """
        return etree.ElementTree(etree.fromstring(xml))
    
    @staticmethod
    def panorama_with_objects() -> etree._ElementTree:
        """Create a Panorama config with sample objects for testing."""
        xml = """
        <config version="10.2.0">
            <devices>
                <entry name="localhost.localdomain">
                    <device-group>
                        <entry name="Test-DG">
                            <address>
                                <entry name="shared-server">
                                    <ip-netmask>10.0.0.1/32</ip-netmask>
                                    <description>Shared server address</description>
                                </entry>
                                <entry name="test-addr-1">
                                    <ip-netmask>192.168.1.100/32</ip-netmask>
                                    <description>Test address 1</description>
                                </entry>
                                <entry name="test-addr-2">
                                    <ip-netmask>192.168.1.101/32</ip-netmask>
                                    <description>Test address 2</description>
                                </entry>
                            </address>
                            <service>
                                <entry name="service-http">
                                    <protocol>
                                        <tcp>
                                            <port>80</port>
                                        </tcp>
                                    </protocol>
                                </entry>
                                <entry name="service-https">
                                    <protocol>
                                        <tcp>
                                            <port>443</port>
                                        </tcp>
                                    </protocol>
                                </entry>
                            </service>
                            <address-group>
                                <entry name="test-group">
                                    <static>
                                        <member>test-addr-1</member>
                                        <member>test-addr-2</member>
                                    </static>
                                    <description>Test address group</description>
                                </entry>
                            </address-group>
                        </entry>
                    </device-group>
                </entry>
            </devices>
            <shared>
                <address>
                    <entry name="shared-dns">
                        <fqdn>dns.google.com</fqdn>
                        <description>Google DNS</description>
                    </entry>
                </address>
            </shared>
        </config>
        """
        return etree.ElementTree(etree.fromstring(xml))


class MockFactory:
    """Factory for creating mock objects."""
    
    @staticmethod
    def xpath_search(return_values: Optional[List] = None) -> MagicMock:
        """Create a mock for xpath_search function."""
        mock = MagicMock()
        if return_values is not None:
            mock.return_value = return_values
        else:
            mock.return_value = []
        return mock
    
    @staticmethod
    def panflow_config(
        device_type: str = "firewall",
        version: str = "10.2",
        context_type: str = "shared"
    ) -> MagicMock:
        """Create a mock PANFlowConfig object."""
        mock_config = MagicMock()
        mock_config.device_type = device_type
        mock_config.version = version
        mock_config.context_type = context_type
        mock_config.tree = ConfigFactory.minimal_firewall()
        return mock_config
    
    @staticmethod
    def cli_runner_result(
        exit_code: int = 0,
        output: str = "",
        exception: Optional[Exception] = None
    ) -> MagicMock:
        """Create a mock CLI runner result."""
        result = MagicMock()
        result.exit_code = exit_code
        result.output = output
        result.stdout = output
        result.exception = exception
        return result
    
    @staticmethod
    def graph_service() -> MagicMock:
        """Create a mock GraphService."""
        mock_graph = MagicMock()
        mock_graph.nodes = {}
        mock_graph.edges = {}
        
        # Add common methods
        mock_graph.add_node = MagicMock()
        mock_graph.add_edge = MagicMock()
        mock_graph.get_node = MagicMock(return_value=None)
        mock_graph.query = MagicMock(return_value=[])
        
        return mock_graph
    
    @staticmethod
    def query_executor(results: Optional[List[Dict]] = None) -> MagicMock:
        """Create a mock QueryExecutor."""
        mock_executor = MagicMock()
        mock_executor.execute = MagicMock(return_value=results or [])
        return mock_executor


class ObjectFactory:
    """Factory for creating test objects."""
    
    @staticmethod
    def address_element(
        name: str = "test-address",
        ip_netmask: str = "192.168.1.1/32",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> etree._Element:
        """Create an address object XML element."""
        elem = etree.Element("entry", name=name)
        
        ip_elem = etree.SubElement(elem, "ip-netmask")
        ip_elem.text = ip_netmask
        
        if description:
            desc_elem = etree.SubElement(elem, "description")
            desc_elem.text = description
        
        if tags:
            tag_elem = etree.SubElement(elem, "tag")
            for tag in tags:
                member = etree.SubElement(tag_elem, "member")
                member.text = tag
        
        return elem
    
    @staticmethod
    def service_element(
        name: str = "test-service",
        protocol: str = "tcp",
        port: str = "8080",
        description: Optional[str] = None
    ) -> etree._Element:
        """Create a service object XML element."""
        elem = etree.Element("entry", name=name)
        
        proto_elem = etree.SubElement(elem, "protocol")
        proto_type_elem = etree.SubElement(proto_elem, protocol)
        port_elem = etree.SubElement(proto_type_elem, "port")
        port_elem.text = port
        
        if description:
            desc_elem = etree.SubElement(elem, "description")
            desc_elem.text = description
        
        return elem
    
    @staticmethod
    def address_group_element(
        name: str = "test-group",
        members: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> etree._Element:
        """Create an address group XML element."""
        elem = etree.Element("entry", name=name)
        
        if members:
            static_elem = etree.SubElement(elem, "static")
            for member in members:
                member_elem = etree.SubElement(static_elem, "member")
                member_elem.text = member
        
        if description:
            desc_elem = etree.SubElement(elem, "description")
            desc_elem.text = description
        
        return elem
    
    @staticmethod
    def tag_element(
        name: str = "test-tag",
        color: str = "color1",
        comments: Optional[str] = None
    ) -> etree._Element:
        """Create a tag XML element."""
        elem = etree.Element("entry", name=name)
        
        color_elem = etree.SubElement(elem, "color")
        color_elem.text = color
        
        if comments:
            comments_elem = etree.SubElement(elem, "comments")
            comments_elem.text = comments
        
        return elem


class PolicyFactory:
    """Factory for creating test policies."""
    
    @staticmethod
    def security_rule_element(
        name: str = "test-rule",
        action: str = "allow",
        from_zones: Optional[List[str]] = None,
        to_zones: Optional[List[str]] = None,
        source: Optional[List[str]] = None,
        destination: Optional[List[str]] = None,
        service: Optional[List[str]] = None,
        application: Optional[List[str]] = None,
        disabled: bool = False
    ) -> etree._Element:
        """Create a security rule XML element."""
        elem = etree.Element("entry", name=name)
        
        # From zones
        from_elem = etree.SubElement(elem, "from")
        for zone in (from_zones or ["any"]):
            member = etree.SubElement(from_elem, "member")
            member.text = zone
        
        # To zones
        to_elem = etree.SubElement(elem, "to")
        for zone in (to_zones or ["any"]):
            member = etree.SubElement(to_elem, "member")
            member.text = zone
        
        # Source
        source_elem = etree.SubElement(elem, "source")
        for src in (source or ["any"]):
            member = etree.SubElement(source_elem, "member")
            member.text = src
        
        # Destination
        dest_elem = etree.SubElement(elem, "destination")
        for dst in (destination or ["any"]):
            member = etree.SubElement(dest_elem, "member")
            member.text = dst
        
        # Service
        service_elem = etree.SubElement(elem, "service")
        for svc in (service or ["any"]):
            member = etree.SubElement(service_elem, "member")
            member.text = svc
        
        # Application
        app_elem = etree.SubElement(elem, "application")
        for app in (application or ["any"]):
            member = etree.SubElement(app_elem, "member")
            member.text = app
        
        # Action
        action_elem = etree.SubElement(elem, "action")
        action_elem.text = action
        
        # Disabled
        if disabled:
            disabled_elem = etree.SubElement(elem, "disabled")
            disabled_elem.text = "yes"
        
        return elem
    
    @staticmethod
    def nat_rule_element(
        name: str = "test-nat",
        nat_type: str = "ipv4",
        from_zones: Optional[List[str]] = None,
        to_zones: Optional[List[str]] = None,
        source: Optional[List[str]] = None,
        destination: Optional[List[str]] = None,
        service: Optional[str] = None,
        disabled: bool = False
    ) -> etree._Element:
        """Create a NAT rule XML element."""
        elem = etree.Element("entry", name=name)
        
        # NAT type
        nat_type_elem = etree.SubElement(elem, "nat-type")
        nat_type_elem.text = nat_type
        
        # From zones
        from_elem = etree.SubElement(elem, "from")
        for zone in (from_zones or ["any"]):
            member = etree.SubElement(from_elem, "member")
            member.text = zone
        
        # To zones
        to_elem = etree.SubElement(elem, "to")
        for zone in (to_zones or ["any"]):
            member = etree.SubElement(to_elem, "member")
            member.text = zone
        
        # Source
        source_elem = etree.SubElement(elem, "source")
        for src in (source or ["any"]):
            member = etree.SubElement(source_elem, "member")
            member.text = src
        
        # Destination
        dest_elem = etree.SubElement(elem, "destination")
        for dst in (destination or ["any"]):
            member = etree.SubElement(dest_elem, "member")
            member.text = dst
        
        # Service
        if service:
            service_elem = etree.SubElement(elem, "service")
            service_elem.text = service
        
        # Disabled
        if disabled:
            disabled_elem = etree.SubElement(elem, "disabled")
            disabled_elem.text = "yes"
        
        return elem


# Utility functions for creating test data
def create_bulk_addresses(count: int, prefix: str = "addr") -> List[etree._Element]:
    """Create multiple address objects for testing."""
    addresses = []
    for i in range(count):
        addr = ObjectFactory.address_element(
            name=f"{prefix}-{i}",
            ip_netmask=f"192.168.{i // 256}.{i % 256}/32",
            description=f"Test address {i}"
        )
        addresses.append(addr)
    return addresses


def create_bulk_services(count: int, prefix: str = "svc") -> List[etree._Element]:
    """Create multiple service objects for testing."""
    services = []
    for i in range(count):
        svc = ObjectFactory.service_element(
            name=f"{prefix}-{i}",
            protocol="tcp" if i % 2 == 0 else "udp",
            port=str(8000 + i),
            description=f"Test service {i}"
        )
        services.append(svc)
    return services


def create_test_criteria(criteria_type: str = "basic") -> Dict[str, Any]:
    """Create test criteria for bulk operations."""
    if criteria_type == "basic":
        return {
            "has-tag": "production",
            "name-contains": "server"
        }
    elif criteria_type == "complex":
        return {
            "has-tag": "production",
            "name-contains": "server",
            "ip-range": "192.168.1.0/24",
            "description-contains": "web"
        }
    elif criteria_type == "service":
        return {
            "protocol": "tcp",
            "port-range": "8000-9000"
        }
    else:
        return {}