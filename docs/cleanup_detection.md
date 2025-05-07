# Understanding Cleanup Detection in PANFlow

This document explains how PANFlow determines which objects and policies to clean up when using the `cleanup` commands. It provides technical details about the detection algorithms and helps you understand what will be affected by cleanup operations.

## Table of Contents

- [Unused Object Detection](#unused-object-detection)
  - [Detection Algorithm](#detection-algorithm)
  - [Comprehensive Policy Coverage](#comprehensive-policy-coverage)
  - [Cross-Context Checks](#cross-context-checks)
  - [Complex Field Handling](#complex-field-handling)
- [Disabled Policy Detection](#disabled-policy-detection)
  - [Policy Identification](#policy-identification)
  - [Panorama-Specific Handling](#panorama-specific-handling)
- [Exclusion Lists](#exclusion-lists)
- [Dry-Run Mode](#dry-run-mode)
- [Best Practices](#best-practices)

## Unused Object Detection

### Detection Algorithm

PANFlow determines if an object is unused through the following process:

1. **Object Inventory**: First, it collects all objects of the specified type (address, service, etc.) in the current context (shared, device group, vsys).

2. **Reference Scanning**: It then searches for references to each object in:
   - Security policies (source, destination, or service fields, depending on object type)
   - NAT policies (source, destination, and translation fields)
   - Decryption policies (source, destination, or service fields, depending on object type)
   - Authentication policies (source, destination fields)
   - Policy-based Forwarding rules (source, destination fields)
   - Application Override policies (source, destination fields)
   - DOS Protection policies (source, destination fields)
   - Other relevant policy types
   - Appropriate group objects (address groups for address objects, service groups for service objects, etc.)

3. **Used Object Tracking**: It builds a comprehensive set of object names that appear in any policy or group.

4. **Comparison**: Finally, it compares the complete list of objects against the set of used objects to identify which ones are unused.

An object is considered unused only if it doesn't appear in any policy or group across all checked contexts.

### Comprehensive Policy Coverage

PANFlow checks for usage across a wide range of policy types:

**For Panorama:**
- Security pre-rules and post-rules
- NAT pre-rules and post-rules
- Decryption pre-rules and post-rules
- Authentication pre-rules and post-rules
- Policy-based Forwarding pre-rules and post-rules
- Application Override pre-rules and post-rules
- DOS Protection pre-rules and post-rules

**For Firewalls:**
- Security rules
- NAT rules
- Decryption rules
- Authentication rules
- Policy-based Forwarding rules
- Application Override rules
- DOS Protection rules

### Cross-Context Checks

For shared objects in Panorama, PANFlow checks for usage across multiple contexts:

1. **Shared Context**: First checks if the object is used in any shared policies

2. **Device Group Contexts**: Then checks if the object is used in any device group's policies

This multi-context check ensures that shared objects that are referenced in any device group are not mistakenly identified as unused.

### Complex Field Handling

The detection accounts for complex policy structures like:

- **Nested Fields**: Some policy types (like NAT) have nested fields such as `source-translation`, `destination-translation`, or `service-translation` that might reference objects
  
- **Different Reference Structures**: Some policies use direct member lists, while others use nested structures
  
- **Protocol-Specific Service References**: For service objects, PANFlow checks protocol-specific fields (tcp, udp) in NAT rules' service translation that might reference service objects

- **Multiple Object Types**: Detection is tailored to each object type, with specific handling for:
  - Address objects: Checked in source/destination fields across all policy types
  - Service objects: Checked in service fields and service-translation across relevant policies
  - Application objects: Checked in application fields
  - Tags: Checked in tag fields

## Disabled Policy Detection

### Policy Identification

A policy is considered disabled if it meets the following criteria:

1. It contains the `<disabled>yes</disabled>` element in its XML structure

2. For Panorama configurations, PANFlow checks both pre-rulebase and post-rulebase policies

The command directly inspects the XML structure to identify rules with the disabled flag set to "yes".

### Panorama-Specific Handling

For Panorama configurations, PANFlow handles different policy locations:

1. **Pre-rulebase**: Checks policies in the device group's pre-rulebase
   
2. **Post-rulebase**: Checks policies in the device group's post-rulebase

Direct XPath queries are used to identify disabled policies in each location, ensuring accurate detection regardless of policy position in the configuration hierarchy.

## Exclusion Lists

Both cleanup commands support exclusion lists via the `--exclude-file` parameter:

1. The exclusion file should be in JSON format, either:
   - A simple array of object/policy names: `["object1", "object2", "object3"]`
   - Or an object with "objects" or "policies" key: `{"objects": ["object1", "object2"]}`

2. Excluded items will never be removed, even if they would otherwise qualify for cleanup

3. This is useful for protecting critical objects or policies that must remain in the configuration

Example exclusion file for objects:
```json
[
  "critical-server",
  "dns-server",
  "gateway-address"
]
```

Example exclusion file for policies:
```json
{
  "policies": [
    "monitoring-rule",
    "breakglass-access",
    "emergency-rule"
  ]
}
```

## Dry-Run Mode

All cleanup commands support a `--dry-run` mode that:

1. Performs all the detection steps described above
   
2. Reports what would be cleaned up, including counts and specific objects/policies
   
3. Does NOT make any changes to the configuration

Using dry-run is strongly recommended before performing any cleanup operation to:
- Understand what will be affected
- Verify that critical objects or policies won't be removed
- Prepare exclusion lists if needed

## Best Practices

1. **Always use dry-run first**: Run the command with `--dry-run` to preview changes before making them

2. **Create exclusion lists**: Identify any objects or policies that should never be removed and add them to exclusion files

3. **Generate reports**: Use the `--report-file` option to save detailed reports of what was cleaned up

4. **Start small**: Begin with specific object types or contexts before cleaning up entire configurations

5. **Validate after cleanup**: Thoroughly test the cleaned configuration to ensure everything functions correctly

6. **Maintain backup configurations**: Always keep a backup of the original configuration before cleanup

7. **Review context-specific impacts**: Remember that shared objects in Panorama might be used across multiple device groups

For more information on using the cleanup commands, see the [CLI Usage Guide](../CLI_USAGE.md#cleanup-commands).