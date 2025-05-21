"""
Natural Language Query commands for PANFlow CLI.

This module provides CLI commands for natural language interaction with PANFlow.
"""

import logging
import os
import json
import datetime
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
        help="Output file for updated configuration (required for cleanup/modify operations)",
    ),
    report_file: Optional[str] = typer.Option(
        None,
        "--report-file",
        "-r",
        help="Output file for report/results (use with --format to specify format)",
    ),
    dry_run: bool = ConfigOptions.dry_run(),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode"),
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format (text, json, table, csv, yaml, html)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output"),
    use_ai: bool = typer.Option(True, "--ai/--no-ai", help="Use AI for processing if available"),
    ai_provider: Optional[str] = typer.Option(
        None, "--ai-provider", help="AI provider to use (openai, anthropic)"
    ),
    ai_model: Optional[str] = typer.Option(None, "--ai-model", help="AI model to use"),
):
    """
    Process a natural language query against the configuration.

    The output file (--output) is for saving modified configurations, while
    the report file (--report-file) is for saving query results in various formats.

    Examples:

        # Find unused address objects in dry run mode
        python cli.py nlq query "cleanup unused address objects, but just show what would be removed"

        # Remove disabled security policies
        python cli.py nlq query "cleanup all disabled security rules" --config firewall.xml --output cleaned.xml

        # Show a report of unused service objects
        python cli.py nlq query "show me all unused service objects" --config panorama.xml

        # Generate an HTML report of unused objects
        python cli.py nlq query "show me unused address objects" --format html --report-file unused_report.html

        # Clean up unused objects and save both modified config and HTML report
        python cli.py nlq query "cleanup unused objects" --config fw.xml --output cleaned.xml --format html --report-file report.html

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
            # JSON format
            output_json = json.dumps(result, indent=2)
            if report_file:
                with open(report_file, "w") as f:
                    f.write(output_json)
                typer.echo(f"Report saved to {report_file}")
            else:
                typer.echo(output_json)
        elif format.lower() == "csv":
            # CSV format
            import csv
            import io

            # Determine if we're writing to a file or a string buffer
            if report_file:
                output_file = open(report_file, "w", newline="")
                csv_writer = csv.writer(output_file)
            else:
                output_stream = io.StringIO()
                csv_writer = csv.writer(output_stream)

            # Write basic information
            csv_writer.writerow(["Intent", result["intent"]])
            csv_writer.writerow(["Success", str(result["success"])])
            csv_writer.writerow(["Processing", result.get("processing", "pattern")])
            csv_writer.writerow(["Message", result.get("message", "Command executed successfully")])

            # If we have result objects, add them to CSV
            if "result" in result and result["result"] and isinstance(result["result"], dict):
                result_data = result["result"]

                # For object listings
                if "objects" in result_data and isinstance(result_data["objects"], list):
                    objects = result_data.get("objects", [])
                    if objects:
                        # Check if these are unused objects specifically
                        if "unused_objects" in result_data:
                            obj_desc = "Unused"
                        else:
                            obj_desc = ""
                            
                        # Get object type if available
                        object_type = ""
                        if "object_type" in result_data:
                            object_type = f" {result_data['object_type']}"
                            
                        # Add header
                        csv_writer.writerow([])
                        csv_writer.writerow([f"{obj_desc}{object_type} Objects ({len(objects)})".strip()])
                        
                        # Check for context information
                        has_context = any("context" in obj for obj in objects) or any("context_name" in obj for obj in objects)
                        
                        # Create column headers based on object structure
                        headers = ["Name"]
                        if any("ip-netmask" in obj for obj in objects):
                            headers.append("IP Address")
                        elif any("fqdn" in obj for obj in objects):
                            headers.append("FQDN")
                        elif any("ip-range" in obj for obj in objects):
                            headers.append("IP Range")
                        
                        # Add Context column if available
                        if has_context:
                            headers.append("Context")
                            
                        csv_writer.writerow(headers)
                        
                        # Add objects
                        for obj in objects:
                            if isinstance(obj, dict):
                                row = [obj.get("name", "")]
                                
                                # Add IP information
                                if "IP Address" in headers:
                                    row.append(obj.get("ip-netmask", ""))
                                elif "FQDN" in headers:
                                    row.append(obj.get("fqdn", ""))
                                elif "IP Range" in headers:
                                    row.append(obj.get("ip-range", ""))
                                    
                                # Add context information if available
                                if has_context:
                                    if "context" in obj:
                                        row.append(obj["context"])
                                    elif "context_name" in obj and "context_type" in obj:
                                        if obj["context_type"] == "device_group":
                                            row.append(f"Device Group: {obj['context_name']}")
                                        elif obj["context_type"] == "vsys":
                                            row.append(f"VSYS: {obj['context_name']}")
                                        else:
                                            row.append(obj.get("context_name", ""))
                                    else:
                                        row.append("")
                                        
                                csv_writer.writerow(row)
                            else:
                                # Simple string object
                                csv_writer.writerow([str(obj)])
                
                # For cleanup operations (objects)
                elif "cleaned_objects" in result_data and isinstance(
                    result_data["cleaned_objects"], list
                ):
                    if result_data["cleaned_objects"]:
                        csv_writer.writerow([])  # Empty row as separator
                        csv_writer.writerow(
                            [f"Removed Objects ({len(result_data['cleaned_objects'])}):"]
                        )
                        csv_writer.writerow(["Name"])

                        for obj in result_data["cleaned_objects"]:
                            csv_writer.writerow([obj])

                        if "output_file" in result_data:
                            csv_writer.writerow([])
                            csv_writer.writerow(
                                ["Configuration saved to:", result_data["output_file"]]
                            )

                # For cleanup policy operations
                elif "cleaned_policies" in result_data and isinstance(
                    result_data["cleaned_policies"], list
                ):
                    if result_data["cleaned_policies"]:
                        csv_writer.writerow([])  # Empty row as separator
                        csv_writer.writerow(
                            [f"Removed Policies ({len(result_data['cleaned_policies'])}):"]
                        )
                        csv_writer.writerow(["Name"])

                        for policy in result_data["cleaned_policies"]:
                            csv_writer.writerow([policy])

                        if "output_file" in result_data:
                            csv_writer.writerow([])
                            csv_writer.writerow(
                                ["Configuration saved to:", result_data["output_file"]]
                            )

                # For bulk update policy operations
                elif "updated_policies" in result_data and isinstance(
                    result_data["updated_policies"], list
                ):
                    if result_data["updated_policies"]:
                        # Get operation details
                        operation = result_data.get("operation", "updated")
                        value = result_data.get("value", "")
                        dry_run = result_data.get("dry_run", False)

                        # Format header based on operation type
                        operation_desc = {
                            "enable": "Enabled",
                            "disable": "Disabled",
                            "add_tag": f"Added Tag '{value}' to",
                            "set_action": f"Set Action '{value}' for",
                            "enable_logging": "Enabled Logging for",
                            "disable_logging": "Disabled Logging for",
                        }.get(operation, "Updated")

                        if dry_run:
                            header = f"Would {operation_desc} Policies (Dry Run) ({len(result_data['updated_policies'])})"
                        else:
                            header = f"{operation_desc} Policies ({len(result_data['updated_policies'])})"

                        csv_writer.writerow([])  # Empty row as separator
                        csv_writer.writerow([header])

                        # Add policy type if it might be present
                        if result_data.get("policy_type") == "all":
                            csv_writer.writerow(["Name", "Policy Type"])

                            for policy in result_data["updated_policies"]:
                                if isinstance(policy, dict) and "name" in policy:
                                    policy_name = policy["name"]
                                    policy_type = policy.get("policy_type", "")
                                    csv_writer.writerow([policy_name, policy_type])
                                else:
                                    csv_writer.writerow([str(policy), ""])
                        else:
                            csv_writer.writerow(["Name"])
                            policy_type = result_data.get("policy_type", "")

                            for policy in result_data["updated_policies"]:
                                if isinstance(policy, dict) and "name" in policy:
                                    policy_name = policy["name"]
                                    csv_writer.writerow([policy_name])
                                else:
                                    csv_writer.writerow([str(policy)])

                        if "output_file" in result_data:
                            csv_writer.writerow([])
                            csv_writer.writerow(
                                ["Configuration saved to:", result_data["output_file"]]
                            )
                
                # For object listings
                elif "objects" in result_data and isinstance(result_data["objects"], list):
                    objects = result_data.get("objects", [])
                    if objects:
                        csv_writer.writerow([])  # Empty row as separator
                        
                        # Determine object type and description
                        obj_desc = "unused" if "unused_objects" in result_data else ""
                        object_type = result_data.get("object_type", "")
                        
                        # Create title based on search type
                        if result_data.get("is_duplicate_search"):
                            header = f"Duplicated {object_type} Objects ({len(objects)})"
                            if result_data.get("unique_values"):
                                header += f" across {result_data.get('unique_values')} unique values"
                        else:
                            header = f"{obj_desc} {object_type} Objects ({len(objects)})".strip().capitalize()
                            
                        csv_writer.writerow([header])
                        
                        # Check if objects have detailed information
                        if objects and isinstance(objects[0], dict):
                            # Determine which columns are needed based on the data
                            columns = ["Name"]
                            
                            # Check if we have context information available
                            has_context = any("context" in obj for obj in objects) or any("context_name" in obj for obj in objects)
                            
                            for field in ["ip-netmask", "ip-range", "fqdn", "protocol", "port", "description"]:
                                if any(field in obj for obj in objects):
                                    columns.append(field.capitalize())
                            
                            # Add context column if available
                            if has_context:
                                columns.append("Context")
                                    
                            # Write header row
                            csv_writer.writerow(columns)
                            
                            # Write object data
                            for obj in objects:
                                row_data = [obj.get("name", "unnamed")]
                                
                                # Process standard fields
                                for field in columns[1:-1] if has_context else columns[1:]:  # Skip the name column and context (if present)
                                    field_key = field.lower()
                                    row_data.append(str(obj.get(field_key, "")))
                                
                                # Add context information if available
                                if has_context and "Context" in columns:
                                    if "context" in obj:
                                        row_data.append(str(obj.get("context", "")))
                                    elif "context_name" in obj:
                                        if "context_type" in obj and obj["context_type"] == "device_group":
                                            row_data.append(f"Device Group: {obj['context_name']}")
                                        elif "context_type" in obj and obj["context_type"] == "vsys":
                                            row_data.append(f"VSYS: {obj['context_name']}")
                                        else:
                                            row_data.append(str(obj.get("context_name", "")))
                                    else:
                                        row_data.append("")
                                    
                                csv_writer.writerow(row_data)
                        else:
                            # Simple objects list
                            # Check if we have context information available in the simpler objects
                            has_context = any(isinstance(obj, dict) and ("context" in obj or "context_name" in obj) for obj in objects)
                            
                            if has_context:
                                csv_writer.writerow(["Name", "Context"])
                                for obj in objects:
                                    if isinstance(obj, str):
                                        csv_writer.writerow([obj, ""])
                                    elif isinstance(obj, dict):
                                        obj_name = obj.get("name", str(obj))
                                        # Format context information
                                        context_str = ""
                                        if "context" in obj:
                                            context_str = str(obj.get("context", ""))
                                        elif "context_name" in obj:
                                            if "context_type" in obj and obj["context_type"] == "device_group":
                                                context_str = f"Device Group: {obj['context_name']}"
                                            elif "context_type" in obj and obj["context_type"] == "vsys":
                                                context_str = f"VSYS: {obj['context_name']}"
                                            else:
                                                context_str = str(obj.get("context_name", ""))
                                        csv_writer.writerow([obj_name, context_str])
                                    else:
                                        csv_writer.writerow([str(obj), ""])
                            else:
                                # No context information available
                                csv_writer.writerow(["Name"])
                                for obj in objects:
                                    if isinstance(obj, str):
                                        csv_writer.writerow([obj])
                                    else:
                                        csv_writer.writerow([str(obj)])

            if report_file:
                output_file.close()
                typer.echo(f"Report saved to {report_file}")
            else:
                typer.echo(output_stream.getvalue())
                output_stream.close()

        elif format.lower() == "yaml":
            # YAML format
            try:
                import yaml

                # Create a function to handle non-serializable objects
                def yaml_safe_dump(obj):
                    if isinstance(obj, dict):
                        return {k: yaml_safe_dump(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [yaml_safe_dump(item) for item in obj]
                    else:
                        return obj

                # Build a structured data representation
                yaml_data = {
                    "nlq_result": {
                        "intent": result["intent"],
                        "success": result["success"],
                        "processing": result.get("processing", "pattern"),
                        "message": result.get("message", "Command executed successfully"),
                    }
                }

                # Add result data if available
                if "result" in result and result["result"]:
                    yaml_data["result"] = yaml_safe_dump(result["result"])

                # Output the YAML
                yaml_output = yaml.dump(yaml_data, sort_keys=False, default_flow_style=False)
                if report_file:
                    with open(report_file, "w") as f:
                        f.write(yaml_output)
                    typer.echo(f"Report saved to {report_file}")
                else:
                    typer.echo(yaml_output)

            except ImportError:
                typer.echo("Error: PyYAML not installed. Install with 'pip install pyyaml'")
                raise typer.Exit(1)

        elif format.lower() == "html":
            # Import the template loader for HTML rendering
            from ...core.template_loader import TemplateLoader
            
            # Create a template loader
            template_loader = TemplateLoader()
            
            # Create a structured dataset for HTML report
            report_info = {
                "Query": query,
                "Configuration": config,
                "Intent": result['intent'],
                "Success": str(result['success']),
                "Processing Method": result.get('processing', 'pattern')
            }
            
            # Add result data if available
            if "result" in result and result["result"] and isinstance(result["result"], dict):
                result_data = result["result"]
                
                # Determine report type and render appropriate template based on intent
                if result["intent"] == "list_unused_objects":
                    # Unused objects report
                    unused_objects = result_data.get("objects", [])
                    
                    # Add log to see the structure of the unused objects for debugging
                    logger.debug(f"Rendering unused objects report with {len(unused_objects)} objects")
                    if unused_objects and len(unused_objects) > 0:
                        logger.debug(f"Sample object structure: {unused_objects[0]}")
                        
                    html_content = template_loader.render_unused_objects_report(
                        {"unused_objects": unused_objects},
                        report_info
                    )
                    report_type = "Unused Objects Report"
                
                # Handle list_objects with show_duplicates=True (duplicate objects)
                elif result["intent"] == "list_objects" and result_data.get("is_duplicate_search") == True:
                    # This is "show me duplicated objects" type of query
                    object_type = result_data.get("object_type", "")
                    objects = result_data.get("objects", {})
                    
                    # We need to reformat these objects into the duplicate format
                    # First, we need to group objects by their value
                    value_to_objects = {}
                    
                    # Check if we already have formatted duplicates
                    if "formatted_duplicates" in result_data:
                        # Use the pre-formatted duplicates with context
                        formatted_dups = result_data.get("formatted_duplicates", {})
                    # Try to extract the duplicates data from the result if no formatted duplicates available
                    elif "duplicates" in result_data:
                        # Convert raw duplicates to the expected format
                        dup_data = result_data.get("duplicates", {})
                        formatted_dups = {}
                        
                        for value, objects_list in dup_data.items():
                            formatted_objects = []
                            for obj in objects_list:
                                if isinstance(obj, tuple) and len(obj) >= 2:
                                    obj_name = obj[0]
                                    obj_data = {"name": obj_name}
                                    
                                    # Add context if available
                                    if len(obj) > 2 and isinstance(obj[2], dict):
                                        obj_context = obj[2]
                                        obj_data["context_type"] = obj_context.get("type", "unknown")
                                        if "device_group" in obj_context:
                                            obj_data["context_name"] = obj_context["device_group"]
                                        elif "vsys" in obj_context:
                                            obj_data["context_name"] = obj_context["vsys"]
                                            
                                    formatted_objects.append(obj_data)
                                else:
                                    # Simple string object
                                    formatted_objects.append({"name": str(obj)})
                                    
                            # Skip empty lists
                            if formatted_objects:
                                formatted_dups[value] = formatted_objects
                        
                    # Get report data with formatted duplicates
                    report_data = {"duplicate_objects": formatted_dups}
                    
                    # Render using duplicate objects template
                    html_content = template_loader.render_duplicate_objects_report(
                        report_data,
                        report_info
                    )
                    report_type = "Duplicate Objects Report"
                
                elif "duplicate" in result["intent"] and ("duplicates" in result_data or "formatted_duplicates" in result_data):
                    # Duplicate objects report
                    object_type = result_data.get("object_type", "")
                    
                    # Check if we have pre-formatted duplicates with context
                    if "formatted_duplicates" in result_data:
                        # Use the pre-formatted duplicates with context
                        formatted_dups = result_data.get("formatted_duplicates", {})
                    else:
                        # Fall back to manually formatting the duplicates
                        dup_data = result_data.get("duplicates", {})
                        formatted_dups = {}
                        
                        # Check if this is the "all" object type (combined results)
                        if object_type.lower() == "all":
                            for value, objects in dup_data.items():
                                if value.startswith('_'):  # Skip internal fields
                                    continue
                                    
                                # Extract object type from the key prefix
                                type_parts = value.split(":", 1)
                                obj_type = type_parts[0] if len(type_parts) > 1 else "unknown"
                                actual_value = type_parts[1] if len(type_parts) > 1 else value
                                
                                # Format key to include object type
                                formatted_key = f"{obj_type}:{actual_value}"
                                
                                # Format objects list with context if available
                                formatted_objects = []
                                for obj in objects:
                                    if isinstance(obj, dict):
                                        # Object already has context information
                                        formatted_objects.append(obj)
                                    elif isinstance(obj, tuple) and len(obj) >= 2:
                                        # Convert tuple to dict with context
                                        obj_data = {"name": obj[0]}
                                        if len(obj) > 2:
                                            # Add context from tuple
                                            obj_data["context_type"] = obj[2].get("type", "unknown")
                                            if "device_group" in obj[2]:
                                                obj_data["context_name"] = obj[2]["device_group"]
                                            elif "vsys" in obj[2]:
                                                obj_data["context_name"] = obj[2]["vsys"]
                                        formatted_objects.append(obj_data)
                                    else:
                                        # Simple string object
                                        formatted_objects.append({"name": str(obj)})
                                        
                                formatted_dups[formatted_key] = formatted_objects
                        else:
                            # Single object type format
                            for value, objects in dup_data.items():
                                if value.startswith('_'):  # Skip internal fields
                                    continue
                                    
                                # Format objects list with context
                                formatted_objects = []
                                for obj in objects:
                                    if isinstance(obj, dict):
                                        # Object already has context information
                                        formatted_objects.append(obj)
                                    elif isinstance(obj, tuple) and len(obj) >= 2:
                                        # Convert tuple to dict with context
                                        obj_data = {"name": obj[0]}
                                        if len(obj) > 2:
                                            # Add context from tuple
                                            obj_data["context_type"] = obj[2].get("type", "unknown")
                                            if "device_group" in obj[2]:
                                                obj_data["context_name"] = obj[2]["device_group"]
                                            elif "vsys" in obj[2]:
                                                obj_data["context_name"] = obj[2]["vsys"]
                                        formatted_objects.append(obj_data)
                                    else:
                                        # Simple string object
                                        formatted_objects.append({"name": str(obj)})
                                        
                                formatted_dups[value] = formatted_objects
                    
                    # Get report data with formatted duplicates
                    report_data = {"duplicate_objects": formatted_dups}
                    
                    # Render using duplicate objects template
                    html_content = template_loader.render_duplicate_objects_report(
                        report_data,
                        report_info
                    )
                    report_type = "Duplicate Objects Report"
                
                elif result["intent"].startswith("cleanup_"):
                    # Cleanup operation report
                    if "cleaned_objects" in result_data:
                        # Convert list of object names to object dictionaries for the template
                        cleaned_objects = []
                        for obj_name in result_data.get("cleaned_objects", []):
                            cleaned_objects.append({"name": obj_name})
                        
                        # Render using unused objects template (reusing it for cleanup)
                        html_content = template_loader.render_unused_objects_report(
                            {"unused_objects": cleaned_objects},
                            report_info
                        )
                        report_type = "Cleanup Operation Report"
                    else:
                        # Generic cleanup report
                        html_content = template_loader.render_template(
                            "reports/components/base_template.html",
                            {
                                "report_title": "Cleanup Operation Report",
                                "content": f"<pre>{json.dumps(result_data, indent=2)}</pre>",
                                "report_info": report_info
                            }
                        )
                        report_type = "Cleanup Operation Report"
                
                else:
                    # Generic NLQ report using base template
                    html_content = template_loader.render_template(
                        "reports/components/base_template.html",
                        {
                            "report_title": "Natural Language Query Results",
                            "content": f"<pre>{json.dumps(result_data, indent=2)}</pre>",
                            "report_info": report_info
                        }
                    )
                    report_type = "Natural Language Query Report"
            
            else:
                # No result data, render generic report
                html_content = template_loader.render_template(
                    "reports/components/base_template.html",
                    {
                        "report_title": "Natural Language Query Results",
                        "content": "<p>No result data available.</p>",
                        "report_info": report_info
                    }
                )
                report_type = "Natural Language Query Report"
            
            # Save to file or display
            if report_file:
                with open(report_file, "w") as f:
                    f.write(html_content)
                typer.echo(f"HTML report saved to {report_file}")
            else:
                # When no report file is specified, print a simple text summary to the console
                typer.echo(f"Query: {query}")
                typer.echo(f"Intent: {result['intent']}")
                typer.echo(f"Success: {result['success']}")
                
                if "result" in result and result["result"] and isinstance(result["result"], dict):
                    result_data = result["result"]
                    
                    # Show appropriate summary based on the data type
                    if "duplicates" in result_data:
                        dup_count = result_data.get("count", 0)
                        unique_values = result_data.get("unique_values", 0)
                        object_type = result_data.get("object_type", "")
                        typer.echo(f"Found {dup_count} duplicate {object_type} objects across {unique_values} values")
                    elif "cleaned_objects" in result_data:
                        count = len(result_data["cleaned_objects"])
                        typer.echo(f"Removed {count} objects")
                    elif "updated_policies" in result_data:
                        count = len(result_data["updated_policies"])
                        typer.echo(f"Updated {count} policies")
                    
                typer.echo("Use --report-file to save the HTML report to a file")

        elif format.lower() == "table":
            # Table format
            from rich.console import Console
            from rich.table import Table

            console = Console()

            # Show basic information
            info_table = Table(title="Natural Language Query Result")
            info_table.add_column("Field", style="cyan")
            info_table.add_column("Value", style="green")

            info_table.add_row("Intent", result["intent"])
            info_table.add_row("Success", str(result["success"]))
            info_table.add_row("Processing", result.get("processing", "pattern"))

            if verbose:
                # Convert command to string if it's a dict
                command = result.get("command", "N/A")
                if isinstance(command, dict):
                    command = str(command)
                info_table.add_row("Command", command)
                if "entities" in result:
                    entities_str = ", ".join([f"{k}={v}" for k, v in result["entities"].items()])
                    info_table.add_row("Entities", entities_str)

            # Get the message or default
            message = result.get("message", "Command executed successfully")

            # If this is a cleanup operation that got converted to find-only operation, add note
            if result["intent"].startswith("cleanup_") and output is None:
                message += " (NOTE: No output file provided. This is a find-only operation. Use -o/--output to specify an output file for actual cleanup.)"

            info_table.add_row("Message", message)
            console.print(info_table)

            # If we have result objects, show them in a table
            if "result" in result and result["result"] and isinstance(result["result"], dict):
                result_data = result["result"]

                # For duplicate findings - need to handle this case first
                if "duplicates" in result_data:
                    dup_count = result_data.get("count", 0)
                    unique_values = result_data.get("unique_values", 0)
                    object_type = result_data.get("object_type", "")

                    if dup_count > 0:
                        # Check if we have formatted duplicates with context info
                        if "formatted_duplicates" in result_data:
                            formatted_dups = result_data["formatted_duplicates"]
                            
                            # Create a grouped table per value
                            console.print(f"[bold]Duplicate {object_type} Objects ({dup_count} across {unique_values} values)[/bold]")
                            console.print()
                            
                            # Iterate through values and show objects grouped by value
                            for value, objects in formatted_dups.items():
                                # Skip internal fields
                                if value.startswith("_"):
                                    continue
                                    
                                # Format the value for display
                                if ":" in value:
                                    parts = value.split(":", 1)
                                    value_display = f"[cyan]{parts[0].capitalize()}:[/cyan] [bold]{parts[1]}[/bold]"
                                else:
                                    value_display = f"[bold]{value}[/bold]"
                                    
                                # Create a table for this duplicate group
                                group_table = Table(
                                    title=f"{value_display} ({len(objects)} objects)",
                                    show_header=True,
                                    box=None
                                )
                                group_table.add_column("Name", style="green")
                                group_table.add_column("Context", style="magenta")
                                
                                # Add each object to the table
                                for obj in objects:
                                    name = obj.get("name", "unnamed")
                                    
                                    # Get context information
                                    context = obj.get("context", "")
                                    if not context and "context_type" in obj:
                                        if obj["context_type"] == "device_group" and "context_name" in obj:
                                            context = f"Device Group: {obj['context_name']}"
                                        elif obj["context_type"] == "vsys" and "context_name" in obj:
                                            context = f"VSYS: {obj['context_name']}"
                                        elif obj["context_type"] == "shared":
                                            context = "Shared"
                                            
                                    group_table.add_row(name, context)
                                
                                # Display the table for this group
                                console.print(group_table)
                                console.print()  # Add spacing between groups
                        else:
                            # Fall back to old display format if formatted_duplicates not available
                            dup_data = result_data["duplicates"]
                            
                            # Check if this is the "all" object type (combined results)
                            if object_type.lower() == "all":
                                # Create a summary table with object type column
                                dup_table = Table(
                                    title=f"Duplicate Objects ({dup_count} across {unique_values} values)"
                                )
                                dup_table.add_column("Object Type", style="magenta")
                                dup_table.add_column("Value/Pattern", style="cyan")
                                dup_table.add_column("Objects", style="green")
    
                                # Add rows for each duplicated value - in "all" mode, keys are prefixed with the object type
                                for value, objects in dup_data.items():
                                    # Skip internal fields
                                    if value.startswith("_"):
                                        continue
    
                                    # Extract object type from the key prefix
                                    type_parts = value.split(":", 1)
                                    obj_type = type_parts[0] if len(type_parts) > 1 else "unknown"
                                    actual_value = type_parts[1] if len(type_parts) > 1 else value
    
                                    # Format the list of objects - handle both strings and tuples
                                    obj_list = []
                                    for obj in objects:
                                        if isinstance(obj, tuple):
                                            obj_list.append(obj[0])  # Assume the first item is the name
                                        else:
                                            obj_list.append(str(obj))
    
                                    objects_str = ", ".join(obj_list)
                                    if len(objects_str) > 70:  # Truncate if too long
                                        objects_str = objects_str[:67] + "..."
    
                                    dup_table.add_row(obj_type, actual_value, objects_str)
                            else:
                                # Normal single object type display
                                # Create a summary table
                                dup_table = Table(
                                    title=f"Duplicate {object_type} Objects ({dup_count} across {unique_values} values)"
                                )
                                dup_table.add_column("Value/Pattern", style="cyan")
                                dup_table.add_column("Objects", style="green")
    
                                # Add rows for each duplicated value
                                for value, objects in dup_data.items():
                                    # Skip internal fields
                                    if value.startswith("_"):
                                        continue
    
                                    # Format the list of objects - handle both strings and tuples
                                    obj_list = []
                                    for obj in objects:
                                        if isinstance(obj, tuple):
                                            obj_list.append(obj[0])  # Assume the first item is the name
                                        else:
                                            obj_list.append(str(obj))
    
                                    objects_str = ", ".join(obj_list)
                                    if len(objects_str) > 70:  # Truncate if too long
                                        objects_str = objects_str[:67] + "..."
    
                                    dup_table.add_row(value, objects_str)
    
                            console.print(dup_table)

                # For cleanup operations (objects)
                if "cleaned_objects" in result_data and isinstance(
                    result_data["cleaned_objects"], list
                ):
                    if result_data["cleaned_objects"]:
                        removed_table = Table(
                            title=f"Removed Objects ({len(result_data['cleaned_objects'])})"
                        )
                        removed_table.add_column("Name", style="red")

                        for obj in result_data["cleaned_objects"]:
                            removed_table.add_row(obj)

                        console.print(removed_table)

                        if "output_file" in result_data:
                            console.print(
                                f"[blue]Configuration saved to:[/blue] {result_data['output_file']}"
                            )

                # For cleanup policy operations
                elif "cleaned_policies" in result_data and isinstance(
                    result_data["cleaned_policies"], list
                ):
                    if result_data["cleaned_policies"]:
                        removed_table = Table(
                            title=f"Removed Policies ({len(result_data['cleaned_policies'])})"
                        )
                        removed_table.add_column("Name", style="red")

                        for policy in result_data["cleaned_policies"]:
                            removed_table.add_row(policy)

                        console.print(removed_table)

                        if "output_file" in result_data:
                            console.print(
                                f"[blue]Configuration saved to:[/blue] {result_data['output_file']}"
                            )

                # For bulk update policy operations
                elif "updated_policies" in result_data and isinstance(
                    result_data["updated_policies"], list
                ):
                    if result_data["updated_policies"]:
                        # Create an appropriate title based on the operation
                        operation = result_data.get("operation", "updated")
                        value = result_data.get("value", "")
                        dry_run = result_data.get("dry_run", False)

                        # Format title based on operation type
                        operation_desc = {
                            "enable": "Enabled",
                            "disable": "Disabled",
                            "add_tag": f"Added Tag '{value}' to",
                            "set_action": f"Set Action '{value}' for",
                            "enable_logging": "Enabled Logging for",
                            "disable_logging": "Disabled Logging for",
                        }.get(operation, "Updated")

                        if dry_run:
                            title = f"Would {operation_desc} {len(result_data['updated_policies'])} Policies (Dry Run)"
                        else:
                            title = f"{operation_desc} {len(result_data['updated_policies'])} Policies"

                        updated_table = Table(title=title)
                        updated_table.add_column("Name", style="green")

                        if "policy_type" in result_data:
                            updated_table.add_column("Policy Type", style="cyan")

                            for policy in result_data["updated_policies"]:
                                # Check if policy is a dict with type information
                                if isinstance(policy, dict) and "policy_type" in policy:
                                    updated_table.add_row(policy["name"], policy["policy_type"])
                                else:
                                    # Assume it's a string or doesn't have policy_type
                                    policy_name = policy if isinstance(policy, str) else policy.get("name", str(policy))
                                    updated_table.add_row(policy_name, result_data.get("policy_type", ""))
                        else:
                            for policy in result_data["updated_policies"]:
                                # Handle both string policy names and policy dictionaries
                                if isinstance(policy, dict):
                                    updated_table.add_row(policy.get("name", str(policy)))
                                else:
                                    updated_table.add_row(str(policy))

                        console.print(updated_table)

                        if "output_file" in result_data:
                            console.print(
                                f"[blue]Configuration saved to:[/blue] {result_data['output_file']}"
                            )

                # For object listings
                elif "objects" in result_data and isinstance(result_data["objects"], list):
                    objects = result_data.get("objects", [])
                    if objects:
                        # Determine object type and description
                        obj_desc = "unused" if "unused_objects" in result_data else ""
                        object_type = result_data.get("object_type", "")

                        # Create title based on search type
                        if result_data.get("is_duplicate_search"):
                            title = f"Duplicated {object_type} Objects ({len(objects)})"
                            if result_data.get("unique_values"):
                                title += f" across {result_data.get('unique_values')} unique values"
                        else:
                            title = f"{obj_desc} {object_type} Objects ({len(objects)})".strip().capitalize()

                        # Create objects table
                        objects_table = Table(title=title)
                        objects_table.add_column("Name")

                        # Add additional columns based on first object
                        if objects and isinstance(objects[0], dict):
                            detail_columns = []
                            # Check if we have context information available
                            has_context = any("context" in obj for obj in objects) or any("context_name" in obj for obj in objects)
                            
                            for field in [
                                "ip-netmask",
                                "ip-range",
                                "fqdn",
                                "protocol",
                                "port",
                                "description",
                            ]:
                                if any(field in obj for obj in objects):
                                    objects_table.add_column(field)
                                    detail_columns.append(field)
                                    
                            # Add context column if available
                            if has_context:
                                objects_table.add_column("Context")
                                detail_columns.append("context")

                            for obj in objects:
                                values = [obj.get("name", "unnamed")]
                                for col in detail_columns:
                                    if col == "context":
                                        # Format context information
                                        if "context" in obj:
                                            values.append(str(obj.get("context", "")))
                                        elif "context_name" in obj:
                                            if "context_type" in obj and obj["context_type"] == "device_group":
                                                values.append(f"Device Group: {obj['context_name']}")
                                            elif "context_type" in obj and obj["context_type"] == "vsys":
                                                values.append(f"VSYS: {obj['context_name']}")
                                            else:
                                                values.append(str(obj.get("context_name", "")))
                                        else:
                                            values.append("")
                                    else:
                                        values.append(str(obj.get(col, "")))
                                objects_table.add_row(*values)
                        else:
                            # Simple objects list
                            for obj in objects:
                                if isinstance(obj, str):
                                    objects_table.add_row(obj)
                                else:
                                    objects_table.add_row(str(obj))

                        console.print(objects_table)

                # For policy reports
                elif (
                    "disabled_policies" in result_data
                    and isinstance(result_data["disabled_policies"], list)
                ) or ("policies" in result_data and isinstance(result_data["policies"], list)):
                    if "disabled_policies" in result_data:
                        policy_list = result_data.get("disabled_policies", [])
                        policy_desc = "Disabled"
                        # Get detailed policy data if available
                        policy_details = result_data.get("disabled_policies_details", [])
                    else:
                        policy_list = result_data.get("policies", [])
                        policy_desc = ""
                        policy_details = policy_list if policy_list and isinstance(policy_list[0], dict) else []

                    # Get the policy type to use in the title
                    policy_type = result_data.get("policy_type", "")

                    # Check if there are no policies to display
                    if len(policy_list) == 0:
                        if policy_type.lower() == "all":
                            console.print(f"No {policy_desc.lower() if policy_desc else ''} policies found across any policy types.")
                        else:
                            type_display = f" {policy_type}" if policy_type else ""
                            console.print(f"No {policy_desc.lower() if policy_desc else ''}{type_display} policies found.")
                    # Check if this is an "all" policy type search with multiple policy types
                    elif policy_type.lower() == "all" and policy_details and any("policy_type" in p for p in policy_details):
                        # Set title for multiple policy types
                        title = f"{policy_desc} Policies ({len(policy_list)})"
                        if policy_desc:
                            title += " - Multiple Policy Types"

                        # Create table with policy type column
                        policies_table = Table(title=title.strip().capitalize())
                        policies_table.add_column("Policy Type", style="magenta")
                        policies_table.add_column("Name", style="cyan")
                        policies_table.add_column("Action", style="green")
                        policies_table.add_column("Source/Destination", style="blue")

                        if "disabled_policies" in result_data:
                            policies_table.add_column("Status", style="yellow")

                        # Group by policy type for display
                        for policy in policy_details:
                            name = policy.get("name", "unnamed")
                            curr_policy_type = policy.get("policy_type", "unknown")
                            action = policy.get("action", "")

                            # Format source/destination details
                            details = []
                            if "from" in policy and "to" in policy:
                                details.append(f"{policy['from']} → {policy['to']}")
                            elif "source" in policy and "destination" in policy:
                                details.append(f"{policy['source']} → {policy['destination']}")

                            src_dest = " | ".join(details)

                            if "disabled_policies" in result_data:
                                policies_table.add_row(
                                    curr_policy_type,
                                    name,
                                    action,
                                    src_dest,
                                    "Disabled" if policy.get("disabled") == "yes" else ""
                                )
                            else:
                                policies_table.add_row(curr_policy_type, name, action, src_dest)
                    else:
                        # Regular single policy type table
                        type_display = f" {policy_type}" if policy_type else ""
                        title = f"{policy_desc}{type_display} Policies ({len(policy_list)})"

                        policies_table = Table(title=title.strip().capitalize())
                        policies_table.add_column("Name", style="cyan")

                        # Add additional columns if policies have fields
                        if policy_details:
                            # Check which columns we need
                            has_action = any("action" in p for p in policy_details)
                            has_from_to = any(("from" in p and "to" in p) for p in policy_details)
                            has_src_dst = any(("source" in p and "destination" in p) for p in policy_details)
                            has_disabled = any("disabled" in p for p in policy_details)

                            if has_action:
                                policies_table.add_column("Action", style="green")
                            if has_from_to or has_src_dst:
                                policies_table.add_column("Source/Destination", style="blue")
                            if has_disabled:
                                policies_table.add_column("Status", style="yellow")

                            # Add rows for each policy
                            for policy in policy_details:
                                name = policy.get("name", "unnamed")

                                # Build row values
                                row_values = [name]

                                if has_action:
                                    row_values.append(policy.get("action", ""))

                                if has_from_to or has_src_dst:
                                    # Format source/destination details
                                    details = []
                                    if "from" in policy and "to" in policy:
                                        details.append(f"{policy['from']} → {policy['to']}")
                                    elif "source" in policy and "destination" in policy:
                                        details.append(f"{policy['source']} → {policy['destination']}")

                                    row_values.append(" | ".join(details))

                                if has_disabled:
                                    row_values.append("Disabled" if policy.get("disabled") == "yes" else "")

                                policies_table.add_row(*row_values)
                        else:
                            # Simple policy list
                            for policy in policy_list:
                                if isinstance(policy, str):
                                    policies_table.add_row(policy)
                                else:
                                    policies_table.add_row(str(policy))

                        console.print(policies_table)

        else:
            # Text format (default)
            if result["success"]:
                processing_method = result.get("processing", "pattern")
                if processing_method == "ai" and verbose:
                    typer.echo(f"Processing: AI-powered")

                typer.echo(f"Intent: {result['intent']}")
                if verbose:
                    typer.echo(f"Entities: {result['entities']}")
                    typer.echo(f"Command: {result['command']}")

                # Get the message or default
                message = result.get("message", "Command executed successfully")

                # If this is a cleanup operation that got converted to find-only operation, add note
                if result["intent"].startswith("cleanup_") and output is None:
                    message += "\nNOTE: No output file provided. This is a find-only operation."
                    message += "\nUse -o/--output to specify an output file for actual cleanup."

                # Show result message
                typer.echo(message)

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
                                                    
                                            # Add context information if available
                                            if "context" in obj:
                                                details.append(f"context:{obj['context']}")
                                            elif "context_name" in obj:
                                                if "context_type" in obj and obj["context_type"] == "device_group":
                                                    details.append(f"context:Device Group: {obj['context_name']}")
                                                elif "context_type" in obj and obj["context_type"] == "vsys":
                                                    details.append(f"context:VSYS: {obj['context_name']}")
                                                else:
                                                    details.append(f"context:{obj['context_name']}")
                                                
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
                                object_type = result_data.get("object_type", "")

                                # Determine if this is an "all" objects search
                                if object_type.lower() == "all":
                                    typer.echo(
                                        f"\nFound {result_data.get('count')} duplicate objects across {result_data.get('unique_values')} values (multiple object types)"
                                    )

                                    # Group by object type for better display
                                    if verbose:
                                        type_counts = {}
                                        for key in result_data.get("duplicates", {}).keys():
                                            if key.startswith("_"):
                                                continue
                                            type_parts = key.split(":", 1)
                                            if len(type_parts) > 1:
                                                obj_type = type_parts[0]
                                                type_counts[obj_type] = type_counts.get(obj_type, 0) + 1

                                        # Display counts by type
                                        if type_counts:
                                            typer.echo("\nBreakdown by type:")
                                            for obj_type, count in type_counts.items():
                                                typer.echo(f"  - {obj_type}: {count} duplicated values")
                                else:
                                    typer.echo(
                                        f"\nFound {result_data.get('count')} duplicate {object_type} objects across {result_data.get('unique_values')} values"
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
        "add tag 'reviewed' to all security policies",
        "disable all nat policies",
        "enable all policies that have deny action",
        "set action to allow for all security rules in device group DG1",
        "enable logging for all security policies",
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
    typer.echo("  --output      : Specify the output file for modified configurations (for cleanup operations)")
    typer.echo("  --report-file : Specify the output file for report/results (separate from config changes)")
    typer.echo("  --dry-run     : Preview changes without modifying the configuration")
    typer.echo("  --format      : Output format (text, json, table, csv, yaml, html)")
    typer.echo("  --verbose     : Show detailed information about the query processing")
    typer.echo("  --ai/--no-ai  : Enable or disable AI processing (if available)")
    typer.echo("  --ai-provider : AI provider to use (openai, anthropic)")
    typer.echo("  --ai-model    : AI model to use (e.g., gpt-3.5-turbo, claude-3-haiku)")
    
    typer.echo("\nOutput and Reports:")
    typer.echo("  For queries that modify configuration (cleanup operations):")
    typer.echo("    - Use --output to save the modified configuration")
    typer.echo("    - Use --report-file to save a separate report of changes")
    typer.echo("  For query-only operations (listing, finding duplicates, etc.):")
    typer.echo("    - Use --report-file to save the results in your chosen format")

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
    report_file: Optional[str] = typer.Option(
        None,
        "--report-file",
        "-r",
        help="Output file for report/results (use with --format to specify format)",
    ),
    dry_run: bool = ConfigOptions.dry_run(),
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format (text, json, table, csv, yaml, html)"
    ),
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

        # Start an interactive session with HTML reports saved to a file
        python cli.py nlq interactive --format html --report-file reports/session_results.html

        # Start an interactive session with config modifications and HTML reporting
        python cli.py nlq interactive --config firewall.xml --output modifications.xml --report-file reports/changes.html --format html

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
    
    # Display selected output paths
    if output:
        typer.echo(f"Configuration modifications will be saved to: {output}")
    if report_file:
        typer.echo(f"Reports will be saved to: {report_file} (Format: {format})")
    
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
                output_json = json.dumps(result, indent=2)
                if report_file:
                    with open(report_file, "w") as f:
                        f.write(output_json)
                    typer.echo(f"Report saved to {report_file}")
                else:
                    typer.echo(output_json)
            elif format.lower() == "html":
                # HTML format using CommandBase formatter
                from ..command_base import CommandBase
                
                # Create a structured dataset for HTML report
                report_data = {
                    "nlq_info": {
                        "intent": result['intent'],
                        "success": result['success'],
                        "processing": result.get('processing', 'pattern'),
                        "message": result.get('message', 'Command executed successfully')
                    }
                }
                
                # Add result data if available
                if "result" in result and result["result"] and isinstance(result["result"], dict):
                    result_data = result["result"]
                    report_data["result"] = result_data
                    
                # Determine report type based on intent
                if result['intent'].startswith('list_'):
                    if "unused_objects" in result['intent']:
                        report_type = "Unused Objects Report"
                    elif "disabled_policies" in result['intent']:
                        report_type = "Disabled Policies Report"
                    elif "duplicate" in result['intent']:
                        report_type = "Duplicate Objects Report"
                    else:
                        report_type = "Object Listing Report"
                elif result['intent'].startswith('cleanup_'):
                    report_type = "Cleanup Operation Report"
                elif result['intent'].startswith('bulk_update_'):
                    report_type = "Policy Update Report" 
                else:
                    report_type = "Natural Language Query Report"
                    
                # Additional info to include in the report
                additional_info = {
                    "Query": query,
                    "Configuration": config,
                    "Interactive Mode": "Yes",
                    "Session Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Use CommandBase.format_output to generate HTML
                CommandBase.format_output(
                    data=report_data,
                    output_format="html",
                    output_file=report_file,
                    table_title="PANFlow Interactive NLQ Results",
                    report_type=report_type,
                    query_text=query,
                    config_file=config,
                    additional_info=additional_info
                )
                
                if report_file:
                    typer.echo(f"HTML report saved to {report_file}")
                else:
                    # Text summary for console
                    typer.echo(f"Query: {query}")
                    typer.echo(f"Intent: {result['intent']}")
                    typer.echo(f"Success: {result['success']}")
                    typer.echo("Use --report-file to save the HTML report to a file")
            elif format.lower() == "yaml":
                try:
                    import yaml
                    yaml_output = yaml.dump(result, sort_keys=False, default_flow_style=False)
                    if report_file:
                        with open(report_file, "w") as f:
                            f.write(yaml_output)
                        typer.echo(f"Report saved to {report_file}")
                    else:
                        typer.echo(yaml_output)
                except ImportError:
                    typer.echo("Error: PyYAML not installed. Install with 'pip install pyyaml'")
            elif format.lower() == "csv":
                # Basic CSV output for interactive mode
                import csv
                import io
                
                # Determine if we're writing to a file or a string buffer
                if report_file:
                    output_file = open(report_file, "w", newline="")
                    csv_writer = csv.writer(output_file)
                else:
                    output_stream = io.StringIO()
                    csv_writer = csv.writer(output_stream)
                
                # Write basic information
                csv_writer.writerow(["Intent", result["intent"]])
                csv_writer.writerow(["Success", str(result["success"])])
                csv_writer.writerow(["Processing", result.get("processing", "pattern")])
                csv_writer.writerow(["Message", result.get("message", "Command executed successfully")])
                
                # If we have result objects, add them to CSV
                if "result" in result and result["result"] and isinstance(result["result"], dict):
                    result_data = result["result"]
                    
                    # Special handling for objects with context information
                    if "objects" in result_data and isinstance(result_data["objects"], list):
                        objects = result_data.get("objects", [])
                        if objects:
                            csv_writer.writerow([])  # Empty row as separator
                            
                            # Determine object type and description
                            obj_desc = "unused" if "unused_objects" in result_data else ""
                            object_type = result_data.get("object_type", "")
                            
                            # Create title based on search type
                            if result_data.get("is_duplicate_search"):
                                header = f"Duplicated {object_type} Objects ({len(objects)})"
                                if result_data.get("unique_values"):
                                    header += f" across {result_data.get('unique_values')} unique values"
                            else:
                                header = f"{obj_desc} {object_type} Objects ({len(objects)})".strip().capitalize()
                                
                            csv_writer.writerow([header])
                            
                            # Check if objects have detailed information
                            if objects and isinstance(objects[0], dict):
                                # Determine which columns are needed based on the data
                                columns = ["Name"]
                                
                                # Check if we have context information available
                                has_context = any("context" in obj for obj in objects) or any("context_name" in obj for obj in objects)
                                
                                for field in ["ip-netmask", "ip-range", "fqdn", "protocol", "port", "description"]:
                                    if any(field in obj for obj in objects):
                                        columns.append(field.capitalize())
                                
                                # Add context column if available
                                if has_context:
                                    columns.append("Context")
                                        
                                # Write header row
                                csv_writer.writerow(columns)
                                
                                # Write object data
                                for obj in objects:
                                    row_data = [obj.get("name", "unnamed")]
                                    
                                    # Process standard fields
                                    for field in columns[1:-1] if has_context else columns[1:]:  # Skip the name column and context (if present)
                                        field_key = field.lower()
                                        row_data.append(str(obj.get(field_key, "")))
                                    
                                    # Add context information if available
                                    if has_context and "Context" in columns:
                                        if "context" in obj:
                                            row_data.append(str(obj.get("context", "")))
                                        elif "context_name" in obj:
                                            if "context_type" in obj and obj["context_type"] == "device_group":
                                                row_data.append(f"Device Group: {obj['context_name']}")
                                            elif "context_type" in obj and obj["context_type"] == "vsys":
                                                row_data.append(f"VSYS: {obj['context_name']}")
                                            else:
                                                row_data.append(str(obj.get("context_name", "")))
                                        else:
                                            row_data.append("")
                                        
                                    csv_writer.writerow(row_data)
                            else:
                                # Simple objects list with possible context info
                                has_context = any(isinstance(obj, dict) and ("context" in obj or "context_name" in obj) for obj in objects)
                                
                                if has_context:
                                    csv_writer.writerow(["Name", "Context"])
                                    for obj in objects:
                                        if isinstance(obj, str):
                                            csv_writer.writerow([obj, ""])
                                        elif isinstance(obj, dict):
                                            obj_name = obj.get("name", str(obj))
                                            # Format context information
                                            context_str = ""
                                            if "context" in obj:
                                                context_str = str(obj.get("context", ""))
                                            elif "context_name" in obj:
                                                if "context_type" in obj and obj["context_type"] == "device_group":
                                                    context_str = f"Device Group: {obj['context_name']}"
                                                elif "context_type" in obj and obj["context_type"] == "vsys":
                                                    context_str = f"VSYS: {obj['context_name']}"
                                                else:
                                                    context_str = str(obj.get("context_name", ""))
                                            csv_writer.writerow([obj_name, context_str])
                                        else:
                                            csv_writer.writerow([str(obj), ""])
                                else:
                                    # Simple list without context
                                    csv_writer.writerow(["Name"])
                                    for obj in objects:
                                        if isinstance(obj, str):
                                            csv_writer.writerow([obj])
                                        else:
                                            csv_writer.writerow([str(obj)])
                    else:
                        # Handle other result types
                        for key, value in result_data.items():
                            if isinstance(value, list) and len(value) > 0:
                                csv_writer.writerow([])
                                csv_writer.writerow([f"{key} ({len(value)}):"])
                                for item in value:
                                    if isinstance(item, dict):
                                        csv_writer.writerow([json.dumps(item)])
                                    else:
                                        csv_writer.writerow([str(item)])
                            elif not isinstance(value, dict):
                                csv_writer.writerow([key, str(value)])
                
                if report_file:
                    output_file.close()
                    typer.echo(f"Report saved to {report_file}")
                else:
                    typer.echo(output_stream.getvalue())
                    output_stream.close()
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

                    # Get the message or default
                    message = result.get("message", "Command executed successfully")
                    if not message.endswith("."):
                        message += "."

                    # If this is a cleanup operation that got converted to find-only operation, add note
                    if result["intent"].startswith("cleanup_") and output is None:
                        message += "\nNOTE: No output file provided. This is a find-only operation."
                        message += "\nUse -o/--output to specify an output file for actual cleanup."

                    # Show result message
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

                            # For bulk update policy operations
                            elif "updated_policies" in result_data and isinstance(
                                result_data["updated_policies"], list
                            ):
                                if result_data["updated_policies"]:
                                    # Get operation details
                                    operation = result_data.get("operation", "updated")
                                    value = result_data.get("value", "")
                                    dry_run = result_data.get("dry_run", False)

                                    # Format title based on operation type
                                    operation_desc = {
                                        "enable": "Enabled",
                                        "disable": "Disabled",
                                        "add_tag": f"Added tag '{value}' to",
                                        "set_action": f"Set action '{value}' for",
                                        "enable_logging": "Enabled logging for",
                                        "disable_logging": "Disabled logging for",
                                    }.get(operation, "Updated")

                                    if dry_run:
                                        typer.echo(f"\nWould {operation_desc.lower()} {result_data.get('count', len(result_data['updated_policies']))} policies (dry run):")
                                    else:
                                        typer.echo(f"\n{operation_desc} {result_data.get('count', len(result_data['updated_policies']))} policies:")

                                    for policy in result_data["updated_policies"]:
                                        if isinstance(policy, dict) and "name" in policy:
                                            policy_name = policy["name"]
                                            if "policy_type" in policy:
                                                typer.echo(f"  - {policy_name} ({policy['policy_type']})")
                                            else:
                                                typer.echo(f"  - {policy_name}")
                                        else:
                                            typer.echo(f"  - {policy}")
                                else:
                                    typer.echo("\nNo policies were updated.")

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
                                                        
                                                # Add context information if available
                                                if "context" in obj:
                                                    details.append(f"context:{obj['context']}")
                                                elif "context_name" in obj:
                                                    if "context_type" in obj and obj["context_type"] == "device_group":
                                                        details.append(f"context:Device Group: {obj['context_name']}")
                                                    elif "context_type" in obj and obj["context_type"] == "vsys":
                                                        details.append(f"context:VSYS: {obj['context_name']}")
                                                    else:
                                                        details.append(f"context:{obj['context_name']}")
                                                        
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
