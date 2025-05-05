# PANFlow Documentation

Welcome to the PANFlow documentation! PANFlow is a comprehensive library for working with Palo Alto Networks PAN-OS XML configurations, supporting both Panorama and firewall configurations across multiple PAN-OS versions.

## Documentation Sections

- **[Getting Started](getting_started.md)**: Installation and basic usage guides
- **[Tutorials](tutorials/index.md)**: Step-by-step guides for common tasks
- **[API Reference](api/index.md)**: Detailed API documentation
- **[Examples](examples/index.md)**: Example code for various use cases
- **[Migration Guide](migration_guide.md)**: Guide for migrating from previous versions

## Key Concepts

1. **[Version-aware XML handling](dynamic_xpath.md)**: Automatically adjusts XPath expressions for different PAN-OS versions (10.1, 10.2, 11.0, 11.1, 11.2)
2. **[Context support](contexts.md)**: Working with shared objects, device groups, templates, and virtual systems
3. **[Object management](api/objects.md)**: Managing PAN-OS objects
4. **[Policy management](api/policies.md)**: Working with security rules, NAT rules, and more
5. **[Bulk operations](api/bulk_operations.md)**: Tools for modifying multiple configuration elements
6. **[Deduplication](deduplication.md)**: Finding and merging duplicate objects
7. **[Error handling](error_handling.md)**: Understanding and handling PANFlow exceptions

## Main Features

- Version-aware XML handling for different PAN-OS versions
- Flexible context support (shared, device groups, templates, vsys)
- Comprehensive object and policy management
- Powerful bulk operations for efficient configuration changes
- Configuration merging and conflict resolution
- Report generation for unused objects, duplicates, and more
- Advanced deduplication engine for finding and merging duplicate objects (address, service, and tag objects)
- Command-line interface for all main operations

## CLI Reference

For CLI usage, see the [CLI Reference](cli_reference.md) or run:

```bash
panflow --help
```

## Contributing

See [Contributing Guide](contributing.md) for information on how to contribute to PANFlow.

## Troubleshooting

Common issues and their solutions are documented in the [Troubleshooting Guide](troubleshooting.md).