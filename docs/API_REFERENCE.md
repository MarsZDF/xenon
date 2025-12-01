# Xenon API Reference

Complete reference for all public functions and classes.

---

## Core Repair Functions

### `repair_xml(xml_string: str) -> str`

Basic XML repair without error handling.

**Parameters:**
- `xml_string` (str): Malformed XML string

**Returns:**
- `str`: Repaired XML

**Raises:**
- May raise exceptions for invalid input

**Example:**
```python
from xenon import repair_xml
result = repair_xml('<root><item>test')
# '<root><item>test</item></root>'
```

---

### `repair_xml_safe(...) -> str`

**Recommended for production.** Safe XML repair with comprehensive error handling and all features.

**Parameters:**
- `xml_input` (Union[bytes, str]): XML to repair (v0.6.0: accepts bytes)
- `strict` (bool, default=False): Validate output, raise if invalid
- `allow_empty` (bool, default=False): Accept empty input
- `max_size` (Optional[int], default=None): Max input size in bytes
- **Security flags:**
  - `strip_dangerous_pis` (bool, default=False): Remove <?php ?>, etc.
  - `strip_external_entities` (bool, default=False): XXE prevention
  - `strip_dangerous_tags` (bool, default=False): Remove <script>, etc.
- **v0.5.0 flags:**
  - `wrap_multiple_roots` (bool, default=False): Wrap in <document>
  - `sanitize_invalid_tags` (bool, default=False): Fix invalid tag names
  - `fix_namespace_syntax` (bool, default=False): Fix namespace issues
  - `auto_wrap_cdata` (bool, default=False): Auto-wrap code in CDATA
- **v0.6.0 flags:**
  - `format_output` (Optional[FormatStyle], default=None): 'pretty', 'compact', 'minify'
  - `html_entities` (Optional[str], default=None): 'numeric', 'unicode'
  - `normalize_unicode` (bool, default=False): Apply NFC normalization

**Returns:**
- `str`: Repaired XML

**Raises:**
- `ValidationError`: Invalid input
- `MalformedXMLError`: Can't repair (strict mode only)
- `RepairError`: Internal error

**Example:**
```python
from xenon import repair_xml_safe

# Basic
result = repair_xml_safe('<root>test')

# All features
result = repair_xml_safe(
    b'<root>&euro;50',
    format_output='pretty',
    html_entities='numeric',
    strip_dangerous_pis=True,
    strict=True
)
```

---

### `repair_xml_with_report(xml_string: str) -> Tuple[str, RepairReport]`

Repair XML and get detailed report of changes.

**Parameters:**
- `xml_string` (str): XML to repair

**Returns:**
- `Tuple[str, RepairReport]`: (repaired_xml, report)

**Example:**
```python
from xenon import repair_xml_with_report

result, report = repair_xml_with_report('<root><item>test')
print(f"Made {len(report)} repairs")
for action in report:
    print(f"  - {action.description}")
```

---

### `repair_xml_with_diff(xml_string: str) -> Tuple[str, RepairReport]`

Alias for `repair_xml_with_report()`. v0.6.0.

---

## Parsing Functions

### `parse_xml(xml_string: str) -> Dict[str, Any]`

Parse XML to dictionary.

**Parameters:**
- `xml_string` (str): XML to parse

**Returns:**
- `Dict[str, Any]`: Nested dictionary

**Raises:**
- May raise exceptions for invalid input

**Example:**
```python
from xenon import parse_xml

result = parse_xml('<root><user name="john">Hello</user></root>')
# {'root': {'user': {'@attributes': {'name': 'john'}, '#text': 'Hello'}}}
```

---

### `parse_xml_safe(xml_string: str, ...) -> Dict[str, Any]`

**Recommended for production.** Safely parse malformed XML to dictionary with error handling.

This function repairs the XML using `repair_xml_safe()`, then converts to a dictionary.

**Parameters:**
- `xml_string` (str): XML to parse
- `strict` (bool, default=False): Validate repaired XML structure
- `allow_empty` (bool, default=False): Accept empty input (returns {})
- `max_size` (Optional[int], default=None): Maximum input size in bytes

**Returns:**
- `Dict[str, Any]`: Dictionary representation of the XML

**Raises:**
- `ValidationError`: Invalid input
- `MalformedXMLError`: If strict=True and repair fails
- `RepairError`: Internal error

