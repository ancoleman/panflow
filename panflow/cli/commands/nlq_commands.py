"""
Natural Language Query commands for PANFlow CLI.

This module provides CLI commands for natural language interaction with PANFlow.
"""

import logging
import os
import json
from typing import Optional, List, Dict, Any
import typer

from ..app import app
from ..common import ConfigOptions

# Import NLQ processor
from panflow.nlq import NLQProcessor

# Create nlq app
nlq_app = typer.Typer(help="Natural language query interface for PANFlow")

# Register with main app
app.add_typer(nlq_app, name="nlq")

# Get logger
logger = logging.getLogger("panflow.cli.nlq")


@nlq_app.command("query")
def process_query(
    query: str = typer.Argument(..., help="Natural language query"),
    config: str = ConfigOptions.config_file(),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for updates (required for cleanup/modify operations, not needed for view-only queries)",
    ),
    dry_run: bool = ConfigOptions.dry_run(),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode"),
    format: str = typer.Option("text", "--format", "-f", help="Output format (text, json, table, csv, yaml, html)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
    use_ai: bool = typer.Option(True, "--ai/--no-ai", help="Use AI for processing if available"),
    ai_provider: Optional[str] = typer.Option(
        None, "--ai-provider", help="AI provider to use (openai, anthropic)"
    ),
    ai_model: Optional[str] = typer.Option(None, "--ai-model", help="AI model to use"),
):
    """
    Process a natural language query against the configuration.

    Examples:

        # Find unused address objects in dry run mode
        python cli.py nlq query "cleanup unused address objects, but just show what would be removed"

        # Remove disabled security policies
        python cli.py nlq query "cleanup all disabled security rules" --config firewall.xml --output cleaned.xml

        # Show a report of unused service objects
        python cli.py nlq query "show me all unused service objects" --config panorama.xml

        # Force using pattern-based processing instead of AI
        python cli.py nlq query "find duplicate address objects" --no-ai

        # Specify a different AI provider and model
        python cli.py nlq query "show me unused objects" --ai-provider anthropic --ai-model claude-3-haiku-20240307
    """
    try:
        # Set environment variables for AI processing if specified
        if ai_provider:
            os.environ["PANFLOW_AI_PROVIDER"] = ai_provider
        if ai_model:
            os.environ["PANFLOW_AI_MODEL"] = ai_model

        # Initialize the NLQ processor with AI setting
        processor = NLQProcessor(use_ai=use_ai)

        # Configure logging to avoid duplicate output
        # Reduce log level for most logs except important ones
        old_level = logging.getLogger("panflow").level

        if not verbose:
            # Keep specific loggers at INFO level for important information
            for logger_name in ["panflow.nlq", "panflow.core.config_loader"]:
                logging.getLogger(logger_name).setLevel(logging.INFO)

            # Set all other panflow loggers to WARNING
            logging.getLogger("panflow").setLevel(logging.WARNING)

        # Process the query
        if not verbose:
            typer.echo("Processing query...")

        # If dry_run is specified in the command line, add it to the query
        if dry_run:
            # Add "dry run" to the end of the query if it doesn't already contain a dry run indicator
            if not any(
                phrase in query.lower()
                for phrase in ["dry run", "preview", "simulate", "without making changes"]
            ):
                query = f"{query} (dry run)"

        result = processor.process(query, config, output)

        # Restore log level
        logging.getLogger("panflow").setLevel(old_level)

        # Display the results based on format
        if format.lower() == "json":
            typer.echo(json.dumps(result, indent=2))
        else:
            # Text format
            if result["success"]:
                processing_method = result.get("processing", "pattern")
                if processing_method == "ai" and verbose:
                    typer.echo(f"Processing: AI-powered")

                typer.echo(f"Intent: {result['intent']}")
                if verbose:
                    typer.echo(f"Entities: {result['entities']}")
                    typer.echo(f"Command: {result['command']}")

                # Show result message
                typer.echo(result.get("message", "Command executed successfully"))

                # If we have a result object, show it
                if "result" in result and result["result"]:
                    # Format the result based on the type of operation
                    result_data = result["result"]
                    if isinstance(result_data, dict):
                        # For cleanup operations
                        if "cleaned_objects" in result_data and isinstance(
                            result_data["cleaned_objects"], list
                        ):
                            if result_data["cleaned_objects"]:
                                typer.echo(
                                    f"\nRemoved {result_data.get('count', len(result_data['cleaned_objects']))} objects:"
                                )
                                for obj in result_data["cleaned_objects"]:
                                    typer.echo(f"  - {obj}")
                            else:
                                typer.echo("\nNo objects were removed.")

                            # Show output file if available
                            if "output_file" in result_data:
                                typer.echo(
                                    f"\nConfiguration saved to: {result_data['output_file']}"
                                )

                        # For cleanup policy operations
                        elif "cleaned_policies" in result_data and isinstance(
                            result_data["cleaned_policies"], list
                        ):
                            if result_data["cleaned_policies"]:
                                typer.echo(
                                    f"\nRemoved {result_data.get('count', len(result_data['cleaned_policies']))} policies:"
                                )
                                for policy in result_data["cleaned_policies"]:
                                    typer.echo(f"  - {policy}")
                            else:
                                typer.echo("\nNo policies were removed.")

                            # Show output file if available
                            if "output_file" in result_data:
                                typer.echo(
                                    f"\nConfiguration saved to: {result_data['output_file']}"
                                )

                        # For general object listings
                        elif "objects" in result_data and isinstance(result_data["objects"], list):
                            objects = result_data.get("objects", [])
                            if objects:
                                # Check if these are unused objects specifically
                                if "unused_objects" in result_data:
                                    obj_desc = "unused"
                                else:
                                    obj_desc = ""

                                # Get object type if available
                                object_type = ""
                                if "object_type" in result_data:
                                    object_type = f" {result_data['object_type']}"

                                # Display header
                                # Check if this is a duplicates search
                                if result_data.get("is_duplicate_search"):
                                    object_type_str = object_type.strip()
                                    count_str = (
                                        f"{len(objects)} duplicated {object_type_str} objects"
                                    )
                                    if result_data.get("unique_values"):
                                        count_str += f" across {result_data.get('unique_values')} unique values"
                                else:
                                    count_str = (
                                        f"{len(objects)} {obj_desc}{object_type} objects".strip()
                                    )

                                typer.echo(f"\nFound {count_str}:")

                                # Use formatted objects if available
                                if "formatted_objects" in result_data and isinstance(
                                    result_data["formatted_objects"], list
                                ):
                                    for obj in result_data["formatted_objects"]:
                                        typer.echo(f"  - {obj}")
                                else:
                                    # Simple fallback formatting
                                    for obj in objects:
                                        if isinstance(obj, dict):
                                            name = obj.get("name", "unnamed")
                                            # Try to extract basic info
                                            details = []
                                            for field in [
                                                "ip-netmask",
                                                "ip-range",
                                                "fqdn",
                                                "protocol",
                                            ]:
                                                if field in obj:
                                                    details.append(f"{field}:{obj[field]}")
                                            if details:
                                                typer.echo(f"  - {name}: {' | '.join(details)}")
                                            else:
                                                typer.echo(f"  - {name}")
                                        else:
                                            typer.echo(f"  - {obj}")
                            else:
                                typer.echo("\nNo objects found.")

                        # For any policy-related reports (disabled policies or regular policy listing)
                        elif (
                            "disabled_policies" in result_data
                            and isinstance(result_data["disabled_policies"], list)
                        ) or (
                            "policies" in result_data and isinstance(result_data["policies"], list)
                        ):
                            # Check which type of policy data we have
                            if "disabled_policies" in result_data:
                                policy_list = result_data.get("disabled_policies", [])
                                policy_desc = "disabled"
                            else:
                                policy_list = result_data.get("policies", [])
                                policy_desc = ""

                            if policy_list:
                                # Use appropriate header based on policy type
                                count_str = f"{len(policy_list)} {policy_desc}".strip()
                                typer.echo(f"\nFound {count_str} policies:")

                                # Use the formatted_policies field if available
                                if "formatted_policies" in result_data and isinstance(
                                    result_data["formatted_policies"], list
                                ):
                                    for policy in result_data["formatted_policies"]:
                                        typer.echo(f"  - {policy}")
                                else:
                                    # Fallback to just displaying policies with simple formatting
                                    for policy in policy_list:
                                        if isinstance(policy, dict):
                                            name = policy.get("name", "unnamed")
                                            extras = []
                                            if "action" in policy:
                                                extras.append(f"action:{policy['action']}")
                                            if policy.get("disabled") == "yes":
                                                extras.append("DISABLED")
                                            if extras:
                                                typer.echo(f"  - {name}: {' | '.join(extras)}")
                                            else:
                                                typer.echo(f"  - {name}")
                                        else:
                                            typer.echo(f"  - {policy}")
                            else:
                                typer.echo(f"\nNo {policy_desc} policies found.")

                        # For duplicate findings
                        elif "duplicates" in result_data:
                            if result_data.get("count", 0) > 0:
                                typer.echo(
                                    f"\nFound {result_data.get('count')} duplicate objects across {result_data.get('unique_values')} values"
                                )
                            else:
                                typer.echo("\nNo duplicate objects found.")

                        # For any other result type
                        else:
                            typer.echo("\nResult:")
                            for key, value in result_data.items():
                                if key not in ["details"]:  # Skip detailed technical data
                                    if isinstance(value, list) and len(value) > 5:
                                        # For long lists, show the first few items
                                        typer.echo(
                                            f"  {key}: {value[:5]} ... ({len(value) - 5} more)"
                                        )
                                    else:
                                        typer.echo(f"  {key}: {value}")
                    else:
                        typer.echo(f"\nResult: {result['result']}")
            else:
                processing_method = result.get("processing", "pattern")
                if processing_method == "ai" and verbose:
                    typer.echo(f"Processing: AI-powered")

                typer.echo(f"Error: {result['message']}")

                # Show suggestions if available
                if "suggestions" in result and result["suggestions"]:
                    typer.echo("\nSuggestions:")
                    for suggestion in result["suggestions"]:
                        typer.echo(f"  - {suggestion}")

    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        typer.echo(f"Error processing query: {str(e)}")
        raise typer.Exit(1)


