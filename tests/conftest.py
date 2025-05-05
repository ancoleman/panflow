"""
Test configuration and fixtures for PANFlow tests.

This module provides pytest fixtures for unit and integration tests.
"""

import os
import sys
import pytest
from lxml import etree
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Test fixtures path
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')

@pytest.fixture
def fixture_path():
    """Return the path to the fixtures directory."""
    return Path(FIXTURES_DIR)

@pytest.fixture
def sample_xml_string():
    """Return a sample PAN-OS XML configuration string."""
    return """
    <config version="10.1.0">
      <shared>
        <address>
          <entry name="test-address">
            <ip-netmask>192.168.1.1/32</ip-netmask>
            <description>Test address object</description>
            <tag>
              <member>test-tag</member>
            </tag>
          </entry>
        </address>
      </shared>
    </config>
    """

@pytest.fixture
def sample_xml_element(sample_xml_string):
    """Return a parsed XML element from the sample string."""
    return etree.fromstring(sample_xml_string.encode('utf-8'))

@pytest.fixture
def sample_xml_tree(sample_xml_string):
    """Return a parsed XML tree from the sample string."""
    return etree.ElementTree(etree.fromstring(sample_xml_string.encode('utf-8')))

@pytest.fixture
def panorama_xml_tree():
    """Return a minimal Panorama XML configuration tree for testing."""
    xml_str = """
    <config version="10.1.0">
      <devices>
        <entry name="localhost.localdomain">
          <device-group>
            <entry name="test-dg">
              <address>
                <entry name="test-address">
                  <ip-netmask>192.168.1.1/32</ip-netmask>
                </entry>
              </address>
            </entry>
          </device-group>
        </entry>
      </devices>
      <shared>
        <address>
          <entry name="shared-address">
            <ip-netmask>10.0.0.1/32</ip-netmask>
          </entry>
        </address>
      </shared>
    </config>
    """
    return etree.ElementTree(etree.fromstring(xml_str.encode('utf-8')))

@pytest.fixture
def firewall_xml_tree():
    """Return a minimal firewall XML configuration tree for testing."""
    xml_str = """
    <config version="10.1.0">
      <devices>
        <entry name="localhost.localdomain">
          <vsys>
            <entry name="vsys1">
              <address>
                <entry name="vsys-address">
                  <ip-netmask>192.168.1.1/32</ip-netmask>
                </entry>
              </address>
              <rulebase>
                <security>
                  <rules>
                    <entry name="test-rule">
                      <action>allow</action>
                      <source>
                        <member>any</member>
                      </source>
                      <destination>
                        <member>any</member>
                      </destination>
                      <service>
                        <member>application-default</member>
                      </service>
                      <application>
                        <member>any</member>
                      </application>
                    </entry>
                  </rules>
                </security>
              </rulebase>
            </entry>
          </vsys>
        </entry>
      </devices>
    </config>
    """
    return etree.ElementTree(etree.fromstring(xml_str.encode('utf-8')))

@pytest.fixture
def sample_xpath_mapping():
    """Return a sample XPath mapping dict for testing."""
    return {
        "contexts": {
            "panorama": {
                "shared": "/config/shared",
                "device_group": "/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='{device_group}']"
            },
            "firewall": {
                "shared": "/config/shared",
                "vsys": "/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{vsys}']"
            }
        },
        "objects": {
            "address": "{base_path}/address/entry[@name='{name}']",
            "address-group": "{base_path}/address-group/entry[@name='{name}']"
        },
        "policies": {
            "panorama": {
                "security_pre_rules": "{base_path}/pre-rulebase/security/rules/entry[@name='{name}']"
            },
            "firewall": {
                "security_rules": "{base_path}/rulebase/security/rules/entry[@name='{name}']"
            }
        }
    }