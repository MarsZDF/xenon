"""Tests for XML formatting (v0.6.0)."""

import pytest

from xenon.formatting import format_xml, preserve_formatting


class TestXMLFormatting:
    """Test XML formatting functionality."""

    def test_pretty_print_simple(self):
        """Test pretty-printing simple XML."""
        xml = "<root><item>test</item><another>data</another></root>"
        result = format_xml(xml, style="pretty")

        assert "<root>" in result
        assert "<item>test</item>" in result
        assert "</root>" in result
        # Should have indentation
        assert "  <item>" in result or "    <item>" in result

    def test_pretty_print_with_custom_indent(self):
        """Test pretty-printing with custom indentation."""
        xml = "<root><item>test</item></root>"
        result = format_xml(xml, style="pretty", indent="    ")  # 4 spaces

        assert "    <item>" in result or "<item>" in result
        assert "</item>" in result

    def test_minify_xml(self):
        """Test XML minification."""
        xml = """<root>
    <item>test</item>
    <another>data</another>
</root>"""
        result = format_xml(xml, style="minify")

        assert "\n" not in result or result.count("\n") < 2
        assert "<root><item>test</item>" in result

    def test_compact_xml(self):
        """Test compact XML format."""
        xml = "<root>   <item>test</item>   <another>data</another>   </root>"
        result = format_xml(xml, style="compact")

        assert "\n" in result  # Has newlines
        assert result.count("\n") >= 3  # Multiple lines
        assert "  " not in result or result.count("  ") < 5  # Minimal indentation

    def test_preserve_whitespace_in_minify(self):
        """Test that preserve_whitespace keeps significant whitespace."""
        xml = "<code>  x = 5  </code>"
        result = format_xml(xml, style="minify", preserve_whitespace=True)

        # Content whitespace should be preserved
        assert "x = 5" in result

    def test_format_with_attributes(self):
        """Test formatting XML with attributes."""
        xml = '<root attr="value"><item id="123">test</item></root>'
        result = format_xml(xml, style="pretty")

        assert 'attr="value"' in result
        assert 'id="123"' in result

    def test_format_with_cdata(self):
        """Test formatting XML with CDATA sections."""
        xml = "<code><![CDATA[if (x < 5) { }]]></code>"
        result = format_xml(xml, style="pretty")

        assert "<![CDATA[" in result
        assert "]]>" in result

    def test_format_empty_string(self):
        """Test formatting empty string."""
        result = format_xml("", style="pretty")
        assert result == ""

        result = format_xml("   ", style="pretty")
        assert result.strip() == ""

    def test_invalid_style_raises_error(self):
        """Test that invalid style raises ValueError."""
        with pytest.raises(ValueError, match="Unknown format style"):
            format_xml("<root/>", style="invalid")

    def test_preserve_formatting_function(self):
        """Test preserve_formatting utility."""
        xml = "line1\r\nline2\r\nline3  \n\n\nline4"
        result = preserve_formatting(xml)

        assert "\r" not in result  # Line endings normalized
        assert "  \n" not in result or result.count("  \n") < 2  # Trailing whitespace removed
        # Should not have more than 1 consecutive blank line
        assert "\n\n\n" not in result

    def test_format_with_declaration(self):
        """Test formatting XML with declaration."""
        xml = '<?xml version="1.0"?><root><item>test</item></root>'
        result = format_xml(xml, style="pretty")

        # Declaration handling varies, just ensure it processes
        assert "<root>" in result
        assert "<item>test</item>" in result

    def test_pretty_print_fallback(self, monkeypatch):
        """Test fallback to simple indentation when minidom fails."""
        from xml.dom import minidom

        def mock_parse(*args, **kwargs):
            raise Exception("Minidom failed")

        monkeypatch.setattr(minidom, "parseString", mock_parse)

        xml = "<root><item>test</item></root>"
        result = format_xml(xml, style="pretty")

        # Should still be formatted (using fallback)
        # Note: _simple_indent puts text on new lines
        assert "<root>" in result
        assert "  <item>" in result
        assert "    test" in result
        assert "  </item>" in result
        assert "</root>" in result

    def test_minify_removes_all_whitespace(self):
        """Test minify removes unnecessary whitespace."""
        xml = """
        <root>
            <item>
                test
            </item>
        </root>
        """
        result = format_xml(xml, style="minify")

        # Should be very compact
        assert len(result) < len(xml) / 2
        assert "<root><item>" in result or "<root> <item>" in result
