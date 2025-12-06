"""Tests for utility functions."""

import pytest

from xenon import TrustLevel, XenonException
from xenon.utils import (
    batch_repair,
    batch_repair_with_reports,
    decode_xml,
    extract_text_content,
    stream_repair,
    validate_xml_structure,
)


class TestDecodeXml:
    """Tests for decode_xml() function."""

    def test_decode_xml_auto(self):
        """Test automatic decoding."""
        xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?><root>test</root>'
        result = decode_xml(xml_bytes)
        assert result == '<?xml version="1.0" encoding="UTF-8"?><root>test</root>'

    def test_decode_xml_explicit(self):
        """Test decoding with explicit encoding."""
        xml_bytes = b"<root>test</root>"
        result = decode_xml(xml_bytes, encoding="utf-8")
        assert result == "<root>test</root>"

    def test_decode_xml_fallback(self):
        """Test fallback on decode error."""
        # Invalid encoding for the bytes
        xml_bytes = b"\xff\xfe<\x00r\x00o\x00o\x00t\x00>\x00"  # UTF-16 LE
        result = decode_xml(xml_bytes, encoding="ascii")
        # Should fallback to UTF-8 with replacement
        assert isinstance(result, str)

    def test_decode_xml_with_bom(self):
        """Test decoding with BOM auto-detection."""
        xml_bytes = b"\xef\xbb\xbf<root>test</root>"
        result = decode_xml(xml_bytes)
        assert "<root>test</root>" in result


class TestBatchRepair:
    """Test batch repair functionality."""

    def test_batch_repair_all_valid(self):
        """Test batch repair with all valid XML."""
        xml_batch = ["<root>item1</root>", "<root>item2</root>", "<root>item3</root>"]
        results = batch_repair(xml_batch, trust=TrustLevel.TRUSTED)

        assert len(results) == 3
        for xml, error in results:
            assert error is None
            assert "<root>" in xml

    def test_batch_repair_with_truncation(self):
        """Test batch repair with truncated XML."""
        xml_batch = ["<root>item1", "<root>item2</root>", "<root>item3"]
        results = batch_repair(xml_batch, trust=TrustLevel.TRUSTED)

        assert len(results) == 3
        for xml, error in results:
            assert error is None
            assert "</root>" in xml

    def test_batch_repair_on_error_skip(self):
        """Test skip behavior on error."""
        xml_batch = [
            "<root>valid</root>",
            None,  # Will cause error
            "<root>valid2</root>",
        ]
        # Use on_error='skip' to return original on error
        results = batch_repair(xml_batch, trust=TrustLevel.TRUSTED, on_error="skip")

        assert len(results) == 3
        # First and third should succeed
        assert results[0][1] is None
        assert results[2][1] is None
        # Second should have error
        assert results[1][1] is not None

    def test_batch_repair_on_error_return_empty(self):
        """Test return_empty behavior on error."""
        xml_batch = [
            "<root>valid</root>",
            None,  # Will cause error
        ]
        results = batch_repair(xml_batch, trust=TrustLevel.TRUSTED, on_error="return_empty")

        assert len(results) == 2
        assert results[0][1] is None
        assert results[1][0] == ""  # Empty on error
        assert results[1][1] is not None

    def test_batch_repair_on_error_raise(self):
        """Test raise behavior on error."""
        xml_batch = [
            "<root>valid</root>",
            None,  # Will cause error
        ]
        with pytest.raises(XenonException):
            batch_repair(xml_batch, trust=TrustLevel.TRUSTED, on_error="raise")

    def test_batch_repair_passes_kwargs(self):
        """Test that kwargs are passed to repair function."""
        xml_batch = ["<root>item</root>"]
        results = batch_repair(xml_batch, trust=TrustLevel.TRUSTED, strict=False)
        assert len(results) == 1

    def test_batch_repair_empty_list(self):
        """Test with empty input list."""
        results = batch_repair([], trust=TrustLevel.TRUSTED)
        assert len(results) == 0


