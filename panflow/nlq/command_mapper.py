"""
Command mapping module for PANFlow NLQ.

This module is responsible for mapping intents and entities to PANFlow commands.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger("panflow.nlq.command")

class CommandMapper:
    """
    Mapper for translating intents and entities to PANFlow commands.
    
    This class maps the detected intent and extracted entities to the
    appropriate PANFlow command and arguments.
    """
    
    def __init__(self):
        """Initialize the command mapper."""
        # Define intent to command mappings
        self.intent_command_map = {
            "cleanup_unused_objects": "cleanup_unused_objects",
            "cleanup_disabled_policies": "cleanup_disabled_policies",
            "list_unused_objects": "list_unused_objects",  # Using a different command for listing vs cleaning
            "list_disabled_policies": "list_disabled_policies",
            "find_duplicates": "find_duplicates",
            "help": "help",
        }
        
        # Define required parameters for each command
        self.command_required_params = {
            "cleanup_unused_objects": ["config", "object_type", "output"],  # Output required for cleanup
            "cleanup_disabled_policies": ["config", "policy_type", "output"],  # Output required for cleanup
            "list_unused_objects": ["config"],  # Only config required for listing
            "list_disabled_policies": ["config"],  # Only config required for listing
            "find_duplicates": ["config"],  # Only config required for listing
            "help": [],
        }
        
        # Define optional parameters for each command
        self.command_optional_params = {
            "cleanup_unused_objects": ["device_type", "context", "device_group", "vsys", "template", "dry_run"],
            "cleanup_disabled_policies": ["device_type", "context", "device_group", "vsys", "template", "dry_run"],
            "list_unused_objects": ["object_type", "device_type", "context", "device_group", "vsys", "template"],
            "list_disabled_policies": ["policy_type", "device_type", "context", "device_group", "vsys", "template"],
            "find_duplicates": ["object_type", "device_type", "context", "device_group", "vsys", "template"],
            "help": [],
        }
    
    def map(self, intent: str, entities: Dict[str, Any], config_file: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Map intent and entities to PANFlow command arguments.
        
        Args:
            intent: The detected intent
            entities: The extracted entities
            config_file: Path to the configuration file
            output_file: Path to save the output (optional)
            
        Returns:
            Dictionary with command and arguments
        """
        logger.info(f"Command mapper called with: intent={intent}, config_file={config_file}, output_file={output_file}, entities={entities}")
        
        # Get the command for this intent
        command = self.intent_command_map.get(intent)
        if command is None:
            raise ValueError(f"No command mapping for intent: {intent}")
        
        # Start building the command arguments
        command_args = {
            "command": command,
            "config": config_file,
        }
        
        # Only add output file if required for this command
        required_params = self.command_required_params.get(command, [])
        logger.info(f"Required params for {command}: {required_params}")
        if "output" in required_params:
            logger.info(f"Output is required for {command}, output_file is {output_file}")
            if output_file is not None:
                command_args["output"] = output_file
                logger.info(f"Setting output={output_file} in command_args")
        
        # Add required parameters
        required_params = self.command_required_params.get(command, [])
        for param in required_params:
            if param == "config" or param == "output":
                continue  # Already handled these
            
            if param in entities:
                command_args[param] = entities[param]
            else:
                # For missing required parameters, try to use sensible defaults
                if param == "object_type" and "object_type" not in entities:
                    command_args["object_type"] = "address"
                elif param == "policy_type" and "policy_type" not in entities:
                    command_args["policy_type"] = "security_rules"
                else:
                    logger.warning(f"Missing required parameter: {param}")
                    raise ValueError(f"Missing required parameter: {param}")
        
        # Add optional parameters if they exist in entities
        optional_params = self.command_optional_params.get(command, [])
        for param in optional_params:
            if param == "output":
                continue  # Skip output - already handled
                
            if param in entities and entities[param] is not None:
                command_args[param] = entities[param]
        
        # Special handling for commands
        # For cleanup commands, we need output parameter and convert type params
        if command == "cleanup_unused_objects":
            # Convert object_type to object_types (list) with the right parameter name
            if "object_type" in command_args:
                object_type = command_args["object_type"]
                object_types = [object_type] if isinstance(object_type, str) else object_type
                command_args["object_types"] = object_types
                del command_args["object_type"]
                
            # Make sure output is set - it's required for cleanup operations
            # Check if output is None or not in command_args
            if "output" not in command_args or command_args["output"] is None:
                if output_file is not None:
                    command_args["output"] = output_file
                else:
                    # If we're doing a cleanup but no output file is provided, convert to a "list" operation
                    logger.info("No output file provided for cleanup operation, converting to list-only operation")
                    command_args["command"] = "list_unused_objects"
                    if "object_types" in command_args:
                        command_args["object_type"] = command_args["object_types"][0]
                        del command_args["object_types"]
                
        elif command == "cleanup_disabled_policies":
            # Convert policy_type to policy_types (list) with the right parameter name
            if "policy_type" in command_args:
                policy_type = command_args["policy_type"]
                policy_types = [policy_type] if isinstance(policy_type, str) else policy_type
                command_args["policy_types"] = policy_types
                del command_args["policy_type"]
                
            # Make sure output is set - it's required for cleanup operations
            # Check if output is None or not in command_args
            if "output" not in command_args or command_args["output"] is None:
                if output_file is not None:
                    command_args["output"] = output_file
                else:
                    # If we're doing a cleanup but no output file is provided, convert to a "list" operation
                    logger.info("No output file provided for cleanup operation, converting to list-only operation")
                    command_args["command"] = "list_disabled_policies" 
                    if "policy_types" in command_args:
                        command_args["policy_type"] = command_args["policy_types"][0]
                        del command_args["policy_types"]
                
        # For list commands, we need to handle type parameters differently
        elif command == "list_unused_objects":
            # For list commands, we just set object_type directly
            if "object_type" not in command_args:
                command_args["object_type"] = "address"  # Default
                
        elif command == "list_disabled_policies":
            # For list commands, we just set policy_type directly
            if "policy_type" not in command_args:
                command_args["policy_type"] = "security_rules"  # Default
                
        elif command == "find_duplicates":
            # For find duplicates, we just set object_type directly
            if "object_type" not in command_args:
                command_args["object_type"] = "address"  # Default
        
        return command_args