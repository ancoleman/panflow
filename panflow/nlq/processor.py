"""
Core NLQ processing module for PANFlow.

This module handles the main processing of natural language queries,
including intent detection, entity extraction, and command mapping.
"""

import os
import re
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path

from .intent_parser import IntentParser
from .entity_extractor import EntityExtractor
from .command_mapper import CommandMapper

logger = logging.getLogger("panflow.nlq")


class NLQProcessor:
    """
    Natural Language Query processor for PANFlow.

    This class processes natural language queries and translates them
    to PANFlow commands. It can use either:
    - AI-powered processing (if available and configured)
    - Pattern-based processing (as a fallback)
    """

    def __init__(self, use_ai: bool = True):
        """
        Initialize the NLQ processor.

        Args:
            use_ai: Whether to attempt to use AI for processing (will fall back to pattern-based if AI is unavailable)
        """
        # Initialize standard pattern-based components
        self.intent_parser = IntentParser()
        self.entity_extractor = EntityExtractor()
        self.command_mapper = CommandMapper()

        # Initialize AI processor if enabled
        self.use_ai = use_ai
        self.ai_processor = None

        if use_ai:
            try:
                from .ai_processor import AIProcessor

                # Check for API keys in environment
                api_key = None
                provider = os.environ.get("PANFLOW_AI_PROVIDER", "openai").lower()
                model = os.environ.get(
                    "PANFLOW_AI_MODEL",
                    "gpt-3.5-turbo" if provider == "openai" else "claude-3-haiku-20240307",
                )

                # Try to find API key based on provider
                if provider == "openai":
                    api_key = os.environ.get("OPENAI_API_KEY")
                elif provider == "anthropic":
                    api_key = os.environ.get("ANTHROPIC_API_KEY")

                # Initialize the AI processor
                self.ai_processor = AIProcessor(
                    api_key=api_key, model=model, provider=provider, use_local_fallback=True
                )

                # Log AI availability
                if self.ai_processor.available():
                    logger.info(f"AI processing enabled using {provider} ({model})")
                else:
                    logger.info(
                        f"AI processing not available, falling back to pattern-based processing"
                    )
            except ImportError as e:
                logger.warning(f"Could not import AI processor: {e}")
            except Exception as e:
                logger.error(f"Error initializing AI processor: {e}", exc_info=True)

    def ai_available(self) -> bool:
        """
        Check if AI processing is available.

        Returns:
            True if AI processing is available, False otherwise
        """
        return self.use_ai and self.ai_processor is not None and self.ai_processor.available()

    def process(
        self, query: str, config_file: str, output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language query.

        Args:
            query: The natural language query to process
            config_file: Path to the configuration file
            output_file: Path to save the output (optional, and only needed for cleanup operations)

        Returns:
            Dictionary with results of the command execution
        """
        logger.info(f"Processing query: {query}")

        # Determine if this is a view-only query (as opposed to a cleanup/modification query)
        is_view_query = any(
            keyword in query.lower()
            for keyword in ["show", "list", "display", "find", "get", "what"]
        )

        # Try AI processing first if available
        if self.ai_available():
            try:
                ai_result = self.ai_processor.process_query(query)
                intent = ai_result.get("intent")
                entities = ai_result.get("entities", {})
                confidence = ai_result.get("confidence", 0.0)

                logger.debug(
                    f"AI processing result: intent={intent}, confidence={confidence:.2f}, entities={entities}"
                )

                # If this is a cleanup intent but seems to be a view query based on keywords, adjust the intent
                if intent and intent.startswith("cleanup_") and is_view_query:
                    logger.info(
                        f"Query seems to be a view operation but got cleanup intent. Adjusting intent from {intent}"
                    )
                    if intent == "cleanup_unused_objects":
                        intent = "list_unused_objects"
                    elif intent == "cleanup_disabled_policies":
                        intent = "list_disabled_policies"

                if intent and confidence >= 0.6:
                    # AI processing succeeded with good confidence
                    # Ensure entities include configuration info
                    if "config" not in entities:
                        entities["config"] = config_file
                    if output_file and "output" not in entities:
                        entities["output"] = output_file

                    # Add the original query to entities for context
                    entities["original_query"] = query

                    # Map to command arguments
                    logger.info(
                        f"Mapping intent '{intent}' to command args with config_file={config_file}, output_file={output_file}"
                    )
                    command_args = self.command_mapper.map(
                        intent, entities, config_file, output_file
                    )
                    logger.info(f"Mapped to command args: {command_args}")

                    # Execute command
                    try:
                        result = self.execute_command(command_args)
                        return {
                            "success": True,
                            "message": "Command executed successfully",
                            "intent": intent,
                            "entities": entities,
                            "command": command_args,
                            "result": result,
                            "processing": "ai",
                        }
                    except Exception as e:
                        logger.error(f"Error executing command: {e}", exc_info=True)
                        return {
                            "success": False,
                            "message": f"Error executing command: {str(e)}",
                            "intent": intent,
                            "entities": entities,
                            "command": command_args,
                            "processing": "ai",
                        }
                else:
                    logger.info(
                        f"AI processing yielded low confidence ({confidence:.2f}), falling back to pattern-based"
                    )
            except Exception as e:
                logger.error(
                    f"Error in AI processing, falling back to pattern-based: {e}", exc_info=True
                )

        # Fall back to pattern-based processing
        # Identify the intent
        intent, confidence = self.intent_parser.parse(query)
        logger.debug(f"Pattern-based intent detection: {intent} (confidence: {confidence:.2f})")

        # If this is a cleanup intent but seems to be a view query based on keywords, adjust the intent
        if intent and intent.startswith("cleanup_") and is_view_query:
            logger.info(
                f"Query seems to be a view operation but got cleanup intent. Adjusting intent from {intent}"
            )
            if intent == "cleanup_unused_objects":
                intent = "list_unused_objects"
            elif intent == "cleanup_disabled_policies":
                intent = "list_disabled_policies"

        # Extract entities
        entities = self.entity_extractor.extract(query)

        # Add the original query to entities for context
        entities["original_query"] = query

        logger.debug(f"Pattern-based entity extraction: {entities}")

        # If we couldn't determine the intent with sufficient confidence, return early
        if confidence < 0.6:
            return {
                "success": False,
                "message": f"Not confident in understanding the request (confidence: {confidence:.2f})",
                "suggestions": self.get_suggestions(query),
                "intent": intent,
                "entities": entities,
                "processing": "pattern",
            }

        # Map to command arguments
        logger.info(
            f"Mapping intent '{intent}' to command args with config_file={config_file}, output_file={output_file}"
        )
        command_args = self.command_mapper.map(intent, entities, config_file, output_file)
        logger.info(f"Mapped to command args: {command_args}")

        # Execute command and return results
        try:
            result = self.execute_command(command_args)
            return {
                "success": True,
                "message": "Command executed successfully",
                "intent": intent,
                "entities": entities,
                "command": command_args,
                "result": result,
                "processing": "pattern",
            }
        except Exception as e:
            logger.error(f"Error executing command: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error executing command: {str(e)}",
                "intent": intent,
                "entities": entities,
                "command": command_args,
                "processing": "pattern",
            }

    def execute_command(self, command_args: Dict[str, Any]) -> Any:
        """
        Execute a PANFlow command based on the provided arguments.

        This method uses the appropriate PANFlow functionality to execute the command.
        For CLI commands, it will use the CLI app directly.

        Args:
            command_args: Dictionary with command arguments

        Returns:
            Result of the command execution with detailed, well-formatted information
            for different operation types (list, cleanup, etc.)
        """
        command_name = command_args.pop("command")

        # For listing objects
        if command_name == "list_objects":
            from panflow import PANFlowConfig

            # Extract parameters
            config_file = command_args.get("config")
            # Handle both "object_type" and "type" parameters
            if "object_type" in command_args:
                object_type = command_args["object_type"]
            elif "type" in command_args:
                object_type = (
                    command_args["type"][0]
                    if isinstance(command_args["type"], list)
                    else command_args["type"]
                )
            else:
                # Try to extract object type from the query string if it's available
                query = command_args.get("original_query", "")
                if "address" in query.lower():
                    object_type = "address"
                elif "service" in query.lower():
                    object_type = "service"
                elif "tag" in query.lower():
                    object_type = "tag"
                else:
                    object_type = "address"  # Default

            logger.info(f"Listing {object_type} objects...")

            # Initialize the configuration
            xml_config = PANFlowConfig(config_file=config_file)

            # Get device type and set appropriate context
            device_type = xml_config.device_type.lower()

            # Default context type based on device type
            if device_type == "panorama":
                # Panorama uses "device_group" as context type
                context_type = command_args.get("context", "device_group")
                if "device_group" not in command_args:
                    # Use the first device group or "shared" as default
                    device_groups = xml_config.tree.xpath(
                        '/config/devices/entry[@name="localhost.localdomain"]/device-group/entry/@name'
                    )
                    default_dg = device_groups[0] if device_groups else "shared"
                    command_args["device_group"] = default_dg
            else:
                context_type = command_args.get("context", "vsys")
                if "vsys" not in command_args:
                    command_args["vsys"] = "vsys1"  # Default vsys

            # Get context kwargs
            context_kwargs = {}
            if "device_group" in command_args:
                context_kwargs["device_group"] = command_args["device_group"]
            if "vsys" in command_args:
                context_kwargs["vsys"] = command_args["vsys"]
            if "template" in command_args:
                context_kwargs["template"] = command_args["template"]

            # Check if we should find duplicates
            show_duplicates = command_args.get("show_duplicates", False)
            duplicates = {}  # Initialize the duplicates variable

            if show_duplicates:
                # Import the deduplication engine to find duplicates
                from panflow.core.deduplication import DeduplicationEngine

                # Create deduplication engine
                engine = DeduplicationEngine(
                    xml_config.tree,
                    xml_config.device_type,
                    context_type,
                    xml_config.version,
                    **context_kwargs,
                )

                # Find duplicates based on object type
                if object_type == "address":
                    duplicates, _ = engine.find_duplicate_addresses()
                elif object_type == "service":
                    duplicates, _ = engine.find_duplicate_services()
                else:
                    # Generic handling for other types
                    duplicates, _ = engine.find_duplicates(object_type)

                # Create a consolidated list of only the duplicate objects
                duplicate_objects = {}
                # Get all objects for reference (do this once outside the loop for efficiency)
                all_objects = xml_config.get_objects(object_type, context_type, **context_kwargs)

                for value, obj_list in duplicates.items():
                    for obj_info in obj_list:
                        # Handle different return types from the duplicate finding methods
                        if hasattr(obj_info, "object_name"):
                            obj_name = obj_info.object_name
                        elif isinstance(obj_info, tuple) and len(obj_info) >= 1:
                            obj_name = obj_info[0]  # Assume first item is the name
                        elif isinstance(obj_info, str):
                            obj_name = obj_info
                        else:
                            logger.warning(f"Unknown object info format: {type(obj_info)}")
                            continue

                        if obj_name in all_objects:
                            duplicate_objects[obj_name] = all_objects[obj_name]

                objects = duplicate_objects
                logger.info(
                    f"Found {len(duplicates)} unique values with duplicate {object_type} objects"
                )
            else:
                # Get all objects of the specified type
                objects = xml_config.get_objects(object_type, context_type, **context_kwargs)

            # Return a simplified result
            object_count = len(objects)
            logger.info(f"Found {object_count} {object_type} objects")

            # Format objects for display
            formatted_objects = []
            for obj_name, obj_props in objects.items():
                formatted_obj = {"name": obj_name}
                # Add all properties to the object
                if isinstance(obj_props, dict):
                    formatted_obj.update(obj_props)
                formatted_objects.append(formatted_obj)

            # Try to add formatted_objects_text using the common formatter
            try:
                from panflow.cli.common import format_objects_list

                formatted_lines = format_objects_list(formatted_objects, include_header=False)
                # Extract just the object info without the prefix
                formatted_objects_text = [line[4:] for line in formatted_lines]
            except ImportError:
                # Fallback if import fails
                formatted_objects_text = None

            # Build the appropriate message based on whether we were looking for duplicates
            if show_duplicates:
                message = f"Found {object_count} duplicated {object_type} objects"
                if len(duplicates) > 0:
                    message += f" across {len(duplicates)} unique values"
            else:
                message = f"Found {object_count} {object_type} objects"

            return {
                "message": message,
                "count": object_count,
                "object_type": object_type,
                "objects": formatted_objects,
                "formatted_objects": formatted_objects_text,  # Include formatted objects for display
                "is_duplicate_search": show_duplicates,
                "unique_values": len(duplicates) if show_duplicates else None,
            }

        # For listing policies
        elif command_name == "list_policies":
            from panflow import PANFlowConfig

            # Extract parameters
            config_file = command_args.get("config")
            # Handle both "policy_type" and "type" parameters
            if "policy_type" in command_args:
                policy_type = command_args["policy_type"]
            elif "type" in command_args:
                policy_type = (
                    command_args["type"][0]
                    if isinstance(command_args["type"], list)
                    else command_args["type"]
                )
            else:
                # Try to extract policy type from the query string if it's available
                query = command_args.get("original_query", "")

                # Initialize the configuration to check the device type
                xml_config = PANFlowConfig(config_file=config_file)
                device_type = xml_config.device_type.lower()

                # Adjust policy type based on device type
                if device_type == "panorama":
                    if "security" in query.lower():
                        # If "post" is in the query, use post-rules, otherwise use pre-rules
                        if "post" in query.lower():
                            policy_type = "security_post_rules"
                        else:
                            policy_type = "security_pre_rules"  # Default to pre-rules
                    elif "nat" in query.lower():
                        # If "post" is in the query, use post-rules, otherwise use pre-rules
                        if "post" in query.lower():
                            policy_type = "nat_post_rules"
                        else:
                            policy_type = "nat_pre_rules"  # Default to pre-rules
                    else:
                        policy_type = "security_pre_rules"  # Default for Panorama
                else:
                    # For firewall
                    if "security" in query.lower():
                        policy_type = "security_rules"
                    elif "nat" in query.lower():
                        policy_type = "nat_rules"
                    else:
                        policy_type = "security_rules"  # Default

            logger.info(f"Listing {policy_type} policies...")

            # Initialize the configuration
            xml_config = PANFlowConfig(config_file=config_file)

            # Get device type and set appropriate context
            device_type = xml_config.device_type.lower()

            # Default context type based on device type
            if device_type == "panorama":
                # Panorama uses "device_group" as context type
                context_type = command_args.get("context", "device_group")
                if "device_group" not in command_args:
                    # Use the first device group or "shared" as default
                    device_groups = xml_config.tree.xpath(
                        '/config/devices/entry[@name="localhost.localdomain"]/device-group/entry/@name'
                    )
                    default_dg = device_groups[0] if device_groups else "shared"
                    command_args["device_group"] = default_dg
            else:
                context_type = command_args.get("context", "vsys")
                if "vsys" not in command_args:
                    command_args["vsys"] = "vsys1"  # Default vsys

            # Get context kwargs
            context_kwargs = {}
            if "device_group" in command_args:
                context_kwargs["device_group"] = command_args["device_group"]
            if "vsys" in command_args:
                context_kwargs["vsys"] = command_args["vsys"]
            if "template" in command_args:
                context_kwargs["template"] = command_args["template"]

            # Check if this is a request for all policy types
            is_all_policy_types = policy_type.lower() == "all"

            if is_all_policy_types:
                logger.info("Request for 'all' policy types detected, checking multiple policy types")

                # For different device types, select appropriate policy types
                if device_type == "panorama":
                    policy_types = ["security_pre_rules", "security_post_rules", "nat_pre_rules", "nat_post_rules"]
                else:
                    policy_types = ["security_rules", "nat_rules"]

                # Store all policies with type information
                all_policies = {}
                all_formatted_policies = []

                # Loop through each policy type
                for current_policy_type in policy_types:
                    logger.info(f"Getting {current_policy_type}...")

                    try:
                        # Get policies for this type
                        current_policies = xml_config.get_policies(current_policy_type, context_type, **context_kwargs)

                        # Format policies for display
                        for policy_name, policy_props in current_policies.items():
                            # Create a policy dict with name and type fields
                            formatted_policy = {"name": policy_name, "policy_type": current_policy_type}

                            # Add key fields to the formatted policy
                            if isinstance(policy_props, dict):
                                key_fields = [
                                    "action",
                                    "from",
                                    "to",
                                    "source",
                                    "destination",
                                    "service",
                                    "application",
                                    "disabled",
                                ]
                                for field in key_fields:
                                    if field in policy_props:
                                        formatted_policy[field] = policy_props[field]

                            all_formatted_policies.append(formatted_policy)

                        # Add all policies from this type to the combined dictionary
                        all_policies.update(current_policies)
                    except Exception as e:
                        # Log error but continue with other policy types
                        logger.warning(f"Error getting {current_policy_type}: {str(e)}")

                # Use the combined results
                policies = all_policies
                formatted_policies = all_formatted_policies
                policy_type = "all"  # Set to "all" for display purposes

                # Get total count
                policy_count = len(formatted_policies)
                logger.info(f"Found {policy_count} policies across multiple policy types")
            else:
                # Regular single policy type handling
                # Adjust policy type if necessary for the device type
                if device_type == "panorama":
                    if policy_type == "security_rules":
                        policy_type = "security_pre_rules"
                    elif policy_type == "nat_rules":
                        policy_type = "nat_pre_rules"
                    logger.info(f"Adjusted policy type to {policy_type} for Panorama device")

                # Get policies of the specified type
                policies = xml_config.get_policies(policy_type, context_type, **context_kwargs)

                # Get total count
                policy_count = len(policies)
                logger.info(f"Found {policy_count} {policy_type}")

                # Format policies for display
                formatted_policies = []
                for policy_name, policy_props in policies.items():
                    # Create a policy dict with name field
                    formatted_policy = {"name": policy_name}
                    # Add key fields to the formatted policy
                    if isinstance(policy_props, dict):
                        key_fields = [
                            "action",
                            "from",
                            "to",
                            "source",
                            "destination",
                            "service",
                            "application",
                            "disabled",
                        ]
                        for field in key_fields:
                            if field in policy_props:
                                formatted_policy[field] = policy_props[field]
                    formatted_policies.append(formatted_policy)

            # Try to add formatted_policies_text using the common formatter
            try:
                from panflow.cli.common import format_policies_list

                formatted_lines = format_policies_list(formatted_policies, include_header=False)
                # Extract just the policy info without the prefix
                formatted_policies_text = [line[4:] for line in formatted_lines]
            except ImportError:
                # Fallback if import fails
                formatted_policies_text = None

            return {
                "message": f"Found {policy_count} {policy_type}",
                "count": policy_count,
                "policies": formatted_policies,
                "formatted_policies": formatted_policies_text,  # Include formatted policies for display
            }

        # For viewing unused objects (no cleanup)
        elif command_name == "list_unused_objects":
            from panflow import PANFlowConfig
            from panflow.reporting import generate_unused_objects_report

            # Extract parameters
            config_file = command_args.get("config")
            # Handle both "object_type" and "type" parameters
            if "object_type" in command_args:
                object_type = command_args["object_type"]
            elif "type" in command_args:
                object_type = (
                    command_args["type"][0]
                    if isinstance(command_args["type"], list)
                    else command_args["type"]
                )
            else:
                object_type = "address"  # Default

            logger.info(f"Analyzing {object_type} objects for usage...")

            # Initialize the configuration
            xml_config = PANFlowConfig(config_file=config_file)

            # Get device type and set appropriate context
            device_type = xml_config.device_type.lower()

            # Default context type based on device type
            if device_type == "panorama":
                # Panorama uses "device_group" as context type
                context_type = command_args.get("context", "device_group")
                if "device_group" not in command_args:
                    # Use the first device group or "shared" as default
                    device_groups = xml_config.tree.xpath(
                        '/config/devices/entry[@name="localhost.localdomain"]/device-group/entry/@name'
                    )
                    default_dg = device_groups[0] if device_groups else "shared"
                    command_args["device_group"] = default_dg
            else:
                context_type = command_args.get("context", "vsys")
                if "vsys" not in command_args:
                    command_args["vsys"] = "vsys1"  # Default vsys

            # Get context kwargs
            context_kwargs = {}
            if "device_group" in command_args:
                context_kwargs["device_group"] = command_args["device_group"]
            if "vsys" in command_args:
                context_kwargs["vsys"] = command_args["vsys"]
            if "template" in command_args:
                context_kwargs["template"] = command_args["template"]

            # Ensure object_type is set
            if not object_type:
                object_type = "address"  # Default to address if somehow None

            # Generate the report
            logger.info(f"Generating report for {object_type} objects...")
            report = generate_unused_objects_report(
                xml_config.tree,
                xml_config.device_type,
                context_type,
                xml_config.version,
                object_type=object_type,
                **context_kwargs,
            )

            # Return a simplified result
            unused_count = len(report.get("unused_objects", []))
            logger.info(f"Found {unused_count} unused {object_type} objects")
            return {
                "message": f"Found {unused_count} unused {object_type} objects",
                "count": unused_count,
                "unused_objects": [obj["name"] for obj in report.get("unused_objects", [])],
            }

        # For viewing disabled policies (no cleanup)
        elif command_name == "list_disabled_policies":
            from panflow import PANFlowConfig

            # Extract parameters
            config_file = command_args.get("config")

            # Handle both policy_type and type parameters
            if "policy_type" in command_args:
                policy_type = command_args["policy_type"]
            elif "type" in command_args:
                policy_type = (
                    command_args["type"][0]
                    if isinstance(command_args["type"], list)
                    else command_args["type"]
                )
            else:
                policy_type = "security_rules"  # Default

            # Check if this is a request for all policy types
            is_all_policy_types = False
            if policy_type.lower() in ["all", "any", "policy", "policies"]:
                is_all_policy_types = True
                logger.info("Request for 'all' policy types detected, checking multiple policy types")

            # Initialize the configuration
            xml_config = PANFlowConfig(config_file=config_file)

            # Get device type and set appropriate context
            device_type = xml_config.device_type.lower()

            # Default context type based on device type
            if device_type == "panorama":
                # Panorama uses "device_group" as context type
                context_type = command_args.get("context", "device_group")
                if "device_group" not in command_args:
                    # Use the first device group or "shared" as default
                    device_groups = xml_config.tree.xpath(
                        '/config/devices/entry[@name="localhost.localdomain"]/device-group/entry/@name'
                    )
                    default_dg = device_groups[0] if device_groups else "shared"
                    command_args["device_group"] = default_dg
            else:
                context_type = command_args.get("context", "vsys")
                if "vsys" not in command_args:
                    command_args["vsys"] = "vsys1"  # Default vsys

            # Get context kwargs
            context_kwargs = {}
            if "device_group" in command_args:
                context_kwargs["device_group"] = command_args["device_group"]
            if "vsys" in command_args:
                context_kwargs["vsys"] = command_args["vsys"]
            if "template" in command_args:
                context_kwargs["template"] = command_args["template"]

            # Instead of just getting names, get detailed policy info for disabled policies
            # For better presentation, we'll use the policy module
            from panflow.modules.policies import get_policies

            # Process policy types based on whether we're checking all or specific types
            if is_all_policy_types:
                # For different device types, select appropriate policy types
                if device_type == "panorama":
                    policy_types = ["security_pre_rules", "security_post_rules", "nat_pre_rules", "nat_post_rules"]
                else:
                    policy_types = ["security_rules", "nat_rules"]

                logger.info(f"Analyzing multiple policy types: {', '.join(policy_types)}")

                # Store all disabled policies with type information
                all_disabled_policies_details = []

                # Loop through each policy type and collect disabled policies
                for current_policy_type in policy_types:
                    logger.info(f"Checking for disabled {current_policy_type}...")

                    # Get policies for this type
                    current_policy_dict = get_policies(
                        xml_config.tree,
                        current_policy_type,
                        device_type,
                        context_type,
                        xml_config.version,
                        **context_kwargs,
                    )

                    # Filter to just the disabled ones
                    for name, properties in current_policy_dict.items():
                        if properties.get("disabled") == "yes":
                            policy_info = {"name": name, "policy_type": current_policy_type}
                            policy_info.update(properties)
                            all_disabled_policies_details.append(policy_info)

                # Use the combined results
                disabled_policies_details = all_disabled_policies_details
                policy_type = "all"  # Set to "all" for display purposes
            else:
                # Regular single policy type handling
                logger.info(f"Analyzing {policy_type} for disabled policies...")

                # Get all policies first
                if device_type == "panorama":
                    # Adjust policy type to match what's expected for panorama
                    if policy_type == "security_rules":
                        policy_type = "security_pre_rules"
                    elif policy_type == "nat_rules":
                        policy_type = "nat_pre_rules"

                # Get all policies
                policy_dict = get_policies(
                    xml_config.tree,
                    policy_type,
                    device_type,
                    context_type,
                    xml_config.version,
                    **context_kwargs,
                )

                # Filter to just the disabled ones
                disabled_policies_details = []
                for name, properties in policy_dict.items():
                    if properties.get("disabled") == "yes":
                        policy_info = {"name": name}
                        policy_info.update(properties)
                        disabled_policies_details.append(policy_info)

            # Extract just names for backwards compatibility
            disabled_policies = [p["name"] for p in disabled_policies_details]

            # Return a detailed result
            disabled_count = len(disabled_policies)
            if is_all_policy_types:
                logger.info(f"Found {disabled_count} disabled policies across multiple policy types")
            else:
                logger.info(f"Found {disabled_count} disabled {policy_type}")

            # Format detailed output for text display using common formatting
            try:
                from panflow.cli.common import format_policies_list, format_policy_for_display

                # Create formatted policies without header (we'll add our own)
                formatted_policies_with_prefix = format_policies_list(
                    disabled_policies_details, include_header=False
                )

                # Extract just the policy info without the "  - " prefix
                formatted_policies = [line[4:] for line in formatted_policies_with_prefix]
            except ImportError:
                # Fallback to direct formatting if import fails
                formatted_policies = []
                for policy in disabled_policies_details:
                    # Use a simple formatting approach if we can't import the common formatter
                    name = policy.get("name", "unnamed")
                    action = policy.get("action", "")
                    disabled = " (DISABLED)" if policy.get("disabled") == "yes" else ""
                    formatted_policy = f"{name}: action:{action}{disabled}"
                    formatted_policies.append(formatted_policy)

            return {
                "message": f"Found {disabled_count} disabled {policy_type}",
                "count": disabled_count,
                "disabled_policies": disabled_policies,
                "disabled_policies_details": disabled_policies_details,
                "formatted_policies": formatted_policies,  # For enhanced display
            }

        # For cleanup operations, use the existing CLI commands
        elif command_name == "cleanup_unused_objects":
            from panflow.cli.commands.cleanup_commands import cleanup_unused_objects
            import json
            import os

            # Make sure we have required parameters with the correct names
            if "device_type" not in command_args:
                # Initialize the configuration to get device type
                from panflow import PANFlowConfig

                xml_config = PANFlowConfig(config_file=command_args["config"])
                command_args["device_type"] = xml_config.device_type.lower()

                # Also set version while we have the config loaded
                if "version" not in command_args:
                    command_args["version"] = xml_config.version

            # Set defaults for required params that might be missing
            if "context" not in command_args:
                command_args["context"] = (
                    "device_group" if command_args["device_type"].lower() == "panorama" else "vsys"
                )

            if "vsys" not in command_args and command_args["context"] == "vsys":
                command_args["vsys"] = "vsys1"

            # Make sure device_group is set for Panorama configs
            if (
                command_args["device_type"].lower() == "panorama"
                and "device_group" not in command_args
            ):
                # Initialize config if we haven't already
                if "xml_config" not in locals():
                    from panflow import PANFlowConfig

                    xml_config = PANFlowConfig(config_file=command_args["config"])

                # Get available device groups
                device_groups = xml_config.tree.xpath(
                    '/config/devices/entry[@name="localhost.localdomain"]/device-group/entry/@name'
                )
                if device_groups:
                    command_args["device_group"] = str(device_groups[0])
                else:
                    command_args["device_group"] = "shared"

            # Default to dry run if not specified
            if "dry_run" not in command_args:
                command_args["dry_run"] = False

            # Set exclude_file to None if not provided
            if "exclude_file" not in command_args:
                command_args["exclude_file"] = None

            # Create a temporary report file to capture the results
            import tempfile

            temp_report_file = os.path.join(
                tempfile.gettempdir(), f"panflow_cleanup_report_{os.getpid()}.json"
            )
            command_args["report_file"] = temp_report_file

            # Make sure we have a valid output file
            if "output" not in command_args or command_args["output"] is None:
                # Log the issue
                logger.error("No output file specified for cleanup operation")
                return {
                    "message": "Cannot cleanup unused objects without an output file. Please specify an output file with --output.",
                    "success": False,
                }

            # Log the parameters for debugging
            logger.debug(f"Calling cleanup_unused_objects with parameters: {command_args}")

            # Get the object types
            object_types = command_args.get("object_types", ["address"])
            logger.info(f"Cleaning up unused {', '.join(object_types)} objects...")

            # Remove 'original_query' parameter as it's not expected by the cleanup function
            if "original_query" in command_args:
                command_args_clean = {
                    k: v for k, v in command_args.items() if k != "original_query"
                }
            else:
                command_args_clean = command_args

            # Call the cleanup function
            cleanup_unused_objects(**command_args_clean)

            # Read the report file to get the results
            if os.path.exists(temp_report_file):
                try:
                    with open(temp_report_file, "r") as f:
                        report_data = json.load(f)

                    # Clean up temporary file
                    os.unlink(temp_report_file)

                    # Create a user-friendly result
                    cleaned_objects = []
                    for obj_type, objects in report_data.get("cleaned_objects", {}).items():
                        cleaned_objects.extend(objects)

                    total_cleaned = report_data.get("summary", {}).get("total_cleaned_up", 0)

                    return {
                        "message": f"Cleaned up {total_cleaned} unused objects",
                        "count": total_cleaned,
                        "cleaned_objects": cleaned_objects,
                        "output_file": command_args["output"],
                        "details": report_data,
                    }
                except Exception as e:
                    logger.error(f"Error reading cleanup report: {e}")

            # Fallback if report can't be read
            return {
                "message": f"Cleaned up unused {', '.join(object_types)} objects",
                "output_file": command_args["output"],
            }

        elif command_name == "cleanup_disabled_policies":
            from panflow.cli.commands.cleanup_commands import cleanup_disabled_policies
            import json
            import os

            # Make sure we have required parameters with the correct names
            if "device_type" not in command_args:
                # Initialize the configuration to get device type
                from panflow import PANFlowConfig

                xml_config = PANFlowConfig(config_file=command_args["config"])
                command_args["device_type"] = xml_config.device_type.lower()

                # Also set version while we have the config loaded
                if "version" not in command_args:
                    command_args["version"] = xml_config.version

            # Set defaults for required params that might be missing
            if "context" not in command_args:
                command_args["context"] = (
                    "device_group" if command_args["device_type"].lower() == "panorama" else "vsys"
                )

            if "vsys" not in command_args and command_args["context"] == "vsys":
                command_args["vsys"] = "vsys1"

            # Make sure device_group is set for Panorama configs
            if (
                command_args["device_type"].lower() == "panorama"
                and "device_group" not in command_args
            ):
                # Initialize config if we haven't already
                if "xml_config" not in locals():
                    from panflow import PANFlowConfig

                    xml_config = PANFlowConfig(config_file=command_args["config"])

                # Get available device groups
                device_groups = xml_config.tree.xpath(
                    '/config/devices/entry[@name="localhost.localdomain"]/device-group/entry/@name'
                )
                if device_groups:
                    command_args["device_group"] = str(device_groups[0])
                else:
                    command_args["device_group"] = "shared"

            # Default to dry run if not specified
            if "dry_run" not in command_args:
                command_args["dry_run"] = False

            # Set exclude_file to None if not provided
            if "exclude_file" not in command_args:
                command_args["exclude_file"] = None

            # Create a temporary report file to capture the results
            import tempfile

            temp_report_file = os.path.join(
                tempfile.gettempdir(), f"panflow_cleanup_report_{os.getpid()}.json"
            )
            command_args["report_file"] = temp_report_file

            # Make sure we have a valid output file
            if "output" not in command_args or command_args["output"] is None:
                # Log the issue
                logger.error("No output file specified for cleanup operation")
                return {
                    "message": "Cannot cleanup disabled policies without an output file. Please specify an output file with --output.",
                    "success": False,
                }

            # Log the parameters for debugging
            logger.debug(f"Calling cleanup_disabled_policies with parameters: {command_args}")

            # Get the policy types
            policy_types = command_args.get("policy_types", ["security_rules"])
            logger.info(f"Cleaning up disabled {', '.join(policy_types)} policies...")

            # Remove 'original_query' parameter as it's not expected by the cleanup function
            if "original_query" in command_args:
                command_args_clean = {
                    k: v for k, v in command_args.items() if k != "original_query"
                }
            else:
                command_args_clean = command_args

            # Call the cleanup function
            cleanup_disabled_policies(**command_args_clean)

            # Read the report file to get the results
            if os.path.exists(temp_report_file):
                try:
                    with open(temp_report_file, "r") as f:
                        report_data = json.load(f)

                    # Clean up temporary file
                    os.unlink(temp_report_file)

                    # Create a user-friendly result
                    cleaned_policies = []
                    for policy_type, policies in report_data.get("cleaned_policies", {}).items():
                        cleaned_policies.extend(policies)

                    total_cleaned = report_data.get("summary", {}).get("total_cleaned_up", 0)

                    return {
                        "message": f"Cleaned up {total_cleaned} disabled policies",
                        "count": total_cleaned,
                        "cleaned_policies": cleaned_policies,
                        "output_file": command_args["output"],
                        "details": report_data,
                    }
                except Exception as e:
                    logger.error(f"Error reading cleanup report: {e}")

            # Fallback if report can't be read
            return {
                "message": f"Cleaned up disabled {', '.join(policy_types)} policies",
                "output_file": command_args["output"],
            }

        # Add more commands as needed
        elif command_name in ["find_duplicates", "deduplicate_objects"]:
            from panflow import PANFlowConfig
            from panflow.core.deduplication import DeduplicationEngine

            # Extract parameters
            config_file = command_args.get("config")
            output_file = command_args.get("output")
            dry_run = command_args.get("dry_run", False)

            # Handle both "object_type" and "type" parameters
            if "object_type" in command_args:
                object_type = command_args["object_type"]
            elif "type" in command_args:
                object_type = (
                    command_args["type"][0]
                    if isinstance(command_args["type"], list)
                    else command_args["type"]
                )
            else:
                object_type = "address"  # Default

            # Determine whether to find or deduplicate
            is_deduplication = command_name == "deduplicate_objects" and output_file is not None

            action_word = "Deduplicating" if is_deduplication else "Analyzing"
            logger.info(f"{action_word} {object_type} objects for duplicates...")

            # Initialize the configuration
            xml_config = PANFlowConfig(config_file=config_file)

            # Get device type and set appropriate context
            device_type = xml_config.device_type.lower()

            # Default context type based on device type
            if device_type == "panorama":
                # Panorama uses "device_group" as context type
                context_type = command_args.get("context", "device_group")
                if "device_group" not in command_args:
                    # Use the first device group or "shared" as default
                    device_groups = xml_config.tree.xpath(
                        '/config/devices/entry[@name="localhost.localdomain"]/device-group/entry/@name'
                    )
                    default_dg = device_groups[0] if device_groups else "shared"
                    command_args["device_group"] = default_dg
            else:
                context_type = command_args.get("context", "vsys")
                if "vsys" not in command_args:
                    command_args["vsys"] = "vsys1"  # Default vsys

            # Get context kwargs
            context_kwargs = {}
            if "device_group" in command_args:
                context_kwargs["device_group"] = command_args["device_group"]
            if "vsys" in command_args:
                context_kwargs["vsys"] = command_args["vsys"]
            if "template" in command_args:
                context_kwargs["template"] = command_args["template"]

            # Create deduplication engine
            engine = DeduplicationEngine(
                xml_config.tree,
                xml_config.device_type,
                context_type,
                xml_config.version,
                **context_kwargs,
            )

            # Check if this is a request for "all" types of objects
            if object_type.lower() in ["all", "any", "every", "object", "objects"]:
                logger.info("Request for 'all' object types detected, checking common object types")

                # Initialize combined results
                combined_duplicates = {}
                common_types = ["address", "service", "tag"]

                # For deduplication, track which type each value belongs to
                value_to_type_map = {}

                # Check each common object type
                for obj_type in common_types:
                    logger.info(f"Checking for duplicate {obj_type} objects...")
                    if obj_type == "address":
                        type_duplicates, _ = engine.find_duplicate_addresses()
                    elif obj_type == "service":
                        type_duplicates, _ = engine.find_duplicate_services()
                    else:
                        # Generic handling for other types
                        type_duplicates, _ = engine.find_duplicates(obj_type)

                    # Add type prefix to each key to avoid key collisions
                    for key, value in type_duplicates.items():
                        combined_key = f"{obj_type}:{key}"
                        combined_duplicates[combined_key] = value
                        # Store the mapping of combined key to object type for deduplication
                        value_to_type_map[combined_key] = obj_type

                # Use the combined results
                duplicates = combined_duplicates
                # Update object type for display
                original_object_type = object_type
                object_type = "all"

                # If this is a deduplication request, we need to modify the to_remove processing
                if is_deduplication and not dry_run:
                    # Set a flag to indicate we're deduplicating all types
                    deduplicating_all_types = True
                else:
                    deduplicating_all_types = False
            else:
                # Regular single type handling
                if object_type == "address":
                    duplicates, _ = engine.find_duplicate_addresses()
                elif object_type == "service":
                    duplicates, _ = engine.find_duplicate_services()
                else:
                    # Generic handling for other types
                    duplicates, _ = engine.find_duplicates(object_type)

            # Count total duplicates
            total_duplicates = sum(len(items) - 1 for items in duplicates.values())
            unique_values = len(duplicates)

            # Process deduplication if requested and not in dry run mode
            cleaned_count = 0
            cleaned_objects = []

            if is_deduplication and not dry_run:
                try:
                    # The deduplication engine doesn't have a general deduplicate method yet,
                    # so let's implement a simple version ourselves based on the duplicates found

                    # First, verify if we actually found any duplicates
                    if not duplicates:
                        logger.info(f"No duplicate {object_type} objects found to deduplicate")
                        return {
                            "message": f"No duplicate {object_type} objects found to deduplicate",
                            "count": 0,
                            "success": True,
                        }

                    # Process duplicates - keep first occurrence, mark others for removal
                    to_remove = []
                    object_type_map = {}  # Used to track object type for "all" deduplication

                    for value, objects_list in duplicates.items():
                        # Skip if there's only one object
                        if len(objects_list) <= 1:
                            continue

                        # Keep the first one, mark others for removal
                        # Skip the first item (index 0) and add the rest to the removal list
                        if isinstance(objects_list[0], tuple):
                            # Handle tuple format (name, path)
                            for obj in objects_list[1:]:
                                obj_name = obj[0] if len(obj) > 0 else None
                                if obj_name:
                                    to_remove.append(obj_name)
                                    # If this is deduplicating all types, track the object type
                                    if 'deduplicating_all_types' in locals() and deduplicating_all_types and 'value_to_type_map' in locals():
                                        if value in value_to_type_map:
                                            object_type_map[obj_name] = value_to_type_map[value]
                                        # If the key itself contains object type info (e.g., "address:10.10.10.10")
                                        elif ":" in value:
                                            obj_type = value.split(":", 1)[0]
                                            object_type_map[obj_name] = obj_type
                        else:
                            # Handle other formats (might have object_name attribute)
                            for obj in objects_list[1:]:
                                if hasattr(obj, "object_name"):
                                    to_remove.append(obj.object_name)
                                    # If this is deduplicating all types, track the object type
                                    if 'deduplicating_all_types' in locals() and deduplicating_all_types and 'value_to_type_map' in locals():
                                        if value in value_to_type_map:
                                            object_type_map[obj.object_name] = value_to_type_map[value]
                                        # If the key itself contains object type info (e.g., "address:10.10.10.10")
                                        elif ":" in value:
                                            obj_type = value.split(":", 1)[0]
                                            object_type_map[obj.object_name] = obj_type
                                elif isinstance(obj, str):
                                    to_remove.append(obj)
                                    # If this is deduplicating all types, track the object type
                                    if 'deduplicating_all_types' in locals() and deduplicating_all_types and 'value_to_type_map' in locals():
                                        if value in value_to_type_map:
                                            object_type_map[obj] = value_to_type_map[value]
                                        # If the key itself contains object type info (e.g., "address:10.10.10.10")
                                        elif ":" in value:
                                            obj_type = value.split(":", 1)[0]
                                            object_type_map[obj] = obj_type

                    # Remove the duplicate objects
                    cleaned_count = len(to_remove)
                    cleaned_objects = to_remove

                    if cleaned_count > 0:
                        # Actually remove the duplicated objects from the config
                        import lxml.etree as ET

                        # Create a copy of the XML tree
                        updated_tree = ET.ElementTree(ET.fromstring(ET.tostring(xml_config.tree.getroot())))

                        # Track successful removals
                        successful_removals = []

                        # Process each object to remove
                        for obj_name in to_remove:
                            try:
                                # Determine the object type for this object
                                current_obj_type = object_type
                                if 'deduplicating_all_types' in locals() and deduplicating_all_types and obj_name in object_type_map:
                                    # Use the object type from the map for this specific object
                                    current_obj_type = object_type_map[obj_name]
                                    logger.debug(f"Using specific object type '{current_obj_type}' for object '{obj_name}'")

                                # Find the object's context type
                                if device_type == "panorama":
                                    # Try to find in device groups first
                                    if "device_group" in context_kwargs:
                                        context = "device_group"
                                        dg_name = context_kwargs["device_group"]
                                        xpath = f'/config/devices/entry[@name="localhost.localdomain"]/device-group/entry[@name="{dg_name}"]/{current_obj_type}/entry[@name="{obj_name}"]'
                                    else:
                                        # Default to shared
                                        context = "shared"
                                        xpath = f'/config/shared/{current_obj_type}/entry[@name="{obj_name}"]'
                                else:
                                    # For firewall configs
                                    if "vsys" in context_kwargs:
                                        vsys_name = context_kwargs["vsys"]
                                        xpath = f'/config/devices/entry[@name="localhost.localdomain"]/vsys/entry[@name="{vsys_name}"]/{current_obj_type}/entry[@name="{obj_name}"]'
                                    else:
                                        # Default to vsys1
                                        xpath = f'/config/devices/entry[@name="localhost.localdomain"]/vsys/entry[@name="vsys1"]/{current_obj_type}/entry[@name="{obj_name}"]'

                                # Find the object element
                                object_elem = updated_tree.xpath(xpath)
                                if object_elem and len(object_elem) > 0:
                                    # Get the parent element
                                    parent = object_elem[0].getparent()
                                    if parent is not None:
                                        # Remove the object from its parent
                                        parent.remove(object_elem[0])
                                        successful_removals.append(obj_name)
                                        logger.info(f"Removed duplicate object: {obj_name}")
                                    else:
                                        logger.warning(f"Could not find parent for object: {obj_name}")
                                else:
                                    logger.warning(f"Could not find object {obj_name} using xpath: {xpath}")
                            except Exception as e:
                                logger.error(f"Error removing duplicate object {obj_name}: {str(e)}")

                        # Save the updated tree to the output file
                        updated_tree.write(output_file, pretty_print=True, encoding="UTF-8", xml_declaration=True)

                        # Update the count to reflect actually removed objects
                        cleaned_count = len(successful_removals)
                        cleaned_objects = successful_removals

                        logger.info(f"Deduplicated {cleaned_count} {object_type} objects")
                        logger.info(f"Updated configuration saved to {output_file}")
                    else:
                        logger.info(f"No objects to deduplicate")

                except Exception as e:
                    logger.error(f"Error deduplicating objects: {e}")
                    return {
                        "message": f"Error deduplicating objects: {str(e)}",
                        "count": 0,
                        "success": False,
                    }

            # Return result based on operation type
            if is_deduplication:
                message = (
                    f"Deduplicated {cleaned_count} {object_type} objects"
                    if not dry_run
                    else f"Would deduplicate {total_duplicates} {object_type} objects"
                )
                return {
                    "message": message,
                    "count": cleaned_count if not dry_run else total_duplicates,
                    "unique_values": unique_values,
                    "object_type": object_type,
                    "cleaned_objects": cleaned_objects,
                    "output_file": output_file,
                    "success": True,
                }
            else:
                # Just finding duplicates, no deduplication
                logger.info(
                    f"Found {total_duplicates} duplicate {object_type} objects across {unique_values} values"
                )
                return {
                    "message": f"Found {total_duplicates} duplicate {object_type} objects across {unique_values} values",
                    "count": total_duplicates,
                    "unique_values": unique_values,
                    "object_type": object_type,
                    "duplicates": duplicates,
                }

        else:
            # For bulk update operations
            if command_name == "bulk_update_policies":
                from panflow import PANFlowConfig
                from panflow.core.bulk_operations import ConfigUpdater, ConfigQuery
                import json
                import os
                from lxml import etree

                # Extract parameters
                config_file = command_args.get("config")
                output_file = command_args.get("output")
                policy_type = command_args.get("policy_type")
                operation = command_args.get("operation")
                value = command_args.get("value")
                criteria = command_args.get("criteria", None)  # Optional criteria for filtering
                dry_run = command_args.get("dry_run", False)

                # Make sure we have required parameters
                if not all([config_file, output_file, policy_type, operation, value]):
                    missing = []
                    if not config_file:
                        missing.append("config_file")
                    if not output_file:
                        missing.append("output_file")
                    if not policy_type:
                        missing.append("policy_type")
                    if not operation:
                        missing.append("operation")
                    if not value:
                        missing.append("value")
                    raise ValueError(f"Missing required parameters for bulk update: {', '.join(missing)}")

                # Initialize the configuration
                xml_config = PANFlowConfig(config_file=config_file)

                # Determine the device type
                device_type = xml_config.device_type.lower()

                # Default context type based on device type
                if device_type == "panorama":
                    # Panorama uses "device_group" as context type
                    context_type = command_args.get("context", "device_group")
                    if "device_group" not in command_args:
                        # Use the first device group or "shared" as default
                        device_groups = xml_config.tree.xpath(
                            '/config/devices/entry[@name="localhost.localdomain"]/device-group/entry/@name'
                        )
                        default_dg = device_groups[0] if device_groups else "shared"
                        command_args["device_group"] = default_dg
                else:
                    context_type = command_args.get("context", "vsys")
                    if "vsys" not in command_args:
                        command_args["vsys"] = "vsys1"  # Default vsys

                # Get context kwargs
                context_kwargs = {}
                if "device_group" in command_args:
                    context_kwargs["device_group"] = command_args["device_group"]
                if "vsys" in command_args:
                    context_kwargs["vsys"] = command_args["vsys"]
                if "template" in command_args:
                    context_kwargs["template"] = command_args["template"]

                # Create a temporary report file to capture the results
                import tempfile
                temp_report_file = os.path.join(
                    tempfile.gettempdir(), f"panflow_bulkupdate_report_{os.getpid()}.json"
                )

                # Set up operation parameters for bulk update
                operation_args = {
                    "config_file": config_file,
                    "device_type": device_type,
                    "context_type": context_type,
                    "policy_type": policy_type,
                    "output_file": output_file,
                    "report_file": temp_report_file,
                    "dry_run": dry_run,
                    "operation": operation,
                    "value": value,
                }

                # Add context specific parameters
                operation_args.update(context_kwargs)

                # Add criteria if specified
                if criteria:
                    operation_args["criteria"] = criteria

                # Adjust policy type based on device type if necessary
                if device_type == "panorama" and policy_type == "security_rules":
                    policy_type = "security_pre_rules"
                    logger.info(f"Adjusted policy_type from security_rules to security_pre_rules for Panorama device")
                elif device_type == "panorama" and policy_type == "nat_rules":
                    policy_type = "nat_pre_rules"
                    logger.info(f"Adjusted policy_type from nat_rules to nat_pre_rules for Panorama device")

                # Log the operation
                logger.info(f"Performing bulk update: {operation}={value} on {policy_type} policies")

                try:
                    # Initialize the configuration
                    xml_config = PANFlowConfig(config_file=config_file)
                    tree = xml_config.tree

                    # Create a ConfigUpdater and ConfigQuery
                    updater = ConfigUpdater(tree, device_type, context_type, xml_config.version, **context_kwargs)
                    query = ConfigQuery(tree, device_type, context_type, xml_config.version, **context_kwargs)

                    # Get policies to update
                    if policy_type == "all":
                        # For "all" policy types, we need to update each type separately
                        if device_type == "panorama":
                            policy_types_to_update = ["security_pre_rules", "security_post_rules", "nat_pre_rules", "nat_post_rules"]
                            logger.info("Using all panorama policy types for 'all' policy update")
                        else:
                            policy_types_to_update = ["security_rules", "nat_rules"]
                            logger.info("Using all firewall policy types for 'all' policy update")
                    else:
                        # Still need to handle individual policy types for Panorama properly
                        if device_type == "panorama" and policy_type == "security_rules":
                            policy_types_to_update = ["security_pre_rules"]
                            logger.info("Using security_pre_rules for 'security_rules' on Panorama")
                        elif device_type == "panorama" and policy_type == "nat_rules":
                            policy_types_to_update = ["nat_pre_rules"]
                            logger.info("Using nat_pre_rules for 'nat_rules' on Panorama")
                        else:
                            policy_types_to_update = [policy_type]

                    # Track all updated policies
                    all_updated_policies = []

                    # Process each policy type
                    for current_policy_type in policy_types_to_update:
                        logger.info(f"Applying operation {operation}={value} to {current_policy_type}")

                        # Get all policies of this type
                        try:
                            # Use queries for policy selection
                            # First try to get policies directly from the config
                            from panflow.modules.policies import get_policies

                            policies_dict = get_policies(
                                tree,
                                current_policy_type,
                                device_type,
                                context_type,
                                xml_config.version,
                                **context_kwargs
                            )

                            policy_names = list(policies_dict.keys())

                            if not policy_names:
                                logger.warning(f"No {current_policy_type} found in configuration using get_policies")
                                # Fall back to query system
                                policy_list = query.select_policies(current_policy_type)
                                logger.debug(f"Policy list from query: {policy_list}")

                                if not policy_list:
                                    logger.info(f"No {current_policy_type} found to update")
                                    continue

                                # Get just the policy names
                                policy_names = []
                                for policy in policy_list:
                                    if isinstance(policy, dict) and "name" in policy:
                                        policy_names.append(policy["name"])
                                    elif hasattr(policy, "get") and policy.get("name"):
                                        policy_names.append(policy.get("name"))
                                    elif hasattr(policy, "name"):
                                        policy_names.append(policy.name)
                                    elif hasattr(policy, "get") and callable(policy.get):
                                        name = policy.get("name")
                                        if name:
                                            policy_names.append(name)

                            logger.info(f"Found {len(policy_names)} policies of type {current_policy_type}: {policy_names}")

                            if not policy_names:
                                logger.info(f"No {current_policy_type} found with names")
                                continue
                        except Exception as e:
                            logger.error(f"Error retrieving policies of type {current_policy_type}: {str(e)}")
                            continue

                        if not policy_names:
                            logger.info(f"No {current_policy_type} found to update")
                            continue

                        # Apply the operation to all policies
                        if operation == "add_tag":
                            # Find the policies and add tags directly
                            updated = []
                            for policy_name in policy_names:
                                try:
                                    # Create xpath to the specific policy
                                    if current_policy_type in ["security_pre_rules", "security_post_rules"] and device_type.lower() == "panorama":
                                        # For Panorama security policies
                                        rulebase = "pre-rulebase" if current_policy_type == "security_pre_rules" else "post-rulebase"
                                        device_group = context_kwargs.get("device_group", "shared")

                                        if device_group == "shared":
                                            xpath = f'/config/shared/{rulebase}/security/rules/entry[@name="{policy_name}"]'
                                        else:
                                            xpath = f'/config/devices/entry[@name="localhost.localdomain"]/device-group/entry[@name="{device_group}"]/{rulebase}/security/rules/entry[@name="{policy_name}"]'
                                    elif current_policy_type in ["nat_pre_rules", "nat_post_rules"] and device_type.lower() == "panorama":
                                        # For Panorama NAT policies
                                        rulebase = "pre-rulebase" if current_policy_type == "nat_pre_rules" else "post-rulebase"
                                        device_group = context_kwargs.get("device_group", "shared")

                                        if device_group == "shared":
                                            xpath = f'/config/shared/{rulebase}/nat/rules/entry[@name="{policy_name}"]'
                                        else:
                                            xpath = f'/config/devices/entry[@name="localhost.localdomain"]/device-group/entry[@name="{device_group}"]/{rulebase}/nat/rules/entry[@name="{policy_name}"]'
                                    else:
                                        # For other security policies, use the actual xpath resolver
                                        from panflow.core.xpath_resolver import get_policy_xpath
                                        xpath = get_policy_xpath(
                                            current_policy_type,
                                            device_type,
                                            context_type,
                                            xml_config.version,
                                            name=policy_name,
                                            **context_kwargs
                                        )

                                    # Find the policy element
                                    policy_elem = tree.xpath(xpath)
                                    if policy_elem and len(policy_elem) > 0:
                                        policy = policy_elem[0]

                                        # Find or create tag element
                                        tag_elem = policy.find('./tag')
                                        if tag_elem is None:
                                            tag_elem = etree.SubElement(policy, 'tag')

                                        # Check if tag already exists
                                        member_exists = False
                                        for member in tag_elem.findall('./member'):
                                            if member.text == value:
                                                member_exists = True
                                                break

                                        # Add the tag if it doesn't exist
                                        if not member_exists:
                                            member = etree.SubElement(tag_elem, 'member')
                                            member.text = value
                                            updated.append(policy_name)
                                            logger.info(f"Added tag '{value}' to policy '{policy_name}'")
                                    else:
                                        logger.warning(f"Policy '{policy_name}' not found at xpath: {xpath}")
                                except Exception as e:
                                    logger.error(f"Error adding tag to policy '{policy_name}': {str(e)}")
                        elif operation == "set_action":
                            updated = []
                            for policy_name in policy_names:
                                try:
                                    # Similar approach as add_tag but for action
                                    if current_policy_type in ["security_pre_rules", "security_post_rules"] and device_type.lower() == "panorama":
                                        rulebase = "pre-rulebase" if current_policy_type == "security_pre_rules" else "post-rulebase"
                                        device_group = context_kwargs.get("device_group", "shared")

                                        if device_group == "shared":
                                            xpath = f'/config/shared/{rulebase}/security/rules/entry[@name="{policy_name}"]'
                                        else:
                                            xpath = f'/config/devices/entry[@name="localhost.localdomain"]/device-group/entry[@name="{device_group}"]/{rulebase}/security/rules/entry[@name="{policy_name}"]'
                                    elif current_policy_type in ["nat_pre_rules", "nat_post_rules"] and device_type.lower() == "panorama":
                                        # For Panorama NAT policies
                                        rulebase = "pre-rulebase" if current_policy_type == "nat_pre_rules" else "post-rulebase"
                                        device_group = context_kwargs.get("device_group", "shared")

                                        if device_group == "shared":
                                            xpath = f'/config/shared/{rulebase}/nat/rules/entry[@name="{policy_name}"]'
                                        else:
                                            xpath = f'/config/devices/entry[@name="localhost.localdomain"]/device-group/entry[@name="{device_group}"]/{rulebase}/nat/rules/entry[@name="{policy_name}"]'
                                    else:
                                        from panflow.core.xpath_resolver import get_policy_xpath
                                        xpath = get_policy_xpath(
                                            current_policy_type,
                                            device_type,
                                            context_type,
                                            xml_config.version,
                                            name=policy_name,
                                            **context_kwargs
                                        )

                                    policy_elem = tree.xpath(xpath)
                                    if policy_elem and len(policy_elem) > 0:
                                        policy = policy_elem[0]

                                        # Find or create action element
                                        action_elem = policy.find('./action')
                                        if action_elem is None:
                                            action_elem = etree.SubElement(policy, 'action')

                                        # Update the action
                                        old_value = action_elem.text
                                        action_elem.text = value
                                        updated.append(policy_name)
                                        logger.info(f"Changed action from '{old_value}' to '{value}' for policy '{policy_name}'")
                                    else:
                                        logger.warning(f"Policy '{policy_name}' not found at xpath: {xpath}")
                                except Exception as e:
                                    logger.error(f"Error setting action for policy '{policy_name}': {str(e)}")
                        elif operation == "enable":
                            updated = []
                            for policy_name in policy_names:
                                try:
                                    # Similar approach for enabling policies
                                    if current_policy_type in ["security_pre_rules", "security_post_rules"] and device_type.lower() == "panorama":
                                        rulebase = "pre-rulebase" if current_policy_type == "security_pre_rules" else "post-rulebase"
                                        device_group = context_kwargs.get("device_group", "shared")

                                        if device_group == "shared":
                                            xpath = f'/config/shared/{rulebase}/security/rules/entry[@name="{policy_name}"]'
                                        else:
                                            xpath = f'/config/devices/entry[@name="localhost.localdomain"]/device-group/entry[@name="{device_group}"]/{rulebase}/security/rules/entry[@name="{policy_name}"]'
                                    elif current_policy_type in ["nat_pre_rules", "nat_post_rules"] and device_type.lower() == "panorama":
                                        # For Panorama NAT policies
                                        rulebase = "pre-rulebase" if current_policy_type == "nat_pre_rules" else "post-rulebase"
                                        device_group = context_kwargs.get("device_group", "shared")

                                        if device_group == "shared":
                                            xpath = f'/config/shared/{rulebase}/nat/rules/entry[@name="{policy_name}"]'
                                        else:
                                            xpath = f'/config/devices/entry[@name="localhost.localdomain"]/device-group/entry[@name="{device_group}"]/{rulebase}/nat/rules/entry[@name="{policy_name}"]'
                                    else:
                                        from panflow.core.xpath_resolver import get_policy_xpath
                                        xpath = get_policy_xpath(
                                            current_policy_type,
                                            device_type,
                                            context_type,
                                            xml_config.version,
                                            name=policy_name,
                                            **context_kwargs
                                        )

                                    policy_elem = tree.xpath(xpath)
                                    if policy_elem and len(policy_elem) > 0:
                                        policy = policy_elem[0]

                                        # Remove the disabled element if it exists
                                        disabled_elem = policy.find('./disabled')
                                        if disabled_elem is not None:
                                            policy.remove(disabled_elem)
                                            updated.append(policy_name)
                                            logger.info(f"Enabled policy '{policy_name}'")
                                    else:
                                        logger.warning(f"Policy '{policy_name}' not found at xpath: {xpath}")
                                except Exception as e:
                                    logger.error(f"Error enabling policy '{policy_name}': {str(e)}")
                        elif operation == "disable":
                            updated = []
                            for policy_name in policy_names:
                                try:
                                    # Similar approach for disabling policies
                                    if current_policy_type in ["security_pre_rules", "security_post_rules"] and device_type.lower() == "panorama":
                                        rulebase = "pre-rulebase" if current_policy_type == "security_pre_rules" else "post-rulebase"
                                        device_group = context_kwargs.get("device_group", "shared")

                                        if device_group == "shared":
                                            xpath = f'/config/shared/{rulebase}/security/rules/entry[@name="{policy_name}"]'
                                        else:
                                            xpath = f'/config/devices/entry[@name="localhost.localdomain"]/device-group/entry[@name="{device_group}"]/{rulebase}/security/rules/entry[@name="{policy_name}"]'
                                    elif current_policy_type in ["nat_pre_rules", "nat_post_rules"] and device_type.lower() == "panorama":
                                        # For Panorama NAT policies
                                        rulebase = "pre-rulebase" if current_policy_type == "nat_pre_rules" else "post-rulebase"
                                        device_group = context_kwargs.get("device_group", "shared")

                                        if device_group == "shared":
                                            xpath = f'/config/shared/{rulebase}/nat/rules/entry[@name="{policy_name}"]'
                                        else:
                                            xpath = f'/config/devices/entry[@name="localhost.localdomain"]/device-group/entry[@name="{device_group}"]/{rulebase}/nat/rules/entry[@name="{policy_name}"]'
                                    else:
                                        from panflow.core.xpath_resolver import get_policy_xpath
                                        xpath = get_policy_xpath(
                                            current_policy_type,
                                            device_type,
                                            context_type,
                                            xml_config.version,
                                            name=policy_name,
                                            **context_kwargs
                                        )

                                    policy_elem = tree.xpath(xpath)
                                    if policy_elem and len(policy_elem) > 0:
                                        policy = policy_elem[0]

                                        # Find or create disabled element
                                        disabled_elem = policy.find('./disabled')
                                        if disabled_elem is None:
                                            disabled_elem = etree.SubElement(policy, 'disabled')
                                            disabled_elem.text = "yes"
                                            updated.append(policy_name)
                                            logger.info(f"Disabled policy '{policy_name}'")
                                    else:
                                        logger.warning(f"Policy '{policy_name}' not found at xpath: {xpath}")
                                except Exception as e:
                                    logger.error(f"Error disabling policy '{policy_name}': {str(e)}")
                        elif operation == "enable_logging":
                            # Handle enable_logging operation directly
                            updated = []
                            for policy_name in policy_names:
                                try:
                                    # Similar approach for enabling logging
                                    if current_policy_type in ["security_pre_rules", "security_post_rules"] and device_type.lower() == "panorama":
                                        rulebase = "pre-rulebase" if current_policy_type == "security_pre_rules" else "post-rulebase"
                                        device_group = context_kwargs.get("device_group", "shared")

                                        if device_group == "shared":
                                            xpath = f'/config/shared/{rulebase}/security/rules/entry[@name="{policy_name}"]'
                                        else:
                                            xpath = f'/config/devices/entry[@name="localhost.localdomain"]/device-group/entry[@name="{device_group}"]/{rulebase}/security/rules/entry[@name="{policy_name}"]'
                                    elif current_policy_type in ["nat_pre_rules", "nat_post_rules"] and device_type.lower() == "panorama":
                                        # For Panorama NAT policies
                                        rulebase = "pre-rulebase" if current_policy_type == "nat_pre_rules" else "post-rulebase"
                                        device_group = context_kwargs.get("device_group", "shared")

                                        if device_group == "shared":
                                            xpath = f'/config/shared/{rulebase}/nat/rules/entry[@name="{policy_name}"]'
                                        else:
                                            xpath = f'/config/devices/entry[@name="localhost.localdomain"]/device-group/entry[@name="{device_group}"]/{rulebase}/nat/rules/entry[@name="{policy_name}"]'
                                    else:
                                        from panflow.core.xpath_resolver import get_policy_xpath
                                        xpath = get_policy_xpath(
                                            current_policy_type,
                                            device_type,
                                            context_type,
                                            xml_config.version,
                                            name=policy_name,
                                            **context_kwargs
                                        )

                                    policy_elem = tree.xpath(xpath)
                                    if policy_elem and len(policy_elem) > 0:
                                        policy = policy_elem[0]

                                        # Create or update log-start and log-end
                                        for log_type in ['log-start', 'log-end']:
                                            log_elem = policy.find(f'./{log_type}')
                                            if log_elem is None:
                                                log_elem = etree.SubElement(policy, log_type)
                                                log_elem.text = "yes"
                                                updated.append(policy_name)
                                                logger.info(f"Enabled {log_type} for policy '{policy_name}'")
                                    else:
                                        logger.warning(f"Policy '{policy_name}' not found at xpath: {xpath}")
                                except Exception as e:
                                    logger.error(f"Error enabling logging for policy '{policy_name}': {str(e)}")
                        elif operation == "disable_logging":
                            # Handle disable_logging operation directly
                            updated = []
                            for policy_name in policy_names:
                                try:
                                    # Similar approach for disabling logging
                                    if current_policy_type in ["security_pre_rules", "security_post_rules"] and device_type.lower() == "panorama":
                                        rulebase = "pre-rulebase" if current_policy_type == "security_pre_rules" else "post-rulebase"
                                        device_group = context_kwargs.get("device_group", "shared")

                                        if device_group == "shared":
                                            xpath = f'/config/shared/{rulebase}/security/rules/entry[@name="{policy_name}"]'
                                        else:
                                            xpath = f'/config/devices/entry[@name="localhost.localdomain"]/device-group/entry[@name="{device_group}"]/{rulebase}/security/rules/entry[@name="{policy_name}"]'
                                    elif current_policy_type in ["nat_pre_rules", "nat_post_rules"] and device_type.lower() == "panorama":
                                        # For Panorama NAT policies
                                        rulebase = "pre-rulebase" if current_policy_type == "nat_pre_rules" else "post-rulebase"
                                        device_group = context_kwargs.get("device_group", "shared")

                                        if device_group == "shared":
                                            xpath = f'/config/shared/{rulebase}/nat/rules/entry[@name="{policy_name}"]'
                                        else:
                                            xpath = f'/config/devices/entry[@name="localhost.localdomain"]/device-group/entry[@name="{device_group}"]/{rulebase}/nat/rules/entry[@name="{policy_name}"]'
                                    else:
                                        from panflow.core.xpath_resolver import get_policy_xpath
                                        xpath = get_policy_xpath(
                                            current_policy_type,
                                            device_type,
                                            context_type,
                                            xml_config.version,
                                            name=policy_name,
                                            **context_kwargs
                                        )

                                    policy_elem = tree.xpath(xpath)
                                    if policy_elem and len(policy_elem) > 0:
                                        policy = policy_elem[0]

                                        # Find and remove or set log-start and log-end
                                        for log_type in ['log-start', 'log-end']:
                                            log_elem = policy.find(f'./{log_type}')
                                            if log_elem is not None:
                                                log_elem.text = "no"
                                                updated.append(policy_name)
                                                logger.info(f"Disabled {log_type} for policy '{policy_name}'")
                                    else:
                                        logger.warning(f"Policy '{policy_name}' not found at xpath: {xpath}")
                                except Exception as e:
                                    logger.error(f"Error disabling logging for policy '{policy_name}': {str(e)}")
                        else:
                            logger.warning(f"Unknown operation: {operation}")
                            continue

                        # Remove duplicates from the updated list
                        if isinstance(updated, list):
                            updated = list(set(updated))

                        # Add policy type information for "all" policy types
                        if policy_type == "all":
                            updated_with_type = []
                            for policy_name in updated:
                                updated_with_type.append({"name": policy_name, "policy_type": current_policy_type})
                            all_updated_policies.extend(updated_with_type)
                        else:
                            all_updated_policies.extend([{"name": name} for name in updated])

                    # Save the updated configuration if not in dry run mode
                    if not dry_run:
                        # Save the tree to the output file
                        tree.write(output_file, pretty_print=True, encoding="UTF-8", xml_declaration=True)
                        logger.info(f"Updated configuration saved to {output_file}")

                    # Create a summary
                    updated_policies = all_updated_policies
                    updated_count = len(updated_policies)

                    # Get operation description
                    operation_desc = {
                        "enable": "Enabled",
                        "disable": "Disabled",
                        "add_tag": "Added tag",
                        "set_action": "Updated action to",
                        "enable_logging": "Enabled logging for",
                        "disable_logging": "Disabled logging for",
                    }.get(operation, operation)

                    # Format policies for better display
                    formatted_policies = []
                    for policy in updated_policies:
                        if isinstance(policy, dict):
                            policy_name = policy.get("name", "unnamed")
                            policy_type_str = policy.get("policy_type", policy_type)
                            formatted_policies.append(f"{policy_name} ({policy_type_str})")
                        else:
                            formatted_policies.append(str(policy))

                    message = f"{operation_desc} {updated_count} {policy_type} policies"
                    if updated_count > 0:
                        # Add details about what was updated if available
                        if operation == "add_tag":
                            message += f" with tag '{value}'"
                        elif operation == "set_action":
                            message += f" to '{value}'"

                    if dry_run:
                        message = f"Would {operation_desc.lower()} {updated_count} {policy_type} policies (dry run)"

                    return {
                        "message": message,
                        "count": updated_count,
                        "operation": operation,
                        "value": value,
                        "policy_type": policy_type,
                        "updated_policies": updated_policies,
                        "formatted_policies": formatted_policies,  # Add formatted policies for better display
                        "output_file": output_file,
                    }

                except Exception as e:
                    logger.error(f"Error in bulk update operation: {str(e)}")
                    raise ValueError(f"Error in bulk update operation: {str(e)}")
            else:
                raise ValueError(f"Unknown command: {command_name}")

    def get_suggestions(self, query: str) -> List[str]:
        """
        Get suggestions for ambiguous queries.

        Args:
            query: The natural language query

        Returns:
            List of suggested queries
        """
        # TODO: Implement suggestions based on query
        return [
            "Try asking to 'cleanup unused address objects'",
            "Try asking to 'show all disabled security rules'",
            "Try asking to 'find duplicate address objects'",
            "Try asking to 'cleanup duplicate service objects'",
        ]
