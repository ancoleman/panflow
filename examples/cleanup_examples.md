# PANFlow Cleanup Command Examples

This document provides practical examples for using the PANFlow cleanup commands to identify and remove unused objects and disabled policies from your PAN-OS configurations.

## Cleanup Unused Objects

### Basic Usage

```bash
# Preview unused address objects (dry-run mode)
python cli.py cleanup unused-objects --config firewall.xml --output updated.xml --dry-run

# Clean up unused address objects
python cli.py cleanup unused-objects --config firewall.xml --output updated.xml
```

### Cleaning Up Multiple Object Types

```bash
# Clean up multiple object types in one command
python cli.py cleanup unused-objects --config firewall.xml --output updated.xml \
  --type address --type service --type tag

# Clean up address group objects
python cli.py cleanup unused-objects --config firewall.xml --output updated.xml \
  --type address-group

# Clean up service objects and service groups
python cli.py cleanup unused-objects --config firewall.xml --output updated.xml \
  --type service --type service-group
  
# Clean up all supported object types
python cli.py cleanup unused-objects --config firewall.xml --output updated.xml \
  --type address --type service --type address-group --type service-group --type tag
```

### Using Context Options

```bash
# Clean up unused objects in Panorama shared context
python cli.py cleanup unused-objects --config panorama.xml --output updated.xml \
  --device-type panorama --context shared

# Clean up unused objects in a specific device group
python cli.py cleanup unused-objects --config panorama.xml --output updated.xml \
  --device-type panorama --context device_group --device-group DG1

# Clean up unused objects in a specific VSYS
python cli.py cleanup unused-objects --config firewall.xml --output updated.xml \
  --device-type firewall --context vsys --vsys vsys1
```

### Using Exclusion Lists

```bash
# Create an exclusion file (protected-objects.json)
cat > protected-objects.json << EOF
[
  "gateway-address",
  "dns-server",
  "management-network",
  "critical-server"
]
EOF

# Run cleanup with exclusion list
python cli.py cleanup unused-objects --config firewall.xml --output updated.xml \
  --exclude-file protected-objects.json
```

### Generating Reports

```bash
# Generate a report of cleaned-up objects
python cli.py cleanup unused-objects --config firewall.xml --output updated.xml \
  --report-file cleanup-report.json

# Analyze the cleanup report with jq (if installed)
jq '.summary' cleanup-report.json
jq '.cleaned_objects.address' cleanup-report.json
```

## Cleanup Disabled Policies

### Basic Usage

```bash
# Preview disabled policies (dry-run mode)
python cli.py cleanup disabled-policies --config firewall.xml --output updated.xml --dry-run

# Clean up disabled security policies
python cli.py cleanup disabled-policies --config firewall.xml --output updated.xml
```

### Cleaning Up Specific Policy Types

```bash
# Clean up disabled security pre-rules in Panorama
python cli.py cleanup disabled-policies --config panorama.xml --output updated.xml \
  --device-type panorama --context device_group --device-group DG1 \
  --type security_pre_rules

# Clean up multiple policy types
python cli.py cleanup disabled-policies --config panorama.xml --output updated.xml \
  --device-type panorama --context device_group --device-group DG1 \
  --type security_pre_rules --type security_post_rules
```

### Using Exclusion Lists

```bash
# Create an exclusion file (protected-policies.json)
cat > protected-policies.json << EOF
[
  "emergency-access-rule",
  "temporary-disabled-rule",
  "maintenance-window-rule"
]
EOF

# Run cleanup with exclusion list
python cli.py cleanup disabled-policies --config firewall.xml --output updated.xml \
  --exclude-file protected-policies.json
```

### Generating Reports

```bash
# Generate a report of cleaned-up policies
python cli.py cleanup disabled-policies --config firewall.xml --output updated.xml \
  --report-file disabled-policies-report.json

# Analyze the report
jq '.summary' disabled-policies-report.json
jq '.cleaned_policies' disabled-policies-report.json
```

## Combined Cleanup Workflows

### Comprehensive Cleanup with Reporting

