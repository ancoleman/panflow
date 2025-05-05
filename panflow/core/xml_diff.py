"""
XML diff utilities for PANFlow.

This module provides tools for comparing XML elements and generating diffs.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple, Union, Set
from enum import Enum
from lxml import etree

from .exceptions import PANFlowError
from .xml_utils import element_to_dict, find_element
from .xml_builder import XmlNode

# Initialize logger
logger = logging.getLogger("panflow")

class DiffType(Enum):
    """Types of differences between XML elements."""
    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"
    UNCHANGED = "unchanged"

class DiffItem:
    """
    Represents a difference between XML elements.
    
    Attributes:
        type: Type of difference
        path: Path to the difference
        source_value: Value in the source element
        target_value: Value in the target element
    """
    
    def __init__(
        self, 
        diff_type: DiffType, 
        path: str, 
        source_value: Optional[Any] = None, 
        target_value: Optional[Any] = None
    ):
        """
        Initialize a diff item.
        
        Args:
            diff_type: Type of difference
            path: Path to the difference
            source_value: Value in the source element
            target_value: Value in the target element
        """
        self.type = diff_type
        self.path = path
        self.source_value = source_value
        self.target_value = target_value
    
    def __repr__(self) -> str:
        """String representation."""
        if self.type == DiffType.ADDED:
            return f"{self.path}: ADDED {self.target_value}"
        elif self.type == DiffType.REMOVED:
            return f"{self.path}: REMOVED {self.source_value}"
        elif self.type == DiffType.CHANGED:
            return f"{self.path}: CHANGED {self.source_value} -> {self.target_value}"
        else:
            return f"{self.path}: UNCHANGED"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary.
        
        Returns:
            Dictionary representation
        """
        result = {
            "type": self.type.value,
            "path": self.path
        }
        
        if self.source_value is not None:
            result["source_value"] = self.source_value
            
        if self.target_value is not None:
            result["target_value"] = self.target_value
            
        return result

