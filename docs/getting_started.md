# Getting Started with PANFlow

This guide will help you install and start using PANFlow for PAN-OS XML configuration management.

## Prerequisites

- Python 3.7 or newer
- pip or Poetry for package management
- Basic familiarity with PAN-OS configurations
- Access to PAN-OS XML configuration files

## Installation

### Using pip

```bash
pip install panflow
```

### Using Poetry

```bash
poetry add panflow
```

### From Source

```bash
git clone https://github.com/yourusername/panflow.git
cd panflow
pip install -e .
```

## Quick Start

Here's a simple example to get you started:

```python
from panflow import PANFlowConfig

# Load a configuration file
config = PANFlowConfig("firewall.xml")

# List all address objects in shared context
addresses = config.get_objects("address", "shared")
for name, props in addresses.items():
    print(f"Address: {name}, IP: {props.get('ip-netmask', 'N/A')}")

# Add a new address object
properties = {
    "ip-netmask": "192.168.1.100/32",
    "description": "New server"
}
config.add_object("address", "new-server", properties, "shared")

# Save the modified configuration
config.save("updated-firewall.xml")
```

## CLI Usage

PANFlow provides a comprehensive CLI for working with configurations:

```bash
# List all address objects
panflow object list --config firewall.xml --type address --context shared

# Add a new address object
panflow object add --config firewall.xml --type address --name web-server \
  --properties properties.json --output updated.xml

# Generate report of unused objects
panflow report unused-objects --config firewall.xml --output report.json
```

For more CLI examples, see the [CLI Reference](cli_reference.md).

## Working with Different Contexts

PANFlow supports different contexts in PAN-OS configurations:

```python
# Working with shared context
shared_objects = config.get_objects("address", "shared")

# Working with device group context (Panorama)
dg_objects = config.get_objects("address", "device_group", device_group="my-device-group")

# Working with vsys context (Firewall)
vsys_objects = config.get_objects("address", "vsys", vsys="vsys1")

# Working with template context (Panorama)
template_objects = config.get_objects("address", "template", template="my-template")
```

## Error Handling

PANFlow provides standardized error handling with specific exception types:

```python
from panflow import PANFlowError, ObjectNotFoundError

try:
    obj = config.get_object("address", "nonexistent", "shared")
except ObjectNotFoundError:
    print("Object not found")
except PANFlowError as e:
    print(f"Other error: {e}")
```

## Next Steps

- Explore the [Tutorials](tutorials/index.md) for specific use cases
- Check the [Examples](examples/index.md) for more code samples
- See the [API Reference](api/index.md) for detailed documentation