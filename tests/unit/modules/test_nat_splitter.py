"""
Tests for the NAT splitter module functionality.

This module specifically tests that the module layer correctly
re-exports the core functionality.
"""

import pytest
from lxml import etree

from panflow.modules.nat_splitter import (
    NATRuleSplitter,
    split_bidirectional_nat_rule,
    split_all_bidirectional_nat_rules
)

# Also import from core for comparison
from panflow.core.nat_splitter import (
    NATRuleSplitter as CoreNATRuleSplitter,
    split_bidirectional_nat_rule as core_split_bidirectional_nat_rule,
    split_all_bidirectional_nat_rules as core_split_all_bidirectional_nat_rules
)

def test_module_reexports_core_classes():
    """Test that the module re-exports core classes correctly."""
    # Verify that the module imports are the same objects as the core ones
    assert NATRuleSplitter is CoreNATRuleSplitter
    assert split_bidirectional_nat_rule is core_split_bidirectional_nat_rule
    assert split_all_bidirectional_nat_rules is core_split_all_bidirectional_nat_rules

def test_module_class_instantiation():
    """Test that the re-exported class can be instantiated correctly."""
    # Create a minimal XML tree
    root = etree.Element("config")
    tree = etree.ElementTree(root)
    
    # Create a splitter instance from the module import
    splitter = NATRuleSplitter(
        tree=tree,
        device_type="firewall",
        context_type="vsys",
        version="10.1"
    )
    
    # Verify the instance attributes
    assert splitter.tree is tree
    assert splitter.device_type == "firewall"
    assert splitter.context_type == "vsys"
    assert splitter.version == "10.1"