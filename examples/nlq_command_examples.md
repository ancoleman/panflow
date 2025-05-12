# Natural Language Query (NLQ) Command Examples

This document provides a comprehensive set of examples for using the Natural Language Query (NLQ) feature in PANFlow. 

## Basic Command Structure

```
python cli.py nlq query "your natural language query" [options]
```

Common options:
- `--config`, `-c`: Path to XML configuration file (required)
- `--output`, `-o`: Output file for updates (required for modification operations)
- `--dry-run`: Preview changes without modifying the configuration
- `--ai/--no-ai`: Enable or disable AI processing
- `--format`, `-f`: Output format (text, json)
- `--verbose`, `-v`: Show detailed information

## Object Management Examples

### Listing Objects

```bash
# List all address objects
python cli.py nlq query "list all address objects" --config config.xml

# Show service objects
python cli.py nlq query "show me service objects" --config config.xml

# List application objects
python cli.py nlq query "list application objects" --config config.xml

# Find address objects containing a specific IP
python cli.py nlq query "find address objects with 10.0.0 in them" --config config.xml

# List all tag objects
python cli.py nlq query "show all tag objects" --config config.xml
```

### Listing Groups

```bash
# List address groups
python cli.py nlq query "list address-groups" --config config.xml

# Show service groups
python cli.py nlq query "show all service-groups" --config config.xml

# List application groups
python cli.py nlq query "list application groups" --config config.xml

# Find groups in a specific context
python cli.py nlq query "list address groups in device group DG1" --config config.xml
```

## Policy Management Examples

### Listing Policies

```bash
# List all security policies
python cli.py nlq query "list all security policies" --config config.xml

# Show NAT rules
python cli.py nlq query "show nat rules" --config config.xml

# List security pre-rules (Panorama)
python cli.py nlq query "list pre security rules" --config config.xml

# Show security post-rules (Panorama)
python cli.py nlq query "show security post rules" --config config.xml

# List rules with specific attributes
python cli.py nlq query "show security rules that use the any source" --config config.xml
python cli.py nlq query "find policies that use HTTP service" --config config.xml
```

### Finding Disabled Policies

```bash
# List all disabled security policies
python cli.py nlq query "list disabled security policies" --config config.xml

# Show disabled NAT rules
python cli.py nlq query "show disabled nat rules" --config config.xml

# Find disabled rules in a specific context
python cli.py nlq query "find disabled security rules in device group DG1" --config config.xml
```

## Finding Unused Objects

```bash
# Show all unused address objects
python cli.py nlq query "show me all unused address objects" --config config.xml

# Find unused service objects
python cli.py nlq query "find unused service objects" --config config.xml

# List unused address groups
python cli.py nlq query "list unused address groups" --config config.xml

# Find unused service groups
python cli.py nlq query "find unused service groups" --config config.xml

# Show all unused objects
python cli.py nlq query "show me all unused objects" --config config.xml

# Find unused objects in a specific context
python cli.py nlq query "find unused objects in device group DG1" --config config.xml
```

## Deduplication Examples

### Finding Duplicate Objects

```bash
# Find duplicate address objects
python cli.py nlq query "find duplicate address objects" --config config.xml

# Show duplicate service objects
python cli.py nlq query "show me duplicate service objects" --config config.xml

# Find address objects with the same IP
python cli.py nlq query "show me address objects with the same IP" --config config.xml

# List all duplicate objects
python cli.py nlq query "find all duplicate objects" --config config.xml

# Find duplicates in a specific context
python cli.py nlq query "find duplicate objects in device group DG1" --config config.xml
```

### Cleaning Up Duplicate Objects

```bash
# Clean up duplicate address objects
python cli.py nlq query "cleanup duplicate address objects" --config config.xml --output deduped.xml

# Deduplicate service objects
python cli.py nlq query "deduplicate service objects" --config config.xml --output deduped.xml

# Remove all duplicate objects
python cli.py nlq query "clean up all duplicate objects" --config config.xml --output deduped.xml

# Consolidate duplicate objects in a specific context
python cli.py nlq query "deduplicate objects in device group DG1" --config config.xml --output deduped.xml

# Clean up with dry run mode
python cli.py nlq query "clean up duplicate objects but don't make changes" --config config.xml
```

## Cleanup Operations

### Cleaning Up Unused Objects

```bash
# Cleanup unused address objects
python cli.py nlq query "cleanup unused address objects" --config config.xml --output cleaned.xml

# Remove unused service objects
python cli.py nlq query "remove unused service objects" --config config.xml --output cleaned.xml

# Clean up unused address groups
python cli.py nlq query "cleanup unused address groups" --config config.xml --output cleaned.xml

# Remove all unused objects
python cli.py nlq query "cleanup all unused objects" --config config.xml --output cleaned.xml

# Cleanup unused objects in a specific context
python cli.py nlq query "cleanup unused objects in device group DG1" --config config.xml --output cleaned.xml
```

