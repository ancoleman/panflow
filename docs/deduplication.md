# Deduplication Feature Documentation

The deduplication feature in PANFlow helps identify and merge duplicate objects in PAN-OS configurations. This improves configuration management, reduces redundancy, and simplifies maintenance.

## Overview

Duplicate objects in PAN-OS configurations are common, especially in environments where multiple administrators make changes or when configurations grow organically over time. The deduplication engine identifies objects with the same values but different names and merges them, updating all references to point to the single retained object.

## Access Methods

Deduplication functionality can be accessed through three interfaces:

1. **CLI Commands** - Using the `deduplicate` namespace as documented below
2. **API** - Programmatically through the DeduplicationEngine class
3. **Natural Language Query (NLQ)** - Using natural language commands like "show duplicated address objects" or "clean up duplicated service objects"

## Supported Object Types

The deduplication engine supports the following object types:

- **Address Objects** - IP addresses (ip-netmask), FQDNs, and IP ranges
- **Service Objects** - TCP/UDP services with port definitions, including ICMP, SCTP, and ICMP6
- **Tag Objects** - Tags with color and comment attributes

## Command Structure

The deduplication functionality is organized into several commands under the `deduplicate` namespace:

```
panflow deduplicate <command> [options]
```

Available commands:
- `find` - Find duplicate objects without making changes
- `merge` - Find and merge duplicate objects
- `simulate` - Simulate deduplication and generate impact analysis
- `report` - Generate a comprehensive deduplication report
- `hierarchical` - Find and merge duplicates across device group hierarchy (Panorama only)

## Common Options

These options apply to most deduplication commands:

- `--config, -c TEXT` - Path to XML configuration file (required)
- `--type, -t TEXT` - Type of object to deduplicate (address, service, tag) (required)
- `--device-type, -d TEXT` - Device type (firewall or panorama) (default: firewall)
- `--context TEXT` - Context (shared, device_group, vsys, template) (default: shared)
- `--device-group TEXT` - Device group name (for Panorama device_group context)
- `--vsys TEXT` - VSYS name (for firewall vsys context) (default: vsys1)
- `--template TEXT` - Template name (for Panorama template context)
- `--version TEXT` - PAN-OS version (auto-detected if not specified)

## Finding Duplicate Objects

The `find` command identifies duplicate objects without making changes:

```bash
panflow deduplicate find --config CONFIG --type TYPE [options]
```

### Options

- `--output, -o TEXT` - Output file for results (JSON format)
- `--pattern, -p TEXT` - Pattern to filter objects (e.g., "10.0.0" for addresses)
- `--include-file TEXT` - JSON file with list of object names to include
- `--exclude-file TEXT` - JSON file with list of object names to exclude
- `--min-group-size, -g INT` - Minimum number of objects in a duplicate group (default: 2)

### Example

```bash
panflow deduplicate find --config firewall.xml --type address --output duplicates.json
```

## Merging Duplicate Objects

The `merge` command identifies and merges duplicate objects:

```bash
panflow deduplicate merge --config CONFIG --type TYPE --output OUTPUT [options]
```

### Options

- `--strategy, -s TEXT` - Strategy for choosing primary object (first, shortest, longest, alphabetical, context_priority) (default: first)
- `--pattern, -p TEXT` - Pattern to filter objects (e.g., "10.0.0" for addresses)
- `--include-file TEXT` - JSON file with list of object names to include
- `--exclude-file TEXT` - JSON file with list of object names to exclude
- `--dry-run` - Show what would be done without making changes
- `--impact-report, -i TEXT` - Generate a detailed impact report and save to this file

### Example

```bash
panflow deduplicate merge --config firewall.xml --type address --output deduped.xml --strategy alphabetical
```

## Hierarchical Deduplication (Panorama Only)

For Panorama configurations, the `hierarchical` command provides advanced deduplication that considers the device group hierarchy:

```bash
panflow deduplicate hierarchical find --config CONFIG --type TYPE [options]
panflow deduplicate hierarchical merge --config CONFIG --type TYPE --output OUTPUT [options]
```

### Additional Hierarchical Options

- `--strategy TEXT` - Strategy for choosing primary object (highest_level, first, shortest, longest, alphabetical, pattern) (default: highest_level)
- `--pattern-filter TEXT` - Regular expression pattern to prioritize object names (for 'pattern' strategy)
- `--allow-merging-with-upper-level` - Whether to prioritize objects in parent contexts (default: True)

### Example

```bash
# Find hierarchical duplicates prioritizing shared objects
panflow deduplicate hierarchical find --config panorama.xml --type address --output hierarchical_duplicates.json

# Merge duplicates keeping objects from highest hierarchy level
panflow deduplicate hierarchical merge --config panorama.xml --type address --output merged.xml --strategy highest_level
```

## Selection Strategies

