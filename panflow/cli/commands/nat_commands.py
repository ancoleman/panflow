"""
NAT commands for PANFlow CLI.

This module provides commands for managing PAN-OS NAT rules,
including functionality for splitting bidirectional NAT rules.
"""

import json
import logging
import typer
from typing import Optional, Dict, Any, List

from panflow.core.config_loader import load_config_from_file, save_config, detect_device_type
from panflow.core.nat_splitter import split_bidirectional_nat_rule, split_all_bidirectional_nat_rules

from ..app import policy_app
from ..common import common_options, ConfigOptions

# Get logger
logger = logging.getLogger("panflow")

# Create a NAT command group
nat_app = typer.Typer(help="Commands for working with NAT rules")
policy_app.add_typer(nat_app, name="nat")

@nat_app.command("split-bidirectional")
def split_bidirectional_command(
    config_file: str = typer.Option(
        ..., "--config", "-c",
        help="Path to XML configuration file"
    ),
    rule_name: str = typer.Option(
        ..., "--rule-name", "-r",
        help="Name of the bidirectional NAT rule to split"
    ),
    policy_type: str = typer.Option(
        "nat_rules", "--policy-type", "-t",
        help="Type of NAT policy (nat_rules, nat_pre_rules, nat_post_rules)"
    ),
    reverse_name_suffix: str = typer.Option(
        "-reverse", "--reverse-suffix", "-s",
        help="Suffix to add to the name of the reverse rule"
    ),
    zone_swap: bool = typer.Option(
        True, "--zone-swap/--no-zone-swap",
        help="Whether to swap source and destination zones in the reverse rule"
    ),
    address_swap: bool = typer.Option(
        True, "--address-swap/--no-address-swap",
        help="Whether to swap source and destination addresses in the reverse rule"
    ),
    disable_bidirectional: bool = typer.Option(
        True, "--disable-bidirectional/--keep-bidirectional",
        help="Whether to disable bidirectional flag on the original rule"
    ),
    any_any_return: bool = typer.Option(
        False, "--any-any-return/--no-any-any-return",
        help="If True, use 'any' for source zone and address in the return rule"
    ),
    device_type: str = typer.Option(
        "firewall", "--device-type", "-d",
        help="Device type (firewall or panorama)"
    ),
    context: str = typer.Option(
        "vsys", "--context", "-x",
        help="Context (shared, device_group, vsys)"
    ),
    device_group: Optional[str] = typer.Option(
        None, "--device-group", "--dg",
        help="Device group name (required for device_group context)"
    ),
    vsys: str = typer.Option(
        "vsys1", "--vsys", "-v",
        help="VSYS name (required for vsys context)"
    ),
    version: str = typer.Option(
        "10.2", "--version", 
        help="PAN-OS version"
    ),
    output_file: str = ConfigOptions.output_file(),
    dry_run: bool = ConfigOptions.dry_run()
):
    """
    Split a bidirectional NAT rule into two unidirectional rules.
    
    This command splits a bidirectional NAT rule into two separate rules:
    1. The original rule with bidirectional flag disabled (optional)
    2. A new reverse rule for the return traffic
    
    Examples:
    
        # Split a bidirectional NAT rule with default settings
        python cli.py policy nat split-bidirectional --config config.xml --rule-name "Bidir-NAT-Rule"
        
        # Split a rule but keep the bidirectional flag on the original rule
        python cli.py policy nat split-bidirectional --config config.xml --rule-name "Bidir-NAT-Rule" --keep-bidirectional
        
        # Split a rule and use "any" for source in return rule
        python cli.py policy nat split-bidirectional --config config.xml --rule-name "Bidir-NAT-Rule" --any-any-return
        
        # Perform a dry run to see what would happen without making changes
        python cli.py policy nat split-bidirectional --config config.xml --rule-name "Bidir-NAT-Rule" --dry-run
    """
    try:
        # Load the configuration
        tree, detected_version = load_config_from_file(config_file)
        version_to_use = version or detected_version
        device_type_to_use = device_type or detect_device_type(tree)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        
        # Log the operation
        logger.info(f"Splitting bidirectional NAT rule: {rule_name}")
        logger.info(f"Configuration: device_type={device_type_to_use}, context={context}, version={version_to_use}")
        
        if dry_run:
            logger.info("DRY RUN MODE: No changes will be made")
            logger.info(f"Would split rule '{rule_name}' and create a reverse rule named '{rule_name}{reverse_name_suffix}'")
            logger.info(f"Zone swap: {zone_swap}, Address swap: {address_swap}, Disable bidirectional: {disable_bidirectional}")
            logger.info(f"Any-any return: {any_any_return}")
            return
        
        # Split the rule
        result = split_bidirectional_nat_rule(
            tree=tree,
            rule_name=rule_name,
            policy_type=policy_type,
            reverse_name_suffix=reverse_name_suffix,
            zone_swap=zone_swap,
            address_swap=address_swap,
            disable_orig_bidirectional=disable_bidirectional,
            return_rule_any_any=any_any_return,
            device_type=device_type_to_use,
            context_type=context,
            version=version_to_use,
            **context_kwargs
        )
        
        # Check the result
        if result.get("success", False):
            logger.info(f"Successfully split bidirectional NAT rule '{rule_name}'")
            logger.info(f"Created reverse rule: '{result.get('reverse_rule')}'")
            
            # Save the updated configuration
            if save_config(tree, output_file):
                logger.info(f"Configuration saved to {output_file}")
            else:
                logger.error(f"Failed to save configuration to {output_file}")
                raise typer.Exit(1)
        else:
            logger.error(f"Failed to split rule: {result.get('error', 'Unknown error')}")
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error splitting bidirectional NAT rule: {e}")
        raise typer.Exit(1)

