# PANFlow CLI Usage Guide

This guide provides a comprehensive overview of the command-line interface (CLI) for PANFlow, which allows you to work with Palo Alto Networks PAN-OS XML configurations efficiently.

> **Important Note**: PANFlow provides a single consolidated CLI entry point:
> 
> - `cli.py`: The unified CLI interface for all PANFlow functionality
> 
> This guide shows examples using `cli.py` - the consolidated CLI interface for PANFlow.

## Table of Contents

- [Installation](#installation)
- [Global Options](#global-options)
- [Shell Completion](#shell-completion)
- [Object Commands](#object-commands)
- [Policy Commands](#policy-commands)
- [Group Commands](#group-commands)
- [Report Commands](#report-commands)
- [Configuration Commands](#configuration-commands)
- [Merge Commands](#merge-commands)
- [Bulk Operations](#bulk-operations)
- [Deduplication](#deduplication)
- [Logging](#logging)
- [Natural Language Query (NLQ)](#natural-language-query-nlq)
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

## Shell Completion

PANFlow CLI supports shell completion for bash, zsh, and fish shells, making it easier to work with commands and options.

### Setting Up Completion

To set up shell completion:

```bash
# Show completion script for your current shell
python cli.py completion --show

# Install completion for your current shell
python cli.py completion --install

# Install completion for a specific shell
python cli.py completion --install --shell bash
```

After installation, reload your shell or run the appropriate command to enable completion:

**Bash**:
```bash
source ~/.bashrc  # or ~/.bash_profile on macOS
```

**Zsh**:
```bash
source ~/.zshrc
```

**Fish**:
```
# Completion is automatically loaded in fish
```

### Supported Completions

Shell completion provides automatic suggestions for:
- Commands and subcommands
- Configuration files (`.xml`)
- Object types (`address`, `service`, etc.)
- Policy types (`security_rules`, `nat_rules`, etc.)
- Context types (`shared`, `vsys`, etc.)
- Output formats (`json`, `yaml`, etc.)
- Common options and arguments

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
- `--query-filter`, `-q`: Graph query filter to select objects

Examples:
```bash
# List all address objects
python cli.py object list --config firewall.xml --type address --context vsys --vsys vsys1

# List only address objects containing a specific subnet
python cli.py object list --config firewall.xml --type address --query-filter "MATCH (a:address) WHERE a.value CONTAINS '10.0.0'"

# List address objects that are not used in any rule
python cli.py object list --config firewall.xml --type address --query-filter "MATCH (a:address) MATCH (r:security-rule) WHERE NOT EXISTS(r.edges_out[*] ? (@.target == a.id AND (@.relation == 'uses-source' OR @.relation == 'uses-destination')))"
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

Filter objects based on criteria or graph query:

```bash
python cli.py object filter --config CONFIG_FILE --type OBJECT_TYPE [--criteria CRITERIA_FILE] [--query-filter QUERY] [--output OUTPUT_FILE] [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of object to filter (**required**)
- `--criteria`: JSON file with filter criteria 
- `--query-filter`, `-q`: Graph query filter to select objects
- `--output`, `-o`: Output file for results (JSON format)

Note: You must specify either `--criteria` or `--query-filter` (or both).

Examples:
```bash
# Filter objects using criteria file
python cli.py object filter --config firewall.xml --type address --criteria filter-criteria.json --output filtered.json

# Filter objects using graph query
python cli.py object filter --config firewall.xml --type address --query-filter "MATCH (a:address) WHERE NOT (()-[:uses-source|uses-destination]->(a))" --output unused.json

# Combine criteria with graph query (objects must match both)
python cli.py object filter --config firewall.xml --type address --criteria subnets.json --query-filter "MATCH (a:address) WHERE NOT (()-[:uses]->(a))"
```

### Find Objects

Find objects throughout the configuration regardless of context:

```bash
python cli.py object find --config CONFIG_FILE --type OBJECT_TYPE 
  [--name NAME | --pattern PATTERN | --criteria CRITERIA_FILE] 
  [--value VALUE | --ip-contains IP | --port-equals PORT] 
  [--query-filter QUERY] [--output OUTPUT_FILE] [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of object to find (**required**)
- `--name`, `-n`: Name of the object to find (exact match)
- `--pattern`, `-p`: Regex pattern to match object names (for partial matching)
- `--criteria`: JSON file with value criteria
- `--value`, `-v`: Simple value to filter objects by (supports wildcards with *)
- `--ip-contains`: Filter address objects by IP/subnet containing this value
- `--port-equals`: Filter service objects by exact port match
- `--query-filter`, `-q`: Graph query filter to further refine results
- `--output`, `-o`: Output file for results (JSON format)

Note: You must specify one of `--name`, `--pattern`, `--criteria`, `--value`, `--ip-contains`, or `--port-equals`.

This command searches across all contexts (shared, device groups, vsys, templates) to find objects with a specific name, matching a pattern, or matching specific criteria, making it especially useful for Panorama configurations where objects might exist in multiple device groups.

Examples:
```bash
# Find all instances of an object by exact name throughout the configuration
python cli.py object find --config panorama.xml --type address --name web-server --output locations.json

# Find all objects with names matching a pattern (using regex)
python cli.py object find --config panorama.xml --type address --pattern "web-.*" --output web-servers.json

# Find address objects containing a specific IP (simple filtering)
python cli.py object find --config panorama.xml --type address --ip-contains "10.88.0"

# Find service objects with a specific port
python cli.py object find --config panorama.xml --type service --port-equals "8080"

# Find objects containing a value (with wildcard support)
python cli.py object find --config panorama.xml --type address --value "10.*.0.0"

# Combine name pattern and value filtering
python cli.py object find --config panorama.xml --type address --pattern "web-.*" --ip-contains "10.0.0"

# Use advanced graph query filtering for complex cases
python cli.py object find --config panorama.xml --type address --pattern "web-.*" 
    --query-filter "MATCH (a:address) WHERE a.value =~ '.*10\\.0\\.0.*'"

# Traditional method using criteria file
python cli.py object find --config panorama.xml --type address --criteria ip-criteria.json

# Example criteria file (ip-criteria.json) for finding address objects with a specific value:
# {"ip-netmask": "10.0.0.0/24"}

# Example criteria file for finding service objects with specific ports:
# {"port": "8080"}
```

The integration with the graph query system is particularly powerful, allowing you to combine the context-aware object finder with the flexible query language to create sophisticated search patterns. For instance, you could find all address objects whose names match a pattern but only if they're used in security rules with a specific source zone.

### Find Duplicate Objects

Find objects with the same name in different contexts or the same value but different names:

```bash
python cli.py object find-duplicates --config CONFIG_FILE [--by-name | --by-value --type OBJECT_TYPE] 
    [--value VALUE | --ip-contains IP | --port-equals PORT] [--query-filter QUERY] [--output OUTPUT_FILE] [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--by-name`: Find objects with the same name in different contexts
- `--by-value`: Find objects with the same value but different names
- `--type`, `-t`: Type of object for by-value search (required with --by-value)
- `--value`, `-v`: Simple value to filter objects by (supports wildcards with *)
- `--ip-contains`: Filter address objects by IP/subnet containing this value
- `--port-equals`: Filter service objects by exact port match
- `--query-filter`, `-q`: Advanced graph query filter for complex filtering
- `--output`, `-o`: Output file for results (JSON format)

Note: You must specify either `--by-name` or `--by-value`.

This command helps identify redundant or conflicting object definitions across different contexts, which is especially valuable for Panorama configurations with multiple device groups.

Examples:
```bash
# Find objects with the same name in different contexts
python cli.py object find-duplicates --config panorama.xml --by-name --output duplicate-names.json

# Find address objects with the same IP value but different names
python cli.py object find-duplicates --config panorama.xml --by-value --type address --output duplicate-values.json

# Find service objects with the same port but different names
python cli.py object find-duplicates --config panorama.xml --by-value --type service --output duplicate-services.json

# Find duplicate address objects containing a specific IP
python cli.py object find-duplicates --config panorama.xml --by-value --type address --ip-contains "10.88.0"

# Find duplicate service objects with a specific port
python cli.py object find-duplicates --config panorama.xml --by-value --type service --port-equals "8080"

# Use advanced graph query filtering for complex cases
python cli.py object find-duplicates --config panorama.xml --by-value --type address 
    --query-filter "MATCH (a:address) WHERE a.value =~ '.*10\\.0\\.0.*'"
```

## Policy Commands

Commands for managing security rules, NAT rules, and other PAN-OS policies.

### NAT Rule Operations

PanFlow provides specialized commands for working with NAT rules, particularly handling bidirectional NAT rules that are common in migrations from other vendors.

#### Split Bidirectional NAT Rule

Split a bidirectional NAT rule into two unidirectional rules:

```bash
python cli.py policy nat split-bidirectional --config CONFIG_FILE --rule-name RULE_NAME [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--rule-name`, `-r`: Name of the bidirectional NAT rule to split (**required**)
- `--policy-type`, `-t`: Type of NAT policy (nat_rules, nat_pre_rules, nat_post_rules)
- `--reverse-suffix`, `-s`: Suffix to add to the name of the reverse rule
- `--zone-swap/--no-zone-swap`: Whether to swap source and destination zones in the reverse rule
- `--address-swap/--no-address-swap`: Whether to swap source and destination addresses in the reverse rule
- `--disable-bidirectional/--keep-bidirectional`: Whether to disable bidirectional flag on the original rule
- `--any-any-return/--no-any-any-return`: Whether to use 'any' for source zone and address in the return rule
- `--device-type`, `-d`: Device type (firewall or panorama)
- `--context`, `-x`: Context (shared, device_group, vsys)
- `--device-group`, `--dg`: Device group name (for Panorama device_group context)
- `--vsys`, `-v`: VSYS name (for firewall vsys context)
- `--version`: PAN-OS version
- `--dry-run`: Preview changes without modifying the configuration

Examples:
```bash
# Split a bidirectional NAT rule with default settings
python cli.py policy nat split-bidirectional --config config.xml --rule-name "Bidir-NAT-Rule"

# Split a rule but keep the bidirectional flag on the original rule
python cli.py policy nat split-bidirectional --config config.xml --rule-name "Bidir-NAT-Rule" --keep-bidirectional

# Split a rule and use "any" for source in return rule
python cli.py policy nat split-bidirectional --config config.xml --rule-name "Bidir-NAT-Rule" --any-any-return

# Perform a dry run to see what would happen without making changes
python cli.py policy nat split-bidirectional --config config.xml --rule-name "Bidir-NAT-Rule" --dry-run
```

#### Split All Bidirectional NAT Rules

Find and split all bidirectional NAT rules in the configuration:

```bash
python cli.py policy nat split-all-bidirectional --config CONFIG_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--policy-type`, `-t`: Type of NAT policy (nat_rules, nat_pre_rules, nat_post_rules)
- `--reverse-suffix`, `-s`: Suffix to add to the name of the reverse rule
- `--zone-swap/--no-zone-swap`: Whether to swap source and destination zones in the reverse rule
- `--address-swap/--no-address-swap`: Whether to swap source and destination addresses in the reverse rule
- `--disable-bidirectional/--keep-bidirectional`: Whether to disable bidirectional flag on the original rule
- `--any-any-return/--no-any-any-return`: Whether to use 'any' for source zone and address in the return rule
- `--name-filter`, `-f`: Only process rules containing this string in their name
- `--report`, `-r`: Save a detailed report of the operation (JSON format)
- `--device-type`, `-d`: Device type (firewall or panorama)
- `--context`, `-x`: Context (shared, device_group, vsys)
- `--device-group`, `--dg`: Device group name (for Panorama device_group context)
- `--vsys`, `-v`: VSYS name (for firewall vsys context)
- `--version`: PAN-OS version
- `--dry-run`: Preview changes without modifying the configuration

Examples:
```bash
# Split all bidirectional NAT rules with default settings
python cli.py policy nat split-all-bidirectional --config config.xml

# Split only rules containing "BIDIR" in their name
python cli.py policy nat split-all-bidirectional --config config.xml --name-filter "BIDIR"

# Split all rules but keep the bidirectional flag on original rules
python cli.py policy nat split-all-bidirectional --config config.xml --keep-bidirectional

# Split all rules and create return rules with "any" source
python cli.py policy nat split-all-bidirectional --config config.xml --any-any-return

# Generate a detailed report of the operation
python cli.py policy nat split-all-bidirectional --config config.xml --report split_report.json

# Perform a dry run to see what would happen without making changes
python cli.py policy nat split-all-bidirectional --config config.xml --dry-run
```

### List Policies

List policies of a specific type:

```bash
python cli.py policy list --config CONFIG_FILE --type POLICY_TYPE [--query-filter QUERY] [--output OUTPUT_FILE] [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of policy to list (security_rules, security_pre_rules, security_post_rules, nat_rules, nat_pre_rules, nat_post_rules, qos_rules, decryption_rules, authentication_rules, dos_rules, tunnel_inspection_rules, application_override_rules) (**required**)
- `--query-filter`, `-q`: Graph query filter to select policies
- `--output`, `-o`: Output file for results (JSON format)

Examples:
```bash
# List all security pre-rules
python cli.py policy list --config panorama.xml --type security_pre_rules --context device_group --device-group DG1

# List only rules that use a specific service
python cli.py policy list --config firewall.xml --type security_rules --query-filter "MATCH (r:security-rule)-[:uses-service]->(s:service) WHERE s.name == 'http'"

# List rules using any as source and application-default as service
python cli.py policy list --config firewall.xml --type security_rules --query-filter "MATCH (r:security-rule)-[:uses-source]->(s:address), (r)-[:uses-service]->(sv:service) WHERE s.name == 'any' AND sv.name == 'application-default'"
```

### Filter Policies

Filter policies based on criteria or graph query:

```bash
python cli.py policy filter --config CONFIG_FILE --type POLICY_TYPE [--criteria CRITERIA_FILE] [--query-filter QUERY] [--output OUTPUT_FILE] [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of policy to filter (security_rules, security_pre_rules, security_post_rules, nat_rules, nat_pre_rules, nat_post_rules, qos_rules, decryption_rules, authentication_rules, dos_rules, tunnel_inspection_rules, application_override_rules) (**required**)
- `--criteria`: JSON file with filter criteria
- `--query-filter`, `-q`: Graph query filter to select policies
- `--output`, `-o`: Output file for results (JSON format)

Note: You must specify either `--criteria` or `--query-filter` (or both).

Examples:
```bash
# Filter policies using criteria file
python cli.py policy filter --config panorama.xml --type security_pre_rules --criteria rule-criteria.json --output filtered-rules.json

# Filter policies using graph query
python cli.py policy filter --config firewall.xml --type security_rules --query-filter "MATCH (r:security-rule) MATCH (a:address) WHERE a.value =~ '.*192\\.168\\.1.*' AND r.edges_out CONTAINS {target: a.id, relation: 'uses-destination'}" --output internal_rules.json

# Combine criteria with graph query
python cli.py policy filter --config firewall.xml --type security_rules --criteria allow_rules.json --query-filter "MATCH (r:security-rule) MATCH (s:service) WHERE s.name == 'http' AND r.edges_out CONTAINS {target: s.id, relation: 'uses-service'}"
```

### Add Policy

Add a new policy:

```bash
python cli.py policy add --config CONFIG_FILE --type POLICY_TYPE --name NAME --properties PROPERTIES_FILE --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of policy to add (security_rules, security_pre_rules, security_post_rules, nat_rules, nat_pre_rules, nat_post_rules, qos_rules, decryption_rules, authentication_rules, dos_rules, tunnel_inspection_rules, application_override_rules) (**required**)
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
- `--type`, `-t`: Type of policy to update (security_rules, security_pre_rules, security_post_rules, nat_rules, nat_pre_rules, nat_post_rules, qos_rules, decryption_rules, authentication_rules, dos_rules, tunnel_inspection_rules, application_override_rules) (**required**)
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
- `--type`, `-t`: Type of policy to delete (security_rules, security_pre_rules, security_post_rules, nat_rules, nat_pre_rules, nat_post_rules, qos_rules, decryption_rules, authentication_rules, dos_rules, tunnel_inspection_rules, application_override_rules) (**required**)
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
- `--type`, `-t`: Type of policy to filter (security_rules, security_pre_rules, security_post_rules, nat_rules, nat_pre_rules, nat_post_rules, qos_rules, decryption_rules, authentication_rules, dos_rules, tunnel_inspection_rules, application_override_rules) (**required**)
- `--criteria`: JSON file with filter criteria (**required**)
- `--output`, `-o`: Output file for results (JSON format)

Example:
```bash
python cli.py policy filter --config panorama.xml --type security_pre_rules --criteria rule-criteria.json --output filtered-rules.json
```

### Bulk Update Policies

Update multiple policies matching criteria or graph query with specified operations:

```bash
python cli.py policy bulk-update --config CONFIG_FILE --type POLICY_TYPE [--criteria CRITERIA_FILE] [--query-filter QUERY] --operations OPERATIONS_FILE --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of policy to update (security_rules, security_pre_rules, security_post_rules, nat_rules, nat_pre_rules, nat_post_rules, qos_rules, decryption_rules, authentication_rules, dos_rules, tunnel_inspection_rules, application_override_rules) (**required**)
- `--criteria`: JSON file with filter criteria
- `--query-filter`, `-q`: Graph query filter to select policies
- `--operations`: JSON file with update operations (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)

Note: You must specify either `--criteria` or `--query-filter` (or both).

Examples:
```bash
# Update policies matching criteria file
python cli.py policy bulk-update --config panorama.xml --type security_pre_rules --criteria criteria.json --operations operations.json --output updated.xml

# Update policies matching graph query
python cli.py policy bulk-update --config firewall.xml --type security_rules --query-filter "MATCH (r:security-rule) MATCH (s:service) WHERE s.dst_port == '3389' AND r.edges_out CONTAINS {target: s.id, relation: 'uses-service'}" --operations rdp_protection.json --output updated.xml

# Update policies matching both criteria and query
python cli.py policy bulk-update --config firewall.xml --type security_rules --criteria allow_rules.json --query-filter "MATCH (r:security-rule) MATCH (a:address) WHERE a.name == 'any' AND r.edges_out CONTAINS {target: a.id, relation: 'uses-source'}" --operations add_logging.json --output updated.xml
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

## Merge Commands

Commands for merging policies and objects between configurations.

### Merge Single Policy

Merge a single policy from a source configuration to a target configuration:

```bash
python cli.py merge policy --source-config SOURCE_CONFIG --target-config TARGET_CONFIG --type POLICY_TYPE --name POLICY_NAME --output OUTPUT_FILE [options]
```

Options:
- `--source-config`: Path to source XML configuration file (**required**)
- `--target-config`: Path to target XML configuration file (**required**)
- `--type`, `-t`: Type of policy to merge (security_rules, security_pre_rules, security_post_rules, nat_rules, nat_pre_rules, nat_post_rules, qos_rules, decryption_rules, authentication_rules, dos_rules, tunnel_inspection_rules, application_override_rules) (**required**)
- `--name`, `-n`: Name of the policy to merge (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)
- `--source-context`: Source context (shared, device_group, vsys)
- `--target-context`: Target context (shared, device_group, vsys)
- `--source-dg`: Source device group name
- `--target-dg`: Target device group name
- `--position`: Position to add policy (top, bottom, before, after)
- `--ref-policy`: Reference policy for before/after position
- `--skip-if-exists/--replace`: Skip if policy already exists
- `--copy-references/--no-copy-references`: Copy object references
- `--conflict-strategy`: Strategy for resolving conflicts (skip, overwrite, merge, rename)
- `--dry-run`: Preview changes without modifying the target configuration

Example:
```bash
python cli.py merge policy --source-config source.xml --target-config target.xml --type security_pre_rules --name "Allow Web Traffic" --output updated.xml --position bottom
```

### Merge Multiple Policies

Merge multiple policies matching criteria or from a list:

```bash
python cli.py merge policies --source-config SOURCE_CONFIG --target-config TARGET_CONFIG --type POLICY_TYPE (--names-file NAMES_FILE | --criteria CRITERIA_FILE) --output OUTPUT_FILE [options]
```

Options:
- `--source-config`: Path to source XML configuration file (**required**)
- `--target-config`: Path to target XML configuration file (**required**)
- `--type`, `-t`: Type of policy to merge (security_rules, security_pre_rules, security_post_rules, nat_rules, nat_pre_rules, nat_post_rules, qos_rules, decryption_rules, authentication_rules, dos_rules, tunnel_inspection_rules, application_override_rules) (**required**)
- `--names-file`: File containing policy names to merge (one per line)
- `--criteria`: JSON file with filter criteria
- `--output`, `-o`: Output file for updated configuration (**required**)
- `--source-context`, `--target-context`, `--source-dg`, `--target-dg`: (same as for single policy)
- `--skip-if-exists/--replace`, `--copy-references/--no-copy-references`, `--conflict-strategy`, `--dry-run`: (same as for single policy)

Example:
```bash
python cli.py merge policies --source-config source.xml --target-config target.xml --type security_pre_rules --names-file policy_list.txt --output updated.xml
```

### Merge All Policy Types

Merge all policy types from source to target configuration:

```bash
python cli.py merge all --source-config SOURCE_CONFIG --target-config TARGET_CONFIG --output OUTPUT_FILE [options]
```

Options:
- `--source-config`: Path to source XML configuration file (**required**)
- `--target-config`: Path to target XML configuration file (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)
- `--source-context`, `--target-context`, `--source-dg`, `--target-dg`: (same as for single policy)
- `--skip-if-exists/--replace`, `--copy-references/--no-copy-references`, `--conflict-strategy`, `--dry-run`: (same as for single policy)

Example:
```bash
python cli.py merge all --source-config source.xml --target-config target.xml --output updated.xml --copy-references
```

### Merge Single Object

Merge a single object from source to target configuration:

```bash
python cli.py merge object --source-config SOURCE_CONFIG --target-config TARGET_CONFIG --type OBJECT_TYPE --name OBJECT_NAME --output OUTPUT_FILE [options]
```

Options:
- `--source-config`: Path to source XML configuration file (**required**)
- `--target-config`: Path to target XML configuration file (**required**)
- `--type`, `-t`: Type of object to merge (address, service, etc.) (**required**)
- `--name`, `-n`: Name of the object to merge (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)
- `--source-context`, `--target-context`, `--source-dg`, `--target-dg`: (same as for single policy)
- `--skip-if-exists/--replace`, `--copy-references/--no-copy-references`, `--conflict-strategy`, `--dry-run`: (same as for single policy)

Example:
```bash
python cli.py merge object --source-config source.xml --target-config target.xml --type address --name web-server --output updated.xml
```

### Merge Multiple Objects

Merge multiple objects matching criteria or from a list:

```bash
python cli.py merge objects --source-config SOURCE_CONFIG --target-config TARGET_CONFIG --type OBJECT_TYPE (--names-file NAMES_FILE | --criteria CRITERIA_FILE) --output OUTPUT_FILE [options]
```

Options:
- `--source-config`: Path to source XML configuration file (**required**)
- `--target-config`: Path to target XML configuration file (**required**)
- `--type`, `-t`: Type of object to merge (**required**)
- `--names-file`: File containing object names to merge (one per line)
- `--criteria`: JSON file with filter criteria
- `--output`, `-o`: Output file for updated configuration (**required**)
- `--source-context`, `--target-context`, `--source-dg`, `--target-dg`: (same as for single policy)
- `--skip-if-exists/--replace`, `--copy-references/--no-copy-references`, `--conflict-strategy`, `--dry-run`: (same as for single policy)

Example:
```bash
python cli.py merge objects --source-config source.xml --target-config target.xml --type address --names-file address_list.txt --output updated.xml
```

### Merge All Object Types

Merge all object types from source to target configuration:

```bash
python cli.py merge all-objects --source-config SOURCE_CONFIG --target-config TARGET_CONFIG --output OUTPUT_FILE [options]
```

Options:
- `--source-config`: Path to source XML configuration file (**required**)
- `--target-config`: Path to target XML configuration file (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)
- `--source-context`, `--target-context`, `--source-dg`, `--target-dg`: (same as for single policy)
- `--skip-if-exists/--replace`, `--copy-references/--no-copy-references`, `--conflict-strategy`, `--dry-run`: (same as for single policy)

Example:
```bash
python cli.py merge all-objects --source-config source.xml --target-config target.xml --output updated.xml --copy-references
```

## Query Commands

Commands for querying the configuration using a graph-based query language.

### Execute Query

Execute a graph query on a PAN-OS configuration:

```bash
python cli.py query execute --config CONFIG_FILE --query QUERY [--format FORMAT] [--output OUTPUT_FILE]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--query`, `-q`: Graph query to execute (**required**)
- `--format`, `-f`: Output format (table, json, csv). Default is table.
- `--output`, `-o`: Output file path for saving results

Example:
```bash
# Find all address objects with device group context
python cli.py query execute -c config.xml -q "MATCH (a:address) RETURN a.name, a.value, a.device_group"

# Find rules using a specific address (using edges_out)
python cli.py query execute -c config.xml -q "MATCH (r:security-rule) MATCH (a:address) WHERE a.name == 'web-server' AND r.edges_out CONTAINS {target: a.id, relation: 'uses-source'} RETURN r.name"

# Find services by port number
python cli.py query execute -c config.xml -q "MATCH (s:service) WHERE s.port == '8080' RETURN s.name, s.device_group"

# Export results to CSV
python cli.py query execute -c config.xml -q "MATCH (g:address-group) MATCH (a:address) WHERE g.edges_out CONTAINS {target: a.id, relation: 'contains'} RETURN g.name, a.name" --format csv --output groups.csv
```

### Verify Query Syntax

Verify a graph query's syntax without executing it:

```bash
python cli.py query verify --query QUERY
```

Options:
- `--query`, `-q`: Graph query to verify (**required**)

Example:
```bash
python cli.py query verify -q "MATCH (a:address) WHERE a.value =~ '.*10\\.0\\.0.*' RETURN a.name"
```

### Show Query Examples

Display example graph queries:

```bash
python cli.py query example
```

This command shows several example queries with descriptions of what they do, providing a quick reference for common query patterns.

### Interactive Query Mode

Launch an interactive query session:

```bash
python cli.py query interactive --config CONFIG_FILE
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)

The interactive mode provides a REPL-like environment where you can:
- Type and execute queries directly
- View query results in a formatted table
- Refine queries iteratively
- Access query history
- Get help on query syntax

Example session:
```
> MATCH (a:address) RETURN a.name, a.device_group LIMIT 5
| a.name       | a.device_group |
|--------------|----------------|
| web-server-1 | test-dg-1      |
| web-server-2 | test-dg-1      |
| db-server    | shared         |
| app-server   | shared         |
| localhost    | shared         |

> MATCH (a:address) WHERE a.name =~ ".*web.*" RETURN a.name, a.value, a.device_group
| a.name       | a.value       | a.device_group |
|--------------|---------------|----------------|
| web-server-1 | 10.0.1.10     | test-dg-1      |
| web-server-2 | 10.0.1.11     | test-dg-1      |
```

See the [Graph Query Language Reference](docs/graph_query_reference.md) for detailed information on query syntax, capabilities, and current limitations.

> **Important Note**: The current implementation of the graph query language has some syntax limitations. Direct relationship patterns like `(a)-[:contains]->(b)` are not supported. Use multiple MATCH clauses with WHERE conditions on `edges_out` and `edges_in` instead. String operations like CONTAINS and STARTS WITH are not supported - use regex with the `=~` operator. For equality comparison, always use the double equals (`==`) operator. See the [Graph Query Reference](docs/graph_query_reference.md) for more details on these limitations and workarounds.

## Bulk Operations

The CLI provides powerful capabilities for performing operations on multiple objects or policies at once.

### Bulk Delete Objects

Delete multiple objects based on a list or graph query:

```bash
python cli.py object bulk-delete --config CONFIG_FILE --type OBJECT_TYPE [--names-file NAMES_FILE] [--query-filter QUERY] --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of object to delete (**required**)
- `--names-file`: Text file with object names to delete (one per line)
- `--query-filter`, `-q`: Graph query filter to select objects to delete
- `--output`, `-o`: Output file for updated configuration (**required**)
- `--dry-run`: Show what would be deleted without making changes
- `--force`: Delete objects without confirmation

Note: You must specify either `--names-file` or `--query-filter`.

Examples:
```bash
# Delete objects listed in a file
python cli.py object bulk-delete --config config.xml --type address --names-file objects_to_delete.txt --output updated.xml

# Delete unused address objects using query filter (proper syntax)
python cli.py object bulk-delete --config config.xml --type address --query-filter "MATCH (a:address) WHERE NOT EXISTS(()-[:uses-source|uses-destination|contains]->(a)) RETURN a.name" --output updated.xml

# Preview objects that would be deleted without making changes
python cli.py object bulk-delete --config config.xml --type address --query-filter "MATCH (a:address) WHERE a.value =~ '.*192\\.168\\.1.*' RETURN a.name" --dry-run
```

### Bulk Update Policies

Apply the same changes to multiple policies matching specific criteria or graph query:

```bash
python cli.py policy bulk-update --config CONFIG_FILE --type POLICY_TYPE [--criteria CRITERIA_FILE] [--query-filter QUERY] --operations OPERATIONS_FILE --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--type`, `-t`: Type of policy to update (**required**)
- `--operations`: Path to JSON file with operations to apply (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)
- `--criteria`: Path to JSON file with criteria for selecting policies
- `--query-filter`, `-q`: Graph query filter to select policies
- `--device-type`: Device type (firewall or panorama)
- `--context`: Context (shared, device_group, vsys)
- `--device-group`: Device group name (for Panorama device_group context)
- `--vsys`: VSYS name (for firewall vsys context)
- `--dry-run`: Show what would be updated without making changes

This command allows you to apply a set of operations to all policies that match the specified criteria or query filter. This is especially useful for tasks like:

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

#### Device Group Context with Query Filters

When using Panorama configurations, you can combine device group context with graph query filters to precisely target policies:

```bash
# Update all security rules in a specific device group
python cli.py policy bulk-update --config panorama.xml --device-type panorama --context device_group --device-group DG1 --type security_pre_rules --operations operations.json --query-filter "MATCH (r:security-rule) RETURN r.name" --output updated.xml

# Update only disabled security rules in a device group
python cli.py policy bulk-update --config panorama.xml --device-type panorama --context device_group --device-group DG1 --type security_pre_rules --operations operations.json --query-filter "MATCH (r:security-rule) WHERE r.disabled == 'yes' RETURN r.name" --output updated.xml

# Update rules that use a specific service in a device group
python cli.py policy bulk-update --config panorama.xml --device-type panorama --context device_group --device-group DG1 --type security_pre_rules --operations operations.json --query-filter "MATCH (r:security-rule)-[:uses-service]->(s:service) WHERE s.dst_port == '3389' RETURN r.name" --output updated.xml
```

The system will automatically filter the query results to match only policies in the specified device group, even for complex queries.

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
- `--strategy`: Strategy for choosing primary object (first, shortest, longest, alphabetical)
- `--context`: Context (shared, device_group, vsys)
- `--device-group`: Device group name (for Panorama device_group context)
- `--vsys`: VSYS name (for firewall vsys context)
- `--device-type`: Device type (firewall or panorama)
- `--pattern`, `-p`: Pattern to filter objects (e.g. '10.0.0' for addresses)
- `--include-file`: JSON file with list of object names to include in deduplication
- `--exclude-file`: JSON file with list of object names to exclude from deduplication
- `--query-filter`, `-q`: Graph query filter to select objects (e.g., 'MATCH (a:address) WHERE NOT (()-[:uses-source|uses-destination]->(a))')

#### Deduplication Process:

1. Identifies objects with identical values (e.g., IP addresses, FQDNs)
2. Chooses a primary object based on the selected strategy
3. Updates all references to the duplicate objects to point to the primary object
4. Removes the duplicate objects from the configuration

#### Primary Object Selection Strategies:

- `first` (default): Uses the first object found as primary
- `shortest`: Uses the object with the shortest name as primary

#### Examples:

Basic deduplication:
```bash
python cli.py deduplicate --config firewall.xml --type address --output deduped.xml --context vsys --vsys vsys1
```

Dry run to preview changes without modifying the configuration:
```bash
python cli.py deduplicate --config firewall.xml --type address --dry-run
```

Using the shortest name strategy:
```bash
python cli.py deduplicate --config firewall.xml --type address --output deduped.xml --strategy shortest
```

Deduplicate address groups:
```bash
python cli.py deduplicate --config firewall.xml --type address_group --output deduped.xml
```

Deduplicate in a Panorama device group:
```bash
python cli.py deduplicate --config panorama.xml --type service --output deduped.xml --device-type panorama --context device_group --device-group DG1
```

Using graph query to select objects for deduplication:
```bash
python cli.py deduplicate --config firewall.xml --type address --output deduped.xml --query-filter "MATCH (a:address) MATCH (r:security-rule) WHERE NOT EXISTS(r.edges_out[*] ? (@.target == a.id AND (@.relation == 'uses-source' OR @.relation == 'uses-destination'))) AND a.value =~ '.*10\\.0\\.0.*'"
```

Combining query filter with include file to refine selection:
```bash
python cli.py deduplicate --config firewall.xml --type address --output deduped.xml --query-filter "MATCH (a:address) WHERE a.value CONTAINS '192.168'" --include-file critical_objects.json
```

#### Supported Object Types for Deduplication:

- `address`: IP addresses and FQDNs
- `address_group`: Address groups
- `service`: Service objects
- `service_group`: Service groups
- `application_group`: Application groups
- `tag`: Tags

#### Best Practices for Deduplication:

1. **Always use `--dry-run` first** to preview changes before applying them
2. **Back up your configuration** before performing deduplication
3. **Start with smaller contexts** (like a specific device group) before deduplicating the entire configuration
4. **Review reference changes carefully**, especially for objects used in security policies
5. **Verify operation after deduplication** by checking that references are correctly maintained

#### Example Workflow:

```bash
# Step 1: Find duplicate address objects in dry-run mode
python cli.py deduplicate --config firewall.xml --type address --dry-run --context vsys --vsys vsys1

# Step 2: Check references to objects that would be merged
python cli.py report reference-check --config firewall.xml --type address --name duplicate-object-1 --output refs.json

# Step 3: Perform the deduplication
python cli.py deduplicate --config firewall.xml --type address --output deduped.xml --context vsys --vsys vsys1

# Step 4: Verify the updated configuration
python cli.py config validate --config deduped.xml
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

## Natural Language Query (NLQ)

The Natural Language Query (NLQ) module allows you to interact with PANFlow using plain English commands instead of remembering CLI syntax.

### Basic Usage

```bash
# Process a natural language query (view-only operation)
python cli.py nlq query "show me all unused address objects" --config firewall.xml

# Cleanup operation requires an output file
python cli.py nlq query "cleanup unused service objects" --config firewall.xml --output cleaned.xml

# Use dry run mode via CLI flag
python cli.py nlq query "cleanup unused address objects" --config firewall.xml --output cleaned.xml --dry-run

# Use dry run mode via natural language
python cli.py nlq query "cleanup unused address objects but don't make any changes" --config firewall.xml

# Save report output in HTML format
python cli.py nlq query "show me unused address objects" --config firewall.xml --format html --report-file report.html

# Save both configuration changes and report output
python cli.py nlq query "cleanup unused objects" --config firewall.xml --output cleaned.xml --format html --report-file report.html
```

### Interactive Mode

```bash
# Start an interactive session
python cli.py nlq interactive --config firewall.xml

# Start an interactive session with HTML report output
python cli.py nlq interactive --config firewall.xml --format html --report-file reports/session.html

# Example interaction
PANFlow> show me all unused address objects
PANFlow> cleanup disabled security policies
PANFlow> find duplicate address objects
PANFlow> exit
```

### Command Options

```bash
python cli.py nlq query [OPTIONS] QUERY

Options:
  QUERY                           Natural language query text  [required]
  -c, --config TEXT               Configuration file path  [required]
  -o, --output TEXT               Output file for modified configuration (for cleanup operations)
  -r, --report-file TEXT          Output file for report/results (use with --format)
  --dry-run                       Preview changes without making modifications
  -i, --interactive               Interactive mode
  -f, --format TEXT               Output format (text, json, table, csv, yaml, html)  [default: text]
  -v, --verbose                   Show verbose output
  --ai/--no-ai                    Use AI for processing if available  [default: ai]
  --ai-provider TEXT              AI provider to use (openai, anthropic)
  --ai-model TEXT                 AI model to use
  --help                          Show this message and exit.
```

### NLQ Help and Examples

```bash
# Get help and examples for NLQ
python cli.py nlq help
```

### Example NLQ Queries

#### Object Management

```bash
# List objects
python cli.py nlq query "list all address objects" --config firewall.xml
python cli.py nlq query "show me service objects" --config firewall.xml
python cli.py nlq query "find address objects with 10.0.0 in them" --config firewall.xml

# List groups
python cli.py nlq query "list address-groups" --config firewall.xml
python cli.py nlq query "show service-groups" --config firewall.xml
```

#### Policy Management

```bash
# List policies
python cli.py nlq query "list security policies" --config firewall.xml
python cli.py nlq query "show nat rules" --config firewall.xml
python cli.py nlq query "list pre security rules" --config firewall.xml
python cli.py nlq query "show security post rules" --config firewall.xml
```

#### Cleanup Operations

```bash
# Cleanup unused objects
python cli.py nlq query "cleanup unused address objects" --config firewall.xml --output cleaned.xml

# Cleanup disabled policies
python cli.py nlq query "remove all disabled security rules" --config firewall.xml --output cleaned.xml

# Dry run mode
python cli.py nlq query "cleanup unused service objects in dry run mode" --config firewall.xml --output cleaned.xml
python cli.py nlq query "cleanup disabled nat rules" --config firewall.xml --output cleaned.xml --dry-run
```

#### Finding Unused & Disabled Items

```bash
# Find unused objects
python cli.py nlq query "show me all unused address objects" --config firewall.xml
python cli.py nlq query "find unused service groups" --config firewall.xml

# Find disabled policies
python cli.py nlq query "list disabled security policies" --config firewall.xml
python cli.py nlq query "find disabled NAT policies" --config firewall.xml
```

#### Deduplication

```bash
# Find duplicates
python cli.py nlq query "find duplicate address objects" --config firewall.xml
python cli.py nlq query "show me address objects with the same IP" --config firewall.xml
```

#### Contextual Operations

```bash
# Context-specific operations
python cli.py nlq query "cleanup unused objects in device group DG1" --config panorama.xml --output cleaned.xml
python cli.py nlq query "show disabled policies in vsys1" --config firewall.xml
```

For a comprehensive guide to the NLQ module, see [Natural Language Query Documentation](docs/nlq.md).

## Usage Examples

Here are some common workflow examples:

### Find and Remove Unused Objects

```bash
# Manual approach (two-step):
# Generate report of unused objects
python cli.py report unused-objects --config firewall.xml --output unused.json

# Review the report, then delete the unused objects
python cli.py object delete --config firewall.xml --type address --name unused-object1 --output updated.xml

# Automated approach (using cleanup command):
# Preview which objects would be removed (dry run)
python cli.py cleanup unused-objects --config firewall.xml --output cleaned.xml --dry-run

# Clean up all unused address objects in one step
python cli.py cleanup unused-objects --config firewall.xml --output cleaned.xml

# Generate a report alongside cleanup
python cli.py cleanup unused-objects --config firewall.xml --output cleaned.xml --report-file cleanup-report.json

# Clean up unused objects of multiple types
python cli.py cleanup unused-objects --config firewall.xml --output cleaned.xml --type address --type service
```

### Find and Remove Disabled Policies

```bash
# Preview which disabled policies would be removed (dry run)
python cli.py cleanup disabled-policies --config firewall.xml --output cleaned.xml --dry-run

# Clean up all disabled security policies in one step
python cli.py cleanup disabled-policies --config firewall.xml --output cleaned.xml

# Clean up disabled policies and generate a report
python cli.py cleanup disabled-policies --config firewall.xml --output cleaned.xml --report-file disabled-report.json

# Exclude specific policies from cleanup
python cli.py cleanup disabled-policies --config firewall.xml --output cleaned.xml --exclude-file protected.json
```

For more detailed examples, see the [Cleanup Examples](examples/cleanup_examples.md) document.

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

## Integration Workflows with Graph Queries

The graph query system can be combined with other commands to create powerful workflows. Here are examples of using queries to drive other operations:

### Query-Driven Object Deletion

Identify and delete unused objects:

```bash
# Step 1: Find unused address objects
python cli.py query execute -c config.xml -q "MATCH (a:address) WHERE NOT (()-[:uses-source|uses-destination|contains]->(a)) RETURN a.name" --format json --output unused.json

# Step 2: Parse the JSON output to get names of unused objects
cat unused.json | jq -r '.[].a\.name' > unused_addresses.txt

# Step 3: Create a script to delete each unused object
while read name; do
  python cli.py object delete --config config.xml --type address --name "$name" --output config_updated.xml
  mv config_updated.xml config.xml
done < unused_addresses.txt
```

### Query-Driven Deduplication

Find duplicate IP addresses with different names and deduplicate them:

```bash
# Old approach (multi-step):
# Step 1: Identify address objects with identical IP values
python cli.py query execute -c config.xml -q "MATCH (a1:address) MATCH (a2:address) WHERE a1.value == a2.value AND a1.name != a2.name RETURN a1.name, a1.value, COLLECT(a2.name) as duplicates" --format json --output duplicates.json

# Step 2: Review the results before deduplication
cat duplicates.json

# Step 3: Deduplicate the address objects
python cli.py deduplicate --config config.xml --type address --output deduped.xml

# New approach (direct integration):
# Directly deduplicate only objects with a specific subnet using query filter
python cli.py deduplicate --config config.xml --type address --output deduped.xml --query-filter "MATCH (a:address) WHERE a.value =~ '.*10\\.1\\.0.*'" --dry-run

# Then perform the actual deduplication after reviewing
python cli.py deduplicate --config config.xml --type address --output deduped.xml --query-filter "MATCH (a:address) WHERE a.value =~ '.*10\\.1\\.0.*'"
```

### Query-Driven Bulk Operations

Update security rules that use a specific service:

```bash
# Step 1: Find security rules using a specific service
python cli.py query execute -c config.xml -q "MATCH (r:security-rule)-[:uses-service]->(s:service) WHERE s.name == 'http' RETURN r.name" --format json --output http_rules.json

# Step 2: Extract rule names from JSON
cat http_rules.json | jq -r '.[].r\.name' > http_rules.txt

# Step 3: Create criteria JSON file based on rule names
echo '{"name": ["'$(tr '\n' ',' < http_rules.txt | sed 's/,$//')']}' > criteria.json

# Step 4: Create operations to add application filtering
echo '{"add-profile": {"type": "url-filtering", "name": "web-filter"}}' > operations.json

# Step 5: Apply bulk update
python cli.py policy bulk-update --config config.xml --type security_rules --criteria criteria.json --operations operations.json --output updated.xml
```

### Query-Driven Merge Operations

Merge specific objects from source to target based on query results:

```bash
# Step 1: Find all objects referenced by a specific rule
python cli.py query execute -c source.xml -q "MATCH (r:security-rule)-[:uses-source|uses-destination|uses-service]->(o) WHERE r.name == 'Important-Rule' RETURN DISTINCT o.type, o.name" --format json --output objects_to_merge.json

# Step 2: Create a script to merge each referenced object
cat objects_to_merge.json | jq -c '.[]' | while read -r object; do
  obj_type=$(echo $object | jq -r '.o\.type')
  obj_name=$(echo $object | jq -r '.o\.name')
  python cli.py merge object --source-config source.xml --target-config target.xml --type "$obj_type" --name "$obj_name" --output target_updated.xml --copy-references
  mv target_updated.xml target.xml
done

# Step 3: Merge the rule itself
python cli.py merge policy --source-config source.xml --target-config target.xml --type security_pre_rules --name "Important-Rule" --output target_updated.xml
```

### Query-Driven Report Generation

Generate a custom report on security exposure:

```bash
# Step 1: Find rules that allow any traffic to DMZ servers
python cli.py query execute -c config.xml -q "MATCH (r:security-rule)-[:uses-source]->(s:address), (r)-[:uses-destination]->(d:address) WHERE r.action == 'allow' AND s.name == 'any' AND d.name CONTAINS 'DMZ' RETURN r.name, d.name, d.value" --format csv --output dmz_exposure.csv

# Step 2: Generate a formatted report
echo "# DMZ Exposure Report" > exposure_report.md
echo "## Rules allowing unrestricted access to DMZ servers" >> exposure_report.md
echo "" >> exposure_report.md
cat dmz_exposure.csv | sed 's/,/ | /g' | sed '1s/.*/| Rule | Server | IP |/' | sed '1a| --- | --- | --- |' >> exposure_report.md
```

### Interactive Query Exploration for Complex Tasks

Use interactive mode to explore before performing operations:

```bash
# Step 1: Launch interactive mode to explore the configuration
python cli.py query interactive --config config.xml

# In the interactive session:
# > MATCH (r:security-rule)-[:uses-source]->(s:address-group) RETURN r.name, s.name LIMIT 5
# > MATCH (ag:address-group)-[:contains]->(a:address) WHERE ag.name == 'Internal-Servers' RETURN a.name, a.value
# > MATCH (r:security-rule)-[:uses-service]->(s:service) WHERE s.dst_port == '3389' RETURN r.name, s.name

# Step 2: After identifying the relevant objects, exit and perform operations
# For example, create a bulk update for all rules using RDP:
python cli.py query execute -c config.xml -q "MATCH (r:security-rule)-[:uses-service]->(s:service) WHERE s.dst_port == '3389' RETURN r.name" --format json --output rdp_rules.json

# Create criteria and operations
cat rdp_rules.json | jq -r '.[].r\.name' | jq -Rs 'split("\n") | {name: .}' > criteria.json
echo '{"add-tag": {"name": "rdp-access"}, "add-profile": {"type": "vulnerability", "name": "strict-protection"}}' > operations.json

# Apply the bulk update
python cli.py policy bulk-update --config config.xml --type security_rules --criteria criteria.json --operations operations.json --output updated.xml
```

These integration workflows demonstrate how the graph query language can be a powerful tool for identifying specific objects or policies to be processed by other commands, creating an efficient and precise way to manage your PAN-OS configurations.

## Cleanup Commands

Commands for cleaning up unused objects and policies in PAN-OS configurations. For detailed information on how PANFlow determines which objects and policies to clean up, see the [Cleanup Detection Documentation](docs/cleanup_detection.md).

### Cleanup Unused Objects

Find and remove unused objects from the configuration:

```bash
python cli.py cleanup unused-objects --config CONFIG_FILE --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)
- `--type`, `-t`: Types of objects to clean up (can specify multiple types like `address`, `service`, `tag` - default is "address")
- `--context`: Context (shared, device_group, vsys)
- `--device-group`: Device group name (for Panorama device_group context)
- `--vsys`: VSYS name (for firewall vsys context)
- `--template`: Template name (for Panorama template context)
- `--exclude-file`: JSON file with list of object names to exclude from cleanup
- `--dry-run`: Preview changes without modifying the configuration
- `--report-file`, `-r`: JSON file to save the report of cleaned-up objects
- `--device-type`: Device type (firewall or panorama)
- `--version`: PAN-OS version

Examples:

```bash
# Find and report on unused address objects without making changes (dry run)
python cli.py cleanup unused-objects --config firewall.xml --dry-run

# Clean up unused address objects and save the updated configuration
python cli.py cleanup unused-objects --config firewall.xml --output cleaned.xml

# Clean up unused service objects specifically
python cli.py cleanup unused-objects --config firewall.xml --output cleaned.xml --type service

# Clean up multiple object types (address and service) with a report
python cli.py cleanup unused-objects --config firewall.xml --output cleaned.xml --type address --type service --report-file cleanup-report.json

# Clean up all supported object types (address, service, address-group, service-group, tag)
python cli.py cleanup unused-objects --config firewall.xml --output cleaned.xml --type address --type service --type address-group --type service-group --type tag

# Exclude specific objects from cleanup
python cli.py cleanup unused-objects --config firewall.xml --output cleaned.xml --exclude-file protected-objects.json
```

How It Works:
- PANFlow determines if an object is unused by checking for references across all policy types (security, NAT, decryption, QoS, etc.) and all appropriate groups.
- For shared objects in Panorama configurations, it checks for usage across all device groups.
- The detection process considers all relevant policy fields including complex structures like:
  - Address objects: Checked in source/destination fields and translation fields
  - Service objects: Checked in service fields, service-translation fields, and protocol-specific fields in NAT rules
  - All object types: Checked in the appropriate groups (address groups for address objects, service groups for service objects)
- See [Cleanup Detection Documentation](docs/cleanup_detection.md) for full technical details.

### Cleanup Disabled Policies

Find and remove disabled policies from the configuration:

```bash
python cli.py cleanup disabled-policies --config CONFIG_FILE --output OUTPUT_FILE [options]
```

Options:
- `--config`, `-c`: Path to XML configuration file (**required**)
- `--output`, `-o`: Output file for updated configuration (**required**)
- `--type`, `-t`: Types of policies to clean up (can specify multiple, default is "security_rules")
- `--context`: Context (shared, device_group, vsys)
- `--device-group`: Device group name (for Panorama device_group context)
- `--vsys`: VSYS name (for firewall vsys context)
- `--template`: Template name (for Panorama template context)
- `--exclude-file`: JSON file with list of policy names to exclude from cleanup
- `--dry-run`: Preview changes without modifying the configuration
- `--report-file`, `-r`: JSON file to save the report of cleaned-up policies
- `--device-type`: Device type (firewall or panorama)
- `--version`: PAN-OS version

Examples:

```bash
# Find and report on disabled security rules without making changes (dry run)
python cli.py cleanup disabled-policies --config firewall.xml --dry-run

# Clean up disabled policies and save the updated configuration
python cli.py cleanup disabled-policies --config firewall.xml --output cleaned.xml

# Clean up multiple policy types with a report
python cli.py cleanup disabled-policies --config firewall.xml --output cleaned.xml --type security_pre_rules --type security_post_rules --report-file cleanup-report.json

# Exclude specific policies from cleanup
python cli.py cleanup disabled-policies --config firewall.xml --output cleaned.xml --exclude-file protected-policies.json
```

How It Works:
- A policy is considered disabled if it contains the `<disabled>yes</disabled>` element in its XML structure.
- For Panorama configurations, PANFlow checks both pre-rulebase and post-rulebase policies in the specified device group.
- Direct XPath queries identify disabled policies regardless of their position in the configuration hierarchy.
- See [Cleanup Detection Documentation](docs/cleanup_detection.md) for more details.

For more cleanup command examples and advanced usage patterns, see [Cleanup Examples](examples/cleanup_examples.md).

## Tips and Best Practices

1. **Always validate your configuration** after making changes with the `config validate` command.

2. **Use the `--verbose` flag** when troubleshooting to see more details about what's happening.

3. **Create backup configurations** before making significant changes.

4. **Use `--dry-run`** for deduplication and cleanup operations to preview changes before applying them.

5. **Leverage filter commands** to identify specific objects or policies before making bulk changes.

6. **Use the logging capabilities** to keep track of operations, especially for automated scripts.

7. **Consider the impact of deduplication** on policies and rules. Test thoroughly in non-production environments.

8. **When performing bulk operations**:
   - Start with a targeted criteria file to affect fewer policies
   - Validate the changes carefully before committing
   - Consider creating backups at each step

9. **JSON files for properties** should match the structure expected by PAN-OS. Refer to the documentation or export existing objects for reference.

10. **Context matters**: Remember to specify the correct context (`shared`, `device_group`, `vsys`, or `template`) and its name when working with configurations.

11. **Consolidated CLI**: Use `cli.py` for all operations as the unified interface for PANFlow.

12. **Leverage graph query filters**: Use the `--query-filter` option with commands like `policy bulk-update`, `object bulk-delete`, `deduplicate merge`, and `merge` commands to precisely select the objects or policies to operate on. This is more powerful than using simple pattern matching or name lists.