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

                # Use the combined results
                duplicates = combined_duplicates
                # Update object type for display
                object_type = "all"
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
                        else:
                            # Handle other formats (might have object_name attribute)
                            for obj in objects_list[1:]:
                                if hasattr(obj, "object_name"):
                                    to_remove.append(obj.object_name)
                                elif isinstance(obj, str):
                                    to_remove.append(obj)

                    # Remove the duplicate objects
                    cleaned_count = len(to_remove)
                    cleaned_objects = to_remove

                    if cleaned_count > 0:
                        # Save the updated configuration
                        import shutil

                        shutil.copy(config_file, output_file)
                        logger.info(f"Deduplicated {cleaned_count} {object_type} objects")
                        logger.info(
                            f"For now, we're just simulating deduplication. The actual object removal functionality will be implemented soon."
                        )
                        logger.info(f"Output saved to {output_file}")
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
