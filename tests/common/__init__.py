"""
Common test utilities for PANFlow test suite.

This module provides shared fixtures, mock factories, and test base classes
to reduce duplication across test files and improve test maintainability.
"""

from .fixtures import *
from .factories import *
from .base import *
from .benchmarks import *

__all__ = [
    # Fixtures
    "firewall_config",
    "panorama_config",
    "panorama_with_objects",
    "panorama_with_policies",
    "sample_address_objects",
    "sample_service_objects",
    
    # Factories
    "ConfigFactory",
    "MockFactory",
    "ObjectFactory",
    "PolicyFactory",
    
    # Base classes
    "BaseTestCase",
    "CLITestCase",
    "XMLTestCase",
    
    # Benchmarks
    "benchmark",
    "track_performance",
]