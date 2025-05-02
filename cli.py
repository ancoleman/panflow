#!/usr/bin/env python3
"""
PANFlow for PAN-OS XML CLI

A comprehensive command-line interface for working with PAN-OS XML configurations
using the dynamic PAN-OS XML utilities.
"""

import os
import sys
import json
from typing import List, Dict, Optional, Any, Tuple, Union
import typer
import logging

# Import the new refactored modules
from panflow import (
    PanOsXmlConfig, configure_logging, get_all_versions
)
from panflow.core.logging_utils import (
    verbose_callback, quiet_callback, log_level_callback, log_file_callback
)

from panflow.core.deduplication import DeduplicationEngine
from panflow.core.policy_merger import PolicyMerger
from panflow.core.object_merger import ObjectMerger
from panflow.core.config_loader import load_config_from_file, save_config, detect_device_type

# Create main Typer app
app = typer.Typer(help="PANFlow CLI")
object_app = typer.Typer(help="Object management commands")
policy_app = typer.Typer(help="Policy management commands")
group_app = typer.Typer(help="Group management commands")
report_app = typer.Typer(help="Report generation commands")
config_app = typer.Typer(help="Configuration management commands")
merge_app = typer.Typer(help="Policy and Object merge commands")


# Add sub-apps to main app
app.add_typer(object_app, name="object")
app.add_typer(policy_app, name="policy")
app.add_typer(group_app, name="group")
app.add_typer(report_app, name="report")
app.add_typer(config_app, name="config")
app.add_typer(merge_app, name="merge")

# Get logger
logger = logging.getLogger("panflow")

# Main CLI command callback
@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output", callback=verbose_callback),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress console output", callback=quiet_callback),
    log_level: str = typer.Option("info", "--log-level", "-l", help="Set log level (debug, info, warning, error, critical)", callback=log_level_callback),
    log_file: Optional[str] = typer.Option(None, "--log-file", "-f", help="Log to file", callback=log_file_callback),
):
    """
    PANFlow Utilities CLI

    A comprehensive command-line interface for working with PAN-OS XML configurations
    using the PANFlow utilities.
    """
    # Ensure logging is configured properly with the right level for console output
    from panflow.core.logging_utils import configure_logging
    # Log level will already be set by callbacks, but we need to ensure a console handler exists
    configure_logging(level=log_level, log_file=log_file, quiet=quiet, verbose=verbose)
    logger.info("PANFLow CLI initialized")

# ===== Object Commands =====

