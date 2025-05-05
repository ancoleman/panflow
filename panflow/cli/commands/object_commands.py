"""
Object management commands for the PANFlow CLI.

This module provides commands for managing PAN-OS objects.
"""

import json
import typer
import logging
from typing import Optional, Dict, Any

from panflow import PANFlowConfig
from ..app import object_app
from ..common import (
    ConfigOptions, ContextOptions, ObjectOptions
)

# Get logger
logger = logging.getLogger("panflow")

@object_app.command("list")
def list_objects(
    config: str = ConfigOptions.config_file(),
    object_type: str = ObjectOptions.object_type(),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results (JSON format)"),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    version: Optional[str] = ConfigOptions.version(),
):
    """List objects of specified type"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Get context kwargs
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
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
    config: str = ConfigOptions.config_file(),
    object_type: str = ObjectOptions.object_type(),
    name: str = ObjectOptions.object_name(),
    properties_file: str = typer.Option(..., "--properties", "-p", help="JSON file with object properties"),
    output: str = ConfigOptions.output_file(),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    version: Optional[str] = ConfigOptions.version(),
):
    """Add a new object"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Read properties from file
        with open(properties_file, 'r') as f:
            properties = json.load(f)
        
        # Get context kwargs
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
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
    config: str = ConfigOptions.config_file(),
    object_type: str = ObjectOptions.object_type(),
    name: str = ObjectOptions.object_name(),
    properties_file: str = typer.Option(..., "--properties", "-p", help="JSON file with updated object properties"),
    output: str = ConfigOptions.output_file(),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    version: Optional[str] = ConfigOptions.version(),
):
    """Update an existing object"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Read properties from file
        with open(properties_file, 'r') as f:
            properties = json.load(f)
        
        # Get context kwargs
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
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
    config: str = ConfigOptions.config_file(),
    object_type: str = ObjectOptions.object_type(),
    name: str = ObjectOptions.object_name(),
    output: str = ConfigOptions.output_file(),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    version: Optional[str] = ConfigOptions.version(),
):
    """Delete an object"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Get context kwargs
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
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
    config: str = ConfigOptions.config_file(),
    object_type: str = ObjectOptions.object_type(),
    criteria_file: str = typer.Option(..., "--criteria", help="JSON file with filter criteria"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file for results (JSON format)"),
    device_type: str = ConfigOptions.device_type(),
    context: str = ContextOptions.context_type(),
    device_group: Optional[str] = ContextOptions.device_group(),
    vsys: str = ContextOptions.vsys(),
    template: Optional[str] = ContextOptions.template(),
    version: Optional[str] = ConfigOptions.version(),
):
    """Filter objects based on criteria"""
    try:
        # Initialize the configuration
        xml_config = PANFlowConfig(config_file=config, device_type=device_type, version=version)
        
        # Read criteria from file
        with open(criteria_file, 'r') as f:
            criteria = json.load(f)
        
        # Get context kwargs
        context_kwargs = ContextOptions.get_context_kwargs(context, device_group, vsys, template)
        
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