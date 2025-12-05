# Xenon v1.1.0 Roadmap

## Overview
v1.1.0 focuses on **Async Support**, **Developer Tooling (CLI)**, and **Data Interoperability**.

---

## Completed Features (Ready for Release)

### 1. Async/Await Support ✅
**Status**: Implemented & Tested
Native async streaming for modern Python ecosystems.
- `feed_async()` / `finalize_async()`
- Async context manager support
- Zero blocking for high-concurrency apps

---

## Proposed Features

### 2. CLI Tool ⭐⭐⭐⭐
**Priority: HIGH**

Command-line interface for quick repairs without writing code.

```bash
# Repair single file
xenon repair input.xml -o output.xml --trust untrusted

# Batch repair directory
xenon repair-batch ./xml_files/ -o ./repaired/ --parallel

# Validate XML against schema
xenon validate input.xml --schema schema.xsd

# Pipe from stdin (Unix philosophy)
cat llm_output.txt | xenon repair --extract-xml > repaired.xml
```

**Benefits:**
- Integration with CI/CD pipelines
- Quick debugging of files
- Language-agnostic usage via shell

**Implementation:**
- Use `argparse` or `click`
- Entry point in `pyproject.toml`
- comprehensive `--help`

---

### 3. JSON Conversion Enhancements ⭐⭐⭐
**Priority: MEDIUM**

Improve `parse_xml()` with more control over JSON output conventions (BadgerFish, GData, etc.).

```python
from xenon import parse_xml

# Configurable conversion
result = parse_xml(
    xml,
    trust=TrustLevel.UNTRUSTED,
    config={
        'force_list': {'item', 'entry'},  # Always make these lists
        'text_key': '$t',                 # Instead of '#text'
        'attr_prefix': '@',               # Instead of '@attributes' dict
        'strip_whitespace': True
    }
)
```

**Benefits:**
- Better interoperability with frontend frameworks
- Consistent handling of single-item vs multi-item lists

---

### 4. Performance Optimization ⭐⭐
**Priority: MEDIUM**

With secure-by-default (v1.0.0) checks, performance has dropped ~20%. We aim to recover this.

**Strategies:**
- **Profile Hot Paths**: Identify bottlenecks in `tokenize` and `escape_entities`.
- **Fast Path**: If `TrustLevel.TRUSTED`, bypass all regex checks.
- **Cython/MyPyC**: Compile critical state machine loops.

---

### 5. Integrations (Future) ⭐
**Priority: LOW**

- **LlamaIndex**: Data loader for resilient XML parsing.
- **Pydantic**: Parse repaired XML directly into Pydantic models.

---

## Timeline

- **v1.1.0-alpha**: Release with Async support (Immediate)
- **v1.1.0-beta**: Add CLI Tool (1 week)
- **v1.1.0-rc**: JSON Enhancements & Performance (2 weeks)
- **v1.1.0 Final**: (3 weeks)