**Example:**
```python
from xenon import parse_xml_safe

# Parse malformed XML
result = parse_xml_safe('<root><item>test')
# {'root': {'item': 'test'}}

# Handle empty input
result = parse_xml_safe('', allow_empty=True)
# {}
```

---

### `parse_xml_lenient(xml_input: Any) -> Dict[str, Any]`

Parse XML in lenient mode - **never raises exceptions**.

Attempts to parse any input and always returns a dict, even if the input is invalid. Returns empty dict on any error.

**Parameters:**
- `xml_input` (Any): Any input (can be None, int, list, etc.)

**Returns:**
- `Dict[str, Any]`: Dictionary representation, or empty dict on error

**Example:**
```python
from xenon import parse_xml_lenient

# Handles None gracefully
result = parse_xml_lenient(None)
# {}

# Repairs and parses malformed XML
result = parse_xml_lenient('<root><item>test</item>')
# {'root': {'item': 'test'}}

# Returns empty dict on invalid input
result = parse_xml_lenient('invalid')
# {}

# Perfect for fault-tolerant pipelines
for data in untrusted_inputs:
    parsed = parse_xml_lenient(data)
    if parsed:
        process(parsed)
```

---

### `repair_xml_lenient(xml_input: Any) -> str`

Repair XML in lenient mode - **never raises exceptions**.

Attempts to repair any input and always returns a string, even if the input is invalid. Returns empty string on any error.

**Parameters:**
- `xml_input` (Any): Any input (can be None, int, list, etc.)

**Returns:**
- `str`: Repaired XML string, or empty string on error

**Example:**
```python
from xenon import repair_xml_lenient

# Handles None gracefully
result = repair_xml_lenient(None)
# ''

# Converts non-strings
result = repair_xml_lenient(123)
# ''

# Repairs malformed XML
result = repair_xml_lenient('<root><item')
# '<root><item></item></root>'

# Perfect for ETL pipelines with dirty data
for raw_data in messy_inputs:
    xml = repair_xml_lenient(raw_data)
    if xml:
        save_to_db(xml)
```

---

## Formatting Functions (v0.6.0)

### `format_xml(xml_string: str, style: FormatStyle = 'pretty', ...) -> str`

Format XML with various styles.

**Parameters:**
- `xml_string` (str): XML to format
- `style` (FormatStyle): 'pretty', 'compact', or 'minify'
- `indent` (str, default='  '): Indentation (pretty mode)
- `max_line_length` (int, default=100): Line wrapping limit
- `preserve_whitespace` (bool, default=False): Keep significant whitespace

**Returns:**
- `str`: Formatted XML

**Raises:**
- `ValueError`: Unknown style

**Example:**
```python
from xenon import format_xml

pretty = format_xml(xml, style='pretty', indent='    ')
minified = format_xml(xml, style='minify')
```

---

## Entity Functions (v0.6.0)

### `convert_html_entities(text: str, preserve_xml_entities: bool = True) -> str`

Convert HTML entities to numeric XML entities.

**Parameters:**
- `text` (str): Text with HTML entities
- `preserve_xml_entities` (bool, default=True): Keep &lt;, &gt;, etc.

**Returns:**
- `str`: Text with numeric entities

**Example:**
```python
from xenon import convert_html_entities

result = convert_html_entities("&euro;50 &mdash; &copy;2024")
# '&#8364;50 &#8212; &#169;2024'
```

---

### `normalize_entities(text: str, mode: str = 'numeric') -> str`

Normalize all entities to consistent format.

**Parameters:**
- `text` (str): Text with mixed entities
- `mode` (str): 'numeric' or 'unicode'

**Returns:**
- `str`: Normalized text

**Example:**
```python
from xenon import normalize_entities

result = normalize_entities("&euro;50 &#8364;50", mode='numeric')
# '&#8364;50 &#8364;50'
```

---

## Encoding Functions (v0.6.0)

### `detect_encoding(data: Union[bytes, str]) -> Tuple[str, float]`

Detect encoding from BOM or XML declaration.

**Parameters:**
- `data` (Union[bytes, str]): XML data

**Returns:**
- `Tuple[str, float]`: (encoding_name, confidence_0_to_1)

**Example:**
```python
from xenon import detect_encoding

encoding, confidence = detect_encoding(b'\xef\xbb\xbf<root/>')
# ('utf-8-sig', 1.0)
```

---

### `normalize_encoding(data: Union[bytes, str], target_encoding: str = 'utf-8', normalize_unicode: bool = True) -> str`

Normalize data to target encoding.

