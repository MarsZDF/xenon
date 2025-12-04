# Changelog

All notable changes to Xenon will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **🚀 Async/Await Support**: Native async streaming for modern Python ecosystems
  - `feed_async()`: Async variant of `feed()` for use with `async for` loops
  - `finalize_async()`: Async variant of `finalize()`
  - Async context manager support (`async with StreamingXMLRepair(...)`)
  - Fully compatible with any async LLM SDK or streaming framework
  - Zero blocking - yields control to event loop for responsive concurrent operations
  - 18 comprehensive async tests ensuring reliability
- **Integration Examples**: New `examples/04_async_llm_integration.py` with 6 real-world patterns:
  - Generic async LLM streaming integration
  - Real-time error recovery streaming
  - Async pipeline integration (works with any async framework)
  - Concurrent stream processing
  - Error handling in async contexts
  - Performance monitoring

### Changed
- Updated dev dependencies: Added `pytest-asyncio>=0.21.0` for async test support
- Streaming module now imports `asyncio` for async functionality
- Documentation updated with async examples in module docstrings

### Performance
- Async operations are non-blocking and don't interfere with event loop
- Concurrent stream processing tested with 10+ simultaneous repairs
- Throughput maintained: ~800 chunks/sec, ~13 KB/sec per stream

### Documentation
- Added comprehensive async examples showing real-world integration patterns
- Updated `StreamingXMLRepair` docstring with both sync and async usage
- Added performance monitoring example showing metrics tracking

## [1.0.0] - 2025-12-03

### 🔒 BREAKING CHANGES

**This release introduces mandatory trust levels for secure-by-default XML repair. All code using Xenon must be updated.**

#### Required Changes
- All core functions now require a `trust` parameter:
  - `repair_xml_safe(xml)` → `repair_xml_safe(xml, trust=TrustLevel.UNTRUSTED)`
  - `parse_xml_safe(xml)` → `parse_xml_safe(xml, trust=TrustLevel.UNTRUSTED)`
  - `batch_repair([xml])` → `batch_repair([xml], trust=TrustLevel.UNTRUSTED)`
  - `StreamingXMLRepair()` → `StreamingXMLRepair(trust=TrustLevel.UNTRUSTED)`
- Must import `TrustLevel` enum: `from xenon import TrustLevel`

#### Migration Guide
1. Add `TrustLevel` to imports: `from xenon import repair_xml_safe, TrustLevel`
2. Add `trust` parameter to all function calls
3. Choose appropriate trust level:
   - **`TrustLevel.UNTRUSTED`**: LLM output, user uploads, external APIs (DEFAULT - use this when unsure)
   - **`TrustLevel.INTERNAL`**: Internal services, config files, database exports
   - **`TrustLevel.TRUSTED`**: Test fixtures, hardcoded literals only

#### Why This Change?
Making trust explicit forces security thinking at the point of use, creating a "pit of success" that makes insecure code harder to write accidentally.

### Added
- **Trust Level System** (`TrustLevel` enum):
  - `TrustLevel.UNTRUSTED`: Maximum security for untrusted sources
    - Strips dangerous PIs (<?php ?>, <?asp ?>, <?jsp ?>)
    - Strips external entities (XXE prevention)
    - Strips dangerous tags (<script>, <iframe>, <object>, <embed>)
    - Max depth limit: 1000 (DoS prevention)
    - Enables strict validation and threat auditing
  - `TrustLevel.INTERNAL`: Moderate security for internal sources
    - Strips external entities (defense in depth)
    - Max depth limit: 10000
  - `TrustLevel.TRUSTED`: No security overhead for known-good data
    - All security checks disabled
    - Maximum performance
- **`SecurityError` Exception**: Raised when security limits exceeded
  - Max depth violations
  - Entity expansion attacks
  - Other security circuit breakers
- **`XMLRepairEngine.from_trust_level()` Factory Method**:
  - Create pre-configured engines from trust levels
  - Example: `engine = XMLRepairEngine.from_trust_level(TrustLevel.UNTRUSTED)`
- **Streaming Security Filtering**:
  - `StreamingXMLRepair` now respects trust-level security settings
  - Dangerous PIs filtered in real-time during streaming
- **Audit Mode and Threat Detection** (`xenon.audit` module):
  - `ThreatDetector`: Detect and classify security threats in XML input
    - Detects XXE attempts, dangerous PIs, XSS vectors, entity bombs, deep nesting
    - Provides severity levels (LOW, MEDIUM, HIGH, CRITICAL)
    - Context extraction for threat locations
  - `AuditLogger`: Log security-relevant operations for compliance and debugging
    - Tracks trust levels, threats detected, actions taken
    - JSON export for integration with SIEM systems
    - Can be disabled for performance-sensitive applications
  - `SecurityMetrics`: Track security metrics over time
    - Counters for detected and blocked threats
    - Statistics by trust level
    - Uptime and timestamp tracking
  - 29 comprehensive audit tests with 96% code coverage
