"""
AI-powered natural language processing module for PANFlow.

This module provides integration with language models for enhanced
natural language understanding capabilities.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
import requests

logger = logging.getLogger("panflow.nlq.ai")

class AIProcessor:
    """
    AI processor for natural language queries using language models.
    
    This class handles processing of natural language queries through
    integration with AI language models, either through API calls
    or local model inference.
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 model: str = "gpt-3.5-turbo",
                 provider: str = "openai",
                 use_local_fallback: bool = True):
        """
        Initialize the AI processor.
        
        Args:
            api_key: API key for the language model service
            model: Model identifier to use
            provider: Provider to use (openai, anthropic, etc.)
            use_local_fallback: Whether to fall back to local processing if API fails
        """
        self.api_key = api_key or os.environ.get(f"{provider.upper()}_API_KEY")
        self.model = model
        self.provider = provider
        self.use_local_fallback = use_local_fallback
        
        # Load command reference for context
        self.command_reference = self._load_command_reference()
        
        # Initialize provider-specific clients
        if provider == "openai" and self.api_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info(f"Initialized OpenAI client with model {model}")
            except ImportError:
                logger.warning("OpenAI package not installed. Install with 'pip install openai'")
                self.client = None
            except Exception as e:
                logger.error(f"Error initializing OpenAI client: {e}")
                self.client = None
        elif provider == "anthropic" and self.api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info(f"Initialized Anthropic client with model {model}")
            except ImportError:
                logger.warning("Anthropic package not installed. Install with 'pip install anthropic'")
                self.client = None
            except Exception as e:
                logger.error(f"Error initializing Anthropic client: {e}")
                self.client = None
        else:
            self.client = None
            if self.api_key:
                logger.warning(f"Unsupported provider: {provider}")
            else:
                logger.info(f"No API key provided for {provider}, will use local fallback")
    
    def _load_command_reference(self) -> Dict[str, Any]:
        """
        Load the command reference information for context.
        
        Returns:
            Dictionary with command reference information
        """
        # Define basic command reference
        command_ref = {
            "commands": [
                {
                    "name": "cleanup_unused_objects",
                    "description": "Find and remove unused objects from the configuration",
                    "parameters": {
                        "object_type": {
                            "description": "Type of object to clean up",
                            "required": True,
                            "options": ["address", "service", "tag", "address-group", "service-group"]
                        },
                        "dry_run": {
                            "description": "Preview changes without modifying the configuration",
                            "required": False,
                            "type": "boolean"
                        },
                        "context": {
                            "description": "Context to operate in",
                            "required": False,
                            "options": ["shared", "device_group", "vsys", "template"]
                        }
                    },
                    "examples": [
                        "cleanup unused address objects",
                        "remove all unused services but don't make changes",
                        "delete unused objects in device group DG1"
                    ]
                },
                {
                    "name": "cleanup_disabled_policies",
                    "description": "Find and remove disabled policies from the configuration",
                    "parameters": {
                        "policy_type": {
                            "description": "Type of policy to clean up",
                            "required": True,
                            "options": ["security_rules", "nat_rules", "security_pre_rules", "security_post_rules"]
                        },
                        "dry_run": {
                            "description": "Preview changes without modifying the configuration",
                            "required": False,
                            "type": "boolean"
                        },
                        "context": {
                            "description": "Context to operate in",
                            "required": False,
                            "options": ["shared", "device_group", "vsys", "template"]
                        }
                    },
                    "examples": [
                        "cleanup disabled security rules",
                        "remove all inactive policies",
                        "delete disabled rules in vsys1"
                    ]
                },
                {
                    "name": "list_unused_objects",
                    "description": "Generate a report of unused objects",
                    "parameters": {
                        "object_type": {
                            "description": "Type of object to report on",
                            "required": True,
                            "options": ["address", "service", "tag", "address-group", "service-group"]
                        },
                        "context": {
                            "description": "Context to operate in",
                            "required": False,
                            "options": ["shared", "device_group", "vsys", "template"]
                        }
                    },
                    "examples": [
                        "show me all unused address objects",
                        "list unused services",
                        "find unreferenced objects in device group DG1"
                    ]
                },
                {
                    "name": "list_disabled_policies",
                    "description": "Generate a report of disabled policies",
                    "parameters": {
                        "policy_type": {
                            "description": "Type of policy to report on",
                            "required": True,
                            "options": ["security_rules", "nat_rules", "security_pre_rules", "security_post_rules"]
                        },
                        "context": {
                            "description": "Context to operate in",
                            "required": False,
                            "options": ["shared", "device_group", "vsys", "template"]
                        }
                    },
                    "examples": [
                        "show me all disabled security rules",
                        "list inactive policies",
                        "find disabled rules in vsys1"
                    ]
                },
                {
                    "name": "find_duplicates",
                    "description": "Find duplicate objects in the configuration",
                    "parameters": {
                        "object_type": {
                            "description": "Type of object to find duplicates for",
                            "required": True,
                            "options": ["address", "service", "tag", "address-group", "service-group"]
                        },
                        "context": {
                            "description": "Context to operate in",
                            "required": False,
                            "options": ["shared", "device_group", "vsys", "template"]
                        }
                    },
                    "examples": [
                        "find duplicate address objects",
                        "show me all duplicate services",
                        "identify duplicates in device group DG1"
                    ]
                }
            ]
        }
        
        return command_ref
    
    def available(self) -> bool:
        """
        Check if the AI processing is available.
        
        Returns:
            True if AI processing is available, False otherwise
        """
        return self.client is not None
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a natural language query using AI.
        
        Args:
            query: The natural language query to process
            
        Returns:
            Dictionary with intent and entities
        """
        if not self.available():
            logger.warning("AI processing not available, returning empty result")
            return {"intent": None, "entities": {}, "confidence": 0.0}
        
        try:
            if self.provider == "openai":
                return self._process_with_openai(query)
            elif self.provider == "anthropic":
                return self._process_with_anthropic(query)
            else:
                logger.warning(f"Unsupported provider: {self.provider}")
                return {"intent": None, "entities": {}, "confidence": 0.0}
        except Exception as e:
            logger.error(f"Error processing query with AI: {e}", exc_info=True)
            return {"intent": None, "entities": {}, "confidence": 0.0}
    
    def _process_with_openai(self, query: str) -> Dict[str, Any]:
        """
        Process a query using OpenAI's API.
        
        Args:
            query: The natural language query
            
        Returns:
            Dictionary with intent and entities
        """
        # Create the prompt
        system_prompt = f"""You are an AI assistant for the PANFlow CLI tool, which manages Palo Alto Networks firewall configurations. 
