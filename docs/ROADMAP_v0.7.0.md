# Xenon v0.7.0 Roadmap

## Overview
v0.7.0 focuses on **advanced features, developer experience, and production tooling**.

---

## Proposed Features

### 1. XML Schema Validation ⭐⭐⭐
**Priority: HIGH**

Add XML Schema (XSD) validation support for repair verification.

```python
from xenon import repair_xml_safe, validate_against_schema

# Validate repaired XML against schema
xml = repair_xml_safe(llm_output)
is_valid, errors = validate_against_schema(xml, schema_file='schema.xsd')

# Or validate during repair
xml = repair_xml_safe(
    llm_output,
    schema='schema.xsd',  # Auto-validate after repair
    strict=True  # Raise if validation fails
)
```

**Benefits:**
- Ensure repaired XML matches expected structure
- Critical for production systems with strict schemas
- Better error messages showing schema violations

**Implementation:**
- Use `xml.etree.ElementTree` for basic validation
- Optional: `lxml` support for full XSD 1.1 (keep zero-dep for core)
- Add `SchemaValidationError` exception with detailed violations

---

### 2. Streaming XML Parser for Huge Files ⭐⭐⭐
**Priority: HIGH**

Handle XML files too large to fit in memory (GB+ files).

```python
from xenon import stream_repair_file

# Process 10GB XML file in chunks
for repaired_chunk, errors in stream_repair_file(
    'huge.xml',
    chunk_size=8192,  # 8KB chunks
    output_file='repaired.xml'
):
    if errors:
        log_errors(errors)
```

**Benefits:**
- Process arbitrarily large XML files
- Constant memory usage
- Essential for ETL pipelines with large datasets

**Implementation:**
- Already have `stream_repair()` for iterators
- Need file-specific wrapper with buffering
- Track repair context across chunks

---

### 3. CLI Tool ⭐⭐
**Priority: MEDIUM**

Command-line interface for quick repairs without writing code.

```bash
# Repair single file
xenon repair input.xml -o output.xml --format pretty

# Batch repair directory
xenon repair-batch ./xml_files/ -o ./repaired/ --parallel

# Validate XML
xenon validate input.xml --schema schema.xsd

# Show diff
xenon diff input.xml repaired.xml --format unified

# Pipe from stdin
cat llm_output.txt | xenon repair --extract-xml > repaired.xml
```

**Benefits:**
- Use Xenon from shell scripts, CI/CD
- No Python code needed for simple tasks
- Integrate with existing Unix pipelines

**Implementation:**
- Use `argparse` for CLI parsing
- Entry point in `pyproject.toml`: `[project.scripts]`
- Support JSON output for programmatic use

---

### 4. XML to JSON Conversion Enhancements ⭐⭐
**Priority: MEDIUM**

Improve `parse_xml()` with more control over JSON output.

```python
from xenon import parse_xml

# Current (v0.6.0)
result = parse_xml('<root><item>test</item></root>')
# {'root': {'item': 'test'}}

# v0.7.0: Configurable conversion
result = parse_xml(
    xml,
    mode='simple',          # 'simple', 'badgerfish', 'gdata'
    array_tags=['item'],    # Force arrays for these tags
    text_key='$text',       # Customize text key (default: '#text')
    attr_key='$attr',       # Customize attribute key (default: '@attributes')
    strip_whitespace=True   # Strip text content whitespace
)
```

**Benefits:**
- Compatible with common JSON-XML conventions
- Better control over output structure
- Handle arrays consistently

**Implementation:**
- Add `XMLToJSONConverter` class with strategies
- Keep `parse_xml()` as simple wrapper
- Add `to_json()` method to RepairReport

---

### 5. Repair Plugins/Hooks System ⭐⭐
**Priority: MEDIUM**

Allow users to add custom repair logic.

```python
from xenon import XMLRepairEngine, RepairHook

class CustomTagFixer(RepairHook):
    """Fix company-specific tag issues."""

    def before_repair(self, xml: str) -> str:
        # Pre-process XML
        return xml.replace('<badtag>', '<goodtag>')

    def after_repair(self, xml: str) -> str:
        # Post-process repaired XML
        return xml.replace('temp-', '')

engine = XMLRepairEngine(hooks=[CustomTagFixer()])
result = engine.repair_xml(llm_output)
```

