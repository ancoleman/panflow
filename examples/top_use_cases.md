# PANFlow Top Use Cases and CLI Commands

This document covers the most common use cases for PANFlow and provides detailed CLI command examples for each. These use cases focus on configuration management tasks that can be applied to whole configurations or specific device groups/vsys contexts.

## Table of Contents

1. [Merging Duplicate Objects](#1-merging-duplicate-objects)
2. [Applying Log Settings to Rules](#2-applying-log-settings-to-rules)
3. [Adding Objects to Policies](#3-adding-objects-to-policies)
4. [Removing Objects from Policies](#4-removing-objects-from-policies)
5. [Replacing Objects in Policies](#5-replacing-objects-in-policies) 
6. [Bulk Object Renaming](#6-bulk-object-renaming)
7. [Generating Reports](#7-generating-reports)
8. [Managing Security Profiles](#8-managing-security-profiles)
9. [Splitting Bi-Directional NAT Rules](#9-splitting-bi-directional-nat-rules)
10. [Locating Large Address Groups](#10-locating-large-address-groups)
11. [Enabling/Disabling Policies](#11-enablingdisabling-policies)
12. [Deleting Policies](#12-deleting-policies)

---

## 1. Merging Duplicate Objects

PANFlow provides powerful deduplication capabilities to identify and merge duplicate objects based on their values rather than names.

### Merge Duplicate Addresses

```bash
# Basic deduplication of address objects
python cli.py deduplicate merge --config CONFIG.xml --type address --output deduplicated.xml

# Using a specific name selection strategy (first, shortest, longest, alphabetical)
python cli.py deduplicate merge --config CONFIG.xml --type address --output deduplicated.xml --primary-name-strategy shortest

# Dry run to preview changes without applying them
python cli.py deduplicate merge --config CONFIG.xml --type address --output deduplicated.xml --dry-run

# Hierarchical deduplication (migrates objects to highest device group)
python cli.py deduplicate hierarchical merge --config CONFIG.xml --type address --output deduplicated.xml --device-type panorama
```

### Merge Duplicate Services

```bash
# Merge duplicate service objects
python cli.py deduplicate merge --config CONFIG.xml --type service --output deduplicated.xml

# Merge duplicate service groups
python cli.py deduplicate merge --config CONFIG.xml --type service-group --output deduplicated.xml
```

### Merge Duplicate Address Groups

```bash
# Merge duplicate address groups
python cli.py deduplicate merge --config CONFIG.xml --type address-group --output deduplicated.xml
```

## 2. Applying Log Settings to Rules

You can apply log settings to security policies matching specific criteria or query filters.

### Add Log Forwarding Profile

```bash
# Create operations JSON file
cat > log_operations.json << EOF
{
  "add-profile": {
    "type": "log-forwarding",
    "name": "detailed-logging-profile"
  }
}
EOF

# Apply to all "allow" rules
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.action == 'allow'" \
  --operations log_operations.json --output updated.xml
```

### Enable Log at Session End

```bash
# Create operations JSON file
cat > log_end_operations.json << EOF
{
  "update-logging": {
    "setting": "log-end"
  }
}
EOF

# Apply to all rules in the DMZ zone
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule)-[:uses_source_zone]->(z) WHERE z.name == 'dmz'" \
  --operations log_end_operations.json --output updated.xml
```

### Enable Both Session Start and End Logging

```bash
# Create operations JSON file
cat > log_both_operations.json << EOF
{
  "update-logging": {
    "setting": "log-both"
  }
}
EOF

# Apply to rules using a specific service
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule)-[:uses_service]->(s) WHERE s.name == 'https'" \
  --operations log_both_operations.json --output updated.xml
```

### Using the Script Approach

For simpler workflows, you can use the included script:

```bash
# Add log setting to specific policies
python add_log_setting.py CONFIG.xml UPDATED.xml log-profile-name policy1 policy2 policy3

# Remove log setting from specific policies
python remove_log_setting.py CONFIG.xml UPDATED.xml policy1 policy2 policy3
```

## 3. Adding Objects to Policies

Add address objects, services, or other elements to policies that match specific criteria.

### Add Source Address to Policies

```bash
# Create operations JSON file
cat > add_source_operations.json << EOF
{
  "add-object": {
    "name": "new-server-10.1.1.10",
    "field": "source"
  }
}
EOF

# Apply to policies with a specific tag
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule)-[:has_tag]->(t) WHERE t.name == 'web-servers'" \
  --operations add_source_operations.json --output updated.xml
```

### Add Service to Policies

```bash
# Create operations JSON file
cat > add_service_operations.json << EOF
{
  "add-object": {
    "name": "https-8443",
    "field": "service"
  }
}
EOF

# Apply to policies with specific description
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.description CONTAINS 'web access'" \
  --operations add_service_operations.json --output updated.xml
```

### Add Zone to Policies

```bash
# Create operations JSON file
cat > add_zone_operations.json << EOF
{
  "add-zone": {
    "name": "new-zone",
    "location": "to"
  }
}
EOF

# Apply to policies matching a name pattern
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.name STARTS WITH 'external-'" \
  --operations add_zone_operations.json --output updated.xml
```

## 4. Removing Objects from Policies

Remove address objects, services, or other elements from policies based on specific criteria.

### Remove Source Address from Policies

```bash
# Create operations JSON file
cat > remove_source_operations.json << EOF
{
  "remove-object": {
    "name": "old-server-192.168.1.10",
    "field": "source"
  }
}
EOF

# Apply to all security rules
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --operations remove_source_operations.json --output updated.xml
```

### Remove Service from Policies

```bash
# Create operations JSON file
cat > remove_service_operations.json << EOF
{
  "remove-object": {
    "name": "telnet",
    "field": "service"
  }
}
EOF

# Apply to policies using a specific destination
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule)-[:uses_destination]->(d) WHERE d.name == 'internal-servers'" \
  --operations remove_service_operations.json --output updated.xml
```

## 5. Replacing Objects in Policies

To replace objects in policies, you would typically use a combination of remove and add operations.

### Replace Source Address

```bash
# Create operations JSON file with remove and add operations
cat > replace_source_operations.json << EOF
{
  "remove-object": {
    "name": "old-server-192.168.1.10",
    "field": "source"
  },
  "add-object": {
    "name": "new-server-10.1.1.10",
    "field": "source"
  }
}
EOF

# Apply to policies with specific criteria
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --criteria source_criteria.json --operations replace_source_operations.json --output updated.xml
```

### Replace Service

```bash
# Create operations JSON file with remove and add operations
cat > replace_service_operations.json << EOF
{
  "remove-object": {
    "name": "http",
    "field": "service"
  },
  "add-object": {
    "name": "https",
    "field": "service"
  }
}
EOF

# Apply to policies matching a query
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.name CONTAINS 'web'" \
  --operations replace_service_operations.json --output updated.xml
```

## 6. Bulk Object Renaming

PANFlow supports bulk renaming of policies and objects with different renaming strategies.

### Direct Replacement

```bash
# Create operations JSON file 
cat > rename_operations.json << EOF
{
  "rename": {
    "mode": "replace",
    "name": "NEW-POLICY-NAME"
  }
}
EOF

# Apply to a specific policy
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.name == 'OLD-POLICY-NAME'" \
  --operations rename_operations.json --output updated.xml
```

### Add Prefix to Names

```bash
# Create operations JSON file
cat > prefix_operations.json << EOF
{
  "rename": {
    "mode": "prefix",
    "prefix": "DMZ-"
  }
}
EOF

# Apply to all rules with a specific zone
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule)-[:uses_source_zone]->(z) WHERE z.name == 'dmz'" \
  --operations prefix_operations.json --output updated.xml
```

### Add Suffix to Names

```bash
# Create operations JSON file
cat > suffix_operations.json << EOF
{
  "rename": {
    "mode": "suffix",
    "suffix": "-DEPRECATED"
  }
}
EOF

# Apply to rules with a specific tag
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule)-[:has_tag]->(t) WHERE t.name == 'old'" \
  --operations suffix_operations.json --output updated.xml
```

### Pattern-Based Renaming

```bash
# Create operations JSON file
cat > regex_operations.json << EOF
{
  "rename": {
    "mode": "regex",
    "pattern": "SRV-(\\d+)",
    "replacement": "SERVER-\\1"
  }
}
EOF

# Apply to all objects matching the pattern
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.name =~ 'SRV-\\d+'" \
  --operations regex_operations.json --output updated.xml
```

## 7. Generating Reports

PANFlow can generate detailed reports in various formats to analyze and document your configuration.

### Duplicate Objects Report

```bash
# Generate a report of duplicate objects
python cli.py deduplicate report --config CONFIG.xml --output report.json

# Generate report in different formats
python cli.py deduplicate report --config CONFIG.xml --output report.csv --format csv
python cli.py deduplicate report --config CONFIG.xml --output report.html --format html
```

### Unused Objects Report

```bash
# Generate a report of unused objects
python cli.py report unused-objects --config CONFIG.xml --output unused.json

# Generate report in different formats
python cli.py report unused-objects --config CONFIG.xml --output unused.csv --format csv
python cli.py report unused-objects --config CONFIG.xml --output unused.html --format html
```

### Policy Analysis Report

```bash
# Generate a policy analysis report
python cli.py report policy-analysis --config CONFIG.xml --output policy_analysis.json

# Generate report in different formats
python cli.py report policy-analysis --config CONFIG.xml --output policy_analysis.csv --format csv
python cli.py report policy-analysis --config CONFIG.xml --output policy_analysis.html --format html
```

## 8. Managing Security Profiles

Add, modify, or remove security profiles on policies matching specific criteria.

### Add Security Profile Group

```bash
# Create operations JSON file
cat > add_profile_operations.json << EOF
{
  "add-profile": {
    "type": "group",
    "name": "strict-security-profile"
  }
}
EOF

# Apply to all allow rules
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.action == 'allow'" \
  --operations add_profile_operations.json --output updated.xml
```

### Add Individual Security Profiles

```bash
# Create operations JSON file with multiple profile types
cat > security_profiles_operations.json << EOF
{
  "add-profile": {
    "type": "antivirus",
    "name": "default-av"
  },
  "add-profile": {
    "type": "vulnerability",
    "name": "strict-vuln"
  },
  "add-profile": {
    "type": "url-filtering",
    "name": "default-url"
  }
}
EOF

# Apply to rules with a specific destination zone
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule)-[:uses_destination_zone]->(z) WHERE z.name == 'internet'" \
  --operations security_profiles_operations.json --output updated.xml
```

## 9. Splitting Bi-Directional NAT Rules

PANFlow provides specific functionality to split bi-directional NAT rules into separate SNAT and DNAT rules.

### Split a Specific Bi-Directional NAT Rule

```bash
# Split a specific bidirectional NAT rule
python cli.py policy nat split-bidirectional --config CONFIG.xml --rule-name "VPN-Access-Rule" --output updated.xml
```

### Split All Bi-Directional NAT Rules

```bash
# Split all bidirectional NAT rules in the configuration
python cli.py policy nat split-all-bidirectional --config CONFIG.xml --output updated.xml

# Split with custom naming pattern
python cli.py policy nat split-all-bidirectional --config CONFIG.xml --output updated.xml \
  --naming-pattern "{original-name}-{direction}" --dnat-suffix "inbound" --snat-suffix "outbound"
```

## 10. Locating Large Address Groups

Find and report on large address groups that might impact performance.

### Find Address Groups by Size

```bash
# Find address groups with more than 50 members
python cli.py object filter --config CONFIG.xml --type address_group \
  --query-filter "MATCH (a:address_group) WHERE size(a.members) > 50" --output large_groups.json

# Output in a different format
python cli.py object filter --config CONFIG.xml --type address_group \
  --query-filter "MATCH (a:address_group) WHERE size(a.members) > 50" --output large_groups.csv --format csv
```

### Find the Largest Address Groups

```bash
# Find and sort address groups by size (requires post-processing)
python cli.py object list --config CONFIG.xml --type address_group --output all_groups.json

# You would then need to sort these groups by size using external tools or scripts
```

## 11. Enabling/Disabling Policies

Enable or disable policies based on various criteria.

### Disable Policies

```bash
# Create operations JSON file
cat > disable_operations.json << EOF
{
  "enable-disable": {
    "action": "disable"
  }
}
EOF

# Disable policies containing a specific address
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule)-[:uses_destination]->(d) WHERE d.name == 'legacy-server'" \
  --operations disable_operations.json --output updated.xml
```

### Enable Policies

```bash
# Create operations JSON file
cat > enable_operations.json << EOF
{
  "enable-disable": {
    "action": "enable"
  }
}
EOF

# Enable policies with a specific tag
python cli.py policy bulk-update --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule)-[:has_tag]->(t) WHERE t.name == 'ready-to-deploy'" \
  --operations enable_operations.json --output updated.xml
```

## 12. Deleting Policies

Delete policies based on specific criteria.

### Delete Security Rules

```bash
# Delete security rules that match criteria
python cli.py policy bulk-delete --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.name CONTAINS 'TEMP-'" \
  --output updated.xml

# Perform a dry run first to see what would be deleted
python cli.py policy bulk-delete --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.name CONTAINS 'TEMP-'" \
  --output updated.xml --dry-run
```

### Delete Rules with Specific Tags

```bash
# Delete all rules with a specific tag
python cli.py policy bulk-delete --config CONFIG.xml --type security_rules \
  --query-filter "MATCH (r:security_rule)-[:has_tag]->(t) WHERE t.name == 'to-be-deleted'" \
  --output updated.xml
```

---

## Best Practices

1. **Always use the `--dry-run` flag** to preview changes before applying them to your configuration
2. **Create backups** of your configuration before making bulk changes
3. **Start with small batches** when applying changes to large configurations
4. **Apply to specific device groups or vsys** when working with Panorama configurations
5. **Validate changes** after applying them to ensure the expected results
6. **Use version control** to track configuration changes over time
7. **Test in non-production environments** before applying changes to production
8. **Use specific contexts** with the `--context`, `--device-group`, or `--vsys` parameters to target changes