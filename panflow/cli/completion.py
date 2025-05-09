"""
CLI completion support for PANFlow.

This module provides functions for generating and installing shell completion scripts
for the PANFlow CLI. Supported shells include bash, zsh, and fish.
"""

import os
import sys
import typer
import shlex
import platform
import subprocess
from typing import Optional
from pathlib import Path

def detect_shell() -> str:
    """
    Detect the current shell.
    
    Returns:
        str: The detected shell (bash, zsh, fish) or 'unknown'
    """
    # Check environment variable first
    shell_path = os.environ.get("SHELL", "")
    if shell_path:
        shell_name = os.path.basename(shell_path)
        if shell_name in ["bash", "zsh", "fish"]:
            return shell_name
    
    # If we can't determine from env var, try platform-specific approaches
    if platform.system() == "Windows":
        # PowerShell or CMD, we'll default to bash for WSL users
        return "bash"
    
    # Default to bash as fallback
    return "bash"

def generate_completion_script(shell: Optional[str] = None) -> str:
    """
    Generate the completion script for the specified shell.
    
    Args:
        shell: The shell to generate the script for (bash, zsh, fish)
        
    Returns:
        str: The completion script content
    """
    shell = shell or detect_shell()
    
    # Use typer's completion command to generate the script
    cmd = [sys.executable, "-m", "typer", "panflow.cli.app", "utils", "completion"]
    
    if shell:
        cmd.extend(["--shell", shell])
    
    try:
        result = subprocess.run(
            cmd, 
            text=True, 
            capture_output=True, 
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error generating completion script: {e}", err=True)
        typer.echo(e.stderr, err=True)
        raise typer.Exit(1)

def show_completion(shell: Optional[str] = None):
    """
    Show the completion script for the specified shell.
    
    Args:
        shell: The shell to generate the script for (bash, zsh, fish)
    """
    shell = shell or detect_shell()
    script = generate_completion_script(shell)
    typer.echo(script)
    
    # Show installation instructions
    typer.echo()
    typer.echo(f"# To install completion for {shell}, run:")
    if shell == "bash":
        typer.echo("# panflow completion --install")
        typer.echo("# Or add this line to your ~/.bashrc:")
        typer.echo(f"# eval \"$({' '.join(sys.argv[:-1]) if len(sys.argv) > 1 else sys.argv[0]} completion --show)\"")
    elif shell == "zsh":
        typer.echo("# panflow completion --install")
        typer.echo("# Or add this line to your ~/.zshrc:")
        typer.echo(f"# eval \"$({' '.join(sys.argv[:-1]) if len(sys.argv) > 1 else sys.argv[0]} completion --show)\"")
    elif shell == "fish":
        typer.echo("# panflow completion --install")
        typer.echo("# Or add this line to your ~/.config/fish/config.fish:")
        typer.echo(f"# {' '.join(sys.argv[:-1]) if len(sys.argv) > 1 else sys.argv[0]} completion --show | source")

def install_completion(shell: Optional[str] = None, custom_path: Optional[Path] = None):
    """
    Install the completion script for the specified shell.
    
    Args:
        shell: The shell to install the script for (bash, zsh, fish)
        custom_path: Custom path to install the completion script
    """
    shell = shell or detect_shell()
    script = generate_completion_script(shell)
    
    # Determine the appropriate location for the completion script
    if custom_path:
        completion_path = custom_path
    else:
        home = Path.home()
        if shell == "bash":
            # Different locations based on OS
            if platform.system() == "Darwin":  # macOS
                # Try to find Homebrew's bash-completion directory first
                if Path("/usr/local/etc/bash_completion.d").exists():
                    completion_path = Path("/usr/local/etc/bash_completion.d/panflow")
                elif Path("/opt/homebrew/etc/bash_completion.d").exists():
                    completion_path = Path("/opt/homebrew/etc/bash_completion.d/panflow")
                else:
                    # Fall back to user's directory
                    completion_path = home / ".bash_completion.d" / "panflow"
                    os.makedirs(home / ".bash_completion.d", exist_ok=True)
                    
                    # Add line to .bash_profile if not already there
                    bash_profile = home / ".bash_profile"
                    bash_completion_line = f'[ -f "$HOME/.bash_completion.d/panflow" ] && . "$HOME/.bash_completion.d/panflow"'
                    if bash_profile.exists():
                        with open(bash_profile, "r") as f:
                            content = f.read()
                        if bash_completion_line not in content:
                            with open(bash_profile, "a") as f:
                                f.write(f"\n# PANFlow completion\n{bash_completion_line}\n")
            else:  # Linux and others
                if Path("/etc/bash_completion.d").exists() and os.access("/etc/bash_completion.d", os.W_OK):
                    completion_path = Path("/etc/bash_completion.d/panflow")
                else:
                    # Fall back to user's directory
                    completion_path = home / ".local" / "share" / "bash-completion" / "completions" / "panflow"
                    os.makedirs(completion_path.parent, exist_ok=True)
        elif shell == "zsh":
            if platform.system() == "Darwin":  # macOS
                # Try Homebrew's zsh site-functions
                if Path("/usr/local/share/zsh/site-functions").exists():
                    completion_path = Path("/usr/local/share/zsh/site-functions/_panflow")
                elif Path("/opt/homebrew/share/zsh/site-functions").exists():
                    completion_path = Path("/opt/homebrew/share/zsh/site-functions/_panflow")
                else:
                    # Fall back to user's directory
                    completion_path = home / ".zsh" / "completions" / "_panflow"
                    os.makedirs(completion_path.parent, exist_ok=True)
                    
                    # Add line to .zshrc if not already there
                    zshrc = home / ".zshrc"
                    zsh_completion_line = f'fpath=($HOME/.zsh/completions $fpath)'
                    zsh_compinit_line = 'autoload -Uz compinit && compinit'
                    if zshrc.exists():
                        with open(zshrc, "r") as f:
                            content = f.read()
                        to_append = ""
                        if zsh_completion_line not in content:
                            to_append += f"\n# PANFlow completion\n{zsh_completion_line}\n"
                        if zsh_compinit_line not in content:
                            to_append += f"{zsh_compinit_line}\n"
                        if to_append:
                            with open(zshrc, "a") as f:
                                f.write(to_append)
            else:  # Linux and others
                if Path("/usr/share/zsh/site-functions").exists() and os.access("/usr/share/zsh/site-functions", os.W_OK):
                    completion_path = Path("/usr/share/zsh/site-functions/_panflow")
                else:
                    # Fall back to user's directory
                    completion_path = home / ".zsh" / "completions" / "_panflow"
                    os.makedirs(completion_path.parent, exist_ok=True)
                    
                    # Add line to .zshrc if not already there
                    zshrc = home / ".zshrc"
                    zsh_completion_line = f'fpath=($HOME/.zsh/completions $fpath)'
                    zsh_compinit_line = 'autoload -Uz compinit && compinit'
                    if zshrc.exists():
                        with open(zshrc, "r") as f:
                            content = f.read()
                        to_append = ""
                        if zsh_completion_line not in content:
                            to_append += f"\n# PANFlow completion\n{zsh_completion_line}\n"
                        if zsh_compinit_line not in content:
                            to_append += f"{zsh_compinit_line}\n"
                        if to_append:
                            with open(zshrc, "a") as f:
                                f.write(to_append)
        elif shell == "fish":
            # Fish completions go in a standard location
            fish_dir = home / ".config" / "fish" / "completions"
            os.makedirs(fish_dir, exist_ok=True)
            completion_path = fish_dir / "panflow.fish"
        else:
            typer.echo(f"Unsupported shell: {shell}", err=True)
            raise typer.Exit(1)
    
    # Make sure the parent directory exists
    os.makedirs(completion_path.parent, exist_ok=True)
    
    # Write the completion script
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
        
        return completion_path
    except IOError as e:
        typer.echo(f"Error installing completion script: {e}", err=True)
        
        # Suggest alternative with sudo if permission denied
        if isinstance(e, PermissionError):
            typer.echo("Try running with sudo or use a custom path:")
            typer.echo(f"sudo panflow completion --install --shell {shell}")
            typer.echo("or")
            typer.echo(f"panflow completion --install --shell {shell} --path /path/to/custom/location")
        
        raise typer.Exit(1)