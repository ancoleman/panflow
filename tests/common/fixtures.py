"""
Shared fixtures for PANFlow tests.

This module provides reusable pytest fixtures for common test scenarios,
reducing duplication across test files.
"""

import pytest
from lxml import etree
from pathlib import Path
from typing import Dict, List, Any

from panflow import PANFlowConfig


# Sample XML configurations as constants
FIREWALL_CONFIG_MINIMAL = """
<config version="10.2.0">
    <mgt-config>
        <users>
            <entry name="admin">
                <permissions>
                    <role-based>
                        <superuser>yes</superuser>
                    </role-based>
                </permissions>
            </entry>
        </users>
    </mgt-config>
    <shared>
        <address/>
        <address-group/>
        <service/>
        <service-group/>
        <tag/>
    </shared>
    <devices>
        <entry name="localhost.localdomain">
            <vsys>
                <entry name="vsys1">
                    <address/>
                    <address-group/>
                    <service/>
                    <service-group/>
                    <tag/>
                    <rulebase>
                        <security>
                            <rules/>
                        </security>
                        <nat>
                            <rules/>
                        </nat>
                    </rulebase>
                </entry>
            </vsys>
        </entry>
    </devices>
</config>
"""

PANORAMA_CONFIG_MINIMAL = """
<config version="10.2.0">
    <mgt-config>
        <users>
            <entry name="admin">
                <permissions>
                    <role-based>
                        <superuser>yes</superuser>
                    </role-based>
                </permissions>
            </entry>
        </users>
    </mgt-config>
    <shared>
        <address/>
        <address-group/>
        <service/>
        <service-group/>
        <tag/>
        <pre-rulebase>
            <security>
                <rules/>
            </security>
            <nat>
                <rules/>
            </nat>
        </pre-rulebase>
        <post-rulebase>
            <security>
                <rules/>
            </security>
            <nat>
                <rules/>
            </nat>
        </post-rulebase>
    </shared>
    <devices>
        <entry name="localhost.localdomain">
            <device-group/>
            <template/>
        </entry>
    </devices>
</config>
"""


@pytest.fixture
def firewall_config():
    """Minimal firewall configuration for testing."""
    return etree.ElementTree(etree.fromstring(FIREWALL_CONFIG_MINIMAL))


@pytest.fixture
def panorama_config():
    """Minimal Panorama configuration for testing."""
    return etree.ElementTree(etree.fromstring(PANORAMA_CONFIG_MINIMAL))


@pytest.fixture
def panorama_with_objects():
    """Panorama configuration with sample objects."""
    xml = """
    <config version="10.2.0">
        <shared>
            <address>
                <entry name="shared-server">
                    <ip-netmask>10.0.0.1/32</ip-netmask>
                    <description>Shared server</description>
                </entry>
            </address>
            <service>
                <entry name="tcp-8080">
                    <protocol>
                        <tcp>
                            <port>8080</port>
                        </tcp>
                    </protocol>
                </entry>
            </service>
            <tag>
                <entry name="Production">
                    <color>color1</color>
                </entry>
            </tag>
        </shared>
        <devices>
            <entry name="localhost.localdomain">
                <device-group>
                    <entry name="DG-Parent">
                        <address>
                            <entry name="parent-server">
                                <ip-netmask>192.168.1.1/32</ip-netmask>
                            </entry>
                        </address>
                        <devices>
                            <entry name="DG-Child">
                                <address>
                                    <entry name="child-server">
                                        <ip-netmask>192.168.2.1/32</ip-netmask>
                                    </entry>
                                </address>
                            </entry>
                        </devices>
                    </entry>
                    <entry name="DG-Standalone">
                        <address>
                            <entry name="standalone-server">
                                <ip-netmask>10.1.1.1/32</ip-netmask>
                            </entry>
                        </address>
                    </entry>
                </device-group>
            </entry>
        </devices>
    </config>
    """
    return etree.ElementTree(etree.fromstring(xml))


