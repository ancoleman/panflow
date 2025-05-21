# XML Abstractions

PANFlow provides a set of high-level abstractions for working with XML, making it easier to create, modify, and query XML elements with a more Pythonic interface.

## XmlNode

`XmlNode` is a wrapper around lxml's Element that provides a more intuitive interface:

```python
from panflow.core.xml import XmlNode

# Create a node from an existing Element
node = XmlNode(element)

# Create a node from XML string
node = XmlNode.from_string('<address name="web-server"><ip-netmask>192.168.1.1/32</ip-netmask></address>')

# Create a new node
node = XmlNode.create('address', {'name': 'web-server'})

# Get node attributes and properties
tag = node.tag  # 'address'
attributes = node.attributes  # {'name': 'web-server'}
text = node.text  # Get element text content

# Modify node
node.text = "Some text content"
node.set_attribute('description', 'Web server')
node.remove_attribute('temp')

# Navigation
parent = node.parent
children = node.children

# Add children
ip_node = node.add_child('ip-netmask', text='192.168.1.1/32')
desc_node = node.add_child('description', attributes={'type': 'comment'}, text='Web server')

# Finding elements
members = node.find_all('.//member')
member = node.find('./member[1]')

# Check if element exists
has_desc = node.exists('./description')

# Convert to string
xml_str = node.to_string(pretty_print=True)

# Convert to dictionary
node_dict = node.to_dict()
```

## XmlBuilder

`XmlBuilder` provides a fluent interface for creating XML:

```python
from panflow.core.xml import XmlBuilder

# Create a builder for a config element
builder = XmlBuilder('config', {'version': '10.1.0'})

# Build a PAN-OS configuration hierarchically
builder.into('devices') \
    .into('entry', {'name': 'localhost.localdomain'}) \
    .into('vsys') \
    .into('entry', {'name': 'vsys1'}) \
    .into('address') \
    .into('entry', {'name': 'web-server'}) \
    .add('ip-netmask', text='192.168.1.1/32') \
    .add('description', text='Web server') \
    .up() \
    .up() \
    .into('entry', {'name': 'app-server'}) \
    .add('ip-netmask', text='192.168.1.2/32') \
    .root_up()

# Get the built XML as an XmlNode
xml = builder.build()

# Convert to string
xml_str = builder.to_string(pretty_print=True)
```

## XPathBuilder

`XPathBuilder` makes it easier to construct XPath expressions:

```python
from panflow.core.xml import XPathBuilder

# Create an XPath for finding address objects with a specific tag
xpath = XPathBuilder() \
    .anywhere() \
    .element('entry') \
    .child('tag') \
    .child('member') \
    .with_text('web') \
    .parent() \
    .parent() \
    .build()

# Result: //entry/tag/member[text()='web']/..
```

## XmlQuery

`XmlQuery` provides a jQuery-like interface for selecting and manipulating XML:

```python
from panflow.core.xml import XmlQuery, XmlNode

# Create a query from an XML element or XmlNode
node = XmlNode.from_string('<config>...</config>')
query = XmlQuery(node)

# Find elements
addresses = query.find_all('.//address/entry')

# Find a single element
address = query.find('.//address/entry[@name="web-server"]')

# Filter elements with a condition
web_servers = query.filter(lambda el: 'web' in el.get('name', ''))

# Count results
count = addresses.count()

# Get the first result
first_address = addresses.first()

# Map results to extract data
names = addresses.map(lambda el: el.get('name'))

# Each (iterate over results)
addresses.each(lambda el: print(f"Address: {el.get('name')}"))

# Check if elements exist
if query.exists('.//address/entry[@name="web-server"]'):
    print("Web server exists")
```

## XmlDiff

`XmlDiff` helps identify differences between XML elements:

```python
from panflow.core.xml import XmlNode, XmlDiff, DiffType

# Create two XML documents to compare
original = XmlNode.from_string("<config><settings><option>old</option></settings></config>")
modified = XmlNode.from_string("<config><settings><option>new</option></settings></config>")

# Initialize diff with source and target
diff = XmlDiff(original.element, modified.element)

# Compare the elements
diff.compare()

# Get the differences
diff_items = diff.get_diffs()

# Process the differences
for item in diff_items:
    if item.diff_type == DiffType.ADDED:
        print(f"Added: {item.path} - {item.target_value}")
    elif item.diff_type == DiffType.REMOVED:
        print(f"Removed: {item.path} - {item.source_value}")
    elif item.diff_type == DiffType.CHANGED:
        print(f"Changed: {item.path} from {item.source_value} to {item.target_value}")
```

## Combined Example

Here's a complete example showing how to use these abstractions together:

```python
from panflow.core.xml import XmlNode, XmlBuilder, XPathBuilder, XmlQuery, XmlDiff

# Create a configuration with an address object
builder = XmlBuilder('config')
builder.into('devices') \
    .into('entry', {'name': 'localhost.localdomain'}) \
    .into('vsys') \
    .into('entry', {'name': 'vsys1'}) \
    .into('address') \
    .into('entry', {'name': 'web-server'}) \
    .add('ip-netmask', text='192.168.1.1/32') \
    .root_up()

# Get the XML and create a query
xml = builder.build()
query = XmlQuery(xml)

# Find the address element using XPathBuilder
xpath = XPathBuilder().anywhere().element('entry').with_attribute('name', 'web-server').build()
address_element = query.find(xpath).first()

# Create an XmlNode for easier manipulation
if address_element:
    address = XmlNode(address_element)
    # Add description and tag
    address.add_child('description', text='Main web server')
    tag_node = address.add_child('tag')
    tag_node.add_child('member', text='web')

# Create a different version to compare against
modified_builder = XmlBuilder('config')
modified_builder.into('devices') \
    .into('entry', {'name': 'localhost.localdomain'}) \
    .into('vsys') \
    .into('entry', {'name': 'vsys1'}) \
    .into('address') \
    .into('entry', {'name': 'web-server'}) \
    .add('ip-netmask', text='192.168.1.2/32') \
    .add('description', text='Web server') \
    .root_up()

modified_xml = modified_builder.build()

# Compare the two versions
diff = XmlDiff(xml.element, modified_xml.element)
diff.compare()
diffs = diff.get_diffs()

# Print the differences
for item in diffs:
    print(item)  # Uses __repr__ to format diff items
```

These abstractions significantly simplify working with XML in PANFlow, making your code more readable and maintainable.