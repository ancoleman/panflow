"""
Code duplication analyzer for PANFlow.

This module provides tools to analyze code duplication and track
reduction progress during refactoring.
"""

import ast
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional, Any
from collections import defaultdict
import difflib


class CodeBlock:
    """Represents a block of code for duplication analysis."""
    
    def __init__(self, file_path: str, start_line: int, end_line: int, content: str):
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.content = content
        self.normalized_content = self._normalize_code(content)
        self.hash = self._compute_hash()
    
    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison (remove comments, normalize whitespace)."""
        lines = []
        for line in code.split('\n'):
            # Remove comments
            if '#' in line:
                line = line[:line.index('#')]
            # Strip whitespace
            line = line.strip()
            if line:
                lines.append(line)
        return '\n'.join(lines)
    
    def _compute_hash(self) -> str:
        """Compute hash of normalized content."""
        return hashlib.md5(self.normalized_content.encode()).hexdigest()
    
    def similarity(self, other: 'CodeBlock') -> float:
        """Calculate similarity to another code block (0.0 to 1.0)."""
        matcher = difflib.SequenceMatcher(
            None,
            self.normalized_content,
            other.normalized_content
        )
        return matcher.ratio()


class DuplicationAnalyzer:
    """Analyze code duplication in Python files."""
    
    def __init__(self, min_lines: int = 10, similarity_threshold: float = 0.85):
        """
        Initialize analyzer.
        
        Args:
            min_lines: Minimum lines to consider as duplication
            similarity_threshold: Similarity threshold (0.0 to 1.0)
        """
        self.min_lines = min_lines
        self.similarity_threshold = similarity_threshold
        self.code_blocks: List[CodeBlock] = []
        self.duplicates: Dict[str, List[CodeBlock]] = defaultdict(list)
    
    def analyze_file(self, file_path: Path):
        """Analyze a single Python file for code blocks."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Extract functions and classes
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    # Get source lines
                    start_line = node.lineno
                    end_line = node.end_lineno or start_line
                    
                    if end_line - start_line >= self.min_lines:
                        # Extract code
                        lines = content.split('\n')[start_line-1:end_line]
                        block_content = '\n'.join(lines)
                        
                        block = CodeBlock(
                            str(file_path),
                            start_line,
                            end_line,
                            block_content
                        )
                        self.code_blocks.append(block)
        
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    def analyze_directory(self, directory: Path, pattern: str = "*.py"):
        """Analyze all Python files in a directory."""
        for file_path in directory.rglob(pattern):
            # Skip test files and __pycache__
            if '__pycache__' in str(file_path) or 'test_' in file_path.name:
                continue
            self.analyze_file(file_path)
    
    def find_duplicates(self):
        """Find duplicate code blocks."""
        # Group by hash for exact duplicates
        hash_groups = defaultdict(list)
        for block in self.code_blocks:
            hash_groups[block.hash].append(block)
        
        # Add exact duplicates
        for hash_value, blocks in hash_groups.items():
            if len(blocks) > 1:
                self.duplicates[f"exact_{hash_value}"] = blocks
        
        # Find similar blocks (not exact duplicates)
        processed = set()
        for i, block1 in enumerate(self.code_blocks):
            if block1.hash in processed:
                continue
            
            similar_blocks = [block1]
            for j, block2 in enumerate(self.code_blocks[i+1:], i+1):
                if block2.hash not in processed:
                    similarity = block1.similarity(block2)
                    if similarity >= self.similarity_threshold and similarity < 1.0:
                        similar_blocks.append(block2)
                        processed.add(block2.hash)
            
            if len(similar_blocks) > 1:
                self.duplicates[f"similar_{block1.hash[:8]}"] = similar_blocks
    
    def generate_report(self) -> str:
        """Generate a duplication report."""
        report_lines = [
            "Code Duplication Analysis Report",
            "=" * 50,
            f"Total files analyzed: {len(set(b.file_path for b in self.code_blocks))}",
            f"Total code blocks: {len(self.code_blocks)}",
            f"Duplicate groups found: {len(self.duplicates)}",
            ""
        ]
        
        total_duplicated_lines = 0
        
        for group_id, blocks in self.duplicates.items():
            is_exact = group_id.startswith("exact_")
            report_lines.append(f"{'Exact' if is_exact else 'Similar'} Duplicate Group ({len(blocks)} instances):")
            
            for block in blocks:
                lines = block.end_line - block.start_line + 1
                total_duplicated_lines += lines
                report_lines.append(f"  - {block.file_path}:{block.start_line}-{block.end_line} ({lines} lines)")
            
            # Show first few lines of the duplicate
            report_lines.append("  Preview:")
            preview_lines = blocks[0].content.split('\n')[:5]
            for line in preview_lines:
                report_lines.append(f"    {line}")
            if len(blocks[0].content.split('\n')) > 5:
                report_lines.append("    ...")
            report_lines.append("")
        
        # Summary statistics
        total_lines = sum(b.end_line - b.start_line + 1 for b in self.code_blocks)
        duplication_percentage = (total_duplicated_lines / total_lines * 100) if total_lines > 0 else 0
        
        report_lines.extend([
            "Summary:",
            f"  Total lines analyzed: {total_lines}",
            f"  Duplicated lines: {total_duplicated_lines}",
            f"  Duplication percentage: {duplication_percentage:.1f}%"
        ])
        
        return "\n".join(report_lines)
    
    def get_duplication_stats(self) -> Dict[str, Any]:
        """Get duplication statistics."""
        total_lines = sum(b.end_line - b.start_line + 1 for b in self.code_blocks)
        duplicated_lines = sum(
            sum(block.end_line - block.start_line + 1 for block in blocks)
            for blocks in self.duplicates.values()
        )
        
        return {
            "files_analyzed": len(set(b.file_path for b in self.code_blocks)),
            "total_blocks": len(self.code_blocks),
            "duplicate_groups": len(self.duplicates),
            "total_lines": total_lines,
            "duplicated_lines": duplicated_lines,
            "duplication_percentage": (duplicated_lines / total_lines * 100) if total_lines > 0 else 0
        }


