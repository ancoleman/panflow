"""
Bulk operations module for PANFlow.

This module provides functionality for bulk operations on PAN-OS configurations.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Union, Tuple

from lxml import etree

from .config_loader import load_config_from_file

def xpath_search(tree, xpath):
    """
    Utility function to safely search XML using XPath.
    
    Args:
        tree: The ElementTree to search
        xpath: XPath expression
        
    Returns:
        List of matched elements
    """
    try:
        return tree.xpath(xpath)
    except Exception as e:
        logger.error(f"XPath search failed: {e}")
        return []

from .xpath_resolver import (
    get_policy_xpath,
    get_object_xpath,
    get_context_xpath,
)
from .graph_utils import ConfigGraph
from .graph_service import GraphService
from .query_language import Query
from .query_engine import QueryExecutor


logger = logging.getLogger("panflow")


class ConfigQuery:
    """
    Class for querying PAN-OS configurations.

    This class provides methods for querying policies and objects with advanced filtering.
    """

    def __init__(self, tree, device_type, context_type, version, **kwargs):
        """
        Initialize a ConfigQuery instance.

        Args:
            tree: ElementTree containing the configuration
            device_type: Type of device ("firewall" or "panorama")
            context_type: Type of context (shared, device_group, vsys)
            version: PAN-OS version
            **kwargs: Additional context parameters (device_group, vsys, etc.)
        """
        self.tree = tree
        self.device_type = device_type
        self.context_type = context_type
        self.version = version
        self.context_kwargs = kwargs

        logger.debug(
            f"Initialized ConfigQuery: device_type={device_type}, context_type={context_type}, "
            f"version={version}, context_kwargs={kwargs}"
        )

    def get_policies(self, policy_type):
        """
        Get policies of the specified type.

        Args:
            policy_type: Type of policy to get (security_pre_rules, nat_rules, etc.)

        Returns:
            List of policy dictionaries with all relevant attributes
        """
        logger.info(f"Getting {policy_type} policies")

        try:
            # Get all policy elements of this type
            policies = self.select_policies(policy_type)

            if not policies:
                logger.info(f"No {policy_type} policies found")
                return []

            # Log names of the policies found to debug issues
            logger.debug(
                f"Found policies with names: {[p.get('name', 'unnamed') for p in policies]}"
            )

            # Convert XML elements to dictionaries
            policy_dicts = []
            for policy in policies:
                policy_dict = self._policy_to_dict(policy)
                policy_dicts.append(policy_dict)

            logger.info(f"Found {len(policy_dicts)} {policy_type} policies")
            return policy_dicts

        except Exception as e:
            logger.error(f"Error getting policies: {str(e)}", exc_info=True)
            return []

    def _policy_to_dict(self, policy_element):
        """
        Convert a policy XML element to a dictionary.

        Args:
            policy_element: The policy XML element

        Returns:
            Dictionary containing the policy attributes
        """
        try:
            # Base policy attributes
            policy_name = policy_element.get("name")
            # Some XML parsers might not handle the attribute correctly, try alternate methods
            if not policy_name:
                # Try to check parent for name attributes
                if hasattr(policy_element, "getparent") and policy_element.getparent() is not None:
                    policy_name = policy_element.getparent().get("name")

            policy_dict = {
                "name": policy_name if policy_name else "unnamed",
                "xml_element": policy_element,  # Keep reference to original element
            }

            # Extract description if present
            description_elem = policy_element.find("./description")
            if description_elem is not None and description_elem.text:
                policy_dict["description"] = description_elem.text

            # Extract common policy attributes
            for simple_attr in ["action", "log-start", "log-end", "disabled"]:
                attr_elem = policy_element.find(f"./{simple_attr}")
                if attr_elem is not None and attr_elem.text:
                    # Convert dashed attribute names to underscore format
                    attr_name = simple_attr.replace("-", "_")
                    policy_dict[attr_name] = attr_elem.text

            # Extract list-type attributes (source, destination, service, application)
            for list_attr in ["from", "to", "source", "destination", "service", "application"]:
                members = policy_element.findall(f"./{list_attr}/member")
                if members:
                    # Convert 'from' and 'to' to source_zone and destination_zone
                    if list_attr == "from":
                        attr_name = "source_zone"
                    elif list_attr == "to":
                        attr_name = "destination_zone"
                    else:
                        attr_name = list_attr

                    policy_dict[attr_name] = [m.text for m in members if m.text]

            # Extract tags
            tags = policy_element.findall("./tag/member")
            if tags:
                policy_dict["tags"] = [t.text for t in tags if t.text]

            # Extract profile settings
            profile_group = policy_element.findall("./profile-setting/group/member")
            if profile_group:
                policy_dict["profile_group"] = [p.text for p in profile_group if p.text]

            return policy_dict

        except Exception as e:
            logger.error(f"Error converting policy element to dict: {str(e)}", exc_info=True)
            # Return minimal dict with name to avoid breaking code that expects a dict
            return {"name": policy_element.get("name", "unknown"), "error": str(e)}

    def select_policies(self, policy_type, criteria=None):
        """
        Select policies matching the criteria with enhanced filtering capabilities.

        Args:
            policy_type: Type of policy to select (security_pre_rules, nat_rules, etc.)
            criteria: Dictionary of criteria to filter policies. Enhanced criteria include:
                - 'field_exists': Check if a field exists
                - 'field_missing': Check if a field is missing
                - 'text_contains': Check if text contains a substring
                - 'regex_match': Use regular expressions for matching
                - 'has_profile_type': Check for specific security profile types
                - 'date_before'/'date_after': Filter by modification date

        Returns:
            List of matching policy elements
        """
        logger.info(f"Selecting {policy_type} policies with criteria: {criteria}")

        # Get base XPath for the policy type
        try:
            base_xpath = get_policy_xpath(
                policy_type,
                self.device_type,
                self.context_type,
                self.version,
                **self.context_kwargs,
            )

            logger.debug(f"Generated base XPath: {base_xpath}")

            # Start with all policies of this type
            results = xpath_search(self.tree, base_xpath)
            initial_count = len(results)
            logger.info(f"Found {initial_count} {policy_type} policies before filtering")

            # Detailed debug logging for investigation
            if initial_count > 0:
                for i, result in enumerate(results):
                    # Check if this element has a name attribute
                    name = result.get("name")
                    # If it doesn't, try to get it from 'entry' parent
                    if not name and hasattr(result, "tag") and result.tag != "entry":
                        # Look for parent entry elements
                        for parent in result.iterancestors():
                            if parent.tag == "entry":
                                name = parent.get("name")
                                break

                    logger.debug(f"Policy {i+1}/{initial_count}: name='{name}', tag='{result.tag}'")
            else:
                logger.debug(f"No policies found with XPath: {base_xpath}")

            # Apply filters if criteria is provided
            if criteria and results:
                logger.debug(f"Applying filtering criteria: {criteria}")
                filtered_results = []

                for policy in results:
                    if self._matches_enhanced_criteria(policy, criteria):
                        policy_name = policy.get("name", "unknown")
                        filtered_results.append(policy)
                        logger.debug(f"Policy '{policy_name}' matches criteria")

                logger.info(f"Filtered down to {len(filtered_results)} matching policies")
                return filtered_results

            return results

        except Exception as e:
            logger.error(f"Error selecting policies: {str(e)}", exc_info=True)
            return []

    def _matches_enhanced_criteria(self, element, criteria):
        """
        Check if an element matches the enhanced criteria.

        Args:
            element: XML element to check
            criteria: Dictionary of enhanced criteria

        Returns:
            bool: True if the element matches all criteria, False otherwise
        """
        import re
        from datetime import datetime

        element_name = element.get("name", "unknown")
        logger.debug(f"Evaluating enhanced criteria for element '{element_name}'")

        try:
            for key, value in criteria.items():
                # Handle enhanced criteria types
                if key == "field_exists":
                    for field in value if isinstance(value, list) else [value]:
                        if not element.xpath(f"./{field}"):
                            logger.debug(
                                f"Element '{element_name}' is missing required field: {field}"
                            )
                            return False

                elif key == "field_missing":
                    for field in value if isinstance(value, list) else [value]:
                        if element.xpath(f"./{field}"):
                            logger.debug(
                                f"Element '{element_name}' has field that should be missing: {field}"
                            )
                            return False

                elif key == "text_contains":
                    field_path, substring = value.get("field", ""), value.get("text", "")
                    field_elements = element.xpath(f"./{field_path}")
                    if not field_elements or not any(
                        substring in (elem.text or "") for elem in field_elements
                    ):
                        logger.debug(f"Element '{element_name}' does not contain text: {substring}")
                        return False

                elif key == "regex_match":
                    field_path, pattern = value.get("field", ""), value.get("pattern", "")
                    field_elements = element.xpath(f"./{field_path}")
                    if not field_elements or not any(
                        re.search(pattern, (elem.text or "")) for elem in field_elements
                    ):
                        logger.debug(
                            f"Element '{element_name}' does not match regex pattern: {pattern}"
                        )
                        return False

                elif key == "has_profile_type":
                    profile_type = value
                    profile_elements = element.xpath(f".//profile-setting//{profile_type}")
                    if not profile_elements:
                        logger.debug(
                            f"Element '{element_name}' does not have profile type: {profile_type}"
                        )
                        return False

                elif key == "date_before" or key == "date_after":
                    # This assumes a 'last-modified' attribute or element
                    date_str = element.get("last-modified", "")
                    if not date_str:
                        mod_elem = element.find("./last-modified")
                        date_str = mod_elem.text if mod_elem is not None else ""

                    if date_str:
                        try:
                            mod_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                            compare_date = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

                            if key == "date_before" and mod_date >= compare_date:
                                logger.debug(
                                    f"Element '{element_name}' modification date {mod_date} is not before {compare_date}"
                                )
                                return False
                            elif key == "date_after" and mod_date <= compare_date:
                                logger.debug(
                                    f"Element '{element_name}' modification date {mod_date} is not after {compare_date}"
                                )
                                return False
                        except ValueError:
                            logger.warning(
                                f"Invalid date format in element '{element_name}' or criteria"
                            )

                # Handle standard field matching (as in the original method)
                elif key == "name":
                    if isinstance(value, list):
                        if element.get("name") not in value:
                            logger.debug(f"Element '{element_name}' name not in list: {value}")
                            return False
                    else:
                        if element.get("name") != value:
                            logger.debug(f"Element '{element_name}' name does not match {value}")
                            return False
                elif key == "has-tag":
                    tag_elements = element.xpath("./tag/member")
                    tag_values = [tag.text for tag in tag_elements if tag.text]
                    if value not in tag_values:
                        logger.debug(f"Element '{element_name}' does not have tag: {value}")
                        return False
                elif key in ["source", "destination", "application", "service"]:
                    member_elements = element.xpath(f"./{key}/member")
                    member_values = [m.text for m in member_elements if m.text]

                    if isinstance(value, list):
                        if not any(v in member_values for v in value):
                            logger.debug(
                                f"Element '{element_name}' {key} values {member_values} don't match any in {value}"
                            )
                            return False
                    else:
                        if value not in member_values:
                            logger.debug(
                                f"Element '{element_name}' {key} values {member_values} don't include {value}"
                            )
                            return False
                else:
                    child_elements = element.xpath(f"./{key}")
                    if not child_elements:
                        logger.debug(f"Element '{element_name}' has no child element: {key}")
                        return False

                    if (
                        value is not None
                        and child_elements[0].text
                        and child_elements[0].text.strip() != str(value).strip()
                    ):
                        logger.debug(
                            f"Element '{element_name}' {key} value '{child_elements[0].text}' doesn't match '{value}'"
                        )
                        return False

            logger.debug(f"Element '{element_name}' matches all criteria")
            return True
        except Exception as e:
            logger.error(
                f"Error matching criteria for element '{element_name}': {str(e)}", exc_info=True
            )
            return False

    def select_objects(self, object_type, criteria=None):
        """
        Select objects matching the criteria.

        Args:
            object_type: Type of object to select (address, service, etc.)
            criteria: Dictionary of criteria to filter objects

        Returns:
            List of matching object elements
        """
        logger.info(f"Selecting {object_type} objects with criteria: {criteria}")

        try:
            # Get base XPath for the object type
            base_xpath = get_object_xpath(
                object_type,
                self.device_type,
                self.context_type,
                self.version,
                **self.context_kwargs,
            )

            logger.debug(f"Generated base XPath: {base_xpath}")

            # Start with all objects of this type
            results = xpath_search(self.tree, base_xpath)
            initial_count = len(results)
            logger.info(f"Found {initial_count} {object_type} objects before filtering")

            # Apply filters if criteria is provided
            if criteria and results:
                logger.debug(f"Applying filtering criteria: {criteria}")
                filtered_results = []

                for obj in results:
                    if self._matches_criteria(obj, criteria):
                        obj_name = obj.get("name", "unknown")
                        filtered_results.append(obj)
                        logger.debug(f"Object '{obj_name}' matches criteria")

                logger.info(f"Filtered down to {len(filtered_results)} matching objects")
                return filtered_results

            return results

        except Exception as e:
            logger.error(f"Error selecting objects: {str(e)}", exc_info=True)
            return []

    def _matches_criteria(self, element, criteria):
        """
        Check if an element matches the provided criteria.

        Args:
            element: XML element to check
            criteria: Dictionary of criteria to match against

        Returns:
            bool: True if the element matches all criteria, False otherwise
        """
        element_name = element.get("name", "unknown")
        logger.debug(f"Evaluating criteria for element '{element_name}'")

        try:
            for key, value in criteria.items():
                # Handle 'name' specially since it's an attribute, not a child element
                if key == "name":
                    if isinstance(value, list):
                        if element.get("name") not in value:
                            logger.debug(f"Element '{element_name}' name not in list: {value}")
                            return False
                    else:
                        if element.get("name") != value:
                            logger.debug(f"Element '{element_name}' name doesn't match: {value}")
                            return False
                # For other fields, check if they exist and match the expected value
                else:
                    child_elements = element.xpath(f"./{key}")
                    if not child_elements:
                        logger.debug(f"Element '{element_name}' has no child element: {key}")
                        return False

                    if (
                        value is not None
                        and child_elements[0].text
                        and child_elements[0].text.strip() != str(value).strip()
                    ):
                        logger.debug(
                            f"Element '{element_name}' {key} value '{child_elements[0].text}' doesn't match '{value}'"
                        )
                        return False

            logger.debug(f"Element '{element_name}' matches all criteria")
            return True
        except Exception as e:
            logger.error(
                f"Error matching criteria for element '{element_name}': {str(e)}", exc_info=True
            )
            return False

    def get_all_objects(self, object_type):
        """
        Get all objects of the specified type.

        Args:
            object_type: Type of object to get (address, service, etc.)

        Returns:
            List of object dictionaries with all relevant attributes
        """
        logger.info(f"Getting all {object_type} objects")

        try:
            # Get all object elements of this type
            objects = self.select_objects(object_type)

            if not objects:
                logger.info(f"No {object_type} objects found")
                return []

            # Convert XML elements to dictionaries
            object_dicts = []
            for obj in objects:
                object_dict = self._object_to_dict(obj, object_type)
                object_dicts.append(object_dict)

            logger.info(f"Found {len(object_dicts)} {object_type} objects")
            return object_dicts

        except Exception as e:
            logger.error(f"Error getting objects: {str(e)}", exc_info=True)
            return []

    def _object_to_dict(self, object_element, object_type):
        """
        Convert an object XML element to a dictionary.

        Args:
            object_element: The object XML element
            object_type: Type of the object

        Returns:
            Dictionary containing the object attributes
        """
        try:
            # Base object attributes
            object_dict = {
                "name": object_element.get("name", "unnamed"),
                "type": object_type,
                "xml_element": object_element,  # Keep reference to original element
            }

            # Extract type-specific attributes
            if object_type == "address":
                for addr_type in ["ip-netmask", "ip-range", "fqdn"]:
                    addr_elem = object_element.find(f"./{addr_type}")
                    if addr_elem is not None and addr_elem.text:
                        object_dict["addr_type"] = addr_type
                        object_dict["value"] = addr_elem.text
                        break
            elif object_type == "service":
                for protocol in ["tcp", "udp"]:
                    port_elem = object_element.find(f"./{protocol}/port")
                    if port_elem is not None and port_elem.text:
                        object_dict["protocol"] = protocol
                        object_dict["port"] = port_elem.text
                        break

            # Description is common to many object types
            description_elem = object_element.find("./description")
            if description_elem is not None and description_elem.text:
                object_dict["description"] = description_elem.text

            # Tags are also common
            tags = object_element.findall("./tag/member")
            if tags:
                object_dict["tags"] = [t.text for t in tags if t.text]

            return object_dict

        except Exception as e:
            logger.error(f"Error converting object element to dict: {str(e)}", exc_info=True)
            # Return minimal dict with name to avoid breaking code that expects a dict
            return {"name": object_element.get("name", "unknown"), "type": object_type, "error": str(e)}


class ConfigUpdater:
    """
    Class for updating PAN-OS configurations with bulk operations.

    This class provides methods for bulk updating policies and objects with various operations.
    """

    def __init__(self, tree, device_type, context_type, version, **kwargs):
        """
        Initialize a ConfigUpdater instance.

        Args:
            tree: ElementTree containing the configuration
            device_type: Type of device ("firewall" or "panorama")
            context_type: Type of context (shared, device_group, vsys)
            version: PAN-OS version
            **kwargs: Additional context parameters (device_group, vsys, etc.)
        """
        self.tree = tree
        self.device_type = device_type
        self.context_type = context_type
        self.version = version
        self.context_kwargs = kwargs
        
        # Create a query object for selecting elements
        self.query = ConfigQuery(tree, device_type, context_type, version, **kwargs)

        logger.debug(
            f"Initialized ConfigUpdater: device_type={device_type}, context_type={context_type}, "
            f"version={version}, context_kwargs={kwargs}"
        )

    def add_object(self, object_type, object_data):
        """
        Add a new object to the configuration.

        Args:
            object_type: Type of object to add (address, service, etc.)
            object_data: Dictionary containing object data

        Returns:
            bool: True if the object was added, False if it already exists or an error occurred
        """
        logger.info(f"Adding {object_type} object: {object_data.get('name')}")

        try:
            # Get the base XPath for this object type and context
            base_xpath = get_object_xpath(
                object_type, self.device_type, self.context_type, self.version, **self.context_kwargs
            )

            logger.debug(f"Generated base XPath: {base_xpath}")

            # Check if the object already exists
            object_name = object_data.get("name")
            if not object_name:
                logger.error("Missing object name in object data")
                return False

            # Generate XPath for the specific object
            object_xpath = f"{base_xpath}[@name='{object_name}']"
            existing_objects = self.tree.xpath(object_xpath)

            if existing_objects:
                logger.warning(f"{object_type} object '{object_name}' already exists")
                return False

            # Find or create the parent element
            parent_xpath = "/".join(base_xpath.split("/")[:-1])
            parents = self.tree.xpath(parent_xpath)

            if not parents:
                logger.error(f"Parent element not found: {parent_xpath}")
                return False

            parent = parents[0]

            # Create the new object element
            new_object = etree.SubElement(parent, "entry")
            new_object.set("name", object_name)

            # Set object attributes based on type
            if object_type == "address":
                self._set_address_attributes(new_object, object_data)
            elif object_type == "service":
                self._set_service_attributes(new_object, object_data)
            # Add more object types as needed

            logger.info(f"Added {object_type} object: {object_name}")
            return True

        except Exception as e:
            logger.error(f"Error adding object: {str(e)}", exc_info=True)
            return False

    def _set_address_attributes(self, element, data):
        """Set attributes for an address object."""
        addr_type = data.get("addr_type", "ip-netmask")
        value = data.get("value")

        if not value:
            logger.warning(f"Missing value for address object: {data.get('name')}")
            return

        addr_elem = etree.SubElement(element, addr_type)
        addr_elem.text = value

        # Add description if provided
        description = data.get("description")
        if description:
            desc_elem = etree.SubElement(element, "description")
            desc_elem.text = description

        # Add tags if provided
        tags = data.get("tags")
        if tags:
            tags_elem = etree.SubElement(element, "tag")
            for tag in tags:
                tag_member = etree.SubElement(tags_elem, "member")
                tag_member.text = tag

    def _set_service_attributes(self, element, data):
        """Set attributes for a service object."""
        protocol = data.get("protocol", "tcp")
        port = data.get("port")

        if not port:
            logger.warning(f"Missing port for service object: {data.get('name')}")
            return

        protocol_elem = etree.SubElement(element, protocol)
        port_elem = etree.SubElement(protocol_elem, "port")
        port_elem.text = port

        # Add description if provided
        description = data.get("description")
        if description:
            desc_elem = etree.SubElement(element, "description")
            desc_elem.text = description

        # Add tags if provided
        tags = data.get("tags")
        if tags:
            tags_elem = etree.SubElement(element, "tag")
            for tag in tags:
                tag_member = etree.SubElement(tags_elem, "member")
                tag_member.text = tag

    def update_object(self, object_type, object_name, updates):
        """
        Update an existing object with the provided updates.

        Args:
            object_type: Type of object to update (address, service, etc.)
            object_name: Name of the object to update
            updates: Dictionary of updates to apply

        Returns:
            bool: True if updates were applied, False otherwise
        """
        logger.info(f"Updating {object_type} object: {object_name}")

        try:
            # Get the object element
            objects = self.query.select_objects(object_type, {"name": object_name})

            if not objects:
                logger.warning(f"{object_type} object '{object_name}' not found")
                return False

            object_elem = objects[0]

            # Apply updates based on object type
            if object_type == "address":
                return self._update_address_object(object_elem, updates)
            elif object_type == "service":
                return self._update_service_object(object_elem, updates)
            # Add more object types as needed

            logger.warning(f"Unsupported object type for updates: {object_type}")
            return False

        except Exception as e:
            logger.error(f"Error updating object: {str(e)}", exc_info=True)
            return False

    def _update_address_object(self, element, updates):
        """Update an address object with the provided updates."""
        modified = False

        # Update value if provided
        if "value" in updates:
            # Check if addr_type is also being updated
            addr_type = updates.get("addr_type", None)
            if not addr_type:
                # Try to find existing type
                for a_type in ["ip-netmask", "ip-range", "fqdn"]:
                    existing = element.find(f"./{a_type}")
                    if existing is not None:
                        addr_type = a_type
                        break

            if addr_type:
                # Remove all existing address type elements
                for a_type in ["ip-netmask", "ip-range", "fqdn"]:
                    for existing in element.findall(f"./{a_type}"):
                        element.remove(existing)

                # Add new address type element
                addr_elem = etree.SubElement(element, addr_type)
                addr_elem.text = updates["value"]
                modified = True
            else:
                logger.warning("Cannot update address value without knowing the address type")

        # Update description if provided
        if "description" in updates:
            desc_elem = element.find("./description")
            if desc_elem is not None:
                desc_elem.text = updates["description"]
            else:
                desc_elem = etree.SubElement(element, "description")
                desc_elem.text = updates["description"]
            modified = True

        # Update tags if provided
        if "tags" in updates:
            tags_elem = element.find("./tag")
            if tags_elem is not None:
                # Remove existing tags
                for member in tags_elem.findall("./member"):
                    tags_elem.remove(member)
            else:
                tags_elem = etree.SubElement(element, "tag")

            # Add new tags
            for tag in updates["tags"]:
                tag_member = etree.SubElement(tags_elem, "member")
                tag_member.text = tag
            modified = True

        return modified

    def _update_service_object(self, element, updates):
        """Update a service object with the provided updates."""
        modified = False

        # Update port if provided
        if "port" in updates:
            protocol = updates.get("protocol", None)
            if not protocol:
                # Try to find existing protocol
                for p_type in ["tcp", "udp"]:
                    existing = element.find(f"./{p_type}")
                    if existing is not None:
                        protocol = p_type
                        break

            if protocol:
                # Remove all existing protocol elements
                for p_type in ["tcp", "udp"]:
                    for existing in element.findall(f"./{p_type}"):
                        element.remove(existing)

                # Add new protocol element with port
                protocol_elem = etree.SubElement(element, protocol)
                port_elem = etree.SubElement(protocol_elem, "port")
                port_elem.text = updates["port"]
                modified = True
            else:
                logger.warning("Cannot update port value without knowing the protocol")

        # Update description if provided
        if "description" in updates:
            desc_elem = element.find("./description")
            if desc_elem is not None:
                desc_elem.text = updates["description"]
            else:
                desc_elem = etree.SubElement(element, "description")
                desc_elem.text = updates["description"]
            modified = True

        # Update tags if provided
        if "tags" in updates:
            tags_elem = element.find("./tag")
            if tags_elem is not None:
                # Remove existing tags
                for member in tags_elem.findall("./member"):
                    tags_elem.remove(member)
            else:
                tags_elem = etree.SubElement(element, "tag")

            # Add new tags
            for tag in updates["tags"]:
                tag_member = etree.SubElement(tags_elem, "member")
                tag_member.text = tag
            modified = True

        return modified

    def delete_object(self, object_type, object_name):
        """
        Delete an object from the configuration.

        Args:
            object_type: Type of object to delete (address, service, etc.)
            object_name: Name of the object to delete

        Returns:
            bool: True if the object was deleted, False otherwise
        """
        logger.info(f"Deleting {object_type} object: {object_name}")

        try:
            # Get the base XPath for this object type and context
            base_xpath = get_object_xpath(
                object_type, self.device_type, self.context_type, self.version, **self.context_kwargs
            )

            # Generate XPath for the specific object
            object_xpath = f"{base_xpath}[@name='{object_name}']"
            objects = self.tree.xpath(object_xpath)

            if not objects:
                logger.warning(f"{object_type} object '{object_name}' not found")
                return False

            # Remove the object
            for obj in objects:
                parent = obj.getparent()
                if parent is not None:
                    parent.remove(obj)
                    logger.info(f"Deleted {object_type} object: {object_name}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error deleting object: {str(e)}", exc_info=True)
            return False

    def bulk_update_policies(self, policy_type, criteria=None, operations=None, query_filter=None, existing_graph=None):
        """
        Update multiple policies matching criteria with specified operations.

        Args:
            policy_type: Type of policy to update (security_pre_rules, nat_rules, etc.)
            criteria: Dictionary of criteria to select policies
            operations: Dictionary of operations to perform on selected policies
            query_filter: Optional graph query filter to select policies
            existing_graph: Optional existing graph to reuse

        Returns:
            int: Number of policies updated
        """
        logger.info(f"Starting bulk update of {policy_type} policies")
        logger.info(f"Selection criteria: {criteria}")
        logger.info(f"Update operations: {operations}")
        if query_filter:
            logger.info(f"Using graph query filter: {query_filter}")

        if not criteria and not query_filter:
            logger.error("No selection criteria or query filter provided")
            raise ValueError("No selection criteria or query filter provided")
            
        # If we have a query filter but no results were found, still keep going with empty criteria
        # This will allow for the fallback XPath method to work

        if not operations:
            logger.error("No update operations provided")
            raise ValueError("No update operations provided")

        try:
            # For Panorama, we need to handle pre and post rules differently
            actual_policy_type = policy_type
            if self.device_type == "panorama" and policy_type in ["security_rules", "nat_rules"]:
                # Convert generic types to pre-rulebase types for Panorama
                if policy_type == "security_rules":
                    actual_policy_type = "security_pre_rules"
                elif policy_type == "nat_rules":
                    actual_policy_type = "nat_pre_rules"
                logger.info(f"Converted policy_type from {policy_type} to {actual_policy_type} for Panorama")
            
            # If we have a graph query filter, process it first to get matching policy names
            if query_filter:
                matching_policy_names = self._get_policies_from_query(
                    query_filter,
                    policy_type=actual_policy_type,
                    context_type=self.context_type,
                    device_group=self.context_kwargs.get("device_group"),
                    existing_graph=existing_graph
                )
                
                if matching_policy_names:
                    # If we already have criteria, extend it with the names from the query
                    if criteria:
                        if "name" in criteria:
                            if isinstance(criteria["name"], list):
                                criteria["name"].extend(matching_policy_names)
                            else:
                                criteria["name"] = [criteria["name"]] + matching_policy_names
                        else:
                            criteria["name"] = matching_policy_names
                    else:
                        # If we don't have criteria yet, create one with the names
                        criteria = {"name": matching_policy_names}
                    
                    logger.info(f"Updated selection criteria with query results: {criteria}")
                else:
                    logger.warning(f"Query filter did not match any policies. Creating empty criteria to continue.")
                    # If no policies matched, create an empty criteria that won't match anything
                    # This will prevent errors later when trying to use a None criteria
                    if not criteria:
                        criteria = {"name": []}
                        
                    # Let the process continue so the XPath fallback method or direct selection can work

            # Now use the regular policy selection with the updated criteria and correct policy type
            matching_policies = self.query.select_policies(actual_policy_type, criteria)
            
            # For Panorama, try post-rulebase as well if no matches found in pre-rulebase
            if self.device_type == "panorama" and not matching_policies:
                if actual_policy_type == "security_pre_rules":
                    post_type = "security_post_rules"
                elif actual_policy_type == "nat_pre_rules":
                    post_type = "nat_post_rules"
                else:
                    post_type = None
                
                if post_type:
                    logger.info(f"No matches in pre-rulebase, trying {post_type}")
                    matching_policies = self.query.select_policies(post_type, criteria)
            
            # Debug: print the names of available policies
            available_policies = self.query.select_policies(actual_policy_type)
            available_names = [p.get('name', 'unknown') for p in available_policies]
            logger.info(f"Available policies in context: {available_names}")
            
            # If still no matching policies but we have device group context,
            # try directly querying the XML as a last resort
            if not matching_policies and self.device_type == "panorama" and self.context_type == "device_group":
                device_group = self.context_kwargs.get("device_group")
                if device_group and criteria and "name" in criteria:
                    # Use direct XPath to find policies with matching names
                    logger.info(f"Trying direct XML lookup for policies in device group {device_group}")
                    policy_names = criteria["name"] if isinstance(criteria["name"], list) else [criteria["name"]]
                    
                    direct_matches = []
                    # Check both pre and post rulebase
                    pre_xpath = f"/config/devices/entry/device-group/entry[@name='{device_group}']/pre-rulebase/security/rules/entry"
                    post_xpath = f"/config/devices/entry/device-group/entry[@name='{device_group}']/post-rulebase/security/rules/entry"
                    
                    for policy in self.tree.xpath(pre_xpath):
                        name = policy.get("name")
                        if name in policy_names:
                            logger.info(f"Found policy '{name}' in pre-rulebase via direct XML lookup")
                            direct_matches.append(policy)
                    
                    for policy in self.tree.xpath(post_xpath):
                        name = policy.get("name")
                        if name in policy_names:
                            logger.info(f"Found policy '{name}' in post-rulebase via direct XML lookup")
                            direct_matches.append(policy)
                    
                    if direct_matches:
                        logger.info(f"Found {len(direct_matches)} policies via direct XML lookup")
                        matching_policies = direct_matches
            
            if not matching_policies:
                logger.warning("No policies found matching the criteria")
                return 0

            updated_count = 0
            for policy in matching_policies:
                if self._apply_operations(policy, operations):
                    updated_count += 1

            logger.info(f"Updated {updated_count} policies")
            return updated_count

        except Exception as e:
            logger.error(f"Error in bulk update: {str(e)}", exc_info=True)
            raise

    def _get_policies_from_query(self, query_filter, policy_type=None, context_type=None, device_group=None, existing_graph=None):
        """
        Get policy names from a graph query filter.

        Args:
            query_filter: The graph query filter to execute
            policy_type: Type of policy (security_pre_rules, nat_rules, etc.)
            context_type: The type of context (shared, device_group, vsys)
            device_group: The device group name (for device_group context)
            existing_graph: Optional existing graph to reuse

        Returns:
            List of policy names matching the query
        """
        try:
            # Use existing graph if provided, otherwise create a new one
            if existing_graph:
                logger.debug("Using existing graph for query")
                graph = existing_graph
            else:
                # Create graph with device context
                logger.debug(f"Creating graph with device_type={self.device_type}, context_type={self.context_type}, context_kwargs={self.context_kwargs}")
                graph = ConfigGraph(self.device_type, self.context_type, **self.context_kwargs)
                graph.build_from_xml(self.tree)
            
            # Determine context values to use, prioritizing passed parameters
            actual_context_type = context_type if context_type else self.context_type
            actual_device_group = device_group if device_group else self.context_kwargs.get("device_group")
            
            # Log all security rule nodes in the graph for debugging
            security_rule_nodes = []
            for node_id, attrs in graph.graph.nodes(data=True):
                if attrs.get("type") == "security-rule":
                    name = attrs.get("name", "unknown")
                    dg = attrs.get("device_group", "none")
                    action = attrs.get("action", "unknown")
                    security_rule_nodes.append(f"{name} (device_group: {dg}, action: {action})")
            
            logger.debug(f"Security rule nodes in graph: {security_rule_nodes}")

            # Prepare a query that returns policy names and device group if available
            # For device-group specific contexts, modify the query to filter by device group
            if self.device_type == "panorama" and actual_context_type == "device_group":
                if actual_device_group:
                    # Use more specific query to filter by device group as well
                    if "RETURN" not in query_filter.upper():
                        device_group_condition = f" AND r.device_group == '{actual_device_group}'"
                        if "WHERE" in query_filter:
                            # Add device group condition to existing WHERE clause
                            query_text = query_filter.replace("WHERE", f"WHERE r.device_group == '{actual_device_group}' AND ")
                        else:
                            # Add WHERE clause with device group condition
                            query_text = f"{query_filter} WHERE r.device_group == '{actual_device_group}'"
                        query_text = f"{query_text} RETURN r.name"
                    else:
                        # Preserve existing RETURN clause, but add device group condition
                        if "WHERE" in query_filter:
                            query_text = query_filter.replace("WHERE", f"WHERE r.device_group == '{actual_device_group}' AND ")
                        else:
                            # Insert WHERE clause before RETURN
                            parts = query_filter.split("RETURN")
                            query_text = f"{parts[0]} WHERE r.device_group == '{actual_device_group}' RETURN{parts[1]}"
                    
                    logger.info(f"Modified query for device group {actual_device_group}: {query_text}")
                else:
                    # No device group specified, use original query
                    if "RETURN" not in query_filter.upper():
                        query_text = f"{query_filter} RETURN r.name"
                    else:
                        query_text = query_filter
            else:
                # Not a device group context, use original query
                if "RETURN" not in query_filter.upper():
                    query_text = f"{query_filter} RETURN r.name"
                else:
                    query_text = query_filter

            # Execute the query
            query = Query(query_text)
            executor = QueryExecutor(graph)
            results = executor.execute(query)

            # Extract policy names from results
            policy_names = []
            for row in results:
                if "r.name" in row:
                    policy_names.append(row["r.name"])
                elif len(row) == 1:  # If only one column, use its value
                    policy_names.append(list(row.values())[0])

            logger.info(f"Query matched {len(policy_names)} policies")
            
            # Now filter to ensure we only have policies that match both the query and the device group
            if self.device_type == "panorama" and actual_context_type == "device_group":
                if actual_device_group:
                    # Get all policies from the specific device group context
                    dg_policies = []
                    dg_xpath = f"/config/devices/entry/device-group/entry[@name='{actual_device_group}']/pre-rulebase/security/rules/entry"
                    for rule in self.tree.xpath(dg_xpath):
                        name = rule.get("name")
                        if name:
                            dg_policies.append(name)
                    
                    # Now filter the query results to only include policies from this device group
                    filtered_names = [name for name in policy_names if name in dg_policies]
                    if len(filtered_names) != len(policy_names):
                        logger.info(f"Filtered from {len(policy_names)} to {len(filtered_names)} policies in device group {actual_device_group}")
                    return filtered_names
                    
            return policy_names

        except Exception as e:
            logger.warning(f"Graph query failed: {e}. Falling back to regular policy selection.")
            
            # For device-group specific contexts, try to get policies directly from XPath
            if self.device_type == "panorama" and actual_context_type == "device_group":
                if actual_device_group:
                    # Try to understand the query intent - are we looking for allow rules?
                    action_match = None
                    if "r.action" in query_filter and "allow" in query_filter:
                        action_match = "allow"
                    elif "r.action" in query_filter and "deny" in query_filter:
                        action_match = "deny"
                    elif "r.action" in query_filter and "drop" in query_filter:
                        action_match = "drop"
                    
                    # Get all policies from the specific device group context
                    dg_policies = []
                    
                    # Check both pre and post rulebase
                    pre_xpath = f"/config/devices/entry/device-group/entry[@name='{actual_device_group}']/pre-rulebase/security/rules/entry"
                    post_xpath = f"/config/devices/entry/device-group/entry[@name='{actual_device_group}']/post-rulebase/security/rules/entry"
                    
                    # If we're filtering by action, include that in XPath
                    if action_match:
                        pre_xpath = f"{pre_xpath}[action='{action_match}']"
                        post_xpath = f"{post_xpath}[action='{action_match}']"
                    
                    # Get rules from pre-rulebase
                    for rule in self.tree.xpath(pre_xpath):
                        name = rule.get("name")
                        if name:
                            dg_policies.append(name)
                    
                    # Get rules from post-rulebase
                    for rule in self.tree.xpath(post_xpath):
                        name = rule.get("name")
                        if name:
                            dg_policies.append(name)
                    
                    logger.info(f"Found {len(dg_policies)} policies in device group {actual_device_group} using XPath fallback")
                    return dg_policies
            
            # Return empty list as a last resort
            return []

    def _apply_operations(self, policy, operations):
        """
        Apply operations to a policy.

        Args:
            policy: The policy XML element to update
            operations: Dictionary of operations to perform

        Returns:
            bool: True if any modifications were made, False otherwise
        """
        policy_name = policy.get("name", "unknown")
        logger.debug(f"Applying operations to policy: {policy_name}")

        modified = False
        for op, params in operations.items():
            if op == "log-setting":
                # Set log setting
                log_setting_elem = policy.find("./log-setting")
                if log_setting_elem is not None:
                    old_setting = log_setting_elem.text
                    log_setting_elem.text = params
                    logger.info(
                        f"Updated log-setting of policy '{policy_name}' from '{old_setting}' to '{params}'"
                    )
                else:
                    log_setting_elem = etree.SubElement(policy, "log-setting")
                    log_setting_elem.text = params
                    logger.info(f"Added log-setting '{params}' to policy '{policy_name}'")
                modified = True
            elif op == "disable":
                # Disable the policy
                disabled_elem = policy.find("./disabled")
                if disabled_elem is not None:
                    disabled_elem.text = "yes"
                else:
                    disabled_elem = etree.SubElement(policy, "disabled")
                    disabled_elem.text = "yes"
                logger.info(f"Disabled policy: {policy_name}")
                modified = True
            elif op == "enable":
                # Enable the policy
                disabled_elem = policy.find("./disabled")
                if disabled_elem is not None:
                    policy.remove(disabled_elem)
                    logger.info(f"Enabled policy: {policy_name}")
                    modified = True
            elif op == "set-log":
                # Set log start/end values
                for log_type, value in params.items():
                    if log_type not in ["log-start", "log-end"]:
                        logger.warning(f"Invalid log type: {log_type}")
                        continue

                    log_elem = policy.find(f"./{log_type}")
                    if log_elem is not None:
                        old_value = log_elem.text
                        log_elem.text = value
                        logger.info(
                            f"Updated {log_type} of policy '{policy_name}' from '{old_value}' to '{value}'"
                        )
                    else:
                        log_elem = etree.SubElement(policy, log_type)
                        log_elem.text = value
                        logger.info(f"Added {log_type} '{value}' to policy '{policy_name}'")
                    modified = True
            elif op == "add-profile":
                # Add profile settings
                modified |= self._add_profile(policy, params)
            elif op == "add-tag":
                # Add a tag
                modified |= self._add_tag(policy, params)
            elif op == "add-zone":
                # Add a zone
                modified |= self._add_zone(policy, params)
            elif op == "change-action":
                # Change the action
                modified |= self._change_action(policy, params)
            elif op == "add-object":
                # Add an object to source/destination/service
                modified |= self._add_object(policy, params)
            elif op == "remove-object":
                # Remove an object from source/destination/service
                modified |= self._remove_object(policy, params)
            elif op == "update-description":
                # Update the description
                modified |= self._update_description(policy, params)
            else:
                logger.warning(f"Unsupported operation: {op}")

        return modified

    def _add_profile(self, element, params):
        """
        Add a profile to a policy element.

        Args:
            element: XML element to update
            params: Parameters for the operation

        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get("name", "unknown")
        profile_type = params.get("type")
        profile_name = params.get("name")

        if not profile_type or not profile_name:
            logger.warning(
                f"Missing profile type or name in add-profile operation for policy '{element_name}'"
            )
            return False

        logger.debug(f"Adding profile '{profile_name}' of type '{profile_type}' to policy '{element_name}'")

        try:
            # Check if profile-setting element exists
            profile_setting = element.find("./profile-setting")
            if profile_setting is None:
                logger.debug(f"Creating new profile-setting element for '{element_name}'")
                profile_setting = etree.SubElement(element, "profile-setting")

            # Handle different types of profiles
            if profile_type == "group":
                # Add to group element
                group_elem = profile_setting.find("./group")
                if group_elem is None:
                    group_elem = etree.SubElement(profile_setting, "group")

                # Check if profile already exists
                members = group_elem.xpath("./member")
                member_values = [m.text for m in members if m.text]

                if profile_name not in member_values:
                    member = etree.SubElement(group_elem, "member")
                    member.text = profile_name
                    logger.info(f"Added group profile '{profile_name}' to policy '{element_name}'")
                    return True
                else:
                    logger.debug(f"Group profile '{profile_name}' already exists in policy '{element_name}'")
                    return False
            elif profile_type == "log-forwarding":
                # Set log-forwarding profile
                log_forwarding = profile_setting.find("./log-forwarding")
                if log_forwarding is not None:
                    old_profile = log_forwarding.text
                    log_forwarding.text = profile_name
                    logger.info(
                        f"Updated log-forwarding profile of policy '{element_name}' from '{old_profile}' to '{profile_name}'"
                    )
                    return True
                else:
                    log_forwarding = etree.SubElement(profile_setting, "log-forwarding")
                    log_forwarding.text = profile_name
                    logger.info(f"Added log-forwarding profile '{profile_name}' to policy '{element_name}'")
                    return True
            elif profile_type in ["virus", "spyware", "vulnerability", "url-filtering", "file-blocking", "wildfire-analysis"]:
                # Add individual security profiles
                profile_elem = profile_setting.find(f"./{profile_type}")
                if profile_elem is None:
                    profile_elem = etree.SubElement(profile_setting, profile_type)

                # Check if this profile is already set
                if profile_elem.text == profile_name:
                    logger.debug(f"Profile '{profile_name}' already set for {profile_type} in policy '{element_name}'")
                    return False

                # Update the profile
                old_profile = profile_elem.text
                profile_elem.text = profile_name
                if old_profile:
                    logger.info(
                        f"Updated {profile_type} profile of policy '{element_name}' from '{old_profile}' to '{profile_name}'"
                    )
                else:
                    logger.info(f"Added {profile_type} profile '{profile_name}' to policy '{element_name}'")
                return True
            elif profile_type in ["profiles"]:
                # Handle profiles container for individual security profiles
                profiles_elem = profile_setting.find("./profiles")
                if profiles_elem is None:
                    profiles_elem = etree.SubElement(profile_setting, "profiles")

                # The 'name' parameter contains a dict of profile settings
                for profile_key, profile_value in params.get("profiles", {}).items():
                    profile_elem = profiles_elem.find(f"./{profile_key}")
                    if profile_elem is None:
                        profile_elem = etree.SubElement(profiles_elem, profile_key)

                members = profile_elem.xpath("./member")
                member_values = [m.text for m in members if m.text]

                if profile_name not in member_values:
                    member = etree.SubElement(profile_elem, "member")
                    member.text = profile_name
                    logger.info(f"Added {profile_type} profile '{profile_name}'")
                    return True
                else:
                    logger.debug(f"Profile '{profile_name}' already exists in {profile_type}")
                    return False
            else:
                logger.warning(f"Unsupported profile type: {profile_type}")
                return False

        except Exception as e:
            logger.error(
                f"Error adding profile to element '{element_name}': {str(e)}", exc_info=True
            )
            return False

    def _add_tag(self, element, params):
        """
        Add a tag to an element.

        Args:
            element: XML element to update
            params: Parameters for the operation

        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get("name", "unknown")
        tag_name = params.get("name")

        if not tag_name:
            logger.warning(f"Missing tag name in add-tag operation for element '{element_name}'")
            return False

        logger.debug(f"Adding tag '{tag_name}' to element '{element_name}'")

        try:
            # Check if tag element exists
            tags = element.find("./tag")
            if tags is None:
                logger.debug(f"Creating new tag element for '{element_name}'")
                tags = etree.SubElement(element, "tag")

            # Check if this tag is already present
            members = tags.xpath("./member")
            member_values = [m.text for m in members if m.text]

            if tag_name not in member_values:
                member = etree.SubElement(tags, "member")
                member.text = tag_name
                logger.info(f"Added tag '{tag_name}' to element '{element_name}'")
                return True
            else:
                logger.debug(f"Tag '{tag_name}' already exists for element '{element_name}'")
                return False

        except Exception as e:
            logger.error(f"Error adding tag to element '{element_name}': {str(e)}", exc_info=True)
            return False

    def _add_zone(self, element, params):
        """
        Add a zone to a policy element.

        Args:
            element: XML element to update
            params: Parameters for the operation

        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get("name", "unknown")
        zone_name = params.get("name")
        location = params.get("location", "to")  # Default to 'to' if not specified

        if not zone_name:
            logger.warning(f"Missing zone name in add-zone operation for policy '{element_name}'")
            return False

        logger.debug(
            f"Adding zone '{zone_name}' to '{location}' section of policy '{element_name}'"
        )

        try:
            # Ensure location is valid ('from', 'to', or 'both')
            locations = []
            if location == "both":
                locations = ["from", "to"]
            else:
                locations = [location]

            modified = False

            for loc in locations:
                # Check if the location element exists
                loc_elem = element.find(f"./{loc}")
                if loc_elem is None:
                    logger.debug(f"Creating new {loc} element for policy '{element_name}'")
                    loc_elem = etree.SubElement(element, loc)

                # Check if this zone is already present
                members = loc_elem.xpath("./member")
                member_values = [m.text for m in members if m.text]

                if zone_name not in member_values:
                    member = etree.SubElement(loc_elem, "member")
                    member.text = zone_name
                    logger.info(
                        f"Added zone '{zone_name}' to {loc} section of policy '{element_name}'"
                    )
                    modified = True
                else:
                    logger.debug(
                        f"Zone '{zone_name}' already exists in {loc} section of policy '{element_name}'"
                    )

            return modified

        except Exception as e:
            logger.error(f"Error adding zone to policy '{element_name}': {str(e)}", exc_info=True)
            return False

    def _change_action(self, element, params):
        """
        Change the action of a policy.

        Args:
            element: XML element to update
            params: Parameters for the operation

        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get("name", "unknown")
        action = params.get("action")

        if not action:
            logger.warning(f"Missing action in change-action operation for policy '{element_name}'")
            return False

        logger.debug(f"Changing action of policy '{element_name}' to '{action}'")

        try:
            # Find the action element
            action_elem = element.find("./action")

            if action_elem is not None:
                old_action = action_elem.text
                if old_action != action:
                    action_elem.text = action
                    logger.info(
                        f"Changed action of policy '{element_name}' from '{old_action}' to '{action}'"
                    )
                    return True
                else:
                    logger.debug(f"Policy '{element_name}' already has action '{action}'")
                    return False
            else:
                # Create new action element
                action_elem = etree.SubElement(element, "action")
                action_elem.text = action
                logger.info(f"Added action '{action}' to policy '{element_name}'")
                return True

        except Exception as e:
            logger.error(
                f"Error changing action of policy '{element_name}': {str(e)}", exc_info=True
            )
            return False

    def _add_object(self, element, params):
        """
        Add an object to a policy's source, destination, or service field.

        Args:
            element: XML element to update
            params: Parameters for the operation

        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get("name", "unknown")
        object_name = params.get("name")
        field = params.get("field")  # 'source', 'destination', 'service', 'application'

        if not object_name or not field:
            logger.warning(
                f"Missing name or field in add-object operation for element '{element_name}'"
            )
            return False

        logger.debug(
            f"Adding object '{object_name}' to {field} section of element '{element_name}'"
        )

        try:
            # Check if the field element exists
            field_elem = element.find(f"./{field}")
            if field_elem is None:
                logger.debug(f"Creating new {field} element for '{element_name}'")
                field_elem = etree.SubElement(element, field)

            # Check if this object is already present
            members = field_elem.xpath("./member")
            member_values = [m.text for m in members if m.text]

            if object_name not in member_values:
                member = etree.SubElement(field_elem, "member")
                member.text = object_name
                logger.info(
                    f"Added object '{object_name}' to {field} section of element '{element_name}'"
                )
                return True
            else:
                logger.debug(
                    f"Object '{object_name}' already exists in {field} section of element '{element_name}'"
                )
                return False

        except Exception as e:
            logger.error(
                f"Error adding object to element '{element_name}': {str(e)}", exc_info=True
            )
            return False

    def _remove_object(self, element, params):
        """
        Remove an object from a policy's source, destination, or service field.

        Args:
            element: XML element to update
            params: Parameters for the operation

        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get("name", "unknown")
        object_name = params.get("name")
        field = params.get("field")  # 'source', 'destination', 'service', 'application'

        if not object_name or not field:
            logger.warning(
                f"Missing name or field in remove-object operation for element '{element_name}'"
            )
            return False

        logger.debug(
            f"Removing object '{object_name}' from {field} section of element '{element_name}'"
        )

        try:
            # Find the field element
            field_elem = element.find(f"./{field}")
            if field_elem is None:
                logger.warning(f"Field {field} not found in element '{element_name}'")
                return False

            # Find the member element to remove
            for member in field_elem.xpath("./member"):
                if member.text == object_name:
                    field_elem.remove(member)
                    logger.info(
                        f"Removed object '{object_name}' from {field} section of element '{element_name}'"
                    )
                    return True

            logger.debug(
                f"Object '{object_name}' not found in {field} section of element '{element_name}'"
            )
            return False

        except Exception as e:
            logger.error(
                f"Error removing object from element '{element_name}': {str(e)}", exc_info=True
            )
            return False

    def _update_description(self, element, params):
        """
        Update the description of an element.

        Args:
            element: XML element to update
            params: Parameters for the operation

        Returns:
            bool: True if modifications were made, False otherwise
        """
        element_name = element.get("name", "unknown")
        description = params.get("text")
        mode = params.get("mode", "replace")  # 'replace', 'append', or 'prepend'

        if description is None:  # Allow empty string as a valid value to clear description
            logger.warning(
                f"Missing description text in update-description operation for element '{element_name}'"
            )
            return False

        logger.debug(f"Updating description of element '{element_name}'")

        try:
            # Find the description element
            desc_elem = element.find("./description")
            
            # If the element doesn't exist, create it unless description is empty
            if desc_elem is None:
                if description:
                    desc_elem = etree.SubElement(element, "description")
                    desc_elem.text = description
                    logger.info(f"Added description to element '{element_name}'")
                    return True
                else:
                    # Nothing to do if there's no description element and we're setting an empty description
                    return False
            else:
                # Element exists, update based on mode
                old_desc = desc_elem.text or ""
                
                if mode == "replace":
                    # Simply replace the text
                    if old_desc != description:
                        desc_elem.text = description
                        logger.info(f"Updated description of element '{element_name}'")
                        return True
                elif mode == "append":
                    # Append the new text
                    new_desc = old_desc + description
                    if old_desc != new_desc:
                        desc_elem.text = new_desc
                        logger.info(f"Appended to description of element '{element_name}'")
                        return True
                elif mode == "prepend":
                    # Prepend the new text
                    new_desc = description + old_desc
                    if old_desc != new_desc:
                        desc_elem.text = new_desc
                        logger.info(f"Prepended to description of element '{element_name}'")
                        return True
                else:
                    logger.warning(f"Unsupported description update mode: {mode}")
                    return False
                
                logger.debug(f"Description of element '{element_name}' already matches desired value")
                return False

        except Exception as e:
            logger.error(
                f"Error updating description of element '{element_name}': {str(e)}", exc_info=True
            )
            return False