**Parameters:**
- `data` (Union[bytes, str]): Input data
- `target_encoding` (str, default='utf-8'): Target encoding
- `normalize_unicode` (bool, default=True): Apply NFC normalization

**Returns:**
- `str`: Normalized string

---

## Utility Functions (v0.6.0)

### `decode_xml(xml_bytes: bytes, encoding: Optional[str] = None) -> str`

Decode XML bytes, auto-detecting encoding.

**Parameters:**
- `xml_bytes` (bytes): Raw XML bytes
- `encoding` (Optional[str], default=None): Explicit encoding

**Returns:**
- `str`: Decoded XML

**Example:**
```python
from xenon import decode_xml

xml = decode_xml(b'\xef\xbb\xbf<root>test</root>')
```

---

### `batch_repair(xml_strings: List[str], *, show_progress: bool = False, on_error: str = 'skip', **repair_kwargs) -> List[Tuple[str, Optional[Exception]]]`

Repair multiple XMLs in batch.

**Parameters:**
- `xml_strings` (List[str]): XMLs to repair
- `show_progress` (bool, default=False): Show progress
- `on_error` (str, default='skip'): 'skip', 'raise', or 'return_empty'
- `**repair_kwargs`: Passed to `repair_xml_safe()`

**Returns:**
- `List[Tuple[str, Optional[Exception]]]`: [(xml, error), ...]

**Example:**
```python
from xenon import batch_repair

results = batch_repair(['<root>test1', '<root>test2</root>'])
for xml, error in results:
    if error:
        print(f"Failed: {error}")
```

---

### `batch_repair_with_reports(xml_strings: List[str], *, show_progress: bool = False, filter_func: Optional[Callable] = None) -> List[Tuple[str, RepairReport]]`

Batch repair with detailed reports.

**Parameters:**
- `xml_strings` (List[str]): XMLs to repair
- `show_progress` (bool, default=False): Show progress
- `filter_func` (Optional[Callable], default=None): Filter results

**Returns:**
- `List[Tuple[str, RepairReport]]`: [(xml, report), ...]

---

### `stream_repair(xml_iterator: Iterator[str], **repair_kwargs) -> Iterator[Tuple[str, Optional[Exception]]]`

Stream repair for large datasets.

**Parameters:**
- `xml_iterator` (Iterator[str]): Iterator yielding XMLs
- `**repair_kwargs`: Passed to `repair_xml_safe()`

**Yields:**
- `Tuple[str, Optional[Exception]]`: (xml, error)

**Example:**
```python
from xenon import stream_repair

def xml_gen():
    for i in range(10000):
        yield f'<item id="{i}">data{i}'

for xml, error in stream_repair(xml_gen()):
    if not error:
        process(xml)
```

---

### `validate_xml_structure(xml_string: str) -> Tuple[bool, List[str]]`

Lightweight XML structure validation.

**Parameters:**
- `xml_string` (str): XML to validate

**Returns:**
- `Tuple[bool, List[str]]`: (is_valid, issues)

**Example:**
```python
from xenon import validate_xml_structure

is_valid, issues = validate_xml_structure('<root><item>test')
if not is_valid:
    print(f"Issues: {issues}")
```

---

### `extract_text_content(xml_string: str) -> str`

Extract plain text from XML, removing all tags.

**Parameters:**
- `xml_string` (str): XML string

**Returns:**
- `str`: Plain text

**Example:**
```python
from xenon import extract_text_content

text = extract_text_content('<root><p>Hello</p><p>World</p></root>')
# 'HelloWorld'
```

---

## Error Context Helpers (v0.6.0)

### `get_line_column(text: str, position: int) -> Tuple[int, int]`

Convert character position to line/column.

**Parameters:**
- `text` (str): Full text
- `position` (int): Character position (0-indexed)

**Returns:**
- `Tuple[int, int]`: (line, column) both 1-indexed

**Example:**
```python
from xenon import get_line_column

line, col = get_line_column("line1\nline2\nline3", 8)
# (2, 3)
```

---

### `get_context_snippet(text: str, position: int, max_length: int = 50) -> str`

Extract context snippet around a position.

**Parameters:**
- `text` (str): Full text
- `position` (int): Character position (0-indexed)
- `max_length` (int, default=50): Max snippet length

**Returns:**
- `str`: Context snippet

**Example:**
```python
from xenon import get_context_snippet

snippet = get_context_snippet("Hello world test", 6, max_length=20)
# 'Hello world...'
```