class PatternAnalyzer:
    """Analyze common patterns in code."""
    
    def __init__(self):
        self.patterns: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
    
    def analyze_file(self, file_path: Path):
        """Analyze patterns in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Common patterns to look for
            patterns_to_check = {
                "typer_option": r'typer\.Option\([^)]+\)',
                "try_except": r'try:\s*\n.*?\nexcept.*?:',
                "config_load": r'PANFlowConfig\([^)]+\)',
                "context_kwargs": r'context_kwargs\s*=\s*\{[^}]*\}',
                "format_output": r'if\s+format\s*==\s*["\']json["\']:',
                "error_handling": r'console\.print\(.*?\[red\]Error.*?\)',
            }
            
            import re
            for pattern_name, pattern_regex in patterns_to_check.items():
                matches = re.finditer(pattern_regex, content, re.DOTALL | re.MULTILINE)
                for match in matches:
                    line_no = content[:match.start()].count('\n') + 1
                    self.patterns[pattern_name].append((str(file_path), line_no))
        
        except Exception as e:
            print(f"Error analyzing patterns in {file_path}: {e}")
    
    def analyze_directory(self, directory: Path):
        """Analyze patterns in all Python files."""
        for file_path in directory.rglob("*.py"):
            if '__pycache__' not in str(file_path):
                self.analyze_file(file_path)
    
    def generate_report(self) -> str:
        """Generate pattern analysis report."""
        report_lines = [
            "Code Pattern Analysis Report",
            "=" * 50,
            ""
        ]
        
        for pattern_name, occurrences in sorted(self.patterns.items(), key=lambda x: -len(x[1])):
            report_lines.append(f"{pattern_name}: {len(occurrences)} occurrences")
            
            # Show first 5 occurrences
            for file_path, line_no in occurrences[:5]:
                report_lines.append(f"  - {file_path}:{line_no}")
            
            if len(occurrences) > 5:
                report_lines.append(f"  ... and {len(occurrences) - 5} more")
            report_lines.append("")
        
        return "\n".join(report_lines)


def analyze_duplication(directory: str, output_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze code duplication in a directory.
    
    Args:
        directory: Directory to analyze
        output_file: Optional file to save report
        
    Returns:
        Duplication statistics
    """
    analyzer = DuplicationAnalyzer()
    analyzer.analyze_directory(Path(directory))
    analyzer.find_duplicates()
    
    report = analyzer.generate_report()
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report)
    else:
        print(report)
    
    return analyzer.get_duplication_stats()


def analyze_patterns(directory: str, output_file: Optional[str] = None):
    """
    Analyze code patterns in a directory.
    
    Args:
        directory: Directory to analyze
        output_file: Optional file to save report
    """
    analyzer = PatternAnalyzer()
    analyzer.analyze_directory(Path(directory))
    
    report = analyzer.generate_report()
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report)
    else:
        print(report)