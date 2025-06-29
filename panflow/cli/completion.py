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

    # We're going to generate the completion scripts ourselves
    # since the typer.__main__ module doesn't exist
    if shell == "bash":
        return generate_bash_completion()
    elif shell == "zsh":
        return generate_zsh_completion()
    elif shell == "fish":
        return generate_fish_completion()
    else:
        typer.echo(f"Unsupported shell: {shell}", err=True)
        raise typer.Exit(1)

def generate_bash_completion() -> str:
    """Generate bash completion script."""
    app_name = "panflow"
    return f'''
# panflow completion script for bash
_panflow_completion() {{
    local IFS=$'\\n'
    local response

    response=$(env COMP_WORDS="${{COMP_WORDS[*]}}" COMP_CWORD=$COMP_CWORD {app_name} completion)

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

complete -o nosort -F _panflow_completion {app_name}
'''

def generate_zsh_completion() -> str:
    """Generate zsh completion script."""
    app_name = "panflow"
    return f'''
#compdef {app_name}

_panflow_completion() {{
    local -a completions
    local -a completions_with_descriptions
    local -a response

    response=("$({app_name} completion "$words")")

    for key value in $response; do
        completions+=("$value")
    done

    # Sort the completions case-insensitively
    for i in $(echo ${{completions}} | sort | uniq); do
        completions_with_descriptions+=("$i:command description")
    done

    _describe -t options "options" completions_with_descriptions
}}

compdef _panflow_completion {app_name}
'''

def generate_fish_completion() -> str:
    """Generate fish completion script."""
    app_name = "panflow"
    return f'''
function __fish_{app_name}_complete
    set -l response

    for i in (commandline -opc)
        set -a response $i
    end

    set -l cmd ({app_name} completion (string join " " $response))

    for i in $cmd
        echo $i
    end
end

complete -f -c {app_name} -a "(__fish_{app_name}_complete)"
'''


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
        typer.echo(
            f"# eval \"$({' '.join(sys.argv[:-1]) if len(sys.argv) > 1 else sys.argv[0]} completion --show)\""
        )
    elif shell == "zsh":
        typer.echo("# panflow completion --install")
        typer.echo("# Or add this line to your ~/.zshrc:")
        typer.echo(
            f"# eval \"$({' '.join(sys.argv[:-1]) if len(sys.argv) > 1 else sys.argv[0]} completion --show)\""
        )
    elif shell == "fish":
        typer.echo("# panflow completion --install")
        typer.echo("# Or add this line to your ~/.config/fish/config.fish:")
        typer.echo(
            f"# {' '.join(sys.argv[:-1]) if len(sys.argv) > 1 else sys.argv[0]} completion --show | source"
        )