- **Comprehensive Trust Level Tests**:
  - 13 new security tests validating trust level enforcement
  - Tests for UNTRUSTED, INTERNAL, and TRUSTED behaviors
  - Factory method tests
  - Streaming security tests
  - Total test count: 461 tests (419 original + 13 security + 29 audit)

### Changed
- **Security Model**: Secure-by-default with explicit trust levels (BREAKING)
- **Function Signatures**: All core functions require `trust` parameter (BREAKING)
- **Parser Exceptions**: Max depth violations now raise `SecurityError` instead of `RepairError`
- **Documentation**: Complete rewrite of README.md for v1.0.0 security model
  - Added prominent v1.0.0 breaking changes section
  - Trust level usage guide with examples
  - Migration guide for v0.x → v1.0.0
  - Updated all code examples to include trust parameter
- **Test Suite**: All 419 existing tests updated to use trust levels

### Deprecated
- `repair_xml()` - Use `repair_xml_safe(xml, trust=TrustLevel.TRUSTED)` instead
- `parse_xml()` - Use `parse_xml_safe(xml, trust=TrustLevel.TRUSTED)` instead
- **Note**: Deprecated functions will be removed in v2.0.0

### Security
- **Defense in Depth**: Trust levels provide layered security appropriate for input source
- **Pit of Success**: API design makes insecure choices difficult
- **Explicit Security**: No more "opt-in" security flags that developers forget to enable
- **Circuit Breakers**: Automatic limits prevent DoS attacks via deeply nested XML

### Performance
- `TrustLevel.UNTRUSTED`: ~15-20% slower than v0.x (security overhead)
- `TrustLevel.INTERNAL`: ~5% slower than v0.x (minimal security overhead)
- `TrustLevel.TRUSTED`: Identical to v0.x performance (no security checks)

### Documentation
- Complete README.md rewrite with v1.0.0 security model
- Added migration guide in README.md
- Updated all examples to show trust levels
- Function reference updated with trust parameter documentation
- Enhanced security model documentation

### Usage: Audit Mode Example
```python
from xenon import repair_xml_safe, TrustLevel, ThreatDetector, AuditLogger, SecurityMetrics

# Create audit components
detector = ThreatDetector()
logger = AuditLogger()
metrics = SecurityMetrics()

# Process untrusted XML with auditing
untrusted_xml = '<?php hack ?><root><script>XSS</script></root>'

# Detect threats
threats = detector.detect_threats(untrusted_xml)
for threat in threats:
    print(f"{threat.severity.value.upper()}: {threat.description}")

# Repair with trust level
result = repair_xml_safe(untrusted_xml, trust=TrustLevel.UNTRUSTED)

# Log the operation
logger.log_repair_operation(
    xml_input=untrusted_xml,
    xml_output=result,
    trust_level="untrusted",
    threats=threats,
    actions_taken=["Stripped PHP PI", "Stripped script tag"]
)

# Record metrics
metrics.record_threats(threats)
metrics.increment("untrusted_inputs_processed")

# Get statistics
stats = metrics.get_stats()
print(f"Total threats detected: {stats['counters']['total_threats_detected']}")

# Export audit log as JSON
import json
audit_json = json.dumps(logger.to_json(), indent=2)
```

## [0.7.0] - 2025-12-02

### Added
- **Streaming XML Repair** (`StreamingXMLRepair`): Real-time token-by-token XML repair for LLM streaming output
  - Near-zero latency: Yields XML as tokens arrive, no waiting for full completion
  - Constant memory usage: Small buffer (~200 bytes) instead of full XML in memory
  - Handles chunk boundaries: Tags and attributes can be split across chunks
  - Conversational fluff stripping: Automatically discards text before first `<` tag
  - Context manager support: Auto-finalize prevents unclosed tags
  - Production-ready: Integrates attribute quoting, entity escaping, and truncation repair
  - 48 comprehensive tests with 94% code coverage
  - Note: Currently sync-only; async support planned for future release
- `StreamState` enum for tracking streaming parser state machine
- Comprehensive streaming documentation in README and design docs

### Technical Details
- State machine with 6 states: INITIAL, IN_TEXT, IN_TAG, IN_COMMENT, IN_CDATA, IN_PI
- Invalid tag detection: Correctly handles `<10` from text like `"5 < 10"`
- Tag stack management for case-insensitive closing tag matching
- Reuses 60% of existing repair engine code (attribute quoting, entity escaping)

### Changed
- Updated README with v0.7.0 streaming examples and feature highlights
- Version bumped to 0.7.0 in `__init__.py` and `pyproject.toml`

### Documentation
- Added "What's New in v0.7.0" section to README with examples
- See `docs/STREAMING_DESIGN.md` for detailed architecture
- See `docs/STREAMING_ANALYSIS.md` for feasibility study and performance analysis
- See `docs/ROADMAP_v0.7.0.md` for feature roadmap