@nat_app.command("split-all-bidirectional")
def split_all_bidirectional_command(
    config_file: str = typer.Option(
        ..., "--config", "-c",
        help="Path to XML configuration file"
    ),
    policy_type: str = typer.Option(
        "nat_rules", "--policy-type", "-t",
        help="Type of NAT policy (nat_rules, nat_pre_rules, nat_post_rules)"
    ),
    reverse_name_suffix: str = typer.Option(
        "-reverse", "--reverse-suffix", "-s",
        help="Suffix to add to the name of the reverse rule"
    ),
    zone_swap: bool = typer.Option(
        True, "--zone-swap/--no-zone-swap",
        help="Whether to swap source and destination zones in the reverse rule"
    ),
    address_swap: bool = typer.Option(
        True, "--address-swap/--no-address-swap",
        help="Whether to swap source and destination addresses in the reverse rule"
    ),
    disable_bidirectional: bool = typer.Option(
        True, "--disable-bidirectional/--keep-bidirectional",
        help="Whether to disable bidirectional flag on the original rule"
    ),
    any_any_return: bool = typer.Option(
        False, "--any-any-return/--no-any-any-return",
        help="If True, use 'any' for source zone and address in the return rule"
    ),
    name_filter: Optional[str] = typer.Option(
        None, "--name-filter", "-f",
        help="Only process rules containing this string in their name"
    ),
    device_type: str = typer.Option(
        "firewall", "--device-type", "-d",
        help="Device type (firewall or panorama)"
    ),
    context: str = typer.Option(
        "vsys", "--context", "-x",
        help="Context (shared, device_group, vsys)"
    ),
    device_group: Optional[str] = typer.Option(
        None, "--device-group", "--dg",
        help="Device group name (required for device_group context)"
    ),
    vsys: str = typer.Option(
        "vsys1", "--vsys", "-v",
        help="VSYS name (required for vsys context)"
    ),
    version: str = typer.Option(
        "10.2", "--version", 
        help="PAN-OS version"
    ),
    output_file: str = ConfigOptions.output_file(),
    report_file: Optional[str] = typer.Option(
        None, "--report", "-r",
        help="Save a detailed report of the operation (JSON format)"
    ),
    dry_run: bool = ConfigOptions.dry_run()
):
    """
    Split all bidirectional NAT rules in the configuration.
    
    This command finds and splits all bidirectional NAT rules into pairs of unidirectional rules.
    You can optionally filter which rules to process by name.
    
    Examples:
    
        # Split all bidirectional NAT rules with default settings
        python cli.py policy nat split-all-bidirectional --config config.xml
        
        # Split only rules containing "BIDIR" in their name
        python cli.py policy nat split-all-bidirectional --config config.xml --name-filter "BIDIR"
        
        # Split all rules but keep the bidirectional flag on original rules
        python cli.py policy nat split-all-bidirectional --config config.xml --keep-bidirectional
        
        # Split all rules and create return rules with "any" source
        python cli.py policy nat split-all-bidirectional --config config.xml --any-any-return
        
        # Generate a detailed report of the operation
        python cli.py policy nat split-all-bidirectional --config config.xml --report split_report.json
        
        # Perform a dry run to see what would happen without making changes
        python cli.py policy nat split-all-bidirectional --config config.xml --dry-run
    """
    try:
        # Load the configuration
        tree, detected_version = load_config_from_file(config_file)
        version_to_use = version or detected_version
        device_type_to_use = device_type or detect_device_type(tree)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        
        # Log the operation
        logger.info(f"Splitting all bidirectional NAT rules of type: {policy_type}")
        if name_filter:
            logger.info(f"Only processing rules containing: {name_filter}")
        logger.info(f"Configuration: device_type={device_type_to_use}, context={context}, version={version_to_use}")
        
        if dry_run:
            logger.info("DRY RUN MODE: No changes will be made")
            
            # Find all matching bidirectional rules (limited to log what would be done without changes)
            from panflow.core.nat_splitter import NATRuleSplitter
            splitter = NATRuleSplitter(
                tree=tree,
                device_type=device_type_to_use,
                context_type=context,
                version=version_to_use,
                **context_kwargs
            )
            
            # Create XPath to find all bidirectional rules for counting
            from panflow.core.xpath_resolver import get_policy_xpath
            base_xpath = get_policy_xpath(
                policy_type,
                device_type_to_use,
                context,
                version_to_use,
                **context_kwargs
            )
            
            # Find all bidirectional rules
            import re
            from panflow.core.config_loader import xpath_search
            if name_filter:
                rule_xpath = f"{base_xpath}/entry[bi-directional='yes' and contains(@name, '{name_filter}')]"
            else:
                rule_xpath = f"{base_xpath}/entry[bi-directional='yes']"
                
            bidirectional_rules = xpath_search(tree, rule_xpath)
            
            if not bidirectional_rules:
                logger.info("No bidirectional NAT rules found that match the criteria")
                return
            
            logger.info(f"Would split {len(bidirectional_rules)} bidirectional NAT rules:")
            for rule in bidirectional_rules:
                rule_name = rule.get("name", "unknown")
                logger.info(f"  - Would split rule '{rule_name}' and create '{rule_name}{reverse_name_suffix}'")
            
            logger.info(f"Zone swap: {zone_swap}, Address swap: {address_swap}, Disable bidirectional: {disable_bidirectional}")
            logger.info(f"Any-any return: {any_any_return}")
            return
        
        # Split all matching rules
        result = split_all_bidirectional_nat_rules(
            tree=tree,
            policy_type=policy_type,
            reverse_name_suffix=reverse_name_suffix,
            zone_swap=zone_swap,
            address_swap=address_swap,
            disable_orig_bidirectional=disable_bidirectional,
            return_rule_any_any=any_any_return,
            name_filter=name_filter,
            device_type=device_type_to_use,
            context_type=context,
            version=version_to_use,
            **context_kwargs
        )
        
        # Process the result
        if result.get("success", False):
            processed = result.get("processed", 0)
            succeeded = result.get("succeeded", 0)
            failed = result.get("failed", 0)
            
            logger.info(f"Processed {processed} bidirectional NAT rules:")
            logger.info(f"  - Successfully split: {succeeded}")
            logger.info(f"  - Failed to split: {failed}")
            
            # Save the updated configuration if any rules were processed
            if succeeded > 0:
                if save_config(tree, output_file):
                    logger.info(f"Configuration saved to {output_file}")
                else:
                    logger.error(f"Failed to save configuration to {output_file}")
                    raise typer.Exit(1)
            
            # Save the report if requested
            if report_file:
                with open(report_file, 'w') as f:
                    json.dump(result, f, indent=2)
                logger.info(f"Operation report saved to {report_file}")
        else:
            logger.error(f"Failed to split rules: {result.get('error', 'Unknown error')}")
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error splitting bidirectional NAT rules: {e}")
        raise typer.Exit(1)