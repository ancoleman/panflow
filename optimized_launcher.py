#!/usr/bin/env python3
"""
Ultra-Optimized Launcher Script for PANFlow.

This launcher uses extreme optimization techniques for fast startup:
1. Deferred imports - only imports modules when they're actually needed
2. Conditional path selection - avoids expensive operations based on command
3. Early exit paths for common commands like --help
4. Specialized handling for completion to improve shell response time
"""

import sys
import os

# Apply performance optimizations
os.environ['PYTHONOPTIMIZE'] = '2'  # -O -O: remove asserts and docstrings

# Disable warnings that slow down startup
import warnings
warnings.filterwarnings("ignore")

# Add script directory to PATH for importing panflow
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Check arguments before importing anything else
if len(sys.argv) <= 1 or sys.argv[1] in ('--help', '-h'):
    # Hard-coded help text for fastest response
    print("""
 Usage: panflow [OPTIONS] COMMAND [ARGS]...                                     
                                                                                
 PANFlow CLI                                                                    
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --verbose             -v            Enable verbose output                    │
│ --quiet               -q            Suppress console output                  │
│ --log-level           -l      TEXT  Set log level (debug, info, warning,     │
│                                     error, critical)                         │
│                                     [default: info]                          │
│ --log-file            -f      TEXT  Log to file [default: None]              │
│ --install-completion                Install completion for the current       │
│                                     shell.                                   │
│ --show-completion                   Show completion for the current shell,   │
│                                     to copy it or customize the              │
│                                     installation.                            │
│ --help                              Show this message and exit.              │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ cleanup        Clean up unused objects and policies                          │
│ completion     Shell completion support.                                     │
│ config         Configuration management commands                             │
│ deduplicate    Find and merge duplicate objects                              │
│ group          Group management commands                                     │
│ merge          Policy and Object merge commands                              │
│ nlq            Natural language query interface for PANFlow                  │
│ object         Object management commands                                    │
│ policy         Policy management commands                                    │
│ query          Query PAN-OS configurations using graph query language        │
│ report         Report generation commands                                    │
╰──────────────────────────────────────────────────────────────────────────────╯
""")
    sys.exit(0)

if sys.argv[1] in ('--version', '-V'):
    # Hard-coded version for fastest response
    print("PANFlow v0.3.0")
    sys.exit(0)

if sys.argv[1] == 'object' and len(sys.argv) == 2:
    # Hard-coded object help for fastest response
    print("""
 Usage: panflow object [OPTIONS] COMMAND [ARGS]...
 
 Object management commands
 
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ add             Add objects to configuration                                 │
│ delete          Delete objects from configuration                            │
│ filter          Filter objects by name, type, or group                       │
│ list            List objects in configuration                                │
│ set-group       Add objects to a group                                       │
│ update          Update object attributes                                     │
╰──────────────────────────────────────────────────────────────────────────────╯
""")
    sys.exit(0)

# Check if this is a completion request (special fast path)
is_completion = len(sys.argv) > 1 and ("__complete" in sys.argv or sys.argv[1] == "__complete")

# Import the minimal components required based on the request
if is_completion:
    # Only import what's needed for completion - very minimal
    from panflow.cli import app

    if __name__ == "__main__":
        # Run with completion arguments
        app()
else:
    # Import only what's needed for normal execution
    from panflow.cli import app

    # Handle specific common commands with pre-optimized paths
    if len(sys.argv) > 1 and sys.argv[1] == "completion":
        # For completion command, we need to import typer
        import typer
        from typing import Optional
        from pathlib import Path
        
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
            script = ""
            if shell == "bash":
                script = f"""
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
            elif shell == "zsh":
                script = f"""
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
            elif shell == "fish":
                script = f"""
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

    if __name__ == "__main__":
        # Run with standard arguments
        app()