@nlq_app.command("help")
def show_help():
    """
    Show help and examples for natural language queries.
    """
    typer.echo("PANFlow Natural Language Query Help")
    typer.echo("\nYou can ask questions or give commands in natural language.")
    typer.echo("\nExamples of queries you can use:")

    examples = [
        "cleanup unused address objects",
        "find all disabled security rules",
        "show me unused service objects",
        "remove all unused objects but don't make changes yet",
        "find duplicate address objects",
        "cleanup disabled policies in device group DG1",
        "show me all the unused objects in vsys1",
        "show me all duplicate service objects in the shared context",
        "remove all disabled security rules in device group DG1",
    ]

    for example in examples:
        typer.echo(f"  - {example}")

    typer.echo("\nUsage:")
    typer.echo('  python cli.py nlq query "your natural language query"')
    typer.echo(
        '  python cli.py nlq query "cleanup unused objects" --config config.xml --output updated.xml'
    )

    typer.echo("\nOptions:")
    typer.echo("  --config      : Specify the input configuration file")
    typer.echo("  --output      : Specify the output file for modified configurations")
    typer.echo("  --dry-run     : Preview changes without modifying the configuration")
    typer.echo("  --format      : Output format (text, json, table, csv, yaml, html)")
    typer.echo("  --verbose     : Show detailed information about the query processing")
    typer.echo("  --ai/--no-ai  : Enable or disable AI processing (if available)")
    typer.echo("  --ai-provider : AI provider to use (openai, anthropic)")
    typer.echo("  --ai-model    : AI model to use (e.g., gpt-3.5-turbo, claude-3-haiku)")

    typer.echo("\nAI Integration:")
    typer.echo("  For AI-powered natural language processing, set the appropriate API key:")
    typer.echo("  - OpenAI:    export OPENAI_API_KEY=your_api_key")
    typer.echo("  - Anthropic: export ANTHROPIC_API_KEY=your_api_key")
    typer.echo("  Or specify a different provider at runtime:")
    typer.echo('  python cli.py nlq query "your query" --ai-provider anthropic')

    typer.echo("\nInteractive Mode:")
    typer.echo("  Start an interactive session for multiple queries:")
    typer.echo("  python cli.py nlq interactive")
    typer.echo("  This maintains context between queries and provides a more fluid experience.")