When merging duplicates, one object must be kept while others are removed. The following strategies are available:

### Standard Strategies
- `first` - Keep the first object encountered (default)
- `shortest` - Keep the object with the shortest name
- `longest` - Keep the object with the longest name
- `alphabetical` - Keep the object with the first name alphabetically

### Context-Aware Strategies
- `context_priority` - Prioritize objects based on context hierarchy (shared > device groups > vsys)
- `highest_level` - (Hierarchical only) Prioritize objects in parent contexts and higher-level device groups
- `pattern` - (Hierarchical only) Prioritize objects matching a regular expression pattern

## Filtering

Deduplication can be controlled using several filtering mechanisms:

### Pattern Filtering

The `--pattern` option filters objects based on a text pattern:

```bash
panflow deduplicate merge --config firewall.xml --type address --output deduped.xml --pattern "10.1.1"
```

This would only consider address objects containing "10.1.1" in their name or value.

### Include/Exclude Lists

You can provide JSON files with specific object names to include or exclude:

**include.json:**
```json
["web-server", "db-server", "app-server"]
```

**exclude.json:**
```json
["critical-server", "production-*"]
```

```bash
panflow deduplicate merge --config firewall.xml --type address --output deduped.xml --include-file include.json --exclude-file exclude.json
```

## Reference Tracking

The deduplication engine tracks references to objects in:

### Address Objects
- Address groups (member references)
- Security policies (source and destination fields)
- NAT policies (source and destination translation fields)

### Service Objects
- Service groups (member references)
- Security policies (service field)
- NAT policies (service and translated-service fields)

### Tag Objects
- Object tags (address, service, address-group, service-group objects)
- Policy tags (security and NAT policies)

## Device Group Hierarchy Support

For Panorama configurations, the deduplication engine:

1. **Builds device group hierarchy** - Automatically detects parent-child relationships between device groups
2. **Prioritizes by level** - Higher-level device groups take precedence over child device groups
3. **Considers shared context** - Shared objects have the highest priority in hierarchical operations
4. **Tracks context information** - Maintains context details (shared, device group name, hierarchy level) for each object

## Impact Analysis

The impact analysis features show what changes would be made by deduplication:

```bash
panflow deduplicate simulate --config firewall.xml --type address --output impact.json --detailed
```

The generated report includes:
- Objects to be kept/deleted with context information
- Policy impacts across all policy types
- Group impacts and member changes
- Reference changes with detailed paths

## Object Value Detection

The deduplication engine identifies duplicate objects based on their configuration values:

### Address Objects
- **ip-netmask**: IP address with subnet mask (e.g., "192.168.1.1/24")
- **fqdn**: Fully qualified domain name (e.g., "www.example.com")
- **ip-range**: IP address range (e.g., "192.168.1.1-192.168.1.10")

### Service Objects
- **TCP/UDP**: Protocol type, destination port, and optional source port
- **ICMP/ICMP6**: Protocol type, ICMP type, and optional ICMP code
- **SCTP**: Protocol type and port information

### Tag Objects
- **color**: Tag color value (or "none" if not specified)
- **comments**: Tag comment text (or empty string if not specified)

## Practical Examples

### Finding All Duplicate Address Objects

```bash
panflow deduplicate find --config firewall.xml --type address --output duplicates.json
```

### Merging Duplicate Services with Name Pattern

```bash
panflow deduplicate merge --config firewall.xml --type service --output deduped.xml --pattern "HTTP"
```

### Simulating Impact Before Deduplication

```bash
panflow deduplicate simulate --config firewall.xml --type address --output impact.json --detailed
```

### Generating Comprehensive Deduplication Report

```bash
panflow deduplicate report --config firewall.xml --output report.json
```

### Selective Deduplication with Dry Run

```bash
panflow deduplicate merge --config firewall.xml --type tag --output deduped.xml --include-file important_tags.json --dry-run
```

### Hierarchical Deduplication Examples

```bash
# Find duplicates across entire Panorama hierarchy
panflow deduplicate hierarchical find --config panorama.xml --type address

# Merge duplicates keeping shared objects as primary
panflow deduplicate hierarchical merge --config panorama.xml --type address --output consolidated.xml --strategy highest_level

# Use pattern-based selection for hierarchical merge
panflow deduplicate hierarchical merge --config panorama.xml --type service --output consolidated.xml --strategy pattern --pattern-filter "^std-"
```

## Natural Language Query Examples

PANFlow supports natural language for deduplication operations through the NLQ module:

### Finding Duplicates with NLQ

```bash
# Find duplicate address objects
panflow nlq query "show me all duplicated address objects" --config firewall.xml

# Find duplicate service objects
panflow nlq query "find duplicate service objects" --config firewall.xml

# Find all types of duplicates
panflow nlq query "show all duplicate objects" --config firewall.xml
```

