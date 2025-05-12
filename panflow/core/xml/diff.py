"""
XML diff utilities for PANFlow.

This module provides functionality for comparing XML trees and identifying
differences between them, which is useful for configuration management
and change tracking.
"""

import logging
import enum
from typing import Dict, Any, Optional, List, Tuple, Union, Iterator, Set
from lxml import etree

from ..exceptions import PANFlowError, DiffError
from .base import element_to_dict, find_element
from .builder import XmlNode

# Initialize logger
logger = logging.getLogger("panflow")


class DiffType(enum.Enum):
    """Enumeration of diff operation types."""

    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"
    UNCHANGED = "unchanged"


class DiffItem:
    """
    Represents a single difference between two XML elements.

    A DiffItem captures the path, type of change, and before/after values
    of a difference between two XML trees.
    """

    def __init__(
        self, path: str, diff_type: DiffType, source_value: Any = None, target_value: Any = None
    ):
        """
        Initialize a diff item.

        Args:
            path: XPath-like path to the changed element
            diff_type: Type of difference
            source_value: Value in source (before) XML
            target_value: Value in target (after) XML
        """
        self.path = path
        self.diff_type = diff_type
        self.source_value = source_value
        self.target_value = target_value

    def __repr__(self) -> str:
        """String representation."""
        if self.diff_type == DiffType.ADDED:
            return f"{self.path}: ADDED {self.target_value}"
        elif self.diff_type == DiffType.REMOVED:
            return f"{self.path}: REMOVED {self.source_value}"
        elif self.diff_type == DiffType.CHANGED:
            return f"{self.path}: CHANGED {self.source_value} -> {self.target_value}"
        else:
            return f"{self.path}: UNCHANGED"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "path": self.path,
            "type": self.diff_type.value,
            "source_value": self.source_value,
            "target_value": self.target_value,
        }


