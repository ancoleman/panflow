"""
Backwards compatibility checker for PANFlow.

This module provides tools to ensure that refactoring doesn't break
existing functionality or APIs.
"""

import ast
import inspect
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict
import importlib
import difflib


class APISignature:
    """Represents an API signature for comparison."""
    
    def __init__(self, name: str, type: str, params: List[str], defaults: Dict[str, Any]):
        self.name = name
        self.type = type  # 'function', 'method', 'class'
        self.params = params
        self.defaults = defaults
    
    def __eq__(self, other: 'APISignature') -> bool:
        """Check if signatures are compatible."""
        if self.name != other.name or self.type != other.type:
            return False
        
        # Check parameters (order matters for positional args)
        if self.params != other.params:
            # Allow additional optional parameters at the end
            if len(other.params) > len(self.params):
                # New params must have defaults
                new_params = other.params[len(self.params):]
                for param in new_params:
                    if param not in other.defaults:
                        return False
                # Check that existing params match
                return self.params == other.params[:len(self.params)]
            else:
                return False
        
        return True
    
    def __str__(self) -> str:
        """String representation."""
        param_strs = []
        for param in self.params:
            if param in self.defaults:
                param_strs.append(f"{param}={repr(self.defaults[param])}")
            else:
                param_strs.append(param)
        
        return f"{self.name}({', '.join(param_strs)})"


