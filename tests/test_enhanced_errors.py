"""Tests for enhanced error messages with line/column context."""

import pytest

from xenon.exceptions import (
    MalformedXMLError,
    RepairError,
    ValidationError,
    XenonException,
    get_context_snippet,
    get_line_column,
)


class TestExceptionEnhancements:
    """Test enhanced exception features."""

    def test_exception_with_line_only(self):
        """Test exception with line number only."""
        exc = XenonException("Test error", line=5)
        assert exc.line == 5
        assert exc.column is None
        assert "line 5" in str(exc)

    def test_exception_with_line_and_column(self):
        """Test exception with line and column."""
        exc = XenonException("Test error", line=5, column=12)
        assert exc.line == 5
        assert exc.column == 12
        assert "line 5, column 12" in str(exc)

    def test_exception_with_context(self):
        """Test exception with context snippet."""
        exc = XenonException("Test error", context="<root><item>")
        assert exc.context == "<root><item>"
        assert "Context:" in str(exc)
        assert "<root><item>" in str(exc)

    def test_exception_with_all_info(self):
        """Test exception with all context information."""
        exc = XenonException("Invalid tag", line=3, column=8, context="<root><bad tag>")
        assert exc.line == 3
        assert exc.column == 8
        assert "line 3, column 8" in str(exc)
        assert "<root><bad tag>" in str(exc)

    def test_validation_error_inherits_enhancement(self):
        """Test that ValidationError inherits enhancements."""
        exc = ValidationError("Input too large", line=10)
        assert exc.line == 10
        assert "line 10" in str(exc)

    def test_malformed_xml_error_inherits_enhancement(self):
        """Test that MalformedXMLError inherits enhancements."""
        exc = MalformedXMLError("Unclosed tag", line=5, column=3, context="<root><item")
        assert exc.line == 5
        assert exc.column == 3
        assert "line 5, column 3" in str(exc)

    def test_repair_error_inherits_enhancement(self):
        """Test that RepairError inherits enhancements."""
        exc = RepairError("Internal error", line=1, context="<broken>")
        assert exc.line == 1
        assert "<broken>" in str(exc)


class TestContextHelpers:
    """Test helper functions for error context."""

    def test_get_line_column_simple(self):
        """Test line/column calculation for simple text."""
        text = "line1\nline2\nline3"
        line, col = get_line_column(text, 0)
        assert line == 1
        assert col == 1

    def test_get_line_column_second_line(self):
        """Test line/column on second line."""
        text = "line1\nline2\nline3"
        # Position 6 is 'l' in "line2"
        line, col = get_line_column(text, 6)
        assert line == 2
        assert col == 1

    def test_get_line_column_middle_of_line(self):
        """Test line/column in middle of line."""
        text = "line1\nline2\nline3"
        # Position 8 is 'n' in "line2"
        line, col = get_line_column(text, 8)
        assert line == 2
        assert col == 3

    def test_get_line_column_empty_text(self):
        """Test line/column with empty text."""
        line, col = get_line_column("", 0)
        assert line == 1
        assert col == 1

    def test_get_line_column_negative_position(self):
        """Test line/column with negative position."""
        line, col = get_line_column("test", -1)
        assert line == 1
        assert col == 1

    def test_get_context_snippet_middle(self):
        """Test context snippet extraction from middle."""
        text = "This is a long line of text that will be truncated"
        snippet = get_context_snippet(text, 10, max_length=20)
        assert len(snippet) <= 24  # 20 + "..." on each side
        assert "long" in snippet

    def test_get_context_snippet_start(self):
        """Test context snippet at start of text."""
        text = "Short text here"
        snippet = get_context_snippet(text, 0, max_length=20)
        assert "Short" in snippet
        assert not snippet.startswith("...")

    def test_get_context_snippet_end(self):
        """Test context snippet at end of text."""
        text = "Some text at the very end"
        snippet = get_context_snippet(text, len(text) - 5, max_length=20)
        assert "end" in snippet

    def test_get_context_snippet_empty_text(self):
        """Test context snippet with empty text."""
        snippet = get_context_snippet("", 0)
        assert snippet == ""

    def test_get_context_snippet_invalid_position(self):
        """Test context snippet with invalid position."""
        snippet = get_context_snippet("test", 100)
        assert snippet == ""


class TestRealWorldErrorScenarios:
    """Test enhanced errors in real-world scenarios."""

    def test_xml_with_error_on_specific_line(self):
        """Test error reporting for XML error on specific line."""
        xml = """<root>
    <item id="1">
        <bad tag>
    </item>
</root>"""
        # Simulate error at position of "<bad tag>"
        position = xml.find("<bad tag>")
        line, col = get_line_column(xml, position)
        context = get_context_snippet(xml, position, max_length=30)

        exc = MalformedXMLError("Invalid tag name", line=line, column=col, context=context)

        assert exc.line == 3
        assert "line 3" in str(exc)
        assert "bad tag" in str(exc).lower()

    def test_truncated_xml_error_context(self):
        """Test error context for truncated XML."""
        xml = "<root><item>data</item><another"
        position = len(xml) - 1  # Last character
        line, col = get_line_column(xml, position)
        context = get_context_snippet(xml, position)

        exc = MalformedXMLError("Unexpected end of input", line=line, column=col, context=context)

        assert "another" in str(exc)
        assert "line 1" in str(exc)

    def test_multiline_xml_error_tracking(self):
        """Test error tracking across multiple lines."""
        xml = """<?xml version="1.0"?>
<root>
    <users>
        <user id=invalid>
            <name>Test</name>
        </user>
    </users>
</root>"""
        # Find the invalid attribute
        position = xml.find("id=invalid")
        line, col = get_line_column(xml, position)

        exc = ValidationError(
            "Unquoted attribute value",
            line=line,
            column=col,
            context=get_context_snippet(xml, position, 40),
        )

        assert exc.line == 4
        assert "id=invalid" in str(exc)
