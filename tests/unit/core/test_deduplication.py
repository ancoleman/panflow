"""
Unit tests for the DeduplicationEngine class.
"""

import pytest
from lxml import etree
from unittest.mock import patch, MagicMock, call

from panflow.core.deduplication import DeduplicationEngine


@pytest.fixture
def sample_config_with_duplicates():
    """
    Create a sample configuration with duplicate objects.
    """
    xml = """
    <config version="10.2.0">
        <devices>
            <entry name="localhost.localdomain">
                <device-group>
                    <entry name="DG1">
                        <address>
                            <entry name="server1">
                                <ip-netmask>192.168.1.100/32</ip-netmask>
                                <description>Web server 1</description>
                            </entry>
                            <entry name="server2">
                                <ip-netmask>192.168.1.100/32</ip-netmask>
                                <description>Web server duplicate</description>
                            </entry>
                            <entry name="db-server1">
                                <ip-netmask>192.168.1.200/32</ip-netmask>
                                <description>Database server</description>
                            </entry>
                            <entry name="db-server2">
                                <ip-netmask>192.168.1.200/32</ip-netmask>
                                <description>Duplicate database server</description>
                            </entry>
                            <entry name="unique-server">
                                <ip-netmask>192.168.1.50/32</ip-netmask>
                                <description>Unique server</description>
                            </entry>
                        </address>
                        <address-group>
                            <entry name="web-group">
                                <static>
                                    <member>server1</member>
                                </static>
                            </entry>
                            <entry name="db-group">
                                <static>
                                    <member>db-server1</member>
                                    <member>db-server2</member>
                                </static>
                            </entry>
                        </address-group>
                        <service>
                            <entry name="http">
                                <protocol>
                                    <tcp>
                                        <port>80</port>
                                    </tcp>
                                </protocol>
                            </entry>
                            <entry name="http-alt">
                                <protocol>
                                    <tcp>
                                        <port>80</port>
                                    </tcp>
                                </protocol>
                            </entry>
                            <entry name="https">
                                <protocol>
                                    <tcp>
                                        <port>443</port>
                                    </tcp>
                                </protocol>
                            </entry>
                        </service>
                        <service-group>
                            <entry name="web-services">
                                <members>
                                    <member>http</member>
                                    <member>https</member>
                                </members>
                            </entry>
                        </service-group>
                        <tag>
                            <entry name="web">
                                <color>#FF0000</color>
                            </entry>
                            <entry name="web-alt">
                                <color>#FF0000</color>
                            </entry>
                        </tag>
                        <security>
                            <rules>
                                <entry name="allow-web">
                                    <source>
                                        <member>any</member>
                                    </source>
                                    <destination>
                                        <member>server1</member>
                                    </destination>
                                    <service>
                                        <member>http</member>
                                    </service>
                                    <action>allow</action>
                                </entry>
                                <entry name="allow-db">
                                    <source>
                                        <member>any</member>
                                    </source>
                                    <destination>
                                        <member>db-server2</member>
                                    </destination>
                                    <service>
                                        <member>any</member>
                                    </service>
                                    <action>allow</action>
                                </entry>
                            </rules>
                        </security>
                    </entry>
                </device-group>
            </entry>
        </devices>
    </config>
    """
    return etree.ElementTree(etree.fromstring(xml))


def test_init_deduplication_engine(sample_config_with_duplicates):
    """Test DeduplicationEngine initialization."""
    engine = DeduplicationEngine(
        sample_config_with_duplicates, "panorama", "device_group", "10.2", device_group="DG1"
    )

    assert engine.tree == sample_config_with_duplicates
    assert engine.device_type == "panorama"
    assert engine.context_type == "device_group"
    assert engine.version == "10.2"
    assert engine.context_kwargs == {"device_group": "DG1"}


