# CLI Command Pattern Abstraction

This document outlines the CLI command pattern abstraction used in PANFlow to standardize command implementation, error handling, and output formatting.

## Overview

PANFlow's CLI commands have been refactored to use a common command pattern that reduces duplication and improves maintainability. The key components of this pattern are:

1. **CommandBase class**: A base class that provides common functionality for all commands
2. **Decorator functions**: A set of decorators that apply common patterns to command functions
3. **Standard command pattern**: A combined decorator that applies all standard command processing
4. **Consistent output formatting**: Standardized output formats and formatting logic

## CommandBase Class

The `CommandBase` class in `panflow/cli/command_base.py` provides common functionality for PANFlow CLI commands, including:

- Configuration loading
- Context parameter handling
- Output formatting
- Error handling

### Key Methods

| Method | Description |
|--------|-------------|
| `load_config` | Loads a PANFlowConfig from a file |
| `get_context_params` | Gets context parameters for the command |
| `format_output` | Formats and displays or saves command output |
| `handle_error` | Handles command errors consistently |

## Command Decorators

The command_base module provides several decorators that can be applied to command functions:

### command_error_handler

```python
@command_error_handler
def my_command(...):
    # Command implementation
```

This decorator catches exceptions and handles them consistently, logging errors and providing user-friendly error messages.

### config_loader

```python
@config_loader
def my_command(panflow_config: PANFlowConfig, ...):
    # Command implementation using panflow_config
```

This decorator extracts config_file, device_type, and version arguments, loads the configuration, and adds it as a 'panflow_config' parameter to the function.

### context_handler

```python
@context_handler
def my_command(context_kwargs: Dict[str, str], ...):
    # Command implementation using context_kwargs
```

This decorator extracts context, device_group, vsys, and template arguments, and adds a 'context_kwargs' parameter to the function.

### output_formatter

```python
@output_formatter
def my_command(...):
    # Command implementation returning data to be formatted
    return data
```

This decorator formats the return value of the function based on the output_format and output_file parameters.

### standard_command

```python
@standard_command
def my_command(panflow_config: PANFlowConfig, context_kwargs: Dict[str, str], ...):
    # Command implementation with all standard handling
    return data
```

This combined decorator applies error_handler, config_loader, context_handler, and output_formatter in a single decorator.

## Output Formatting

The command pattern provides standardized output formatting through the `OutputFormat` enum and the `format_output` method. Supported formats include:

- JSON
- Table (rich formatted tables)
- Text
- CSV
- YAML
- HTML

## Example Usage

### Using the Standard Command Decorator

```python
@app.command("list")
@standard_command
def list_objects(
    panflow_config: PANFlowConfig,
    context_kwargs: Dict[str, str],
    object_type: str = ObjectOptions.object_type(),
    output_format: OutputFormat = typer.Option(OutputFormat.JSON, "--format", "-f"),
):
    # Implementation using panflow_config and context_kwargs
    # Return data to be formatted according to output_format
    return data
```

### Using Individual Decorators

```python
@app.command("get")
@command_error_handler
@config_loader
@context_handler
def get_object(
    panflow_config: PANFlowConfig,
    context_kwargs: Dict[str, str],
    object_type: str,
    name: str,
):
    # Implementation
    return data
```

### Using the CommandBase Class Directly

```python
@app.command("add")
def add_object(
    config: str = ConfigOptions.config_file(),
    # Other parameters
):
    cmd = CommandBase()
    
    try:
        # Load the configuration
        panflow_config = cmd.load_config(config, device_type, version)
        
        # Rest of implementation
        
        # Format output
        cmd.format_output(result, output_format, output_file)
        
    except Exception as e:
        # Handle the error
        cmd.handle_error(e, "add_object")
```

## Migration Guide

To migrate existing command implementations to the new pattern:

1. Import the necessary components from command_base:
   ```python
   from ..command_base import (
       CommandBase, command_error_handler, config_loader, 
       context_handler, output_formatter, standard_command,
       OutputFormat
   )
   ```

2. Apply the standard_command decorator or individual decorators to your command function

3. Update parameter types to include the injected parameters (panflow_config, context_kwargs)

4. Return your data for automatic formatting or handle formatting manually using CommandBase.format_output()

5. Remove try/except blocks and manual error handling as the decorators will handle this

## Benefits

The command pattern abstraction provides several benefits:

1. **Reduced duplication**: Common code patterns are abstracted into reusable components
2. **Improved consistency**: Commands handle errors and format output consistently
3. **Better maintainability**: Changes to error handling or output formatting can be made in one place
4. **Simplified command implementation**: Command functions can focus on core logic rather than boilerplate
5. **Enhanced user experience**: Consistent error messages and output formats
6. **Typed parameter injection**: Clear type annotations for injected parameters