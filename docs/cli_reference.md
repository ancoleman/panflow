# PANFlow CLI Reference

This document provides comprehensive documentation for the PANFlow command-line interface.

## Global Options

These options can be used with any command:

```
--verbose, -v         Enable verbose output
--quiet, -q           Suppress console output
--log-level, -l TEXT  Set log level (debug, info, warning, error, critical)
--log-file, -f TEXT   Log to file
--help                Show help message and exit
```

## Command Structure

PANFlow commands are organized in a hierarchical structure:

```
panflow [global options] <command> [command options] <subcommand> [subcommand options]
```

## Object Management Commands

### List Objects

List objects of a specific type:

```bash
panflow object list --config CONFIG --type TYPE [options]
```

Options:
- `--config, -c TEXT`: Path to XML configuration file (required)
- `--type, -t TEXT`: Type of object to list (address, service, etc.) (required)
- `--output, -o TEXT`: Output file for results (JSON format)
- `--device-type, -d TEXT`: Device type (firewall or panorama) (default: firewall)
- `--context TEXT`: Context (shared, device_group, vsys, template) (default: shared)
- `--device-group TEXT`: Device group name (for Panorama device_group context)
- `--vsys TEXT`: VSYS name (for firewall vsys context) (default: vsys1)
- `--template TEXT`: Template name (for Panorama template context)
- `--version TEXT`: PAN-OS version (auto-detected if not specified)

### Add Object

Add a new object:

```bash
panflow object add --config CONFIG --type TYPE --name NAME --properties PROPERTIES --output OUTPUT [options]
```

Options:
- `--config, -c TEXT`: Path to XML configuration file (required)
- `--type, -t TEXT`: Type of object to add (address, service, etc.) (required)
- `--name, -n TEXT`: Name of the object (required)
- `--properties, -p TEXT`: JSON file with object properties (required)
- `--output, -o TEXT`: Output file for updated configuration (required)
- `--device-type, -d TEXT`: Device type (firewall or panorama) (default: firewall)
- `--context TEXT`: Context (shared, device_group, vsys, template) (default: shared)
- `--device-group TEXT`: Device group name (for Panorama device_group context)
- `--vsys TEXT`: VSYS name (for firewall vsys context) (default: vsys1)
- `--template TEXT`: Template name (for Panorama template context)
- `--version TEXT`: PAN-OS version (auto-detected if not specified)

### Update Object

Update an existing object:

```bash
panflow object update --config CONFIG --type TYPE --name NAME --properties PROPERTIES --output OUTPUT [options]
```

Options:
- (Same as "Add Object")

### Delete Object

Delete an object:

```bash
panflow object delete --config CONFIG --type TYPE --name NAME --output OUTPUT [options]
```

Options:
- `--config, -c TEXT`: Path to XML configuration file (required)
- `--type, -t TEXT`: Type of object to delete (address, service, etc.) (required)
- `--name, -n TEXT`: Name of the object (required)
- `--output, -o TEXT`: Output file for updated configuration (required)
- `--device-type, -d TEXT`: Device type (firewall or panorama) (default: firewall)
- `--context TEXT`: Context (shared, device_group, vsys, template) (default: shared)
- `--device-group TEXT`: Device group name (for Panorama device_group context)
- `--vsys TEXT`: VSYS name (for firewall vsys context) (default: vsys1)
- `--template TEXT`: Template name (for Panorama template context)
- `--version TEXT`: PAN-OS version (auto-detected if not specified)

### Filter Objects

Filter objects based on criteria:

```bash
panflow object filter --config CONFIG --type TYPE --criteria CRITERIA [options]
```

Options:
- `--config, -c TEXT`: Path to XML configuration file (required)
- `--type, -t TEXT`: Type of object to filter (address, service, etc.) (required)
- `--criteria TEXT`: JSON file with filter criteria (required)
- `--output, -o TEXT`: Output file for results (JSON format)
- `--device-type, -d TEXT`: Device type (firewall or panorama) (default: firewall)
- `--context TEXT`: Context (shared, device_group, vsys, template) (default: shared)
- `--device-group TEXT`: Device group name (for Panorama device_group context)
- `--vsys TEXT`: VSYS name (for firewall vsys context) (default: vsys1)
- `--template TEXT`: Template name (for Panorama template context)
- `--version TEXT`: PAN-OS version (auto-detected if not specified)

## Policy Management Commands

### List Policies

List policies of a specific type:

```bash
panflow policy list --config CONFIG --type TYPE [options]
```

