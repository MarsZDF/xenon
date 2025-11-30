#!/usr/bin/env python
"""
Performance benchmarks for Xenon XML repair library.

Run with: python benchmarks/run_benchmarks.py
Or with pytest-benchmark: pytest benchmarks/ --benchmark-only
"""

import time
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xenon import repair_xml, repair_xml_safe, parse_xml, repair_xml_with_report
from xenon.utils import batch_repair, validate_xml_structure


class BenchmarkRunner:
    """Simple benchmark runner without external dependencies."""

    def __init__(self):
        self.results = []

    def benchmark(self, name, func, *args, iterations=1000, **kwargs):
        """Run a benchmark."""
        # Warmup
        for _ in range(10):
            func(*args, **kwargs)

        # Measure
        start = time.perf_counter()
        for _ in range(iterations):
            func(*args, **kwargs)
        end = time.perf_counter()

        elapsed = (end - start) / iterations
        self.results.append({
            "name": name,
            "time_ms": elapsed * 1000,
            "iterations": iterations
        })

        return elapsed

    def print_results(self):
        """Print formatted benchmark results."""
        print("\n" + "=" * 80)
        print("Xenon Performance Benchmarks")
        print("=" * 80)
        print(f"{'Benchmark':<50} {'Time (ms)':<15} {'Iterations'}")
        print("-" * 80)

        for result in sorted(self.results, key=lambda x: x['time_ms']):
            print(f"{result['name']:<50} {result['time_ms']:>10.4f}      {result['iterations']:>8}")

        print("=" * 80)


# Test data
SMALL_TRUNCATED = '<root><item>Hello'
MEDIUM_TRUNCATED = '<root>' + '<item>data</item>' * 10 + '<item>incomplete'
LARGE_TRUNCATED = '<root>' + '<item>data</item>' * 100 + '<item>incomplete'

SMALL_WITH_ENTITIES = '<root>Tom & Jerry < > test</root>'
MEDIUM_WITH_ENTITIES = '<root>' + '<item>Tom & Jerry < ></item>' * 10 + '</root>'
LARGE_WITH_ENTITIES = '<root>' + '<item>Tom & Jerry < ></item>' * 100 + '</root>'

SMALL_MALFORMED_ATTRS = '<root><item name=value>test</item></root>'
MEDIUM_MALFORMED_ATTRS = '<root>' + '<item name=value>test</item>' * 10 + '</root>'
LARGE_MALFORMED_ATTRS = '<root>' + '<item name=value>test</item>' * 100 + '</root>'

SMALL_INVALID_TAGS = '<root><123invalid>data</123invalid></root>'
MEDIUM_INVALID_TAGS = '<root>' + '<123invalid>data</123invalid>' * 10 + '</root>'

WELL_FORMED = '<root><item>Hello World</item></root>'
COMPLEX_WELL_FORMED = '<root>' + '<item attr="value">data</item>' * 50 + '</root>'

MULTIPLE_ISSUES = '<root><item name=unquoted>Tom & Jerry<123bad>test'

BATCH_SMALL = ['<root><item>Hello' for _ in range(10)]
BATCH_MEDIUM = ['<root><item>Hello' for _ in range(100)]