```bash
# Step 1: Clean up disabled policies
python cli.py cleanup disabled-policies --config firewall.xml --output temp.xml \
  --report-file disabled-report.json

# Step 2: Clean up unused address objects
python cli.py cleanup unused-objects --config temp.xml --output cleaned.xml \
  --type address --report-file unused-addr-report.json

# Step 3: Clean up unused service objects
python cli.py cleanup unused-objects --config cleaned.xml --output final.xml \
  --type service --report-file unused-svc-report.json
```

### Cleanup with Custom Exclusion by Object Type

```bash
# Create type-specific exclusion files
cat > exclude-addresses.json << EOF
["gateway", "dns-server", "management-server"]
EOF

cat > exclude-services.json << EOF
["ssh", "https-alt", "monitoring-service"]
EOF

cat > exclude-policies.json << EOF
["breakglass", "emergency-access"]
EOF

# Run multi-stage cleanup with different exclusion files
python cli.py cleanup disabled-policies --config firewall.xml --output stage1.xml \
  --exclude-file exclude-policies.json

python cli.py cleanup unused-objects --config stage1.xml --output stage2.xml \
  --type address --exclude-file exclude-addresses.json

python cli.py cleanup unused-objects --config stage2.xml --output final.xml \
  --type service --exclude-file exclude-services.json
```

### Panorama Multi-Device Group Cleanup

```bash
# Create a bash script to clean up multiple device groups
cat > cleanup_all_device_groups.sh << 'EOF'
#!/bin/bash
CONFIG_FILE="panorama.xml"
TEMP_FILE="temp.xml"
FINAL_FILE="cleaned_panorama.xml"

# Get list of device groups
DEVICE_GROUPS=$(python -c "from lxml import etree; tree = etree.parse('$CONFIG_FILE'); dgs = tree.xpath('/config/devices/entry[@name=\"localhost.localdomain\"]/device-group/entry/@name'); print(' '.join([dg for dg in dgs]))")

# Copy initial config to temp file
cp "$CONFIG_FILE" "$TEMP_FILE"

# Clean up each device group
for DG in $DEVICE_GROUPS; do
  echo "Cleaning up device group: $DG"
  
  # Disabled policies
  python cli.py cleanup disabled-policies --config "$TEMP_FILE" --output "$TEMP_FILE" \
    --device-type panorama --context device_group --device-group "$DG" \
    --report-file "reports/${DG}_disabled_policies.json" --dry-run
  
  # Unused objects
  python cli.py cleanup unused-objects --config "$TEMP_FILE" --output "$TEMP_FILE" \
    --device-type panorama --context device_group --device-group "$DG" \
    --type address --type service \
    --report-file "reports/${DG}_unused_objects.json" --dry-run
done

# Clean up shared context
echo "Cleaning up shared context"
python cli.py cleanup unused-objects --config "$TEMP_FILE" --output "$FINAL_FILE" \
  --device-type panorama --context shared \
  --type address --type service --type tag \
  --report-file "reports/shared_unused_objects.json" --dry-run

echo "Cleanup preview complete. Remove --dry-run flag to execute actual cleanup."
EOF

chmod +x cleanup_all_device_groups.sh
```

## Advanced Integration Examples

### Combining with Object Finding

```bash
# Find objects with a specific pattern, then clean up
python cli.py object find --config firewall.xml --type address --pattern "temp-*" --output temp_objects.json

# Parse the results to create an inclusion list (only clean up temp objects)
jq -r '.[].name' temp_objects.json > temp_objects_list.txt
cat temp_objects_list.txt | jq -Rs 'split("\n") | map(select(length > 0))' > cleanup_only_these.json

# Run cleanup with custom logic (clean up only temp objects)
python cli.py cleanup unused-objects --config firewall.xml --output cleaned.xml \
  --type address --include-file cleanup_only_these.json
```

### Integration with Graph Queries