Options:
- `--config, -c TEXT`: Path to XML configuration file (required)
- `--type, -t TEXT`: Type of policy to list (security_pre_rules, nat_rules, etc.) (required)
- `--output, -o TEXT`: Output file for results (JSON format)
- `--device-type, -d TEXT`: Device type (firewall or panorama) (default: firewall)
- `--context TEXT`: Context (shared, device_group, vsys) (default: shared)
- `--device-group TEXT`: Device group name (for Panorama device_group context)
- `--vsys TEXT`: VSYS name (for firewall vsys context) (default: vsys1)
- `--version TEXT`: PAN-OS version (auto-detected if not specified)

### Bulk Update Policies

Bulk update policies matching criteria:

```bash
panflow policy bulk-update --config CONFIG --type TYPE --criteria CRITERIA --operations OPERATIONS --output OUTPUT [options]
```

Options:
- `--config, -c TEXT`: Path to XML configuration file (required)
- `--type, -t TEXT`: Type of policy to update (required)
- `--criteria TEXT`: JSON file with filter criteria (required)
- `--operations TEXT`: JSON file with update operations (required)
- `--output, -o TEXT`: Output file for updated configuration (required)
- `--device-type, -d TEXT`: Device type (firewall or panorama) (default: firewall)
- `--context TEXT`: Context (shared, device_group, vsys) (default: shared)
- `--device-group TEXT`: Device group name
- `--vsys TEXT`: VSYS name (default: vsys1)
- `--version TEXT`: PAN-OS version

## Group Management Commands

### Add Member to Group

Add a member to a group:

```bash
panflow group add-member --config CONFIG --type TYPE --group GROUP --member MEMBER --output OUTPUT [options]
```

Options:
- `--config, -c TEXT`: Path to XML configuration file (required)
- `--type, -t TEXT`: Type of group (address_group, service_group, etc.) (required)
- `--group, -g TEXT`: Name of the group (required)
- `--member, -m TEXT`: Name of the member to add (required)
- `--output, -o TEXT`: Output file for updated configuration (required)
- `--device-type, -d TEXT`: Device type (firewall or panorama) (default: firewall)
- `--context TEXT`: Context (shared, device_group, vsys, template) (default: shared)
- `--device-group TEXT`: Device group name (for Panorama device_group context)
- `--vsys TEXT`: VSYS name (for firewall vsys context) (default: vsys1)
- `--template TEXT`: Template name (for Panorama template context)
- `--version TEXT`: PAN-OS version (auto-detected if not specified)

## Report Commands

### Unused Objects Report

Generate report of unused objects:

```bash
panflow report unused-objects --config CONFIG --output OUTPUT [options]
```

Options:
- `--config, -c TEXT`: Path to XML configuration file (required)
- `--output, -o TEXT`: Output file for report (JSON format) (required)
- `--device-type, -d TEXT`: Device type (firewall or panorama) (default: firewall)
- `--context TEXT`: Context (shared, device_group, vsys, template) (default: shared)
- `--device-group TEXT`: Device group name (for Panorama device_group context)
- `--vsys TEXT`: VSYS name (for firewall vsys context) (default: vsys1)
- `--template TEXT`: Template name (for Panorama template context)
- `--version TEXT`: PAN-OS version (auto-detected if not specified)

## Configuration Commands

### Validate Configuration

Validate XML configuration structure:

```bash
panflow config validate --config CONFIG [options]
```

Options:
- `--config, -c TEXT`: Path to XML configuration file (required)
- `--device-type, -d TEXT`: Device type (firewall or panorama) (default: firewall)
- `--version TEXT`: PAN-OS version (auto-detected if not specified)

## Deduplication Commands

PANFlow provides several commands for finding and merging duplicate objects in the configuration. For detailed documentation, see [Deduplication Feature Documentation](deduplication.md).

### Find Duplicate Objects

Find duplicate objects without making changes:

```bash
panflow deduplicate find --config CONFIG --type TYPE [options]
```

Options:
- `--config, -c TEXT`: Path to XML configuration file (required)
- `--type, -t TEXT`: Type of object to deduplicate (address, service, tag) (required)
- `--output, -o TEXT`: Output file for results (JSON format)
- `--device-type, -d TEXT`: Device type (firewall or panorama) (default: firewall)
- `--context TEXT`: Context (shared, device_group, vsys) (default: shared)
- `--device-group TEXT`: Device group name
- `--vsys TEXT`: VSYS name (default: vsys1)
- `--pattern, -p TEXT`: Pattern to filter objects (e.g., "10.0.0" for addresses)
- `--include-file TEXT`: JSON file with list of object names to include
- `--exclude-file TEXT`: JSON file with list of object names to exclude
- `--min-group-size, -g INT`: Minimum number of objects in a duplicate group (default: 2)
- `--version TEXT`: PAN-OS version