---

## Exception Classes

### `XenonException(message, line=None, column=None, context=None)`

Base exception for all Xenon errors.

**Attributes:**
- `line` (Optional[int]): Line number (1-indexed)
- `column` (Optional[int]): Column number (1-indexed)
- `context` (Optional[str]): Surrounding text

**Example:**
```python
from xenon import XenonException

try:
    repair_xml_safe(bad_xml)
except XenonException as e:
    print(f"Error at line {e.line}, column {e.column}")
    print(f"Context: {e.context}")
```

---

### `ValidationError`

Raised when input validation fails.

**When raised:**
- Wrong input type (not str/bytes)
- Empty input when `allow_empty=False`
- Input too large (exceeds `max_size`)

---

### `MalformedXMLError`

Raised when XML is too malformed to repair (strict mode only).

**When raised:**
- `strict=True` and output is still invalid after repair

---

### `RepairError`

Raised on internal repair errors.

**When raised:**
- Unexpected error during repair process
- May indicate a bug in Xenon

---

## Advanced Classes

### `XMLRepairEngine(...)`

Low-level repair engine for advanced use cases.

**Parameters:**
All the same flags as `repair_xml_safe()`, or:
- `config` (XMLRepairConfig): Configuration object

**Methods:**
- `repair_xml(xml_string: str) -> str`
- `xml_to_dict(xml_string: str) -> Dict[str, Any]`

**Example:**
```python
from xenon import XMLRepairEngine

engine = XMLRepairEngine(strip_dangerous_pis=True)
result = engine.repair_xml('<root>test')
```

---

### `SecurityFlags` (Flag Enum)

Security feature flags for bitwise operations.

**Values:**
- `NONE` - No security features (default)
- `STRIP_DANGEROUS_PIS` - Remove dangerous processing instructions (<?php ?>, etc.)
- `STRIP_EXTERNAL_ENTITIES` - Remove external entities (XXE prevention)
- `STRIP_DANGEROUS_TAGS` - Remove dangerous tags (<script>, <iframe>, etc.)

**Usage:**
```python
from xenon import SecurityFlags, XMLRepairConfig

# Single flag
config = XMLRepairConfig(security=SecurityFlags.STRIP_DANGEROUS_PIS)

# Multiple flags (bitwise OR)
config = XMLRepairConfig(
    security=SecurityFlags.STRIP_DANGEROUS_PIS | SecurityFlags.STRIP_EXTERNAL_ENTITIES
)

# All security features
config = XMLRepairConfig(
    security=SecurityFlags.STRIP_DANGEROUS_PIS
    | SecurityFlags.STRIP_EXTERNAL_ENTITIES
    | SecurityFlags.STRIP_DANGEROUS_TAGS
)
```

---

### `RepairFlags` (Flag Enum)

Repair feature flags for bitwise operations.

**Values:**
- `NONE` - No special repairs (default)
- `WRAP_MULTIPLE_ROOTS` - Wrap multiple root elements in <document>
- `SANITIZE_INVALID_TAGS` - Fix invalid tag names (starts with number, spaces, etc.)
- `FIX_NAMESPACE_SYNTAX` - Fix invalid namespace syntax (multiple colons)
- `AUTO_WRAP_CDATA` - Auto-wrap code content in CDATA sections

**Usage:**
```python
from xenon import RepairFlags, XMLRepairConfig

# Single flag
config = XMLRepairConfig(repair=RepairFlags.SANITIZE_INVALID_TAGS)

# Multiple flags (bitwise OR)
config = XMLRepairConfig(
    repair=RepairFlags.SANITIZE_INVALID_TAGS | RepairFlags.AUTO_WRAP_CDATA
)

# All repair features
config = XMLRepairConfig(
    repair=RepairFlags.WRAP_MULTIPLE_ROOTS
    | RepairFlags.SANITIZE_INVALID_TAGS
    | RepairFlags.FIX_NAMESPACE_SYNTAX
    | RepairFlags.AUTO_WRAP_CDATA
)
```

---

### `XMLRepairConfig(...)`

Configuration object (v0.5.0+).

**Parameters:**
- `security` (SecurityFlags, default=SecurityFlags.NONE): Security features to enable
- `repair` (RepairFlags, default=RepairFlags.NONE): Repair features to enable
- `match_threshold` (int, default=2): Tag matching threshold for autocorrection

**Methods:**

