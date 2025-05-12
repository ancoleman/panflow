# PanFlow Policy CLI Usage Examples

## 1. Security Profile Operations

### Add a Profile Group to Rules with Source Zone "trust"

```bash
# Create operations.json
cat > operations.json << EOF
{
  "add-profile": {
    "type": "group",
    "name": "strict-security-profile"
  }
}
EOF

# Run the command
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --query-filter "MATCH (r:security_rule)-[:uses_source_zone]->(z) WHERE z.name == 'trust'" \
  --operations operations.json \
  --output updated_config.xml
```

### Remove a Profile Group from All Allow Rules

```bash
# First export the rules that need modification
python3 cli.py policy list \
  --config config.xml \
  --type security_pre_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.action == 'allow'" \
  --output allow_rules.json

# Modify the exported rules to remove the profile group (manual step)
# Then re-import the modified rules (would require import functionality)
```

## 2. Log Forwarding Profile Operations

### Add a Log Forwarding Profile to All Deny Rules

```bash
# Create operations.json with log forwarding profile
cat > operations.json << EOF
{
  "log-setting": "detailed-logging-profile"
}
EOF

# Run the command
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --query-filter "MATCH (r:security-rule) WHERE r.action == 'deny'" \
  --operations operations.json \
  --output updated_config.xml \
  --device-type panorama \
  --context device_group \
  --device-group your-device-group
```

### Add a Log Forwarding Profile to Multiple Specific Policies

```bash
# Create a policy criteria file for specific policies
cat > policy_criteria.json << EOF
{
  "name": ["policy-name-1", "policy-name-2", "policy-name-3"]
}
EOF

# Create operations.json
cat > operations.json << EOF
{
  "log-setting": "detailed-logging-profile"
}
EOF

# Run the command with policy criteria
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --criteria policy_criteria.json \
  --operations operations.json \
  --output updated_config.xml \
  --device-type panorama \
  --context device_group \
  --device-group your-device-group
```

### Remove Log Forwarding Profiles from All Policies

```bash
# Create operations.json to remove log profile
cat > operations.json << EOF
{
  "log-setting": null
}
EOF

# Run the command on all security policies
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --operations operations.json \
  --output updated_config.xml \
  --device-type panorama \
  --context device_group \
  --device-group your-device-group
```

### Direct XML Modification for Adding Log Profiles (Alternative Method)

In cases where the bulk-update command has limitations, you can use a direct XML modification approach:

```python
#!/usr/bin/env python3

import sys
import xml.etree.ElementTree as ET

def add_log_profile_to_policies(xml_file, output_file, profile_name, policy_names):
    """
    Add a log forwarding profile to specific security policies
    """
    # Parse the XML file
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Find all the specified policies and add the log setting
    rules_modified = 0

    # Look for policies in device groups
    for device_group in root.findall('./devices/entry/device-group/entry'):
        dg_name = device_group.get('name')
        print(f"Checking device group: {dg_name}")

        # Look in pre-rulebase for security rules
        for rule in device_group.findall('./pre-rulebase/security/rules/entry'):
            rule_name = rule.get('name')

            if rule_name in policy_names:
                print(f"Found matching rule: {rule_name}")

                # Check if log-setting already exists
                log_setting = rule.find('./log-setting')
                if log_setting is not None:
                    print(f"Rule {rule_name} already has log-setting: {log_setting.text}")
                    log_setting.text = profile_name
                else:
                    print(f"Adding log-setting {profile_name} to rule {rule_name}")
                    log_setting = ET.SubElement(rule, 'log-setting')
                    log_setting.text = profile_name

                rules_modified += 1

    # Save the updated XML
    tree.write(output_file)
    print(f"Modified {rules_modified} rules and saved to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python add_log_setting.py <input_xml> <output_xml> <profile_name> <policy1> [policy2 ...]")
        sys.exit(1)

    xml_file = sys.argv[1]
    output_file = sys.argv[2]
    profile_name = sys.argv[3]
    policy_names = sys.argv[4:]

    add_log_profile_to_policies(xml_file, output_file, profile_name, policy_names)
```

Run the script:
```bash
python add_log_setting.py config.xml updated_config.xml log-profile-name policy1 policy2 policy3
```

### Direct XML Modification for Removing Log Profiles (Alternative Method)

```python
#!/usr/bin/env python3

import sys
import xml.etree.ElementTree as ET

def remove_log_profile_from_policies(xml_file, output_file, policy_names):
    """
    Remove log forwarding profile from specific security policies
    """
    # Parse the XML file
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Find all the specified policies and remove the log setting
    rules_modified = 0

    # Look for policies in device groups
    for device_group in root.findall('./devices/entry/device-group/entry'):
        dg_name = device_group.get('name')
        print(f"Checking device group: {dg_name}")

        # Look in pre-rulebase for security rules
        for rule in device_group.findall('./pre-rulebase/security/rules/entry'):
            rule_name = rule.get('name')

            if rule_name in policy_names:
                print(f"Found matching rule: {rule_name}")

                # Check if log-setting exists
                log_setting = rule.find('./log-setting')
                if log_setting is not None:
                    print(f"Removing log-setting from rule {rule_name}")
                    rule.remove(log_setting)
                    rules_modified += 1
                else:
                    print(f"Rule {rule_name} does not have a log-setting")

    # Save the updated XML
    tree.write(output_file)
    print(f"Modified {rules_modified} rules and saved to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python remove_log_setting.py <input_xml> <output_xml> <policy1> [policy2 ...]")
        sys.exit(1)

    xml_file = sys.argv[1]
    output_file = sys.argv[2]
    policy_names = sys.argv[3:]

    remove_log_profile_from_policies(xml_file, output_file, policy_names)
```

