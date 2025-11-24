#!/usr/bin/env python
"""
Demonstration of Xenon's Error Handling Features
=================================================

This script demonstrates the three different modes:
1. Safe mode (recommended for production)
2. Lenient mode (never raises)
3. Default mode (original behavior)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from xenon import (
    repair_xml_safe,
    repair_xml_lenient,
    repair_xml,
    ValidationError,
    RepairError
)


def demo_safe_mode():
    """Demonstrate safe mode with error handling."""
    print("=" * 70)
    print("SAFE MODE - Production-Ready Error Handling")
    print("=" * 70)

    # Example 1: Invalid input type
    print("\n1. Invalid Input Type (None)")
    try:
        result = repair_xml_safe(None)
        print(f"   Result: {result}")
    except ValidationError as e:
        print(f"   ✓ Caught: {e}")

    # Example 2: Empty string (not allowed by default)
    print("\n2. Empty String (not allowed by default)")
    try:
        result = repair_xml_safe('')
        print(f"   Result: {result}")
    except ValidationError as e:
        print(f"   ✓ Caught: {e}")

    # Example 3: Empty string with allow_empty=True
    print("\n3. Empty String (with allow_empty=True)")
    result = repair_xml_safe('', allow_empty=True)
    print(f"   Result: {repr(result)}")

    # Example 4: Valid malformed XML
    print("\n4. Valid Malformed XML")
    result = repair_xml_safe('<root><item name=test')
    print(f"   Input:  '<root><item name=test'")
    print(f"   Result: {result}")

    # Example 5: Strict mode
    print("\n5. Strict Mode Validation")
    result = repair_xml_safe('<root><item>', strict=True)
    print(f"   Input:  '<root><item>'")
    print(f"   Result: {result}")

    # Example 6: Size limit
    print("\n6. Size Limit Validation")
    try:
        large_xml = '<root>' + 'x' * 1000
        result = repair_xml_safe(large_xml, max_size=500)
    except ValidationError as e:
        print(f"   ✓ Caught size limit error: Too large")


def demo_lenient_mode():
    """Demonstrate lenient mode that never raises."""
    print("\n\n" + "=" * 70)
    print("LENIENT MODE - Never Raises Exceptions")
    print("=" * 70)

    test_cases = [
        (None, "None input"),
        (123, "Integer input"),
        (['<root>'], "List input"),
        ('', "Empty string"),
        ('<root><item', "Truncated XML"),
        ('Here is: <root><msg>Hello</msg></root>', "XML with fluff"),
    ]

    for inp, description in test_cases:
        result = repair_xml_lenient(inp)
        print(f"\n   {description}")
        print(f"      Input:  {repr(inp)[:50]}")
        print(f"      Result: {repr(result)[:50]}")


def demo_default_mode():
    """Demonstrate default mode (original behavior)."""
    print("\n\n" + "=" * 70)
    print("DEFAULT MODE - Original Behavior")
    print("=" * 70)

    # Works fine with valid input
    print("\n1. Valid XML")
    result = repair_xml('<root><item>')
    print(f"   Input:  '<root><item>'")
    print(f"   Result: {result}")

    # Works with malformed XML
    print("\n2. Malformed Attributes")
    result = repair_xml('<item id=123 name=test>')
    print(f"   Input:  '<item id=123 name=test>'")
    print(f"   Result: {result}")

    # Crashes with invalid input
    print("\n3. Invalid Input (None) - WILL CRASH")
    try:
        result = repair_xml(None)
    except AttributeError as e:
        print(f"   ❌ Crashed: {type(e).__name__}: {e}")
        print(f"   → Use repair_xml_safe() instead!")


def demo_comparison():
    """Side-by-side comparison of all three modes."""
    print("\n\n" + "=" * 70)
    print("COMPARISON: Same Invalid Input, Different Modes")
    print("=" * 70)

    invalid_input = None

    print(f"\nInput: {repr(invalid_input)}")
    print("-" * 70)

    # Default mode
    print("\n1. DEFAULT MODE (repair_xml)")
    try:
        result = repair_xml(invalid_input)
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   ❌ Error: {type(e).__name__}")

    # Safe mode
    print("\n2. SAFE MODE (repair_xml_safe)")
    try:
        result = repair_xml_safe(invalid_input)
        print(f"   Result: {result}")
    except ValidationError as e:
        print(f"   ✓ Caught ValidationError with helpful message:")
        print(f"      \"{e}\"")

    # Lenient mode
    print("\n3. LENIENT MODE (repair_xml_lenient)")
    result = repair_xml_lenient(invalid_input)
    print(f"   ✓ Never raises: {repr(result)}")


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "XENON ERROR HANDLING DEMO" + " " * 28 + "║")
    print("╚" + "=" * 68 + "╝")

    demo_safe_mode()
    demo_lenient_mode()
    demo_default_mode()
    demo_comparison()

    print("\n\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
Choose the right mode for your use case:

✅ SAFE MODE (repair_xml_safe)
   - Production applications
   - When you need helpful error messages
   - When input validation is important
   - When you want optional strict output validation

✅ LENIENT MODE (repair_xml_lenient)
   - Batch processing with mixed data quality
   - When you prefer empty results over exceptions
   - Rapid prototyping and exploration
   - When fault tolerance is more important than correctness

✅ DEFAULT MODE (repair_xml)
   - Simple scripts where you control the input
   - Backward compatibility with existing code
   - When you're certain input is always a string

Recommendation: Use SAFE MODE for new projects!
    """)


if __name__ == '__main__':
    main()
