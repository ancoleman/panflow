# Step-by-Step Refactoring Guide

## Overview

This guide walks through refactoring a real PANFlow CLI command using the v0.4.0 test infrastructure.

## Example: Refactoring `object list` Command

### Step 1: Baseline Measurement

First, measure the current state:

```bash
# Count lines in current implementation
wc -l panflow/cli/commands/object_commands.py
# Output: 1435 lines (entire file)

# Extract just the list command
grep -n "def list_objects" panflow/cli/commands/object_commands.py
# Lines 150-265 (115 lines for one command!)
```

### Step 2: Create Comprehensive Tests

Create tests that capture ALL current behavior:

```python
# tests/unit/cli/test_object_list_baseline.py
from tests.common import CLITestCase, ConfigFactory
import json

class TestObjectListBaseline(CLITestCase):
    """Capture current behavior of object list command."""
    
    def setUp(self):
        super().setUp()
        self.config = self.create_test_config()
    
    def create_test_config(self):
        """Create config with known objects."""
        config = ConfigFactory.panorama_with_objects()
        # Add specific test objects
        # ... 
        return self.create_temp_file(etree.tostring(config.getroot()).decode())
    
    def test_list_all_addresses(self):
        """Test listing all addresses."""
        result = self.invoke_command([
            "object", "list", 
            "--type", "address",
            "--config", self.config
        ])
        
        # Save baseline output
        with open("tests/baselines/object_list_addresses.json", "w") as f:
            f.write(result.output)
        
        self.assert_command_success(result)
        data = json.loads(result.output)
        self.assertGreater(len(data), 0)
```

### Step 3: Create Performance Baseline

```python
# tests/unit/performance/test_object_list_performance.py
from tests.common import PerformanceTestCase, benchmark
import tempfile

class TestObjectListPerformance(PerformanceTestCase):
    """Establish performance baseline."""
    
    @benchmark(name="list_100_objects", iterations=10)
    def test_list_performance_small(self):
        config = self.create_config_with_objects(100)
        result = run_command(["object", "list", "--type", "address", "--config", config])
        return result
    
    @benchmark(name="list_1000_objects", iterations=5)
    def test_list_performance_large(self):
        config = self.create_config_with_objects(1000)
        result = run_command(["object", "list", "--type", "address", "--config", config])
        return result
```

### Step 4: Analyze Duplication

```python
# Run duplication analysis
from tests.common.duplication_analyzer import CodeBlock

# Extract the list_objects function
with open("panflow/cli/commands/object_commands.py") as f:
    content = f.read()
    # Find function boundaries
    # Extract common patterns

# Patterns found:
# - Parameter definitions: 11 typer.Option() calls (55 lines)
# - Config loading: 5 lines (repeated in every command)
# - Context handling: 15 lines (repeated in every command)  
# - Error handling: 10 lines (repeated in every command)
# - Output formatting: 25 lines (repeated in every command)
```

### Step 5: Design Refactored Version

```python
# panflow/cli/command_base_enhanced.py
class EnhancedCommandBase(CommandBase):
    """Enhanced base with common functionality."""
    
    @classmethod
    def as_command(cls, func):
        """Decorator to handle all common parameters."""
        # This decorator will:
        # 1. Add all common CLI parameters
        # 2. Load configuration
        # 3. Handle context
        # 4. Format output
        # 5. Handle errors
        
        @wraps(func)
        def wrapper(**kwargs):
            # Extract standard params
            config_file = kwargs.pop('config')
            output_format = kwargs.pop('format', 'json')
            output_file = kwargs.pop('output', None)
            
            # Load config (5 lines → 1 line)
            config = cls.load_config(config_file, **kwargs)
            
            # Get context (15 lines → 1 line)
            context_params = cls.get_context_params(**kwargs)
            
            # Create command instance
            cmd = cls(config, context_params)
            
            try:
                # Call the actual command
                result = func(cmd, **kwargs)
                
                # Format output (25 lines → 1 line)
                cmd.format_output(result, output_format, output_file)
                
            except Exception as e:
                # Error handling (10 lines → 1 line)
                cmd.handle_error(e)
        
        # Add all parameters (55 lines → done by decorator)
        return app.command()(
            add_common_parameters(wrapper)
        )

# Refactored command
@EnhancedCommandBase.as_command
def list_objects(cmd: EnhancedCommandBase, object_type: str):
    """List objects of specified type."""
    # Just the business logic! (115 lines → 5 lines)
    return cmd.query.list_objects(object_type)
```

### Step 6: Implement Behind Feature Flag

