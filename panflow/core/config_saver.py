"""
Configuration saver for PANFlow

This module provides utilities for saving PAN-OS XML configurations
to files, with features like timestamping, backups, and validation.
"""

import os
import json
import shutil
import logging
from typing import Dict, Any, Optional, Union, List, Tuple
from datetime import datetime
import zipfile

# Try to import lxml first, fall back to ElementTree if not available
try:
    from lxml import etree
    HAVE_LXML = True
except ImportError:
    import xml.etree.ElementTree as etree
    HAVE_LXML = False

from .xml.base import (
    parse_xml, prettify_xml, validate_xml, element_to_dict
)
from .exceptions import PANFlowError, ParseError

logger = logging.getLogger("panflow")

class ConfigSaverError(PANFlowError):
    """Base exception for configuration saving operations."""
    pass

class ConfigSaver:
    """
    Class for saving PAN-OS XML configurations.
    
    Provides methods for saving configurations with backups, timestamps,
    and various export formats.
    """
    
    def __init__(
        self,
        config_dir: str = '.',
        backup_dir: Optional[str] = None,
        create_backup: bool = True,
        validate_before_save: bool = False,
        schema_file: Optional[str] = None,
        pretty_print: bool = True
    ):
        """
        Initialize the ConfigSaver with specified options.
        
        Args:
            config_dir: Directory for saving configurations
            backup_dir: Directory for backups (if None, uses config_dir/backups)
            create_backup: Whether to back up existing files before overwriting
            validate_before_save: Whether to validate XML before saving
            schema_file: XML Schema file for validation
            pretty_print: Whether to pretty-print XML when saving
        """
        self.config_dir = os.path.abspath(config_dir)
        self.backup_dir = os.path.abspath(backup_dir) if backup_dir else os.path.join(self.config_dir, 'backups')
        self.create_backup = create_backup
        self.validate_before_save = validate_before_save
        self.schema_file = schema_file
        self.pretty_print = pretty_print
        
        # Create directories if they don't exist
        os.makedirs(self.config_dir, exist_ok=True)
        if self.create_backup:
            os.makedirs(self.backup_dir, exist_ok=True)
    
    def save(
        self,
        tree_or_element: Union[etree._ElementTree, etree._Element],
        filename: str,
        overwrite: bool = True
    ) -> str:
        """
        Save XML configuration to a file.
        
        Args:
            tree_or_element: ElementTree or Element to save
            filename: Target filename (with or without .xml extension)
            overwrite: Whether to overwrite existing file
            
        Returns:
            Path to the saved file
            
        Raises:
            ConfigSaverError: If saving fails
        """
        try:
            # Ensure filename has .xml extension
            if not filename.lower().endswith('.xml'):
                filename += '.xml'
            
            # Construct full file path
            file_path = os.path.join(self.config_dir, filename)
            
            # Check if file exists and create backup if needed
            if os.path.exists(file_path):
                if not overwrite:
                    raise ConfigSaverError(f"File already exists: {file_path}")
                
                if self.create_backup:
                    self._create_backup(file_path)
            
            # Validate if enabled
            if self.validate_before_save and self.schema_file:
                tree = tree_or_element if isinstance(tree_or_element, etree._ElementTree) else etree.ElementTree(tree_or_element)
                valid, error = validate_xml(tree, self.schema_file)
                if not valid:
                    raise ConfigSaverError(f"XML validation failed: {error}")
            
            # Write the XML to file
            if isinstance(tree_or_element, etree._ElementTree):
                tree = tree_or_element
            else:
                tree = etree.ElementTree(tree_or_element)
            
            if self.pretty_print and HAVE_LXML:
                xml_string = prettify_xml(tree)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(xml_string)
            else:
                tree.write(file_path, encoding='utf-8', xml_declaration=True)
            
            logger.info(f"Configuration saved to {file_path}")
            return file_path
        
        except Exception as e:
            if not isinstance(e, ConfigSaverError):
                logger.error(f"Error saving configuration: {e}")
                raise ConfigSaverError(f"Failed to save configuration: {e}")
            raise
    
    def save_with_timestamp(
        self,
        tree_or_element: Union[etree._ElementTree, etree._Element],
        base_filename: str,
        timestamp_format: str = "%Y%m%d_%H%M%S"
    ) -> str:
        """
        Save configuration with a timestamp in the filename.
        
        Args:
            tree_or_element: ElementTree or Element to save
            base_filename: Base filename without extension
            timestamp_format: Format for timestamp
            
        Returns:
            Path to the saved file
        """
        timestamp = datetime.now().strftime(timestamp_format)
        filename = f"{base_filename}_{timestamp}.xml"
        return self.save(tree_or_element, filename, overwrite=True)
    
    def save_as_json(
        self,
        tree_or_element: Union[etree._ElementTree, etree._Element],
        filename: str,
        indent: int = 2,
        overwrite: bool = True
    ) -> str:
        """
        Save configuration as JSON.
        
        Args:
            tree_or_element: ElementTree or Element to save
            filename: Target filename (with or without .json extension)
            indent: JSON indentation
            overwrite: Whether to overwrite existing file
            
        Returns:
            Path to the saved file
            
        Raises:
            ConfigSaverError: If saving fails
        """
        try:
            # Ensure filename has .json extension
            if not filename.lower().endswith('.json'):
                filename += '.json'
            
            # Construct full file path
            file_path = os.path.join(self.config_dir, filename)
            
            # Check if file exists and create backup if needed
            if os.path.exists(file_path):
                if not overwrite:
                    raise ConfigSaverError(f"File already exists: {file_path}")
                
                if self.create_backup:
                    self._create_backup(file_path)
            
            # Convert XML to dictionary
            element = tree_or_element if isinstance(tree_or_element, etree._Element) else tree_or_element.getroot()
            data = element_to_dict(element)
            
            # Write the JSON to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent)
            
            logger.info(f"Configuration saved as JSON to {file_path}")
            return file_path
        
        except Exception as e:
            logger.error(f"Error saving configuration as JSON: {e}")
            raise ConfigSaverError(f"Failed to save configuration as JSON: {e}")
    
    def create_archive(
        self,
        files: List[str],
        archive_name: str,
        format: str = 'zip',
        base_dir: Optional[str] = None
    ) -> str:
        """
        Create an archive of configuration files.
        
        Args:
            files: List of files to archive
            archive_name: Name of the archive file
            format: Archive format ('zip' or 'tar')
            base_dir: Base directory for resolving relative paths
            
        Returns:
            Path to the created archive
            
        Raises:
            ConfigSaverError: If creating the archive fails
        """
        try:
            # Default base dir to config_dir
            if base_dir is None:
                base_dir = self.config_dir
            
            # Ensure archive has the appropriate extension
            if format == 'zip' and not archive_name.lower().endswith('.zip'):
                archive_name += '.zip'
            elif format == 'tar' and not archive_name.lower().endswith('.tar.gz'):
                archive_name += '.tar.gz'
            
            # Construct full archive path
            archive_path = os.path.join(self.config_dir, archive_name)
            
            # Create archive based on format
            if format == 'zip':
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file in files:
                        file_path = os.path.join(base_dir, file) if not os.path.isabs(file) else file
                        if os.path.exists(file_path):
                            arcname = os.path.basename(file_path)
                            zipf.write(file_path, arcname)
                        else:
                            logger.warning(f"File not found: {file_path}")
            elif format == 'tar':
                import tarfile
                with tarfile.open(archive_path, 'w:gz') as tarf:
                    for file in files:
                        file_path = os.path.join(base_dir, file) if not os.path.isabs(file) else file
                        if os.path.exists(file_path):
                            arcname = os.path.basename(file_path)
                            tarf.add(file_path, arcname)
                        else:
                            logger.warning(f"File not found: {file_path}")
            else:
                raise ConfigSaverError(f"Unsupported archive format: {format}")
            
            logger.info(f"Created archive: {archive_path}")
            return archive_path
        
        except Exception as e:
            logger.error(f"Error creating archive: {e}")
            raise ConfigSaverError(f"Failed to create archive: {e}")
    
    def _create_backup(self, file_path: str) -> str:
        """
        Create a backup of a file before modification.
        
        Args:
            file_path: Path to the file to back up
            
        Returns:
            Path to the backup file
        """
        backup_filename = f"{os.path.basename(file_path)}.bak"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        # If the backup already exists, create a timestamped version
        if os.path.exists(backup_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{os.path.basename(file_path)}.{timestamp}.bak"
            backup_path = os.path.join(self.backup_dir, backup_filename)
        
        # Create backup
        shutil.copy2(file_path, backup_path)
        logger.debug(f"Created backup: {backup_path}")
        return backup_path
    
    def get_saved_configs(
        self,
        pattern: Optional[str] = None,
        include_backups: bool = False
    ) -> List[str]:
        """
        Get a list of saved configuration files.
        
        Args:
            pattern: Optional filename pattern to match
            include_backups: Whether to include backup files
            
        Returns:
            List of configuration file paths
        """
        configs = []
        
        # List files in the config directory
        if os.path.exists(self.config_dir):
            for file in os.listdir(self.config_dir):
                if file.lower().endswith('.xml'):
                    if pattern is None or pattern in file:
                        configs.append(os.path.join(self.config_dir, file))
        
        # List files in the backup directory if requested
        if include_backups and os.path.exists(self.backup_dir):
            for file in os.listdir(self.backup_dir):
                if file.lower().endswith('.xml') or file.lower().endswith('.bak'):
                    if pattern is None or pattern in file:
                        configs.append(os.path.join(self.backup_dir, file))
        
        return sorted(configs)
    
    def cleanup_backups(
        self,
        max_age_days: Optional[int] = None,
        max_files: Optional[int] = None,
        dry_run: bool = False
    ) -> List[str]:
        """
        Clean up old backup files.
        
        Args:
            max_age_days: Maximum age of files to keep (days)
            max_files: Maximum number of backup files to keep
            dry_run: Don't actually delete files, just show what would be deleted
            
        Returns:
            List of files that were deleted (or would be deleted in dry run)
        """
        deleted_files = []
        
        if not os.path.exists(self.backup_dir):
            return deleted_files
        
        # Get all backup files with their modification times
        backups = []
        for file in os.listdir(self.backup_dir):
            if file.lower().endswith(('.xml.bak', '.bak')):
                file_path = os.path.join(self.backup_dir, file)
                mtime = os.path.getmtime(file_path)
                backups.append((file_path, mtime))
        
        # Sort by modification time (oldest first)
        backups.sort(key=lambda x: x[1])
        
        # Delete files based on age
        if max_age_days is not None:
            now = datetime.now().timestamp()
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            for file_path, mtime in backups:
                age_seconds = now - mtime
                if age_seconds > max_age_seconds:
                    deleted_files.append(file_path)
        
        # Delete files based on max count
        if max_files is not None and len(backups) > max_files:
            # How many files to delete
            to_delete = len(backups) - max_files
            
            # Add oldest files to delete list (that aren't already there)
            for i in range(min(to_delete, len(backups))):
                file_path = backups[i][0]
                if file_path not in deleted_files:
                    deleted_files.append(file_path)
        
        # Delete the files if not a dry run
        if not dry_run:
            for file_path in deleted_files:
                try:
                    os.remove(file_path)
                    logger.debug(f"Deleted backup file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")
        
        return deleted_files