def test_find_duplicates_address(sample_config_with_duplicates):
    """Test finding duplicate address objects."""
    engine = DeduplicationEngine(
        sample_config_with_duplicates, "panorama", "device_group", "10.2", device_group="DG1"
    )

    duplicates, references = engine.find_duplicate_addresses()

    # Should find two sets of duplicates
    assert len(duplicates) == 2

    # Check first set (192.168.1.100/32)
    ip_100_key = next(k for k in duplicates.keys() if "192.168.1.100" in k)
    ip_100_objects = duplicates[ip_100_key]
    assert len(ip_100_objects) == 2
    # Handle both 2-tuple and 3-tuple formats
    ip_100_names = []
    for obj_tuple in ip_100_objects:
        if len(obj_tuple) == 3:
            name, _, _ = obj_tuple
        else:
            name, _ = obj_tuple
        ip_100_names.append(name)
    assert "server1" in ip_100_names
    assert "server2" in ip_100_names

    # Check second set (192.168.1.200/32)
    ip_200_key = next(k for k in duplicates.keys() if "192.168.1.200" in k)
    ip_200_objects = duplicates[ip_200_key]
    assert len(ip_200_objects) == 2
    # Handle both 2-tuple and 3-tuple formats
    ip_200_names = []
    for obj_tuple in ip_200_objects:
        if len(obj_tuple) == 3:
            name, _, _ = obj_tuple
        else:
            name, _ = obj_tuple
        ip_200_names.append(name)
    assert "db-server1" in ip_200_names
    assert "db-server2" in ip_200_names


def test_find_duplicates_service(sample_config_with_duplicates):
    """Test finding duplicate service objects."""
    engine = DeduplicationEngine(
        sample_config_with_duplicates, "panorama", "device_group", "10.2", device_group="DG1"
    )

    duplicates, references = engine.find_duplicate_services()

    # Should find one set of duplicates (TCP port 80)
    assert len(duplicates) == 1

    # Check the duplicates
    tcp_80_key = next(iter(duplicates.keys()))
    tcp_80_objects = duplicates[tcp_80_key]
    assert len(tcp_80_objects) == 2
    tcp_80_names = [name for name, _ in tcp_80_objects]
    assert "http" in tcp_80_names
    assert "http-alt" in tcp_80_names


def test_find_duplicates_tag(sample_config_with_duplicates):
    """Test finding duplicate tag objects."""
    engine = DeduplicationEngine(
        sample_config_with_duplicates, "panorama", "device_group", "10.2", device_group="DG1"
    )

    duplicates, references = engine.find_duplicate_tags()

    # Should find one set of duplicates (color #FF0000)
    assert len(duplicates) == 1

    # Check the duplicates
    red_key = next(iter(duplicates.keys()))
    red_objects = duplicates[red_key]
    assert len(red_objects) == 2
    red_names = [name for name, _ in red_objects]
    assert "web" in red_names
    assert "web-alt" in red_names


def test_find_references(sample_config_with_duplicates):
    """Test finding references to objects."""
    engine = DeduplicationEngine(
        sample_config_with_duplicates, "panorama", "device_group", "10.2", device_group="DG1"
    )

    # Mock xpath_search to simulate finding references
    with patch("panflow.core.deduplication.xpath_search") as mock_search:
        # Simulate group references to server1
        group_ref = etree.Element("entry", name="web-group")
        static = etree.SubElement(group_ref, "static")
        member = etree.SubElement(static, "member")
        member.text = "server1"

        # Simulate rule references to server1
        rule_ref = etree.Element("entry", name="allow-web")
        dest = etree.SubElement(rule_ref, "destination")
        rule_member = etree.SubElement(dest, "member")
        rule_member.text = "server1"

        # Set up mock to return different results based on xpath
        def mock_search_side_effect(tree, xpath):
            if "address-group" in xpath:
                return [group_ref]
            elif "security/rules" in xpath:
                return [rule_ref]
            else:
                return []

        mock_search.side_effect = mock_search_side_effect

        # Find references
        references = engine._find_references("address")

        # Should have references for server1
        assert "server1" in references
        # For panorama, it checks both pre and post rulebases, so we might get more than 2
        assert len(references["server1"]) >= 2

        # Check reference types - they should contain proper path format
        ref_paths = [ref_path for ref_path, _ in references["server1"]]
        # Should have at least one address-group reference
        assert any("address-group:" in path for path in ref_paths)
        # Should have at least one security rule reference (pre or post)
        assert any("security:" in path or "pre-security:" in path or "post-security:" in path for path in ref_paths)


