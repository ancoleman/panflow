#!/usr/bin/env python3
"""
Example usage of PANFlow's enhanced XML abstractions.

This script demonstrates how to use the new XML abstractions
for a more Pythonic approach to working with PAN-OS XML.
"""

from panflow.core import (
    XmlNode, XmlBuilder, XPathBuilder, XmlQuery, XmlDiff, DiffType
)

def main():
    """Main demonstration function."""
    print("PANFlow XML Abstractions Example")
    print("================================")
    
    # Example 1: Creating XML with XmlBuilder
    print("\n1. Creating XML with XmlBuilder")
    print("-------------------------------")
    
    builder = XmlBuilder("config", {"version": "10.1.0"})
    builder.into("devices") \
        .into("entry", {"name": "localhost.localdomain"}) \
        .into("vsys") \
        .into("entry", {"name": "vsys1"}) \
        .into("address") \
        .into("entry", {"name": "web-server"}) \
        .add("ip-netmask", text="192.168.1.100/32") \
        .add("description", text="Web server") \
        .add("tag") \
        .into("member", text="web") \
        .up() \
        .up() \
        .root_up()
    
    xml = builder.build()
    print(xml.to_string(pretty_print=True))
    
    # Example 2: Using XmlNode for navigation
    print("\n2. Using XmlNode for navigation")
    print("------------------------------")
    
    # Find an element
    address = xml.find(".//entry[@name='web-server']")
    if address:
        print(f"Found address element: {address.get_attribute('name')}")
        
        # Get child elements
        ip = address.find("./ip-netmask")
        description = address.find("./description")
        
        print(f"IP: {ip.text if ip else 'Not found'}")
        print(f"Description: {description.text if description else 'Not found'}")
        
        # Modify an element
        if description:
            description.text = "Updated web server"
            print(f"Updated description: {description.text}")
        
        # Add a child element
        address.add_child("comment", text="Added via XmlNode")
        
        # Convert to dictionary
        address_dict = address.to_dict()
        print("Address as dictionary:")
        print(address_dict)
    
    # Example 3: Using XPathBuilder for easy XPath construction
    print("\n3. Using XPathBuilder for XPath construction")
    print("-----------------------------------------")
    
    # Build an XPath expression
    xpath_builder = XPathBuilder()
    xpath = xpath_builder.anywhere() \
        .element("entry") \
        .with_name("web-server") \
        .child("tag") \
        .child("member") \
        .build()
    
    print(f"Built XPath: {xpath}")
    
    # Find elements using the built XPath
    tags = xml.find_all(xpath)
    print(f"Found {len(tags)} tags: {[tag.text for tag in tags]}")
    
    # Example 4: Using XmlQuery for filtering and transformation
    print("\n4. Using XmlQuery for querying and filtering")
    print("------------------------------------------")
    
    # Create a query from the XML
    query = XmlQuery.from_node(xml)
    
    # Find and filter elements
    entries = query.find(".//entry") \
        .has_attribute("name") \
        .has_child("ip-netmask")
    
    print(f"Found {entries.count()} address entries:")
    entries.each(lambda node: print(f"  - {node.get_attribute('name')}"))
    
    # Map transformation
    values = entries.map(lambda node: {
        "name": node.get_attribute("name"),
        "ip": node.find("./ip-netmask").text if node.find("./ip-netmask") else None,
        "desc": node.find("./description").text if node.find("./description") else None
    })
    
    print("Mapped values:")
    for value in values:
        print(f"  - {value['name']}: {value['ip']} ({value['desc']})")
    
    # Example 5: Using XmlDiff for comparing XML
    print("\n5. Using XmlDiff for comparing XML")
    print("--------------------------------")
    
    # Create a modified version of the XML
    modified_builder = XmlBuilder("config", {"version": "10.1.0"})
    modified_builder.into("devices") \
        .into("entry", {"name": "localhost.localdomain"}) \
        .into("vsys") \
        .into("entry", {"name": "vsys1"}) \
        .into("address") \
        .into("entry", {"name": "web-server"}) \
        .add("ip-netmask", text="192.168.1.200/32") \
        .add("description", text="Updated web server") \
        .add("tag") \
        .into("member", text="web") \
        .up() \
        .up() \
        .into("entry", {"name": "new-server"}) \
        .add("ip-netmask", text="192.168.1.101/32") \
        .add("description", text="New server") \
        .root_up()
    
    modified_xml = modified_builder.build()
    
    # Compare the XML trees
    diffs = XmlDiff.compare(xml.element, modified_xml.element)
    
    print(f"Found {len(diffs)} differences:")
    for diff in diffs:
        if diff.type == DiffType.ADDED:
            print(f"  + {diff.path}")
        elif diff.type == DiffType.REMOVED:
            print(f"  - {diff.path}")
        elif diff.type == DiffType.CHANGED:
            print(f"  ~ {diff.path}: {diff.source_value} -> {diff.target_value}")
    
    # Format diffs for display
    print("\nFormatted diff (markdown):")
    print(XmlDiff.format_diff(diffs, "markdown"))

if __name__ == "__main__":
    main()