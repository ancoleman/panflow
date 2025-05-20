"""
PyInstaller hooks for PANFlow.
Used to improve performance and optimize startup time.
"""

import os
import sys


def pre_find_module_path(api):
    """
    Pre-hook that can exclude unnecessary modules from being processed by PyInstaller.
    This reduces binary size and improves startup time.
    """
    # Skip heavy test modules in the analysis
    if api.module_name.startswith('test') or api.module_name.startswith('pytest'):
        return None


def pre_safe_import_module(api):
    """
    Pre-hook that runs before a module is imported during analysis.
    Can be used to prepare the environment.
    """
    # Skip certain heavy modules from being analyzed deeply
    if api.module_name in [
        'pandas',
        'matplotlib',
        'scipy',
        'numpy.testing',
    ]:
        api.add_runtime_module(api.module_name)
        return True


def runtime_hook():
    """
    Runtime hook that runs when the packaged application starts.
    Used to optimize the environment for faster startup.
    """
    # Set environment variables for better performance
    os.environ['PYTHONOPTIMIZE'] = '2'
    os.environ['PYTHONNUMPY'] = 'OPENBLAS'
    
    # Disable warnings
    import warnings
    warnings.filterwarnings("ignore")
    
    # Reduce recursion limit for improved startup performance
    sys.setrecursionlimit(1500)
    
    # On macOS, disable App Nap for better performance
    try:
        from Foundation import NSProcessInfo
        NSProcessInfo.processInfo().beginActivityWithOptions_reason_(
            0x00FFFFFF, "PANFlow CLI Tool")
    except ImportError:
        pass

    # Apply optimization for CLI tools
    os.environ['TYPER_STANDARD_CMD_OPTIONS'] = '0'