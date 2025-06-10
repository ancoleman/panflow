"""
Performance benchmarking utilities for PANFlow tests.

This module provides tools for measuring and tracking performance
to ensure refactoring doesn't introduce performance regressions.
"""

import time
import functools
import statistics
from typing import Callable, Dict, List, Any, Optional, Tuple
from pathlib import Path
import json
import os


class PerformanceBenchmark:
    """Class for tracking performance benchmarks."""
    
    def __init__(self, name: str, baseline_file: Optional[str] = None):
        """
        Initialize a performance benchmark.
        
        Args:
            name: Name of the benchmark suite
            baseline_file: Path to baseline performance data
        """
        self.name = name
        self.results: Dict[str, List[float]] = {}
        self.baseline_file = baseline_file
        self.baseline_data: Dict[str, Dict[str, float]] = {}
        
        if baseline_file and Path(baseline_file).exists():
            self.load_baseline()
    
    def load_baseline(self):
        """Load baseline performance data."""
        with open(self.baseline_file, 'r') as f:
            self.baseline_data = json.load(f)
    
    def save_baseline(self):
        """Save current results as baseline."""
        if not self.baseline_file:
            return
        
        baseline = {}
        for test_name, times in self.results.items():
            baseline[test_name] = {
                "mean": statistics.mean(times),
                "median": statistics.median(times),
                "stdev": statistics.stdev(times) if len(times) > 1 else 0,
                "min": min(times),
                "max": max(times),
                "samples": len(times)
            }
        
        os.makedirs(os.path.dirname(self.baseline_file), exist_ok=True)
        with open(self.baseline_file, 'w') as f:
            json.dump(baseline, f, indent=2)
    
    def measure(self, test_name: str, func: Callable, *args, **kwargs) -> Tuple[Any, float]:
        """
        Measure the execution time of a function.
        
        Args:
            test_name: Name of the test
            func: Function to measure
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Tuple of (result, execution_time)
        """
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        
        execution_time = end - start
        
        if test_name not in self.results:
            self.results[test_name] = []
        self.results[test_name].append(execution_time)
        
        return result, execution_time
    
    def measure_repeated(
        self,
        test_name: str,
        func: Callable,
        iterations: int = 10,
        warmup: int = 2,
        *args,
        **kwargs
    ) -> Dict[str, float]:
        """
        Measure a function multiple times for statistical accuracy.
        
        Args:
            test_name: Name of the test
            func: Function to measure
            iterations: Number of measurements to take
            warmup: Number of warmup iterations
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Dictionary with statistical measurements
        """
        # Warmup iterations
        for _ in range(warmup):
            func(*args, **kwargs)
        
        # Actual measurements
        times = []
        for _ in range(iterations):
            _, exec_time = self.measure(test_name, func, *args, **kwargs)
            times.append(exec_time)
        
        return {
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0,
            "min": min(times),
            "max": max(times),
            "iterations": iterations
        }
    
    def compare_to_baseline(self, test_name: str) -> Optional[Dict[str, Any]]:
        """
        Compare current results to baseline.
        
        Args:
            test_name: Name of the test to compare
            
        Returns:
            Comparison results or None if no baseline
        """
        if test_name not in self.results or test_name not in self.baseline_data:
            return None
        
        current_times = self.results[test_name]
        baseline = self.baseline_data[test_name]
        
        current_mean = statistics.mean(current_times)
        baseline_mean = baseline["mean"]
        
        return {
            "current_mean": current_mean,
            "baseline_mean": baseline_mean,
            "difference": current_mean - baseline_mean,
            "percent_change": ((current_mean - baseline_mean) / baseline_mean) * 100,
            "regression": current_mean > baseline_mean * 1.1,  # 10% threshold
            "improvement": current_mean < baseline_mean * 0.9
        }
    
    def generate_report(self) -> str:
        """Generate a performance report."""
        report_lines = [
            f"Performance Benchmark Report: {self.name}",
            "=" * 50,
            ""
        ]
        
        for test_name, times in self.results.items():
            report_lines.append(f"Test: {test_name}")
            report_lines.append(f"  Samples: {len(times)}")
            report_lines.append(f"  Mean: {statistics.mean(times):.4f}s")
            report_lines.append(f"  Median: {statistics.median(times):.4f}s")
            if len(times) > 1:
                report_lines.append(f"  Std Dev: {statistics.stdev(times):.4f}s")
            report_lines.append(f"  Min: {min(times):.4f}s")
            report_lines.append(f"  Max: {max(times):.4f}s")
            
            # Compare to baseline if available
            comparison = self.compare_to_baseline(test_name)
            if comparison:
                report_lines.append("  Baseline Comparison:")
                report_lines.append(f"    Baseline: {comparison['baseline_mean']:.4f}s")
                report_lines.append(f"    Change: {comparison['percent_change']:+.1f}%")
                if comparison['regression']:
                    report_lines.append("    ⚠️  PERFORMANCE REGRESSION DETECTED")
                elif comparison['improvement']:
                    report_lines.append("    ✅ Performance improved")
            
            report_lines.append("")
        
        return "\n".join(report_lines)


