"""
Command-line interface for graph queries.

This module implements the CLI commands for querying PAN-OS configurations
using the graph query language.
"""

import logging
import sys
import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

import typer
from lxml import etree
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax

from panflow.core.xml.base import load_xml_file
from panflow.core.graph_utils import ConfigGraph
from panflow.core.query_language import Query, Lexer
from panflow.core.query_engine import QueryExecutor
from panflow.core.graph_service import GraphService
from panflow.cli.common import CommonOptions, file_callback, output_callback

# Set up logging
logger = logging.getLogger(__name__)
console = Console()

# Create query command app
app = typer.Typer(help="Query PAN-OS configurations using graph query language")


@app.command()
def execute(
    config_file: Path = typer.Option(
        ...,
        "--config",
        "-c",
        help="Path to the PAN-OS configuration file",
        callback=file_callback,
    ),
    query: str = typer.Option(
        ...,
        "--query",
        "-q",
        help="Graph query to execute",
    ),
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format (table, json, text, csv, yaml, html)",
        callback=output_callback,
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path",
    ),
):
    """
    Execute a graph query on a PAN-OS configuration.

    Example:
        panflow query execute -c config.xml -q "MATCH (a:address) RETURN a.name, a.value"
    """
    logger.info(f"Executing query on configuration file: {config_file}")
    logger.debug(f"Query: {query}")

    try:
        # Load the XML configuration
        xml_root = load_xml_file(config_file)

        # Use GraphService to execute the query
        graph_service = GraphService()
        results = graph_service.execute_custom_query(xml_root, query)

        # Display the results
        _display_results(results, output_format, output_file)

    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command()
def interactive(
    config_file: Path = typer.Option(
        ...,
        "--config",
        "-c",
        help="Path to the PAN-OS configuration file",
        callback=file_callback,
    ),
):
    """
    Start an interactive query session.

    Example:
        panflow query interactive -c config.xml
    """
    logger.info(f"Starting interactive query session on configuration file: {config_file}")

    try:
        # Load the XML configuration
        xml_root = load_xml_file(config_file)

        # Create graph service
        graph_service = GraphService()

        console.print("[bold green]PAN-OS Graph Query Shell[/bold green]")
        console.print("Enter graph queries or 'exit' to quit")
        console.print()

        while True:
            try:
                # Get query from user
                user_input = console.input("[bold blue]query>[/bold blue] ")

                if user_input.lower() in ["exit", "quit"]:
                    break

                if not user_input.strip():
                    continue

                # Execute the query through GraphService
                results = graph_service.execute_custom_query(xml_root, user_input)

                # Display the results as a table
                _display_results(results, "table", None)

            except KeyboardInterrupt:
                console.print("\nUse 'exit' to quit")
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {str(e)}")

    except Exception as e:
        logger.error(f"Error in interactive session: {str(e)}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command()
def verify(
    query: str = typer.Option(
        ...,
        "--query",
        "-q",
        help="Graph query to verify",
    ),
):
    """
    Verify a graph query syntax without executing it.

    Example:
        panflow query verify -q "MATCH (a:address) RETURN a.name"
    """
    logger.info(f"Verifying query syntax: {query}")

    try:
        # Parse the query to verify syntax
        lexer = Lexer(query)
        tokens = lexer.tokenize()

        # Display tokens
        table = Table(title="Query Tokens")
        table.add_column("Type", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Position", style="blue")

        for token in tokens:
            if token.type.name == "EOF":
                continue
            table.add_row(token.type.name, token.value, str(token.position))

        console.print(table)

        # Try to parse the query
        parsed_query = Query(query)

        # Display success message
        console.print("[bold green]Query syntax is valid[/bold green]")

    except Exception as e:
        logger.error(f"Error verifying query: {str(e)}")
        console.print(f"[bold red]Syntax Error:[/bold red] {str(e)}")
        sys.exit(1)


@app.command()
def example():
    """
    Show example graph queries.

    Example:
        panflow query example
    """
    examples = [
        {
            "name": "Find all address objects",
            "query": "MATCH (a:address) RETURN a.name, a.value, a.addr_type",
            "description": "This query returns all address objects with their names, values, and types.",
        },
        {
            "name": "Find all address groups and their members",
            "query": "MATCH (g:address-group)-[:contains]->(a:address) RETURN g.name, a.name",
            "description": "This query returns all address groups and their member addresses.",
        },
        {
            "name": "Find all security rules using a specific address",
            "query": "MATCH (r:security-rule)-[:uses-source|uses-destination]->(a:address) WHERE a.name == 'web-server' RETURN r.name",
            "description": "This query returns all security rules that use 'web-server' as a source or destination.",
        },
        {
            "name": "Find all unused address objects",
            "query": "MATCH (a:address) WHERE NOT ((:security-rule)-[:uses-source|uses-destination]->(a)) AND NOT ((:address-group)-[:contains]->(a)) RETURN a.name",
            "description": "This query returns all address objects that are not used in any security rule or address group.",
        },
        {
            "name": "Find rules allowing specific services",
            "query": "MATCH (r:security-rule)-[:uses-service]->(s:service) WHERE s.name == 'http' OR s.name == 'https' RETURN r.name",
            "description": "This query returns all security rules that allow HTTP or HTTPS services.",
        },
    ]

    table = Table(title="Example Graph Queries")
    table.add_column("Name", style="cyan")
    table.add_column("Query", style="green")
    table.add_column("Description", style="blue")

    for example in examples:
        table.add_row(example["name"], example["query"], example["description"])

    console.print(table)


def _display_results(
    results: List[Dict[str, Any]], output_format: str, output_file: Optional[Path]
):
    """
    Display or save query results.

    Args:
        results: Query results
        output_format: Output format (table, json, csv)
        output_file: Optional output file path
    """
    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    if output_format == "json":
        output = json.dumps(results, indent=2)
        if output_file:
            with open(output_file, "w") as f:
                f.write(output)
        else:
            syntax = Syntax(output, "json", theme="monokai", line_numbers=True)
            console.print(syntax)

    elif output_format == "csv":
        if not output_file:
            console.print("[yellow]CSV format requires an output file[/yellow]")
            return

        # Get header from first result
        headers = list(results[0].keys())

        # Write CSV file
        with open(output_file, "w") as f:
            # Write header
            f.write(",".join([f'"{h}"' for h in headers]) + "\n")

            # Write rows
            for row in results:
                values = []
                for header in headers:
                    value = row.get(header, "")
                    if isinstance(value, str):
                        # Escape quotes and wrap in quotes
                        escaped_value = value.replace('"', '\\"')
                        value = f'"{escaped_value}"'
                    else:
                        value = str(value)
                    values.append(value)
                f.write(",".join(values) + "\n")

        console.print(f"[green]Results saved to {output_file}[/green]")

    else:  # table format
        # Get columns from first result
        columns = list(results[0].keys())

        table = Table()
        for column in columns:
            table.add_column(column, style="cyan")

        # Add rows
        for row in results:
            table.add_row(*[str(row.get(col, "")) for col in columns])

        if output_file:
            # Save table as text
            with open(output_file, "w") as f:
                # Write header
                header = " | ".join(columns)
                f.write(header + "\n")
                f.write("-" * len(header) + "\n")

                # Write rows
                for row in results:
                    f.write(" | ".join([str(row.get(col, "")) for col in columns]) + "\n")

            console.print(f"[green]Results saved to {output_file}[/green]")
        else:
            console.print(table)
