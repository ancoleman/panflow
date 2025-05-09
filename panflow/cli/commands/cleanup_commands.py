"""
Cleanup commands for PanFlow CLI.

This module provides commands for cleaning up unused objects and policies in PAN-OS configurations.
"""

import logging
import json
from typing import Dict, Any, Optional, List, Set
import typer

from ..app import app
from ..common import ConfigOptions, ContextOptions, ObjectOptions

# Import core modules
from panflow import PANFlowConfig
from panflow.reporting import (
    generate_unused_objects_report,
    generate_security_rule_coverage_report
)
from panflow.core.graph_service import GraphService

# Get logger
logger = logging.getLogger("panflow")

# Create cleanup app
cleanup_app = typer.Typer(help="Clean up unused objects and policies")

# Register with main app
app.add_typer(cleanup_app, name="cleanup")

@cleanup_app.command("unused-objects")
def cleanup_unused_objects(
    config: str = ConfigOptions.config_file(),
    output: str = ConfigOptions.output_file(),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    object_types: List[str] = typer.Option(["address"], "--type", "-t", help="Types of objects to clean up"),
    exclude_file: Optional[str] = typer.Option(None, "--exclude-file", help="JSON file with list of object names to exclude from cleanup"),
    dry_run: bool = ConfigOptions.dry_run(),
    report_file: Optional[str] = typer.Option(None, "--report-file", "-r", help="JSON file to save the report of cleaned-up objects"),
    version: Optional[str] = ConfigOptions.version(),
):
    """
    Find and remove unused objects from the configuration.
    
    This command identifies objects that are not referenced anywhere in the configuration
    and removes them to clean up your rule base.
    
    By default, it operates on address objects only, but can be configured to handle
    other object types like services and tags.
    
    Examples:
    
        # Find and report on unused address objects without making changes (dry run)
        python cli.py cleanup unused-objects --config firewall.xml --dry-run
        
        # Clean up unused address objects and save the updated configuration
        python cli.py cleanup unused-objects --config firewall.xml --output cleaned.xml
        
        # Clean up multiple object types (address and service) with a report
        python cli.py cleanup unused-objects --config firewall.xml --output cleaned.xml --type address --type service --report-file cleanup-report.json
        
        # Exclude specific objects from cleanup
        python cli.py cleanup unused-objects --config firewall.xml --output cleaned.xml --exclude-file protected-objects.json
    """
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Get context kwargs
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
        # Build exclude list if specified
        exclude_list = set()
        if exclude_file:
            try:
                with open(exclude_file, 'r') as f:
                    exclude_data = json.load(f)
                    if isinstance(exclude_data, list):
                        exclude_list = set(exclude_data)
                    else:
                        exclude_list = set(exclude_data.get('objects', []))
                logger.info(f"Loaded {len(exclude_list)} objects to exclude from cleanup")
            except Exception as e:
                logger.error(f"Error loading exclude file {exclude_file}: {e}")
                raise typer.Exit(1)
        
        # Track changes for reporting
        cleanup_report = {
            "summary": {
                "total_unused_found": 0,
                "total_cleaned_up": 0,
                "excluded": len(exclude_list),
                "object_types": object_types
            },
            "cleaned_objects": {}
        }
        
        # Process each object type
        for obj_type in object_types:
            # Generate unused objects report
            report_data = generate_unused_objects_report(
                xml_config.tree,
                xml_config.device_type,  # Use detected device_type from PANFlowConfig
                context,
                xml_config.version,
                object_type=obj_type,  # Pass the object type
                **context_kwargs
            )
            
            unused_objects = report_data.get('unused_objects', [])
            # Filter out objects in the exclude list
            filtered_unused = [obj for obj in unused_objects if obj['name'] not in exclude_list]
            
            # Update report
            cleanup_report["summary"]["total_unused_found"] += len(unused_objects)
            cleanup_report["cleaned_objects"][obj_type] = []
            
            logger.info(f"Found {len(unused_objects)} unused {obj_type} objects.")
            logger.info(f"After applying exclusions: {len(filtered_unused)} objects will be processed.")
            
            if dry_run:
                # In dry-run mode, just report what would be deleted
                if filtered_unused:
                    logger.info(f"Dry run: The following {obj_type} objects would be deleted:")
                    for obj in filtered_unused:
                        logger.info(f"  - {obj['name']}")
                    cleanup_report["cleaned_objects"][obj_type] = [obj['name'] for obj in filtered_unused]
            else:
                # Actually delete the objects
                deleted_count = 0
                for obj in filtered_unused:
                    try:
                        if xml_config.delete_object(obj_type, obj['name'], context, **context_kwargs):
                            logger.info(f"Deleted unused {obj_type} object '{obj['name']}'")
                            cleanup_report["cleaned_objects"][obj_type].append(obj['name'])
                            deleted_count += 1
                        else:
                            logger.warning(f"Failed to delete {obj_type} object '{obj['name']}'")
                    except Exception as e:
                        logger.error(f"Error deleting {obj_type} object '{obj['name']}': {e}")
                
                cleanup_report["summary"]["total_cleaned_up"] += deleted_count
                logger.info(f"Cleaned up {deleted_count} unused {obj_type} objects")
        
        # Save the report if requested
        if report_file:
            with open(report_file, 'w') as f:
                json.dump(cleanup_report, f, indent=2)
            logger.info(f"Cleanup report saved to {report_file}")
        
        # Save the updated configuration if not in dry-run mode
        if not dry_run and cleanup_report["summary"]["total_cleaned_up"] > 0:
            if xml_config.save(output):
                logger.info(f"Updated configuration saved to {output}")
            else:
                logger.error(f"Failed to save configuration to {output}")
                raise typer.Exit(1)
        
        # Summary message
        if dry_run:
            logger.info(f"Dry run summary: Would have cleaned up {sum(len(objs) for objs in cleanup_report['cleaned_objects'].values())} unused objects")
        else:
            logger.info(f"Cleanup summary: Removed {cleanup_report['summary']['total_cleaned_up']} unused objects")
    
    except Exception as e:
        logger.error(f"Error cleaning up unused objects: {e}", exc_info=True)
        raise typer.Exit(1)