**`from_booleans(**kwargs) -> XMLRepairConfig`** (classmethod)
Create config from individual boolean parameters (backward compatible).

```python
from xenon import XMLRepairConfig

config = XMLRepairConfig.from_booleans(
    strip_dangerous_pis=True,
    strip_external_entities=True,
    sanitize_invalid_tags=True,
    auto_wrap_cdata=True
)
```

**`has_security_feature(flag: SecurityFlags) -> bool`**
Check if a security feature is enabled.

```python
config = XMLRepairConfig(security=SecurityFlags.STRIP_DANGEROUS_PIS)
if config.has_security_feature(SecurityFlags.STRIP_DANGEROUS_PIS):
    print("PI stripping enabled")
```

**`has_repair_feature(flag: RepairFlags) -> bool`**
Check if a repair feature is enabled.

**`has_any_feature() -> bool`**
Check if any non-default features are enabled.

**Example:**
```python
from xenon import XMLRepairConfig, SecurityFlags, RepairFlags, XMLRepairEngine

# Using flags (recommended for multiple features)
config = XMLRepairConfig(
    security=SecurityFlags.STRIP_DANGEROUS_PIS | SecurityFlags.STRIP_EXTERNAL_ENTITIES,
    repair=RepairFlags.SANITIZE_INVALID_TAGS | RepairFlags.AUTO_WRAP_CDATA
)

engine = XMLRepairEngine(config=config)
result = engine.repair_xml('<root><?php code ?><123tag>test</123tag></root>')
```

---

### `RepairType` (Enum)

Enumeration of all repair types performed by Xenon.

**Values:**
- `TRUNCATION` - Fixed truncated/incomplete XML
- `CONVERSATIONAL_FLUFF` - Removed non-XML text
- `MALFORMED_ATTRIBUTE` - Fixed attribute syntax
- `UNESCAPED_ENTITY` - Escaped special characters (&, <, >)
- `CDATA_WRAPPED` - Wrapped content in CDATA sections
- `TAG_TYPO` - Fixed tag name typos
- `TAG_CASE_MISMATCH` - Fixed mismatched tag case
- `NAMESPACE_INJECTED` - Fixed namespace issues
- `DUPLICATE_ATTRIBUTE` - Removed duplicate attributes
- `INVALID_TAG_NAME` - Fixed invalid tag names
- `INVALID_NAMESPACE` - Fixed invalid namespace syntax
- `MULTIPLE_ROOTS` - Wrapped multiple root elements
- `DANGEROUS_PI_STRIPPED` - Removed dangerous processing instructions
- `DANGEROUS_TAG_STRIPPED` - Removed dangerous tags
- `EXTERNAL_ENTITY_STRIPPED` - Removed external entities (XXE prevention)

**Example:**
```python
from xenon import repair_xml_with_report, RepairType

result, report = repair_xml_with_report(xml)
for action in report.actions:
    if action.repair_type == RepairType.TRUNCATION:
        print(f"Fixed truncation: {action.description}")
```

---

### `RepairAction` (Dataclass)

Represents a single repair action taken during XML repair.

**Fields:**
- `repair_type` (RepairType): Type of repair performed
- `description` (str): Human-readable description
- `location` (str, optional): Location info (line, tag, etc.)
- `before` (str, optional): Original text
- `after` (str, optional): Repaired text

**Example:**
```python
from xenon import repair_xml_with_report

result, report = repair_xml_with_report('<root><item')
for action in report.actions:
    print(f"Type: {action.repair_type.value}")
    print(f"Description: {action.description}")
    if action.before:
        print(f"Changed '{action.before}' → '{action.after}'")
```

---

### `RepairReport`

Detailed report of repair actions with comprehensive analysis methods.

**Properties:**
- `original_xml` (str): Original XML
- `repaired_xml` (str): Repaired XML
- `actions` (List[RepairAction]): List of repairs performed

**Methods:**

#### Analysis Methods

**`summary() -> str`**
Get human-readable summary of all repairs.

```python
result, report = repair_xml_with_report(xml)
print(report.summary())
# Performed 2 repair(s):
#   - [truncation] Added closing tags
#   - [unescaped_entity] Escaped & character
```

**`by_type() -> Dict[RepairType, List[RepairAction]]`**
Group actions by repair type.

```python
result, report = repair_xml_with_report(xml)
grouped = report.by_type()
for repair_type, actions in grouped.items():
    print(f"{repair_type.value}: {len(actions)} repairs")
```

**`statistics() -> Dict[str, int]`**
Get statistics about repairs performed.

