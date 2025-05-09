#!/usr/bin/env python3
"""
CLI Command Migrator

This script analyzes existing CLI commands and generates migrated versions
that use the new command pattern abstraction.

Usage:
    python cli_command_migrator.py --module path/to/commands_file.py --command command_name

Options:
    --module    Path to the module containing the command to migrate
    --command   Name of the command function to migrate
    --backup    Create a backup of the original file (default: True)
    --replace   Replace the command in the file (default: False)
    --output    Output path for the migrated command (default: None)
"""

import argparse
import ast
import inspect
import os
import re
import sys
import typing
from pathlib import Path
import astor

# Add the project root to the path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class CommandVisitor(ast.NodeVisitor):
    """AST visitor to analyze CLI commands."""
    
    def __init__(self, command_name):
        self.command_name = command_name
        self.command_node = None
        self.decorator_nodes = []
        self.parameters = []
        self.config_param = None
        self.device_type_param = None
        self.version_param = None
        self.context_params = {}
        self.output_params = {}
        self.try_except_blocks = []
        self.return_values = []
        self.imports = []
    
    def visit_FunctionDef(self, node):
        """Visit function definitions to find the target command."""
        if node.name == self.command_name:
            self.command_node = node
            self.decorator_nodes = node.decorator_list
            
            # Extract parameters
            for arg in node.args.args:
                if hasattr(arg, 'annotation') and arg.annotation:
                    arg_type = astor.to_source(arg.annotation).strip()
                else:
                    arg_type = 'Any'
                
                if arg.arg == 'config' or arg.arg == 'config_file':
                    self.config_param = {'name': arg.arg, 'type': arg_type}
                elif arg.arg == 'device_type':
                    self.device_type_param = {'name': arg.arg, 'type': arg_type}
                elif arg.arg == 'version':
                    self.version_param = {'name': arg.arg, 'type': arg_type}
                elif arg.arg in ['context', 'context_type']:
                    self.context_params['context'] = {'name': arg.arg, 'type': arg_type}
                elif arg.arg in ['device_group']:
                    self.context_params['device_group'] = {'name': arg.arg, 'type': arg_type}
                elif arg.arg in ['vsys']:
                    self.context_params['vsys'] = {'name': arg.arg, 'type': arg_type}
                elif arg.arg in ['template']:
                    self.context_params['template'] = {'name': arg.arg, 'type': arg_type}
                elif arg.arg in ['output_format', 'format']:
                    self.output_params['format'] = {'name': arg.arg, 'type': arg_type}
                elif arg.arg in ['output_file', 'output']:
                    self.output_params['file'] = {'name': arg.arg, 'type': arg_type}
                
                self.parameters.append({
                    'name': arg.arg,
                    'type': arg_type,
                    'default': None  # Default will be handled separately
                })
            
            # Extract default values
            if node.args.defaults:
                non_default_count = len(node.args.args) - len(node.args.defaults)
                for i, default in enumerate(node.args.defaults):
                    param_index = non_default_count + i
                    if param_index < len(self.parameters):
                        self.parameters[param_index]['default'] = astor.to_source(default).strip()
            
            # Visit the function body
            self.generic_visit(node)
    
    def visit_Try(self, node):
        """Extract try/except blocks."""
        self.try_except_blocks.append(node)
        self.generic_visit(node)
    
    def visit_Return(self, node):
        """Extract return statements."""
        self.return_values.append(node)
        self.generic_visit(node)
    
    def visit_Import(self, node):
        """Extract import statements."""
        self.imports.extend(node.names)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Extract from import statements."""
        for name in node.names:
            self.imports.append({
                'module': node.module,
                'name': name.name,
                'asname': name.asname
            })
        self.generic_visit(node)

def analyze_command(module_path, command_name):
    """
    Analyze a CLI command to determine its structure.
    
    Args:
        module_path: Path to the module containing the command
        command_name: Name of the command function
        
    Returns:
        CommandVisitor instance with analysis results
    """
    with open(module_path, 'r', encoding='utf-8') as f:
        module_content = f.read()
    
    module_ast = ast.parse(module_content)
    visitor = CommandVisitor(command_name)
    visitor.visit(module_ast)
    
    return visitor

def determine_migration_strategy(analysis):
    """
    Determine the best migration strategy for the command.
    
    Args:
        analysis: CommandVisitor instance with analysis results
        
    Returns:
        dict with strategy information
    """
    # Check for key parameters
    has_config = analysis.config_param is not None
    has_context = 'context' in analysis.context_params
    has_try_except = len(analysis.try_except_blocks) > 0
    has_output_format = 'format' in analysis.output_params
    
    # Determine the most appropriate decorator
    if has_config and has_context and has_try_except and has_output_format:
        strategy = 'standard_command'
    elif has_config and has_try_except:
        strategy = 'combined_decorators'
    else:
        strategy = 'command_base'
    
    return {
        'strategy': strategy,
        'needs_config_loader': has_config,
        'needs_context_handler': has_context,
        'needs_error_handler': has_try_except,
        'needs_output_formatter': has_output_format
    }

def generate_migrated_command(analysis, strategy):
    """
    Generate a migrated version of the command.
    
    Args:
        analysis: CommandVisitor instance with analysis results
        strategy: Migration strategy dict
        
    Returns:
        string containing the migrated command code
    """
    command_name = analysis.command_name
    docstring = None
    if analysis.command_node.body and isinstance(analysis.command_node.body[0], ast.Expr) and isinstance(analysis.command_node.body[0].value, ast.Str):
        docstring = analysis.command_node.body[0].value.s
    
    # Start with imports
    imports = [
        "from typing import Dict, Any, Optional, List",
        "from panflow import PANFlowConfig"
    ]
    
    if strategy['strategy'] == 'standard_command':
        imports.append("from ..command_base import standard_command, OutputFormat")
    elif strategy['strategy'] == 'combined_decorators':
        imports.append("from ..command_base import (command_error_handler, config_loader, context_handler, output_formatter, OutputFormat)")
    else:
        imports.append("from ..command_base import CommandBase, OutputFormat")
    
    # Generate function signature
    if strategy['strategy'] == 'standard_command':
        # For standard_command, use injected parameters
        signature = [
            "@standard_command",
            f"def {command_name}(",
            "    panflow_config: PANFlowConfig,",
            "    context_kwargs: Dict[str, str],"
        ]
        
        # Add parameters excluding the ones handled by decorators
        for param in analysis.parameters:
            param_name = param['name']
            if param_name in ['config', 'config_file', 'device_type', 'version', 
                             'context', 'context_type', 'device_group', 'vsys', 'template']:
                continue
                
            # Update output format type if present
            if param_name in ['output_format', 'format']:
                param_type = "OutputFormat"
                param_default = param.get('default', 'None')
                if param_default == '"json"' or param_default == "'json'":
                    param_default = "OutputFormat.JSON"
                elif param_default == '"table"' or param_default == "'table'":
                    param_default = "OutputFormat.TABLE"
                elif param_default == '"csv"' or param_default == "'csv'":
                    param_default = "OutputFormat.CSV"
                elif param_default == '"yaml"' or param_default == "'yaml'":
                    param_default = "OutputFormat.YAML"
                elif param_default == '"text"' or param_default == "'text'":
                    param_default = "OutputFormat.TEXT"
                elif param_default == '"html"' or param_default == "'html'":
                    param_default = "OutputFormat.HTML"
                
                signature.append(f"    {param_name}: {param_type} = {param_default},")
            else:
                param_type = param['type']
                param_default = param.get('default', 'None')
                signature.append(f"    {param_name}: {param_type} = {param_default},")
                
        signature.append("):")
        
    elif strategy['strategy'] == 'combined_decorators':
        # For combined decorators, use individual decorators
        decorators = []
        if strategy['needs_error_handler']:
            decorators.append("@command_error_handler")
        if strategy['needs_config_loader']:
            decorators.append("@config_loader")
        if strategy['needs_context_handler']:
            decorators.append("@context_handler")
        if strategy['needs_output_formatter']:
            decorators.append("@output_formatter")
        
        signature = decorators + [f"def {command_name}("]
        
        # Add injected parameters
        if strategy['needs_config_loader']:
            signature.append("    panflow_config: PANFlowConfig,")
        if strategy['needs_context_handler']:
            signature.append("    context_kwargs: Dict[str, str],")
        
        # Add parameters excluding the ones handled by decorators
        for param in analysis.parameters:
            param_name = param['name']
            if (strategy['needs_config_loader'] and param_name in ['config', 'config_file', 'device_type', 'version']) or \
               (strategy['needs_context_handler'] and param_name in ['context', 'context_type', 'device_group', 'vsys', 'template']):
                continue
                
            # Update output format type if present
            if param_name in ['output_format', 'format']:
                param_type = "OutputFormat"
                param_default = param.get('default', 'None')
                if param_default == '"json"' or param_default == "'json'":
                    param_default = "OutputFormat.JSON"
                elif param_default == '"table"' or param_default == "'table'":
                    param_default = "OutputFormat.TABLE"
                elif param_default == '"csv"' or param_default == "'csv'":
                    param_default = "OutputFormat.CSV"
                elif param_default == '"yaml"' or param_default == "'yaml'":
                    param_default = "OutputFormat.YAML"
                elif param_default == '"text"' or param_default == "'text'":
                    param_default = "OutputFormat.TEXT"
                elif param_default == '"html"' or param_default == "'html'":
                    param_default = "OutputFormat.HTML"
                
                signature.append(f"    {param_name}: {param_type} = {param_default},")
            else:
                param_type = param['type']
                param_default = param.get('default', 'None')
                signature.append(f"    {param_name}: {param_type} = {param_default},")
                
        signature.append("):")
        
    else:  # CommandBase approach
        # For CommandBase, keep original signature
        signature = [f"def {command_name}("]
        
        for param in analysis.parameters:
            param_name = param['name']
            param_type = param['type']
            param_default = param.get('default', 'None')
            
            # Update output format type if present
            if param_name in ['output_format', 'format']:
                param_type = "str"  # Keep as string for compatibility
                
            signature.append(f"    {param_name}: {param_type} = {param_default},")
                
        signature.append("):")
    
    # Add docstring
    function_body = []
    if docstring:
        function_body.append(f'    """{docstring}"""')
    
    # Add function body
    if strategy['strategy'] == 'standard_command' or strategy['strategy'] == 'combined_decorators':
        # Remove boilerplate from function body
        # This is a simplified approach - a real implementation would need to parse the function body
        # Here we just provide a template for the common case
        
        # Add implementation based on original function
        if analysis.config_param:
            function_body.append("    # Use panflow_config instead of loading configuration")
        
        if 'context' in analysis.context_params:
            function_body.append("    # Use context_kwargs instead of building context dict")
        
        # Add core function logic - simplified for this example
        function_body.append("    # Core implementation")
        function_body.append("    # TODO: Migrate your implementation here")
        function_body.append("    # Remember to use panflow_config and context_kwargs instead of manually creating them")
        
        # Add return statement
        function_body.append("    # Return value for automatic formatting")
        function_body.append("    return result  # Replace with your actual result variable")
        
    else:  # CommandBase approach
        function_body.append("    cmd = CommandBase()")
        function_body.append("    ")
        function_body.append("    try:")
        function_body.append("        # Load configuration")
        if analysis.config_param:
            config_param = analysis.config_param['name']
            function_body.append(f"        panflow_config = cmd.load_config({config_param}, device_type, version)")
        
        function_body.append("        ")
        function_body.append("        # Get context parameters")
        if 'context' in analysis.context_params:
            context_param = analysis.context_params['context']['name']
            device_group_param = analysis.context_params.get('device_group', {}).get('name', 'device_group')
            vsys_param = analysis.context_params.get('vsys', {}).get('name', 'vsys')
            template_param = analysis.context_params.get('template', {}).get('name', 'template')
            function_body.append(f"        context_kwargs = cmd.get_context_params({context_param}, {device_group_param}, {vsys_param}, {template_param})")
        
        function_body.append("        ")
        function_body.append("        # Core implementation")
        function_body.append("        # TODO: Migrate your implementation here")
        
        function_body.append("        ")
        function_body.append("        # Format output")
        if 'format' in analysis.output_params:
            format_param = analysis.output_params['format']['name']
            file_param = analysis.output_params.get('file', {}).get('name', 'output_file')
            function_body.append(f"        cmd.format_output(result, {format_param}, {file_param})")
        else:
            function_body.append("        cmd.format_output(result)")
        
        function_body.append("        ")
        function_body.append("    except Exception as e:")
        function_body.append(f"        cmd.handle_error(e, \"{command_name}\")")
    
    # Combine everything
    migrated_command = "\n".join(imports) + "\n\n" + "\n".join(signature) + "\n" + "\n".join(function_body)
    
    return migrated_command

def replace_command_in_file(module_path, command_name, migrated_code, create_backup=True):
    """
    Replace a command in a file with the migrated version.
    
    Args:
        module_path: Path to the module file
        command_name: Name of the command to replace
        migrated_code: New code for the command
        create_backup: Whether to create a backup of the original file
        
    Returns:
        bool indicating success
    """
    with open(module_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create backup if requested
    if create_backup:
        backup_path = f"{module_path}.bak"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Backup created at {backup_path}")
    
    # Find the command
    function_pattern = r"(?:@[\w\.]+\s*\n)*def\s+{}\s*\([^)]*\):.*?(?=\n\S|\Z)".format(command_name)
    function_match = re.search(function_pattern, content, re.DOTALL)
    
    if not function_match:
        print(f"Could not find command {command_name} in {module_path}")
        return False
    
    # Replace the command
    new_content = content[:function_match.start()] + migrated_code + content[function_match.end():]
    
    with open(module_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"Command {command_name} replaced in {module_path}")
    return True

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Migrate CLI commands to the new command pattern")
    parser.add_argument("--module", required=True, help="Path to the module containing the command")
    parser.add_argument("--command", required=True, help="Name of the command function to migrate")
    parser.add_argument("--backup", action="store_true", default=True, help="Create a backup of the original file")
    parser.add_argument("--replace", action="store_true", help="Replace the command in the file")
    parser.add_argument("--output", help="Output path for the migrated command")
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_arguments()
    
    # Check if the module file exists
    if not os.path.isfile(args.module):
        print(f"Module file {args.module} not found")
        return 1
    
    # Analyze the command
    print(f"Analyzing command {args.command} in {args.module}...")
    analysis = analyze_command(args.module, args.command)
    
    if analysis.command_node is None:
        print(f"Command {args.command} not found in {args.module}")
        return 1
    
    # Determine migration strategy
    print("Determining migration strategy...")
    strategy = determine_migration_strategy(analysis)
    print(f"Migration strategy: {strategy['strategy']}")
    
    # Generate migrated command
    print("Generating migrated command...")
    migrated_code = generate_migrated_command(analysis, strategy)
    
    # Output migrated command
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(migrated_code)
        print(f"Migrated command written to {args.output}")
    elif args.replace:
        replace_command_in_file(args.module, args.command, migrated_code, args.backup)
    else:
        print("\nMigrated command:")
        print("-----------------")
        print(migrated_code)
        print("-----------------")
        print("To replace the command, use --replace or specify an output file with --output")
    
    print("Migration complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())