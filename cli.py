#!/usr/bin/env python3
"""
PANFlow CLI entry point.

This script serves as the entry point for the PANFlow command-line interface.
"""

import sys
import typer
from typing import Optional
from pathlib import Path
from panflow.cli import app
from panflow.cli.completion import install_completion, show_completion


@app.callback()
def callback():
    """
    PANFlow CLI - Palo Alto Networks Configuration Management Tool.
    """
    pass


@app.command()
def completion(
    shell: Optional[str] = typer.Option(
        None,
        "--shell",
        "-s",
        help="Shell type (bash, zsh, fish)",
    ),
    install: bool = typer.Option(
        False, "--install", "-i", help="Install completion for the specified shell"
    ),
    show: bool = typer.Option(False, "--show", help="Show completion script"),
    path: Optional[Path] = typer.Option(
        None, "--path", "-p", help="Custom path to install the completion script"
    ),
    # Add a specific parameter to detect completion requests from the shell
    complete_args: Optional[str] = typer.Argument(None, hidden=True),
):
    """
    Shell completion support.

    Enable tab completion for CLI commands by installing the appropriate
    script for your shell. Supports Bash, Zsh, and Fish.

    Examples:
        # Show completion script for current shell:
        panflow completion --show

        # Install completion for your shell:
        panflow completion --install

        # Install completion for a specific shell:
        panflow completion --install --shell bash
    """
    # Handle shell completion requests
    if complete_args is not None:
        # This is a request from the shell for completions
        # We would parse the args and provide completions here
        # For now, just return empty to avoid errors
        return ""

    if show:
        show_completion(shell)
        raise typer.Exit()

    if install:
        install_completion(shell, path)
        raise typer.Exit()

    # If no options provided, show help
    typer.echo("Use --install to install completion or --show to display completion script")
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