def test_merge_duplicates_shortest_strategy(sample_config_with_duplicates):
    """Test merging duplicates using shortest name strategy."""
    engine = DeduplicationEngine(
        sample_config_with_duplicates, "panorama", "device_group", "10.2", device_group="DG1"
    )

    # Find duplicates first
    duplicates, references = engine.find_duplicate_addresses()

    # Merge duplicates using shortest name strategy
    changes = engine.merge_duplicates(duplicates, references, "shortest")

    # Should have changes (list of tuples)
    assert len(changes) > 0
    
    # Check that deletions were scheduled for the longer names
    delete_changes = [change for change in changes if change[0] == "delete"]
    delete_names = [change[1] for change in delete_changes]
    
    # server2 is longer than server1, so it should be deleted
    assert "server2" in delete_names
    # db-server2 is longer than db-server1, so it should be deleted  
    assert "db-server2" in delete_names


def test_merge_duplicates_alphabetical_strategy(sample_config_with_duplicates):
    """Test merging duplicates using alphabetical name strategy."""
    engine = DeduplicationEngine(
        sample_config_with_duplicates, "panorama", "device_group", "10.2", device_group="DG1"
    )

    # Find duplicates first
    duplicates, references = engine.find_duplicate_services()

    # Merge duplicates using alphabetical name strategy
    changes = engine.merge_duplicates(duplicates, references, "alphabetical")

    # Should have changes (list of tuples)
    assert len(changes) > 0
    
    # Check that deletions were scheduled
    delete_changes = [change for change in changes if change[0] == "delete"]
    delete_names = [change[1] for change in delete_changes]
    
    # http-alt comes after http alphabetically, so it should be deleted
    assert "http-alt" in delete_names


def test_format_reference_location():
    """Test the _format_reference_location method."""
    engine = DeduplicationEngine(
        etree.ElementTree(etree.Element("config")),
        "panorama",
        "device_group", 
        "10.2",
        device_group="DG1"
    )

    # Test address group reference
    location = engine._format_reference_location("address-group:web-servers")
    assert "Device Group: DG1" in location
    assert "Address-Group: web-servers" in location

    # Test security rule reference
    location = engine._format_reference_location("pre-security:allow-web:source")
    assert "Device Group: DG1" in location
    assert "Rulebase: Pre-Rulebase Security" in location
    assert "Rule: allow-web" in location
    assert "Field: source" in location


def test_select_primary_object_first():
    """Test selecting primary object using 'first' strategy."""
    engine = DeduplicationEngine(
        etree.ElementTree(etree.Element("config")),
        "panorama",
        "device_group",
        "10.2",
        device_group="DG1",
    )

    # Create sample objects
    objects = [
        ("server2", etree.Element("entry", name="server2")),
        ("server1", etree.Element("entry", name="server1")),
        ("long-server-name", etree.Element("entry", name="long-server-name")),
    ]

    # Select using 'first' strategy
    primary = engine._select_primary_object(objects, "first")

    # Should return the first object tuple
    assert primary[0] == "server2"


def test_select_primary_object_shortest():
    """Test selecting primary object using 'shortest' strategy."""
    engine = DeduplicationEngine(
        etree.ElementTree(etree.Element("config")),
        "panorama",
        "device_group",
        "10.2",
        device_group="DG1",
    )

    # Create sample objects
    objects = [
        ("server2", etree.Element("entry", name="server2")),
        ("server1", etree.Element("entry", name="server1")),
        ("long-server-name", etree.Element("entry", name="long-server-name")),
    ]

    # Select using 'shortest' strategy
    primary = engine._select_primary_object(objects, "shortest")

    # server1 and server2 are same length (7 chars), should pick one of them
    assert primary[0] in ["server1", "server2"]


def test_select_primary_object_longest():
    """Test selecting primary object using 'longest' strategy."""
    engine = DeduplicationEngine(
        etree.ElementTree(etree.Element("config")),
        "panorama",
        "device_group",
        "10.2",
        device_group="DG1",
    )

    # Create sample objects
    objects = [
        ("server2", etree.Element("entry", name="server2")),
        ("server1", etree.Element("entry", name="server1")),
        ("long-server-name", etree.Element("entry", name="long-server-name")),
    ]

    # Select using 'longest' strategy
    primary = engine._select_primary_object(objects, "longest")

    assert primary[0] == "long-server-name"