def install_completion(shell: Optional[str] = None, custom_path: Optional[Path] = None):
    """
    Install the completion script for the specified shell.

    Args:
        shell: The shell to install the script for (bash, zsh, fish)
        custom_path: Custom path to install the completion script
    """
    shell = shell or detect_shell()
    script = generate_completion_script(shell)

    # Get the executable path - handle both packaged and non-packaged cases
    executable_path = get_executable_path()

    # Update the completion script to use the correct executable path
    if "sys.argv[0]" in script:
        script = script.replace("sys.argv[0]", f'"{executable_path}"')
    if "{app_name}" in script:
        script = script.replace("{app_name}", "panflow")

    # Determine the appropriate location for the completion script
    if custom_path:
        completion_path = custom_path
    else:
        home = Path.home()
        if shell == "bash":
            # Different locations based on OS
            if platform.system() == "Darwin":  # macOS
                # Try to find Homebrew's bash-completion directory first
                if Path("/usr/local/etc/bash_completion.d").exists() and os.access(
                    "/usr/local/etc/bash_completion.d", os.W_OK
                ):
                    completion_path = Path("/usr/local/etc/bash_completion.d/panflow")
                elif Path("/opt/homebrew/etc/bash_completion.d").exists() and os.access(
                    "/opt/homebrew/etc/bash_completion.d", os.W_OK
                ):
                    completion_path = Path("/opt/homebrew/etc/bash_completion.d/panflow")
                else:
                    # Fall back to user's directory
                    completion_path = home / ".bash_completion.d" / "panflow"
                    os.makedirs(home / ".bash_completion.d", exist_ok=True)

                    # Add line to .bash_profile if not already there
                    for profile in [".bash_profile", ".profile", ".bashrc"]:
                        bash_profile = home / profile
                        if bash_profile.exists():
                            bash_completion_line = f'[ -f "$HOME/.bash_completion.d/panflow" ] && . "$HOME/.bash_completion.d/panflow"'
                            try:
                                with open(bash_profile, "r") as f:
                                    content = f.read()
                                if bash_completion_line not in content:
                                    with open(bash_profile, "a") as f:
                                        f.write(f"\n# PANFlow completion\n{bash_completion_line}\n")
                                    typer.echo(f"Added completion sourcing to {bash_profile}")
                                break
                            except Exception as e:
                                typer.echo(f"Warning: Could not update {profile}: {e}")
            else:  # Linux and others
                if Path("/etc/bash_completion.d").exists() and os.access(
                    "/etc/bash_completion.d", os.W_OK
                ):
                    completion_path = Path("/etc/bash_completion.d/panflow")
                else:
                    # Fall back to user's directory
                    completion_path = (
                        home / ".local" / "share" / "bash-completion" / "completions" / "panflow"
                    )
                    os.makedirs(completion_path.parent, exist_ok=True)
        elif shell == "zsh":
            if platform.system() == "Darwin":  # macOS
                # Try Homebrew's zsh site-functions
                if Path("/usr/local/share/zsh/site-functions").exists() and os.access(
                    "/usr/local/share/zsh/site-functions", os.W_OK
                ):
                    completion_path = Path("/usr/local/share/zsh/site-functions/_panflow")
                elif Path("/opt/homebrew/share/zsh/site-functions").exists() and os.access(
                    "/opt/homebrew/share/zsh/site-functions", os.W_OK
                ):
                    completion_path = Path("/opt/homebrew/share/zsh/site-functions/_panflow")
                else:
                    # Fall back to user's directory
                    completion_path = home / ".zsh" / "completions" / "_panflow"
                    os.makedirs(completion_path.parent, exist_ok=True)

                    # Add line to .zshrc if not already there
                    zshrc = home / ".zshrc"
                    if zshrc.exists():
                        try:
                            zsh_completion_line = f"fpath=($HOME/.zsh/completions $fpath)"
                            zsh_compinit_line = "autoload -Uz compinit && compinit"

                            with open(zshrc, "r") as f:
                                content = f.read()
                            to_append = ""
                            if zsh_completion_line not in content:
                                to_append += f"\n# PANFlow completion\n{zsh_completion_line}\n"
                            if zsh_compinit_line not in content and "compinit" not in content:
                                to_append += f"{zsh_compinit_line}\n"
                            if to_append:
                                with open(zshrc, "a") as f:
                                    f.write(to_append)
                                typer.echo(f"Added completion configuration to {zshrc}")
                        except Exception as e:
                            typer.echo(f"Warning: Could not update .zshrc: {e}")
            else:  # Linux and others
                if Path("/usr/share/zsh/site-functions").exists() and os.access(
                    "/usr/share/zsh/site-functions", os.W_OK
                ):
                    completion_path = Path("/usr/share/zsh/site-functions/_panflow")
                else:
                    # Fall back to user's directory
                    completion_path = home / ".zsh" / "completions" / "_panflow"
                    os.makedirs(completion_path.parent, exist_ok=True)

                    # Add line to .zshrc if not already there
                    zshrc = home / ".zshrc"
                    if zshrc.exists():
                        try:
                            zsh_completion_line = f"fpath=($HOME/.zsh/completions $fpath)"
                            zsh_compinit_line = "autoload -Uz compinit && compinit"

                            with open(zshrc, "r") as f:
                                content = f.read()
                            to_append = ""
                            if zsh_completion_line not in content:
                                to_append += f"\n# PANFlow completion\n{zsh_completion_line}\n"
                            if zsh_compinit_line not in content and "compinit" not in content:
                                to_append += f"{zsh_compinit_line}\n"
                            if to_append:
                                with open(zshrc, "a") as f:
                                    f.write(to_append)
                                typer.echo(f"Added completion configuration to {zshrc}")
                        except Exception as e:
                            typer.echo(f"Warning: Could not update .zshrc: {e}")
        elif shell == "fish":
            # Fish completions go in a standard location
            fish_dir = home / ".config" / "fish" / "completions"
            os.makedirs(fish_dir, exist_ok=True)
            completion_path = fish_dir / "panflow.fish"
        else:
            typer.echo(f"Unsupported shell: {shell}", err=True)
            raise typer.Exit(1)

    # Make sure the parent directory exists
    try:
        os.makedirs(completion_path.parent, exist_ok=True)
    except PermissionError:
        typer.echo(f"Error: Permission denied when creating directory {completion_path.parent}")
        suggestion_path = home / ".local" / "share" / f"panflow_{shell}_completion"
        if shell == "zsh":
            suggestion_path = home / ".zsh" / "completions" / "_panflow"
        elif shell == "fish":
            suggestion_path = home / ".config" / "fish" / "completions" / "panflow.fish"

        typer.echo(f"Try using a custom path in your home directory:")
        typer.echo(f"panflow completion --install --shell {shell} --path {suggestion_path}")
        raise typer.Exit(1)

    # Write the completion script
    try:
        with open(completion_path, "w") as f:
            f.write(script)
        typer.echo(f"Completion script installed to {completion_path}")

        # Additional instructions
        if shell == "bash":
            typer.echo("\nYou may need to restart your shell or source the completion script:")
            typer.echo(f"source {completion_path}")

            # For macOS, suggest adding to profile if not already done
            if platform.system() == "Darwin" and str(completion_path).startswith(str(home)):
                profiles = [".bash_profile", ".profile", ".bashrc"]
                profile_exists = False
                for profile in profiles:
                    if (home / profile).exists():
                        profile_exists = True
                        typer.echo(f"\nTo load completions on startup, add this line to your {profile}:")
                        typer.echo(f"[[ -f {completion_path} ]] && source {completion_path}")
                        break
                if not profile_exists:
                    typer.echo("\nTo load completions on startup, create a .bash_profile file with:")
                    typer.echo(f"[[ -f {completion_path} ]] && source {completion_path}")

        elif shell == "zsh":
            typer.echo("\nYou may need to restart your shell or reload completions:")
            typer.echo("autoload -Uz compinit && compinit")

            # For macOS/Linux, suggest user directory if using system dir
            if not str(completion_path).startswith(str(home)):
                typer.echo("\nIf you prefer to not modify system directories, you can also use:")
                typer.echo(f"panflow completion --install --shell zsh --path ~/.zsh/completions/_panflow")

        elif shell == "fish":
            typer.echo("\nCompletion should be available immediately in fish.")

        return completion_path
    except IOError as e:
        typer.echo(f"Error installing completion script: {e}", err=True)

        # Suggest alternative with sudo if permission denied
        if isinstance(e, PermissionError):
            typer.echo("\nTry one of these alternatives:")
            typer.echo("1. Run with sudo:")
            typer.echo(f"   sudo panflow completion --install --shell {shell}")
            typer.echo("2. Use a custom path in your home directory:")
            if shell == "bash":
                custom_suggestion = f"~/.bash_completion.d/panflow"
            elif shell == "zsh":
                custom_suggestion = f"~/.zsh/completions/_panflow"
            elif shell == "fish":
                custom_suggestion = f"~/.config/fish/completions/panflow.fish"
            typer.echo(f"   panflow completion --install --shell {shell} --path {custom_suggestion}")

        raise typer.Exit(1)


def get_executable_path():
    """
    Get the path to the executable, handling both packaged and non-packaged cases.
    """
    # Check if we're running in a packaged application
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # Get the actual executable path
        executable = sys.executable
        return executable
    else:
        # Check if we can find the panflow command in PATH
        panflow_path = shutil.which("panflow")
        if panflow_path:
            return panflow_path
        else:
            # Fall back to the current script
            return sys.argv[0]