### Cleaning Up Disabled Policies

```bash
# Cleanup disabled security policies
python cli.py nlq query "cleanup disabled security rules" --config config.xml --output cleaned.xml

# Remove disabled NAT rules
python cli.py nlq query "remove disabled nat rules" --config config.xml --output cleaned.xml

# Clean up all disabled policies
python cli.py nlq query "cleanup all disabled policies" --config config.xml --output cleaned.xml

# Remove disabled rules in a specific context
python cli.py nlq query "cleanup disabled rules in device group DG1" --config config.xml --output cleaned.xml
```

## Dry Run Examples

### Using the --dry-run Flag

```bash
# Preview cleaning up unused address objects
python cli.py nlq query "cleanup unused address objects" --config config.xml --output cleaned.xml --dry-run

# Preview removing disabled security policies
python cli.py nlq query "cleanup disabled security rules" --config config.xml --output cleaned.xml --dry-run
```

### Using Natural Language for Dry Run

```bash
# Dry run via natural language
python cli.py nlq query "cleanup unused objects but don't make changes" --config config.xml --output cleaned.xml

# Preview without modifying
python cli.py nlq query "remove disabled policies in dry run mode" --config config.xml --output cleaned.xml

# Simulate cleanup
python cli.py nlq query "show me what would be removed if I cleaned up unused objects" --config config.xml --output cleaned.xml

# Just preview changes
python cli.py nlq query "preview cleanup of disabled nat rules" --config config.xml --output cleaned.xml
```

## Interactive Mode Examples

```bash
# Start an interactive session
python cli.py nlq interactive --config config.xml

# Start an interactive session with dry run mode enabled
python cli.py nlq interactive --config config.xml --dry-run

# Start an interactive session with a specified output file
python cli.py nlq interactive --config config.xml --output cleaned.xml

# Start with a specific AI provider
python cli.py nlq interactive --config config.xml --ai-provider anthropic
```

## Advanced Examples

### Object Management with Complex Criteria

```bash
# Find address objects with specific patterns
python cli.py nlq query "find address objects that start with 'WEB-'" --config config.xml

# List objects with specific criteria
python cli.py nlq query "show address objects in the 192.168 subnet" --config config.xml

# Find objects used in specific policy types
python cli.py nlq query "find address objects used in nat rules" --config config.xml
```

### Policy Management with Complex Criteria

```bash
# Find rules with specific attributes
python cli.py nlq query "find security rules that allow traffic to the internet" --config config.xml

# List rules by action
python cli.py nlq query "show security rules with deny action" --config config.xml

# Find rules using specific services
python cli.py nlq query "find rules that use RDP service" --config config.xml
```

### Contextual Queries

```bash
# Operations in specific device groups
python cli.py nlq query "show unused objects in device group Marketing" --config config.xml

# Operations in specific vsys
python cli.py nlq query "find disabled rules in vsys3" --config config.xml

# Shared context operations
python cli.py nlq query "cleanup unused objects in shared context" --config config.xml --output cleaned.xml
```

### Combined Operations

```bash
# Find and clean up duplicates in one operation
python cli.py nlq query "find and cleanup duplicate address objects" --config config.xml --output cleaned.xml

# Find and remove unused objects
python cli.py nlq query "find unused service objects and remove them" --config config.xml --output cleaned.xml

# Clean up both duplicates and unused objects
python cli.py nlq query "deduplicate address objects and remove unused ones" --config config.xml --output cleaned.xml

# List and clean up disabled rules
python cli.py nlq query "find and remove all disabled security rules" --config config.xml --output cleaned.xml

# Comprehensive cleanup
python cli.py nlq query "clean up all duplicate and unused objects" --config config.xml --output cleaned.xml
```

## Tips for Effective NLQ Usage

1. **Be specific** about the object or policy type you're interested in (address, service, security rules, nat rules, etc.)

2. **Include contextual information** if needed (device group, vsys, etc.)

3. **Use action verbs** that clearly indicate what you want to do:
   - "list", "show", "find" for viewing operations
   - "cleanup", "remove", "delete" for modification operations

4. **Always use `--dry-run`** or include "dry run" in your query when first testing cleanup operations

5. **For complex operations**, start with a view-only query to confirm what would be affected, then proceed with the cleanup

6. **Use the interactive mode** for iterative exploration of your configuration