"""
Feature flag framework for PANFlow.

This module provides a simple feature flag system to enable gradual rollout
of refactored code and easy rollback if issues are discovered.
"""

import os
import json
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from functools import wraps

from .logging_utils import logger


class FeatureFlags:
    """Manage feature flags for PANFlow."""
    
    # Default feature flags
    _defaults = {
        # v0.4.x features
        "use_enhanced_command_base": False,
        "use_enhanced_object_commands": False,  # v0.4.2 - All object commands refactored
        "use_enhanced_policy_commands": False,  # v0.4.3 - All policy commands refactored
        "use_test_utilities": True,
        "enable_performance_tracking": False,
        
        # v0.5.x features
        "use_new_cli_pattern": False,
        "use_bulk_operation_framework": False,
        "use_context_manager": False,
        
        # v0.6.x features
        "use_optimized_xml": False,
        "use_enhanced_graph": False,
        
        # General flags
        "enable_debug_mode": False,
        "use_legacy_mode": False,
    }
    
    _instance = None
    _flags: Dict[str, bool] = {}
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize feature flags."""
        if self._initialized:
            return
        
        self._initialized = True
        self._flags = self._defaults.copy()
        
        # Load from environment variables
        self._load_from_env()
        
        # Load from config file if exists
        self._load_from_file()
    
    def _load_from_env(self):
        """Load feature flags from environment variables."""
        for flag_name in self._flags:
            env_name = f"PANFLOW_FF_{flag_name.upper()}"
            if env_name in os.environ:
                value = os.environ[env_name].lower()
                self._flags[flag_name] = value in ("true", "1", "yes", "on")
                logger.debug(f"Feature flag '{flag_name}' set to {self._flags[flag_name]} from env")
    
    def _load_from_file(self, config_file: Optional[str] = None):
        """Load feature flags from a configuration file."""
        if config_file is None:
            # Check standard locations
            possible_files = [
                Path.home() / ".panflow" / "feature_flags.json",
                Path.cwd() / ".panflow_features.json",
                Path("/etc/panflow/feature_flags.json"),
            ]
            
            for file_path in possible_files:
                if file_path.exists():
                    config_file = str(file_path)
                    break
        
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r') as f:
                    file_flags = json.load(f)
                    self._flags.update(file_flags)
                    logger.debug(f"Loaded feature flags from {config_file}")
            except Exception as e:
                logger.warning(f"Failed to load feature flags from {config_file}: {e}")
    
    def is_enabled(self, flag_name: str) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            flag_name: Name of the feature flag
            
        Returns:
            True if enabled, False otherwise
        """
        return self._flags.get(flag_name, False)
    
    def enable(self, flag_name: str):
        """Enable a feature flag."""
        self._flags[flag_name] = True
        logger.info(f"Feature flag '{flag_name}' enabled")
    
    def disable(self, flag_name: str):
        """Disable a feature flag."""
        self._flags[flag_name] = False
        logger.info(f"Feature flag '{flag_name}' disabled")
    
    def set(self, flag_name: str, value: bool):
        """Set a feature flag value."""
        self._flags[flag_name] = value
        logger.info(f"Feature flag '{flag_name}' set to {value}")
    
    def get_all(self) -> Dict[str, bool]:
        """Get all feature flags and their values."""
        return self._flags.copy()
    
    def reset(self):
        """Reset all flags to defaults."""
        self._flags = self._defaults.copy()
        logger.info("Feature flags reset to defaults")
    
    def save_to_file(self, config_file: str):
        """Save current feature flags to a file."""
        try:
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(self._flags, f, indent=2)
            logger.info(f"Feature flags saved to {config_file}")
        except Exception as e:
            logger.error(f"Failed to save feature flags to {config_file}: {e}")


# Global instance
_feature_flags = FeatureFlags()


def is_enabled(flag_name: str) -> bool:
    """
    Check if a feature flag is enabled.
    
    Args:
        flag_name: Name of the feature flag
        
    Returns:
        True if enabled, False otherwise
    """
    return _feature_flags.is_enabled(flag_name)


def enable(flag_name: str):
    """Enable a feature flag."""
    _feature_flags.enable(flag_name)


def disable(flag_name: str):
    """Disable a feature flag."""
    _feature_flags.disable(flag_name)