```bash
# Use graph query to find address objects in a specific subnet
python cli.py query execute --config config.xml \
  --query "MATCH (a:address) WHERE a.value CONTAINS '10.0.0' AND NOT (()-[:uses-source|uses-destination]->(a)) RETURN a.name" \
  --format json --output subnet_unused.json

# Parse query results to create an inclusion list
jq -r '.[].a\.name' subnet_unused.json > subnet_list.txt
cat subnet_list.txt | jq -Rs 'split("\n") | map(select(length > 0))' > subnet_objs.json

# Clean up only the objects from the query results
python cli.py cleanup unused-objects --config config.xml --output cleaned.xml \
  --type address --include-file subnet_objs.json
```

### Periodic Cleanup Script

```bash
# Create a script for regular cleanup maintenance
cat > weekly_cleanup.sh << 'EOF'
#!/bin/bash
DATE=$(date +"%Y%m%d")
CONFIG_DIR="/path/to/configs"
LATEST_CONFIG="$CONFIG_DIR/current.xml"
BACKUP_DIR="$CONFIG_DIR/backups"
REPORT_DIR="$CONFIG_DIR/reports/$DATE"

# Create directories if they don't exist
mkdir -p "$BACKUP_DIR"
mkdir -p "$REPORT_DIR"

# Create a backup before cleaning
cp "$LATEST_CONFIG" "$BACKUP_DIR/pre_cleanup_$DATE.xml"

# Create report files
DISABLED_REPORT="$REPORT_DIR/disabled_policies.json"
UNUSED_ADDR_REPORT="$REPORT_DIR/unused_addresses.json"
UNUSED_SVC_REPORT="$REPORT_DIR/unused_services.json"

# Run cleanup commands
echo "Step 1: Clean up disabled policies"
python cli.py cleanup disabled-policies \
  --config "$LATEST_CONFIG" \
  --output "$CONFIG_DIR/stage1.xml" \
  --report-file "$DISABLED_REPORT"

echo "Step 2: Clean up unused address objects"
python cli.py cleanup unused-objects \
  --config "$CONFIG_DIR/stage1.xml" \
  --output "$CONFIG_DIR/stage2.xml" \
  --type address \
  --report-file "$UNUSED_ADDR_REPORT"

echo "Step 3: Clean up unused service objects"
python cli.py cleanup unused-objects \
  --config "$CONFIG_DIR/stage2.xml" \
  --output "$CONFIG_DIR/cleaned_$DATE.xml" \
  --type service \
  --report-file "$UNUSED_SVC_REPORT"

# Update the current config
cp "$CONFIG_DIR/cleaned_$DATE.xml" "$LATEST_CONFIG"

# Generate summary report
echo "Cleanup Summary for $DATE" > "$REPORT_DIR/summary.txt"
echo "----------------------" >> "$REPORT_DIR/summary.txt"
echo "Disabled policies removed: $(jq '.summary.total_cleaned_up' $DISABLED_REPORT)" >> "$REPORT_DIR/summary.txt"
echo "Unused addresses removed: $(jq '.summary.total_cleaned_up' $UNUSED_ADDR_REPORT)" >> "$REPORT_DIR/summary.txt"
echo "Unused services removed: $(jq '.summary.total_cleaned_up' $UNUSED_SVC_REPORT)" >> "$REPORT_DIR/summary.txt"
echo "----------------------" >> "$REPORT_DIR/summary.txt"

echo "Cleanup completed. Reports saved to $REPORT_DIR"
EOF

chmod +x weekly_cleanup.sh
```

## Troubleshooting Tips

### Debugging Cleanup Issues

```bash
# Run with verbose logging to see more details
python cli.py cleanup unused-objects --config firewall.xml --output updated.xml \
  --dry-run --verbose

# Save detailed logs to a file
python cli.py cleanup unused-objects --config firewall.xml --output updated.xml \
  --dry-run --log-file cleanup_debug.log --log-level debug

# Check a specific object for references
python cli.py report reference-check --config firewall.xml \
  --type address --name "object-not-being-cleaned" --output references.json
```

For more information on how PANFlow determines which objects and policies to clean up, see the [Cleanup Detection Documentation](../docs/cleanup_detection.md).