### Merge Duplicate Objects

Find and merge duplicate objects:

```bash
panflow deduplicate merge --config CONFIG --type TYPE --output OUTPUT [options]
```

Options:
- `--config, -c TEXT`: Path to XML configuration file (required)
- `--type, -t TEXT`: Type of object to deduplicate (address, service, tag) (required)
- `--output, -o TEXT`: Output file for updated configuration (required)
- `--device-type, -d TEXT`: Device type (firewall or panorama) (default: firewall)
- `--context TEXT`: Context (shared, device_group, vsys) (default: shared)
- `--device-group TEXT`: Device group name
- `--vsys TEXT`: VSYS name (default: vsys1)
- `--strategy, -s TEXT`: Strategy for choosing primary object (first, shortest, longest, alphabetical) (default: first)
- `--pattern, -p TEXT`: Pattern to filter objects (e.g., "10.0.0" for addresses)
- `--include-file TEXT`: JSON file with list of object names to include
- `--exclude-file TEXT`: JSON file with list of object names to exclude
- `--dry-run`: Show what would be done without making changes
- `--impact-report, -i TEXT`: Generate a detailed impact report and save to this file
- `--version TEXT`: PAN-OS version

### Simulate Deduplication

Simulate deduplication and generate impact analysis without making changes:

```bash
panflow deduplicate simulate --config CONFIG --type TYPE --output OUTPUT [options]
```

Options:
- `--config, -c TEXT`: Path to XML configuration file (required)
- `--type, -t TEXT`: Type of object to deduplicate (address, service, tag) (required)
- `--output, -o TEXT`: Output file for impact report (JSON format) (required)
- `--device-type, -d TEXT`: Device type (firewall or panorama) (default: firewall)
- `--context TEXT`: Context (shared, device_group, vsys) (default: shared)
- `--device-group TEXT`: Device group name
- `--vsys TEXT`: VSYS name (default: vsys1)
- `--strategy, -s TEXT`: Strategy for choosing primary object (first, shortest, longest, alphabetical) (default: first)
- `--pattern, -p TEXT`: Pattern to filter objects (e.g., "10.0.0" for addresses)
- `--include-file TEXT`: JSON file with list of object names to include
- `--exclude-file TEXT`: JSON file with list of object names to exclude
- `--detailed, -d`: Include detailed policy and reference information
- `--version TEXT`: PAN-OS version

### Generate Deduplication Report

Generate a comprehensive deduplication report for the configuration:

```bash
panflow deduplicate report --config CONFIG --output OUTPUT [options]
```

Options:
- `--config, -c TEXT`: Path to XML configuration file (required)
- `--output, -o TEXT`: Output file for report (JSON format) (required)
- `--types, -t LIST`: Types of objects to analyze (address, service, tag). If not specified, all types are analyzed.
- `--device-type, -d TEXT`: Device type (firewall or panorama) (default: firewall)
- `--context TEXT`: Context (shared, device_group, vsys) (default: shared)
- `--device-group TEXT`: Device group name
- `--vsys TEXT`: VSYS name (default: vsys1)
- `--version TEXT`: PAN-OS version

## Merge Commands

### Merge Policy

Merge a policy from source to target configuration:

```bash
panflow merge policy --source-config SOURCE_CONFIG --target-config TARGET_CONFIG --type TYPE --name NAME --output OUTPUT [options]
```

Options:
- `--source-config TEXT`: Path to source XML configuration file (required)
- `--target-config TEXT`: Path to target XML configuration file (required)
- `--type, -t TEXT`: Type of policy to merge (security_pre_rules, nat_rules, etc.) (required)
- `--name, -n TEXT`: Name of the policy to merge (required)
- `--source-context TEXT`: Source context (shared, device_group, vsys) (default: shared)
- `--target-context TEXT`: Target context (shared, device_group, vsys) (default: shared)
- `--source-dg TEXT`: Source device group name
- `--target-dg TEXT`: Target device group name
- `--source-vsys TEXT`: Source VSYS name (default: vsys1)
- `--target-vsys TEXT`: Target VSYS name (default: vsys1)
- `--source-type TEXT`: Source device type (firewall or panorama) (default: panorama)
- `--target-type TEXT`: Target device type (firewall or panorama) (default: panorama)
- `--source-version TEXT`: Source PAN-OS version
- `--target-version TEXT`: Target PAN-OS version
- `--position TEXT`: Position to add policy (top, bottom, before, after) (default: bottom)
- `--ref-policy TEXT`: Reference policy for before/after position
- `--skip-if-exists/--replace`: Skip if policy already exists (deprecated, use conflict_strategy instead) (default: True)
- `--copy-references/--no-copy-references`: Copy object references (default: True)
- `--conflict-strategy TEXT`: Strategy for resolving conflicts: skip, overwrite, merge, rename, keep_target, keep_source (default: skip)
- `--dry-run`: Preview changes without modifying the target configuration
- `--output, -o TEXT`: Output file for updated configuration (required)

