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
            "cleanup_duplicate_objects": "deduplicate_objects",
            "cleanup_disabled_policies": "cleanup_disabled_policies",
            "list_unused_objects": "list_unused_objects",  # Using a different command for listing vs cleaning
            "list_disabled_policies": "list_disabled_policies",
            "list_objects": "list_objects",
            "list_policies": "list_policies",
            "find_duplicates": "find_duplicates",
            "bulk_update_policies": "bulk_update_policies",
            "help": "help",
        }

        # Define required parameters for each command
        self.command_required_params = {
            "cleanup_unused_objects": [
                "config",
                "object_type",
                "output",
            ],  # Output required for cleanup
            "deduplicate_objects": [
                "config",
                "object_type",
                "output",
            ],  # Output required for deduplication
            "cleanup_disabled_policies": [
                "config",
                "policy_type",
                "output",
            ],  # Output required for cleanup
            "list_unused_objects": ["config"],  # Only config required for listing
            "list_disabled_policies": ["config"],  # Only config required for listing
            "list_objects": ["config"],  # Only config required for listing objects
            "list_policies": ["config"],  # Only config required for listing policies
            "find_duplicates": ["config"],  # Only config required for listing
            "bulk_update_policies": ["config", "output", "operation", "value"],  # Need config, output, operation, and value for bulk updates
            "help": [],
        }

        # Define optional parameters for each command
        self.command_optional_params = {
            "cleanup_unused_objects": [
                "device_type",
                "context",
                "device_group",
                "vsys",
                "template",
                "dry_run",
            ],
            "deduplicate_objects": [
                "device_type",
                "context",
                "device_group",
                "vsys",
                "template",
                "dry_run",
            ],
            "cleanup_disabled_policies": [
                "device_type",
                "context",
                "device_group",
                "vsys",
                "template",
                "dry_run",
            ],
            "list_unused_objects": [
                "object_type",
                "device_type",
                "context",
                "device_group",
                "vsys",
                "template",
            ],
            "list_disabled_policies": [
                "policy_type",
                "device_type",
                "context",
                "device_group",
                "vsys",
                "template",
            ],
            "list_objects": [
                "object_type",
                "device_type",
                "context",
                "device_group",
                "vsys",
                "template",
            ],
            "list_policies": [
                "policy_type",
                "device_type",
                "context",
                "device_group",
                "vsys",
                "template",
            ],
            "find_duplicates": [
                "object_type",
                "device_type",
                "context",
                "device_group",
                "vsys",
                "template",
            ],
            "bulk_update_policies": [
                "policy_type",
                "device_type",
                "context",
                "device_group",
                "vsys",
                "template",
                "criteria",
                "dry_run",
            ],
            "help": [],
        }

    def map(
        self,
        intent: str,
        entities: Dict[str, Any],
        config_file: str,
        output_file: Optional[str] = None,
    ) -> Dict[str, Any]:
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
        logger.info(
            f"Command mapper called with: intent={intent}, config_file={config_file}, output_file={output_file}, entities={entities}"
        )

        # Get the command for this intent
        command = self.intent_command_map.get(intent)
        if command is None:
            raise ValueError(f"No command mapping for intent: {intent}")

        # Special case handling for queries about unused objects
        if intent == "list_objects" and "original_query" in entities:
            query = entities.get("original_query", "").lower()
            if "unused" in query and "object" in query:
                logger.info(f"Query contains 'unused objects', converting intent from {intent} to list_unused_objects")
                command = "list_unused_objects"
                intent = "list_unused_objects"
        
        # Start building the command arguments
        command_args = {
            "command": command,
            "config": config_file,
        }

        # Pass through the original query for context extraction
        if "original_query" in entities:
            command_args["original_query"] = entities["original_query"]

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
                    # Initialize config to check device type if needed
                    from panflow import PANFlowConfig

                    if "device_type" not in entities:
                        xml_config = PANFlowConfig(config_file=config_file)
                        device_type = xml_config.device_type.lower()
                    else:
                        device_type = entities["device_type"].lower()

                    # Set appropriate default policy type based on device type
                    if device_type == "panorama":
                        command_args["policy_type"] = "security_pre_rules"
                    else:
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

        # Special handling for show_duplicates flag
        if "show_duplicates" in entities and entities["show_duplicates"]:
            # Pass through the show_duplicates flag
            command_args["show_duplicates"] = entities["show_duplicates"]

            # If this is a regular list_objects command but show_duplicates is true,
            # consider if we should remap it to find_duplicates
            if command == "list_objects" and entities.get("show_duplicates"):
                logger.info(
                    "Detected request for duplicated objects, passing through show_duplicates flag"
                )
                # Just keep the list_objects command but with the show_duplicates flag

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
                    logger.info(
                        "No output file provided for cleanup operation, converting to list-only operation"
                    )
                    command_args["command"] = "list_unused_objects"
                    if "object_types" in command_args:
                        command_args["object_type"] = command_args["object_types"][0]
                        del command_args["object_types"]

        # For deduplication commands, set up the parameters properly
        elif command == "deduplicate_objects":
            # Make sure output is set - it's required for deduplication operations
            if "output" not in command_args or command_args["output"] is None:
                if output_file is not None:
                    command_args["output"] = output_file
                else:
                    # If we're doing deduplication but no output file is provided, convert to a "find duplicates" operation
                    logger.info(
                        "No output file provided for deduplication operation, converting to find-only operation"
                    )
                    command_args["command"] = "find_duplicates"
                    # Make sure show_duplicates flag is set for proper display
                    command_args["show_duplicates"] = True

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
                    logger.info(
                        "No output file provided for cleanup operation, converting to list-only operation"
                    )
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
                # Check if entities has policy_type set to "all"
                if entities.get("policy_type") == "all":
                    command_args["policy_type"] = "all"
                else:
                    # Initialize config to check device type if needed
                    from panflow import PANFlowConfig

                    if "device_type" not in command_args:
                        xml_config = PANFlowConfig(config_file=config_file)
                        device_type = xml_config.device_type.lower()
                    else:
                        device_type = command_args["device_type"].lower()

                    # Set appropriate default policy type based on device type
                    if device_type == "panorama":
                        command_args["policy_type"] = "security_pre_rules"
                    else:
                        command_args["policy_type"] = "security_rules"

        elif command == "find_duplicates":
            # For find duplicates, we just set object_type directly
            if "object_type" not in command_args:
                # Default to address unless this is an explicit "all objects" request
                if entities.get("original_query", "").lower().find("all object") >= 0:
                    command_args["object_type"] = "all"
                else:
                    command_args["object_type"] = "address"  # Default

        elif command == "bulk_update_policies":
            # Extract operation type and value from the query
            query = entities.get("original_query", "").lower()

            # Make sure we have a valid output file for bulk operations
            if "output" not in command_args or command_args["output"] is None:
                if output_file is not None:
                    command_args["output"] = output_file
                else:
                    # If we're doing a bulk update but no output file is provided, convert to a list operation
                    logger.info("No output file provided for bulk update operation, converting to list-only operation")
                    command_args["command"] = "list_policies"
                    if "policy_type" not in command_args:
                        # Initialize config to check device type if needed
                        from panflow import PANFlowConfig

                        if "device_type" not in entities:
                            xml_config = PANFlowConfig(config_file=config_file)
                            device_type = xml_config.device_type.lower()
                        else:
                            device_type = entities["device_type"].lower()

                        # Set appropriate default policy type based on device type
                        if device_type == "panorama":
                            command_args["policy_type"] = "security_pre_rules"
                        else:
                            command_args["policy_type"] = "security_rules"
                    return command_args

            # Check if the entity extractor already determined the operation
            if "operation" in entities and entities["operation"] in ["enable_logging", "disable_logging", "add_tag", "set_action", "enable", "disable"]:
                logger.info(f"Using operation from entity extractor: {entities['operation']}")
                command_args["operation"] = entities["operation"]
                if "value" in entities:
                    command_args["value"] = entities["value"]
                else:
                    command_args["value"] = "yes"  # Default value
            else:
                # Determine operation type from query if not already set by entity extractor
                if ("log" in query or "logging" in query) and any(word in query for word in ["enable", "set", "add", "turn on", "activate"]):
                    command_args["operation"] = "enable_logging"
                    command_args["value"] = "yes"
                    logger.info("Detected enable_logging operation from query")
                elif ("log" in query or "logging" in query) and any(word in query for word in ["disable", "remove", "turn off", "deactivate"]):
                    command_args["operation"] = "disable_logging"
                    command_args["value"] = "yes"
                    logger.info("Detected disable_logging operation from query")
                elif ("tag" in query) and any(word in query for word in ["add", "set", "apply"]):
                    command_args["operation"] = "add_tag"
                    # Extract tag value from entities or from the query
                    if "tag_value" in entities:
                        command_args["value"] = entities["tag_value"]
                    else:
                        # Try to extract from query using regex
                        import re
                        tag_match = re.search(r"tag\s+['\"]?([^'\"]+)['\"]?", query)
                        if tag_match:
                            command_args["value"] = tag_match.group(1)
                        else:
                            # Default tag value
                            command_args["value"] = "updated-by-nlq"
                elif "action" in query and any(word in query for word in ["set", "change", "update"]):
                    command_args["operation"] = "set_action"
                    # Extract action value
                    if "action_value" in entities:
                        command_args["value"] = entities["action_value"]
                    else:
                        # Try to determine action from query
                        if "allow" in query or "accept" in query:
                            command_args["value"] = "allow"
                        elif "deny" in query or "drop" in query or "block" in query:
                            command_args["value"] = "deny"
                        else:
                            # Default
                            command_args["value"] = "allow"
                elif (("enable" in query or "enabling" in query) and
                    not ("disable" in query or "disabling" in query)):
                    command_args["operation"] = "enable"
                    command_args["value"] = "yes"
                elif "disable" in query or "disabling" in query:
                    command_args["operation"] = "disable"
                    command_args["value"] = "yes"
                else:
                    # Default to enable/disable operation
                    if "disable" in query:
                        command_args["operation"] = "disable"
                        command_args["value"] = "yes"
                    else:
                        command_args["operation"] = "enable"
                        command_args["value"] = "yes"

            logger.info(f"Final operation determined: {command_args.get('operation')}, value: {command_args.get('value')}")

            # Set policy type if not already set
            if "policy_type" not in command_args:
                from panflow import PANFlowConfig

                # Determine device type
                if "device_type" not in entities:
                    xml_config = PANFlowConfig(config_file=config_file)
                    device_type = xml_config.device_type.lower()
                else:
                    device_type = entities["device_type"].lower()

                # Extract policy type from query
                if "security" in query and "pre" in query:
                    command_args["policy_type"] = "security_pre_rules" if device_type == "panorama" else "security_rules"
                elif "security" in query and "post" in query:
                    command_args["policy_type"] = "security_post_rules" if device_type == "panorama" else "security_rules"
                elif "nat" in query and "pre" in query:
                    command_args["policy_type"] = "nat_pre_rules" if device_type == "panorama" else "nat_rules"
                elif "nat" in query and "post" in query:
                    command_args["policy_type"] = "nat_post_rules" if device_type == "panorama" else "nat_rules"
                elif "nat" in query:
                    command_args["policy_type"] = "nat_pre_rules" if device_type == "panorama" else "nat_rules"
                elif "all" in query:
                    command_args["policy_type"] = "all"
                elif "security" in query and device_type == "panorama":
                    # Default to pre rules for security policies on Panorama
                    command_args["policy_type"] = "security_pre_rules"
                else:
                    # Default to security rules
                    command_args["policy_type"] = "security_pre_rules" if device_type == "panorama" else "security_rules"

            # Default to dry_run if not specified
            if "dry_run" not in command_args:
                command_args["dry_run"] = False

        return command_args
