from lxml import etree
import logging
from .xpath_resolver import get_object_xpath, get_policy_xpath
from .config_loader import xpath_search


class ConfigQuery:
    def __init__(self, tree, device_type, context_type, version, **kwargs):
        self.tree = tree
        self.device_type = device_type
        self.context_type = context_type
        self.version = version
        self.context_kwargs = kwargs
        
    def select_policies(self, policy_type, criteria=None):
        """Select policies matching the criteria"""
        # Get base XPath for the policy type
        base_xpath = get_policy_xpath(policy_type, self.device_type, self.context_type, 
                                      self.version, **self.context_kwargs)
        
        # Start with all policies of this type
        results = xpath_search(self.tree, base_xpath)
        
        # Apply filters if criteria is provided
        if criteria:
            filtered_results = []
            for policy in results:
                if self._matches_criteria(policy, criteria):
                    filtered_results.append(policy)
            return filtered_results
        
        return results
    
    def _matches_criteria(self, element, criteria):
        """Check if an element matches the criteria"""
        for key, value in criteria.items():
            # Handle XPath expressions in criteria
            if key.startswith('xpath:'):
                xpath = key[6:]  # Remove 'xpath:' prefix
                matches = element.xpath(xpath)
                if not matches:
                    return False
                continue
                
            # Handle standard field matching
            if key == 'name':
                if element.get('name') != value:
                    return False
            elif key == 'has-tag':
                tag_elements = element.xpath('./tag/member')
                tag_values = [tag.text for tag in tag_elements if tag.text]
                if value not in tag_values:
                    return False
            # Add more criteria types as needed
                
        return True

class ConfigUpdater:
    def __init__(self, tree, device_type, context_type, version, **kwargs):
        self.tree = tree
        self.device_type = device_type
        self.context_type = context_type
        self.version = version
        self.context_kwargs = kwargs
        self.query = ConfigQuery(tree, device_type, context_type, version, **kwargs)
        
    def bulk_update_policies(self, policy_type, criteria, update_operations):
        """Update all policies matching criteria with specified operations"""
        # Select matching policies
        policies = self.query.select_policies(policy_type, criteria)
        
        updated_count = 0
        for policy in policies:
            if self._apply_updates(policy, update_operations):
                updated_count += 1
                
        return updated_count
    
    def _apply_updates(self, element, operations):
        """Apply update operations to an element"""
        modified = False
        
        for operation, params in operations.items():
            if operation == 'add-profile':
                # Add log forwarding profile or security profile
                profile_type = params.get('type')
                profile_name = params.get('name')
                
                # Check if profile-setting exists
                profile_setting = element.find('./profile-setting')
                if profile_setting is None:
                    profile_setting = etree.SubElement(element, 'profile-setting')
                
                if profile_type == 'log-forwarding':
                    # Set log-forwarding profile
                    log_setting = etree.SubElement(profile_setting, 'log-setting')
                    log_setting.text = profile_name
                    modified = True
                elif profile_type in ['group', 'virus', 'spyware', 'vulnerability', 'url-filtering']:
                    # Add security profile or group
                    profile_elem = profile_setting.find(f'./{profile_type}')
                    if profile_elem is None:
                        profile_elem = etree.SubElement(profile_setting, profile_type)
                    
                    # Add as member if it's not already there
                    members = profile_elem.xpath('./member')
                    member_values = [m.text for m in members if m.text]
                    
                    if profile_name not in member_values:
                        member = etree.SubElement(profile_elem, 'member')
                        member.text = profile_name
                        modified = True
            
            elif operation == 'add-tag':
                # Add tag to the element
                tag_name = params.get('name')
                
                # Check if tag element exists
                tags = element.find('./tag')
                if tags is None:
                    tags = etree.SubElement(element, 'tag')
                
                # Check if this tag is already present
                members = tags.xpath('./member')
                member_values = [m.text for m in members if m.text]
                
                if tag_name not in member_values:
                    member = etree.SubElement(tags, 'member')
                    member.text = tag_name
                    modified = True
            
            # Add more operations as needed
                
        return modified