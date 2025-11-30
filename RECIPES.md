# Xenon Recipes

Common patterns and solutions for using Xenon in real-world applications.

## Table of Contents

- [LLM Integration](#llm-integration)
- [Data Extraction](#data-extraction)
- [Error Handling](#error-handling)
- [Performance Optimization](#performance-optimization)
- [Security](#security)
- [Testing](#testing)

---

## LLM Integration

### Recipe 1: OpenAI GPT Integration

```python
import openai
from xenon import repair_xml, parse_xml

def extract_structured_data(prompt):
    """Extract structured data from OpenAI GPT."""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{
            "role": "system",
            "content": "You are a data extraction assistant. Always return data in XML format."
        }, {
            "role": "user",
            "content": prompt
        }]
    )

    llm_output = response.choices[0].message.content

    # Repair and parse the XML
    repaired_xml = repair_xml(llm_output)
    data = parse_xml(repaired_xml)

    return data

# Usage
result = extract_structured_data("Extract customer information from this text: ...")
```

### Recipe 2: Anthropic Claude Integration

```python
import anthropic
from xenon import repair_xml_with_report, parse_xml

def extract_with_claude(prompt, track_repairs=True):
    """Extract data using Claude with repair tracking."""
    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-3-opus-20240229",
        messages=[{"role": "user", "content": prompt}]
    )

    llm_output = message.content[0].text

    if track_repairs:
        repaired_xml, report = repair_xml_with_report(llm_output)
        data = parse_xml(repaired_xml)

        # Log what was fixed
        if len(report) > 0:
            print(f"Performed {len(report)} repairs:")
            print(report.summary())

        return data, report
    else:
        repaired_xml = repair_xml(llm_output)
        return parse_xml(repaired_xml)

# Usage
data, report = extract_with_claude("Extract product info...")
```

### Recipe 3: Retry Logic for Failed Extractions

```python
from xenon import repair_xml_safe, MalformedXMLError
import time

def extract_with_retry(llm_function, max_retries=3):
    """Extract XML from LLM with retry logic."""
    for attempt in range(max_retries):
        try:
            llm_output = llm_function()
            repaired = repair_xml_safe(llm_output, strict=True)
            return repaired
        except MalformedXMLError as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                time.sleep(1)
            else:
                raise

# Usage
def my_llm_call():
    # Your LLM API call here
    return "<data>...</data>"

result = extract_with_retry(my_llm_call)
```

---

## Data Extraction

### Recipe 4: Extracting Customer Data

```python
from xenon import parse_xml

llm_output = """
Here's the customer data:
<customers>
    <customer id="1">
        <name>Acme Corp</name>
        <contact email="info@acme.com" phone="555-1234"/>
    </customer>
</customers>
"""

data = parse_xml(llm_output)

# Access nested data
customers = data.get('customers', {}).get('customer', [])
if not isinstance(customers, list):
    customers = [customers]

for customer in customers:
    name = customer.get('name', '')
    email = customer.get('contact', {}).get('@attributes', {}).get('email', '')
    print(f"Customer: {name}, Email: {email}")
```

### Recipe 5: Handling Multiple Root Elements

```python
from xenon import repair_xml_safe

# LLM returned multiple root elements
llm_output = """
<product id="1"><name>Laptop</name></product>
<product id="2"><name>Mouse</name></product>
<product id="3"><name>Keyboard</name></product>
"""

# Wrap in synthetic root
repaired = repair_xml_safe(llm_output, wrap_multiple_roots=True)
# Now: <document><product>...</product><product>...</product>...</document>

data = parse_xml(repaired)
products = data['document']['product']
```

---

## Error Handling

### Recipe 6: Graceful Degradation

```python
from xenon import repair_xml_lenient, parse_xml_lenient

def process_llm_output_safe(llm_output):
    """Process LLM output with graceful degradation."""
    # Try lenient mode - never raises exceptions
    repaired = repair_xml_lenient(llm_output)

    if not repaired:
        # Couldn't repair - return empty result
        return None

    data = parse_xml_lenient(repaired)
    return data if data else None

# Usage - always returns None or valid data, never raises
result = process_llm_output_safe(some_llm_output)
if result:
    print(f"Success: {result}")
else:
    print("Could not extract valid data")
```

### Recipe 7: Error Categorization

```python
from xenon import repair_xml_safe, ValidationError, MalformedXMLError, RepairError

def categorize_errors(xml_string):
    """Categorize different types of failures."""
    try:
        result = repair_xml_safe(xml_string, strict=True)
        return {"status": "success", "data": result}
    except ValidationError as e:
        # Input validation failed (wrong type, too large, etc.)
        return {"status": "invalid_input", "error": str(e)}
    except MalformedXMLError as e:
        # XML still malformed after repair
        return {"status": "unrepairable", "error": str(e)}
    except RepairError as e:
        # Internal repair error
        return {"status": "repair_failed", "error": str(e)}

result = categorize_errors(llm_output)
if result["status"] == "success":
    print(f"Data: {result['data']}")
else:
    print(f"Error ({result['status']}): {result['error']}")
```

---

## Performance Optimization

### Recipe 8: Batch Processing for High Throughput

```python
from xenon.utils import batch_repair
import concurrent.futures

def process_large_dataset(xml_list, parallel=True):
    """Process large dataset efficiently."""
    if parallel:
        # Process in parallel batches
        batch_size = 100
        batches = [xml_list[i:i+batch_size] for i in range(0, len(xml_list), batch_size)]

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(batch_repair, batch) for batch in batches]
            for future in concurrent.futures.as_completed(futures):
                results.extend(future.result())

        return results
    else:
        # Process sequentially with batch_repair
        return batch_repair(xml_list, show_progress=True)

# Usage
large_dataset = ['<root><item>...</item></root>' for _ in range(10000)]
results = process_large_dataset(large_dataset)
```

### Recipe 9: Streaming Processing

```python
from xenon.utils import stream_repair

def process_xml_stream(xml_source):
    """Process XML from a streaming source."""
    successful = 0
    failed = 0

    for repaired, error in stream_repair(xml_source):
        if error is None:
            successful += 1
            # Process the repaired XML
            yield repaired
        else:
            failed += 1
            # Log error or handle failure
            print(f"Failed to repair: {error}")

    print(f"Processed: {successful} successful, {failed} failed")

# Usage with generator
def xml_generator():
    # Could be reading from file, API, etc.
    for line in open('data.xml'):
        if line.strip():
            yield line.strip()

for repaired_xml in process_xml_stream(xml_generator()):
    # Process each repaired XML
    pass
```

---

## Security

### Recipe 10: Production-Ready Secure Processing

```python
from xenon import repair_xml_safe

def secure_xml_processing(untrusted_xml, max_size_mb=1):
    """Process untrusted XML with all security features."""
    max_size_bytes = max_size_mb * 1024 * 1024

    result = repair_xml_safe(
        untrusted_xml,
        # Security features
        strip_dangerous_pis=True,        # Remove <?php, <?asp, etc.
        strip_external_entities=True,    # Prevent XXE attacks
        strip_dangerous_tags=True,       # Remove <script>, <iframe>, etc.
        # Validation
        strict=True,                     # Validate output
        max_size=max_size_bytes,        # Prevent DoS
        allow_empty=False,               # Reject empty input
        # Repair features
        wrap_multiple_roots=True,        # Handle multiple roots
        sanitize_invalid_tags=True,      # Fix invalid tag names
        fix_namespace_syntax=True,       # Fix namespace issues
    )

    return result

# Usage
user_input = get_user_submitted_xml()
safe_xml = secure_xml_processing(user_input)
```

### Recipe 11: Content Security Policy

```python
from xenon import repair_xml_safe, repair_xml_with_report

def process_with_security_audit(xml_string):
    """Process XML and audit security issues."""
    repaired, report = repair_xml_with_report(xml_string)

    # Check if security issues were found
    if report.has_security_issues():
        security_actions = [
            action for action in report.actions
            if action.repair_type.value in [
                'dangerous_pi_stripped',
                'dangerous_tag_stripped',
                'external_entity_stripped'
            ]
        ]

        # Log security violations
        for action in security_actions:
            log_security_violation(action)

        # Decide whether to accept or reject
        if len(security_actions) > 5:
            raise SecurityError("Too many security violations")

    return repaired
```

---

## Testing

### Recipe 12: Testing LLM Integrations

```python
import pytest
from xenon import repair_xml, parse_xml

# Test data representing common LLM failure modes
TEST_CASES = [
    # (input, expected_has_key)
    ('<root><item>test', 'root'),  # Truncation
    ('Here is: <root><item>test</item></root> Done!', 'root'),  # Fluff
    ('<root attr=unquoted>test</root>', 'root'),  # Malformed attrs
    ('<root>Tom & Jerry</root>', 'root'),  # Unescaped entities
]

@pytest.mark.parametrize("xml_input,expected_key", TEST_CASES)
def test_llm_failure_modes(xml_input, expected_key):
    """Test that Xenon handles common LLM failures."""
    repaired = repair_xml(xml_input)
    parsed = parse_xml(repaired)
    assert expected_key in parsed

def test_batch_processing():
    """Test batch processing of multiple LLM outputs."""
    from xenon.utils import batch_repair

    inputs = ['<root><item>' for _ in range(10)]
    results = batch_repair(inputs)

    assert len(results) == 10
    for repaired, error in results:
        assert error is None
        assert '</root>' in repaired
```

### Recipe 13: Performance Regression Testing

```python
import time
from xenon import repair_xml

def benchmark_repair(xml, iterations=1000):
    """Benchmark repair performance."""
    start = time.perf_counter()
    for _ in range(iterations):
        repair_xml(xml)
    end = time.perf_counter()

    avg_ms = (end - start) / iterations * 1000
    return avg_ms

def test_performance_targets():
    """Ensure performance targets are met."""
    small_xml = '<root><item>test'
    medium_xml = '<root>' + '<item>data</item>' * 10

    assert benchmark_repair(small_xml) < 0.1, "Small XML too slow"
    assert benchmark_repair(medium_xml) < 0.5, "Medium XML too slow"
```

---

## Advanced Patterns

### Recipe 14: Custom Configuration for Specific LLM

```python
from xenon import XMLRepairEngine, XMLRepairConfig, RepairFlags

# Create custom config for specific LLM behavior
GPT4_CONFIG = XMLRepairConfig(
    # GPT-4 tends to create invalid tag names
    repair=RepairFlags.SANITIZE_INVALID_TAGS
)

CLAUDE_CONFIG = XMLRepairConfig(
    # Claude sometimes creates multiple roots
    repair=RepairFlags.WRAP_MULTIPLE_ROOTS
)

# Create engines for each
gpt4_engine = XMLRepairEngine(GPT4_CONFIG)
claude_engine = XMLRepairEngine(CLAUDE_CONFIG)

# Use appropriate engine
if llm_provider == "openai":
    result = gpt4_engine.repair_xml(llm_output)
elif llm_provider == "anthropic":
    result = claude_engine.repair_xml(llm_output)
```

### Recipe 15: Monitoring and Metrics

```python
from xenon import repair_xml_with_report
import logging

class XMLRepairMetrics:
    """Track repair metrics for monitoring."""

    def __init__(self):
        self.total_processed = 0
        self.total_repairs = 0
        self.repair_types = {}

    def process(self, xml_string):
        """Process XML and track metrics."""
        repaired, report = repair_xml_with_report(xml_string)

        self.total_processed += 1
        self.total_repairs += len(report)

        # Track repair types
        for action in report.actions:
            repair_type = action.repair_type.value
            self.repair_types[repair_type] = self.repair_types.get(repair_type, 0) + 1

        # Log if many repairs needed
        if len(report) > 3:
            logging.warning(f"High repair count: {len(report)} repairs needed")

        return repaired

    def get_stats(self):
        """Get repair statistics."""
        return {
            "total_processed": self.total_processed,
            "total_repairs": self.total_repairs,
            "avg_repairs_per_doc": self.total_repairs / max(self.total_processed, 1),
            "repair_types": self.repair_types
        }

# Usage
metrics = XMLRepairMetrics()
for xml in llm_outputs:
    repaired = metrics.process(xml)

print(metrics.get_stats())
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: "XML still malformed after repair"

**Solution**: Use strict mode to understand what's wrong

```python
from xenon import repair_xml_safe, repair_xml_with_report

# First, see what was repaired
repaired, report = repair_xml_with_report(xml)
print(report.summary())

# Then try strict mode
try:
    result = repair_xml_safe(xml, strict=True)
except Exception as e:
    print(f"Validation failed: {e}")
```

#### Issue: "Performance is slow for large XML"

**Solution**: Use batch processing and consider streaming

```python
from xenon.utils import batch_repair, stream_repair

# For list of XMLs
results = batch_repair(xml_list, show_progress=True)

# For streaming data
for repaired, error in stream_repair(xml_generator()):
    process(repaired)
```

#### Issue: "Getting security warnings"

**Solution**: Enable security features

```python
from xenon import repair_xml_safe

result = repair_xml_safe(
    xml,
    strip_dangerous_pis=True,
    strip_external_entities=True,
    strip_dangerous_tags=True
)
```

---

## Best Practices

1. **Always use `repair_xml()` or `repair_xml_safe()` on LLM outputs**
2. **Use `repair_xml_with_report()` to understand and improve LLM prompts**
3. **Enable security features for untrusted content**
4. **Use batch processing for high throughput**
5. **Set `strict=True` in production for validation**
6. **Monitor repair metrics to identify LLM issues**
7. **Use appropriate error handling for your use case**
8. **Consider custom configurations for specific LLMs**

---

For more examples, see the `examples/` directory in the repository.