class XmlDiff:
    """
    Utility for comparing XML elements and generating diffs.
    """
    
    @staticmethod
    def compare(
        source: Union[etree._Element, XmlNode], 
        target: Union[etree._Element, XmlNode],
        ignore_attributes: Optional[List[str]] = None,
        ignore_elements: Optional[List[str]] = None
    ) -> List[DiffItem]:
        """
        Compare two XML elements and generate a diff.
        
        Args:
            source: Source element
            target: Target element
            ignore_attributes: Optional list of attributes to ignore
            ignore_elements: Optional list of element tags to ignore
            
        Returns:
            List of diff items
        """
        # Convert XmlNode to etree.Element if needed
        if isinstance(source, XmlNode):
            source = source.element
            
        if isinstance(target, XmlNode):
            target = target.element
            
        ignore_attributes = ignore_attributes or []
        ignore_elements = ignore_elements or []
        
        diffs = []
        XmlDiff._compare_elements(source, target, "", diffs, ignore_attributes, ignore_elements)
        return diffs
    
    @staticmethod
    def _compare_elements(
        source: Optional[etree._Element], 
        target: Optional[etree._Element], 
        path: str, 
        diffs: List[DiffItem], 
        ignore_attributes: List[str],
        ignore_elements: List[str]
    ) -> None:
        """
        Compare two elements recursively.
        
        Args:
            source: Source element
            target: Target element
            path: Current element path
            diffs: List to add differences to
            ignore_attributes: Attributes to ignore
            ignore_elements: Element tags to ignore
        """
        # Element exists in source but not in target
        if source is not None and target is None:
            diffs.append(DiffItem(
                DiffType.REMOVED, 
                path, 
                XmlDiff._element_summary(source),
                None
            ))
            return
            
        # Element exists in target but not in source
        if source is None and target is not None:
            diffs.append(DiffItem(
                DiffType.ADDED, 
                path, 
                None,
                XmlDiff._element_summary(target)
            ))
            return
            
        # Both elements exist
        if source is not None and target is not None:
            # Skip if this element type should be ignored
            if source.tag in ignore_elements:
                return
                
            # Compare tags
            if source.tag != target.tag:
                diffs.append(DiffItem(
                    DiffType.CHANGED, 
                    f"{path}/@tag", 
                    source.tag,
                    target.tag
                ))
            
            # Compare text
            source_text = (source.text or "").strip()
            target_text = (target.text or "").strip()
            
            if source_text != target_text:
                diffs.append(DiffItem(
                    DiffType.CHANGED, 
                    f"{path}/text()", 
                    source_text,
                    target_text
                ))
            
            # Compare attributes
            source_attrib = {k: v for k, v in source.attrib.items() if k not in ignore_attributes}
            target_attrib = {k: v for k, v in target.attrib.items() if k not in ignore_attributes}
            
            # Attributes in source but not in target
            for name, value in source_attrib.items():
                if name not in target_attrib:
                    diffs.append(DiffItem(
                        DiffType.REMOVED, 
                        f"{path}/@{name}", 
                        value,
                        None
                    ))
                elif target_attrib[name] != value:
                    diffs.append(DiffItem(
                        DiffType.CHANGED, 
                        f"{path}/@{name}", 
                        value,
                        target_attrib[name]
                    ))
            
            # Attributes in target but not in source
            for name, value in target_attrib.items():
                if name not in source_attrib:
                    diffs.append(DiffItem(
                        DiffType.ADDED, 
                        f"{path}/@{name}", 
                        None,
                        value
                    ))
            
            # Compare children
            source_children = list(source)
            target_children = list(target)
            
            # Simple case: elements with name attributes
            if all(child.get("name") is not None for child in source_children + target_children):
                source_children_by_name = {child.get("name"): child for child in source_children}
                target_children_by_name = {child.get("name"): child for child in target_children}
                
                # Children in source but not in target
                for name, child in source_children_by_name.items():
                    if name not in target_children_by_name:
                        child_path = f"{path}/{child.tag}[@name='{name}']"
                        diffs.append(DiffItem(
                            DiffType.REMOVED, 
                            child_path, 
                            XmlDiff._element_summary(child),
                            None
                        ))
                    else:
                        child_path = f"{path}/{child.tag}[@name='{name}']"
                        XmlDiff._compare_elements(
                            child, 
                            target_children_by_name[name], 
                            child_path, 
                            diffs,
                            ignore_attributes,
                            ignore_elements
                        )
                
                # Children in target but not in source
                for name, child in target_children_by_name.items():
                    if name not in source_children_by_name:
                        child_path = f"{path}/{child.tag}[@name='{name}']"
                        diffs.append(DiffItem(
                            DiffType.ADDED, 
                            child_path, 
                            None,
                            XmlDiff._element_summary(child)
                        ))
            else:
                # More complex case: elements without name attributes
                # Group by tag
                source_children_by_tag = {}
                for child in source_children:
                    source_children_by_tag.setdefault(child.tag, []).append(child)
                
                target_children_by_tag = {}
                for child in target_children:
                    target_children_by_tag.setdefault(child.tag, []).append(child)
                
                # Compare children by tag
                all_tags = set(source_children_by_tag.keys()) | set(target_children_by_tag.keys())
                
                for tag in all_tags:
                    source_elements = source_children_by_tag.get(tag, [])
                    target_elements = target_children_by_tag.get(tag, [])
                    
                    # Simple case: same number of elements
                    if len(source_elements) == len(target_elements):
                        for i, (source_elem, target_elem) in enumerate(zip(source_elements, target_elements)):
                            child_path = f"{path}/{tag}[{i+1}]"
                            XmlDiff._compare_elements(
                                source_elem, 
                                target_elem, 
                                child_path, 
                                diffs,
                                ignore_attributes,
                                ignore_elements
                            )
                    else:
                        # Different number of elements
                        # Try to match by content similarity
                        matches = []
                        
                        # Find best matches
                        for i, source_elem in enumerate(source_elements):
                            best_match = None
                            best_score = 0
                            
                            for j, target_elem in enumerate(target_elements):
                                if j in [match[1] for match in matches]:
                                    continue  # Already matched
                                    
                                score = XmlDiff._similarity_score(source_elem, target_elem)
                                if score > best_score:
                                    best_score = score
                                    best_match = j
                            
                            if best_match is not None and best_score > 0.5:  # Arbitrary threshold
                                matches.append((i, best_match))
                        
                        # Compare matched elements
                        for source_idx, target_idx in matches:
                            source_elem = source_elements[source_idx]
                            target_elem = target_elements[target_idx]
                            child_path = f"{path}/{tag}[{target_idx+1}]"
                            XmlDiff._compare_elements(
                                source_elem, 
                                target_elem, 
                                child_path, 
                                diffs,
                                ignore_attributes,
                                ignore_elements
                            )
                        
                        # Add unmatched source elements as removed
                        unmatched_source = [i for i in range(len(source_elements)) 
                                            if i not in [m[0] for m in matches]]
                        for i in unmatched_source:
                            source_elem = source_elements[i]
                            child_path = f"{path}/{tag}[?]"
                            diffs.append(DiffItem(
                                DiffType.REMOVED, 
                                child_path, 
                                XmlDiff._element_summary(source_elem),
                                None
                            ))
                        
                        # Add unmatched target elements as added
                        unmatched_target = [i for i in range(len(target_elements)) 
                                            if i not in [m[1] for m in matches]]
                        for i in unmatched_target:
                            target_elem = target_elements[i]
                            child_path = f"{path}/{tag}[{i+1}]"
                            diffs.append(DiffItem(
                                DiffType.ADDED, 
                                child_path, 
                                None,
                                XmlDiff._element_summary(target_elem)
                            ))
    
    @staticmethod
    def _similarity_score(elem1: etree._Element, elem2: etree._Element) -> float:
        """
        Calculate a similarity score between two elements.
        
        Args:
            elem1: First element
            elem2: Second element
            
        Returns:
            Similarity score (0-1)
        """
        # Simple implementation: tag, attributes, and text similarity
        score = 0.0
        
        # Same tag
        if elem1.tag == elem2.tag:
            score += 0.3
        
        # Text similarity
        text1 = (elem1.text or "").strip()
        text2 = (elem2.text or "").strip()
        
        if text1 == text2:
            score += 0.3
        elif text1 and text2 and (text1 in text2 or text2 in text1):
            score += 0.15
        
        # Attribute similarity
        attrib1 = set(elem1.attrib.items())
        attrib2 = set(elem2.attrib.items())
        
        if attrib1 and attrib2:
            common = len(attrib1.intersection(attrib2))
            total = len(attrib1.union(attrib2))
            score += 0.4 * (common / total)
        
        return score
    
    @staticmethod
    def _element_summary(element: etree._Element) -> Dict[str, Any]:
        """
        Create a summary of an element for diff display.
        
        Args:
            element: Element to summarize
            
        Returns:
            Dictionary summary
        """
        summary = {
            "tag": element.tag
        }
        
        if element.attrib:
            summary["attributes"] = dict(element.attrib)
            
        if element.text and element.text.strip():
            summary["text"] = element.text.strip()
            
        if len(element):
            summary["children_count"] = len(element)
            
        return summary
    
    @staticmethod
    def format_diff(diffs: List[DiffItem], format_type: str = "text") -> str:
        """
        Format a diff for display.
        
        Args:
            diffs: List of diff items
            format_type: Format type (text, html, or markdown)
            
        Returns:
            Formatted diff string
        """
        if format_type == "text":
            return XmlDiff._format_text(diffs)
        elif format_type == "html":
            return XmlDiff._format_html(diffs)
        elif format_type == "markdown":
            return XmlDiff._format_markdown(diffs)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")
    
    @staticmethod
    def _format_text(diffs: List[DiffItem]) -> str:
        """Format diffs as plain text."""
        result = []
        
        for diff in diffs:
            if diff.type == DiffType.ADDED:
                result.append(f"+ {diff.path}: {diff.target_value}")
            elif diff.type == DiffType.REMOVED:
                result.append(f"- {diff.path}: {diff.source_value}")
            elif diff.type == DiffType.CHANGED:
                result.append(f"~ {diff.path}: {diff.source_value} -> {diff.target_value}")
        
        return "\n".join(result)
    
    @staticmethod
    def _format_html(diffs: List[DiffItem]) -> str:
        """Format diffs as HTML."""
        result = ["<table>", "<tr><th>Type</th><th>Path</th><th>Source</th><th>Target</th></tr>"]
        
        for diff in diffs:
            if diff.type == DiffType.ADDED:
                result.append(f"<tr class='added'><td>Added</td><td>{diff.path}</td><td></td><td>{diff.target_value}</td></tr>")
            elif diff.type == DiffType.REMOVED:
                result.append(f"<tr class='removed'><td>Removed</td><td>{diff.path}</td><td>{diff.source_value}</td><td></td></tr>")
            elif diff.type == DiffType.CHANGED:
                result.append(f"<tr class='changed'><td>Changed</td><td>{diff.path}</td><td>{diff.source_value}</td><td>{diff.target_value}</td></tr>")
        
        result.append("</table>")
        return "\n".join(result)
    
    @staticmethod
    def _format_markdown(diffs: List[DiffItem]) -> str:
        """Format diffs as Markdown."""
        result = ["| Type | Path | Source | Target |", "|------|------|--------|--------|"]
        
        for diff in diffs:
            if diff.type == DiffType.ADDED:
                result.append(f"| Added | {diff.path} | | {diff.target_value} |")
            elif diff.type == DiffType.REMOVED:
                result.append(f"| Removed | {diff.path} | {diff.source_value} | |")
            elif diff.type == DiffType.CHANGED:
                result.append(f"| Changed | {diff.path} | {diff.source_value} | {diff.target_value} |")
        
        return "\n".join(result)