def feature_flag(flag_name: str, fallback: Optional[Callable] = None):
    """
    Decorator to conditionally execute functions based on feature flags.
    
    Args:
        flag_name: Name of the feature flag
        fallback: Optional fallback function if flag is disabled
    
    Example:
        @feature_flag("use_new_algorithm")
        def process_data(data):
            # New implementation
            return new_algorithm(data)
            
        # Or with fallback:
        @feature_flag("use_new_algorithm", fallback=old_process_data)
        def process_data(data):
            # New implementation
            return new_algorithm(data)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if is_enabled(flag_name):
                return func(*args, **kwargs)
            elif fallback:
                return fallback(*args, **kwargs)
            else:
                raise RuntimeError(
                    f"Feature '{flag_name}' is disabled and no fallback provided"
                )
        
        wrapper._feature_flag = flag_name
        return wrapper
    
    return decorator


def dual_path(flag_name: str):
    """
    Decorator for dual-path execution based on feature flags.
    
    This decorator expects the function to return a tuple of (new_impl, old_impl).
    
    Example:
        @dual_path("use_new_parser")
        def parse_config(config_file):
            def new_impl():
                return NewParser().parse(config_file)
            
            def old_impl():
                return OldParser().parse(config_file)
            
            return new_impl, old_impl
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            new_impl, old_impl = func(*args, **kwargs)
            
            if is_enabled(flag_name):
                try:
                    return new_impl()
                except Exception as e:
                    logger.error(
                        f"New implementation failed for '{flag_name}', "
                        f"falling back to old: {e}"
                    )
                    return old_impl()
            else:
                return old_impl()
        
        return wrapper
    
    return decorator


class FeatureFlagContext:
    """Context manager for temporarily changing feature flags."""
    
    def __init__(self, **flags):
        """
        Initialize context with temporary flag values.
        
        Args:
            **flags: Feature flags to set temporarily
        """
        self.temp_flags = flags
        self.original_flags = {}
    
    def __enter__(self):
        """Enter context and set temporary flags."""
        for flag_name, value in self.temp_flags.items():
            self.original_flags[flag_name] = _feature_flags._flags.get(flag_name)
            _feature_flags.set(flag_name, value)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original flags."""
        for flag_name, original_value in self.original_flags.items():
            if original_value is None:
                _feature_flags._flags.pop(flag_name, None)
            else:
                _feature_flags.set(flag_name, original_value)


# Utility functions for migration support
def use_legacy_mode():
    """Enable legacy mode for maximum compatibility."""
    enable("use_legacy_mode")
    disable("use_enhanced_command_base")
    disable("use_new_cli_pattern")
    disable("use_bulk_operation_framework")
    disable("use_context_manager")
    disable("use_optimized_xml")
    disable("use_enhanced_graph")
    logger.info("Legacy mode enabled - all new features disabled")


def use_latest_features():
    """Enable all latest features."""
    disable("use_legacy_mode")
    enable("use_enhanced_command_base")
    enable("use_test_utilities")
    enable("enable_performance_tracking")
    logger.info("Latest features enabled")


def get_feature_report() -> str:
    """Generate a report of all feature flags and their status."""
    flags = _feature_flags.get_all()
    
    report_lines = [
        "PANFlow Feature Flags Report",
        "=" * 40,
        ""
    ]
    
    # Group by version
    groups = {
        "v0.4.x": ["use_enhanced_command_base", "use_test_utilities", "enable_performance_tracking"],
        "v0.5.x": ["use_new_cli_pattern", "use_bulk_operation_framework", "use_context_manager"],
        "v0.6.x": ["use_optimized_xml", "use_enhanced_graph"],
        "General": ["enable_debug_mode", "use_legacy_mode"],
    }
    
    for group_name, group_flags in groups.items():
        report_lines.append(f"{group_name} Features:")
        for flag in group_flags:
            if flag in flags:
                status = "✅ Enabled" if flags[flag] else "❌ Disabled"
                report_lines.append(f"  {flag}: {status}")
        report_lines.append("")
    
    # Unknown flags
    known_flags = set()
    for group_flags in groups.values():
        known_flags.update(group_flags)
    
    unknown_flags = set(flags.keys()) - known_flags
    if unknown_flags:
        report_lines.append("Unknown Flags:")
        for flag in unknown_flags:
            status = "✅ Enabled" if flags[flag] else "❌ Disabled"
            report_lines.append(f"  {flag}: {status}")
    
    return "\n".join(report_lines)