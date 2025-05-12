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
    ip_100_names = [name for name, _ in ip_100_objects]
    assert "server1" in ip_100_names
    assert "server2" in ip_100_names

    # Check second set (192.168.1.200/32)
    ip_200_key = next(k for k in duplicates.keys() if "192.168.1.200" in k)
    ip_200_objects = duplicates[ip_200_key]
    assert len(ip_200_objects) == 2
    ip_200_names = [name for name, _ in ip_200_objects]
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
        assert len(references["server1"]) == 2

        # Check reference types
        ref_types = [ref_type for ref_type, _ in references["server1"]]
        assert "address_group" in ref_types
        assert "security_rule" in ref_types or "security_pre_rule" in ref_types


def test_merge_duplicates_shortest_strategy(sample_config_with_duplicates):
    """Test merging duplicates using shortest name strategy."""
    engine = DeduplicationEngine(
        sample_config_with_duplicates, "panorama", "device_group", "10.2", device_group="DG1"
    )

    # Find duplicates first
    duplicates, references = engine.find_duplicate_addresses()

    # Mock _update_references to avoid modifying the XML
    with patch.object(engine, "_update_references") as mock_update:
        mock_update.return_value = []

        # Merge duplicates using shortest name strategy
        changes = engine.merge_duplicates(duplicates, references, "shortest")

        # Should have changes for both duplicate sets
        assert len(changes) == 2

        # For 192.168.1.100/32, server1 should be primary (shorter than server2)
        ip_100_key = next(k for k in changes.keys() if "192.168.1.100" in k)
        assert changes[ip_100_key]["primary"] == "server1"
        assert "server2" in changes[ip_100_key]["merged"]

        # For 192.168.1.200/32, db-server1 should be primary (shorter than db-server2)
        ip_200_key = next(k for k in changes.keys() if "192.168.1.200" in k)
        assert changes[ip_200_key]["primary"] == "db-server1"
        assert "db-server2" in changes[ip_200_key]["merged"]


def test_merge_duplicates_alphabetical_strategy(sample_config_with_duplicates):
    """Test merging duplicates using alphabetical name strategy."""
    engine = DeduplicationEngine(
        sample_config_with_duplicates, "panorama", "device_group", "10.2", device_group="DG1"
    )

    # Find duplicates first
    duplicates, references = engine.find_duplicate_services()

    # Mock _update_references to avoid modifying the XML
    with patch.object(engine, "_update_references") as mock_update:
        mock_update.return_value = []

        # Merge duplicates using alphabetical name strategy
        changes = engine.merge_duplicates(duplicates, references, "alphabetical")

        # Should have changes for TCP port 80 duplicates
        assert len(changes) == 1

        # For TCP port 80, http should be primary (alphabetically before http-alt)
        tcp_80_key = next(iter(changes.keys()))
        assert changes[tcp_80_key]["primary"] == "http"
        assert "http-alt" in changes[tcp_80_key]["merged"]


def test_update_references(sample_config_with_duplicates):
    """Test updating references to merged objects."""
    engine = DeduplicationEngine(
        sample_config_with_duplicates, "panorama", "device_group", "10.2", device_group="DG1"
    )

    # Mock xpath_search to find references
    with patch("panflow.core.deduplication.xpath_search") as mock_search:
        # Create a reference to db-server2 in a group
        group_ref = etree.Element("entry", name="db-group")
        static = etree.SubElement(group_ref, "static")
        member1 = etree.SubElement(static, "member")
        member1.text = "db-server1"
        member2 = etree.SubElement(static, "member")
        member2.text = "db-server2"

        # Create a reference to db-server2 in a rule
        rule_ref = etree.Element("entry", name="allow-db")
        dest = etree.SubElement(rule_ref, "destination")
        rule_member = etree.SubElement(dest, "member")
        rule_member.text = "db-server2"

        # Set up mock to return different results
        mock_search.side_effect = [
            [group_ref],  # address_group search
            [rule_ref],  # security rules search
        ]

        # Update references
        references = {"db-server2": [("address_group", "db-group"), ("security_rule", "allow-db")]}

        updated_refs = engine._update_references("db-server2", "db-server1", references)

        # Check that references were updated
        assert len(updated_refs) == 2
        assert member2.text == "db-server1"
        assert rule_member.text == "db-server1"


def test_remove_duplicate_objects(sample_config_with_duplicates):
    """Test removing duplicate objects after merging."""
    engine = DeduplicationEngine(
        sample_config_with_duplicates, "panorama", "device_group", "10.2", device_group="DG1"
    )

    # Get sample objects to test removal
    xpath = f"/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='DG1']/address/entry[@name='server2']"
    elements = sample_config_with_duplicates.xpath(xpath)
    assert len(elements) == 1
    duplicate = elements[0]

    # Remove the duplicate
    engine._remove_duplicate_object(duplicate)

    # Check that it's removed
    elements = sample_config_with_duplicates.xpath(xpath)
    assert len(elements) == 0


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
    primary, others = engine._select_primary_object(objects, "first")

    assert primary == "server2"
    assert "server1" in others
    assert "long-server-name" in others


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
    primary, others = engine._select_primary_object(objects, "shortest")

    assert primary == "server1"  # server1 and server2 are same length, but alphabetical tiebreaker
    assert "server2" in others
    assert "long-server-name" in others


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
    primary, others = engine._select_primary_object(objects, "longest")

    assert primary == "long-server-name"
    assert "server1" in others
    assert "server2" in others
