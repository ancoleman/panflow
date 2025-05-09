# CLI Command Migration Plan

This document outlines the plan for migrating all CLI commands to the new command pattern abstraction.

## Overview

PANFlow has approximately 45 CLI commands spread across multiple modules. The migration will convert these commands to use the new command pattern abstraction, which provides standardized error handling, configuration loading, context parameter handling, and output formatting.

## Migration Goals

1. **Consistency**: Ensure consistent behavior across all commands
2. **Reduced Duplication**: Eliminate duplicated code patterns
3. **Improved Maintainability**: Centralize common functionality
4. **Enhanced User Experience**: Provide consistent error messages and output formats
5. **Backward Compatibility**: Maintain compatibility with existing command usage patterns

## Migration Process

The migration will be carried out in four phases:

### Phase 1: Preparation (Complete)

- ✅ Create the command pattern abstraction framework
- ✅ Develop the migration tool
- ✅ Create test cases for the command pattern
- ✅ Develop the migration documentation

### Phase 2: Proof of Concept (In Progress)

- ✅ Migrate example commands to validate the approach
- ⬜ Test the migrated commands thoroughly
- ⬜ Refine the migration tool based on findings
- ⬜ Update documentation based on practical experience

### Phase 3: Systematic Migration

- ⬜ Migrate commands in order of priority:
  1. Object commands
  2. Policy commands
  3. Report commands
  4. Group commands
  5. Merge commands
  6. Query commands
  7. Deduplicate commands
  8. NAT commands
  9. NLQ commands
- ⬜ Test each command after migration
- ⬜ Update CLI_USAGE.md to reflect the new capabilities

### Phase 4: Integration and Cleanup

- ⬜ Remove deprecated code patterns
- ⬜ Update all documentation
- ⬜ Perform integration testing
- ⬜ Release as a new version

## Command Priority List

The following is a prioritized list of commands to migrate:

| Priority | Module | Command | Complexity | Status |
|----------|--------|---------|------------|--------|
| 1 | object_commands.py | list_objects | Low | Migrated |
| 2 | object_commands.py | add_object | Low | Migrated |
| 3 | object_commands.py | update_object | Medium | Pending |
| 4 | object_commands.py | delete_object | Low | Pending |
| 5 | object_commands.py | filter_objects | Medium | Pending |
| 6 | object_commands.py | bulk_delete_objects | Medium | Pending |
| 7 | object_commands.py | find_object | Medium | Pending |
| 8 | object_commands.py | find_duplicates | High | Pending |
| 9 | policy_commands.py | list_policies | Low | Pending |
| 10 | policy_commands.py | add_policy | Medium | Pending |
| ... | ... | ... | ... | ... |

## Migration Strategy by Command Type

Different commands require different migration strategies based on their complexity and specific requirements:

### Simple Commands

Examples: list_objects, get_object, delete_object

Strategy: Use the standard_command decorator for full automation

### Commands with File Output

Examples: add_object, update_object, bulk_update_policies

Strategy: Use individual decorators with custom output handling

### Complex Commands

Examples: find_duplicates, merge_policies

Strategy: Use the CommandBase class directly for more control

## Testing Strategy

Each migrated command will be tested using:

1. **Unit Tests**: Test command functionality with mocked dependencies
2. **Integration Tests**: Test command integration with other components
3. **Compatibility Tests**: Verify backward compatibility with existing usage
4. **Parameter Tests**: Test all parameter combinations
5. **Error Handling Tests**: Verify correct error reporting

## Rollout Plan

1. **Release as Beta**: Initially release the migrated commands as -new variants (e.g., list-new)
2. **Gather Feedback**: Collect user feedback on the new commands
3. **Finalize Migration**: Replace original commands with migrated versions
4. **Release New Version**: Release as a new minor version (v0.3.0)

## Success Criteria

The migration will be considered successful when:

1. All commands have been migrated to the new pattern
2. All tests pass
3. The codebase shows a significant reduction in duplicated code
4. User experience is improved with consistent output and error handling
5. No regressions in functionality

## Timeline

- Phase 1 (Preparation): Complete
- Phase 2 (Proof of Concept): 1 week
- Phase 3 (Systematic Migration): 2-3 weeks
- Phase 4 (Integration and Cleanup): 1 week

Total estimated time: 4-5 weeks

## Resources

- [CLI Command Pattern Documentation](cli_command_pattern.md)
- [CLI Command Migration Guide](cli_command_migration.md)
- Migration Tool: `tools/cli_command_migrator.py`
- Migration Script: `cli_migrate.py`
- Example Migrated Commands: `panflow/cli/commands/migrated/`