**Benefits:**
- Extend Xenon without modifying source
- Company-specific repair logic
- A/B test different repair strategies

**Implementation:**
- Define `RepairHook` abstract base class
- Hook points: before_repair, after_repair, on_error
- Add hooks to XMLRepairEngine

---

### 6. Repair Confidence Scoring ⭐
**Priority: LOW**

Score how confident Xenon is about the repair.

```python
from xenon import repair_xml_with_confidence

result, confidence = repair_xml_with_confidence(llm_output)
# confidence: 0.95 (very confident)
# confidence: 0.45 (low confidence - review manually)

if confidence < 0.7:
    send_for_human_review(result)
```

**Confidence factors:**
- Number of repairs made
- Severity of repairs (closing tag vs attribute fix)
- Tag name similarity scores
- Structural complexity

**Benefits:**
- Flag uncertain repairs for human review
- Build automated QA workflows
- Track repair quality over time

---

### 7. XML Diff Visualization Tool ⭐
**Priority: LOW**

Interactive web UI for visualizing repairs.

```bash
# Start web server
xenon serve --port 8000

# Opens browser with UI:
# - Paste XML → See repaired output
# - Side-by-side diff view
# - Repair action log
# - Download repaired XML
```

**Benefits:**
- Debug complex repairs visually
- Demo tool for potential users
- Educational tool

**Implementation:**
- Simple Flask/FastAPI server
- HTML/CSS/JS frontend (no framework needed)
- Use `report.to_html_diff()` from v0.6.0

---

### 8. Performance Optimizations ⭐
**Priority: LOW**

Make Xenon faster for large-scale use.

**Optimizations:**
- Cache compiled regex patterns
- Profile hot paths (entity escaping, tokenization)
- Optimize tag similarity matching (current: difflib, maybe: Levenshtein)
- Add Cython optional dependency for speed

**Target:**
- 2x faster on large XML (1000+ tags)
- 50% less memory usage

---

## Feature Priorities

### Must-Have (v0.7.0 Release Blockers)
1. ✅ XML Schema Validation
2. ✅ Streaming Parser for Huge Files
3. ✅ CLI Tool

### Nice-to-Have (v0.7.0 or v0.7.1)
4. ✅ JSON Conversion Enhancements
5. ✅ Plugin/Hook System

### Future (v0.8.0+)
6. ⏳ Confidence Scoring
7. ⏳ Web UI
8. ⏳ Performance Optimizations

---

## Breaking Changes

**None planned.** v0.7.0 will be fully backward compatible with v0.6.0.

All new features are:
- Opt-in (new functions/flags)
- Additive (don't change existing behavior)
- Gradual (old APIs still work)

---

## Timeline Estimate

Assuming 1-2 devs working:
- **Schema Validation**: 3-5 days
- **Streaming Parser**: 2-3 days
- **CLI Tool**: 3-4 days
- **JSON Enhancements**: 2-3 days
- **Plugin System**: 2-3 days
- **Testing & Docs**: 3-4 days

**Total**: 2-3 weeks for core features

---

## Success Metrics

v0.7.0 is successful if:
- ✅ Can validate repaired XML against XSD schemas
- ✅ Can process multi-GB XML files in constant memory
- ✅ Can use Xenon from command line
- ✅ All v0.6.0 tests still pass
- ✅ No performance regressions
- ✅ 90%+ code coverage maintained

---

## Community Feedback

Before finalizing, gather feedback:
- GitHub Discussions: "What features do you need in v0.7.0?"
- Reddit r/Python: "I built an XML repair library, what's missing?"
- Survey existing users (if any)

**Key question**: What real-world problems are users hitting?

---

## Next Steps

1. ✅ Create this roadmap
2. 🔄 Get community feedback (create GitHub Discussion)
3. 🔄 Prioritize based on feedback
4. 🔄 Create issues for each feature
5. 🔄 Start with highest-priority features
6. 🔄 Release v0.7.0-alpha for early testing
