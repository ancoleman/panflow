# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PANFlow
Optimized for performance and fast startup times
"""

block_cipher = None

# Create runtime hook file
with open('runtime_hook.py', 'w') as f:
    f.write("""
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
""")

a = Analysis(
    ['optimized_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('panflow/templates', 'panflow/templates'),
        ('panflow/xpath_mappings', 'panflow/xpath_mappings'),
    ],
    hiddenimports=[
        # Core components (essential)
        'panflow.cli',
        'panflow.cli.app',
        'panflow.cli.common',
        'panflow.cli.completion',
        'panflow.cli.completions',

        # Commands (lazy-loaded, but still need to be included)
        'panflow.cli.commands',
        'panflow.cli.commands.object_commands',
        'panflow.cli.commands.policy_commands',
        'panflow.cli.commands.cleanup_commands',
        'panflow.cli.commands.deduplicate_commands',
        'panflow.cli.commands.merge_commands',
        'panflow.cli.commands.nat_commands',
        'panflow.cli.commands.nlq_commands',
        'panflow.cli.commands.query_commands',

        # Required core modules
        'panflow.nlq',
        'panflow.core',
        'panflow.core.xml',
        'panflow.modules',
        'panflow.reporting',
        'typer.completion',
    ],
    hookspath=['pyinstaller_hooks'],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=[
        # Exclude test modules to reduce size and improve performance
        'pytest',
        'unittest',
        'nose',
        'doctest',
        # Exclude unused components
        'pandas',
        'scipy',
        'matplotlib',
        'numpy.testing',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='panflow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Strip symbols to reduce size and improve load time
    upx=True,  # Use UPX compression for smaller size
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Add optimization options
    optimize=2,  # Highest optimization level
)

# Create a macOS app bundle
app = BUNDLE(
    exe,
    name='PANFlow.app',
    icon=None,  # You can add an icon file here if you have one
    bundle_identifier='com.paloaltonetworks.panflow',
    info_plist={
        'CFBundleShortVersionString': '0.3.0',
        'CFBundleVersion': '0.3.0',
        'NSHighResolutionCapable': 'True',
        'NSHumanReadableCopyright': 'Copyright © 2025 Palo Alto Networks, Inc.',
        'CFBundleDisplayName': 'PANFlow',
        'CFBundleName': 'PANFlow',
        # Add performance optimizations for macOS
        'LSBackgroundOnly': 'False',
        'LSEnvironment': {
            'PYTHONOPTIMIZE': '2',
            'PYTHONDONTWRITEBYTECODE': '1',
        },
        # Command-line tool marking
        'LSUIElement': 'False',
    },
)