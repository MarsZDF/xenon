"""Performance benchmarks for Xenon XML repair library.

Run with: pytest tests/test_benchmarks.py -v
Mark as slow: pytest -m "not slow" to skip these
"""

import time

import pytest

from xenon import (
    TrustLevel,
    batch_repair,
    convert_html_entities,
    detect_encoding,
    format_xml,
    normalize_entities,
    repair_xml_safe,
)

# Test data of varying sizes
SMALL_XML = "<root><item>test</item></root>"
SMALL_TRUNCATED = "<root><item>test"
SMALL_WITH_ENTITIES = "<p>&euro;50 &mdash; &copy;2024</p>"

MEDIUM_XML = "<root>" + "".join(f'<item id="{i}">data{i}</item>' for i in range(100)) + "</root>"
MEDIUM_TRUNCATED = "<root>" + "".join(f'<item id="{i}">data{i}</item>' for i in range(100))

LARGE_XML = "<root>" + "".join(f'<item id="{i}">data{i}</item>' for i in range(1000)) + "</root>"
LARGE_TRUNCATED = "<root>" + "".join(f'<item id="{i}">data{i}</item>' for i in range(1000))


@pytest.mark.benchmark
class TestRepairBenchmarks:
    """Benchmark core repair operations."""

    def test_repair_small_valid(self):
        """Benchmark repairing small valid XML."""
        start = time.perf_counter()
        result = repair_xml_safe(SMALL_XML, trust=TrustLevel.TRUSTED)
        elapsed = time.perf_counter() - start
        assert "<root>" in result
        assert elapsed < 0.1  # Should be very fast

    def test_repair_small_truncated(self):
        """Benchmark repairing small truncated XML."""
        start = time.perf_counter()
        result = repair_xml_safe(SMALL_TRUNCATED, trust=TrustLevel.TRUSTED)
        elapsed = time.perf_counter() - start
        assert "</root>" in result
        assert elapsed < 0.1

    def test_repair_medium_valid(self):
        """Benchmark repairing medium valid XML."""
        start = time.perf_counter()
        result = repair_xml_safe(MEDIUM_XML, trust=TrustLevel.TRUSTED)
        elapsed = time.perf_counter() - start
        assert "<root>" in result
        assert elapsed < 0.5

    def test_repair_medium_truncated(self):
        """Benchmark repairing medium truncated XML."""
        start = time.perf_counter()
        result = repair_xml_safe(MEDIUM_TRUNCATED, trust=TrustLevel.TRUSTED)
        elapsed = time.perf_counter() - start
        assert "</root>" in result
        assert elapsed < 0.5

    def test_repair_large_valid(self):
        """Benchmark repairing large valid XML."""
        start = time.perf_counter()
        result = repair_xml_safe(LARGE_XML, trust=TrustLevel.TRUSTED)
        elapsed = time.perf_counter() - start
        assert "<root>" in result
        assert elapsed < 1.0  # 1000 items should still be under 1 second

    def test_repair_large_truncated(self):
        """Benchmark repairing large truncated XML."""
        start = time.perf_counter()
        result = repair_xml_safe(LARGE_TRUNCATED, trust=TrustLevel.TRUSTED)
        elapsed = time.perf_counter() - start
        assert "</root>" in result
        assert elapsed < 1.0


@pytest.mark.benchmark
class TestFormattingBenchmarks:
    """Benchmark XML formatting operations (v0.6.0)."""

    def test_format_pretty_small(self):
        """Benchmark pretty-printing small XML."""
        result = format_xml(SMALL_XML, style="pretty")
        assert "<root>" in result

    def test_format_minify_medium(self):
        """Benchmark minifying medium XML."""
        result = format_xml(MEDIUM_XML, style="minify")
        assert "<root>" in result


@pytest.mark.benchmark
class TestEntityBenchmarks:
    """Benchmark HTML entity conversion (v0.6.0)."""

    def test_convert_entities_to_numeric(self):
        """Benchmark converting HTML entities to numeric."""
        result = convert_html_entities(SMALL_WITH_ENTITIES)
        assert "&#" in result

    def test_normalize_entities_to_unicode(self):
        """Benchmark normalizing entities to Unicode."""
        result = normalize_entities(SMALL_WITH_ENTITIES, mode="unicode")
        assert isinstance(result, str)


@pytest.mark.benchmark
class TestEncodingBenchmarks:
    """Benchmark encoding detection (v0.6.0)."""

    def test_detect_encoding_utf8(self):
        """Benchmark detecting UTF-8 encoding."""
        xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?><root>test</root>'
        encoding, _confidence = detect_encoding(xml_bytes)
        assert encoding.lower() == "utf-8"

    def test_detect_encoding_with_bom(self):
        """Benchmark detecting encoding with BOM."""
        xml_bytes = b"\xef\xbb\xbf<root>test</root>"
        encoding, _confidence = detect_encoding(xml_bytes)
        assert "utf-8" in encoding.lower()


@pytest.mark.benchmark
class TestBatchBenchmarks:
    """Benchmark batch processing operations (v0.6.0)."""

    def test_batch_repair_100_items(self):
        """Benchmark batch repair of 100 items."""
        xml_batch = [f"<root><item>{i}</item></root>" for i in range(100)]
        start = time.perf_counter()
        results = batch_repair(xml_batch, trust=TrustLevel.TRUSTED)
        elapsed = time.perf_counter() - start
        assert len(results) == 100
        assert elapsed < 2.0  # 100 items in under 2 seconds


@pytest.mark.benchmark
class TestIntegratedBenchmarks:
    """Benchmark integrated v0.6.0 features."""

    def test_repair_with_formatting(self):
        """Benchmark repair + formatting."""
        result = repair_xml_safe(MEDIUM_TRUNCATED, trust=TrustLevel.TRUSTED, format_output="pretty")
        assert "</root>" in result

    def test_repair_bytes_with_all_features(self):
        """Benchmark bytes input with all v0.6.0 features."""
        xml_bytes = b"<root><p>&euro;50</p><item>data"
        result = repair_xml_safe(
            xml_bytes,
            trust=TrustLevel.TRUSTED,
            format_output="compact",
            html_entities="numeric",
            normalize_unicode=True,
        )
        assert "</item>" in result


@pytest.mark.benchmark
class TestRegressionBenchmarks:
    """Regression benchmarks to track performance over time."""

    def test_typical_llm_output_repair(self):
        """Benchmark typical LLM XML repair scenario."""
        llm_xml = """
        <response>
            <status>success</status>
            <data>
                <user id="123">
                    <name>John & Jane</name>
                    <email>test@example.com</email>
                    <items>
                        <item>Product 1</item>
                        <item>Product 2
        """
        start = time.perf_counter()
        result = repair_xml_safe(llm_xml, trust=TrustLevel.TRUSTED)
        elapsed = time.perf_counter() - start
        assert "</response>" in result
        assert "&amp;" in result
        assert elapsed < 0.5

    def test_malformed_attributes(self):
        """Benchmark repair of malformed attributes."""
        xml = "<root><item id=123 name=test>data</item></root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert "<item" in result

    def test_conversational_fluff(self):
        """Benchmark extraction from conversational fluff."""
        xml = """
        Here is the XML you requested:

        <root>
            <item>data</item>
        </root>

        I hope this helps!
        """
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert "<root>" in result
        assert "requested" not in result  # Fluff removed