def benchmark(name: Optional[str] = None, iterations: int = 1):
    """
    Decorator for benchmarking functions.
    
    Args:
        name: Optional name for the benchmark
        iterations: Number of times to run the function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            test_name = name or func.__name__
            
            # Get or create benchmark instance
            benchmark_instance = getattr(
                wrapper, '_benchmark',
                PerformanceBenchmark(test_name)
            )
            
            if iterations > 1:
                stats = benchmark_instance.measure_repeated(
                    test_name, func, iterations, 0, *args, **kwargs
                )
                result = func(*args, **kwargs)  # Run once more for the result
                
                # Print summary
                print(f"\nBenchmark: {test_name}")
                print(f"  Mean: {stats['mean']:.4f}s")
                print(f"  Median: {stats['median']:.4f}s")
                
                return result
            else:
                result, exec_time = benchmark_instance.measure(
                    test_name, func, *args, **kwargs
                )
                print(f"\nBenchmark: {test_name} - {exec_time:.4f}s")
                return result
        
        wrapper._benchmark = PerformanceBenchmark(name or func.__name__)
        return wrapper
    
    return decorator


def track_performance(baseline_file: str):
    """
    Class decorator for tracking performance of test methods.
    
    Args:
        baseline_file: Path to baseline performance data
    """
    def decorator(cls):
        original_setUp = cls.setUp
        original_tearDown = cls.tearDown
        
        def new_setUp(self):
            self._benchmark = PerformanceBenchmark(cls.__name__, baseline_file)
            if hasattr(original_setUp, '__func__'):
                original_setUp(self)
        
        def new_tearDown(self):
            # Generate and print report
            report = self._benchmark.generate_report()
            print("\n" + report)
            
            # Check for regressions
            regressions = []
            for test_name in self._benchmark.results:
                comparison = self._benchmark.compare_to_baseline(test_name)
                if comparison and comparison['regression']:
                    regressions.append(test_name)
            
            if regressions:
                print(f"\n⚠️  Performance regressions detected in: {', '.join(regressions)}")
            
            if hasattr(original_tearDown, '__func__'):
                original_tearDown(self)
        
        cls.setUp = new_setUp
        cls.tearDown = new_tearDown
        
        # Wrap test methods
        for attr_name in dir(cls):
            if attr_name.startswith('test_'):
                attr = getattr(cls, attr_name)
                if callable(attr):
                    wrapped = performance_wrapper(attr)
                    setattr(cls, attr_name, wrapped)
        
        return cls
    
    def performance_wrapper(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            return self._benchmark.measure(
                method.__name__, method, self, *args, **kwargs
            )[0]
        return wrapper
    
    return decorator


# Utility functions for common performance scenarios
def measure_import_time(module_name: str) -> float:
    """Measure the import time of a module."""
    import importlib
    import sys
    
    # Remove from sys.modules if already imported
    if module_name in sys.modules:
        del sys.modules[module_name]
    
    start = time.perf_counter()
    importlib.import_module(module_name)
    end = time.perf_counter()
    
    return end - start


def measure_memory_usage(func: Callable, *args, **kwargs) -> Tuple[Any, Dict[str, float]]:
    """
    Measure memory usage of a function.
    
    Note: Requires psutil to be installed.
    """
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Get initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run function
        result = func(*args, **kwargs)
        
        # Get final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        return result, {
            "initial_mb": initial_memory,
            "final_mb": final_memory,
            "used_mb": final_memory - initial_memory
        }
    except ImportError:
        # psutil not available
        result = func(*args, **kwargs)
        return result, {"error": "psutil not installed"}


class PerformanceBaseline:
    """Manage performance baselines for the entire test suite."""
    
    def __init__(self, baseline_dir: str = "tests/performance_baselines"):
        """Initialize baseline manager."""
        self.baseline_dir = Path(baseline_dir)
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
    
    def get_baseline_file(self, test_name: str) -> str:
        """Get the baseline file path for a test."""
        return str(self.baseline_dir / f"{test_name}.json")
    
    def update_all_baselines(self):
        """Update all baseline files with current performance data."""
        # This would be called after confirming performance is acceptable
        pass
    
    def check_all_regressions(self) -> List[str]:
        """Check all tests for performance regressions."""
        regressions = []
        
        for baseline_file in self.baseline_dir.glob("*.json"):
            test_name = baseline_file.stem
            # Load and check each baseline
            # Add to regressions if threshold exceeded
        
        return regressions