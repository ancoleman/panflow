# PanFlow CLI Policy Rename Examples

This document provides examples of using the PanFlow CLI to rename security policies in bulk using the newly implemented rename operation with various modes.

## Policy Rename Operations

The rename operation supports four different modes:
- `replace`: Directly replace the policy name with a new name
- `prefix`: Add a prefix to the existing policy name  
- `suffix`: Add a suffix to the existing policy name
- `regex`: Use regular expression pattern matching to rename policies

### Example 1: Direct Replacement (replace mode)

Rename all security policies matching a specific pattern:

```bash
python cli.py policy update --query "name contains 'Old-Policy'" --operation rename --params '{"mode": "replace", "name": "New-Policy-Name"}'
```

Rename a specific security policy by exact name match:

```bash
python cli.py policy update --query "name = 'Old-Policy-Name'" --operation rename --params '{"mode": "replace", "name": "New-Policy-Name"}'
```

### Example 2: Adding a Prefix (prefix mode)

Add a prefix to all security policies in the DMZ zone:

```bash
python cli.py policy update --query "from-zone contains 'DMZ'" --operation rename --params '{"mode": "prefix", "prefix": "DMZ-"}'
```

Add a prefix to all policies that have a specific tag:

```bash
python cli.py policy update --query "tag = 'compliance'" --operation rename --params '{"mode": "prefix", "prefix": "COMP-"}'
```

### Example 3: Adding a Suffix (suffix mode)

Add a suffix to all security policies in the Trust zone:

```bash
python cli.py policy update --query "to-zone contains 'Trust'" --operation rename --params '{"mode": "suffix", "suffix": "-Internal"}'
```

Add a suffix to all policies created before a certain date:

```bash
python cli.py policy update --query "created < '2023-01-01'" --operation rename --params '{"mode": "suffix", "suffix": "-Legacy"}'
```

### Example 4: Regular Expression Renaming (regex mode)

Replace spaces with hyphens in policy names:

```bash
python cli.py policy update --query "name contains ' '" --operation rename --params '{"mode": "regex", "pattern": " ", "replacement": "-"}'
```

Change policy name format from "ABC-123" to "Policy-ABC-123":

```bash
python cli.py policy update --query "name matches '^[A-Z]+-[0-9]+$'" --operation rename --params '{"mode": "regex", "pattern": "^([A-Z]+-[0-9]+)$", "replacement": "Policy-\\\\1"}'
```

Remove specific prefixes from policy names:

```bash
python cli.py policy update --query "name contains 'OLD-'" --operation rename --params '{"mode": "regex", "pattern": "^OLD-", "replacement": ""}'
```

### Example 5: Combined Operations

Rename policies and update other attributes in a single command:

```bash
# First rename policies with the prefix "TEST-", then enable them
python cli.py policy update --query "name contains 'Development'" --operation rename --params '{"mode": "prefix", "prefix": "TEST-"}' --operation enable
```

```bash
# Rename policies and add a tag in one command
python cli.py policy update --query "to-zone = 'DMZ'" --operation rename --params '{"mode": "suffix", "suffix": "-DMZ"}' --operation add-tag --params '{"tags": ["dmz-traffic"]}'
```

## Using the Policy Rename in Workflows

### Example Workflow: Policy Standardization

```bash
# Step 1: Find all non-standard policy names
python cli.py policy list --query "name matches '^(?!STD-).*$'"

# Step 2: Add standard prefix to all policies
python cli.py policy update --query "name matches '^(?!STD-).*$'" --operation rename --params '{"mode": "prefix", "prefix": "STD-"}'

# Step 3: Verify the changes
python cli.py policy list
```

### Example Workflow: Policy Migration

```bash
# Step 1: Identify policies for migration
python cli.py policy list --query "tag = 'migrate-phase1'"

# Step 2: Update policies with migration prefix
python cli.py policy update --query "tag = 'migrate-phase1'" --operation rename --params '{"mode": "prefix", "prefix": "MIGR-"}'

# Step 3: Add migration completion tag
python cli.py policy update --query "name contains 'MIGR-'" --operation add-tag --params '{"tags": ["migration-complete"]}'
```

### Example Workflow: Policy Cleanup and Standardization

```bash
# Step 1: Find policies with inconsistent naming (e.g., containing spaces or special characters)
python cli.py policy list --query "name matches '[^a-zA-Z0-9\\-_]'"

# Step 2: Standardize policy names by replacing spaces and special characters
python cli.py policy update --query "name matches '[^a-zA-Z0-9\\-_]'" --operation rename --params '{"mode": "regex", "pattern": "[^a-zA-Z0-9\\-_]", "replacement": "-"}'

# Step 3: Normalize case in policy names (e.g., make all lowercase with first word capitalized)
python cli.py policy update --query "name matches '^[a-z]'" --operation rename --params '{"mode": "regex", "pattern": "^([a-z])(.*)", "replacement": "\\\\U\\\\1\\\\L\\\\2"}'
```

## Notes and Best Practices

1. Always review the policies that will be affected before performing bulk rename operations:
   ```bash
   python cli.py policy list --query "your query here"
   ```

2. Consider using the `--dry-run` flag to preview changes before applying them:
   ```bash
   python cli.py policy update --query "name contains 'Old'" --operation rename --params '{"mode": "prefix", "prefix": "NEW-"}' --dry-run
   ```

3. Create a backup of your configuration before making bulk changes:
   ```bash
   python cli.py config export --output backup-before-rename.xml
   ```

4. When using regex mode, ensure your pattern is properly escaped, especially when using command-line shells.

5. After performing bulk renames, verify that all policies were successfully renamed and that no references were broken.