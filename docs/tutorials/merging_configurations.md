# Tutorial: Merging Configuration Elements

One of the most powerful features of PANFlow is its ability to merge configuration elements between different PAN-OS configurations. This tutorial will guide you through the process of merging objects and policies.

## Prerequisites

- Basic understanding of PAN-OS configurations
- Two PAN-OS XML configuration files (source and target)
- PANFlow installed and working

## Understanding Configuration Merging

PANFlow allows you to selectively merge:

- Individual objects (addresses, services, etc.)
- Groups of objects based on criteria
- Individual policies
- Groups of policies based on criteria

The merging process includes:

1. Loading source and target configurations
2. Identifying elements to merge
3. Resolving any conflicts using a conflict resolution strategy
4. Copying references if needed
5. Saving the updated target configuration

## Conflict Resolution Strategies

PANFlow supports multiple conflict resolution strategies:

- `skip`: Skip merging if a conflict is detected (default)
- `overwrite`: Overwrite the target with the source element
- `merge`: Attempt to merge the properties of both elements
- `rename`: Rename the source element (adds a suffix)
- `keep_source`: Always use the source element's properties
- `keep_target`: Always use the target element's properties

## Merging Individual Objects

Here's how to merge a single object:

```python
from panflow import PANFlowConfig
from panflow.core.conflict_resolver import ConflictStrategy

# Load source and target configurations
source_config = PANFlowConfig("source.xml")
target_config = PANFlowConfig("target.xml")

# Merge a single address object
success = source_config.merge_object(
    target_config,
    "address",
    "web-server",
    "shared",  # Source context
    "shared",  # Target context
    skip_if_exists=False,  # Don't skip if object exists
    copy_references=True,  # Copy referenced objects (e.g., tags)
    conflict_strategy=ConflictStrategy.MERGE  # Attempt to merge properties
)

if success:
    print("Object merged successfully")
    # Save the target configuration
    target_config.save("updated-target.xml")
else:
    print("Failed to merge object")
```

## Merging Objects Based on Criteria

You can merge multiple objects based on criteria:

```python
from panflow.core.object_merger import ObjectMerger

# Create an object merger
merger = ObjectMerger(
    source_config.tree,
    target_config.tree,
    source_config.device_type,
    target_config.device_type,
    source_config.version,
    target_config.version
)

# Define filter criteria for objects to merge
criteria = {
    "tag": "production"  # Merge objects with the "production" tag
}

# Merge objects matching criteria
copied, total = merger.copy_objects(
    "address",
    "shared",  # Source context
    "shared",  # Target context
    object_names=None,  # No specific names (use criteria instead)
    filter_criteria=criteria,
    skip_if_exists=False,
    copy_references=True,
    conflict_strategy=ConflictStrategy.MERGE
)

print(f"Merged {copied} of {total} objects")

# Save the target configuration
target_config.save("updated-target.xml")
```

## Merging Policies

Merging policies is similar to merging objects:

```python
# Merge a security policy
success = source_config.merge_policy(
    target_config,
    "security_pre_rules",
    "allow-web",
    "device_group",  # Source context
    "device_group",  # Target context
    skip_if_exists=False,
    copy_references=True,
    position="top",  # Place at the top of the rulebase
    source_device_group="DG1",
    target_device_group="DG2"
)

if success:
    print("Policy merged successfully")
    # Save the target configuration
    target_config.save("updated-target.xml")
else:
    print("Failed to merge policy")
```

## Handling Merge Conflicts

You can handle merge conflicts by catching the `ConflictError` exception:

```python
from panflow import ConflictError

try:
    success = source_config.merge_object(
        target_config,
        "address",
        "web-server",
        "shared",
        "shared",
        skip_if_exists=False,
        conflict_strategy=ConflictStrategy.OVERWRITE
    )
    
    if success:
        print("Object merged successfully")
        target_config.save("updated-target.xml")
        
except ConflictError as e:
    print(f"Conflict detected: {e}")
    # You could implement interactive conflict resolution here
    # or log the conflict for later review
```

## Using the CLI for Merging

PANFlow's CLI provides commands for merging:

```bash
# Merge a single object
panflow merge object \
  --source-config source.xml \
  --target-config target.xml \
  --type address \
  --name web-server \
  --conflict-strategy merge \
  --output updated-target.xml

# Merge multiple objects
panflow merge objects \
  --source-config source.xml \
  --target-config target.xml \
  --type address \
  --criteria criteria.json \
  --conflict-strategy merge \
  --output updated-target.xml

# Merge a policy
panflow merge policy \
  --source-config source.xml \
  --target-config target.xml \
  --type security_pre_rules \
  --name allow-web \
  --position top \
  --conflict-strategy merge \
  --output updated-target.xml
```

## Best Practices

1. **Always use dry-run first**: Use the `--dry-run` flag with CLI commands to preview changes
2. **Test with a backup**: Test merges on a backup of your target configuration
3. **Be specific with conflict strategies**: Choose the appropriate strategy for each merge
4. **Review after merging**: Always review the merged configuration for correctness
5. **Consider references**: Decide whether to copy references based on your needs
6. **Use version-aware merging**: Make sure source and target versions are compatible

## Advanced Topics

### Customizing Merge Behavior

You can customize merge behavior by subclassing `ObjectMerger` or `PolicyMerger`:

```python
class CustomObjectMerger(ObjectMerger):
    def merge_element_properties(self, source_element, target_element):
        # Custom merging logic
        result = super().merge_element_properties(source_element, target_element)
        # Additional post-merge processing
        return result
```

### Batch Merging

For large-scale merges, use the batch merging capabilities:

```python
# Merge all address objects in one operation
merger.merge_all_objects(
    ["address", "address-group", "service"],
    "shared",
    "shared",
    skip_if_exists=False,
    copy_references=True,
    conflict_strategy=ConflictStrategy.RENAME
)
```

## Conclusion

Configuration merging is a powerful feature that allows you to consolidate configurations from multiple sources. By understanding the different strategies and options, you can efficiently manage complex PAN-OS deployments.

For more details on the merging APIs, see the [API Reference](../api/object_merger.md) and [API Reference](../api/policy_merger.md).