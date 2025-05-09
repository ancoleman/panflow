# CLI Command Migration Guide

This guide provides detailed instructions for migrating existing CLI commands to the new command pattern abstraction. It includes both manual migration steps and guidance on using the automated migration tool.

## Table of Contents

1. [Understanding the Command Pattern](#understanding-the-command-pattern)
2. [Benefits of Migration](#benefits-of-migration)
3. [Command Classification](#command-classification)
4. [Manual Migration Steps](#manual-migration-steps)
5. [Automated Migration](#automated-migration)
6. [Testing Migrated Commands](#testing-migrated-commands)
7. [Troubleshooting](#troubleshooting)

## Understanding the Command Pattern

The command pattern abstraction introduced in PANFlow v0.3.0 provides a standardized approach to implementing CLI commands. The key components are:

- **CommandBase class**: Provides common functionality for all commands
- **Decorator functions**: Apply common patterns to command functions
- **Standard command pattern**: Combines all standard command processing

Read [cli_command_pattern.md](cli_command_pattern.md) for a detailed overview of the pattern.

## Benefits of Migration

Migrating existing commands to the new pattern provides several benefits:

1. **Reduced code duplication**: Common patterns like error handling and output formatting are centralized
2. **Improved consistency**: Commands handle errors and format output in a consistent way
3. **Enhanced maintainability**: Changes to common functionality only need to be made once
4. **Better type safety**: Parameter injection with clear type annotations
5. **Simplified implementation**: Focus on core command logic rather than boilerplate

## Command Classification

Before migrating commands, classify them based on their compatibility with the command pattern:

### Class 1: Fully Compatible

Commands that:
- Take a config file, device type, and version
- Include context parameters (context, device_group, vsys, template)
- Use standard output formatting

These can be migrated using the `@standard_command` decorator.

### Class 2: Partially Compatible

Commands that:
- Take some but not all standard parameters
- Have special processing needs

These can be migrated using individual decorators (`@command_error_handler`, `@config_loader`, etc.).

### Class 3: Special Cases

Commands that:
- Have unique parameter handling
- Use custom error handling or output formatting
- Integrate with external services

These may need to use the CommandBase class directly.

## Manual Migration Steps

### Step 1: Import Required Components

Add the following imports to your command module:

```python
from ..command_base import (
    CommandBase, command_error_handler, config_loader, 
    context_handler, output_formatter, standard_command,
    OutputFormat
)
```

### Step 2: Update Output Format Parameters

Convert string output format parameters to use the OutputFormat enum:

```python
# Before
output_format: str = typer.Option("json", "--format", "-f", help="Output format")

# After
output_format: OutputFormat = typer.Option(
    OutputFormat.JSON, "--format", "-f", 
    help="Output format (json, table, text, csv, yaml)"
)
```

### Step 3: Add Decorator and Update Function Signature

Add the appropriate decorator and update the function signature to include injected parameters:

```python
# Before
@app.command("list")
def list_objects(
    config: str = ConfigOptions.config_file(),
    object_type: str = ObjectOptions.object_type(),
    # Other parameters...
):
    # Implementation...

# After (using standard_command)
@app.command("list")
@standard_command
def list_objects(
    panflow_config: PANFlowConfig,  # Injected by config_loader
    context_kwargs: Dict[str, str],  # Injected by context_handler
    object_type: str = ObjectOptions.object_type(),
    # Other parameters...
):
    # Implementation...
```

### Step 4: Update Implementation

Remove code that is now handled by the decorators:

1. Remove configuration loading (handled by `config_loader`)
2. Remove context parameter processing (handled by `context_handler`)
3. Remove try/except blocks (handled by `command_error_handler`)
4. Remove manual output formatting (handled by `output_formatter`)

### Step 5: Update Return Value

Make sure your function returns the data to be formatted:

```python
# Before
if output_file:
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
else:
    print(json.dumps(result, indent=2))

# After
return result  # output_formatter will handle the formatting
```

## Automated Migration

For commands that follow common patterns, you can use the `cli_command_migrator.py` script to automate the migration process:

```
python tools/cli_command_migrator.py --module panflow/cli/commands/object_commands.py --command list_objects
```

The script will:
1. Analyze the command function
2. Generate a migrated version
3. Optionally create a backup of the original file
4. Replace the command with the migrated version

## Testing Migrated Commands

After migrating a command, test it thoroughly to ensure it behaves consistently:

1. Run the unit tests for the command
2. Test with various parameter combinations
3. Test error handling by triggering deliberate errors
4. Compare output with the original command

Use the `test_command_migration.py` and `test_command_pattern.py` tests as references.

## Troubleshooting

### Common Migration Issues

1. **Incorrect function signature**: Make sure the injected parameters (`panflow_config`, `context_kwargs`) are correctly typed.

2. **Missing return value**: The function must return the data to be formatted.

3. **Parameter conflicts**: Rename any existing parameters that conflict with injected parameters.

4. **Custom error handling**: If you need custom error handling, use individual decorators instead of `@standard_command`.

5. **Invalid OutputFormat values**: Make sure your code handles all possible values in the OutputFormat enum.

### Solutions

1. **Partially migrating**: You can mix the old style and new pattern by using individual decorators.

2. **Complex commands**: For very complex commands, consider using the CommandBase class directly.

3. **Conditional formatting**: If you need conditional output formatting, handle it in the function and return the formatted string.

4. **External services**: If your command interacts with external services, you may need custom error handling.