@pytest.fixture
def panorama_with_policies():
    """Panorama configuration with sample policies."""
    xml = """
    <config version="10.2.0">
        <shared>
            <pre-rulebase>
                <security>
                    <rules>
                        <entry name="Allow-DNS">
                            <from>
                                <member>any</member>
                            </from>
                            <to>
                                <member>any</member>
                            </to>
                            <source>
                                <member>any</member>
                            </source>
                            <destination>
                                <member>any</member>
                            </destination>
                            <service>
                                <member>dns</member>
                            </service>
                            <application>
                                <member>dns</member>
                            </application>
                            <action>allow</action>
                        </entry>
                    </rules>
                </security>
            </pre-rulebase>
        </shared>
        <devices>
            <entry name="localhost.localdomain">
                <device-group>
                    <entry name="DG-Test">
                        <pre-rulebase>
                            <security>
                                <rules>
                                    <entry name="Block-Bad-IPs">
                                        <from>
                                            <member>untrust</member>
                                        </from>
                                        <to>
                                            <member>trust</member>
                                        </to>
                                        <source>
                                            <member>BadActors</member>
                                        </source>
                                        <destination>
                                            <member>any</member>
                                        </destination>
                                        <service>
                                            <member>any</member>
                                        </service>
                                        <application>
                                            <member>any</member>
                                        </application>
                                        <action>deny</action>
                                    </entry>
                                </rules>
                            </security>
                        </pre-rulebase>
                    </entry>
                </device-group>
            </entry>
        </devices>
    </config>
    """
    return etree.ElementTree(etree.fromstring(xml))


@pytest.fixture
def sample_address_objects() -> List[Dict[str, Any]]:
    """Sample address objects for testing."""
    return [
        {
            "name": "web-server-1",
            "ip-netmask": "192.168.1.10/32",
            "description": "Primary web server",
            "tag": ["web", "production"]
        },
        {
            "name": "web-server-2",
            "ip-netmask": "192.168.1.11/32",
            "description": "Secondary web server",
            "tag": ["web", "production"]
        },
        {
            "name": "db-server",
            "ip-netmask": "192.168.2.50/32",
            "description": "Database server",
            "tag": ["database", "production"]
        },
        {
            "name": "test-network",
            "ip-netmask": "10.0.0.0/24",
            "description": "Test network",
            "tag": ["test"]
        }
    ]


@pytest.fixture
def sample_service_objects() -> List[Dict[str, Any]]:
    """Sample service objects for testing."""
    return [
        {
            "name": "tcp-8080",
            "protocol": "tcp",
            "port": "8080",
            "description": "HTTP alternate port"
        },
        {
            "name": "tcp-8443",
            "protocol": "tcp", 
            "port": "8443",
            "description": "HTTPS alternate port"
        },
        {
            "name": "udp-5060",
            "protocol": "udp",
            "port": "5060",
            "description": "SIP"
        },
        {
            "name": "tcp-range",
            "protocol": "tcp",
            "port": "8000-8010",
            "description": "TCP port range"
        }
    ]


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary configuration file."""
    config_file = tmp_path / "test_config.xml"
    config_file.write_text(FIREWALL_CONFIG_MINIMAL)
    return str(config_file)


@pytest.fixture
def panflow_config(temp_config_file):
    """Create a PANFlowConfig instance with a temporary file."""
    return PANFlowConfig(config_file=temp_config_file)


# Context fixtures
@pytest.fixture(params=["shared", "vsys", "device_group"])
def context_type(request):
    """Parametrized fixture for testing different context types."""
    return request.param


@pytest.fixture
def context_params(context_type):
    """Get appropriate context parameters based on context type."""
    if context_type == "device_group":
        return {"device_group": "DG-Test"}
    elif context_type == "vsys":
        return {"vsys": "vsys1"}
    else:
        return {}


# Version fixtures
@pytest.fixture(params=["10.1", "10.2", "11.0", "11.1", "11.2"])
def panos_version(request):
    """Parametrized fixture for testing different PAN-OS versions."""
    return request.param