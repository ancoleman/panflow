# Using the Test Suite for Safe Refactoring

## Overview

The test infrastructure from v0.4.0 provides a safety net for refactoring. This guide shows how to use these tools effectively during the refactoring process.

## Refactoring Workflow

### 1. Measure Before You Change

Before refactoring any code, establish baselines:

```bash
# Analyze current duplication
python -m tests.common.duplication_analyzer analyze_duplication panflow/ --output baseline_duplication.txt

# Run performance benchmarks
python -m pytest tests/unit/ -v -k "performance" --benchmark-save=baseline

# Check current test coverage
poetry run pytest --cov=panflow --cov-report=html
```

### 2. Use Feature Flags for Safe Changes

When implementing new patterns, use feature flags:

```python
# In your refactored code
from panflow.core.feature_flags import feature_flag, dual_path

@dual_path("use_enhanced_command_base")
def load_config(config_file: str):
    def new_impl():
        # New, cleaner implementation
        return EnhancedConfigLoader(config_file).load()
    
    def old_impl():
        # Original implementation
        return PANFlowConfig(config_file=config_file)
    
    return new_impl, old_impl
```

### 3. Write Tests Using Common Utilities

Before refactoring, ensure comprehensive test coverage:

```python
# tests/unit/cli/test_object_commands_refactored.py
from tests.common import CLITestCase, MockFactory, ObjectFactory

class TestObjectCommandsRefactored(CLITestCase):
    """Test refactored object commands maintain compatibility."""
    
    def setUp(self):
        super().setUp()
        # Use factory to create consistent test data
        self.test_addresses = [
            ObjectFactory.address_element(name=f"addr-{i}", ip_netmask=f"10.0.{i}.1/32")
            for i in range(5)
        ]
    
    def test_list_command_compatibility(self):
        """Ensure refactored list command produces same output."""
        # Test with old implementation
        with FeatureFlagContext(use_enhanced_command_base=False):
            old_result = self.invoke_command(["object", "list", "--type", "address"])
        
        # Test with new implementation
        with FeatureFlagContext(use_enhanced_command_base=True):
            new_result = self.invoke_command(["object", "list", "--type", "address"])
        
        # Results should be identical
        self.assertEqual(old_result.output, new_result.output)
```

### 4. Track Performance Impact

Use benchmarking to ensure refactoring doesn't degrade performance:

```python
# tests/unit/performance/test_refactoring_performance.py
from tests.common import PerformanceTestCase, track_performance

@track_performance("tests/performance_baselines/cli_commands.json")
class TestCLIPerformance(PerformanceTestCase):
    """Track CLI command performance during refactoring."""
    
    def test_object_list_performance(self):
        """Benchmark object list command."""
        # This will automatically track execution time
        config = self.create_large_config(1000)  # 1000 objects
        
        result, exec_time = self.measure_performance(
            run_cli_command,
            ["object", "list", "--config", config, "--type", "address"]
        )
        
        # Assert performance hasn't degraded
        self.assert_performance(exec_time, max_time=2.0)  # 2 second max
```

### 5. Verify API Compatibility

Check that refactoring doesn't break APIs:

```python
# Run compatibility check
from tests.common.compatibility_checker import check_backwards_compatibility

# Before merging refactored code
is_compatible = check_backwards_compatibility(
    "panflow/cli/commands/object_commands.py",  # old
    "panflow/cli/commands/object_commands_refactored.py",  # new
    "compatibility_report.txt"
)

assert is_compatible, "Breaking changes detected!"
```

## Practical Refactoring Example

Let's refactor a typical CLI command using our tools:

### Step 1: Analyze Current Implementation

```python
# First, let's analyze the current duplication in object_commands.py
from tests.common.duplication_analyzer import PatternAnalyzer

analyzer = PatternAnalyzer()
analyzer.analyze_file("panflow/cli/commands/object_commands.py")
print(analyzer.generate_report())

# Output shows:
# typer_option: 47 occurrences
# try_except: 12 occurrences
# config_load: 12 occurrences
# context_kwargs: 12 occurrences
```

### Step 2: Create Tests for Current Behavior

```python
# tests/unit/cli/test_object_get_refactoring.py
from tests.common import CLITestCase, ConfigFactory
import json

class TestObjectGetRefactoring(CLITestCase):
    """Ensure object get behavior is preserved during refactoring."""
    
    def setUp(self):
        super().setUp()
        # Create a config with known objects
        self.config_with_objects = self.create_config_with_test_objects()
    
    def create_config_with_test_objects(self):
        """Create a test configuration with known objects."""
        config = ConfigFactory.panorama_with_objects()
        # Save to temp file
        config_file = self.create_temp_file(etree.tostring(config.getroot()).decode())
        return config_file
    
    def test_get_existing_object(self):
        """Test getting an object that exists."""
        result = self.invoke_command([
            "object", "get",
            "--type", "address",
            "--name", "shared-server"
        ])
        
        self.assert_command_success(result)
        data = json.loads(result.output)
        self.assertEqual(data["name"], "shared-server")
        self.assertEqual(data["ip-netmask"], "10.0.0.1/32")
    
    def test_get_nonexistent_object(self):
        """Test getting an object that doesn't exist."""
        result = self.invoke_command([
            "object", "get",
            "--type", "address",
            "--name", "nonexistent"
        ])
        
        self.assert_command_error(result)
        self.assert_output_contains(result, "not found")
    
    def test_output_formats(self):
        """Test all output formats work correctly."""
        for format in ["json", "yaml", "table", "csv"]:
            result = self.invoke_command([
                "object", "get",
                "--type", "address",
                "--name", "shared-server",
                "--format", format
            ])
            self.assert_command_success(result)
```