@nlq_app.command("interactive")
def interactive_mode(
    config: str = ConfigOptions.config_file(),
    output: Optional[str] = ConfigOptions.output_file(),
    dry_run: bool = ConfigOptions.dry_run(),
    format: str = typer.Option("text", "--format", "-f", help="Output format (text, json, table, csv, yaml, html)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
    use_ai: bool = typer.Option(True, "--ai/--no-ai", help="Use AI for processing if available"),
    ai_provider: Optional[str] = typer.Option(
        None, "--ai-provider", help="AI provider to use (openai, anthropic)"
    ),
    ai_model: Optional[str] = typer.Option(None, "--ai-model", help="AI model to use"),
):
    """
    Start an interactive natural language query session.

    This mode allows you to enter multiple queries in sequence,
    maintaining context between queries.

    Examples:

        # Start an interactive session
        python cli.py nlq interactive --config firewall.xml

        # Start an interactive session with JSON output format
        python cli.py nlq interactive --format json

        # Start an interactive session without AI processing
        python cli.py nlq interactive --no-ai

        # Start an interactive session with a specific AI provider and model
        python cli.py nlq interactive --ai-provider anthropic --ai-model claude-3-haiku-20240307
    """
    # Set environment variables for AI processing if specified
    if ai_provider:
        os.environ["PANFLOW_AI_PROVIDER"] = ai_provider
    if ai_model:
        os.environ["PANFLOW_AI_MODEL"] = ai_model

    # Initialize the NLQ processor with AI setting
    processor = NLQProcessor(use_ai=use_ai)

    typer.echo("PANFlow Natural Language Query Interactive Mode")
    typer.echo("Type 'exit' or 'quit' to end the session, 'help' for help.")
    typer.echo(f"Using configuration file: {config}")
    if output:
        typer.echo(f"Output will be saved to: {output}")

    # Show AI status
    if use_ai:
        if processor.ai_available():
            typer.echo("AI processing: Enabled")
        else:
            typer.echo("AI processing: Unavailable (using pattern-based fallback)")
    else:
        typer.echo("AI processing: Disabled")

    # Interactive loop
    session_context = {}

    while True:
        try:
            # Get user input
            prompt = typer.style("\nPANFlow> ", fg=typer.colors.GREEN, bold=True)
            query = typer.prompt(prompt, type=str)

            # Check for exit commands
            if query.lower() in ["exit", "quit"]:
                typer.echo("Exiting PANFlow NLQ interactive mode.")
                break

            # Check for help command
            if query.lower() == "help":
                show_help()
                continue

            # Configure logging to avoid duplicate output
            # Reduce log level for most logs except important ones
            old_level = logging.getLogger("panflow").level

            if not verbose:
                # Keep specific loggers at INFO level for important information
                for logger_name in ["panflow.nlq", "panflow.core.config_loader"]:
                    logging.getLogger(logger_name).setLevel(logging.INFO)

                # Set all other panflow loggers to WARNING
                logging.getLogger("panflow").setLevel(logging.WARNING)

            # Process the query
            if not verbose:
                typer.echo("Processing query...")

            # If dry_run is specified in the command line, add it to the query
            query_to_process = query
            if dry_run:
                # Add "dry run" to the end of the query if it doesn't already contain a dry run indicator
                if not any(
                    phrase in query_to_process.lower()
                    for phrase in ["dry run", "preview", "simulate", "without making changes"]
                ):
                    query_to_process = f"{query} (dry run)"

            result = processor.process(query_to_process, config, output)

            # Restore log level
            logging.getLogger("panflow").setLevel(old_level)

            # Update session context
            session_context.update(result.get("entities", {}))

            # Display the results based on format
            if format.lower() == "json":
                typer.echo(json.dumps(result, indent=2))
            else:
                # Print debug info about result
                if verbose:
                    typer.echo(f"DEBUG - Result structure: {list(result.keys())}")
                    if "result" in result:
                        typer.echo(f"DEBUG - Result data type: {type(result['result'])}")
                        if isinstance(result["result"], dict):
                            typer.echo(f"DEBUG - Result data keys: {list(result['result'].keys())}")

                # Text format
                if result["success"]:
                    processing_method = result.get("processing", "pattern")
                    if processing_method == "ai" and verbose:
                        typer.echo(f"Processing: AI-powered")

                    typer.echo(f"Intent: {result['intent']}")
                    if verbose:
                        typer.echo(f"Entities: {result['entities']}")
                        typer.echo(f"Command: {result['command']}")

                    # Show result message
                    message = result.get("message", "Command executed successfully")
                    if not message.endswith("."):
                        message += "."
                    typer.echo(message)

                    # If we have a result object, show it
                    # And we have a result object AND it's for a non-verbose user
                    if "result" in result and result["result"] and not verbose:
                        # Format the result based on the type of operation
                        result_data = result["result"]
                        if isinstance(result_data, dict):
                            # For cleanup operations
                            if "cleaned_objects" in result_data and isinstance(
                                result_data["cleaned_objects"], list
                            ):
                                if result_data["cleaned_objects"]:
                                    typer.echo(
                                        f"\nRemoved {result_data.get('count', len(result_data['cleaned_objects']))} objects:"
                                    )
                                    for obj in result_data["cleaned_objects"]:
                                        typer.echo(f"  - {obj}")
                                else:
                                    typer.echo("\nNo objects were removed.")

                                # Show output file if available
                                if "output_file" in result_data:
                                    typer.echo(
                                        f"\nConfiguration saved to: {result_data['output_file']}"
                                    )

                            # For cleanup policy operations
                            elif "cleaned_policies" in result_data and isinstance(
                                result_data["cleaned_policies"], list
                            ):
                                if result_data["cleaned_policies"]:
                                    typer.echo(
                                        f"\nRemoved {result_data.get('count', len(result_data['cleaned_policies']))} policies:"
                                    )
                                    for policy in result_data["cleaned_policies"]:
                                        typer.echo(f"  - {policy}")
                                else:
                                    typer.echo("\nNo policies were removed.")

                                # Show output file if available
                                if "output_file" in result_data:
                                    typer.echo(
                                        f"\nConfiguration saved to: {result_data['output_file']}"
                                    )

                            # For general object listings
                            elif "objects" in result_data and isinstance(
                                result_data["objects"], list
                            ):
                                objects = result_data.get("objects", [])
                                if objects:
                                    # Check if these are unused objects specifically
                                    if "unused_objects" in result_data:
                                        obj_desc = "unused"
                                    else:
                                        obj_desc = ""

                                    # Get object type if available
                                    object_type = ""
                                    if "object_type" in result_data:
                                        object_type = f" {result_data['object_type']}"

                                    # Display header
                                    # Check if this is a duplicates search
                                    if result_data.get("is_duplicate_search"):
                                        object_type_str = object_type.strip()
                                        count_str = (
                                            f"{len(objects)} duplicated {object_type_str} objects"
                                        )
                                        if result_data.get("unique_values"):
                                            count_str += f" across {result_data.get('unique_values')} unique values"
                                    else:
                                        count_str = f"{len(objects)} {obj_desc}{object_type} objects".strip()

                                    typer.echo(f"\nFound {count_str}:")

                                    # Use formatted objects if available
                                    if "formatted_objects" in result_data and isinstance(
                                        result_data["formatted_objects"], list
                                    ):
                                        for obj in result_data["formatted_objects"]:
                                            typer.echo(f"  - {obj}")
                                    else:
                                        # Simple fallback formatting
                                        for obj in objects:
                                            if isinstance(obj, dict):
                                                name = obj.get("name", "unnamed")
                                                # Try to extract basic info
                                                details = []
                                                for field in [
                                                    "ip-netmask",
                                                    "ip-range",
                                                    "fqdn",
                                                    "protocol",
                                                ]:
                                                    if field in obj:
                                                        details.append(f"{field}:{obj[field]}")
                                                if details:
                                                    typer.echo(f"  - {name}: {' | '.join(details)}")
                                                else:
                                                    typer.echo(f"  - {name}")
                                            else:
                                                typer.echo(f"  - {obj}")
                                else:
                                    typer.echo("\nNo objects found.")

                            # For any policy-related reports (disabled policies or regular policy listing)
                            elif (
                                "disabled_policies" in result_data
                                and isinstance(result_data["disabled_policies"], list)
                            ) or (
                                "policies" in result_data
                                and isinstance(result_data["policies"], list)
                            ):
                                # Check which type of policy data we have
                                if "disabled_policies" in result_data:
                                    policy_list = result_data.get("disabled_policies", [])
                                    policy_desc = "disabled"
                                else:
                                    policy_list = result_data.get("policies", [])
                                    policy_desc = ""

                                if policy_list:
                                    # Use appropriate header based on policy type
                                    count_str = f"{len(policy_list)} {policy_desc}".strip()
                                    typer.echo(f"\nFound {count_str} policies:")

                                    # Use the formatted_policies field if available
                                    if "formatted_policies" in result_data and isinstance(
                                        result_data["formatted_policies"], list
                                    ):
                                        for policy in result_data["formatted_policies"]:
                                            typer.echo(f"  - {policy}")
                                    else:
                                        # Fallback to just displaying policies with simple formatting
                                        for policy in policy_list:
                                            if isinstance(policy, dict):
                                                name = policy.get("name", "unnamed")
                                                extras = []
                                                if "action" in policy:
                                                    extras.append(f"action:{policy['action']}")
                                                if policy.get("disabled") == "yes":
                                                    extras.append("DISABLED")
                                                if extras:
                                                    typer.echo(f"  - {name}: {' | '.join(extras)}")
                                                else:
                                                    typer.echo(f"  - {name}")
                                            else:
                                                typer.echo(f"  - {policy}")
                                else:
                                    typer.echo(f"\nNo {policy_desc} policies found.")

                            # For duplicate findings
                            elif "duplicates" in result_data:
                                if result_data.get("count", 0) > 0:
                                    typer.echo(
                                        f"\nFound {result_data.get('count')} duplicate objects across {result_data.get('unique_values')} values"
                                    )
                                else:
                                    typer.echo("\nNo duplicate objects found.")

                            # For any other result type
                            else:
                                typer.echo("\nResult:")
                                for key, value in result_data.items():
                                    if key not in ["details"]:  # Skip detailed technical data
                                        if isinstance(value, list) and len(value) > 5:
                                            # For long lists, show the first few items
                                            typer.echo(
                                                f"  {key}: {value[:5]} ... ({len(value) - 5} more)"
                                            )
                                        else:
                                            typer.echo(f"  {key}: {value}")
                        else:
                            typer.echo(f"\nResult: {result['result']}")
                else:
                    processing_method = result.get("processing", "pattern")
                    if processing_method == "ai" and verbose:
                        typer.echo(f"Processing: AI-powered")

                    typer.echo(f"Error: {result['message']}")

                    # Show suggestions if available
                    if "suggestions" in result and result["suggestions"]:
                        typer.echo("\nSuggestions:")
                        for suggestion in result["suggestions"]:
                            typer.echo(f"  - {suggestion}")

        except KeyboardInterrupt:
            typer.echo("\nExiting PANFlow NLQ interactive mode.")
            break
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            typer.echo(f"Error processing query: {str(e)}")
            continue
