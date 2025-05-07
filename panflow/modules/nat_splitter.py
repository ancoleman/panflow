"""
NAT Splitter module for PANFlow.

This module provides functions for working with PAN-OS NAT rules, particularly
for splitting bidirectional NAT rules into separate unidirectional rules.
"""

import os
from typing import Dict, Any, Optional, List, Tuple, Union
from lxml import etree
import logging

from ..core.nat_splitter import NATRuleSplitter

logger = logging.getLogger("panflow")

def split_bidirectional_nat_rule(
    tree: etree._ElementTree,
    rule_name: str,
    policy_type: str = "nat_rules",
    reverse_name_suffix: str = "-reverse",
    zone_swap: bool = True,
    address_swap: bool = True,
    disable_orig_bidirectional: bool = True,
    return_rule_any_any: bool = False,
    device_type: str = "firewall",
    context_type: str = "vsys",
    version: str = "10.2",
    **kwargs
) -> Dict[str, Any]:
    """
    Split a bidirectional NAT rule into two unidirectional rules.
    
    Args:
        tree: ElementTree containing the configuration
        rule_name: Name of the bidirectional NAT rule to split
        policy_type: Type of NAT policy ("nat_rules", "nat_pre_rules", "nat_post_rules")
        reverse_name_suffix: Suffix to add to the name of the reverse rule
        zone_swap: Whether to swap source and destination zones in the reverse rule
        address_swap: Whether to swap source and destination addresses in the reverse rule
        disable_orig_bidirectional: Whether to disable bidirectional flag on the original rule
        return_rule_any_any: If True, use "any" for source zone and address in the return rule
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)
        
    Returns:
        Dict: Information about the operation
    """
    splitter = NATRuleSplitter(
        tree=tree,
        device_type=device_type,
        context_type=context_type,
        version=version,
        **kwargs
    )
    
    result = splitter.split_bidirectional_rule(
        rule_name=rule_name,
        policy_type=policy_type,
        reverse_name_suffix=reverse_name_suffix,
        zone_swap=zone_swap,
        address_swap=address_swap,
        disable_orig_bidirectional=disable_orig_bidirectional,
        return_rule_any_any=return_rule_any_any
    )
    
    return result

def split_all_bidirectional_nat_rules(
    tree: etree._ElementTree,
    policy_type: str = "nat_rules",
    reverse_name_suffix: str = "-reverse",
    zone_swap: bool = True,
    address_swap: bool = True,
    disable_orig_bidirectional: bool = True,
    return_rule_any_any: bool = False,
    name_filter: Optional[str] = None,
    device_type: str = "firewall",
    context_type: str = "vsys",
    version: str = "10.2",
    **kwargs
) -> Dict[str, Any]:
    """
    Split all bidirectional NAT rules in the configuration.
    
    Args:
        tree: ElementTree containing the configuration
        policy_type: Type of NAT policy ("nat_rules", "nat_pre_rules", "nat_post_rules")
        reverse_name_suffix: Suffix to add to the name of the reverse rule
        zone_swap: Whether to swap source and destination zones in the reverse rule
        address_swap: Whether to swap source and destination addresses in the reverse rule
        disable_orig_bidirectional: Whether to disable bidirectional flag on the original rule
        return_rule_any_any: If True, use "any" for source zone and address in the return rule
        name_filter: Optional string to filter rule names (only process rules containing this string)
        device_type: Type of device ("firewall" or "panorama")
        context_type: Type of context (shared, device_group, vsys)
        version: PAN-OS version
        **kwargs: Additional parameters (device_group, vsys)
        
    Returns:
        Dict: Summary of split operations
    """
    splitter = NATRuleSplitter(
        tree=tree,
        device_type=device_type,
        context_type=context_type,
        version=version,
        **kwargs
    )
    
    result = splitter.split_all_bidirectional_rules(
        policy_type=policy_type,
        reverse_name_suffix=reverse_name_suffix,
        zone_swap=zone_swap,
        address_swap=address_swap,
        disable_orig_bidirectional=disable_orig_bidirectional,
        return_rule_any_any=return_rule_any_any,
        name_filter=name_filter
    )
    
    return result