# Troubleshooting Guide

This guide addresses common issues you might encounter when using PANFlow and provides solutions.

## Installation Issues

### Package Not Found

**Problem**: `pip install panflow` fails with "Package not found" error.

**Solution**: 
- Verify you're using a supported Python version (3.7+)
- Try upgrading pip: `pip install --upgrade pip`
- Try installing with the full URL: `pip install git+https://github.com/yourusername/panflow.git`

### Dependency Conflicts

**Problem**: Installation fails due to dependency conflicts.

**Solution**:
- Create a fresh virtual environment: `python -m venv panflow-env`
- Use `--no-dependencies` and install dependencies manually
- Check for conflicts with existing packages in your environment

## Configuration Loading Issues

### XML Parsing Errors

**Problem**: `ParseError: Failed to parse XML` when loading configurations.

**Solution**:
- Verify the XML file is valid
- Check for XML declaration issues
- Ensure the file encoding is UTF-8
- Try opening and re-saving the file in a text editor

### Version Detection Issues

**Problem**: Incorrect PAN-OS version detection.

**Solution**:
- Specify the version explicitly: `PANFlowConfig(config_file="config.xml", version="10.2")`
- Check if the XML configuration has the correct version attribute
- Update to a more recent version of PANFlow that supports your PAN-OS version

## XPath Operation Issues

### XPath Resolution Failures

**Problem**: `XPathError: Failed to evaluate XPath` when accessing configuration elements.

**Solution**:
- Enable debug logging to see the actual XPath being used
- Check if the context type is correct (shared, device_group, vsys)
- Verify the object type matches PAN-OS naming conventions
- Check if your PAN-OS version is supported

### Elements Not Found

**Problem**: Cannot find elements that you know exist in the configuration.

**Solution**:
- Confirm the object exists in the expected context
- Check for case sensitivity in object names
- Use the CLI to verify the exact path: `panflow object list --config config.xml --type address`
- Enable verbose logging: `panflow --verbose object list ...`

## Merge Operation Issues

### Conflict Resolution Errors

**Problem**: `ConflictError` when merging objects or policies.

**Solution**:
- Use a different conflict strategy: `ConflictStrategy.MERGE` or `ConflictStrategy.RENAME`
- Examine the conflicting elements in both source and target
- Use `--dry-run` with CLI to preview changes without applying them
- Handle conflicts programmatically with a try/except block

### Referenced Objects Missing

**Problem**: Merged elements reference objects that don't exist in the target.

**Solution**:
- Enable `copy_references=True` when merging
- Manually copy required reference objects first
- Use `merger.merge_all_objects()` to merge all object types at once
- Check the `referenced_objects` attribute of the merger after a merge operation

## Security Issues

### XXE Vulnerabilities

**Problem**: Security concerns about XML External Entity (XXE) attacks.

**Solution**:
- PANFlow 0.1.0+ includes protection against XXE attacks
- Ensure you're using the latest version with security patches
- Avoid loading XML from untrusted sources
- Use the secure parsing methods in `xml_utils.py`

### File Size Limits

**Problem**: `SecurityError: File size exceeds maximum allowed size`

**Solution**:
- For large files, increase the limit: `parse_xml(source, max_file_size=200*1024*1024)`
- Split large configurations into smaller files
- Use more efficient processing with streaming parsers

## Performance Issues

### Slow Operations on Large Configurations

**Problem**: Operations are very slow on large configurations.

**Solution**:
- Use specific context paths instead of searching the entire configuration
- Enable result caching for frequently accessed elements
- Use batch operations instead of individual operations
- Consider splitting the configuration into smaller files

### Memory Usage Problems

**Problem**: High memory usage or out-of-memory errors.

**Solution**:
- Process large configurations in chunks
- Use more specific XPath queries
- Release references to large objects when done
- Use streaming XML processing for very large files

## CLI Issues

### Command Not Found

**Problem**: `panflow: command not found` after installation.

**Solution**:
- Check if the package was installed in user mode
- Verify the installation path is in your PATH environment variable
- Try installing with `pip install -e .` from the source directory
- Check if setuptools properly installed the entry point

### CLI Parameter Errors

**Problem**: `BadParameter` or parameter validation errors.

**Solution**:
- Check parameter syntax and requirements in CLI documentation
- Use the `--help` flag to see parameter requirements: `panflow object add --help`
- Ensure context parameters match the context type (e.g., device_group for device_group context)
- For file paths, use absolute paths or verify relative paths

## Logging and Debugging

### Enabling Debug Logging

To get more detailed logging information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or with the CLI:

```bash
panflow --verbose --log-level debug command [options]
```

### Logging to a File

To save logs to a file:

```bash
panflow --log-file panflow.log command [options]
```

### Checking Version Information

To verify PANFlow and dependency versions:

```bash
pip show panflow
pip show lxml
```

## Getting Additional Help

If you encounter issues not covered in this guide:

1. Check the [GitHub Issues](https://github.com/yourusername/panflow/issues) for similar problems
2. Search the documentation for specific error messages
3. Enable debug logging and check the full error traceback
4. File a new issue with detailed information about the problem