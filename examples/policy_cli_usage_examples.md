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
# Create operations.json
cat > operations.json << EOF
{
  "add-profile": {
    "type": "log-forwarding",
    "name": "detailed-logging-profile"
  }
}
EOF

# Run the command
python3 cli.py policy bulk-update \
  --config config.xml \
  --type security_pre_rules \
  --query-filter "MATCH (r:security_rule) WHERE r.action == 'deny'" \
  --operations operations.json \
  --output updated_config.xml
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