@cleanup_app.command("disabled-policies")
def cleanup_disabled_policies(
    config: str = ConfigOptions.config_file(),
    output: str = ConfigOptions.output_file(),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    policy_types: List[str] = typer.Option(["security_rules"], "--type", "-t", help="Types of policies to clean up"),
    exclude_file: Optional[str] = typer.Option(None, "--exclude-file", help="JSON file with list of policy names to exclude from cleanup"),
    dry_run: bool = ConfigOptions.dry_run(),
    report_file: Optional[str] = typer.Option(None, "--report-file", "-r", help="JSON file to save the report of cleaned-up policies"),
    version: Optional[str] = ConfigOptions.version(),
):
    """
    Find and remove disabled policies from the configuration.
    
    This command identifies policies that are disabled in the configuration
    and removes them to clean up your rule base.
    
    By default, it operates on security rules only, but can be configured to handle
    other policy types.
    
    Examples:
    
        # Find and report on disabled security rules without making changes (dry run)
        python cli.py cleanup disabled-policies --config firewall.xml --dry-run
        
        # Clean up disabled policies and save the updated configuration
        python cli.py cleanup disabled-policies --config firewall.xml --output cleaned.xml
        
        # Clean up multiple policy types with a report
        python cli.py cleanup disabled-policies --config firewall.xml --output cleaned.xml --type security_pre_rules --type security_post_rules --report-file cleanup-report.json
        
        # Exclude specific policies from cleanup
        python cli.py cleanup disabled-policies --config firewall.xml --output cleaned.xml --exclude-file protected-policies.json
    """
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Get context kwargs
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
        # Build exclude list if specified
        exclude_list = set()
        if exclude_file:
            try:
                with open(exclude_file, 'r') as f:
                    exclude_data = json.load(f)
                    if isinstance(exclude_data, list):
                        exclude_list = set(exclude_data)
                    else:
                        exclude_list = set(exclude_data.get('policies', []))
                logger.info(f"Loaded {len(exclude_list)} policies to exclude from cleanup")
            except Exception as e:
                logger.error(f"Error loading exclude file {exclude_file}: {e}")
                raise typer.Exit(1)
        
        # Track changes for reporting
        cleanup_report = {
            "summary": {
                "total_disabled_found": 0,
                "total_cleaned_up": 0,
                "excluded": len(exclude_list),
                "policy_types": policy_types
            },
            "cleaned_policies": {}
        }
        
        # Process each policy type
        for policy_type in policy_types:
            disabled_rules = []
            
            # For panorama device type, we need to check both pre and post rulebases
            if xml_config.device_type.lower() == "panorama":
                # Check pre-rules first
                if device_group:
                    # Directly query the rules and check for disabled attribute
                    pre_xpath = f"/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='{device_group}']/pre-rulebase/security/rules/entry[disabled='yes']"
                    pre_disabled_elements = xml_config.tree.xpath(pre_xpath)
                    pre_disabled_rules = [elem.get('name') for elem in pre_disabled_elements if elem.get('name')]
                    logger.debug(f"Found {len(pre_disabled_rules)} disabled pre-rules")
                    disabled_rules.extend(pre_disabled_rules)
                    
                    # Make sure policy_type is set to the correct Panorama policy type
                    # This ensures the delete_policy operation uses the correct XPath
                    policy_type = "security_pre_rules"
                    
                    # Check post-rules
                    post_xpath = f"/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='{device_group}']/post-rulebase/security/rules/entry[disabled='yes']"
                    post_disabled_elements = xml_config.tree.xpath(post_xpath)
                    post_disabled_rules = [elem.get('name') for elem in post_disabled_elements if elem.get('name')]
                    logger.debug(f"Found {len(post_disabled_rules)} disabled post-rules")
                    disabled_rules.extend(post_disabled_rules)
            else:
                # For firewall, just check the main rulebase
                disabled_xpath = f"/config/devices/entry[@name='localhost.localdomain']/vsys/entry[@name='{vsys}']/rulebase/security/rules/entry[disabled='yes']"
                disabled_elements = xml_config.tree.xpath(disabled_xpath)
                disabled_rules = [elem.get('name') for elem in disabled_elements if elem.get('name')]
                
            # Filter out policies in the exclude list
            filtered_disabled = [rule for rule in disabled_rules if rule not in exclude_list]
            
            # Update report
            cleanup_report["summary"]["total_disabled_found"] += len(disabled_rules)
            cleanup_report["cleaned_policies"][policy_type] = []
            
            logger.info(f"Found {len(disabled_rules)} disabled {policy_type}.")
            logger.info(f"After applying exclusions: {len(filtered_disabled)} policies will be processed.")
            
            if dry_run:
                # In dry-run mode, just report what would be deleted
                if filtered_disabled:
                    logger.info(f"Dry run: The following {policy_type} would be deleted:")
                    for rule_name in filtered_disabled:
                        logger.info(f"  - {rule_name}")
                    cleanup_report["cleaned_policies"][policy_type] = filtered_disabled
            else:
                # Actually delete the policies
                deleted_count = 0
                for rule_name in filtered_disabled:
                    try:
                        # For Panorama, determine if this is a pre or post rule
                        if xml_config.device_type.lower() == "panorama":
                            # Check pre-rules
                            pre_xpath = f"/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='{device_group}']/pre-rulebase/security/rules/entry[@name='{rule_name}']"
                            pre_rule = xml_config.tree.xpath(pre_xpath)
                            
                            if pre_rule:
                                # This is a pre-rule
                                delete_policy_type = "security_pre_rules"
                            else:
                                # Must be a post-rule
                                delete_policy_type = "security_post_rules"
                        else:
                            # For firewall, use the standard policy type
                            delete_policy_type = policy_type
                            
                        if xml_config.delete_policy(delete_policy_type, rule_name, context, **context_kwargs):
                            logger.info(f"Deleted disabled {delete_policy_type} '{rule_name}'")
                            cleanup_report["cleaned_policies"][policy_type].append(rule_name)
                            deleted_count += 1
                        else:
                            logger.warning(f"Failed to delete {delete_policy_type} '{rule_name}'")
                    except Exception as e:
                        logger.error(f"Error deleting policy '{rule_name}': {e}")
                
                cleanup_report["summary"]["total_cleaned_up"] += deleted_count
                logger.info(f"Cleaned up {deleted_count} disabled {policy_type}")
        
        # Save the report if requested
        if report_file:
            with open(report_file, 'w') as f:
                json.dump(cleanup_report, f, indent=2)
            logger.info(f"Cleanup report saved to {report_file}")
        
        # Save the updated configuration if not in dry-run mode
        if not dry_run and cleanup_report["summary"]["total_cleaned_up"] > 0:
            if xml_config.save(output):
                logger.info(f"Updated configuration saved to {output}")
            else:
                logger.error(f"Failed to save configuration to {output}")
                raise typer.Exit(1)
        
        # Summary message
        if dry_run:
            logger.info(f"Dry run summary: Would have cleaned up {sum(len(rules) for rules in cleanup_report['cleaned_policies'].values())} disabled policies")
        else:
            logger.info(f"Cleanup summary: Removed {cleanup_report['summary']['total_cleaned_up']} disabled policies")
    
    except Exception as e:
        logger.error(f"Error cleaning up disabled policies: {e}", exc_info=True)
        raise typer.Exit(1)