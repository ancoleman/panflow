"""
Tests for the NAT splitter functionality.

This module tests both the class-based and function-based interfaces
to ensure the consolidation works correctly.
"""

import pytest
from lxml import etree

from panflow.core.nat_splitter import (
    NATRuleSplitter,
    split_bidirectional_nat_rule,
    split_all_bidirectional_nat_rules,
)

# Also test the import from modules (which should now be a re-export)
from panflow.modules.nat_splitter import (
    NATRuleSplitter as ModuleNATRuleSplitter,
    split_bidirectional_nat_rule as module_split_bidirectional_nat_rule,
    split_all_bidirectional_nat_rules as module_split_all_bidirectional_nat_rules,
)


# Test XML with a bidirectional NAT rule
@pytest.fixture
def sample_nat_config():
    """Return a sample PAN-OS XML configuration with a bidirectional NAT rule."""
    xml_str = """
    <config version="10.1.0">
      <devices>
        <entry name="localhost.localdomain">
          <vsys>
            <entry name="vsys1">
              <rulebase>
                <nat>
                  <rules>
                    <entry name="test-bidi-nat">
                      <bi-directional>yes</bi-directional>
                      <from>
                        <member>trust</member>
                      </from>
                      <to>
                        <member>untrust</member>
                      </to>
                      <source>
                        <member>10.0.0.1</member>
                      </source>
                      <destination>
                        <member>192.168.1.1</member>
                      </destination>
                      <service>any</service>
                      <source-translation>
                        <static-ip>
                          <translated-address>192.168.1.10</translated-address>
                        </static-ip>
                      </source-translation>
                    </entry>
                  </rules>
                </nat>
              </rulebase>
            </entry>
          </vsys>
        </entry>
      </devices>
    </config>
    """
    tree = etree.ElementTree(etree.fromstring(xml_str))
    return tree


def test_nat_rule_splitter_class(sample_nat_config):
    """Test the NATRuleSplitter class."""
    tree = sample_nat_config

    # Create a splitter instance
    splitter = NATRuleSplitter(
        tree=tree, device_type="firewall", context_type="vsys", version="10.1", vsys="vsys1"
    )

    # Split the bidirectional rule
    result = splitter.split_bidirectional_rule(
        rule_name="test-bidi-nat",
        policy_type="nat_rules",
        reverse_name_suffix="-reverse",
        zone_swap=True,
        address_swap=True,
        disable_orig_bidirectional=True,
    )

    # Verify the result
    assert result["success"] is True
    assert result["original_rule"] == "test-bidi-nat"
    assert result["reverse_rule"] == "test-bidi-nat-reverse"
    assert result["bidirectional_disabled"] is True

    # Verify the bidirectional flag was removed from the original rule
    rule_xpath = "//entry[@name='test-bidi-nat']"
    rule = tree.xpath(rule_xpath)[0]
    assert rule.find("bi-directional") is None

    # Verify the reverse rule was created
    reverse_rule_xpath = "//entry[@name='test-bidi-nat-reverse']"
    reverse_rules = tree.xpath(reverse_rule_xpath)
    assert len(reverse_rules) == 1

    reverse_rule = reverse_rules[0]

    # Verify zones were swapped
    from_zone = reverse_rule.find("from/member")
    to_zone = reverse_rule.find("to/member")
    assert from_zone.text == "untrust"
    assert to_zone.text == "trust"

    # Verify addresses were swapped
    source = reverse_rule.find("source/member")
    destination = reverse_rule.find("destination/member")
    assert source.text == "192.168.1.1"
    assert destination.text == "10.0.0.1"


def test_split_bidirectional_nat_rule_function(sample_nat_config):
    """Test the standalone split_bidirectional_nat_rule function."""
    tree = sample_nat_config

    # Split the bidirectional rule
    result = split_bidirectional_nat_rule(
        tree=tree,
        rule_name="test-bidi-nat",
        policy_type="nat_rules",
        device_type="firewall",
        context_type="vsys",
        version="10.1",
        vsys="vsys1",
    )

    # Verify the result
    assert result["success"] is True
    assert result["original_rule"] == "test-bidi-nat"
    assert result["reverse_rule"] == "test-bidi-nat-reverse"

    # Verify the reverse rule was created
    reverse_rule_xpath = "//entry[@name='test-bidi-nat-reverse']"
    reverse_rules = tree.xpath(reverse_rule_xpath)
    assert len(reverse_rules) == 1


def test_module_imports_match_core():
    """Test that the module imports match the core implementations."""
    # Verify that the module imports are the same objects as the core ones
    assert ModuleNATRuleSplitter is NATRuleSplitter
    assert module_split_bidirectional_nat_rule is split_bidirectional_nat_rule
    assert module_split_all_bidirectional_nat_rules is split_all_bidirectional_nat_rules


def test_split_all_bidirectional_rules(sample_nat_config):
    """Test the split_all_bidirectional_rules method."""
    # Add a second bidirectional rule
    rules_xpath = "//rules"
    rules = sample_nat_config.xpath(rules_xpath)[0]

    second_rule = etree.SubElement(rules, "entry")
    second_rule.set("name", "test-bidi-nat2")

    bi_directional = etree.SubElement(second_rule, "bi-directional")
    bi_directional.text = "yes"

    from_zone = etree.SubElement(second_rule, "from")
    from_member = etree.SubElement(from_zone, "member")
    from_member.text = "dmz"

    to_zone = etree.SubElement(second_rule, "to")
    to_member = etree.SubElement(to_zone, "member")
    to_member.text = "trust"

    # Create a splitter instance
    splitter = NATRuleSplitter(
        tree=sample_nat_config,
        device_type="firewall",
        context_type="vsys",
        version="10.1",
        vsys="vsys1",
    )

    # Split all bidirectional rules
    result = splitter.split_all_bidirectional_rules(policy_type="nat_rules")

    # Verify the results
    assert result["success"] is True
    assert result["processed"] == 2
    assert result["succeeded"] == 2
    assert result["failed"] == 0

    # Verify both reverse rules were created
    reverse_rules = sample_nat_config.xpath("//entry[contains(@name, '-reverse')]")
    assert len(reverse_rules) == 2


def test_standalone_split_all_rules_function(sample_nat_config):
    """Test the standalone split_all_bidirectional_nat_rules function."""
    # Split all bidirectional rules
    result = split_all_bidirectional_nat_rules(
        tree=sample_nat_config,
        policy_type="nat_rules",
        device_type="firewall",
        context_type="vsys",
        version="10.1",
        vsys="vsys1",
    )

    # Verify the results
    assert result["success"] is True
    assert result["processed"] >= 1  # At least the original rule
    assert result["succeeded"] >= 1
    assert result["failed"] == 0
