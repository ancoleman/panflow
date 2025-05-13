# Testing Bulk Policy Operations

This guide describes how to test the newly implemented bulk policy operations in the Natural Language Query (NLQ) module.

## Test Script

The repository includes a test script `test_bulk_update.py` that can be used to verify bulk policy operations through natural language queries.

### Prerequisites

- PANFlow installed with poetry (`poetry install`)
- A valid PAN-OS configuration file to test against

### Running the Tests

To run the test script, use the following command:

```bash
# Activate poetry environment if not already activated
poetry shell

# Run test for a specific operation
python test_bulk_update.py --config /path/to/config.xml --output /path/to/output.xml --operation <operation_type>
```

Where `<operation_type>` is one of:
- `add_tag` - Test adding tags to policies
- `enable` - Test enabling policies
- `disable` - Test disabling policies
- `set_action` - Test changing policy actions to deny
- `enable_logging` - Test enabling logging for policies
- `disable_logging` - Test disabling logging for policies

### Example

```bash
# Test adding tags to policies
python test_bulk_update.py --config samples/panorama.xml --output output.xml --operation add_tag

# Test enabling policies
python test_bulk_update.py --config samples/panorama.xml --output output.xml --operation enable
```

## Testing with NLQ Command Directly

You can also test bulk operations using the NLQ command directly:

```bash
# Test adding tags
poetry run panflow nlq query "add tag 'reviewed' to all security policies" --config samples/panorama.xml --output output.xml

# Test enabling policies
poetry run panflow nlq query "enable all security policies" --config samples/panorama.xml --output output.xml

# Test disabling policies
poetry run panflow nlq query "disable all security policies" --config samples/panorama.xml --output output.xml

# Test setting policy actions
poetry run panflow nlq query "set action to allow for all security rules" --config samples/panorama.xml --output output.xml

# Test enabling logging
poetry run panflow nlq query "enable logging for all security policies" --config samples/panorama.xml --output output.xml

# Test disabling logging
poetry run panflow nlq query "disable logging for all security policies" --config samples/panorama.xml --output output.xml
```

## Verifying Results

After running the test, you can verify the changes in the output file:

1. Check that the specified changes were applied correctly
2. Verify that the XML structure is valid
3. Confirm that the policies were properly identified and modified

### Verifying XML Changes

You can use the following command to verify changes between the original and modified XML:

```bash
# Compare files using diff
diff -u samples/panorama.xml output.xml | grep -A 5 -B 5 "<tag>" # For tag changes
diff -u samples/panorama.xml output.xml | grep -A 5 -B 5 "<disabled>" # For enable/disable changes
diff -u samples/panorama.xml output.xml | grep -A 5 -B 5 "<action>" # For action changes
diff -u samples/panorama.xml output.xml | grep -A 5 -B 5 "<log-" # For logging changes
```

## Notes on Output Formats

The bulk update operations support multiple output formats:
- JSON
- Table
- CSV
- YAML
- HTML
- Text (default)

You can specify the output format using the `--format` parameter:

```bash
poetry run panflow nlq query "add tag 'reviewed' to all security policies" --config samples/panorama.xml --output output.xml --format table
```