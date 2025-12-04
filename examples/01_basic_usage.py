#!/usr/bin/env python
"""
Basic Usage Examples for Xenon XML Repair Library

This script demonstrates the most common use cases for Xenon.
"""

from xenon import repair_xml, parse_xml, repair_xml_safe

print("=" * 80)
print("Xenon Basic Usage Examples")
print("=" * 80)

# Example 1: Simple Truncation
print("\n1. Repairing Truncated XML")
print("-" * 40)
truncated_xml = '<root><user name="Alice"><age>30'
print(f"Input:  {truncated_xml}")
repaired = repair_xml(truncated_xml)
print(f"Output: {repaired}")

# Example 2: Conversational Fluff
print("\n2. Extracting XML from Conversational Text")
print("-" * 40)
llm_response = (
    "Sure! Here is the XML you requested: <root><item>data</item></root> Hope this helps!"
)
print(f"Input:  {llm_response}")
repaired = repair_xml(llm_response)
print(f"Output: {repaired}")

# Example 3: Malformed Attributes
print("\n3. Fixing Malformed Attributes")
print("-" * 40)
malformed_attrs = "<user name=John age=30 city=NYC>Hello</user>"
print(f"Input:  {malformed_attrs}")
repaired = repair_xml(malformed_attrs)
print(f"Output: {repaired}")

# Example 4: Unescaped Entities
print("\n4. Escaping Unescaped Entities")
print("-" * 40)
unescaped = "<message>Tom & Jerry < > test</message>"
print(f"Input:  {unescaped}")
repaired = repair_xml(unescaped)
print(f"Output: {repaired}")

# Example 5: Parsing to Dictionary
print("\n5. Parsing XML to Dictionary")
print("-" * 40)
xml = '<user name="Alice"><age>30</age><city>NYC</city></user>'
print(f"Input:  {xml}")
parsed = parse_xml(xml)
print(f"Output: {parsed}")

# Example 6: Safe Repair with Validation
print("\n6. Safe Repair with Strict Validation")
print("-" * 40)
xml = "<root><item>incomplete"
print(f"Input:  {xml}")
try:
    repaired = repair_xml_safe(xml, strict=True)
    print(f"Output: {repaired}")
    print("✓ Validation passed!")
except Exception as e:
    print(f"✗ Validation failed: {e}")

# Example 7: Multiple Issues
print("\n7. Repairing Multiple Issues at Once")
print("-" * 40)
complex_xml = "<root><user name=Alice>Tom & Jerry<item>unclosed"
print(f"Input:  {complex_xml}")
repaired = repair_xml(complex_xml)
print(f"Output: {repaired}")

# Example 8: Empty/Whitespace Input
print("\n8. Handling Empty Input")
print("-" * 40)
empty_xml = "   \n\t  "
print(f"Input:  '{empty_xml}'")
try:
    repaired = repair_xml_safe(empty_xml, allow_empty=True)
    print(f"Output: '{repaired}'")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 80)
print("All examples completed!")
print("=" * 80)
