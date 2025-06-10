"""
Test verbose output formatting for deduplication operations.
"""

import pytest
from unittest.mock import patch, MagicMock
from lxml import etree
import logging

from panflow.core.deduplication import DeduplicationEngine


@pytest.fixture
def sample_tree():
    """Create a sample configuration tree for testing."""
    root = etree.Element("config")
    devices = etree.SubElement(root, "devices")
    entry = etree.SubElement(devices, "entry", name="localhost.localdomain")
    
    # Add device group for Panorama
    dg_parent = etree.SubElement(entry, "device-group")
    dg = etree.SubElement(dg_parent, "entry", name="EDGE-WAN")
    
    # Add address objects
    address = etree.SubElement(dg, "address")
    addr1 = etree.SubElement(address, "entry", name="10.252.0.0_16")
    ip1 = etree.SubElement(addr1, "ip-netmask")
    ip1.text = "10.252.0.0/16"
    
    addr2 = etree.SubElement(address, "entry", name="us_g_n_INT_BN_10.252")
    ip2 = etree.SubElement(addr2, "ip-netmask")
    ip2.text = "10.252.0.0/16"
    
    # Add address group
    addr_group = etree.SubElement(dg, "address-group")
    group1 = etree.SubElement(addr_group, "entry", name="Private-Subnets")
    static = etree.SubElement(group1, "static")
    member1 = etree.SubElement(static, "member")
    member1.text = "us_g_n_INT_BN_10.252"
    
    # Add security rule
    pre_rulebase = etree.SubElement(dg, "pre-rulebase")
    security = etree.SubElement(pre_rulebase, "security")
    rules = etree.SubElement(security, "rules")
    rule1 = etree.SubElement(rules, "entry", name="Allow-Internal")
    
    # Add source
    source = etree.SubElement(rule1, "source")
    src_member = etree.SubElement(source, "member")
    src_member.text = "us_g_n_INT_BN_10.252"
    
    return etree.ElementTree(root)


def test_format_reference_location_address_group():
    """Test formatting of address group reference locations."""
    engine = DeduplicationEngine(
        tree=None,
        device_type="panorama",
        context_type="device_group",
        version="11.0",
        device_group="EDGE-WAN"
    )
    
    # Test address group reference
    ref_path = "address-group:Private-Subnets"
    location = engine._format_reference_location(ref_path)
    assert location == "Device Group: EDGE-WAN | Address-Group: Private-Subnets"


def test_format_reference_location_security_rule():
    """Test formatting of security rule reference locations."""
    engine = DeduplicationEngine(
        tree=None,
        device_type="panorama",
        context_type="device_group",
        version="11.0",
        device_group="EDGE-WAN"
    )
    
    # Test security rule source reference
    ref_path = "pre-security:Allow-Internal:source"
    location = engine._format_reference_location(ref_path)
    assert location == "Device Group: EDGE-WAN | Rulebase: Pre-Rulebase Security | Rule: Allow-Internal | Field: source"


def test_format_reference_location_nat_rule():
    """Test formatting of NAT rule reference locations."""
    engine = DeduplicationEngine(
        tree=None,
        device_type="panorama",
        context_type="device_group",
        version="11.0",
        device_group="EDGE-WAN"
    )
    
    # Test NAT rule destination translation reference
    ref_path = "nat:Web-NAT:destination-translation"
    location = engine._format_reference_location(ref_path)
    assert location == "Device Group: EDGE-WAN | Rulebase: NAT | Rule: Web-NAT | Field: destination-translation"


def test_format_reference_location_shared_context():
    """Test formatting with shared context."""
    engine = DeduplicationEngine(
        tree=None,
        device_type="panorama",
        context_type="shared",
        version="11.0"
    )
    
    # Test with shared context
    ref_path = "address-group:Global-Networks"
    location = engine._format_reference_location(ref_path)
    assert location == "Device Group: Shared | Address-Group: Global-Networks"


def test_format_reference_location_vsys():
    """Test formatting with vsys context."""
    engine = DeduplicationEngine(
        tree=None,
        device_type="firewall",
        context_type="vsys",
        version="11.0",
        vsys="vsys1"
    )
    
    # Test with vsys context
    ref_path = "security:Allow-Web:destination"
    location = engine._format_reference_location(ref_path)
    assert location == "VSYS: vsys1 | Rulebase: Security | Rule: Allow-Web | Field: destination"


def test_verbose_logging_output(sample_tree, caplog):
    """Test that verbose logging output is generated correctly."""
    engine = DeduplicationEngine(
        tree=sample_tree,
        device_type="panorama",
        context_type="device_group",
        version="11.0",
        device_group="EDGE-WAN"
    )
    
    # Set up logging to capture INFO level
    caplog.set_level(logging.INFO)
    
    # Create mock duplicates and references
    duplicates = {
        "ip-netmask:10.252.0.0/16": [
            ("10.252.0.0_16", None),
            ("us_g_n_INT_BN_10.252", None)
        ]
    }
    
    # Create mock reference elements
    mock_group_member = MagicMock()
    mock_group_member.text = "us_g_n_INT_BN_10.252"
    
    mock_rule_member = MagicMock()
    mock_rule_member.text = "us_g_n_INT_BN_10.252"
    
    references = {
        "us_g_n_INT_BN_10.252": [
            ("address-group:Private-Subnets", mock_group_member),
            ("pre-security:Allow-Internal:source", mock_rule_member)
        ]
    }
    
    # Merge duplicates
    engine.merge_duplicates(duplicates, references, "first")
    
    # Check that the verbose log messages were generated
    log_messages = [record.message for record in caplog.records]
    
    # Should contain messages like:
    # "Replacing reference to 'us_g_n_INT_BN_10.252' with '10.252.0.0_16' in Device Group: EDGE-WAN | Address-Group: Private-Subnets"
    # "Replacing reference to 'us_g_n_INT_BN_10.252' with '10.252.0.0_16' in Device Group: EDGE-WAN | Rulebase: Pre-Rulebase Security | Rule: Allow-Internal | Field: source"
    
    expected_messages = [
        "Replacing reference to 'us_g_n_INT_BN_10.252' with '10.252.0.0_16' in Device Group: EDGE-WAN | Address-Group: Private-Subnets",
        "Replacing reference to 'us_g_n_INT_BN_10.252' with '10.252.0.0_16' in Device Group: EDGE-WAN | Rulebase: Pre-Rulebase Security | Rule: Allow-Internal | Field: source"
    ]
    
    for expected in expected_messages:
        assert any(expected in msg for msg in log_messages), f"Expected log message not found: {expected}"


def test_fallback_formatting():
    """Test fallback formatting for unknown reference types."""
    engine = DeduplicationEngine(
        tree=None,
        device_type="panorama",
        context_type="device_group",
        version="11.0",
        device_group="TEST-DG"
    )
    
    # Test unknown reference type
    ref_path = "unknown-type:some-object:field"
    location = engine._format_reference_location(ref_path)
    assert location == "Device Group: TEST-DG | unknown-type:some-object:field"