## [0.6.0] - 2025-11-26

### Added
- **Diff/Patch Reporting**: Compare original and repaired XML
  - `repair_xml_with_diff()` function (alias for `repair_xml_with_report()`)
  - Unified diff format (`report.to_unified_diff()`)
  - Context diff format (`report.to_context_diff()`)
  - HTML diff visualization (`report.to_html_diff()`)
  - Diff statistics (`report.get_diff_summary()`)
- **XML Formatting**: Control output formatting
  - `format_xml()` function with 3 styles: 'pretty', 'minify', 'compact'
  - Integrated with `repair_xml_safe(format_output='pretty')`
  - Configurable indentation for pretty-printing
- **HTML Entity Support**: Handle HTML entities from web-trained LLMs
  - `convert_html_entities()` - Convert HTML entities to numeric XML entities
  - `normalize_entities()` - Normalize all entities with mode selection
  - Support for 40+ common HTML entities (nbsp, copy, euro, mdash, etc.)
  - Integrated with `repair_xml_safe(html_entities='numeric'|'unicode')`
- **Encoding Detection**: Auto-detect and normalize encodings
  - `detect_encoding()` - Detect from BOM or XML declaration
  - `normalize_encoding()` - Convert to UTF-8 with optional Unicode normalization
  - `decode_xml()` - Auto-detect and decode bytes input
  - Bytes input support: `repair_xml_safe(b'<root>...')`
- **Utility Functions**: Powerful helpers for common tasks
  - `batch_repair()` - Process multiple XML strings
  - `batch_repair_with_reports()` - Batch processing with repair reports
  - `stream_repair()` - Streaming for large datasets (file-based)
  - `validate_xml_structure()` - Lightweight validation
  - `extract_text_content()` - Extract plain text from XML
- **Enhanced Error Messages**: Line/column context in exceptions
  - `get_line_column()` helper function
  - `get_context_snippet()` helper function
  - All exceptions include position information when available

### Changed
- `repair_xml_safe()` now accepts bytes input
- `repair_xml_safe()` gained new parameters: `format_output`, `html_entities`, `normalize_unicode`
- Version bumped to 0.6.0

### Documentation
- Added COOKBOOK.md with 15+ practical recipes
- Updated README with v0.6.0 feature showcase
- Added comprehensive examples for all new features

## [0.5.0] - 2025-11-20

### Added
- **XML Compliance Features**:
  - `sanitize_invalid_tags`: Fix invalid tag names (starts with number, contains spaces)
  - `fix_namespace_syntax`: Fix invalid namespace syntax (double colons, multiple segments)
  - `wrap_multiple_roots`: Wrap multiple root elements in synthetic `<document>` root
  - `auto_wrap_cdata`: Automatically wrap code content in CDATA sections
- **Advanced Configuration**:
  - `XMLRepairConfig` class for centralized configuration
  - `SecurityFlags` dataclass for security settings
  - `RepairFlags` dataclass for repair behavior settings
- **Improved Entity Escaping**: No double-escaping of existing entities
- **Reporting System**:
  - `RepairReport` class for tracking repairs
  - `RepairAction` dataclass for individual repair actions
  - `RepairType` enum with 15 repair types
  - `repair_xml_with_report()` function

### Changed
- Improved tag similarity matching algorithm
- Better handling of nested tags with same name
- More robust attribute quoting
- Version bumped to 0.5.0

### Documentation
- Added API_REFERENCE.md with complete API documentation
- Updated README with v0.5.0 features
- Added configuration examples

## [0.2.0] - 2025-11-15

### Added
- **Security Features**:
  - `strip_dangerous_pis`: Remove dangerous processing instructions (PHP, ASP, JSP)
  - `strip_external_entities`: Strip external entity declarations (XXE prevention)
  - `strip_dangerous_tags`: Remove dangerous tags (script, iframe, object, embed)
- **Smart Tag Matching**: Levenshtein distance for typo detection in closing tags
- **Case-Insensitive Matching**: Handles mismatched tag case
- **Comprehensive Test Suite**: 300+ tests with property-based testing

### Changed
- Improved truncation handling
- Better attribute quoting algorithm
- Version bumped to 0.2.0

### Documentation
- Added SECURITY.md with threat model
- Expanded README with security examples

## [0.1.0] - 2025-11-10

### Added
- Initial release
- Core XML repair functionality:
  - Truncation repair (auto-close open tags)
  - Conversational fluff stripping
  - Malformed attribute quoting
  - Unescaped entity escaping
- Three repair modes: `repair_xml()`, `repair_xml_safe()`, `repair_xml_lenient()`
- Dictionary parsing: `parse_xml()`, `parse_xml_safe()`, `parse_xml_lenient()`
- Stack-based parser with deterministic behavior
- Zero dependencies (Python Standard Library only)
- Basic test coverage

### Documentation
- README with quick start guide
- Examples of common use cases

---

**Note**: GitHub releases will be created when tags are pushed to the repository.
