"""
Logging utilities for PANFlow.

This module provides functions for configuring and using the logging system.
"""

import logging
import sys
import os
from typing import Optional, Union, Dict, Any

# Define log levels
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

# Create a global logger
logger = logging.getLogger("panflow")

def configure_logging(
    level: str = "info",
    log_file: Optional[str] = None,
    quiet: bool = False,
    verbose: bool = False,
    json_format: bool = False
) -> None:
    """
    Configure the global logger
    
    Args:
        level: Log level (debug, info, warning, error, critical)
        log_file: Path to log file (optional)
        quiet: Suppress console output if True
        verbose: Enable verbose output if True
        json_format: Use JSON formatting for structured logging
    """
    # Adjust log level based on verbose/quiet flags
    if verbose:
        level = "debug"
    elif quiet and level == "info":  # Only override info level with quiet
        level = "warning"
    
    # Set the log level
    log_level = LOG_LEVELS.get(level.lower(), logging.INFO)
    logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatters
    if json_format:
        import json
        
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    'timestamp': self.formatTime(record),
                    'level': record.levelname,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno
                }
                
                # Add exception info if present
                if record.exc_info:
                    import traceback
                    log_data['exception'] = {
                        'type': record.exc_info[0].__name__,
                        'value': str(record.exc_info[1]),
                        'traceback': traceback.format_tb(record.exc_info[2])
                    }
                
                # Add extra attributes
                if hasattr(record, 'extra_data'):
                    log_data.update(record.extra_data)
                
                return json.dumps(log_data)
        
        console_formatter = JsonFormatter()
        file_formatter = JsonFormatter()
    else:
        console_format = '%(levelname)s: %(message)s'
        file_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        if verbose:
            console_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        console_formatter = logging.Formatter(console_format)
        file_formatter = logging.Formatter(file_format)
    
    # Create console handler unless quiet mode is enabled
    if not quiet:
        # This should be stdout, not stderr for regular messages
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        # IMPORTANT: Set the handler level to match the logger level
        console_handler.setLevel(log_level)
        logger.addHandler(console_handler)
    
    # Create file handler if log file is specified
    if log_file:
        # Create directory if it doesn't exist
        dir_path = os.path.dirname(os.path.abspath(log_file))
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(log_level)  # Set level for file handler too
        logger.addHandler(file_handler)
    
    # Log configuration information at debug level
    logger.debug(f"Logging configured: level={level}, log_file={log_file}, quiet={quiet}, verbose={verbose}, json_format={json_format}")

def log_structured(
    message: str,
    level: str = "info",
    **kwargs
) -> None:
    """
    Log a message with structured additional data.
    
    Args:
        message: Log message
        level: Log level (debug, info, warning, error, critical)
        **kwargs: Additional structured data to include in the log
    """
    log_level = LOG_LEVELS.get(level.lower(), logging.INFO)
    
    # Create a custom record factory to add extra_data
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.extra_data = kwargs
        return record
    
    # Set the custom factory
    logging.setLogRecordFactory(record_factory)
    
    # Log the message
    logger.log(log_level, message, extra={'extra_data': kwargs})
    
    # Restore the original factory
    logging.setLogRecordFactory(old_factory)

def log(
    message: str,
    level: str = "info",
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log a message with optional structured data
    
    Args:
        message: Log message
        level: Log level (debug, info, warning, error, critical)
        data: Optional structured data to include
    """
    log_level = LOG_LEVELS.get(level.lower(), logging.INFO)
    
    # Append structured data if provided
    if data:
        data_str = " ".join(f"{k}={v}" for k, v in data.items())
        message = f"{message} - {data_str}"
    
    logger.log(log_level, message)

# Option callbacks for use with Typer CLI
def verbose_callback(value: bool) -> bool:
    """Typer callback for verbose flag"""
    if value:
        log_level = "debug"
        current_handlers = logger.handlers
        if not current_handlers:
            # Configure logging if not already configured
            configure_logging(level=log_level, quiet=False)
        else:
            # Just update the log level
            logger.setLevel(LOG_LEVELS[log_level])
            for handler in current_handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    handler.setLevel(LOG_LEVELS[log_level])
    return value

def quiet_callback(value: bool) -> bool:
    """Typer callback for quiet flag"""
    if value:
        # Remove all stream handlers
        for handler in logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                logger.removeHandler(handler)
    return value

def log_level_callback(value: str) -> str:
    """Typer callback to validate and set log level"""
    value = value.lower()
    if value not in LOG_LEVELS:
        valid_levels = ", ".join(LOG_LEVELS.keys())
        raise ValueError(f"Log level must be one of: {valid_levels}")
    
    current_handlers = logger.handlers
    if current_handlers:
        # Update the log level
        logger.setLevel(LOG_LEVELS[value])
        for handler in current_handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(LOG_LEVELS[value])
    
    return value

def log_file_callback(value: Optional[str]) -> Optional[str]:
    """Typer callback for log file"""
    if value:
        try:
            # Create directory if it doesn't exist
            dir_path = os.path.dirname(os.path.abspath(value))
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            
            # Add file handler
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            
            # Remove any existing file handlers
            for handler in logger.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    logger.removeHandler(handler)
            
            # Add new file handler
            file_handler = logging.FileHandler(value)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            raise ValueError(f"Cannot write to log file: {str(e)}")
    
    return value