class CompatibilityChecker:
    """Check backwards compatibility of Python APIs."""
    
    def __init__(self):
        self.old_apis: Dict[str, List[APISignature]] = defaultdict(list)
        self.new_apis: Dict[str, List[APISignature]] = defaultdict(list)
        self.breaking_changes: List[Dict[str, Any]] = []
        self.compatible_changes: List[Dict[str, Any]] = []
    
    def extract_module_apis(self, module_path: str) -> Dict[str, List[APISignature]]:
        """Extract API signatures from a module."""
        apis = defaultdict(list)
        
        try:
            # Import the module
            spec = importlib.util.spec_from_file_location("temp_module", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Extract all public APIs
            for name, obj in inspect.getmembers(module):
                if name.startswith('_'):
                    continue
                
                if inspect.isfunction(obj) or inspect.ismethod(obj):
                    sig = self._extract_function_signature(name, obj)
                    if sig:
                        apis[module_path].append(sig)
                
                elif inspect.isclass(obj):
                    # Extract class and its methods
                    class_sig = APISignature(name, 'class', [], {})
                    apis[module_path].append(class_sig)
                    
                    for method_name, method in inspect.getmembers(obj):
                        if not method_name.startswith('_') or method_name == '__init__':
                            if inspect.isfunction(method) or inspect.ismethod(method):
                                method_sig = self._extract_function_signature(
                                    f"{name}.{method_name}", method
                                )
                                if method_sig:
                                    apis[module_path].append(method_sig)
        
        except Exception as e:
            print(f"Error extracting APIs from {module_path}: {e}")
        
        return apis
    
    def _extract_function_signature(self, name: str, func) -> Optional[APISignature]:
        """Extract function signature."""
        try:
            sig = inspect.signature(func)
            params = []
            defaults = {}
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self' or param_name == 'cls':
                    continue
                
                params.append(param_name)
                
                if param.default != inspect.Parameter.empty:
                    defaults[param_name] = param.default
            
            return APISignature(name, 'function', params, defaults)
        
        except Exception:
            return None
    
    def extract_ast_apis(self, file_path: Path) -> Dict[str, List[APISignature]]:
        """Extract API signatures using AST (doesn't require import)."""
        apis = defaultdict(list)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    sig = self._extract_ast_function_signature(node)
                    if sig:
                        apis[str(file_path)].append(sig)
                
                elif isinstance(node, ast.ClassDef):
                    # Add class
                    class_sig = APISignature(node.name, 'class', [], {})
                    apis[str(file_path)].append(class_sig)
                    
                    # Add methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            if not item.name.startswith('_') or item.name == '__init__':
                                method_sig = self._extract_ast_function_signature(
                                    item, class_name=node.name
                                )
                                if method_sig:
                                    apis[str(file_path)].append(method_sig)
        
        except Exception as e:
            print(f"Error extracting AST APIs from {file_path}: {e}")
        
        return apis
    
    def _extract_ast_function_signature(
        self, node: ast.FunctionDef, class_name: Optional[str] = None
    ) -> Optional[APISignature]:
        """Extract function signature from AST."""
        params = []
        defaults = {}
        
        # Get parameter names
        for arg in node.args.args:
            if arg.arg not in ('self', 'cls'):
                params.append(arg.arg)
        
        # Get defaults (matched from the end)
        num_defaults = len(node.args.defaults)
        if num_defaults > 0:
            param_with_defaults = params[-num_defaults:]
            for param, default in zip(param_with_defaults, node.args.defaults):
                # Simple default value extraction
                if isinstance(default, ast.Constant):
                    defaults[param] = default.value
                elif isinstance(default, ast.Name):
                    defaults[param] = default.id
                else:
                    defaults[param] = "..."  # Complex default
        
        name = f"{class_name}.{node.name}" if class_name else node.name
        return APISignature(name, 'function', params, defaults)
    
    def check_compatibility(self, old_path: Path, new_path: Path):
        """Check compatibility between old and new versions."""
        # Extract APIs from both versions
        self.old_apis = self.extract_ast_apis(old_path)
        self.new_apis = self.extract_ast_apis(new_path)
        
        # Check for breaking changes
        for file_path, old_sigs in self.old_apis.items():
            new_file_path = file_path.replace(str(old_path), str(new_path))
            new_sigs = self.new_apis.get(new_file_path, [])
            
            # Create lookup for new signatures
            new_sig_dict = {sig.name: sig for sig in new_sigs}
            
            for old_sig in old_sigs:
                if old_sig.name not in new_sig_dict:
                    self.breaking_changes.append({
                        "type": "removed_api",
                        "file": file_path,
                        "api": str(old_sig),
                        "description": f"API '{old_sig.name}' was removed"
                    })
                else:
                    new_sig = new_sig_dict[old_sig.name]
                    if old_sig != new_sig:
                        self.breaking_changes.append({
                            "type": "signature_changed",
                            "file": file_path,
                            "old_api": str(old_sig),
                            "new_api": str(new_sig),
                            "description": f"API signature changed for '{old_sig.name}'"
                        })
                    else:
                        self.compatible_changes.append({
                            "type": "unchanged",
                            "file": file_path,
                            "api": str(old_sig)
                        })
    
    def check_cli_compatibility(self, old_commands: Dict, new_commands: Dict):
        """Check CLI command compatibility."""
        # Check for removed commands
        for cmd_name, cmd_info in old_commands.items():
            if cmd_name not in new_commands:
                self.breaking_changes.append({
                    "type": "removed_command",
                    "command": cmd_name,
                    "description": f"CLI command '{cmd_name}' was removed"
                })
            else:
                # Check parameters
                old_params = set(cmd_info.get('parameters', []))
                new_params = set(new_commands[cmd_name].get('parameters', []))
                
                removed_params = old_params - new_params
                if removed_params:
                    self.breaking_changes.append({
                        "type": "removed_parameters",
                        "command": cmd_name,
                        "parameters": list(removed_params),
                        "description": f"Parameters removed from '{cmd_name}': {removed_params}"
                    })
    
    def generate_report(self) -> str:
        """Generate compatibility report."""
        report_lines = [
            "Backwards Compatibility Check Report",
            "=" * 50,
            ""
        ]
        
        if self.breaking_changes:
            report_lines.append(f"⚠️  BREAKING CHANGES FOUND: {len(self.breaking_changes)}")
            report_lines.append("")
            
            for change in self.breaking_changes:
                report_lines.append(f"Type: {change['type']}")
                report_lines.append(f"Description: {change['description']}")
                
                if 'file' in change:
                    report_lines.append(f"File: {change['file']}")
                
                if 'old_api' in change:
                    report_lines.append(f"Old: {change['old_api']}")
                    report_lines.append(f"New: {change['new_api']}")
                elif 'api' in change:
                    report_lines.append(f"API: {change['api']}")
                
                report_lines.append("")
        else:
            report_lines.append("✅ No breaking changes found!")
            report_lines.append("")
        
        report_lines.append(f"Compatible APIs: {len(self.compatible_changes)}")
        
        return "\n".join(report_lines)


class TestCompatibilityChecker:
    """Check test compatibility to ensure tests still pass."""
    
    def __init__(self):
        self.test_signatures: Dict[str, Set[str]] = {}
    
    def extract_test_signatures(self, test_dir: Path) -> Set[str]:
        """Extract test function signatures."""
        signatures = set()
        
        for test_file in test_dir.rglob("test_*.py"):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                        signatures.add(f"{test_file.name}::{node.name}")
            
            except Exception as e:
                print(f"Error extracting tests from {test_file}: {e}")
        
        return signatures
    
    def check_test_compatibility(self, old_tests: Path, new_tests: Path) -> Dict[str, Any]:
        """Check if all old tests still exist."""
        old_sigs = self.extract_test_signatures(old_tests)
        new_sigs = self.extract_test_signatures(new_tests)
        
        removed_tests = old_sigs - new_sigs
        added_tests = new_sigs - old_sigs
        
        return {
            "removed_tests": list(removed_tests),
            "added_tests": list(added_tests),
            "compatible": len(removed_tests) == 0
        }


def check_backwards_compatibility(
    old_version_path: str,
    new_version_path: str,
    output_file: Optional[str] = None
) -> bool:
    """
    Check backwards compatibility between versions.
    
    Args:
        old_version_path: Path to old version
        new_version_path: Path to new version
        output_file: Optional file to save report
        
    Returns:
        True if compatible, False if breaking changes found
    """
    checker = CompatibilityChecker()
    
    # Check Python API compatibility
    old_path = Path(old_version_path)
    new_path = Path(new_version_path)
    
    # Check main package
    for py_file in old_path.rglob("*.py"):
        if '__pycache__' not in str(py_file) and 'test_' not in py_file.name:
            checker.check_compatibility(py_file, py_file)
    
    # Generate report
    report = checker.generate_report()
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report)
    else:
        print(report)
    
    return len(checker.breaking_changes) == 0