@object_app.command("list")
def list_objects(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to list (address, service, etc.)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results (JSON format)"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys, template)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name (for Panorama device_group context)"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name (for firewall vsys context)"),
    template: Optional[str] = typer.Option(None, "--template", help="Template name (for Panorama template context)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """List objects of specified type"""
    try:
        # Initialize the configuration
        xml_config = PanOsXmlConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        elif context == "template" and template:
            context_kwargs["template"] = template
        
        logger.info(f"Listing {object_type} objects in {context} context...")
        
        # Get objects (the get_objects function will log details about what it finds)
        objects = xml_config.get_objects(object_type, context, **context_kwargs)
        
        # Save to file if requested
        if output:
            with open(output, 'w') as f:
                json.dump(objects, f, indent=2)
            logger.info(f"Objects saved to {output}")
            
    except Exception as e:
        logger.error(f"Error listing objects: {e}")
        raise typer.Exit(1)

@object_app.command("add")
def add_object(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to add (address, service, etc.)"),
    name: str = typer.Option(..., "--name", "-n", help="Name of the object"),
    properties_file: str = typer.Option(..., "--properties", "-p", help="JSON file with object properties"),
    output: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys, template)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name (for Panorama device_group context)"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name (for firewall vsys context)"),
    template: Optional[str] = typer.Option(None, "--template", help="Template name (for Panorama template context)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """Add a new object"""
    try:
        # Initialize the configuration
        xml_config = PanOsXmlConfig(config_file=config, device_type=device_type, version=version)
        
        # Read properties from file
        with open(properties_file, 'r') as f:
            properties = json.load(f)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        elif context == "template" and template:
            context_kwargs["template"] = template
        
        # Add the object
        if xml_config.add_object(object_type, name, properties, context, **context_kwargs):
            logger.info(f"Successfully added {object_type} object '{name}'")
            
            # Save the updated configuration
            if xml_config.save(output):
                logger.info(f"Configuration saved to {output}")
            else:
                logger.error(f"Failed to save configuration to {output}")
                raise typer.Exit(1)
        else:
            logger.error(f"Failed to add {object_type} object '{name}'")
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error adding object: {e}")
        raise typer.Exit(1)

@object_app.command("update")
def update_object(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to update (address, service, etc.)"),
    name: str = typer.Option(..., "--name", "-n", help="Name of the object"),
    properties_file: str = typer.Option(..., "--properties", "-p", help="JSON file with updated object properties"),
    output: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys, template)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name (for Panorama device_group context)"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name (for firewall vsys context)"),
    template: Optional[str] = typer.Option(None, "--template", help="Template name (for Panorama template context)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """Update an existing object"""
    try:
        # Initialize the configuration
        xml_config = PanOsXmlConfig(config_file=config, device_type=device_type, version=version)
        
        # Read properties from file
        with open(properties_file, 'r') as f:
            properties = json.load(f)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        elif context == "template" and template:
            context_kwargs["template"] = template
        
        # Update the object
        if xml_config.update_object(object_type, name, properties, context, **context_kwargs):
            logger.info(f"Successfully updated {object_type} object '{name}'")
            
            # Save the updated configuration
            if xml_config.save(output):
                logger.info(f"Configuration saved to {output}")
            else:
                logger.error(f"Failed to save configuration to {output}")
                raise typer.Exit(1)
        else:
            logger.error(f"Failed to update {object_type} object '{name}'")
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error updating object: {e}")
        raise typer.Exit(1)

@object_app.command("delete")
def delete_object(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to delete (address, service, etc.)"),
    name: str = typer.Option(..., "--name", "-n", help="Name of the object"),
    output: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys, template)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name (for Panorama device_group context)"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name (for firewall vsys context)"),
    template: Optional[str] = typer.Option(None, "--template", help="Template name (for Panorama template context)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """Delete an object"""
    try:
        # Initialize the configuration
        xml_config = PanOsXmlConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        elif context == "template" and template:
            context_kwargs["template"] = template
        
        # Delete the object
        if xml_config.delete_object(object_type, name, context, **context_kwargs):
            logger.info(f"Successfully deleted {object_type} object '{name}'")
            
            # Save the updated configuration
            if xml_config.save(output):
                logger.info(f"Configuration saved to {output}")
            else:
                logger.error(f"Failed to save configuration to {output}")
                raise typer.Exit(1)
        else:
            logger.error(f"Failed to delete {object_type} object '{name}'")
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error deleting object: {e}")
        raise typer.Exit(1)

@object_app.command("filter")
def filter_objects(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to filter (address, service, etc.)"),
    criteria_file: str = typer.Option(..., "--criteria", help="JSON file with filter criteria"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results (JSON format)"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys, template)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name (for Panorama device_group context)"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name (for firewall vsys context)"),
    template: Optional[str] = typer.Option(None, "--template", help="Template name (for Panorama template context)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """Filter objects based on criteria"""
    try:
        # Initialize the configuration
        xml_config = PanOsXmlConfig(config_file=config, device_type=device_type, version=version)
        
        # Read criteria from file
        with open(criteria_file, 'r') as f:
            criteria = json.load(f)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        elif context == "template" and template:
            context_kwargs["template"] = template
        
        # Filter objects
        filtered_objects = xml_config.filter_objects(object_type, criteria, context, **context_kwargs)
        logger.info(f"Found {len(filtered_objects)} {object_type} objects matching criteria")
        
        # Display filtered objects
        for name in filtered_objects:
            logger.info(f"  - {name}")
        
        # Save to file if requested
        if output:
            with open(output, 'w') as f:
                json.dump(filtered_objects, f, indent=2)
            logger.info(f"Filtered objects saved to {output}")
            
    except Exception as e:
        logger.error(f"Error filtering objects: {e}")
        raise typer.Exit(1)

# ===== Policy Commands =====

@policy_app.command("list")
def list_policies(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    policy_type: str = typer.Option(..., "--type", "-t", help="Type of policy to list (security_pre_rules, nat_rules, etc.)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results (JSON format)"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name (for Panorama device_group context)"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name (for firewall vsys context)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """List policies of specified type"""
    try:
        # Initialize the configuration
        xml_config = PanOsXmlConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        
        # Get policies
        policies = xml_config.get_policies(policy_type, context, **context_kwargs)
        logger.info(f"Found {len(policies)} {policy_type} policies")
        
        # Display policies
        for name in policies:
            logger.info(f"  - {name}")
        
        # Save to file if requested
        if output:
            with open(output, 'w') as f:
                json.dump(policies, f, indent=2)
            logger.info(f"Policies saved to {output}")
            
    except Exception as e:
        logger.error(f"Error listing policies: {e}")
        raise typer.Exit(1)

# Implement remaining policy commands similar to object commands

# ===== Group Commands =====

@group_app.command("add-member")
def add_group_member(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    group_type: str = typer.Option(..., "--type", "-t", help="Type of group (address_group, service_group, etc.)"),
    group_name: str = typer.Option(..., "--group", "-g", help="Name of the group"),
    member_name: str = typer.Option(..., "--member", "-m", help="Name of the member to add"),
    output: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys, template)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name (for Panorama device_group context)"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name (for firewall vsys context)"),
    template: Optional[str] = typer.Option(None, "--template", help="Template name (for Panorama template context)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """Add a member to a group"""
    try:
        # Initialize the configuration
        xml_config = PanOsXmlConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        elif context == "template" and template:
            context_kwargs["template"] = template
        
        # Add member to group
        if xml_config.add_member_to_group(group_type, group_name, member_name, context, **context_kwargs):
            logger.info(f"Successfully added member '{member_name}' to {group_type} '{group_name}'")
            
            # Save the updated configuration
            if xml_config.save(output):
                logger.info(f"Configuration saved to {output}")
            else:
                logger.error(f"Failed to save configuration to {output}")
                raise typer.Exit(1)
        else:
            logger.error(f"Failed to add member '{member_name}' to {group_type} '{group_name}'")
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error adding member to group: {e}")
        raise typer.Exit(1)

# Implement remaining group commands

# ===== Report Commands =====

@report_app.command("unused-objects")
def report_unused_objects(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    output: str = typer.Option(..., "--output", "-o", help="Output file for report (JSON format)"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys, template)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name (for Panorama device_group context)"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name (for firewall vsys context)"),
    template: Optional[str] = typer.Option(None, "--template", help="Template name (for Panorama template context)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """Generate report of unused objects"""
    try:
        # Initialize the configuration
        xml_config = PanOsXmlConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        elif context == "template" and template:
            context_kwargs["template"] = template
        
        # Generate report
        report = xml_config.generate_unused_objects_report(context, output, **context_kwargs)
        
        # Print summary
        if "unused_objects" in report:
            unused_objects = report["unused_objects"]
            logger.info(f"Found {len(unused_objects)} unused address objects")
            
            # Display unused objects
            for obj in unused_objects:
                logger.info(f"  - {obj['name']}")
            
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise typer.Exit(1)

# Implement remaining report commands

# ===== Configuration Commands =====

@config_app.command("validate")
def validate_config(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version (auto-detected if not specified)"),
):
    """Validate XML configuration structure"""
    try:
        # Initialize the configuration
        xml_config = PanOsXmlConfig(config_file=config, device_type=device_type, version=version)
        
        # Basic validation is performed during loading
        logger.info(f"Configuration file loaded and validated successfully")
        logger.info(f"Detected PAN-OS version: {xml_config.version}")
        logger.info(f"Detected device type: {xml_config.device_type}")
        
        # Additional validation could be implemented here
        
    except Exception as e:
        logger.error(f"Error validating configuration: {e}")
        raise typer.Exit(1)

# Implement remaining config commands (merge, compare, etc.)

@policy_app.command("bulk-update")
def bulk_update_policies(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    policy_type: str = typer.Option(..., "--type", "-t", help="Type of policy to update"),
    criteria_file: str = typer.Option(..., "--criteria", help="JSON file with filter criteria"),
    operations_file: str = typer.Option(..., "--operations", help="JSON file with update operations"),
    output: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type (firewall or panorama)"),
    context: str = typer.Option("shared", "--context", help="Context (shared, device_group, vsys)"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version"),
):
    """Bulk update policies matching criteria with specified operations"""
    try:
        # Initialize the configuration
        xml_config = PanOsXmlConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        
        # Read criteria and operations from files
        with open(criteria_file, 'r') as f:
            criteria = json.load(f)
        
        with open(operations_file, 'r') as f:
            operations = json.load(f)
        
        # Create updater and perform bulk update
        updater = ConfigUpdater(xml_config.tree, device_type, context, xml_config.version, **context_kwargs)
        updated_count = updater.bulk_update_policies(policy_type, criteria, operations)
        
        logger.info(f"Updated {updated_count} policies")
        
        # Save the updated configuration
        if xml_config.save(output):
            logger.info(f"Configuration saved to {output}")
        else:
            logger.error(f"Failed to save configuration to {output}")
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        raise typer.Exit(1)

@app.command("deduplicate")
def deduplicate_objects(
    config: str = typer.Option(..., "--config", "-c", help="Path to XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to deduplicate"),
    output: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration"),
    device_type: str = typer.Option("firewall", "--device-type", "-d", help="Device type"),
    context: str = typer.Option("shared", "--context", help="Context"),
    device_group: Optional[str] = typer.Option(None, "--device-group", help="Device group name"),
    vsys: str = typer.Option("vsys1", "--vsys", help="VSYS name"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes"),
    strategy: str = typer.Option("first", "--strategy", help="Strategy for choosing primary object"),
    version: Optional[str] = typer.Option(None, "--version", help="PAN-OS version"),
):
    """Find and merge duplicate objects"""
    try:
        # Initialize the configuration
        xml_config = PanOsXmlConfig(config_file=config, device_type=device_type, version=version)
        
        # Prepare context parameters
        context_kwargs = {}
        if context == "device_group" and device_group:
            context_kwargs["device_group"] = device_group
        elif context == "vsys":
            context_kwargs["vsys"] = vsys
        
        # Create deduplication engine
        engine = DeduplicationEngine(xml_config.tree, device_type, context, xml_config.version, **context_kwargs)
        
        # Find duplicates and references
        duplicates, references = engine.find_duplicate_addresses()
        
        if not duplicates:
            logger.info("No duplicate objects found")
            return
        
        # Log the duplicates found
        for value_key, objects in duplicates.items():
            names = [name for name, _ in objects]
            logger.info(f"Found duplicates with value {value_key}: {', '.join(names)}")
        
        if dry_run:
            logger.info("Dry run - no changes made")
            return
        
        # Merge duplicates
        changes = engine.merge_duplicates(duplicates, references, strategy)
        
        # Apply the changes
        for change_type, name, obj in changes:
            if change_type == 'delete':
                # Delete the object
                parent = obj.getparent()
                if parent is not None:
                    parent.remove(obj)
                    logger.info(f"Deleted duplicate object: {name}")
        
        # Save the updated configuration
        if xml_config.save(output):
            logger.info(f"Configuration saved to {output}")
        else:
            logger.error(f"Failed to save configuration to {output}")
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error in deduplication: {e}")
        raise typer.Exit(1)

@merge_app.command("policy")
def merge_policy(
    source_config: str = typer.Option(..., "--source-config", help="Path to source XML configuration file"),
    target_config: str = typer.Option(..., "--target-config", help="Path to target XML configuration file"),
    policy_type: str = typer.Option(..., "--type", "-t", help="Type of policy to merge (security_pre_rules, nat_rules, etc.)"),
    policy_name: str = typer.Option(..., "--name", "-n", help="Name of the policy to merge"),
    source_context: str = typer.Option("shared", "--source-context", help="Source context (shared, device_group, vsys)"),
    target_context: str = typer.Option("shared", "--target-context", help="Target context (shared, device_group, vsys)"),
    source_device_group: Optional[str] = typer.Option(None, "--source-dg", help="Source device group name"),
    target_device_group: Optional[str] = typer.Option(None, "--target-dg", help="Target device group name"),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option("panorama", "--source-type", help="Source device type (firewall or panorama)"),
    target_device_type: str = typer.Option("panorama", "--target-type", help="Target device type (firewall or panorama)"),
    source_version: Optional[str] = typer.Option(None, "--source-version", help="Source PAN-OS version"),
    target_version: Optional[str] = typer.Option(None, "--target-version", help="Target PAN-OS version"),
    position: str = typer.Option("bottom", "--position", help="Position to add policy (top, bottom, before, after)"),
    ref_policy: Optional[str] = typer.Option(None, "--ref-policy", help="Reference policy for before/after position"),
    skip_if_exists: bool = typer.Option(True, "--skip-if-exists/--replace", help="Skip if policy already exists"),
    copy_references: bool = typer.Option(True, "--copy-references/--no-copy-references", help="Copy object references"),
    output_file: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration")
):
    """Merge a policy from source configuration to target configuration"""
    try:
        # Load source and target configurations
        from panflow.core.config_loader import load_config_from_file, save_config
        
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)
        
        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)
        
        # Create policy merger
        merger = PolicyMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version
        )
        
        # Merge the policy
        result = merger.copy_policy(
            policy_type,
            policy_name,
            source_context,
            target_context,
            skip_if_exists,
            copy_references,
            position,
            ref_policy,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys
        )
        
        if result:
            logger.info(f"Successfully merged policy '{policy_name}'")
            
            # Log copied objects
            if copy_references and merger.copied_objects:
                logger.info(f"Copied {len(merger.copied_objects)} referenced objects")
                for obj_type, obj_name in merger.copied_objects:
                    logger.debug(f"  - {obj_type}: {obj_name}")
            
            # Save the updated configuration
            if save_config(target_tree, output_file):
                logger.info(f"Configuration saved to {output_file}")
            else:
                logger.error(f"Failed to save configuration to {output_file}")
                raise typer.Exit(1)
        else:
            logger.error(f"Failed to merge policy '{policy_name}'")
            
            if merger.skipped_policies:
                for name, reason in merger.skipped_policies:
                    logger.warning(f"  - {name}: {reason}")
                    
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error merging policy: {e}")
        raise typer.Exit(1)

@merge_app.command("policies")
def merge_policies(
    source_config: str = typer.Option(..., "--source-config", help="Path to source XML configuration file"),
    target_config: str = typer.Option(..., "--target-config", help="Path to target XML configuration file"),
    policy_type: str = typer.Option(..., "--type", "-t", help="Type of policy to merge (security_pre_rules, nat_rules, etc.)"),
    policy_names_file: Optional[str] = typer.Option(None, "--names-file", help="File containing policy names to merge (one per line)"),
    criteria_file: Optional[str] = typer.Option(None, "--criteria", help="JSON file with filter criteria"),
    source_context: str = typer.Option("shared", "--source-context", help="Source context (shared, device_group, vsys)"),
    target_context: str = typer.Option("shared", "--target-context", help="Target context (shared, device_group, vsys)"),
    source_device_group: Optional[str] = typer.Option(None, "--source-dg", help="Source device group name"),
    target_device_group: Optional[str] = typer.Option(None, "--target-dg", help="Target device group name"),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option("panorama", "--source-type", help="Source device type (firewall or panorama)"),
    target_device_type: str = typer.Option("panorama", "--target-type", help="Target device type (firewall or panorama)"),
    source_version: Optional[str] = typer.Option(None, "--source-version", help="Source PAN-OS version"),
    target_version: Optional[str] = typer.Option(None, "--target-version", help="Target PAN-OS version"),
    skip_if_exists: bool = typer.Option(True, "--skip-if-exists/--replace", help="Skip if policy already exists"),
    copy_references: bool = typer.Option(True, "--copy-references/--no-copy-references", help="Copy object references"),
    output_file: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration")
):
    """Merge multiple policies from source configuration to target configuration"""
    try:
        # Load source and target configurations
        from panflow.core.config_loader import load_config_from_file, save_config
        
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)
        
        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)
        
        # Create policy merger
        merger = PolicyMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version
        )
        
        # Get policy names or criteria
        policy_names = None
        filter_criteria = None
        
        if policy_names_file:
            with open(policy_names_file, 'r') as f:
                policy_names = [line.strip() for line in f if line.strip()]
        
        if criteria_file:
            with open(criteria_file, 'r') as f:
                import json
                filter_criteria = json.load(f)
        
        if not policy_names and not filter_criteria:
            logger.error("Either policy names file or criteria file must be provided")
            raise typer.Exit(1)
        
        # Merge the policies
        copied, total = merger.copy_policies(
            policy_type,
            source_context,
            target_context,
            policy_names,
            filter_criteria,
            skip_if_exists,
            copy_references,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys
        )
        
        if copied > 0:
            logger.info(f"Successfully merged {copied} of {total} policies")
            
            # Log copied objects
            if copy_references and merger.copied_objects:
                logger.info(f"Copied {len(merger.copied_objects)} referenced objects")
                for obj_type, obj_name in merger.copied_objects[:10]:  # Show first 10
                    logger.debug(f"  - {obj_type}: {obj_name}")
                
                if len(merger.copied_objects) > 10:
                    logger.debug(f"  ... and {len(merger.copied_objects) - 10} more")
            
            # Save the updated configuration
            if save_config(target_tree, output_file):
                logger.info(f"Configuration saved to {output_file}")
            else:
                logger.error(f"Failed to save configuration to {output_file}")
                raise typer.Exit(1)
        else:
            logger.warning(f"No policies were merged (attempted {total})")
            
            if merger.skipped_policies:
                for name, reason in merger.skipped_policies[:10]:  # Show first 10
                    logger.warning(f"  - {name}: {reason}")
                
                if len(merger.skipped_policies) > 10:
                    logger.warning(f"  ... and {len(merger.skipped_policies) - 10} more")
            
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error merging policies: {e}")
        raise typer.Exit(1)

@merge_app.command("all")
def merge_all_policies(
    source_config: str = typer.Option(..., "--source-config", help="Path to source XML configuration file"),
    target_config: str = typer.Option(..., "--target-config", help="Path to target XML configuration file"),
    source_context: str = typer.Option("shared", "--source-context", help="Source context (shared, device_group, vsys)"),
    target_context: str = typer.Option("shared", "--target-context", help="Target context (shared, device_group, vsys)"),
    source_device_group: Optional[str] = typer.Option(None, "--source-dg", help="Source device group name"),
    target_device_group: Optional[str] = typer.Option(None, "--target-dg", help="Target device group name"),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option("panorama", "--source-type", help="Source device type (firewall or panorama)"),
    target_device_type: str = typer.Option("panorama", "--target-type", help="Target device type (firewall or panorama)"),
    source_version: Optional[str] = typer.Option(None, "--source-version", help="Source PAN-OS version"),
    target_version: Optional[str] = typer.Option(None, "--target-version", help="Target PAN-OS version"),
    skip_if_exists: bool = typer.Option(True, "--skip-if-exists/--replace", help="Skip if policy already exists"),
    copy_references: bool = typer.Option(True, "--copy-references/--no-copy-references", help="Copy object references"),
    output_file: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration")
):
    """Merge all policy types from source configuration to target configuration"""
    try:
        # Load source and target configurations
        from panflow.core.config_loader import load_config_from_file, save_config
        
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)
        
        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)
        
        # Create policy merger
        merger = PolicyMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version
        )
        
        # Determine policy types based on device type
        from panflow.constants import POLICY_TYPES
        
        policy_types = POLICY_TYPES.get(source_device_type.lower(), [])
        
        if not policy_types:
            logger.error(f"Unknown device type: {source_device_type}")
            raise typer.Exit(1)
        
        # Merge all policy types
        results = merger.merge_all_policies(
            policy_types,
            source_context,
            target_context,
            skip_if_exists,
            copy_references,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys
        )
        
        # Calculate total policies merged
        total_copied = sum(copied for copied, _ in results.values())
        total_attempted = sum(total for _, total in results.values())
        
        if total_copied > 0:
            logger.info(f"Successfully merged {total_copied} of {total_attempted} policies across all policy types")
            
            # Log details per policy type
            for policy_type, (copied, total) in results.items():
                if total > 0:
                    logger.info(f"  - {policy_type}: {copied} of {total} policies merged")
            
            # Log copied objects
            if copy_references and merger.copied_objects:
                logger.info(f"Copied {len(merger.copied_objects)} referenced objects")
                
                # Count by type
                object_counts = {}
                for obj_type, _ in merger.copied_objects:
                    object_counts[obj_type] = object_counts.get(obj_type, 0) + 1
                
                for obj_type, count in object_counts.items():
                    logger.info(f"  - {obj_type}: {count} objects copied")
            
            # Save the updated configuration
            if save_config(target_tree, output_file):
                logger.info(f"Configuration saved to {output_file}")
            else:
                logger.error(f"Failed to save configuration to {output_file}")
                raise typer.Exit(1)
        else:
            logger.warning(f"No policies were merged (attempted {total_attempted})")
            
            if merger.skipped_policies:
                for name, reason in merger.skipped_policies[:10]:  # Show first 10
                    logger.warning(f"  - {name}: {reason}")
                
                if len(merger.skipped_policies) > 10:
                    logger.warning(f"  ... and {len(merger.skipped_policies) - 10} more")
            
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error merging all policies: {e}")
        raise typer.Exit(1)

# Add to the imports in cli.py
from panflow.core.object_merger import ObjectMerger

# Add these commands to the merge_app group in cli.py

@merge_app.command("object")
def merge_object(
    source_config: str = typer.Option(..., "--source-config", help="Path to source XML configuration file"),
    target_config: str = typer.Option(..., "--target-config", help="Path to target XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to merge (address, service, etc.)"),
    object_name: str = typer.Option(..., "--name", "-n", help="Name of the object to merge"),
    source_context: str = typer.Option("shared", "--source-context", help="Source context (shared, device_group, vsys)"),
    target_context: str = typer.Option("shared", "--target-context", help="Target context (shared, device_group, vsys)"),
    source_device_group: Optional[str] = typer.Option(None, "--source-dg", help="Source device group name"),
    target_device_group: Optional[str] = typer.Option(None, "--target-dg", help="Target device group name"),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option("panorama", "--source-type", help="Source device type (firewall or panorama)"),
    target_device_type: str = typer.Option("panorama", "--target-type", help="Target device type (firewall or panorama)"),
    source_version: Optional[str] = typer.Option(None, "--source-version", help="Source PAN-OS version"),
    target_version: Optional[str] = typer.Option(None, "--target-version", help="Target PAN-OS version"),
    skip_if_exists: bool = typer.Option(True, "--skip-if-exists/--replace", help="Skip if object already exists"),
    copy_references: bool = typer.Option(True, "--copy-references/--no-copy-references", help="Copy group members"),
    output_file: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration")
):
    """Merge a single object from source configuration to target configuration"""
    try:
        # Load source and target configurations
        from panflow.core.config_loader import load_config_from_file, save_config, detect_device_type
        
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)
        
        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)
        
        # Create object merger
        merger = ObjectMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version
        )
        
        # Merge the object
        result = merger.copy_object(
            object_type,
            object_name,
            source_context,
            target_context,
            skip_if_exists,
            copy_references,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys
        )
        
        if result:
            logger.info(f"Successfully merged object '{object_name}'")
            
            # Log referenced/copied objects
            if copy_references and merger.referenced_objects:
                logger.info(f"Referenced {len(merger.referenced_objects)} objects")
                for obj_type, obj_name in merger.referenced_objects:
                    logger.debug(f"  - {obj_type}: {obj_name}")
            
            # Save the updated configuration
            if save_config(target_tree, output_file):
                logger.info(f"Configuration saved to {output_file}")
            else:
                logger.error(f"Failed to save configuration to {output_file}")
                raise typer.Exit(1)
        else:
            logger.error(f"Failed to merge object '{object_name}'")
            
            if merger.skipped_objects:
                for obj_type, name, reason in merger.skipped_objects:
                    logger.warning(f"  - {obj_type} '{name}': {reason}")
                    
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error merging object: {e}")
        raise typer.Exit(1)

@merge_app.command("objects")
def merge_objects(
    source_config: str = typer.Option(..., "--source-config", help="Path to source XML configuration file"),
    target_config: str = typer.Option(..., "--target-config", help="Path to target XML configuration file"),
    object_type: str = typer.Option(..., "--type", "-t", help="Type of object to merge (address, service, etc.)"),
    names_file: Optional[str] = typer.Option(None, "--names-file", help="File containing object names to merge (one per line)"),
    criteria_file: Optional[str] = typer.Option(None, "--criteria", help="JSON file with filter criteria"),
    source_context: str = typer.Option("shared", "--source-context", help="Source context (shared, device_group, vsys)"),
    target_context: str = typer.Option("shared", "--target-context", help="Target context (shared, device_group, vsys)"),
    source_device_group: Optional[str] = typer.Option(None, "--source-dg", help="Source device group name"),
    target_device_group: Optional[str] = typer.Option(None, "--target-dg", help="Target device group name"),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option("panorama", "--source-type", help="Source device type (firewall or panorama)"),
    target_device_type: str = typer.Option("panorama", "--target-type", help="Target device type (firewall or panorama)"),
    source_version: Optional[str] = typer.Option(None, "--source-version", help="Source PAN-OS version"),
    target_version: Optional[str] = typer.Option(None, "--target-version", help="Target PAN-OS version"),
    skip_if_exists: bool = typer.Option(True, "--skip-if-exists/--replace", help="Skip if object already exists"),
    copy_references: bool = typer.Option(True, "--copy-references/--no-copy-references", help="Copy group members"),
    output_file: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration")
):
    """Merge multiple objects from source configuration to target configuration"""
    try:
        # Load source and target configurations
        from panflow.core.config_loader import load_config_from_file, save_config, detect_device_type
        
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)
        
        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)
        
        # Create object merger
        merger = ObjectMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version
        )
        
        # Get object names or criteria
        object_names = None
        filter_criteria = None
        
        if names_file:
            with open(names_file, 'r') as f:
                object_names = [line.strip() for line in f if line.strip()]
        
        if criteria_file:
            with open(criteria_file, 'r') as f:
                import json
                filter_criteria = json.load(f)
        
        if not object_names and not filter_criteria:
            logger.error("Either object names file or criteria file must be provided")
            raise typer.Exit(1)
        
        # Merge the objects
        copied, total = merger.copy_objects(
            object_type,
            source_context,
            target_context,
            object_names,
            filter_criteria,
            skip_if_exists,
            copy_references,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys
        )
        
        if copied > 0:
            logger.info(f"Successfully merged {copied} of {total} {object_type} objects")
            
            # Save the updated configuration
            if save_config(target_tree, output_file):
                logger.info(f"Configuration saved to {output_file}")
            else:
                logger.error(f"Failed to save configuration to {output_file}")
                raise typer.Exit(1)
        else:
            logger.warning(f"No {object_type} objects were merged (attempted {total})")
            
            if merger.skipped_objects:
                for obj_type, name, reason in merger.skipped_objects[:10]:  # Show first 10
                    logger.warning(f"  - {obj_type} '{name}': {reason}")
                
                if len(merger.skipped_objects) > 10:
                    logger.warning(f"  ... and {len(merger.skipped_objects) - 10} more")
            
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error merging objects: {e}")
        raise typer.Exit(1)

@merge_app.command("all-objects")
def merge_all_objects(
    source_config: str = typer.Option(..., "--source-config", help="Path to source XML configuration file"),
    target_config: str = typer.Option(..., "--target-config", help="Path to target XML configuration file"),
    source_context: str = typer.Option("shared", "--source-context", help="Source context (shared, device_group, vsys)"),
    target_context: str = typer.Option("shared", "--target-context", help="Target context (shared, device_group, vsys)"),
    source_device_group: Optional[str] = typer.Option(None, "--source-dg", help="Source device group name"),
    target_device_group: Optional[str] = typer.Option(None, "--target-dg", help="Target device group name"),
    source_vsys: str = typer.Option("vsys1", "--source-vsys", help="Source VSYS name"),
    target_vsys: str = typer.Option("vsys1", "--target-vsys", help="Target VSYS name"),
    source_device_type: str = typer.Option("panorama", "--source-type", help="Source device type (firewall or panorama)"),
    target_device_type: str = typer.Option("panorama", "--target-type", help="Target device type (firewall or panorama)"),
    source_version: Optional[str] = typer.Option(None, "--source-version", help="Source PAN-OS version"),
    target_version: Optional[str] = typer.Option(None, "--target-version", help="Target PAN-OS version"),
    skip_if_exists: bool = typer.Option(True, "--skip-if-exists/--replace", help="Skip if object already exists"),
    copy_references: bool = typer.Option(True, "--copy-references/--no-copy-references", help="Copy group members"),
    output_file: str = typer.Option(..., "--output", "-o", help="Output file for updated configuration")
):
    """Merge all object types from source configuration to target configuration"""
    try:
        # Load source and target configurations
        from panflow.core.config_loader import load_config_from_file, save_config, detect_device_type
        
        source_tree, detected_source_version = load_config_from_file(source_config)
        source_version = source_version or detected_source_version
        source_device_type = source_device_type or detect_device_type(source_tree)
        
        # If target is the same as source, use the same tree
        if target_config == source_config:
            target_tree = source_tree
            target_version = source_version
            target_device_type = source_device_type
        else:
            target_tree, detected_target_version = load_config_from_file(target_config)
            target_version = target_version or detected_target_version
            target_device_type = target_device_type or detect_device_type(target_tree)
        
        # Create object merger
        merger = ObjectMerger(
            source_tree,
            target_tree,
            source_device_type,
            target_device_type,
            source_version,
            target_version
        )
        
        # Determine object types to merge
        from panflow.constants import OBJECT_TYPES
        object_types = ["address", "address_group", "service", "service_group", 
                        "application_group", "tag"]
        
        # Merge all object types
        results = merger.merge_all_objects(
            object_types,
            source_context,
            target_context,
            skip_if_exists,
            copy_references,
            source_device_group=source_device_group,
            target_device_group=target_device_group,
            source_vsys=source_vsys,
            target_vsys=target_vsys
        )
        
        # Calculate total objects merged
        total_copied = sum(copied for copied, _ in results.values())
        total_attempted = sum(total for _, total in results.values())
        
        if total_copied > 0:
            logger.info(f"Successfully merged {total_copied} of {total_attempted} objects across all types")
            
            # Log details per object type
            for object_type, (copied, total) in results.items():
                if total > 0:
                    logger.info(f"  - {object_type}: {copied} of {total} objects merged")
            
            # Save the updated configuration
            if save_config(target_tree, output_file):
                logger.info(f"Configuration saved to {output_file}")
            else:
                logger.error(f"Failed to save configuration to {output_file}")
                raise typer.Exit(1)
        else:
            logger.warning(f"No objects were merged (attempted {total_attempted})")
            
            if merger.skipped_objects:
                for obj_type, name, reason in merger.skipped_objects[:10]:  # Show first 10
                    logger.warning(f"  - {obj_type} '{name}': {reason}")
                
                if len(merger.skipped_objects) > 10:
                    logger.warning(f"  ... and {len(merger.skipped_objects) - 10} more")
            
            raise typer.Exit(1)
            
    except Exception as e:
        logger.error(f"Error merging all objects: {e}")
        raise typer.Exit(1)
# Run the CLI
if __name__ == "__main__":
    app()