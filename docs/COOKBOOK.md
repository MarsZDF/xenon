# Xenon Cookbook

Practical recipes for common XML repair scenarios.

---

## Table of Contents

1. [LLM Integration](#llm-integration) - 3 recipes
2. [Batch Processing](#batch-processing) - 2 recipes
3. [Production Workflows](#production-workflows) - 2 recipes
4. [Security Hardening](#security-hardening) - 2 recipes
5. [Performance Optimization](#performance-optimization) - 2 recipes
6. [Error Handling](#error-handling) - 2 recipes
7. [Custom Workflows](#custom-workflows) - 3 recipes

---

## LLM Integration

### Recipe 1: OpenAI GPT with XML Output

```python
import openai
from xenon import repair_xml_safe

def get_structured_data(prompt: str) -> dict:
    """Get structured XML from GPT and parse it."""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{
            "role": "user",
            "content": f"{prompt}\n\nReturn response as XML."
        }]
    )

    llm_output = response.choices[0].message.content

    # Repair and format
    xml = repair_xml_safe(
        llm_output,
        format_output='pretty',
        html_entities='unicode',  # GPT may use HTML entities
        strip_dangerous_pis=True  # Remove any injected code
    )

    return parse_xml(xml)

# Usage
data = get_structured_data("List 3 products with prices")
```

### Recipe 2: Handle Truncated Streaming Responses

```python
from xenon import repair_xml_safe

def repair_streaming_xml(stream):
    """Repair XML from streaming LLM response."""
    buffer = ""

    for chunk in stream:
        buffer += chunk

    # LLM streams often get cut off mid-tag
    repaired = repair_xml_safe(
        buffer,
        wrap_multiple_roots=True,  # Handle partial output
        auto_wrap_cdata=True       # Protect code snippets
    )

    return repaired
```

### Recipe 3: Extract XML from Conversational Response

```python
from xenon import repair_xml_safe

llm_response = """
Sure! Here's the data you requested:

<users>
    <user id="1">
        <name>Alice</name>
        <email>alice@example.com</email>
    </user>
    <user id="2">
        <name>Bob

I hope this helps! Let me know if you need anything else.
"""

# Xenon automatically extracts and repairs the XML
result = repair_xml_safe(llm_response)
print(result)
# Clean XML with no conversational fluff!
```

---

## Batch Processing

### Recipe 4: Process 1000s of XML Files

```python
from pathlib import Path
from xenon import batch_repair

def repair_directory(input_dir: str, output_dir: str):
    """Repair all XML files in a directory."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Load all XML files
    xml_files = list(input_path.glob('*.xml'))
    xml_contents = [f.read_text() for f in xml_files]

    # Batch repair
    results = batch_repair(
        xml_contents,
        show_progress=True,  # Show progress bar
        on_error='skip'      # Skip failures
    )

    # Save repaired files
    for xml_file, (repaired, error) in zip(xml_files, results):
        if not error:
            output_file = output_path / xml_file.name
            output_file.write_text(repaired)
        else:
            print(f"Failed: {xml_file.name}: {error}")

    return len([r for r in results if not r[1]])  # Count successes

# Usage
successes = repair_directory('./raw_xml/', './repaired/')
print(f"Repaired {successes} files")
```

### Recipe 5: Streaming ETL Pipeline

```python
from xenon import stream_repair
import csv

def xml_etl_pipeline(input_csv: str, output_csv: str):
    """ETL pipeline: CSV → XML → Repair → Parse → CSV."""

    def xml_generator():
        with open(input_csv) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Simulate XML generation from each row
                yield f"<record><id>{row['id']}</id><data>{row['data']}"

    # Stream repair (constant memory)
    with open(output_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'xml', 'status'])
        writer.writeheader()

        for repaired, error in stream_repair(xml_generator()):
            writer.writerow({
                'id': extract_id(repaired),
                'xml': repaired,
                'status': 'success' if not error else 'failed'
            })

# Process millions of records with constant memory
xml_etl_pipeline('input.csv', 'output.csv')
```

---

## Production Workflows

### Recipe 6: Validate and Repair in Production

```python
from xenon import repair_xml_safe, validate_xml_structure
import logging

logger = logging.getLogger(__name__)

def production_xml_handler(xml: str, source: str) -> str:
    """Production-grade XML handling with validation and logging."""

    # Step 1: Quick structure check
    is_valid, issues = validate_xml_structure(xml)
    if issues:
        logger.warning(f"XML from {source} has issues: {issues}")

    # Step 2: Repair with all safety features
    try:
        repaired = repair_xml_safe(
            xml,
            strict=True,                  # Fail if can't repair
            strip_dangerous_pis=True,     # Security
            strip_external_entities=True, # XXE prevention
            strip_dangerous_tags=True,    # XSS prevention
            escape_unsafe_attributes=True, # Enhanced XSS protection
            format_output='compact'       # Consistent formatting
        )

        logger.info(f"Successfully repaired XML from {source}")
        return repaired

    except Exception as e:
        logger.error(f"Failed to repair XML from {source}: {e}")
        if hasattr(e, 'line'):
            logger.error(f"  Error at line {e.line}, column {e.column}")
            logger.error(f"  Context: {e.context}")
        raise

# Usage in API endpoint
@app.post("/api/submit-xml")
def submit_xml(xml: str):
    repaired = production_xml_handler(xml, source="API")
    return {"status": "success", "xml": repaired}
```

### Recipe 7: A/B Test Different Repair Strategies

```python
from xenon import repair_xml_safe
import random

def ab_test_repair(xml: str, user_id: str) -> str:
    """A/B test repair strategies."""

    # Bucket users
    bucket = hash(user_id) % 2

    if bucket == 0:
        # Control: Basic repair
        return repair_xml_safe(xml)
    else:
        # Treatment: Aggressive repair
        return repair_xml_safe(
            xml,
            sanitize_invalid_tags=True,
            fix_namespace_syntax=True,
            auto_wrap_cdata=True
        )

# Track which strategy works better
result = ab_test_repair(llm_output, user_id="user123")
log_metrics(user_id, bucket, success=True)
```

---

## Security Hardening

### Recipe 8: Maximum Security for Untrusted XML

```python
from xenon import repair_xml_safe

def secure_repair(untrusted_xml: str) -> str:
    """Repair untrusted XML with maximum security."""

    return repair_xml_safe(
        untrusted_xml,
        # Security flags
        strip_dangerous_pis=True,      # Remove <?php ?>, etc.
        strip_external_entities=True,  # XXE prevention
        strip_dangerous_tags=True,     # Remove <script>, etc.
        # Validation
        strict=True,                   # Fail if still invalid
        allow_empty=False,             # Reject empty input
        max_size=10 * 1024 * 1024     # 10MB max (DoS prevention)
    )

# Use in web endpoint
@app.post("/upload-xml")
def upload_xml(file: UploadFile):
    xml = file.file.read().decode('utf-8')
    safe_xml = secure_repair(xml)
    return {"status": "safe", "xml": safe_xml}
```

### Recipe 9: Audit Trail for XML Repairs

```python
from xenon import repair_xml_with_report
import json
from datetime import datetime

def repair_with_audit(xml: str, user: str) -> dict:
    """Repair XML and create audit trail."""

    repaired, report = repair_xml_with_report(xml)

    # Create audit record
    audit = {
        "timestamp": datetime.utcnow().isoformat(),
        "user": user,
        "original_length": len(xml),
        "repaired_length": len(repaired),
        "repairs_made": len(report),
        "repairs": [
            {
                "type": action.repair_type.value,
                "description": action.description,
                "position": action.position
            }
            for action in report
        ]
    }

    # Log audit trail
    with open('audit.jsonl', 'a') as f:
        f.write(json.dumps(audit) + '\n')

    return {
        "xml": repaired,
        "audit_id": audit["timestamp"]
    }
```

---

## Performance Optimization

### Recipe 10: Optimize for High Throughput

```python
from xenon import XMLRepairEngine
from functools import lru_cache

# Create reusable engine (faster than creating new one each time)
engine = XMLRepairEngine()

@lru_cache(maxsize=1000)
def cached_repair(xml: str) -> str:
    """Cache repairs for repeated XML patterns."""
    return engine.repair_xml(xml)

# Process 10,000 similar XMLs
for i in range(10000):
    xml = f"<record id='{i}'>data{i}"
    repaired = cached_repair(xml)  # Much faster for duplicates!
```

### Recipe 11: Parallel Batch Processing

```python
from xenon import repair_xml_safe
from concurrent.futures import ThreadPoolExecutor, as_completed

def parallel_batch_repair(xml_list: list[str], max_workers: int = 10) -> list[str]:
    """Repair multiple XMLs in parallel."""

    def repair_one(xml):
        try:
            return repair_xml_safe(xml), None
        except Exception as e:
            return None, str(e)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(repair_one, xml): i for i, xml in enumerate(xml_list)}
        results = [None] * len(xml_list)

        for future in as_completed(futures):
            idx = futures[future]
            results[idx] = future.result()

    return results

# Process 1000 XMLs in parallel
xml_batch = load_xml_batch(1000)
results = parallel_batch_repair(xml_batch)
```

---

## Error Handling

### Recipe 12: Graceful Degradation

```python
from xenon import repair_xml_safe, XenonException

def repair_with_fallback(xml: str) -> str:
    """Try repair, fall back to safe defaults."""

    try:
        # Try strict repair
        return repair_xml_safe(xml, strict=True)
    except XenonException as e:
        print(f"Strict repair failed: {e}")

        try:
            # Fall back to lenient repair
            return repair_xml_safe(xml, strict=False)
        except XenonException:
            # Last resort: return minimal valid XML
            return "<error>Unable to repair XML</error>"
```

### Recipe 13: Detailed Error Reporting

```python
from xenon import repair_xml_safe, get_line_column, get_context_snippet

def detailed_error_report(xml: str) -> dict:
    """Get detailed error report for debugging."""

    try:
        repaired = repair_xml_safe(xml, strict=True)
        return {
            "status": "success",
            "xml": repaired
        }
    except Exception as e:
        # Build detailed error report
        error_report = {
            "status": "error",
            "message": str(e),
            "type": type(e).__name__
        }

        if hasattr(e, 'line') and e.line:
            error_report["line"] = e.line
            error_report["column"] = e.column
            error_report["context"] = e.context

            # Add surrounding lines for context
            lines = xml.split('\n')
            start = max(0, e.line - 3)
            end = min(len(lines), e.line + 2)
            error_report["surrounding_lines"] = lines[start:end]

        return error_report

# Usage
report = detailed_error_report(bad_xml)
if report["status"] == "error":
    print(f"Error on line {report['line']}: {report['message']}")
    print(f"Context:\n" + '\n'.join(report['surrounding_lines']))
```

---

## Custom Workflows

### Recipe 14: Custom Post-Processing

```python
from xenon import repair_xml_safe
import re

def repair_and_transform(xml: str) -> str:
    """Repair XML and apply custom transformations."""

    # Step 1: Repair
    repaired = repair_xml_safe(xml)

    # Step 2: Custom transformations
    # Replace company-specific patterns
    repaired = repaired.replace('<legacyTag>', '<newTag>')
    repaired = repaired.replace('</legacyTag>', '</newTag>')

    # Normalize IDs to uppercase
    repaired = re.sub(
        r'id="([^"]+)"',
        lambda m: f'id="{m.group(1).upper()}"',
        repaired
    )

    # Add metadata
    repaired = repaired.replace(
        '<root>',
        '<root xmlns="http://company.com/schema" version="2.0">'
    )

    return repaired
```

### Recipe 15: Integration with External Validation Libraries (DEPRECATED)

```python
from xenon import repair_xml_safe
from lxml import etree
from xenon import TrustLevel, ValidationError # Added TrustLevel and ValidationError

def repair_and_validate_schema_external(xml: str, xsd_path: str) -> tuple[str, bool]:
    """
    Repair XML and validate against XSD schema using an external library.
    Use Xenon's built-in schema validation instead where possible.
    """

    # Repair first (assuming UNTRUSTED input)
    repaired = repair_xml_safe(xml, trust=TrustLevel.UNTRUSTED) # Added trust level

    # Validate against schema
    schema = etree.XMLSchema(etree.parse(xsd_path))
    doc = etree.fromstring(repaired.encode('utf-8'))
    is_valid = schema.validate(doc)

    if not is_valid:
        errors = schema.error_log
        print(f"Schema validation errors: {errors}")
        raise ValidationError(f"XML failed external schema validation: {errors}") # Added exception

    return repaired, is_valid

# Usage
# Assuming llm_output and 'schema.xsd' exist
# xml, valid = repair_and_validate_schema_external(llm_output, 'schema.xsd')
# if valid:
#     process_xml(xml)
```

### Recipe 17: In-place Schema Validation (NEW)

```python
from xenon import repair_xml_safe, ValidationError, TrustLevel

# Define a simple XSD schema
XSD_SCHEMA_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="root">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="item" type="xs:string"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>"""

def repair_and_validate_in_place(xml: str) -> str:
    """
    Repair XML and validate it against an embedded schema using Xenon's built-in capability.
    This simplifies the validation workflow by integrating it directly into `repair_xml_safe`.
    """
    try:
        # Repair and validate in one call
        repaired = repair_xml_safe(
            xml,
            trust=TrustLevel.UNTRUSTED,
            schema_content=XSD_SCHEMA_CONTENT,
            validate_output_schema=True  # Explicitly enable schema validation
        )
        print("XML repaired and validated successfully!")
        return repaired
    except ValidationError as e:
        print(f"XML repaired but failed schema validation: {e}")
        # Depending on use case, you might want to re-raise or return original/empty
        raise
    except Exception as e:
        print(f"An unexpected error occurred during repair or validation: {e}")
        raise

# Example Usage:
# Valid XML (after potential repair)
valid_xml = "<root><item>Hello</item></root>"
repair_and_validate_in_place(valid_xml)

# Invalid XML (will fail schema validation)
invalid_xml = "<root><wrong_tag>World</wrong_tag></root>"
try:
    repair_and_validate_in_place(invalid_xml)
except ValidationError:
    print("Caught expected ValidationError for invalid XML.")

# Malformed XML that might become valid after repair
malformed_valid_xml = "<root><item>Hello</item"
repair_and_validate_in_place(malformed_valid_xml)
```

### Recipe 16: Analyze Repair Patterns

```python
from xenon import repair_xml_with_report, RepairType
from collections import Counter

def analyze_llm_repair_patterns(xml_samples: list[str]) -> dict:
    """Analyze what types of repairs are most common in LLM output."""

    all_repair_types = Counter()
    security_issues_count = 0
    total_repairs = 0

    for xml in xml_samples:
        result, report = repair_xml_with_report(xml)

        # Count repair types
        for action in report.actions:
            all_repair_types[action.repair_type.value] += 1
            total_repairs += 1

        # Track security issues
        if report.has_security_issues():
            security_issues_count += 1

    # Analyze patterns
    analysis = {
        "total_xmls": len(xml_samples),
        "total_repairs": total_repairs,
        "avg_repairs_per_xml": total_repairs / len(xml_samples),
        "security_issues": security_issues_count,
        "top_repairs": all_repair_types.most_common(5),
        "by_category": {
            "structural": sum(
                all_repair_types[t.value]
                for t in [RepairType.TRUNCATION, RepairType.MULTIPLE_ROOTS]
            ),
            "security": sum(
                all_repair_types[t.value]
                for t in [
                    RepairType.DANGEROUS_PI_STRIPPED,
                    RepairType.DANGEROUS_TAG_STRIPPED,
                    RepairType.EXTERNAL_ENTITY_STRIPPED,
                ]
            ),
            "entity_escaping": all_repair_types["unescaped_entity"],
            "tag_issues": sum(
                all_repair_types[t.value]
                for t in [RepairType.TAG_TYPO, RepairType.TAG_CASE_MISMATCH]
            ),
        }
    }

    return analysis

# Analyze 1000 LLM-generated XMLs
llm_outputs = load_llm_samples(1000)
patterns = analyze_llm_repair_patterns(llm_outputs)

print(f"Average repairs per XML: {patterns['avg_repairs_per_xml']:.2f}")
print(f"Security issues: {patterns['security_issues']}")
print(f"\nTop 5 repair types:")
for repair_type, count in patterns['top_repairs']:
    print(f"  {repair_type}: {count} occurrences")

print(f"\nBy category:")
for category, count in patterns['by_category'].items():
    print(f"  {category}: {count}")

# Use insights to improve prompts
if patterns['by_category']['structural'] > patterns['total_repairs'] * 0.3:
    print("\n⚠️  Consider adding 'Always close all XML tags' to prompts")
```

---

## Tips & Best Practices

### DO ✅

- **Always** use `repair_xml_safe()` for production code
- **Enable** security flags for untrusted input (especially `escape_unsafe_attributes` for XSS protection)
- **Use** `strict=True` when you need guaranteed valid XML
- **Cache** repairs for repeated patterns
- **Log** repair actions for audit trails
- **Validate** critical XML against schemas

### DON'T ❌

- **Don't** parse XML before repairing (Xenon extracts it)
- **Don't** create new XMLRepairEngine() for each repair (reuse it)
- **Don't** ignore exceptions (they have useful context)
- **Don't** assume repaired XML is semantically correct (validate schema)
- **Don't** skip security flags for user-generated content

---

## Need More Help?

- **GitHub Issues**: https://github.com/MarsZDF/xenon/issues
- **Discussions**: https://github.com/MarsZDF/xenon/discussions
- **Examples**: Check `examples/` directory

**Found a useful recipe?** Submit a PR to add it to this cookbook!