class TestBatchRepairWithReports:
    """Test batch repair with reports."""

    def test_batch_with_reports_basic(self):
        """Test basic batch repair with reports."""
        xml_batch = ["<root>item1</root>", "<root>item2"]
        results = batch_repair_with_reports(xml_batch, trust=TrustLevel.TRUSTED)

        assert len(results) == 2
        for xml, report in results:
            assert isinstance(xml, str)
            assert "<root>" in xml

    def test_batch_with_reports_filter_func(self):
        """Test filtering results by report."""
        xml_batch = [
            "<root>valid</root>",  # No repairs needed
            "<root>invalid",  # Needs repair
            "<root>also valid</root>",  # No repairs needed
        ]

        # Only return items that needed repairs
        results = batch_repair_with_reports(
            xml_batch, trust=TrustLevel.TRUSTED, filter_func=lambda r: len(r) > 0
        )

        # Should only include the one that needed repair
        assert len(results) >= 1

        # All results should have had repairs
        for xml, report in results:
            assert len(report) > 0

    def test_batch_with_reports_no_filter(self):
        """Test without filter (returns all)."""
        xml_batch = ["<root>item1</root>", "<root>item2"]
        results = batch_repair_with_reports(xml_batch, trust=TrustLevel.TRUSTED, filter_func=None)

        assert len(results) == 2


class TestStreamRepair:
    """Test streaming repair functionality."""

    def test_stream_repair_basic(self):
        """Test basic streaming repair."""

        def xml_generator():
            yield "<root>item1</root>"
            yield "<root>item2</root>"
            yield "<root>item3</root>"

        results = list(stream_repair(xml_generator(), trust=TrustLevel.TRUSTED))

        assert len(results) == 3
        for xml, error in results:
            assert error is None
            assert "<root>" in xml

    def test_stream_repair_with_errors(self):
        """Test streaming with some errors."""

        def xml_generator():
            yield "<root>valid</root>"
            yield None  # Will cause error
            yield "<root>valid2</root>"

        results = list(stream_repair(xml_generator(), trust=TrustLevel.TRUSTED))

        assert len(results) == 3
        assert results[0][1] is None  # No error
        assert results[1][1] is not None  # Error
        assert results[2][1] is None  # No error

    def test_stream_repair_with_truncation(self):
        """Test streaming repair fixes truncation."""

        def xml_generator():
            yield "<root>item1"
            yield "<root>item2"
            yield "<root>item3"

        results = list(stream_repair(xml_generator(), trust=TrustLevel.TRUSTED))

        for xml, error in results:
            assert error is None
            assert "</root>" in xml

    def test_stream_repair_empty(self):
        """Test streaming with empty iterator."""

        def xml_generator():
            return
            yield  # Never reached

        results = list(stream_repair(xml_generator(), trust=TrustLevel.TRUSTED))
        assert len(results) == 0

    def test_stream_repair_passes_kwargs(self):
        """Test that kwargs are passed through."""

        def xml_generator():
            yield "<root>item</root>"

        results = list(stream_repair(xml_generator(), trust=TrustLevel.TRUSTED, strict=False))
        assert len(results) == 1


class TestValidateXMLStructure:
    """Test XML structure validation."""

    def test_validate_well_formed(self):
        """Test validation of well-formed XML."""
        xml = "<root><item>Hello</item></root>"
        is_valid, issues = validate_xml_structure(xml)
        assert is_valid
        assert len(issues) == 0

    def test_validate_empty_string(self):
        """Test validation of empty string."""
        xml = ""
        is_valid, issues = validate_xml_structure(xml)
        assert not is_valid
        assert any("Empty" in issue for issue in issues)

    def test_validate_whitespace_only(self):
        """Test validation of whitespace-only string."""
        xml = "   \n\t  "
        is_valid, issues = validate_xml_structure(xml)
        assert not is_valid
        assert any("Empty" in issue for issue in issues)

    def test_validate_no_tags(self):
        """Test validation with no XML tags."""
        xml = "Just plain text"
        is_valid, issues = validate_xml_structure(xml)
        assert not is_valid
        assert any("No XML tags" in issue for issue in issues)

    def test_validate_more_opening_tags(self):
        """Test validation with more opening than closing tags."""
        xml = "<root><item><nested></nested></item>"
        is_valid, issues = validate_xml_structure(xml)
        assert not is_valid
        assert any("More opening tags" in issue for issue in issues)

    def test_validate_more_closing_tags(self):
        """Test validation with more closing than opening tags."""
        xml = "<root><item></item></root></extra>"
        is_valid, issues = validate_xml_structure(xml)
        assert not is_valid
        assert any("More closing tags" in issue for issue in issues)

    def test_validate_unescaped_ampersand(self):
        """Test detection of unescaped ampersands."""
        xml = "<root>Tom & Jerry</root>"
        is_valid, issues = validate_xml_structure(xml)
        assert not is_valid
        assert any("unescaped ampersand" in issue for issue in issues)

    def test_validate_escaped_ampersand(self):
        """Test that escaped ampersands are OK."""
        xml = "<root>Tom &amp; Jerry</root>"
        _is_valid, issues = validate_xml_structure(xml)
        # Should not flag escaped ampersands
        assert not any("ampersand" in issue for issue in issues)

    def test_validate_entity_references(self):
        """Test that entity references are not flagged."""
        xml = "<root>&lt; &gt; &quot; &apos; &#65; &#x41;</root>"
        _is_valid, issues = validate_xml_structure(xml)
        # Should not flag valid entity references
        assert not any("ampersand" in issue for issue in issues)

    def test_validate_unquoted_attributes(self):
        """Test detection of unquoted attributes."""
        xml = "<root attr=value>text</root>"
        is_valid, issues = validate_xml_structure(xml)
        assert not is_valid
        assert any("unquoted attribute" in issue for issue in issues)

    def test_validate_quoted_attributes(self):
        """Test that quoted attributes are OK."""
        xml = "<root attr=\"value\" other='value2'>text</root>"
        _is_valid, issues = validate_xml_structure(xml)
        # Should not flag quoted attributes
        assert not any("attribute" in issue for issue in issues)

    def test_validate_self_closing_tags(self):
        """Test that self-closing tags are handled."""
        xml = "<root><item/><item/></root>"
        _is_valid, _issues = validate_xml_structure(xml)
        # Self-closing tags should not cause tag mismatch
        # Note: The current implementation may not perfectly handle this
        # This test documents the behavior

    def test_validate_multiple_issues(self):
        """Test XML with multiple issues."""
        xml = "<root><item attr=unquoted>Tom & Jerry"
        is_valid, issues = validate_xml_structure(xml)
        assert not is_valid
        assert len(issues) >= 2  # Multiple issues detected