Your task is to translate natural language queries into structured commands.

Here is information about the available commands:
{json.dumps(self.command_reference, indent=2)}

Based on the user's query, identify:
1. The intent (which command they want to run)
2. The parameters/entities needed for that command
3. Your confidence level in this interpretation (0.0 to 1.0)

Respond with a JSON object containing:
- intent: The command name
- entities: An object containing all identified parameters
- confidence: A number from 0.0 to 1.0 indicating your confidence

Only output valid JSON without any other text.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            # Parse the response
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Ensure the response has the required fields
            if "intent" not in result or "entities" not in result:
                logger.warning(f"Unexpected response format from OpenAI: {result}")
                return {"intent": None, "entities": {}, "confidence": 0.0}
            
            # Add dry_run entity if it's indicated in the query
            if "dry_run" not in result["entities"]:
                dry_run_phrases = ["dry run", "preview", "without making changes", "don't apply", "simulate", "just show"]
                if any(phrase in query.lower() for phrase in dry_run_phrases):
                    result["entities"]["dry_run"] = True
            
            return result
        
        except Exception as e:
            logger.error(f"Error with OpenAI API: {e}", exc_info=True)
            return {"intent": None, "entities": {}, "confidence": 0.0}
    
    def _process_with_anthropic(self, query: str) -> Dict[str, Any]:
        """
        Process a query using Anthropic's API.
        
        Args:
            query: The natural language query
            
        Returns:
            Dictionary with intent and entities
        """
        # Create the prompt
        system_prompt = f"""You are an AI assistant for the PANFlow CLI tool, which manages Palo Alto Networks firewall configurations. 
Your task is to translate natural language queries into structured commands.

Here is information about the available commands:
{json.dumps(self.command_reference, indent=2)}

Based on the user's query, identify:
1. The intent (which command they want to run)
2. The parameters/entities needed for that command
3. Your confidence level in this interpretation (0.0 to 1.0)

Respond with a JSON object containing:
- intent: The command name
- entities: An object containing all identified parameters
- confidence: A number from 0.0 to 1.0 indicating your confidence

Only output valid JSON without any other text.
"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": query}
                ],
                temperature=0.2
            )
            
            # Parse the response
            content = response.content[0].text
            # Extract JSON from the response
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            result = json.loads(content)
            
            # Ensure the response has the required fields
            if "intent" not in result or "entities" not in result:
                logger.warning(f"Unexpected response format from Anthropic: {result}")
                return {"intent": None, "entities": {}, "confidence": 0.0}
            
            # Add dry_run entity if it's indicated in the query
            if "dry_run" not in result["entities"]:
                dry_run_phrases = ["dry run", "preview", "without making changes", "don't apply", "simulate", "just show"]
                if any(phrase in query.lower() for phrase in dry_run_phrases):
                    result["entities"]["dry_run"] = True
            
            return result
        
        except Exception as e:
            logger.error(f"Error with Anthropic API: {e}", exc_info=True)
            return {"intent": None, "entities": {}, "confidence": 0.0}