Run the script:
```bash
python remove_log_setting.py config.xml updated_config.xml policy1 policy2 policy3
```

## 3. Logging Configuration

### Enable Session Start Logging for All Rules

```bash
# Create operations.json
cat > operations.json << EOF
{
  "update-logging": {
    "setting": "log-start"
  }
}
EOF

# Run the command
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --operations operations.json \
  --output updated_config.xml
```

### Enable Both Start and End Logging for Rules with Specific Tag

```bash
# Create operations.json
cat > operations.json << EOF
{
  "update-logging": {
    "setting": "log-both"
  }
}
EOF

# Run the command
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --query-filter "MATCH (r:security_rule)-[:has_tag]->(t) WHERE t.name == 'important'" \
  --operations operations.json \
  --output updated_config.xml
```

### Disable All Logging for Rules without Security Profiles

```bash
# Create operations.json
cat > operations.json << EOF
{
  "update-logging": {
    "setting": "log-none"
  }
}
EOF

# Run the command using a complex query filter
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --query-filter "MATCH (r:security_rule) WHERE NOT (r)-[:uses_profile_group]->()" \
  --operations operations.json \
  --output updated_config.xml
```

## 4. Tag Management

### Add a Compliance Tag to Rules with Specific Service

```bash
# Create operations.json
cat > operations.json << EOF
{
  "add-tag": {
    "name": "compliance-2023"
  }
}
EOF

# Run the command
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --query-filter "MATCH (r:security_rule)-[:uses_service]->(s) WHERE s.name == 'HTTPS'" \
  --operations operations.json \
  --output updated_config.xml
```

### Add Multiple Tags in a Single Operation

```bash
# Create a criteria file
cat > criteria.json << EOF
{
  "action": "allow",
  "log-start": "yes"
}
EOF

# Create operations file with multiple tag operations
cat > operations.json << EOF
{
  "add-tag": {
    "name": "reviewed"
  },
  "add-tag": {
    "name": "compliant"
  },
  "add-tag": {
    "name": "audited-2023"
  }
}
EOF

# Run the command with criteria file
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --criteria criteria.json \
  --operations operations.json \
  --output updated_config.xml
```

## 5. Enable/Disable Rules

### Disable All Rules with Destination "any"

```bash
# Create operations.json
cat > operations.json << EOF
{
  "enable-disable": {
    "action": "disable"
  }
}
EOF

# Run the command
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --query-filter "MATCH (r:security_rule)-[:uses_destination]->(d) WHERE d.name == 'any'" \
  --operations operations.json \
  --output updated_config.xml
```

### Enable Rules with Specific Description Pattern

```bash
# Create operations.json
cat > operations.json << EOF
{
  "enable-disable": {
    "action": "enable"
  }
}
EOF

# Run the command
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.description =~ '.*TEMPORARY DISABLED.*'" \
  --operations operations.json \
  --output updated_config.xml
```

## 6. User and Group Management

### Add a User Group to Rules with Specific Destination Zone

```bash
# Create operations.json
cat > operations.json << EOF
{
  "add-object": {
    "name": "finance-users",
    "field": "source-user"
  }
}
EOF

# Run the command
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --query-filter "MATCH (r:security_rule)-[:uses_destination_zone]->(z) WHERE z.name == 'dmz'" \
  --operations operations.json \
  --output updated_config.xml
```

### Remove a User from Multiple Rules

```bash
# Create operations.json
cat > operations.json << EOF
{
  "remove-object": {
    "name": "guest-user",
    "field": "source-user"
  }
}
EOF

# Run the command
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --operations operations.json \
  --output updated_config.xml
```

## 7. Address Object Management

### Add Source Address to Specific Rules

```bash
# Create operations.json
cat > operations.json << EOF
{
  "add-object": {
    "name": "new-server-10.1.1.10",
    "field": "source"
  }
}
EOF

# Run the command
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.name =~ 'web-access-.*'" \
  --operations operations.json \
  --output updated_config.xml
```

### Remove Destination Address from Multiple Rules

```bash
# Create operations.json
cat > operations.json << EOF
{
  "remove-object": {
    "name": "legacy-server-192.168.1.50",
    "field": "destination"
  }
}
EOF

# Run the command
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --operations operations.json \
  --output updated_config.xml
```

## 8. Service Object Management

### Add a Service to All Allow Rules

```bash
# Create operations.json
cat > operations.json << EOF
{
  "add-object": {
    "name": "https-8443",
    "field": "service"
  }
}
EOF

# Run the command
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.action == 'allow'" \
  --operations operations.json \
  --output updated_config.xml
```

## 9. Combined Operations Example

### Comprehensive Policy Update

This example demonstrates how to perform multiple operations in a single command:

```bash
# Create operations.json with multiple operations
cat > operations.json << EOF
{
  "add-tag": {
    "name": "updated-2023"
  },
  "update-logging": {
    "setting": "log-both"
  },
  "add-profile": {
    "type": "group",
    "name": "strict-security"
  },
  "update-description": {
    "text": "[Updated] ",
    "mode": "prepend"
  },
  "enable-disable": {
    "action": "enable"
  }
}
EOF

# Run the command with a specific criteria file
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.action == 'allow'" \
  --operations operations.json \
  --output updated_config.xml
```

## 10. Renaming Policies (Workaround)

Since there's no direct rename operation, you can use this approach:

```bash
# 1. Export rules to JSON
python3 cli.py policy list \
  --config config.xml \
  --type security_pre_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.name =~ 'old-naming-convention-.*'" \
  --output rules_to_rename.json

# 2. Modify the JSON file to change the names (manual step or script)
# 3. Delete the old rules (would require a delete command)
# 4. Import the renamed rules (would require an import command)
```