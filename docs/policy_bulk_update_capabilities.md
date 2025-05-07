# PanFlow Policy Bulk Update Capabilities

## Overview

The PanFlow CLI provides comprehensive bulk update capabilities for policies through the `policy bulk-update` command. This document outlines the available operations and provides examples of how to use them.

## Supported Operations

Based on the implementation in the `ConfigUpdater` class, the CLI supports the following policy bulk update operations:

1. **Security Profiles and Profile Groups**
   - Add security profile groups to policies
   - Add individual security profiles (virus, spyware, vulnerability, etc.)

2. **Logging Configuration**
   - Add/remove logging at session start
   - Add/remove logging at session end
   - Enable logging at both start and end
   - Disable all logging
   - Set log forwarding profiles

3. **Tag Management**
   - Add tags to policies

4. **Policy Status**
   - Enable/disable policies

5. **Object References**
   - Add/remove source address objects
   - Add/remove destination address objects
   - Add/remove service objects
   - Add/remove application objects
   - Add/remove zones (source and destination)

6. **Policy Action**
   - Change the action of policies (allow, deny, etc.)

7. **Description Management**
   - Update policy descriptions
   - Append to existing descriptions
   - Prepend to existing descriptions

## Operation Format

Operations are specified in a JSON file with the following structure:

```json
{
  "operation-name": {
    "parameter1": "value1",
    "parameter2": "value2"
  }
}
```

## Operation Details

### 1. Adding Security Profiles or Profile Groups

```json
{
  "add-profile": {
    "type": "group",
    "name": "my-profile-group"
  }
}
```

Supported profile types:
- `group` - For profile groups
- `log-forwarding` - For log forwarding profiles
- Individual profiles: `virus`, `spyware`, `vulnerability`, `url-filtering`, `wildfire-analysis`, `data-filtering`, `file-blocking`, `dns-security`

### 2. Managing Logging

```json
{
  "update-logging": {
    "setting": "log-both"
  }
}
```

Supported log settings:
- `log-start` - Log at session start
- `log-end` - Log at session end
- `log-both` - Log at both session start and end
- `log-none` - Disable all logging

### 3. Managing Tags

```json
{
  "add-tag": {
    "name": "tag-name"
  }
}
```

### 4. Enable/Disable Policies

```json
{
  "enable-disable": {
    "action": "disable"
  }
}
```

Supported actions:
- `enable` - Enable the policy
- `disable` - Disable the policy

### 5. Adding/Removing Objects

```json
{
  "add-object": {
    "name": "object-name",
    "field": "source"
  }
}
```

```json
{
  "remove-object": {
    "name": "object-name",
    "field": "destination"
  }
}
```

Supported fields:
- `source` - Source address objects
- `destination` - Destination address objects
- `service` - Service objects
- `application` - Application objects

### 6. Adding Zones

```json
{
  "add-zone": {
    "name": "zone-name",
    "location": "source"
  }
}
```

Supported locations:
- `from` or `source` - Source zone
- `to` or `destination` - Destination zone
- `both` - Both source and destination zones

### 7. Changing Policy Action

```json
{
  "change-action": {
    "action": "deny"
  }
}
```

### 8. Updating Description

```json
{
  "update-description": {
    "text": "New description",
    "mode": "replace"
  }
}
```

Supported modes:
- `replace` - Replace the existing description
- `append` - Append to the existing description
- `prepend` - Prepend to the existing description

## Example Usage

### Command Line

```bash
python cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.action == 'allow'" \
  --operations operations.json \
  --output updated_config.xml
```

### Operations File (operations.json)

```json
{
  "add-tag": {
    "name": "reviewed"
  },
  "update-logging": {
    "setting": "log-both"
  },
  "add-profile": {
    "type": "group",
    "name": "strict-security"
  },
  "update-description": {
    "text": "[Reviewed] ",
    "mode": "prepend"
  }
}
```

## Multiple Operations

Multiple operations can be combined in a single operations file:

```json
{
  "add-tag": {
    "name": "compliance"
  },
  "update-logging": {
    "setting": "log-both"
  },
  "add-profile": {
    "type": "group",
    "name": "compliance-profile"
  },
  "update-description": {
    "text": "Updated for compliance requirements",
    "mode": "replace"
  }
}
```

## Bulk Renaming

While there isn't a direct "rename" operation, you can achieve renaming by:

1. Creating a new policy with the desired name and the same configuration
2. Deleting the old policy

For simple modifications to names (like adding prefixes/suffixes), you can use a combination of:
- Export the policies to JSON
- Modify the policy names
- Import the policies back with the new names

## Rule Merging

Rule merging functionality is implemented in the `bulk_merge_objects` method and can be accessed through the policy merge command. The CLI supports different conflict resolution strategies when merging rules, including:

- Skip if exists
- Overwrite existing rules
- Keep both (rename duplicates)

## Conclusion

The PanFlow CLI provides a powerful set of bulk update capabilities for policies, allowing administrators to efficiently manage their security policies at scale. These operations cover all the requested functionality and can be combined to create complex policy updates with a single command.