### Step 3: Implement Refactored Version

```python
# panflow/cli/commands/object_commands_refactored.py
from panflow.cli.command_base import standard_command, CommandBase

@app.command()
@standard_command
class GetObject(CommandBase):
    """Get a specific object from the configuration."""
    
    def execute(self, object_type: str, name: str) -> dict:
        """Execute the get operation."""
        obj = self.query.get_object(object_type, name)
        
        if not obj:
            self.error(f"Object not found: {name} (type: {object_type})")
        
        return obj.to_dict()
```

### Step 4: Performance Comparison

```python
# tests/unit/performance/test_get_command_performance.py
from tests.common import benchmark

class TestGetCommandPerformance:
    """Compare performance of old vs new implementation."""
    
    @benchmark(name="get_object_old", iterations=100)
    def test_old_implementation(self, large_config):
        with FeatureFlagContext(use_enhanced_command_base=False):
            run_command(["object", "get", "--type", "address", "--name", "test-1"])
    
    @benchmark(name="get_object_new", iterations=100)
    def test_new_implementation(self, large_config):
        with FeatureFlagContext(use_enhanced_command_base=True):
            run_command(["object", "get", "--type", "address", "--name", "test-1"])
```

### Step 5: Gradual Rollout

```python
# Enable for testing
export PANFLOW_FF_USE_ENHANCED_COMMAND_BASE=true

# Run all tests to verify
poetry run pytest tests/unit/cli/ -v

# Check performance
poetry run pytest tests/unit/performance/ -v --benchmark-compare=baseline

# If all good, enable by default in next release
```

## Measuring Refactoring Success

### 1. Code Reduction Metrics

```python
# Track code reduction after each refactoring
from tests.common.duplication_analyzer import analyze_duplication

# Before
before_stats = analyze_duplication("panflow/cli/commands/")
print(f"Before: {before_stats['total_lines']} lines, {before_stats['duplication_percentage']:.1f}% duplication")

# After refactoring
after_stats = analyze_duplication("panflow/cli/commands/")
print(f"After: {after_stats['total_lines']} lines, {after_stats['duplication_percentage']:.1f}% duplication")
print(f"Reduction: {(1 - after_stats['total_lines']/before_stats['total_lines'])*100:.1f}%")
```

### 2. Test Coverage Tracking

```bash
# Ensure coverage doesn't drop during refactoring
poetry run pytest --cov=panflow --cov-report=term-missing

# Save coverage for comparison
poetry run pytest --cov=panflow --cov-report=json --cov-report=term
mv coverage.json coverage_before_refactoring.json

# After refactoring, compare
poetry run pytest --cov=panflow --cov-report=json
python -m coverage_diff coverage_before_refactoring.json coverage.json
```

### 3. Performance Regression Detection

```python
# Automated performance regression detection
from tests.common.benchmarks import PerformanceBaseline

baseline = PerformanceBaseline()
regressions = baseline.check_all_regressions()

if regressions:
    print(f"⚠️ Performance regressions detected: {regressions}")
    # Don't merge until resolved
```

## Refactoring Checklist

For each refactoring task:

- [ ] Measure current code duplication
- [ ] Write comprehensive tests for current behavior
- [ ] Establish performance baselines
- [ ] Implement refactored version behind feature flag
- [ ] Run all tests with both old and new implementations
- [ ] Compare performance metrics
- [ ] Check API compatibility
- [ ] Run duplication analysis on refactored code
- [ ] Update documentation
- [ ] Plan gradual rollout strategy

## Common Refactoring Patterns

### 1. Consolidating CLI Parameters

```python
# Before: Repeated in every command
def list_objects(
    config: str = typer.Option(...),
    device_type: str = typer.Option(None),
    context: str = typer.Option("shared"),
    device_group: Optional[str] = typer.Option(None),
    vsys: str = typer.Option("vsys1"),
    format: str = typer.Option("json"),
    # ... more repeated options
):
    # Repeated setup code
    try:
        xml_config = PANFlowConfig(config_file=config)
        # ... repeated context handling
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")

# After: Using base class
@standard_command
def list_objects(self, object_type: str):
    # All common parameters handled by decorator
    return self.query.list_objects(object_type)
```

### 2. Extracting Common Patterns

```python
# Identify patterns using analyzer
patterns = PatternAnalyzer()
patterns.analyze_directory("panflow/cli/commands/")

# Extract to base class
class BulkOperationCommand(CommandBase):
    """Base for all bulk operations."""
    
    def select_items(self, criteria, query_filter):
        """Common selection logic."""
        # Extracted from multiple commands
```

### 3. Consolidating Error Handling

```python
# Before: Scattered try/except blocks
try:
    # operation
except Exception as e:
    logger.error(f"Error: {e}")
    console.print(f"[red]Error:[/red] {str(e)}")
    raise typer.Exit(1)

# After: Centralized in decorator
@command_error_handler
def operation(self):
    # Just the business logic
    return self.do_operation()
```

## Conclusion

The test suite provides comprehensive safety nets for refactoring:

1. **Fixtures & Factories** - Consistent test data
2. **Base Classes** - Reduced test duplication
3. **Performance Tracking** - Prevent regressions
4. **Feature Flags** - Safe rollout
5. **Compatibility Checking** - No breaking changes
6. **Duplication Analysis** - Measure progress

By following this workflow, we can confidently refactor the codebase while maintaining stability and measuring our progress toward the 40% code reduction goal.