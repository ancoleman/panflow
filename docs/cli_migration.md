# PAN-OS CLI Guide

## Overview

PANFlow provides a single unified CLI entry point:

1. **cli.py** - The consolidated CLI tool for all PANFlow functionality

This document explains the CLI commands and functionality available in PANFlow.

## Using the CLI

Use `cli.py` for all operations:

```bash
python cli.py [command] [options]
```

## Command Availability

| Command | Available Operations |
|---------|---------------------|
| object | list, add, update, delete, filter, find, find-duplicates, bulk-delete |
| policy | list, add, update, delete, filter, bulk-update |
| group | add-member, remove-member, add-members-file |
| report | unused-objects, duplicate-objects, security-rule-coverage, reference-check |
| config | validate |
| merge | policy, policies, all, object, objects, all-objects |
| query | execute, interactive, verify, example |
| deduplicate | objects |

## Feature Highlights

1. **Query Command**:
   - The `interactive` mode provides a REPL-like environment for exploring configurations
   - Powerful graph-based query language for finding and analyzing objects and policies
   
2. **Merge Commands**:
   - Sophisticated merge operations for combining configurations with conflict resolution
   - Support for deep object reference copying

3. **Deduplication**:
   - Intelligent object deduplication with customizable strategies
   - Safe handling of object references during deduplication

## Additional Information

For detailed command usage and examples, see the [CLI_USAGE.md](../CLI_USAGE.md) file in the root directory.

For query language syntax and examples, see the [query_examples.md](query_examples.md) document.