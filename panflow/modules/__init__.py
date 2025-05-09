"""
Modules package for PANFlow for PAN-OS XML utilities.

This package contains the functional modules for different aspects of
PAN-OS configuration management, including objects, policies, groups, and reports.
"""

# Import key functions from each module for convenient access
from .objects import (
    get_objects, get_object, add_object, update_object, 
    delete_object, filter_objects
)

from .policies import (
    get_policies, get_policy, add_policy, update_policy,
    delete_policy, filter_policies, get_policy_position,
    move_policy, clone_policy
)

from .groups import (
    add_member_to_group, remove_member_from_group, add_members_to_group,
    create_group, get_group_members, get_group_filter
)

from ..reporting import (
    generate_unused_objects_report, generate_duplicate_objects_report,
    generate_security_rule_coverage_report, generate_reference_check_report,
    generate_rule_hit_count_report
)

# Define the public API
__all__ = [
    # Objects module
    'get_objects', 'get_object', 'add_object', 'update_object', 
    'delete_object', 'filter_objects',
    
    # Policies module
    'get_policies', 'get_policy', 'add_policy', 'update_policy',
    'delete_policy', 'filter_policies', 'get_policy_position',
    'move_policy', 'clone_policy',
    
    # Groups module
    'add_member_to_group', 'remove_member_from_group', 'add_members_to_group',
    'create_group', 'get_group_members', 'get_group_filter',
    
    # Reports module
    'generate_unused_objects_report', 'generate_duplicate_objects_report',
    'generate_security_rule_coverage_report', 'generate_reference_check_report',
    'generate_rule_hit_count_report'
]