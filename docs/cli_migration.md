# PAN-OS CLI Migration Guide

## Overview

PANFlow currently provides two CLI entry points:

1. **panflow_cli.py** - The new, package-based CLI tool that will be the primary interface going forward
2. **cli.py** - The legacy CLI tool that contains some functionality not yet migrated to the package-based CLI

This document explains the migration plan and how to work with both tools during the transition period.

## Current Status

`panflow_cli.py` is the recommended CLI entry point for all operations. All functionality from `cli.py` has been migrated to the package-based CLI, including all merge operations.

## Using the CLI Tools

For new development and most operations, use `panflow_cli.py`:

```bash
python panflow_cli.py [command] [options]
```

For operations not yet available in `panflow_cli.py`, you can still use `cli.py`:

```bash
python cli.py [command] [options]
```

## Migration Plan

The goal is to migrate all functionality from `cli.py` to the package-based CLI accessed via `panflow_cli.py`. The migration process involves:

1. Identifying commands and options available in `cli.py` but not in `panflow_cli.py`
2. Moving the implementation to the appropriate package modules
3. Adding the commands to the package-based CLI

## Command Availability

| Command | panflow_cli.py | cli.py |
|---------|---------------|--------|
| object | list, add, update, delete, filter | list, add, update, delete, filter |
| policy | list | list |
| group | add-member | add-member |
| report | unused-objects | unused-objects |
| config | validate | validate |
| merge | policy, policies, all, object, objects, all-objects | policy, policies, all, object, objects, all-objects |
| query | execute, interactive, verify, example | execute, verify, example |
| deduplicate | objects | objects |

## Feature Differences

1. **Query Command**:
   - `panflow_cli.py` includes an `interactive` mode not available in `cli.py`
   
2. **Merge Command**:
   - Both CLIs now provide the same merge operations

## Reporting Issues

If you encounter functionality that's available in `cli.py` but missing from `panflow_cli.py`, please report it so it can be prioritized for migration.

## Timeline

All critical functionality has been migrated to the package-based CLI. The `cli.py` file will be removed in a future release after ensuring all users have transitioned to using `panflow_cli.py`. During this final transition period, both CLI tools will be maintained to ensure backward compatibility, but no new features will be added to `cli.py`.