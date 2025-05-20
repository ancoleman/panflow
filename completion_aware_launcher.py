#!/usr/bin/env python3
"""
Completion-Aware PANFlow Launcher Script.

This launcher is designed to handle completion requests properly in the packaged application.
"""

import sys
import os
import subprocess
import shutil
import typer
from typing import Optional, List
from pathlib import Path

# Add script directory to PATH for importing panflow
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Import CLI app from panflow
from panflow.cli import app

# Define completion function for the packaged app
@app.command()
def completion(
    shell: Optional[str] = typer.Option(
        None, "--shell", "-s", help="Shell type (bash, zsh, fish)"
    ),
    install: bool = typer.Option(
        False, "--install", "-i", help="Install completion for the specified shell"
    ),
    show: bool = typer.Option(
        False, "--show", help="Show completion script"
    ),
    path: Optional[Path] = typer.Option(
        None, "--path", "-p", help="Custom path to install the completion script"
    ),
):
    """
    Shell completion support.
    
    Enable tab completion for CLI commands by installing the appropriate 
    script for your shell. Supports Bash, Zsh, and Fish.
    """
    # Detect shell if not specified
    if not shell:
        shell_path = os.environ.get("SHELL", "")
        if shell_path:
            shell_name = os.path.basename(shell_path)
            if shell_name in ["bash", "zsh", "fish"]:
                shell = shell_name
            else:
                shell = "bash"  # Default to bash
        else:
            shell = "bash"  # Default to bash
    
    # Generate completion script based on shell
    if shell == "bash":
        script = generate_bash_completion()
    elif shell == "zsh":
        script = generate_zsh_completion()
    elif shell == "fish":
        script = generate_fish_completion()
    else:
        typer.echo(f"Unsupported shell: {shell}", err=True)
        raise typer.Exit(1)
    
    if show:
        typer.echo(script)
        raise typer.Exit()
    
    if install:
        # Determine installation path
        if path:
            completion_path = path
        else:
            home = Path.home()
            if shell == "bash":
                # Different locations based on OS
                if sys.platform == "darwin":  # macOS
                    # Try to find Homebrew's bash-completion directory
                    if Path("/usr/local/etc/bash_completion.d").exists():
                        completion_path = Path("/usr/local/etc/bash_completion.d/panflow")
                    elif Path("/opt/homebrew/etc/bash_completion.d").exists():
                        completion_path = Path("/opt/homebrew/etc/bash_completion.d/panflow")
                    else:
                        # Fall back to user's directory
                        completion_path = home / ".bash_completion.d" / "panflow"
                        os.makedirs(home / ".bash_completion.d", exist_ok=True)
                else:  # Linux and others
                    completion_path = home / ".local" / "share" / "bash-completion" / "completions" / "panflow"
                    os.makedirs(completion_path.parent, exist_ok=True)
            elif shell == "zsh":
                if sys.platform == "darwin":  # macOS
                    if Path("/usr/local/share/zsh/site-functions").exists():
                        completion_path = Path("/usr/local/share/zsh/site-functions/_panflow")
                    elif Path("/opt/homebrew/share/zsh/site-functions").exists():
                        completion_path = Path("/opt/homebrew/share/zsh/site-functions/_panflow")
                    else:
                        completion_path = home / ".zsh" / "completions" / "_panflow"
                        os.makedirs(completion_path.parent, exist_ok=True)
                else:  # Linux and others
                    completion_path = home / ".zsh" / "completions" / "_panflow"
                    os.makedirs(completion_path.parent, exist_ok=True)
            elif shell == "fish":
                completion_path = home / ".config" / "fish" / "completions" / "panflow.fish"
                os.makedirs(completion_path.parent, exist_ok=True)
        
        # Make sure the directory exists
        os.makedirs(completion_path.parent, exist_ok=True)
        
        # Write completion script
        try:
            with open(completion_path, "w") as f:
                f.write(script)
            typer.echo(f"Completion script installed to {completion_path}")
            
            # Additional instructions
            if shell == "bash":
                typer.echo("You may need to restart your shell or source the completion script:")
                typer.echo(f"source {completion_path}")
            elif shell == "zsh":
                typer.echo("You may need to restart your shell or reload completions:")
                typer.echo("autoload -Uz compinit && compinit")
            elif shell == "fish":
                typer.echo("Completion should be available immediately in fish.")
                
        except Exception as e:
            typer.echo(f"Error installing completion script: {e}", err=True)
            raise typer.Exit(1)
            
    if not (show or install):
        typer.echo("Use --install to install completion or --show to display completion script")
        raise typer.Exit(1)

def generate_bash_completion() -> str:
    """Generate bash completion script."""
    return f"""
# panflow completion script for bash
_panflow_completion() {{
    local IFS=$'\\n'
    local response

    response=$(COMP_WORDS="${{COMP_WORDS[*]}}" COMP_CWORD=$COMP_CWORD {sys.argv[0]} __complete "${{COMP_WORDS[@]:1}}" 2>/dev/null)

    for completion in $response; do
        IFS=',' read type value <<< "$completion"
        if [[ $type == 'dir' ]]; then
            COMPREPLY=( $(compgen -d -- "$value") )
            return
        elif [[ $type == 'file' ]]; then
            COMPREPLY=( $(compgen -f -- "$value") )
            return
        elif [[ $type == 'plain' ]]; then
            COMPREPLY+=($value)
        fi
    done
}}

complete -o nosort -F _panflow_completion panflow
"""

def generate_zsh_completion() -> str:
    """Generate zsh completion script."""
    return f"""
#compdef panflow

_panflow_completion() {{
    local -a completions
    local -a completions_with_descriptions
    local -a response
    
    response=($({sys.argv[0]} __complete "${{words[@]:1}}" 2>/dev/null))
    
    for key value in $response; do
        completions+=("$value")
    done
    
    _describe -t options "options" completions
}}

compdef _panflow_completion panflow
"""

def generate_fish_completion() -> str:
    """Generate fish completion script."""
    return f"""
function __fish_panflow_complete
    set -l response
    
    for i in (commandline -opc)
        set -a response $i
    end
    
    set -l cmd ({sys.argv[0]} __complete (string join " " $response) 2>/dev/null)
    
    for i in $cmd
        echo $i
    end
end

complete -f -c panflow -a "(__fish_panflow_complete)"
"""

if __name__ == "__main__":
    # When run as the main script, run the CLI app
    app()