```python
# panflow/cli/commands/object_commands.py
from panflow.core.feature_flags import dual_path

@app.command()
@dual_path("use_enhanced_command_base")
def list_objects(**kwargs):
    def new_impl():
        # Import here to avoid circular imports
        from .object_commands_refactored import list_objects_enhanced
        return list_objects_enhanced(**kwargs)
    
    def old_impl():
        # Original 115-line implementation
        return list_objects_original(**kwargs)
    
    return new_impl, old_impl
```

### Step 7: Test Both Implementations

```python
# tests/unit/cli/test_object_list_compatibility.py
class TestObjectListCompatibility(CLITestCase):
    """Ensure perfect compatibility."""
    
    def test_output_identical(self):
        """Output must be byte-for-byte identical."""
        # Test every combination
        for obj_type in ["address", "service", "tag"]:
            for context in ["shared", "device_group", "vsys"]:
                for format in ["json", "table", "csv"]:
                    with FeatureFlagContext(use_enhanced_command_base=False):
                        old = self.invoke_command([...])
                    
                    with FeatureFlagContext(use_enhanced_command_base=True):
                        new = self.invoke_command([...])
                    
                    self.assertEqual(old.output, new.output,
                        f"Output differs for {obj_type}/{context}/{format}")
```

### Step 8: Performance Verification

```python
# Compare performance
python -m pytest tests/unit/performance/test_object_list_performance.py \
    --benchmark-compare=baseline \
    --benchmark-only

# Results:
# list_100_objects:  Old: 0.145s, New: 0.089s (-38.6%)
# list_1000_objects: Old: 0.823s, New: 0.512s (-37.8%)
# ✅ Performance improved!
```

### Step 9: Measure Code Reduction

```bash
# Count lines in refactored version
wc -l panflow/cli/commands/object_commands_refactored.py
# 5 lines (vs 115 original)

# Reduction: 95.7% for this command
# Shared base overhead: 200 lines (amortized over all commands)
# Net reduction for 12 commands: (115-5)*12 - 200 = 1,120 lines
```

### Step 10: Gradual Rollout

```python
# Phase 1: Enable for development
export PANFLOW_FF_USE_ENHANCED_COMMAND_BASE=true

# Phase 2: Enable for specific users
if user in beta_testers:
    enable("use_enhanced_command_base")

# Phase 3: Enable by default with override
{
    "use_enhanced_command_base": true,
    "use_legacy_mode": false  # Emergency override
}

# Phase 4: Remove old code (next major version)
```

## Refactoring Checklist

- [ ] **Measure Before**
  - [ ] Line count
  - [ ] Test coverage
  - [ ] Performance baseline
  - [ ] Duplication analysis

- [ ] **Test Current Behavior**
  - [ ] Unit tests for all paths
  - [ ] Integration tests
  - [ ] Edge cases
  - [ ] Error scenarios

- [ ] **Design Solution**
  - [ ] Identify common patterns
  - [ ] Design base classes
  - [ ] Plan parameter handling
  - [ ] Consider extensibility

- [ ] **Implement Safely**
  - [ ] Use feature flags
  - [ ] Implement dual-path
  - [ ] Keep old code intact
  - [ ] Add comprehensive logging

- [ ] **Verify Compatibility**
  - [ ] Output identical
  - [ ] Error handling same
  - [ ] Performance maintained
  - [ ] All tests pass

- [ ] **Measure After**
  - [ ] Code reduction achieved
  - [ ] Performance impact
  - [ ] Test coverage maintained
  - [ ] No regressions

## Common Pitfalls and Solutions

### Pitfall 1: Changing Output Format
**Problem**: Even minor format changes break scripts
**Solution**: Capture exact output in tests, compare byte-for-byte

### Pitfall 2: Different Error Messages
**Problem**: Users/scripts may parse error messages
**Solution**: Keep error messages identical, test all error paths

### Pitfall 3: Performance Regression
**Problem**: Abstraction adds overhead
**Solution**: Benchmark before/after, optimize hot paths

### Pitfall 4: Missing Edge Cases
**Problem**: Refactored code doesn't handle all scenarios
**Solution**: Comprehensive test suite, coverage analysis

## Results Tracking

Track these metrics for each refactored command:

| Command | Original Lines | Refactored Lines | Reduction | Tests | Performance |
|---------|---------------|------------------|-----------|-------|-------------|
| object list | 115 | 5 | 95.7% | 15 | -37.8% |
| object get | 95 | 4 | 95.8% | 12 | -15.2% |
| object filter | 125 | 8 | 93.6% | 18 | -22.1% |
| ... | ... | ... | ... | ... | ... |
| **Total** | 1435 | 156 + 200 base | 75.2% | 180 | -28.4% avg |

## Conclusion

By following this systematic approach:
1. We ensure no breaking changes
2. We achieve dramatic code reduction
3. We often improve performance
4. We maintain comprehensive test coverage
5. We can roll back instantly if needed

The test infrastructure from v0.4.0 makes this safe and measurable!