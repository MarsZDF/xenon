#!/usr/bin/env python
"""
LLM Integration Examples for Xenon XML Repair Library

This script demonstrates how to use Xenon with various LLM providers
to reliably extract structured data.

Note: This example doesn't actually call LLM APIs (to avoid requiring API keys),
but shows the pattern of how to use Xenon with LLM responses.
"""

from xenon import repair_xml, parse_xml, repair_xml_with_report
import json

print("=" * 80)
print("Xenon LLM Integration Examples")
print("=" * 80)

# Simulated LLM responses (these represent typical failure modes)
llm_responses = {
    "truncated": """
    Here's the user data in XML format:
    <users>
        <user id="1">
            <name>Alice</name>
            <email>alice@example.com</email>
            <role>admin</role>
        </user>
        <user id="2">
            <name>Bob</name>
            <email>bob@example.com
    """,
    "conversational": """
    Of course! I'll extract that information for you. Let me format it as XML:

    <products>
        <product sku="A123">
            <name>Laptop</name>
            <price>999.99</price>
        </product>
        <product sku="B456">
            <name>Mouse</name>
            <price>29.99</price>
        </product>
    </products>

    Does this look good? Let me know if you need any changes!
    """,
    "malformed_attributes": """
    <config>
        <database host=localhost port=5432 name=mydb>
            <credentials user=admin password=secret123/>
        </database>
        <cache enabled=true ttl=3600/>
    </config>
    """,
    "unescaped_entities": """
    <reviews>
        <review id="1">
            <author>John & Jane</author>
            <comment>Great product! 5 < 10 would buy again!</comment>
            <rating>5</rating>
        </review>
    </reviews>
    """,
}


def simulate_llm_call(prompt_type):
    """Simulate an LLM API call returning XML."""
    return llm_responses.get(prompt_type, "")


# Example 1: OpenAI-style Integration
print("\n1. OpenAI-style Integration Pattern")
print("-" * 40)


def get_user_data_from_llm():
    """Simulate getting user data from an LLM."""
    # In real code, this would be:
    # response = openai.ChatCompletion.create(
    #     model="gpt-4",
    #     messages=[{"role": "user", "content": "Extract user data as XML"}]
    # )
    # llm_output = response.choices[0].message.content

    llm_output = simulate_llm_call("truncated")

    # Use Xenon to repair and parse
    repaired_xml = repair_xml(llm_output)
    parsed_data = parse_xml(repaired_xml)

    return parsed_data


user_data = get_user_data_from_llm()
print("Extracted user data:")
print(json.dumps(user_data, indent=2))

# Example 2: Anthropic Claude-style Integration
print("\n2. Anthropic Claude-style Integration Pattern")
print("-" * 40)


def extract_products_with_claude():
    """Simulate extracting product data with Claude."""
    # In real code:
    # response = anthropic.Anthropic().messages.create(
    #     model="claude-3-opus-20240229",
    #     messages=[{"role": "user", "content": "Extract products as XML"}]
    # )
    # llm_output = response.content[0].text

    llm_output = simulate_llm_call("conversational")

    # Use Xenon with detailed reporting
    repaired_xml, report = repair_xml_with_report(llm_output)
    parsed_data = parse_xml(repaired_xml)

    print(f"Repairs performed: {len(report)}")
    if report:
        print(report.summary())

    return parsed_data


product_data = extract_products_with_claude()
print("\nExtracted product data:")
print(json.dumps(product_data, indent=2))

# Example 3: Handling Configuration Data
print("\n3. Extracting Configuration from LLM")
print("-" * 40)


def get_config_from_llm():
    """Extract configuration with error handling."""
    llm_output = simulate_llm_call("malformed_attributes")

    try:
        repaired_xml = repair_xml(llm_output)
        config = parse_xml(repaired_xml)
        return config
    except Exception as e:
        print(f"Error extracting config: {e}")
        return None


config_data = get_config_from_llm()
if config_data:
    print("Extracted configuration:")
    print(json.dumps(config_data, indent=2))

# Example 4: Batch Processing Multiple LLM Outputs
print("\n4. Batch Processing LLM Outputs")
print("-" * 40)

from xenon.utils import batch_repair

# Simulate multiple LLM responses
llm_batch = [
    simulate_llm_call("truncated"),
    simulate_llm_call("conversational"),
    simulate_llm_call("malformed_attributes"),
]

# Repair all at once
results = batch_repair(llm_batch, on_error="skip")

successful_repairs = sum(1 for _, error in results if error is None)
print(f"Successfully repaired {successful_repairs}/{len(llm_batch)} responses")

for i, (repaired, error) in enumerate(results):
    if error is None:
        parsed = parse_xml(repaired)
        print(f"\nBatch item {i + 1}: ✓ Parsed successfully")
    else:
        print(f"\nBatch item {i + 1}: ✗ Error: {error}")

# Example 5: Streaming LLM Responses
print("\n5. Processing Streaming LLM Responses")
print("-" * 40)

from xenon.utils import stream_repair


def llm_stream_generator():
    """Simulate a streaming LLM response."""
    # In real code, this would be a streaming API response
    responses = [
        "<item>first</item>",
        "<item>second",  # Incomplete
        "<item>third</item>",
    ]
    for response in responses:
        yield response


processed_count = 0
for repaired, error in stream_repair(llm_stream_generator()):
    if error is None:
        processed_count += 1
        print(f"  ✓ Stream item {processed_count}: {repaired}")
    else:
        print(f"  ✗ Stream item error: {error}")

# Example 6: Validation and Security
print("\n6. Secure LLM Output Processing")
print("-" * 40)

from xenon import repair_xml_safe

potentially_malicious = """
<?php system('rm -rf /'); ?>
<data>
    <script>alert('xss')</script>
    <user>Alice</user>
</data>
"""

# Use security features
safe_output = repair_xml_safe(
    potentially_malicious, strip_dangerous_pis=True, strip_dangerous_tags=True, strict=True
)

print("Input contained potentially dangerous content")
print(f"Sanitized output: {safe_output}")

print("\n" + "=" * 80)
print("Best Practices for LLM Integration:")
print("=" * 80)
print("1. Always use repair_xml() or repair_xml_safe() on LLM outputs")
print("2. Use repair_xml_with_report() to understand what was fixed")
print("3. Enable security features for untrusted content")
print("4. Use batch_repair() for processing multiple outputs efficiently")
print("5. Consider using strict=True for production systems")
print("6. Log repair reports to improve your LLM prompts over time")
print("=" * 80)