### Deduplicating with NLQ

```bash
# Deduplicate address objects
panflow nlq query "cleanup duplicated address objects" --config firewall.xml --output deduped.xml

# Deduplicate services with dry run
panflow nlq query "deduplicate service objects but don't make changes" --config firewall.xml

# Deduplicate in specific context
panflow nlq query "cleanup duplicate address objects in device group DG1" --config panorama.xml --output deduped.xml
```

## API Usage

The DeduplicationEngine can be used programmatically:

```python
from panflow.core.deduplication import DeduplicationEngine

# Initialize the engine
engine = DeduplicationEngine(
    tree=config_tree,
    device_type="panorama",
    context_type="device_group",
    version="10.2",
    device_group="production-dg"
)

# Find duplicates
duplicates, references = engine.find_duplicates("address", reference_tracking=True)

# Merge duplicates
changes = engine.merge_duplicates(duplicates, references, primary_name_strategy="shortest")

# For hierarchical operations (Panorama only)
hierarchical_duplicates, hierarchical_references, contexts = engine.find_hierarchical_duplicates(
    "address", 
    allow_merging_with_upper_level=True,
    reference_tracking=True
)

# Merge with hierarchical awareness
hierarchical_changes = engine.merge_hierarchical_duplicates(
    hierarchical_duplicates,
    hierarchical_references,
    contexts,
    primary_name_strategy="highest_level"
)
```

## Best Practices

1. **Always run simulation first**:
   ```bash
   panflow deduplicate simulate --config firewall.xml --type address --output impact.json --detailed
   ```

2. **Use dry run to verify changes**:
   ```bash
   panflow deduplicate merge --config firewall.xml --type address --output deduped.xml --dry-run
   ```

3. **Backup configuration before proceeding**:
   ```bash
   cp firewall.xml firewall.backup.xml
   ```

4. **Start with specific object types**:
   - Address objects often have the most duplicates
   - Service objects typically have fewer dependencies

5. **Choose appropriate strategy based on naming conventions**:
   - `alphabetical` works well for standardized names
   - `shortest` works well for consolidating to simpler names
   - `highest_level` is recommended for Panorama hierarchical deduplication

6. **For Panorama configurations**:
   - Use hierarchical deduplication to consider device group relationships
   - Review device group hierarchy before merging
   - Consider impact on child device groups

## Troubleshooting

- **No duplicates found**: Verify object type and context settings
- **Changes not as expected**: Check for references in different contexts
- **Error in deduplication**: Enable verbose logging with `-v` flag
- **Hierarchical issues**: Verify device group hierarchy is correctly detected
- **Reference tracking failures**: Check XPath mappings for your PAN-OS version

## Output Format

The JSON output of the deduplication commands follows this general structure:

```json
{
  "summary": {
    "object_type": "address",
    "duplicate_sets": 5,
    "duplicate_count": 12,
    "objects_to_delete": 7,
    "references_to_update": 15,
    "strategy": "first",
    "context_type": "device_group",
    "device_group": "production-dg"
  },
  "duplicate_sets": {
    "ip-netmask:10.0.0.1/32": [
      {"name": "server1", "context": {"type": "shared"}},
      {"name": "webserver", "context": {"type": "device_group", "device_group": "web-dg"}},
      {"name": "www-1", "context": {"type": "device_group", "device_group": "web-dg"}}
    ],
    "fqdn:example.com": [
      {"name": "example", "context": {"type": "shared"}},
      {"name": "example-fqdn", "context": {"type": "device_group", "device_group": "app-dg"}}
    ]
  },
  "to_be_kept": [
    {"name": "server1", "value": "ip-netmask:10.0.0.1/32", "context": {"type": "shared"}},
    {"name": "example", "value": "fqdn:example.com", "context": {"type": "shared"}}
  ],
  "to_be_deleted": [
    {"name": "webserver", "replaced_by": "server1", "value": "ip-netmask:10.0.0.1/32", "context": {"type": "device_group", "device_group": "web-dg"}},
    {"name": "www-1", "replaced_by": "server1", "value": "ip-netmask:10.0.0.1/32", "context": {"type": "device_group", "device_group": "web-dg"}},
    {"name": "example-fqdn", "replaced_by": "example", "value": "fqdn:example.com", "context": {"type": "device_group", "device_group": "app-dg"}}
  ],
  "policy_impacts": {
    "security": [
      {"policy_name": "Allow-Web", "field": "source", "old_value": "webserver", "new_value": "server1", "context": "pre-security"}
    ],
    "nat": [
      {"policy_name": "NAT-Web", "field": "destination", "old_value": "www-1", "new_value": "server1", "context": "pre-nat"}
    ]
  },
  "group_impacts": [
    {"group_name": "Web-Servers", "group_type": "address-group", "old_member": "webserver", "new_member": "server1"}
  ]
}
```