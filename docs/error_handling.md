# Error Handling in PANFlow

PANFlow provides a structured approach to error handling through a consistent exception hierarchy.

## Exception Hierarchy

All PANFlow exceptions inherit from the base `PANFlowError` class, allowing you to catch all PANFlow-specific errors:

```
PANFlowError
├── ConfigError
├── ValidationError
├── ParseError
├── XPathError
├── ContextError
├── ObjectError
│   ├── ObjectNotFoundError
│   └── ObjectExistsError
├── PolicyError
│   ├── PolicyNotFoundError
│   └── PolicyExistsError
├── MergeError
│   └── ConflictError
├── VersionError
├── FileOperationError
├── BulkOperationError
└── SecurityError
```

## Basic Error Handling

You can catch specific exceptions or use the base class to catch any PANFlow error:

```python
from panflow import PANFlowError, ObjectNotFoundError, ParseError

try:
    # PANFlow operations
    config = PANFlowConfig("firewall.xml")
    address = config.get_object("address", "web-server", "shared")
    
except ObjectNotFoundError:
    # Handle specific case of object not found
    print("The requested object was not found")
    
except ParseError as e:
    # Handle XML parsing errors
    print(f"Failed to parse XML: {e}")
    
except PANFlowError as e:
    # Handle any other PANFlow error
    print(f"PANFlow operation failed: {e}")
    
except Exception as e:
    # Handle any other exception
    print(f"Unexpected error: {e}")
```

## Common Exceptions

### ObjectNotFoundError

Raised when an object cannot be found in the specified context:

```python
try:
    address = config.get_object("address", "nonexistent", "shared")
except ObjectNotFoundError:
    print("Address object does not exist")
```

### ObjectExistsError

Raised when an object already exists but shouldn't:

```python
try:
    # Attempt to add an object that already exists
    config.add_object("address", "existing-address", properties, "shared")
except ObjectExistsError:
    print("Cannot add: this address already exists")
```

### ParseError

Raised when XML parsing fails:

```python
try:
    config = PANFlowConfig("invalid.xml")
except ParseError as e:
    print(f"Failed to parse configuration: {e}")
```

### ConflictError

Raised when there's a conflict during a merge operation:

```python
try:
    merger.copy_object("address", "conflicting-object", "shared", "shared")
except ConflictError as e:
    print(f"Conflict occurred during merge: {e}")
```

### SecurityError

Raised for security-related issues:

```python
try:
    tree, root = parse_xml("suspicious.xml")
except SecurityError as e:
    print(f"Security violation: {e}")
```

## Working with BulkOperationError

The `BulkOperationError` provides additional information about which operations succeeded and which failed:

```python
try:
    updater.bulk_update_policies("security_rules", criteria, operations)
except BulkOperationError as e:
    print(f"Bulk operation partially failed: {e}")
    print(f"Successful operations: {e.successful}")
    print(f"Failed operations: {e.failed}")
```

## Best Practices

1. **Catch specific exceptions first**: Start with the most specific exception types before catching more general ones
2. **Always log exceptions**: Log exceptions with appropriate detail for troubleshooting
3. **Use appropriate granularity**: Catch exceptions at an appropriate level of your application
4. **Handle cleanup**: Ensure proper cleanup in your exception handlers
5. **Provide useful feedback**: Give users clear information about what went wrong and how to fix it

## Error Messages

PANFlow error messages follow a consistent format that includes:

- The specific error type
- A descriptive message explaining what went wrong
- Where applicable, the specific object, context, or operation that failed

This consistency makes errors easier to understand and troubleshoot.