class XmlDiff:
    """
    Compare two XML trees and identify differences.

    This class provides functionality for comparing two XML trees and
    identifying added, removed, and changed elements.
    """

    def __init__(
        self,
        source: Optional[Union[etree._Element, XmlNode]] = None,
        target: Optional[Union[etree._Element, XmlNode]] = None,
    ):
        """
        Initialize with optional source and target XML trees.

        Args:
            source: Source (before) XML tree
            target: Target (after) XML tree
        """
        self.source = source.element if isinstance(source, XmlNode) else source
        self.target = target.element if isinstance(target, XmlNode) else target
        self.diffs: List[DiffItem] = []

    def set_source(self, source: Union[etree._Element, XmlNode]) -> "XmlDiff":
        """
        Set the source XML tree.

        Args:
            source: Source XML tree

        Returns:
            Self for chaining
        """
        self.source = source.element if isinstance(source, XmlNode) else source
        return self

    def set_target(self, target: Union[etree._Element, XmlNode]) -> "XmlDiff":
        """
        Set the target XML tree.

        Args:
            target: Target XML tree

        Returns:
            Self for chaining
        """
        self.target = target.element if isinstance(target, XmlNode) else target
        return self

    def compare(self, detect_moves: bool = False, ignore_order: bool = True) -> "XmlDiff":
        """
        Compare the source and target XML trees.

        Args:
            detect_moves: Whether to detect moved elements
            ignore_order: Whether to ignore the order of elements

        Returns:
            Self for chaining

        Raises:
            DiffError: If source or target is not set
        """
        if self.source is None or self.target is None:
            raise DiffError("Both source and target must be set before comparing")

        self.diffs = []
        self._compare_elements(self.source, self.target, "/", detect_moves, ignore_order)
        return self

    def _compare_elements(
        self,
        source: etree._Element,
        target: etree._Element,
        path: str,
        detect_moves: bool,
        ignore_order: bool,
    ) -> None:
        """
        Compare two elements recursively.

        Args:
            source: Source element
            target: Target element
            path: Current path in the tree
            detect_moves: Whether to detect moved elements
            ignore_order: Whether to ignore the order of elements
        """
        # Compare attributes
        self._compare_attributes(source, target, path)

        # Compare text content
        if (source.text and source.text.strip()) or (target.text and target.text.strip()):
            source_text = source.text.strip() if source.text else ""
            target_text = target.text.strip() if target.text else ""

            if source_text != target_text:
                self.diffs.append(
                    DiffItem(f"{path}text()", DiffType.CHANGED, source_text, target_text)
                )

        # Get children by tag
        source_children_by_tag = self._group_children_by_tag(source)
        target_children_by_tag = self._group_children_by_tag(target)

        # Find tags in both source and target
        common_tags = set(source_children_by_tag.keys()) & set(target_children_by_tag.keys())

        # Handle removed tags
        for tag in set(source_children_by_tag.keys()) - common_tags:
            for child in source_children_by_tag[tag]:
                child_path = self._get_child_path(path, child)
                self._add_removed_element(child, child_path)

        # Handle added tags
        for tag in set(target_children_by_tag.keys()) - common_tags:
            for child in target_children_by_tag[tag]:
                child_path = self._get_child_path(path, child)
                self._add_added_element(child, child_path)

        # Compare children with same tag
        for tag in common_tags:
            source_children = source_children_by_tag[tag]
            target_children = target_children_by_tag[tag]

            # Handle the case where elements have a name attribute (common in PAN-OS XML)
            if all("name" in child.attrib for child in source_children + target_children):
                self._compare_named_children(
                    source_children, target_children, path, detect_moves, ignore_order
                )
            else:
                # For elements without name attributes, compare by index if counts match
                if len(source_children) == len(target_children):
                    for i, (source_child, target_child) in enumerate(
                        zip(source_children, target_children)
                    ):
                        child_path = f"{path}{tag}[{i+1}]/"
                        self._compare_elements(
                            source_child, target_child, child_path, detect_moves, ignore_order
                        )
                else:
                    # Different counts, treat as added/removed
                    for i, source_child in enumerate(source_children):
                        if i < len(target_children):
                            child_path = f"{path}{tag}[{i+1}]/"
                            self._compare_elements(
                                source_child,
                                target_children[i],
                                child_path,
                                detect_moves,
                                ignore_order,
                            )
                        else:
                            child_path = f"{path}{tag}[{i+1}]/"
                            self._add_removed_element(source_child, child_path)

                    for i in range(len(source_children), len(target_children)):
                        child_path = f"{path}{tag}[{i+1}]/"
                        self._add_added_element(target_children[i], child_path)

    def _compare_attributes(
        self, source: etree._Element, target: etree._Element, path: str
    ) -> None:
        """
        Compare attributes of two elements.

        Args:
            source: Source element
            target: Target element
            path: Current path in the tree
        """
        source_attrs = source.attrib
        target_attrs = target.attrib

        # Check for changed or removed attributes
        for name, value in source_attrs.items():
            if name in target_attrs:
                if value != target_attrs[name]:
                    self.diffs.append(
                        DiffItem(f"{path}@{name}", DiffType.CHANGED, value, target_attrs[name])
                    )
            else:
                self.diffs.append(DiffItem(f"{path}@{name}", DiffType.REMOVED, value, None))

        # Check for added attributes
        for name, value in target_attrs.items():
            if name not in source_attrs:
                self.diffs.append(DiffItem(f"{path}@{name}", DiffType.ADDED, None, value))

    def _compare_named_children(
        self,
        source_children: List[etree._Element],
        target_children: List[etree._Element],
        path: str,
        detect_moves: bool,
        ignore_order: bool,
    ) -> None:
        """
        Compare children with 'name' attributes.

        Args:
            source_children: Source child elements
            target_children: Target child elements
            path: Current path in the tree
            detect_moves: Whether to detect moved elements
            ignore_order: Whether to ignore the order of elements
        """
        source_by_name = {child.get("name"): child for child in source_children}
        target_by_name = {child.get("name"): child for child in target_children}

        # Find common named elements
        common_names = set(source_by_name.keys()) & set(target_by_name.keys())

        # Compare common elements
        for name in common_names:
            source_child = source_by_name[name]
            target_child = target_by_name[name]
            child_path = f"{path}{source_child.tag}[@name='{name}']/"
            self._compare_elements(
                source_child, target_child, child_path, detect_moves, ignore_order
            )

        # Handle removed elements
        for name in set(source_by_name.keys()) - common_names:
            child = source_by_name[name]
            child_path = f"{path}{child.tag}[@name='{name}']/"
            self._add_removed_element(child, child_path)

        # Handle added elements
        for name in set(target_by_name.keys()) - common_names:
            child = target_by_name[name]
            child_path = f"{path}{child.tag}[@name='{name}']/"
            self._add_added_element(child, child_path)

    def _add_removed_element(self, element: etree._Element, path: str) -> None:
        """
        Add a diff item for a removed element.

        Args:
            element: Removed element
            path: Path to the element
        """
        self.diffs.append(DiffItem(path, DiffType.REMOVED, element_to_dict(element), None))

    def _add_added_element(self, element: etree._Element, path: str) -> None:
        """
        Add a diff item for an added element.

        Args:
            element: Added element
            path: Path to the element
        """
        self.diffs.append(DiffItem(path, DiffType.ADDED, None, element_to_dict(element)))

    def _group_children_by_tag(self, element: etree._Element) -> Dict[str, List[etree._Element]]:
        """
        Group child elements by tag name.

        Args:
            element: Parent element

        Returns:
            Dictionary mapping tag names to lists of elements
        """
        result = {}
        for child in element:
            if child.tag not in result:
                result[child.tag] = []
            result[child.tag].append(child)
        return result

    def _get_child_path(self, path: str, child: etree._Element) -> str:
        """
        Get the path to a child element.

        Args:
            path: Parent path
            child: Child element

        Returns:
            Path to the child
        """
        if "name" in child.attrib:
            return f"{path}{child.tag}[@name='{child.get('name')}']/"
        else:
            # Find the index of this child among siblings with the same tag
            parent = child.getparent()
            if parent is not None:
                siblings = [c for c in parent if c.tag == child.tag]
                index = siblings.index(child) + 1  # XPath is 1-indexed
                return f"{path}{child.tag}[{index}]/"
            return f"{path}{child.tag}/"

    @property
    def has_differences(self) -> bool:
        """Check if there are any differences."""
        return len(self.diffs) > 0

    def get_diffs(self) -> List[DiffItem]:
        """
        Get the list of differences.

        Returns:
            List of DiffItem objects
        """
        return self.diffs

    def get_diffs_by_type(self, diff_type: DiffType) -> List[DiffItem]:
        """
        Get differences of a specific type.

        Args:
            diff_type: Type of differences to get

        Returns:
            List of DiffItem objects of the specified type
        """
        return [diff for diff in self.diffs if diff.diff_type == diff_type]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the diff results to a dictionary.

        Returns:
            Dictionary with added, removed, and changed items
        """
        return {
            "added": [diff.to_dict() for diff in self.get_diffs_by_type(DiffType.ADDED)],
            "removed": [diff.to_dict() for diff in self.get_diffs_by_type(DiffType.REMOVED)],
            "changed": [diff.to_dict() for diff in self.get_diffs_by_type(DiffType.CHANGED)],
            "total": len(self.diffs),
        }

    def summarize(self) -> Dict[str, int]:
        """
        Get a summary of the differences.

        Returns:
            Dictionary with counts of added, removed, and changed items
        """
        return {
            "added": len(self.get_diffs_by_type(DiffType.ADDED)),
            "removed": len(self.get_diffs_by_type(DiffType.REMOVED)),
            "changed": len(self.get_diffs_by_type(DiffType.CHANGED)),
            "total": len(self.diffs),
        }
