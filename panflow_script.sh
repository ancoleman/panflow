#!/bin/bash
# Ultra-fast wrapper script for PANFlow
# This script provides a faster startup by bypassing Python's import overhead
# for simple commands like --help and completion handling

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# For packaged app, binary is inside MacOS folder
if [[ -d "$SCRIPT_DIR/dist/PANFlow.app" ]]; then
    BINARY_PATH="$SCRIPT_DIR/dist/PANFlow.app/Contents/MacOS/panflow"
elif [[ -f "$SCRIPT_DIR/dist/panflow" ]]; then
    BINARY_PATH="$SCRIPT_DIR/dist/panflow"
else
    # Fallback to running Python directly
    BINARY_PATH="python $SCRIPT_DIR/cli.py"
fi

# Function to show help (hard-coded to avoid Python startup)
show_help() {
  cat << EOF
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
EOF
}

# Function to show version without Python startup
show_version() {
    echo "PANFlow v0.3.0"
}

# Handle special cases for faster response
if [ "$#" -eq 0 ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
    exit 0
fi

if [ "$1" = "--version" ] || [ "$1" = "-V" ]; then
    show_version
    exit 0
fi

# Handle special completion installation cases directly
if [ "$1" = "completion" ] && [ "$2" = "--install" ]; then
    SHELL_TYPE="$(basename "$SHELL")"
    HOME_DIR="$(cd ~ && pwd)"
    
    # Create shell-specific completion scripts
    if [ "$SHELL_TYPE" = "bash" ]; then
        COMPLETION_DIR="$HOME_DIR/.bash_completion.d"
        mkdir -p "$COMPLETION_DIR"
        COMPLETION_FILE="$COMPLETION_DIR/panflow"
        
        cat > "$COMPLETION_FILE" << EOF
# panflow completion script for bash
_panflow_completion() {
    local IFS=$'\n'
    local response

    response=\$(COMP_WORDS="\${COMP_WORDS[*]}" COMP_CWORD=\$COMP_CWORD $BINARY_PATH __complete "\${COMP_WORDS[@]:1}" 2>/dev/null)

    for completion in \$response; do
        IFS=',' read type value <<< "\$completion"
        if [[ \$type == 'dir' ]]; then
            COMPREPLY=( \$(compgen -d -- "\$value") )
            return
        elif [[ \$type == 'file' ]]; then
            COMPREPLY=( \$(compgen -f -- "\$value") )
            return
        elif [[ \$type == 'plain' ]]; then
            COMPREPLY+=(\$value)
        fi
    done
}

complete -o nosort -F _panflow_completion panflow
EOF
        echo "Completion script installed to $COMPLETION_FILE"
        echo "You may need to restart your shell or source the completion script:"
        echo "source $COMPLETION_FILE"
        
    elif [ "$SHELL_TYPE" = "zsh" ]; then
        COMPLETION_DIR="$HOME_DIR/.zsh/completions"
        mkdir -p "$COMPLETION_DIR"
        COMPLETION_FILE="$COMPLETION_DIR/_panflow"
        
        cat > "$COMPLETION_FILE" << EOF
#compdef panflow

_panflow_completion() {
    local -a completions
    local -a completions_with_descriptions
    local -a response
    
    response=(\$($BINARY_PATH __complete "\${words[@]:1}" 2>/dev/null))
    
    for key value in \$response; do
        completions+=("\$value")
    done
    
    _describe -t options "options" completions
}

compdef _panflow_completion panflow
EOF
        echo "Completion script installed to $COMPLETION_FILE"
        echo "You may need to restart your shell or reload completions:"
        echo "autoload -Uz compinit && compinit"
        
    elif [ "$SHELL_TYPE" = "fish" ]; then
        COMPLETION_DIR="$HOME_DIR/.config/fish/completions"
        mkdir -p "$COMPLETION_DIR"
        COMPLETION_FILE="$COMPLETION_DIR/panflow.fish"
        
        cat > "$COMPLETION_FILE" << EOF
function __fish_panflow_complete
    set -l response
    
    for i in (commandline -opc)
        set -a response \$i
    end
    
    set -l cmd ($BINARY_PATH __complete (string join " " \$response) 2>/dev/null)
    
    for i in \$cmd
        echo \$i
    end
end

complete -f -c panflow -a "(__fish_panflow_complete)"
EOF
        echo "Completion script installed to $COMPLETION_FILE"
        echo "Completion should be available immediately in fish."
    else
        # Fall back to Python for unsupported shells
        exec $BINARY_PATH completion --install
    fi
    
    exit 0
fi

# For basic command help, use hard-coded responses when possible
if [ "$1" = "object" ] && [ "$#" -eq 1 ]; then
    cat << EOF
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
EOF
    exit 0
fi

# For completion requests, forward to the binary
if [[ "$1" == "__complete" ]] || [[ "$*" == *" __complete "* ]]; then
    if [[ $BINARY_PATH == python* ]]; then
        # For local development, run the Python CLI directly
        $BINARY_PATH "$@"
    else
        # For packaged app, execute the binary
        exec "$BINARY_PATH" "$@"
    fi
    exit $?
fi

# For all other commands, pass to the executable
if [[ $BINARY_PATH == python* ]]; then
    # For local development, run the Python CLI directly
    $BINARY_PATH "$@"
else
    # For packaged app, execute the binary
    exec "$BINARY_PATH" "$@"
fi
exit $?