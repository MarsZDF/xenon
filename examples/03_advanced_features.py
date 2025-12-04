#!/usr/bin/env python
"""
Advanced Features Examples for Xenon XML Repair Library

This script demonstrates advanced features like reporting, batch processing,
encoding detection, and security features.
"""

from xenon import (
    repair_xml_with_report,
    repair_xml_safe,
    XMLRepairEngine,
    XMLRepairConfig,
    SecurityFlags,
    RepairFlags,
)
from xenon.utils import (
    batch_repair_with_reports,
    validate_xml_structure,
    extract_text_content,
    detect_encoding,
)

print("=" * 80)
print("Xenon Advanced Features Examples")
print("=" * 80)

# Example 1: Detailed Repair Reporting
print("\n1. Detailed Repair Reporting")
print("-" * 40)

xml = "<root><user name=Alice>Tom & Jerry<item>unclosed"
print(f"Input: {xml}")

repaired, report = repair_xml_with_report(xml)
print(f"Output: {repaired}\n")
print(report.summary())
print(f"\nStatistics: {report.statistics()}")

# Example 2: Configuration Objects for Cleaner Code
print("\n2. Using Configuration Objects")
print("-" * 40)

# Old way (still supported)
engine_old = XMLRepairEngine(
    strip_dangerous_pis=True,
    strip_external_entities=True,
    sanitize_invalid_tags=True,
)

# New way (recommended)
config = XMLRepairConfig(
    security=SecurityFlags.STRIP_DANGEROUS_PIS | SecurityFlags.STRIP_EXTERNAL_ENTITIES,
    repair=RepairFlags.SANITIZE_INVALID_TAGS,
)
engine_new = XMLRepairEngine(config)

test_xml = '<123invalid><?php echo "test"; ?><data>content</data></123invalid>'
print(f"Input: {test_xml}")
result = engine_new.repair_xml(test_xml)
print(f"Output: {result}")

# Example 3: Security Features
print("\n3. Security Features")
print("-" * 40)

dangerous_xml = """
<?php system('rm -rf /'); ?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<data>
    <script>alert('xss')</script>
    <iframe src="malicious.com"></iframe>
    <user>&xxe;</user>
</data>
"""

print("Input contains: <?php>, DOCTYPE with SYSTEM entity, <script>, <iframe>")

safe_result = repair_xml_safe(
    dangerous_xml,
    strip_dangerous_pis=True,
    strip_external_entities=True,
    strip_dangerous_tags=True,
)

print(f"Sanitized output: {safe_result}")

# Example 4: Batch Processing with Reports
print("\n4. Batch Processing with Detailed Reports")
print("-" * 40)

xml_batch = [
    "<root>valid</root>",  # No repairs needed
    "<root><item>incomplete",  # Needs repair
    "<user name=unquoted>text & more",  # Multiple issues
]

results = batch_repair_with_reports(
    xml_batch,
    filter_func=lambda r: len(r) > 0,  # Only return items that needed repairs
)

print(f"Processed {len(xml_batch)} items, {len(results)} needed repairs:\n")
for i, (repaired, report) in enumerate(results):
    print(f"Item {i + 1}:")
    print(f"  Repaired: {repaired}")
    print(f"  Repairs: {len(report)}")

# Example 5: Structure Validation
print("\n5. XML Structure Validation")
print("-" * 40)

test_cases = [
    "<root><item>valid</item></root>",
    "<root><item>unclosed",
    "<root attr=unquoted>test</root>",
    "<root>Tom & Jerry</root>",
]

for xml in test_cases:
    is_valid, issues = validate_xml_structure(xml)
    status = "✓" if is_valid else "✗"
    print(f"{status} {xml[:40]}")
    if issues:
        for issue in issues:
            print(f"    - {issue}")

# Example 6: Text Content Extraction
print("\n6. Text Content Extraction")
print("-" * 40)

html_like = """
<article>
    <h1>Welcome</h1>
    <p>This is <b>bold</b> and <i>italic</i> text.</p>
    <!-- This is a comment -->
    <code>function test() { return true; }</code>
</article>
"""

text_only = extract_text_content(html_like)
print(f"Original: {html_like.strip()}")
print(f"Extracted text: {text_only.strip()}")

# Example 7: Encoding Detection
print("\n7. Encoding Detection")
print("-" * 40)

# UTF-8 with BOM
utf8_bom = b'\xef\xbb\xbf<?xml version="1.0"?><root>test</root>'
encoding = detect_encoding(utf8_bom)
print(f"UTF-8 with BOM: {encoding}")

# Declared encoding
declared = b'<?xml version="1.0" encoding="ISO-8859-1"?><root>test</root>'
encoding = detect_encoding(declared)
print(f"Declared encoding: {encoding}")

# Example 8: Multiple Root Element Wrapping
print("\n8. Multiple Root Element Wrapping")
print("-" * 40)

multiple_roots = """
<user>Alice</user>
<user>Bob</user>
<user>Charlie</user>
"""

wrapped = repair_xml_safe(multiple_roots, wrap_multiple_roots=True)
print(f"Input (multiple roots):\n{multiple_roots.strip()}")
print(f"\nOutput (wrapped):\n{wrapped}")

# Example 9: Custom Configuration Combinations
print("\n9. Custom Configuration Combinations")
print("-" * 40)

# Example: Maximum security + all repairs
max_security_config = XMLRepairConfig(
    security=(
        SecurityFlags.STRIP_DANGEROUS_PIS
        | SecurityFlags.STRIP_EXTERNAL_ENTITIES
        | SecurityFlags.STRIP_DANGEROUS_TAGS
    ),
    repair=(
        RepairFlags.WRAP_MULTIPLE_ROOTS
        | RepairFlags.SANITIZE_INVALID_TAGS
        | RepairFlags.FIX_NAMESPACE_SYNTAX
    ),
)

engine = XMLRepairEngine(max_security_config)

complex_xml = """
<?php echo "bad"; ?>
<123tag>
    <bad::namespace>content</bad::namespace>
</123tag>
<another>root</another>
"""

result = engine.repair_xml(complex_xml)
print(f"Input (multiple issues):\n{complex_xml.strip()}")
print(f"\nOutput (all fixes applied):\n{result}")

# Example 10: Performance Comparison
print("\n10. Performance Monitoring")
print("-" * 40)

import time

test_xml = "<root>" + "<item>data</item>" * 100 + "</root>"

start = time.perf_counter()
for _ in range(1000):
    repair_xml_safe(test_xml)
end = time.perf_counter()

avg_time = (end - start) / 1000 * 1000  # Convert to milliseconds
print(f"Average repair time for {len(test_xml)} char XML: {avg_time:.4f} ms")
print(f"Throughput: ~{1000 / avg_time:.0f} repairs/second")

print("\n" + "=" * 80)
print("Advanced Features Summary:")
print("=" * 80)
print("✓ Repair reporting for transparency")
print("✓ Configuration objects for clean code")
print("✓ Security features (XSS/XXE prevention)")
print("✓ Batch processing with filtering")
print("✓ Structure validation without full parsing")
print("✓ Text extraction from XML/HTML")
print("✓ Encoding auto-detection")
print("✓ Multiple root wrapping")
print("✓ Flexible configuration combinations")
print("=" * 80)
