# XML Abstractions

PANFlow provides a set of high-level abstractions for working with XML, making it easier to create, modify, and query XML elements with a more Pythonic interface.

## XmlNode

`XmlNode` is a wrapper around lxml's Element that provides a more intuitive interface:

```python
from panflow.core import XmlNode

# Create a node from an existing Element
node = XmlNode(element)

# Create a node from XML string
node = XmlNode.from_string('<address name="web-server"><ip-netmask>192.168.1.1/32</ip-netmask></address>')

# Create a new node
node = XmlNode.create('address', {'name': 'web-server'})

# Get node attributes and properties
tag = node.tag  # 'address'
name = node.get_attribute('name')  # 'web-server'
children = node.children  # List of child nodes

# Modify node
node.text = "Some text content"
node.set_attribute('description', 'Web server')
node.delete_attribute('temp')

# Navigation
parent = node.parent
child = node.child('ip-netmask')

# Add children
ip_node = node.add_child('ip-netmask', text='192.168.1.1/32')
desc_node = node.add_child('description', text='Web server')

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
from panflow.core import XmlBuilder

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
from panflow.core import XPathBuilder

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
from panflow.core import XmlQuery, XmlNode

# Create a query from an XmlNode
node = XmlNode.from_string('<config>...</config>')
query = XmlQuery.from_node(node)

# Find elements
addresses = query.find('.//address/entry')

# Filter elements
web_servers = addresses.has_attribute('name').has_child('tag').has_text_containing('web')

# Get information
names = web_servers.attribute('name')  # List of names
count = web_servers.count()  # Number of web servers

# Transformation
server_data = web_servers.map(lambda node: {
    'name': node.get_attribute('name'),
    'ip': node.find('./ip-netmask').text if node.find('./ip-netmask') else None
})

# Iteration
web_servers.each(lambda node: print(f"Server: {node.get_attribute('name')}"))
```

## XmlDiff

`XmlDiff` helps identify differences between XML elements:

```python
from panflow.core import XmlDiff, DiffType

# Compare two XML elements
diffs = XmlDiff.compare(source_node.element, target_node.element)

# Process the differences
for diff in diffs:
    if diff.type == DiffType.ADDED:
        print(f"Added: {diff.path}")
    elif diff.type == DiffType.REMOVED:
        print(f"Removed: {diff.path}")
    elif diff.type == DiffType.CHANGED:
        print(f"Changed: {diff.path} from {diff.source_value} to {diff.target_value}")

# Format the differences for display
formatted_diff = XmlDiff.format_diff(diffs, format_type='markdown')
```

## Combined Example

Here's a complete example showing how to use these abstractions together:

```python
from panflow.core import XmlNode, XmlBuilder, XPathBuilder, XmlQuery, XmlDiff

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
query = XmlQuery.from_node(xml)

# Find the address element
address = query.find(
    XPathBuilder().anywhere().element('entry').with_name('web-server').build()
).first()

# Modify the address
if address:
    address.add_child('description', text='Main web server')
    address.add_child('tag').add_child('member', text='web')

# Create a different version
modified_builder = XmlBuilder('config')
modified_builder.into('devices') \
    .into('entry', {'name': 'localhost.localdomain'}) \
    .into('vsys') \
    .into('entry', {'name': 'vsys1'}) \
    .into('address') \
    .into('entry', {'name': 'web-server'}) \
    .add('ip-netmask', text='192.168.1.2/32') \  # Different IP
    .add('description', text='Web server') \
    .root_up()

modified_xml = modified_builder.build()

# Compare the two versions
diffs = XmlDiff.compare(xml.element, modified_xml.element)
formatted_diff = XmlDiff.format_diff(diffs, format_type='text')
print(formatted_diff)
```

These abstractions significantly simplify working with XML in PANFlow, making your code more readable and maintainable.