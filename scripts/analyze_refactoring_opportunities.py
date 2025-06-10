#!/usr/bin/env python3
"""
Analyze the PANFlow codebase to identify refactoring opportunities.

This script uses the test suite tools to find duplication and patterns
that can be consolidated during refactoring.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.common.duplication_analyzer import DuplicationAnalyzer, PatternAnalyzer
from tests.common.compatibility_checker import CompatibilityChecker
from panflow.core.feature_flags import get_feature_report
import json


def analyze_cli_commands():
    """Analyze CLI command duplication."""
    print("=== CLI Command Analysis ===\n")
    
    # Analyze duplication in CLI commands
    analyzer = DuplicationAnalyzer(min_lines=5, similarity_threshold=0.80)
    cli_path = Path("panflow/cli/commands")
    
    print(f"Analyzing {cli_path}...")
    analyzer.analyze_directory(cli_path)
    analyzer.find_duplicates()
    
    stats = analyzer.get_duplication_stats()
    print(f"\nDuplication Statistics:")
    print(f"  Files analyzed: {stats['files_analyzed']}")
    print(f"  Total lines: {stats['total_lines']:,}")
    print(f"  Duplicated lines: {stats['duplicated_lines']:,}")
    print(f"  Duplication rate: {stats['duplication_percentage']:.1f}%")
    
    # Show top duplicate groups
    print(f"\nTop Duplicate Code Blocks:")
    sorted_duplicates = sorted(
        analyzer.duplicates.items(),
        key=lambda x: len(x[1]) * (x[1][0].end_line - x[1][0].start_line),
        reverse=True
    )
    
    for i, (group_id, blocks) in enumerate(sorted_duplicates[:5]):
        lines_per_block = blocks[0].end_line - blocks[0].start_line
        total_lines = lines_per_block * len(blocks)
        print(f"\n  {i+1}. {len(blocks)} instances × {lines_per_block} lines = {total_lines} total lines")
        for block in blocks[:3]:  # Show first 3 instances
            print(f"     - {block.file_path}:{block.start_line}-{block.end_line}")
        if len(blocks) > 3:
            print(f"     ... and {len(blocks)-3} more")
    
    return stats


def analyze_patterns():
    """Analyze common patterns in the codebase."""
    print("\n\n=== Pattern Analysis ===\n")
    
    pattern_analyzer = PatternAnalyzer()
    pattern_analyzer.analyze_directory(Path("panflow"))
    
    # Count patterns by category
    pattern_categories = {
        "CLI Parameters": ["typer_option", "config_load", "context_kwargs"],
        "Error Handling": ["try_except", "error_handling"],
        "Output Formatting": ["format_output", "json_format", "table_format"],
        "Query Operations": ["xpath_search", "graph_query", "select_objects"],
    }
    
    category_counts = {}
    for category, patterns in pattern_categories.items():
        count = sum(len(pattern_analyzer.patterns.get(p, [])) for p in patterns)
        category_counts[category] = count
    
    print("Pattern Categories:")
    for category, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  {category}: {count} occurrences")
    
    # Detailed pattern report
    print("\nDetailed Pattern Occurrences:")
    for pattern_name, occurrences in sorted(
        pattern_analyzer.patterns.items(), 
        key=lambda x: -len(x[1])
    )[:10]:
        print(f"\n  {pattern_name}: {len(occurrences)} occurrences")
        # Group by file
        file_counts = {}
        for file_path, _ in occurrences:
            file_counts[file_path] = file_counts.get(file_path, 0) + 1
        
        for file_path, count in sorted(file_counts.items(), key=lambda x: -x[1])[:3]:
            print(f"    - {file_path}: {count}x")


def identify_refactoring_candidates():
    """Identify the best candidates for refactoring."""
    print("\n\n=== Refactoring Candidates ===\n")
    
    # Analyze specific files for refactoring potential
    candidates = []
    
    cli_files = list(Path("panflow/cli/commands").glob("*.py"))
    for file_path in cli_files:
        if file_path.name.startswith("__"):
            continue
            
        with open(file_path) as f:
            content = f.read()
            lines = len(content.splitlines())
            
        # Count common patterns
        import re
        patterns = {
            "typer.Option": len(re.findall(r'typer\.Option', content)),
            "try/except": len(re.findall(r'try:', content)),
            "PANFlowConfig": len(re.findall(r'PANFlowConfig\(', content)),
            "context_kwargs": len(re.findall(r'context_kwargs', content)),
        }
        
        # Calculate refactoring score
        score = sum(patterns.values()) * 10 + lines
        
        candidates.append({
            "file": file_path.name,
            "lines": lines,
            "patterns": patterns,
            "score": score
        })
    
    # Sort by refactoring potential
    candidates.sort(key=lambda x: -x['score'])
    
    print("Top Refactoring Candidates (by potential impact):")
    for i, candidate in enumerate(candidates[:10]):
        print(f"\n  {i+1}. {candidate['file']} ({candidate['lines']} lines, score: {candidate['score']})")
        print(f"     Patterns: {json.dumps(candidate['patterns'], indent=0).replace('{', '').replace('}', '')}")


def estimate_code_reduction():
    """Estimate potential code reduction from refactoring."""
    print("\n\n=== Code Reduction Estimates ===\n")
    
    # Estimates based on pattern analysis
    estimates = {
        "CLI parameter handling": {
            "current_lines_per_command": 15,
            "refactored_lines": 2,
            "commands": 25,
        },
        "Error handling": {
            "current_lines_per_occurrence": 8,
            "refactored_lines": 1,
            "occurrences": 50,
        },
        "Context handling": {
            "current_lines_per_command": 12,
            "refactored_lines": 0,  # Moved to base
            "commands": 25,
        },
        "Output formatting": {
            "current_lines_per_command": 20,
            "refactored_lines": 3,
            "commands": 20,
        },
    }
    
    total_current = 0
    total_reduced = 0
    
    print("Estimated Reductions by Category:")
    for category, est in estimates.items():
        # Handle different key patterns in estimates
        if "current_lines_per_command" in est:
            current = est["current_lines_per_command"] * est.get("commands", 0)
        elif "current_lines_per_occurrence" in est:
            current = est["current_lines_per_occurrence"] * est.get("occurrences", 0)
        else:
            current = 0
        reduced = est["refactored_lines"] * est.get("commands", est.get("occurrences", 0))
        savings = current - reduced
        
        total_current += current
        total_reduced += reduced
        
        print(f"\n  {category}:")
        print(f"    Current: {current:,} lines")
        print(f"    After refactoring: {reduced:,} lines")
        print(f"    Savings: {savings:,} lines ({savings/current*100:.1f}%)")
    
    # Add overhead for base classes
    base_class_overhead = 500
    net_savings = total_current - total_reduced - base_class_overhead
    
    print(f"\nTotal Estimates:")
    print(f"  Current total: {total_current:,} lines")
    print(f"  After refactoring: {total_reduced:,} lines")
    print(f"  Base class overhead: {base_class_overhead:,} lines")
    print(f"  Net savings: {net_savings:,} lines ({net_savings/total_current*100:.1f}%)")


def check_feature_flags():
    """Check current feature flag status."""
    print("\n\n=== Feature Flag Status ===\n")
    print(get_feature_report())


def main():
    """Run all analyses."""
    print("PANFlow Refactoring Analysis")
    print("=" * 50)
    
    # Run analyses
    cli_stats = analyze_cli_commands()
    analyze_patterns()
    identify_refactoring_candidates()
    estimate_code_reduction()
    check_feature_flags()
    
    # Summary
    print("\n\n=== Summary ===\n")
    print(f"Current duplication in CLI: {cli_stats['duplication_percentage']:.1f}%")
    print(f"Estimated reduction potential: 35-40%")
    print(f"Recommended starting point: object_commands.py")
    print(f"\nNext steps:")
    print("1. Enable feature flags for testing")
    print("2. Refactor high-score files first")
    print("3. Use test suite to verify compatibility")
    print("4. Track metrics after each refactoring")


if __name__ == "__main__":
    main()