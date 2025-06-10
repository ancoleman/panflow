#!/usr/bin/env python3
"""
Demo script showing the enhanced verbose output for deduplication operations.
"""

import logging
from lxml import etree
from panflow.core.deduplication import DeduplicationEngine

# Set up logging to show INFO level messages
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Create a sample configuration
root = etree.Element("config")
devices = etree.SubElement(root, "devices")
entry = etree.SubElement(devices, "entry", name="localhost.localdomain")

# Add device group
dg_parent = etree.SubElement(entry, "device-group")
dg = etree.SubElement(dg_parent, "entry", name="EDGE-WAN")

# Add duplicate address objects
address = etree.SubElement(dg, "address")

# Primary object
addr1 = etree.SubElement(address, "entry", name="10.252.0.0_16")
ip1 = etree.SubElement(addr1, "ip-netmask")
ip1.text = "10.252.0.0/16"

# Duplicate object
addr2 = etree.SubElement(address, "entry", name="us_g_n_INT_BN_10.252")
ip2 = etree.SubElement(addr2, "ip-netmask")
ip2.text = "10.252.0.0/16"

# Add references to the duplicate object
# Reference in address group
addr_group = etree.SubElement(dg, "address-group")
group1 = etree.SubElement(addr_group, "entry", name="Private-Subnets")
static = etree.SubElement(group1, "static")
member1 = etree.SubElement(static, "member")
member1.text = "us_g_n_INT_BN_10.252"

# Reference in security rule
pre_rulebase = etree.SubElement(dg, "pre-rulebase")
security = etree.SubElement(pre_rulebase, "security")
rules = etree.SubElement(security, "rules")
rule1 = etree.SubElement(rules, "entry", name="Allow-Internal")
source = etree.SubElement(rule1, "source")
src_member = etree.SubElement(source, "member")
src_member.text = "us_g_n_INT_BN_10.252"

# Create the deduplication engine
tree = etree.ElementTree(root)
engine = DeduplicationEngine(
    tree=tree,
    device_type="panorama",
    context_type="device_group",
    version="11.0",
    device_group="EDGE-WAN"
)

print("=== Deduplication Demo with Enhanced Verbose Output ===")
print("\nSearching for duplicate objects...")

# Find duplicates
duplicates, references = engine.find_duplicate_addresses()

if duplicates:
    print(f"\nFound {len(duplicates)} sets of duplicate objects")
    for value, objects in duplicates.items():
        names = []
        for obj_tuple in objects:
            if len(obj_tuple) == 3:
                name, _, _ = obj_tuple
            else:
                name, _ = obj_tuple
            names.append(name)
        print(f"  - {value}: {', '.join(names)}")
    
    print("\nPerforming deduplication with enhanced logging...")
    print("-" * 70)
    
    # Merge duplicates - this will show the new verbose output
    changes = engine.merge_duplicates(duplicates, references, "first")
    
    print("-" * 70)
    print(f"\nDeduplication complete!")
    print(f"Total changes made: {len(changes)}")
else:
    print("No duplicate objects found.")