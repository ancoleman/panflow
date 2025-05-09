#!/usr/bin/env python3
"""
CLI Command Migration Script

This script helps migrate CLI commands to the new command pattern abstraction.

Usage:
    python cli_migrate.py [--all] [--file FILE] [--command COMMAND] [--validate] [--apply]

Options:
    --all               Migrate all CLI command files
    --file FILE         Migrate a specific command file
    --command COMMAND   Migrate a specific command in a file
    --validate          Validate the migration without applying it
    --apply             Apply the migration (replace the original files)
"""

import argparse
import os
import sys
import glob
import subprocess
from pathlib import Path

def migrate_command(file_path, command_name, validate=True, apply=False):
    """
    Migrate a specific command in a file.
    
    Args:
        file_path: Path to the command file
        command_name: Name of the command function
        validate: Whether to validate the migration
        apply: Whether to apply the migration
    """
    print(f"Migrating command {command_name} in {file_path}...")
    
    # Run the migration tool
    cmd = [
        "python", 
        "tools/cli_command_migrator.py", 
        "--module", file_path, 
        "--command", command_name
    ]
    
    if apply:
        cmd.extend(["--replace", "--backup"])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error migrating command {command_name}:")
            print(result.stderr)
            return False
        
        print(f"Command {command_name} migrated successfully.")
        
        if validate:
            # Run tests for the command
            print(f"Validating command {command_name}...")
            # TODO: Implement command-specific validation
        
        return True
    
    except Exception as e:
        print(f"Error running migration tool: {str(e)}")
        return False

def migrate_file(file_path, validate=True, apply=False):
    """
    Migrate all commands in a file.
    
    Args:
        file_path: Path to the command file
        validate: Whether to validate the migration
        apply: Whether to apply the migration
    """
    print(f"Migrating commands in {file_path}...")
    
    # Extract command names from the file
    try:
        import re
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all command functions
        cmd_pattern = r'@\w+_app\.command\([\'"](.+?)[\'"]\)\s+def\s+(\w+)'
        commands = re.findall(cmd_pattern, content)
        
        if not commands:
            print(f"No commands found in {file_path}")
            return False
        
        print(f"Found {len(commands)} commands in {file_path}:")
        for cmd_name, func_name in commands:
            print(f"  - {cmd_name} ({func_name})")
        
        # Migrate each command
        success_count = 0
        for _, func_name in commands:
            if migrate_command(file_path, func_name, validate, apply):
                success_count += 1
        
        print(f"Migrated {success_count}/{len(commands)} commands in {file_path}")
        return success_count > 0
    
    except Exception as e:
        print(f"Error migrating file {file_path}: {str(e)}")
        return False

def migrate_all(validate=True, apply=False):
    """
    Migrate all CLI command files.
    
    Args:
        validate: Whether to validate the migration
        apply: Whether to apply the migration
    """
    print("Migrating all CLI command files...")
    
    # Find all command files
    cmd_files = glob.glob("panflow/cli/commands/*_commands.py")
    
    if not cmd_files:
        print("No command files found")
        return False
    
    print(f"Found {len(cmd_files)} command files:")
    for file_path in cmd_files:
        print(f"  - {file_path}")
    
    # Migrate each file
    success_count = 0
    for file_path in cmd_files:
        if migrate_file(file_path, validate, apply):
            success_count += 1
    
    print(f"Migrated {success_count}/{len(cmd_files)} command files")
    return success_count > 0

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Migrate CLI commands to the new command pattern")
    
    # Command selection options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Migrate all CLI command files")
    group.add_argument("--file", help="Migrate a specific command file")
    group.add_argument("--command", nargs=2, metavar=("FILE", "COMMAND"), help="Migrate a specific command in a file")
    
    # Migration options
    parser.add_argument("--validate", action="store_true", help="Validate the migration without applying it")
    parser.add_argument("--apply", action="store_true", help="Apply the migration (replace the original files)")
    
    args = parser.parse_args()
    
    # Run the migration
    if args.all:
        migrate_all(args.validate, args.apply)
    elif args.file:
        migrate_file(args.file, args.validate, args.apply)
    elif args.command:
        migrate_command(args.command[0], args.command[1], args.validate, args.apply)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())