def main():
    """Run all benchmarks."""
    runner = BenchmarkRunner()

    # Category 1: Basic Repair Operations
    print("\nRunning basic repair benchmarks...")
    runner.benchmark("repair_xml() - Small truncated", repair_xml, SMALL_TRUNCATED)
    runner.benchmark("repair_xml() - Medium truncated", repair_xml, MEDIUM_TRUNCATED)
    runner.benchmark("repair_xml() - Large truncated", repair_xml, LARGE_TRUNCATED)

    # Category 2: Entity Escaping
    print("Running entity escaping benchmarks...")
    runner.benchmark("repair_xml() - Small with entities", repair_xml, SMALL_WITH_ENTITIES)
    runner.benchmark("repair_xml() - Medium with entities", repair_xml, MEDIUM_WITH_ENTITIES)
    runner.benchmark("repair_xml() - Large with entities", repair_xml, LARGE_WITH_ENTITIES)

    # Category 3: Attribute Repair
    print("Running attribute repair benchmarks...")
    runner.benchmark("repair_xml() - Small malformed attrs", repair_xml, SMALL_MALFORMED_ATTRS)
    runner.benchmark("repair_xml() - Medium malformed attrs", repair_xml, MEDIUM_MALFORMED_ATTRS)
    runner.benchmark("repair_xml() - Large malformed attrs", repair_xml, LARGE_MALFORMED_ATTRS)

    # Category 4: Tag Name Sanitization
    print("Running tag sanitization benchmarks...")
    runner.benchmark("repair_xml_safe() - Small invalid tags",
                    repair_xml_safe, SMALL_INVALID_TAGS, sanitize_invalid_tags=True)
    runner.benchmark("repair_xml_safe() - Medium invalid tags",
                    repair_xml_safe, MEDIUM_INVALID_TAGS, sanitize_invalid_tags=True)

    # Category 5: Well-Formed XML (No Repairs Needed)
    print("Running well-formed XML benchmarks...")
    runner.benchmark("repair_xml() - Well-formed (noop)", repair_xml, WELL_FORMED)
    runner.benchmark("repair_xml() - Complex well-formed", repair_xml, COMPLEX_WELL_FORMED)

    # Category 6: Multiple Issues
    print("Running complex repair benchmarks...")
    runner.benchmark("repair_xml() - Multiple issues", repair_xml, MULTIPLE_ISSUES)

    # Category 7: Advanced Functions
    print("Running advanced function benchmarks...")
    runner.benchmark("repair_xml_with_report() - Small", repair_xml_with_report, SMALL_TRUNCATED)
    runner.benchmark("parse_xml() - Well-formed", parse_xml, WELL_FORMED)
    runner.benchmark("validate_xml_structure() - Well-formed", validate_xml_structure, WELL_FORMED)

    # Category 8: Batch Operations
    print("Running batch operation benchmarks...")
    runner.benchmark("batch_repair() - 10 items", batch_repair, BATCH_SMALL, iterations=100)
    runner.benchmark("batch_repair() - 100 items", batch_repair, BATCH_MEDIUM, iterations=10)

    # Category 9: Safe vs. Regular
    print("Running safe vs regular benchmarks...")
    runner.benchmark("repair_xml() - Small", repair_xml, SMALL_TRUNCATED)
    runner.benchmark("repair_xml_safe() - Small", repair_xml_safe, SMALL_TRUNCATED)

    # Print results
    runner.print_results()

    # Performance targets
    print("\n" + "=" * 80)
    print("Performance Targets (all times in milliseconds)")
    print("=" * 80)
    print("✓ Small XML (<100 chars):     < 0.1 ms")
    print("✓ Medium XML (~500 chars):    < 0.5 ms")
    print("✓ Large XML (~5000 chars):    < 2.0 ms")
    print("✓ Well-formed (noop):         < 0.05 ms")
    print("=" * 80)

    # Check if we meet targets
    small_time = next(r['time_ms'] for r in runner.results if 'Small truncated' in r['name'])
    medium_time = next(r['time_ms'] for r in runner.results if 'Medium truncated' in r['name'])
    large_time = next(r['time_ms'] for r in runner.results if 'Large truncated' in r['name'])
    noop_time = next(r['time_ms'] for r in runner.results if 'Well-formed (noop)' in r['name'])

    targets_met = all([
        small_time < 0.1,
        medium_time < 0.5,
        large_time < 2.0,
        noop_time < 0.05
    ])

    if targets_met:
        print("\n✅ All performance targets met!")
    else:
        print("\n⚠️  Some performance targets not met:")
        if small_time >= 0.1:
            print(f"   Small XML: {small_time:.4f} ms (target: < 0.1 ms)")
        if medium_time >= 0.5:
            print(f"   Medium XML: {medium_time:.4f} ms (target: < 0.5 ms)")
        if large_time >= 2.0:
            print(f"   Large XML: {large_time:.4f} ms (target: < 2.0 ms)")
        if noop_time >= 0.05:
            print(f"   Well-formed: {noop_time:.4f} ms (target: < 0.05 ms)")

    print()


if __name__ == "__main__":
    main()
