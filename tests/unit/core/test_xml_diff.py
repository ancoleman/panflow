"""
Tests for the XML diff functionality.
"""

import pytest
from lxml import etree

from panflow.core import XmlDiff, DiffItem, DiffType, XmlNode, XmlBuilder


class TestXmlDiff:
    """Tests for the XmlDiff class."""
    
    def test_compare_identical(self):
        """Test comparing identical elements."""
        # Create two identical elements
        xml_str = '<root><child>text</child></root>'
        source = etree.fromstring(xml_str)
        target = etree.fromstring(xml_str)
        
        # Compare them
        diffs = XmlDiff.compare(source, target)
        
        # Should have no diffs
        assert len(diffs) == 0
        
    def test_compare_with_xmlnode(self):
        """Test comparing XmlNode objects."""
        # Create two identical nodes
        source = XmlNode.create('root')
        source.add_child('child', text='text')
        
        target = XmlNode.create('root')
        target.add_child('child', text='text')
        
        # Compare them
        diffs = XmlDiff.compare(source, target)
        
        # Should have no diffs
        assert len(diffs) == 0
        
    def test_added_element(self):
        """Test detecting an added element."""
        # Create source and target with an extra element in target
        source = XmlNode.create('root')
        source.add_child('child1', text='text1')
        
        target = XmlNode.create('root')
        target.add_child('child1', text='text1')
        target.add_child('child2', text='text2')
        
        # Compare them
        diffs = XmlDiff.compare(source, target)
        
        # Should have one diff
        assert len(diffs) == 1
        assert diffs[0].type == DiffType.ADDED
        assert '/child2[1]' in diffs[0].path
        assert diffs[0].source_value is None
        assert diffs[0].target_value is not None
        
    def test_removed_element(self):
        """Test detecting a removed element."""
        # Create source and target with an extra element in source
        source = XmlNode.create('root')
        source.add_child('child1', text='text1')
        source.add_child('child2', text='text2')
        
        target = XmlNode.create('root')
        target.add_child('child1', text='text1')
        
        # Compare them
        diffs = XmlDiff.compare(source, target)
        
        # Should have one diff
        assert len(diffs) == 1
        assert diffs[0].type == DiffType.REMOVED
        assert 'child2' in diffs[0].path
        assert diffs[0].source_value is not None
        assert diffs[0].target_value is None
        
    def test_changed_text(self):
        """Test detecting changed text."""
        # Create source and target with different text
        source = XmlNode.create('root')
        source.add_child('child', text='old text')
        
        target = XmlNode.create('root')
        target.add_child('child', text='new text')
        
        # Compare them
        diffs = XmlDiff.compare(source, target)
        
        # Should have one diff for the text change
        assert len(diffs) == 1
        assert diffs[0].type == DiffType.CHANGED
        assert '/child[1]/text()' in diffs[0].path
        assert diffs[0].source_value == 'old text'
        assert diffs[0].target_value == 'new text'
        
    def test_changed_attribute(self):
        """Test detecting changed attributes."""
        # Create source and target with different attributes
        source = XmlNode.create('root')
        source.add_child('child', {'attr': 'old value'})
        
        target = XmlNode.create('root')
        target.add_child('child', {'attr': 'new value'})
        
        # Compare them
        diffs = XmlDiff.compare(source, target)
        
        # Should have one diff for the attribute change
        assert len(diffs) == 1
        assert diffs[0].type == DiffType.CHANGED
        assert '/child[1]/@attr' in diffs[0].path
        assert diffs[0].source_value == 'old value'
        assert diffs[0].target_value == 'new value'
        
    def test_added_attribute(self):
        """Test detecting an added attribute."""
        # Create source and target with an extra attribute in target
        source = XmlNode.create('root')
        source.add_child('child')
        
        target = XmlNode.create('root')
        target.add_child('child', {'attr': 'value'})
        
        # Compare them
        diffs = XmlDiff.compare(source, target)
        
        # Should have one diff for the added attribute
        assert len(diffs) == 1
        assert diffs[0].type == DiffType.ADDED
        assert '/child[1]/@attr' in diffs[0].path
        assert diffs[0].source_value is None
        assert diffs[0].target_value == 'value'
        
    def test_removed_attribute(self):
        """Test detecting a removed attribute."""
        # Create source and target with an extra attribute in source
        source = XmlNode.create('root')
        source.add_child('child', {'attr': 'value'})
        
        target = XmlNode.create('root')
        target.add_child('child')
        
        # Compare them
        diffs = XmlDiff.compare(source, target)
        
        # Should have one diff for the removed attribute
        assert len(diffs) == 1
        assert diffs[0].type == DiffType.REMOVED
        assert '/child[1]/@attr' in diffs[0].path
        assert diffs[0].source_value == 'value'
        assert diffs[0].target_value is None
        
    def test_ignore_attributes(self):
        """Test ignoring specific attributes."""
        # Create source and target with different attributes
        source = XmlNode.create('root')
        source.add_child('child', {'ignore_me': 'old', 'track_me': 'old'})
        
        target = XmlNode.create('root')
        target.add_child('child', {'ignore_me': 'new', 'track_me': 'new'})
        
        # Compare them with ignore_attributes
        diffs = XmlDiff.compare(source, target, ignore_attributes=['ignore_me'])
        
        # Should have one diff for the tracked attribute only
        assert len(diffs) == 1
        assert '/child[1]/@track_me' in diffs[0].path
        
    def test_ignore_elements(self):
        """Test ignoring specific elements."""
        # Create source and target with different child elements
        source = XmlNode.create('root')
        source.add_child('ignore_me', text='old')
        source.add_child('track_me', text='old')
        
        target = XmlNode.create('root')
        target.add_child('ignore_me', text='new')
        target.add_child('track_me', text='new')
        
        # Compare them with ignore_elements
        diffs = XmlDiff.compare(source, target, ignore_elements=['ignore_me'])
        
        # Should have one diff for the tracked element only
        assert len(diffs) == 1
        assert '/track_me' in diffs[0].path
        
    def test_complex_comparison(self):
        """Test comparing complex structures."""
        # Create a more complex source
        source_builder = XmlBuilder('config')
        source_builder.into('devices')
        source_builder.into('entry').with_attribute('name', 'device1')
        source_builder.into('address').add('entry', {'name': 'address1'}, 'addr1')
        source_builder.up().up()
        source_builder.root_up()
        
        # Create a target with differences
        target_builder = XmlBuilder('config')
        target_builder.into('devices')
        target_builder.into('entry').with_attribute('name', 'device1')
        target_builder.into('address')
        target_builder.add('entry', {'name': 'address1'}, 'addr1-modified')  # Changed text
        target_builder.add('entry', {'name': 'address2'}, 'addr2')  # Added entry
        target_builder.up().up()
        target_builder.root_up()
        
        # Compare them
        source = source_builder.build()
        target = target_builder.build()
        diffs = XmlDiff.compare(source, target)
        
        # Should have two diffs:
        # 1. Changed text in address1
        # 2. Added address2
        assert len(diffs) == 2
        
        # Check for specific diffs
        changed_text = False
        added_entry = False
        
        for diff in diffs:
            if diff.type == DiffType.CHANGED and 'text()' in diff.path:
                changed_text = True
                assert diff.source_value == 'addr1'
                assert diff.target_value == 'addr1-modified'
            elif diff.type == DiffType.ADDED and 'address2' in str(diff.target_value):
                added_entry = True
                
        assert changed_text
        assert added_entry
        
    def test_named_elements(self):
        """Test comparing elements with name attributes (common in PAN-OS XML)."""
        # Create source with named entries
        source_builder = XmlBuilder('config')
        source_builder.into('address')
        source_builder.add('entry', {'name': 'addr1'}, 'value1')
        source_builder.add('entry', {'name': 'addr2'}, 'value2')
        source_builder.root_up()
        
        # Create target with modifications to named entries
        target_builder = XmlBuilder('config')
        target_builder.into('address')
        target_builder.add('entry', {'name': 'addr1'}, 'value1-changed')  # Changed value
        target_builder.add('entry', {'name': 'addr3'}, 'value3')  # New entry
        # addr2 is removed
        target_builder.root_up()
        
        # Compare them
        source = source_builder.build()
        target = target_builder.build()
        diffs = XmlDiff.compare(source, target)
        
        # Should have three diffs:
        # 1. Changed text in addr1
        # 2. Removed addr2
        # 3. Added addr3
        assert len(diffs) == 3
        
        # Check for specific diffs
        changed_text = False
        removed_entry = False
        added_entry = False
        
        for diff in diffs:
            if diff.type == DiffType.CHANGED and "[@name='addr1']" in diff.path:
                changed_text = True
            elif diff.type == DiffType.REMOVED and "[@name='addr2']" in diff.path:
                removed_entry = True
            elif diff.type == DiffType.ADDED and "[@name='addr3']" in diff.path:
                added_entry = True
                
        assert changed_text
        assert removed_entry
        assert added_entry
        
    def test_format_diff(self):
        """Test formatting diffs."""
        # Create some diffs
        diffs = [
            DiffItem(DiffType.ADDED, '/root/child', None, {'tag': 'child'}),
            DiffItem(DiffType.REMOVED, '/root/old', {'tag': 'old'}, None),
            DiffItem(DiffType.CHANGED, '/root/attr/@name', 'old-name', 'new-name')
        ]
        
        # Test text format
        text = XmlDiff.format_diff(diffs, 'text')
        assert '+ /root/child' in text
        assert '- /root/old' in text
        assert '~ /root/attr/@name' in text
        
        # Test html format
        html = XmlDiff.format_diff(diffs, 'html')
        assert '<table>' in html
        assert '<tr class=\'added\'>' in html
        assert '<tr class=\'removed\'>' in html
        assert '<tr class=\'changed\'>' in html
        
        # Test markdown format
        markdown = XmlDiff.format_diff(diffs, 'markdown')
        assert '| Type | Path | Source | Target |' in markdown
        assert '| Added | /root/child |' in markdown
        assert '| Removed | /root/old |' in markdown
        assert '| Changed | /root/attr/@name |' in markdown
        
        # Test invalid format
        with pytest.raises(ValueError):
            XmlDiff.format_diff(diffs, 'invalid')
            
    def test_diff_item_representation(self):
        """Test the string representation of a diff item."""
        added = DiffItem(DiffType.ADDED, '/path', None, 'value')
        assert str(added) == '/path: ADDED value'
        
        removed = DiffItem(DiffType.REMOVED, '/path', 'value', None)
        assert str(removed) == '/path: REMOVED value'
        
        changed = DiffItem(DiffType.CHANGED, '/path', 'old', 'new')
        assert str(changed) == '/path: CHANGED old -> new'
        
        unchanged = DiffItem(DiffType.UNCHANGED, '/path')
        assert str(unchanged) == '/path: UNCHANGED'
        
    def test_diff_item_to_dict(self):
        """Test converting a diff item to a dictionary."""
        added = DiffItem(DiffType.ADDED, '/path', None, 'value')
        added_dict = added.to_dict()
        
        assert added_dict['type'] == 'added'
        assert added_dict['path'] == '/path'
        assert 'source_value' not in added_dict
        assert added_dict['target_value'] == 'value'
        
        changed = DiffItem(DiffType.CHANGED, '/path', 'old', 'new')
        changed_dict = changed.to_dict()
        
        assert changed_dict['type'] == 'changed'
        assert changed_dict['path'] == '/path'
        assert changed_dict['source_value'] == 'old'
        assert changed_dict['target_value'] == 'new'