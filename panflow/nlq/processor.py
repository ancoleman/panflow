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
                model = os.environ.get("PANFLOW_AI_MODEL", "gpt-3.5-turbo" if provider == "openai" else "claude-3-haiku-20240307")
                
                # Try to find API key based on provider
                if provider == "openai":
                    api_key = os.environ.get("OPENAI_API_KEY")
                elif provider == "anthropic":
                    api_key = os.environ.get("ANTHROPIC_API_KEY")
                
                # Initialize the AI processor
                self.ai_processor = AIProcessor(
                    api_key=api_key,
                    model=model,
                    provider=provider,
                    use_local_fallback=True
                )
                
                # Log AI availability
                if self.ai_processor.available():
                    logger.info(f"AI processing enabled using {provider} ({model})")
                else:
                    logger.info(f"AI processing not available, falling back to pattern-based processing")
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
    
    def process(self, query: str, config_file: str, output_file: Optional[str] = None) -> Dict[str, Any]:
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
        is_view_query = any(keyword in query.lower() for keyword in ["show", "list", "display", "find", "get", "what"])
        
        # Try AI processing first if available
        if self.ai_available():
            try:
                ai_result = self.ai_processor.process_query(query)
                intent = ai_result.get("intent")
                entities = ai_result.get("entities", {})
                confidence = ai_result.get("confidence", 0.0)
                
                logger.debug(f"AI processing result: intent={intent}, confidence={confidence:.2f}, entities={entities}")
                
                # If this is a cleanup intent but seems to be a view query based on keywords, adjust the intent
                if intent and intent.startswith("cleanup_") and is_view_query:
                    logger.info(f"Query seems to be a view operation but got cleanup intent. Adjusting intent from {intent}")
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
                    
                    # Map to command arguments
                    logger.info(f"Mapping intent '{intent}' to command args with config_file={config_file}, output_file={output_file}")
                    command_args = self.command_mapper.map(intent, entities, config_file, output_file)
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
                            "processing": "ai"
                        }
                    except Exception as e:
                        logger.error(f"Error executing command: {e}", exc_info=True)
                        return {
                            "success": False,
                            "message": f"Error executing command: {str(e)}",
                            "intent": intent,
                            "entities": entities,
                            "command": command_args,
                            "processing": "ai"
                        }
                else:
                    logger.info(f"AI processing yielded low confidence ({confidence:.2f}), falling back to pattern-based")
            except Exception as e:
                logger.error(f"Error in AI processing, falling back to pattern-based: {e}", exc_info=True)
        
        # Fall back to pattern-based processing
        # Identify the intent
        intent, confidence = self.intent_parser.parse(query)
        logger.debug(f"Pattern-based intent detection: {intent} (confidence: {confidence:.2f})")
        
        # If this is a cleanup intent but seems to be a view query based on keywords, adjust the intent
        if intent and intent.startswith("cleanup_") and is_view_query:
            logger.info(f"Query seems to be a view operation but got cleanup intent. Adjusting intent from {intent}")
            if intent == "cleanup_unused_objects":
                intent = "list_unused_objects"
            elif intent == "cleanup_disabled_policies":
                intent = "list_disabled_policies"
        
        # Extract entities
        entities = self.entity_extractor.extract(query)
        logger.debug(f"Pattern-based entity extraction: {entities}")
        
        # If we couldn't determine the intent with sufficient confidence, return early
        if confidence < 0.6:
            return {
                "success": False,
                "message": f"Not confident in understanding the request (confidence: {confidence:.2f})",
                "suggestions": self.get_suggestions(query),
                "intent": intent,
                "entities": entities,
                "processing": "pattern"
            }
        
        # Map to command arguments
        logger.info(f"Mapping intent '{intent}' to command args with config_file={config_file}, output_file={output_file}")
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
                "processing": "pattern"
            }
        except Exception as e:
            logger.error(f"Error executing command: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error executing command: {str(e)}",
                "intent": intent,
                "entities": entities,
                "command": command_args,
                "processing": "pattern"
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
        
        # For viewing unused objects (no cleanup)
        if command_name == "list_unused_objects":
            from panflow import PANFlowConfig
            from panflow.reporting import generate_unused_objects_report
            
            # Extract parameters
            config_file = command_args.get("config")
            # Handle both "object_type" and "type" parameters
            if "object_type" in command_args:
                object_type = command_args["object_type"]
            elif "type" in command_args:
                object_type = command_args["type"][0] if isinstance(command_args["type"], list) else command_args["type"]
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
                    device_groups = xml_config.tree.xpath('/config/devices/entry[@name="localhost.localdomain"]/device-group/entry/@name')
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
                **context_kwargs
            )
            
            # Return a simplified result
            unused_count = len(report.get('unused_objects', []))
            logger.info(f"Found {unused_count} unused {object_type} objects")
            return {
                "message": f"Found {unused_count} unused {object_type} objects",
                "count": unused_count,
                "unused_objects": [obj['name'] for obj in report.get('unused_objects', [])]
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
                policy_type = command_args["type"][0] if isinstance(command_args["type"], list) else command_args["type"]
            else:
                policy_type = "security_rules"  # Default
                
            logger.info(f"Analyzing {policy_type} for disabled policies...")
            
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
                    device_groups = xml_config.tree.xpath('/config/devices/entry[@name="localhost.localdomain"]/device-group/entry/@name')
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
            
            # For Panorama, we need to handle pre and post rulebases separately
            disabled_policies = []
            device_type = xml_config.device_type.lower()
            
            if device_type == "panorama":
                # Device group is required for Panorama
                device_group = context_kwargs.get("device_group")
                if device_group:
                    # Check pre-rules
                    pre_xpath = f"/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='{device_group}']/pre-rulebase/security/rules/entry[disabled='yes']"
                    pre_disabled_elements = xml_config.tree.xpath(pre_xpath)
                    pre_disabled_rules = [elem.get('name') for elem in pre_disabled_elements if elem.get('name')]
                    disabled_policies.extend(pre_disabled_rules)
                    
                    # Check post-rules
                    post_xpath = f"/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='{device_group}']/post-rulebase/security/rules/entry[disabled='yes']"
                    post_disabled_elements = xml_config.tree.xpath(post_xpath)
                    post_disabled_rules = [elem.get('name') for elem in post_disabled_elements if elem.get('name')]
                    disabled_policies.extend(post_disabled_rules)
            else:
                # For firewall, check the main rulebase
                vsys = context_kwargs.get("vsys", "vsys1")
                disabled_xpath = f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{vsys}']/rulebase/security/rules/entry[disabled='yes']"
                disabled_elements = xml_config.tree.xpath(disabled_xpath)
                disabled_policies = [elem.get('name') for elem in disabled_elements if elem.get('name')]
            
            # Return a simplified result
            disabled_count = len(disabled_policies)
            logger.info(f"Found {disabled_count} disabled {policy_type}")
            return {
                "message": f"Found {disabled_count} disabled {policy_type}",
                "count": disabled_count,
                "disabled_policies": disabled_policies
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
                command_args["context"] = "device_group" if command_args["device_type"].lower() == "panorama" else "vsys"
            
            if "vsys" not in command_args and command_args["context"] == "vsys":
                command_args["vsys"] = "vsys1"
                
            # Make sure device_group is set for Panorama configs
            if command_args["device_type"].lower() == "panorama" and "device_group" not in command_args:
                # Initialize config if we haven't already
                if 'xml_config' not in locals():
                    from panflow import PANFlowConfig
                    xml_config = PANFlowConfig(config_file=command_args["config"])
                
                # Get available device groups
                device_groups = xml_config.tree.xpath('/config/devices/entry[@name="localhost.localdomain"]/device-group/entry/@name')
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
            temp_report_file = os.path.join(tempfile.gettempdir(), f"panflow_cleanup_report_{os.getpid()}.json")
            command_args["report_file"] = temp_report_file
                
            # Make sure we have a valid output file
            if "output" not in command_args or command_args["output"] is None:
                # Log the issue
                logger.error("No output file specified for cleanup operation")
                return {
                    "message": "Cannot cleanup unused objects without an output file. Please specify an output file with --output.",
                    "success": False
                }
                
            # Log the parameters for debugging
            logger.debug(f"Calling cleanup_unused_objects with parameters: {command_args}")
            
            # Get the object types
            object_types = command_args.get("object_types", ["address"])
            logger.info(f"Cleaning up unused {', '.join(object_types)} objects...")
                
            # Call the cleanup function
            cleanup_unused_objects(**command_args)
            
            # Read the report file to get the results
            if os.path.exists(temp_report_file):
                try:
                    with open(temp_report_file, 'r') as f:
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
                        "details": report_data
                    }
                except Exception as e:
                    logger.error(f"Error reading cleanup report: {e}")
            
            # Fallback if report can't be read
            return {
                "message": f"Cleaned up unused {', '.join(object_types)} objects",
                "output_file": command_args["output"]
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
                command_args["context"] = "device_group" if command_args["device_type"].lower() == "panorama" else "vsys"
            
            if "vsys" not in command_args and command_args["context"] == "vsys":
                command_args["vsys"] = "vsys1"
                
            # Make sure device_group is set for Panorama configs
            if command_args["device_type"].lower() == "panorama" and "device_group" not in command_args:
                # Initialize config if we haven't already
                if 'xml_config' not in locals():
                    from panflow import PANFlowConfig
                    xml_config = PANFlowConfig(config_file=command_args["config"])
                
                # Get available device groups
                device_groups = xml_config.tree.xpath('/config/devices/entry[@name="localhost.localdomain"]/device-group/entry/@name')
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
            temp_report_file = os.path.join(tempfile.gettempdir(), f"panflow_cleanup_report_{os.getpid()}.json")
            command_args["report_file"] = temp_report_file
                
            # Make sure we have a valid output file
            if "output" not in command_args or command_args["output"] is None:
                # Log the issue
                logger.error("No output file specified for cleanup operation")
                return {
                    "message": "Cannot cleanup disabled policies without an output file. Please specify an output file with --output.",
                    "success": False
                }
                
            # Log the parameters for debugging
            logger.debug(f"Calling cleanup_disabled_policies with parameters: {command_args}")
            
            # Get the policy types
            policy_types = command_args.get("policy_types", ["security_rules"])
            logger.info(f"Cleaning up disabled {', '.join(policy_types)} policies...")
                
            # Call the cleanup function
            cleanup_disabled_policies(**command_args)
            
            # Read the report file to get the results
            if os.path.exists(temp_report_file):
                try:
                    with open(temp_report_file, 'r') as f:
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
                        "details": report_data
                    }
                except Exception as e:
                    logger.error(f"Error reading cleanup report: {e}")
            
            # Fallback if report can't be read
            return {
                "message": f"Cleaned up disabled {', '.join(policy_types)} policies",
                "output_file": command_args["output"]
            }
        
        # Add more commands as needed
        elif command_name == "find_duplicates":
            from panflow import PANFlowConfig
            from panflow.core.deduplication import DeduplicationEngine
            
            # Extract parameters
            config_file = command_args.get("config")
            # Handle both "object_type" and "type" parameters
            if "object_type" in command_args:
                object_type = command_args["object_type"]
            elif "type" in command_args:
                object_type = command_args["type"][0] if isinstance(command_args["type"], list) else command_args["type"]
            else:
                object_type = "address"  # Default
                
            logger.info(f"Analyzing {object_type} objects for duplicates...")
            
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
                    device_groups = xml_config.tree.xpath('/config/devices/entry[@name="localhost.localdomain"]/device-group/entry/@name')
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
                **context_kwargs
            )
            
            # Find duplicates based on object type
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
            
            # Return a simplified result
            logger.info(f"Found {total_duplicates} duplicate {object_type} objects across {unique_values} values")
            return {
                "message": f"Found {total_duplicates} duplicate {object_type} objects across {unique_values} values",
                "count": total_duplicates,
                "unique_values": unique_values,
                "duplicates": duplicates
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
            "Try asking to 'find duplicate address objects'"
        ]