```python
result, report = repair_xml_with_report(xml)
stats = report.statistics()
print(f"Total repairs: {stats['total_repairs']}")
print(f"Truncation fixes: {stats.get('truncation_count', 0)}")
```

**`to_dict() -> Dict[str, Any]`**
Convert report to dictionary for JSON serialization.

```python
import json
result, report = repair_xml_with_report(xml)
json_data = json.dumps(report.to_dict(), indent=2)
```

**`has_security_issues() -> bool`**
Check if any security-related repairs were performed.

```python
result, report = repair_xml_with_report(untrusted_xml)
if report.has_security_issues():
    log.warning("Security repairs performed - review input source")
```

**`add_action(repair_type, description, location="", before="", after="") -> None`**
Add a repair action (used internally by Xenon).

#### Diff Methods

**`to_unified_diff(context_lines=3) -> str`**
Generate unified diff format showing changes.

```python
result, report = repair_xml_with_report(xml)
diff = report.to_unified_diff()
print(diff)
# --- Original
# +++ Repaired
# @@ -1 +1 @@
# -<root><item
# +<root><item></item></root>
```

**`to_context_diff(context_lines=3) -> str`**
Generate context diff format.

**`to_html_diff(table_style=True) -> str`**
Generate HTML diff with color-coded changes.

```python
result, report = repair_xml_with_report(xml)
html = report.to_html_diff()
with open('diff.html', 'w') as f:
    f.write(html)
```

**`get_diff_summary() -> Dict[str, Any]`**
Get summary statistics about the diff.

```python
result, report = repair_xml_with_report(xml)
stats = report.get_diff_summary()
print(f"Similarity: {stats['similarity_ratio']:.1%}")
print(f"Lines added: {stats['lines_added']}")
```

#### Magic Methods

**`__len__() -> int`**
Number of repairs performed.

```python
result, report = repair_xml_with_report(xml)
print(f"Made {len(report)} repairs")
```

**`__bool__() -> bool`**
Report is truthy if any repairs were performed.

```python
result, report = repair_xml_with_report(xml)
if report:
    print("Repairs were needed")
else:
    print("XML was already valid")
```

---

## Type Hints

```python
from typing import Dict, Any, List, Tuple, Optional, Iterator, Union, Callable
from xenon import FormatStyle

# FormatStyle is Literal['pretty', 'compact', 'minify']
```

---

## Constants

### Supported HTML Entities

40+ entities including:
- Typography: `nbsp`, `copy`, `reg`, `trade`, `euro`, `pound`, `yen`
- Dashes/quotes: `ndash`, `mdash`, `lsquo`, `rsquo`, `ldquo`, `rdquo`
- Math: `times`, `divide`, `plusmn`, `deg`, `frac14`, `frac12`, `frac34`
- Arrows: `larr`, `rarr`, `uarr`, `darr`
- Greek: `alpha`, `beta`, `gamma`, `delta`, `pi`, `sigma`
- Special: `sect`, `hellip`, `bull`

---

## Version Information

```python
import xenon
print(xenon.__version__)  # '0.6.0'
```

---

## Full Import Reference

```python
# Core functions
from xenon import (
    repair_xml,
    repair_xml_safe,
    repair_xml_lenient,
    repair_xml_with_report,
    repair_xml_with_diff,
    parse_xml,
    parse_xml_safe,
    parse_xml_lenient,
)

# v0.6.0: Formatting
from xenon import format_xml, FormatStyle

# v0.6.0: Entities
from xenon import convert_html_entities, normalize_entities

# v0.6.0: Encoding
from xenon import detect_encoding, normalize_encoding

# v0.6.0: Utilities
from xenon import (
    decode_xml,
    batch_repair,
    batch_repair_with_reports,
    stream_repair,
    validate_xml_structure,
    extract_text_content,
)

# v0.6.0: Error context
from xenon import get_line_column, get_context_snippet

# Exceptions
from xenon import (
    XenonException,
    ValidationError,
    MalformedXMLError,
    RepairError,
)

# Advanced
from xenon import (
    XMLRepairEngine,
    XMLRepairConfig,
    SecurityFlags,
    RepairFlags,
    RepairReport,
    RepairAction,
    RepairType,
)
```

---

## See Also

- [Cookbook](COOKBOOK.md) - Practical recipes
- [Performance Guide](PERFORMANCE.md) - Optimization tips
- [README](../README.md) - Overview and quick start
