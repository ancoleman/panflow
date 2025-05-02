# PANFlow CLI Usage Guide

This guide provides a comprehensive overview of the command-line interface (CLI) for PANFlow, which allows you to work with Palo Alto Networks PAN-OS XML configurations efficiently.

## Table of Contents

- [Installation](#installation)
- [Global Options](#global-options)
- [Object Commands](#object-commands)
- [Policy Commands](#policy-commands)
- [Group Commands](#group-commands)
- [Report Commands](#report-commands)
- [Configuration Commands](#configuration-commands)
- [Bulk Operations](#bulk-operations)
- [Deduplication](#deduplication)
- [Logging](#logging)
- [Usage Examples](#usage-examples)
- [Tips and Best Practices](#tips-and-best-practices)

## Installation

1. Ensure you have Python 3.6+ installed
2. Install the required packages:

```bash
pip install typer lxml pyyaml
```

3. Download the PAN-OS XML Utilities files or install via pip (if available as a package)

## Global Options

These options can be used with any command:

| Option | Short | Description |
|--------|-------|-------------|
| `--verbose` | `-v` | Enable verbose output (DEBUG level) |
| `--quiet` | `-q` | Suppress console output |
| `--log-level TEXT` | `-l` | Set log level (debug, info, warning, error, critical) |
| `--log-file TEXT` | `-f` | Log to file |
| `--device-type TEXT` | `-d` | Device type (firewall or panorama) |
| `--context TEXT` | | Context (shared, device_group, vsys, template) |
| `--device-group TEXT` | | Device group name (for Panorama device_group context) |
| `--vsys TEXT` | | VSYS name (for firewall vsys context) |
| `--template TEXT` | | Template name (for Panorama template context) |
| `--version TEXT` | | PAN-OS version (auto-detected if not specified) |

## Object Commands

Commands for managing address objects, service objects, and other PAN-OS objects.

### List Objects

List objects of a specific type:

```bash
python cli.py object list --config CONFIG_FILE --type OBJECT_TYPE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of object to list (e.g., address, service, etc.) (**required**)
- `--output`, `-o`: Output file for results (JSON format)

Example:
```bash
python cli.py object list --config firewall.xml --type address --context vsys --vsys vsys1
```

### Add Object

Add a new object:

```bash
python cli.py object add --config CONFIG_FILE --type OBJECT_TYPE --name NAME --properties PROPERTIES_FILE --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of object to add (**required**)
- `--name`, `-n`: Name of the object (**required**)
- `--properties`, `-p`: JSON file with object properties (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)

Example:
```bash
python cli.py object add --config firewall.xml --type address --name web-server --properties web-server.json --output updated.xml
```

### Update Object

Update an existing object:

```bash
python cli.py object update --config CONFIG_FILE --type OBJECT_TYPE --name NAME --properties PROPERTIES_FILE --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of object to update (**required**)
- `--name`, `-n`: Name of the object (**required**)
- `--properties`, `-p`: JSON file with updated object properties (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)

Example:
```bash
python cli.py object update --config firewall.xml --type address --name web-server --properties updated-server.json --output updated.xml
```

### Delete Object

Delete an object:

```bash
python cli.py object delete --config CONFIG_FILE --type OBJECT_TYPE --name NAME --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of object to delete (**required**)
- `--name`, `-n`: Name of the object (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)

Example:
```bash
python cli.py object delete --config firewall.xml --type address --name old-server --output updated.xml
```

### Filter Objects

Filter objects based on criteria:

```bash
python cli.py object filter --config CONFIG_FILE --type OBJECT_TYPE --criteria CRITERIA_FILE [--output OUTPUT_FILE] [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of object to filter (**required**)
- `--criteria`: JSON file with filter criteria (**required**)
- `--output`, `-o`: Output file for results (JSON format)

Example:
```bash
python cli.py object filter --config firewall.xml --type address --criteria filter-criteria.json --output filtered.json
```

## Policy Commands

Commands for managing security rules, NAT rules, and other PAN-OS policies.

### List Policies

List policies of a specific type:

```bash
python cli.py policy list --config CONFIG_FILE --type POLICY_TYPE [--output OUTPUT_FILE] [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of policy to list (e.g., security_pre_rules, nat_rules) (**required**)
- `--output`, `-o`: Output file for results (JSON format)

Example:
```bash
python cli.py policy list --config panorama.xml --type security_pre_rules --context device_group --device-group DG1
```

### Add Policy

Add a new policy:

```bash
python cli.py policy add --config CONFIG_FILE --type POLICY_TYPE --name NAME --properties PROPERTIES_FILE --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of policy to add (**required**)
- `--name`, `-n`: Name of the policy (**required**)
- `--properties`, `-p`: JSON file with policy properties (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)

Example:
```bash
python cli.py policy add --config panorama.xml --type security_pre_rules --name allow-web --properties web-rule.json --output updated.xml
```

### Update Policy

Update an existing policy:

```bash
python cli.py policy update --config CONFIG_FILE --type POLICY_TYPE --name NAME --properties PROPERTIES_FILE --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of policy to update (**required**)
- `--name`, `-n`: Name of the policy (**required**)
- `--properties`, `-p`: JSON file with updated policy properties (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)

Example:
```bash
python cli.py policy update --config panorama.xml --type security_pre_rules --name allow-web --properties updated-rule.json --output updated.xml
```

### Delete Policy

Delete a policy:

```bash
python cli.py policy delete --config CONFIG_FILE --type POLICY_TYPE --name NAME --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of policy to delete (**required**)
- `--name`, `-n`: Name of the policy (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)

Example:
```bash
python cli.py policy delete --config panorama.xml --type security_pre_rules --name outdated-rule --output updated.xml
```

### Filter Policies

Filter policies based on criteria:

```bash
python cli.py policy filter --config CONFIG_FILE --type POLICY_TYPE --criteria CRITERIA_FILE [--output OUTPUT_FILE] [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of policy to filter (**required**)
- `--criteria`: JSON file with filter criteria (**required**)
- `--output`, `-o`: Output file for results (JSON format)

Example:
```bash
python cli.py policy filter --config panorama.xml --type security_pre_rules --criteria rule-criteria.json --output filtered-rules.json
```

### Bulk Update Policies

Update multiple policies matching criteria with specified operations:

```bash
python cli.py policy bulk-update --config CONFIG_FILE --type POLICY_TYPE --criteria CRITERIA_FILE --operations OPERATIONS_FILE --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of policy to update (**required**)
- `--criteria`: JSON file with filter criteria (**required**)
- `--operations`: JSON file with update operations (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)

Example:
```bash
python cli.py policy bulk-update --config panorama.xml --type security_pre_rules --criteria criteria.json --operations operations.json --output updated.xml
```

Example criteria file (criteria.json):
```json
{
  "has-tag": "old-policy",
  "action": "allow"
}
```

Example operations file (operations.json):
```json
{
  "add-tag": {
    "name": "updated-policy"
  },
  "add-profile": {
    "type": "log-forwarding",
    "name": "default-logging"
  }
}
```

## Group Commands

Commands for managing address groups, service groups, and other PAN-OS groups.

### Add Member to Group

Add a member to a group:

```bash
python cli.py group add-member --config CONFIG_FILE --type GROUP_TYPE --group GROUP_NAME --member MEMBER_NAME --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of group (e.g., address_group, service_group) (**required**)
- `--group`, `-g`: Name of the group (**required**)
- `--member`, `-m`: Name of the member to add (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)

Example:
```bash
python cli.py group add-member --config firewall.xml --type address_group --group web-servers --member new-web-server --output updated.xml
```

### Remove Member from Group

Remove a member from a group:

```bash
python cli.py group remove-member --config CONFIG_FILE --type GROUP_TYPE --group GROUP_NAME --member MEMBER_NAME --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of group (**required**)
- `--group`, `-g`: Name of the group (**required**)
- `--member`, `-m`: Name of the member to remove (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)

Example:
```bash
python cli.py group remove-member --config firewall.xml --type address_group --group web-servers --member old-web-server --output updated.xml
```

### Add Multiple Members to Group

Add multiple members to a group:

```bash
python cli.py group add-members-file --config CONFIG_FILE --type GROUP_TYPE --group GROUP_NAME --members MEMBERS_FILE --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of group (**required**)
- `--group`, `-g`: Name of the group (**required**)
- `--members`: Path to file containing member names (one per line) (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)

Example:
```bash
python cli.py group add-members-file --config firewall.xml --type address_group --group web-servers --members new-servers.txt --output updated.xml
```

## Report Commands

Commands for generating reports on the configuration.

### Unused Objects Report

Generate a report of unused objects:

```bash
python cli.py report unused-objects --config CONFIG_FILE --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--output`, `-o`: Output file for report (JSON format) (**required**)

Example:
```bash
python cli.py report unused-objects --config firewall.xml --output unused-report.json --context vsys --vsys vsys1
```

### Duplicate Objects Report

Generate a report of duplicate objects:

```bash
python cli.py report duplicate-objects --config CONFIG_FILE --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--output`, `-o`: Output file for report (JSON format) (**required**)

Example:
```bash
python cli.py report duplicate-objects --config firewall.xml --output duplicate-report.json
```

### Security Rule Coverage Report

Generate a report of security rule coverage:

```bash
python cli.py report security-rule-coverage --config CONFIG_FILE --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--output`, `-o`: Output file for report (JSON format) (**required**)

Example:
```bash
python cli.py report security-rule-coverage --config panorama.xml --output coverage-report.json --context device_group --device-group DG1
```

### Reference Check Report

Generate a report of references to an object:

```bash
python cli.py report reference-check --config CONFIG_FILE --name OBJECT_NAME --type OBJECT_TYPE --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--name`, `-n`: Name of the object to check (**required**)
- `--type`, `-t`: Type of object to check (**required**)
- `--output`, `-o`: Output file for report (JSON format) (**required**)

Example:
```bash
python cli.py report reference-check --config firewall.xml --name web-server --type address --output references.json
```

## Configuration Commands

Commands for managing and comparing configurations.

### Validate Configuration

Validate an XML configuration structure:

```bash
python cli.py config validate --config CONFIG_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)

Example:
```bash
python cli.py config validate --config firewall.xml --device-type firewall
```

## Bulk Operations

The CLI provides powerful capabilities for performing operations on multiple objects or policies at once.

### Bulk Update Policies

Apply the same changes to multiple policies matching specific criteria:

```bash
python cli.py policy bulk-update --config CONFIG_FILE --type POLICY_TYPE --criteria CRITERIA_FILE --operations OPERATIONS_FILE --output OUTPUT_FILE [options]
```

This command allows you to apply a set of operations to all policies that match the specified criteria. This is especially useful for tasks like:

- Adding a log forwarding profile to multiple rules
- Adding a security profile group to multiple rules
- Adding tags to multiple policies
- Changing actions across multiple policies

Example criteria file (criteria.json):
```json
{
  "source": ["any"],
  "destination": ["any"],
  "service": ["application-default"]
}
```

Example operations file (operations.json):
```json
{
  "add-tag": {
    "name": "audited-2025"
  },
  "add-profile": {
    "type": "log-forwarding",
    "name": "detailed-logging"
  }
}
```

## Deduplication

The CLI provides tools to identify and merge duplicate objects in your configuration.

### Deduplicate Objects

Find and merge duplicate objects:

```bash
python cli.py deduplicate --config CONFIG_FILE --type OBJECT_TYPE --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of object to deduplicate (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)
- `--dry-run`: Show what would be done without making changes
- `--strategy`: Strategy for choosing primary object (first, shortest)

Example:
```bash
python cli.py deduplicate --config firewall.xml --type address --output deduped.xml --context vsys --vsys vsys1
```

The deduplication process:
1. Identifies objects with identical values (e.g., IP addresses, FQDNs)
2. Chooses a primary object based on the selected strategy
3. Updates all references to the duplicate objects to point to the primary object
4. Removes the duplicate objects from the configuration

Adding `--dry-run` will show what duplicates would be merged without making any changes:

```bash
python cli.py deduplicate --config firewall.xml --type address --dry-run
```

## Logging

The CLI provides flexible logging options to control verbosity and output destination:

- `--verbose`, `-v`: Enable verbose (DEBUG level) output
- `--quiet`, `-q`: Suppress console output
- `--log-level`, `-l`: Set specific log level (debug, info, warning, error, critical)
- `--log-file`, `-f`: Log to a file

Examples:

```bash
# Enable verbose logging
python cli.py object list --config firewall.xml --type address --verbose

# Log to a file
python cli.py object list --config firewall.xml --type address --log-file operations.log

# Set specific log level
python cli.py object list --config firewall.xml --type address --log-level warning

# Suppress console output but log to file
python cli.py object list --config firewall.xml --type address --quiet --log-file operations.log
```

## Usage Examples

Here are some common workflow examples:

### Find and Remove Unused Objects

```bash
# Generate report of unused objects
python cli.py report unused-objects --config firewall.xml --output unused.json

# Review the report, then delete the unused objects
python cli.py object delete --config firewall.xml --type address --name unused-object1 --output updated.xml
```

### Find and Merge Duplicate Objects

```bash
# Identify duplicate address objects
python cli.py deduplicate --config firewall.xml --type address --dry-run

# Merge duplicates after reviewing
python cli.py deduplicate --config firewall.xml --type address --output deduped.xml --strategy first
```

### Bulk Update Security Policies

```bash
# Create criteria and operations files
# criteria.json: {"source": ["any"], "application": ["web-browsing"]}
# operations.json: {"add-profile": {"type": "url-filtering", "name": "strict-filtering"}}

# Apply bulk update
python cli.py policy bulk-update --config panorama.xml --type security_pre_rules --criteria criteria.json --operations operations.json --output updated.xml
```

### Update Multiple Policies with the Same Tag

```bash
# Add a tag to all policies that don't have logging enabled
python cli.py policy bulk-update --config firewall.xml --type security_rules --criteria no-logging-criteria.json --operations add-logging-tag.json --output updated.xml
```

### Reference Checking Before Object Deletion

```bash
# Check what references exist to an object
python cli.py report reference-check --config panorama.xml --name critical-server --type address --output refs.json

# Review references before deciding whether to delete
```

## Tips and Best Practices

1. **Always validate your configuration** after making changes with the `config validate` command.

2. **Use the `--verbose` flag** when troubleshooting to see more details about what's happening.

3. **Create backup configurations** before making significant changes.

4. **Use `--dry-run`** for deduplication operations to preview changes before applying them.

5. **Leverage filter commands** to identify specific objects or policies before making bulk changes.

6. **Use the logging capabilities** to keep track of operations, especially for automated scripts.

7. **Consider the impact of deduplication** on policies and rules. Test thoroughly in non-production environments.

8. **When performing bulk operations**:
   - Start with a targeted criteria file to affect fewer policies
   - Validate the changes carefully before committing
   - Consider creating backups at each step

9. **JSON files for properties** should match the structure expected by PAN-OS. Refer to the documentation or export existing objects for reference.

10. **Context matters**: Remember to specify the correct context (`shared`, `device_group`, `vsys`, or `template`) and its name when working with configurations.