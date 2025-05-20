
# Runtime hook for PANFlow
# This script is executed when the application starts
import os
import sys

# Apply performance optimizations
os.environ['PYTHONOPTIMIZE'] = '2'  # -O -O: remove asserts and docstrings
os.environ['PYTHONNUMPY'] = 'OPENBLAS'  # Use faster BLAS implementation

# Reduce startup overhead
sys.setrecursionlimit(1500)  # Lower recursion limit for faster startup

# Disable warnings that slow down startup
import warnings
warnings.filterwarnings("ignore")

# On macOS, disable App Nap for better performance
try:
    from Foundation import NSProcessInfo
    NSProcessInfo.processInfo().beginActivityWithOptions_reason_(
        0x00FFFFFF, "PANFlow CLI Tool")
except ImportError:
    pass

# Disable unnecessary features
os.environ['TYPER_STANDARD_CMD_OPTIONS'] = '0'  # Disable standard options