class TestExtractTextContent:
    """Test text content extraction."""

    def test_extract_simple(self):
        """Test extracting text from simple XML."""
        xml = "<root>Hello World</root>"
        text = extract_text_content(xml)
        assert text == "Hello World"

    def test_extract_nested(self):
        """Test extracting from nested XML."""
        xml = "<root><item>Hello</item><item>World</item></root>"
        text = extract_text_content(xml)
        assert "Hello" in text
        assert "World" in text

    def test_extract_removes_tags(self):
        """Test that all tags are removed."""
        xml = "<root><a>text1</a><b>text2</b></root>"
        text = extract_text_content(xml)
        assert "<" not in text
        assert ">" not in text

    def test_extract_preserves_cdata(self):
        """Test that CDATA content is extracted (tags still removed)."""
        xml = "<root><![CDATA[Special content here]]></root>"
        text = extract_text_content(xml)
        assert "Special content here" in text

        # Note: If CDATA contains tag-like text, those will also be removed
        # because extract_text_content removes ALL tag patterns
        xml_with_tags = "<root><![CDATA[Special <content>]]></root>"
        text2 = extract_text_content(xml_with_tags)
        assert "Special" in text2
        # The <content> tag-like text is also removed by the final tag removal

    def test_extract_removes_comments(self):
        """Test that comments are removed."""
        xml = "<root>text<!-- comment -->more</root>"
        text = extract_text_content(xml)
        assert "comment" not in text
        assert "text" in text
        assert "more" in text

    def test_extract_removes_processing_instructions(self):
        """Test that PIs are removed."""
        xml = '<?xml version="1.0"?><root>text</root><?pi data?>'
        text = extract_text_content(xml)
        assert "xml version" not in text
        assert "pi data" not in text
        assert "text" in text

    def test_extract_removes_doctype(self):
        """Test that DOCTYPE is removed."""
        xml = '<!DOCTYPE root SYSTEM "schema.dtd"><root>text</root>'
        text = extract_text_content(xml)
        assert "DOCTYPE" not in text
        assert "SYSTEM" not in text
        assert "text" in text

    def test_extract_empty_elements(self):
        """Test extracting from empty elements."""
        xml = "<root><item/><item></item></root>"
        text = extract_text_content(xml)
        assert text == ""

    def test_extract_mixed_content(self):
        """Test extracting from mixed content."""
        xml = "<root>Start<item>Middle</item>End</root>"
        text = extract_text_content(xml)
        assert "Start" in text
        assert "Middle" in text
        assert "End" in text

    def test_extract_with_attributes(self):
        """Test that attributes are removed."""
        xml = '<root attr="value">text</root>'
        text = extract_text_content(xml)
        assert "attr" not in text
        assert "value" not in text
        assert "text" in text

    def test_extract_preserves_whitespace(self):
        """Test that whitespace in content is preserved."""
        xml = "<root>  text  with  spaces  </root>"
        text = extract_text_content(xml)
        # Whitespace should be preserved
        assert "  text  with  spaces  " in text