### Merge Policies

Merge multiple policies:

```bash
panflow merge policies --source-config SOURCE_CONFIG --target-config TARGET_CONFIG --type TYPE [--names-file NAMES_FILE | --criteria CRITERIA] --output OUTPUT [options]
```

Options:
- (Similar to "Merge Policy" with additional options for selecting multiple policies)

### Merge All Policies

Merge all policy types:

```bash
panflow merge all --source-config SOURCE_CONFIG --target-config TARGET_CONFIG --output OUTPUT [options]
```

Options:
- (Similar to "Merge Policy" but without policy type and name)

### Merge Object

Merge a single object:

```bash
panflow merge object --source-config SOURCE_CONFIG --target-config TARGET_CONFIG --type TYPE --name NAME --output OUTPUT [options]
```

Options:
- `--source-config TEXT`: Path to source XML configuration file (required)
- `--target-config TEXT`: Path to target XML configuration file (required)
- `--type, -t TEXT`: Type of object to merge (address, service, etc.) (required)
- `--name, -n TEXT`: Name of the object to merge (required)
- `--source-context TEXT`: Source context (shared, device_group, vsys) (default: shared)
- `--target-context TEXT`: Target context (shared, device_group, vsys) (default: shared)
- `--source-dg TEXT`: Source device group name
- `--target-dg TEXT`: Target device group name
- `--source-vsys TEXT`: Source VSYS name (default: vsys1)
- `--target-vsys TEXT`: Target VSYS name (default: vsys1)
- `--source-type TEXT`: Source device type (firewall or panorama) (default: panorama)
- `--target-type TEXT`: Target device type (firewall or panorama) (default: panorama)
- `--source-version TEXT`: Source PAN-OS version
- `--target-version TEXT`: Target PAN-OS version
- `--skip-if-exists/--replace`: Skip if object already exists (deprecated, use conflict_strategy instead) (default: True)
- `--copy-references/--no-copy-references`: Copy group members (default: True)
- `--conflict-strategy TEXT`: Strategy for resolving conflicts (default: skip)
- `--dry-run`: Preview changes without modifying the target configuration
- `--output, -o TEXT`: Output file for updated configuration (required)

### Merge Objects

Merge multiple objects:

```bash
panflow merge objects --source-config SOURCE_CONFIG --target-config TARGET_CONFIG --type TYPE [--names-file NAMES_FILE | --criteria CRITERIA] --output OUTPUT [options]
```

Options:
- (Similar to "Merge Object" with additional options for selecting multiple objects)

### Merge All Objects

Merge all object types:

```bash
panflow merge all-objects --source-config SOURCE_CONFIG --target-config TARGET_CONFIG --output OUTPUT [options]
```

Options:
- (Similar to "Merge Object" but without object type and name)

## Examples

### List all address objects in shared context

```bash
panflow object list --config firewall.xml --type address --context shared
```

### Add a new address object

```bash
panflow object add --config firewall.xml --type address --name web-server \
  --properties web-server.json --output updated.xml
```

### Generate a report of unused objects

```bash
panflow report unused-objects --config firewall.xml --output unused.json
```

### Bulk update security policies matching criteria

```bash
panflow policy bulk-update --config firewall.xml --type security_rules \
  --criteria criteria.json --operations operations.json --output updated.xml
```

### Find duplicate objects and analyze them

```bash
panflow deduplicate find --config firewall.xml --type address --output duplicates.json
```

### Generate detailed deduplication simulation

```bash
panflow deduplicate simulate --config firewall.xml --type service --output impact.json --detailed
```

### Merge duplicate objects with specific strategy

```bash
panflow deduplicate merge --config firewall.xml --type address --strategy alphabetical --output deduped.xml
```

### Generate comprehensive deduplication report

```bash
panflow deduplicate report --config firewall.xml --output dedup_report.json
```

### Merge a policy between configurations

```bash
panflow merge policy --source-config source.xml --target-config target.xml \
  --type security_pre_rules --name allow-web --output updated.xml
```