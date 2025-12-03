"""Tests for entity escaping improvements (v0.5.0)."""

import pytest

from xenon import TrustLevel, XMLRepairEngine, repair_xml_safe


class TestEntityEscaping:
    """Test suite for entity escaping improvements."""

    def test_escape_ampersand(self):
        """Test escaping of ampersand in text."""
        xml = "<root>R&D department</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert result == "<root>R&amp;D department</root>"

    def test_escape_less_than(self):
        """Test escaping of < in text."""
        xml = "<root>a &lt; b</root>"  # Already escaped
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert result == "<root>a &lt; b</root>"
        assert "&amp;lt;" not in result  # No double-escaping

    def test_escape_greater_than(self):
        """Test escaping of > in text."""
        xml = "<root>a &gt; b</root>"  # Already escaped
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert result == "<root>a &gt; b</root>"
        assert "&amp;gt;" not in result  # No double-escaping

    def test_no_double_escaping(self):
        """Test that already escaped entities are not double-escaped."""
        xml = "<root>&lt;already escaped&gt;</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert result == "<root>&lt;already escaped&gt;</root>"
        assert "&amp;lt;" not in result
        assert "&amp;gt;" not in result

    def test_all_standard_entities_preserved(self):
        """Test that all standard XML entities are preserved."""
        xml = "<root>&amp;&lt;&gt;&quot;&apos;</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert result == "<root>&amp;&lt;&gt;&quot;&apos;</root>"
        # Should NOT use CDATA because these are valid entities
        assert "<![CDATA[" not in result

    def test_numeric_entity_preserved(self):
        """Test that numeric entities are preserved."""
        xml = "<root>Price: &#36;100</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert result == "<root>Price: &#36;100</root>"
        assert "&#36;" in result  # Dollar sign entity preserved

    def test_hex_entity_preserved(self):
        """Test that hexadecimal entities are preserved."""
        xml = "<root>Unicode: &#x2764;</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert result == "<root>Unicode: &#x2764;</root>"
        assert "&#x2764;" in result  # Heart emoji entity preserved

    def test_mixed_escaped_and_unescaped(self):
        """Test mix of escaped and unescaped characters."""
        xml = "<root>&lt;tag&gt; & text</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert "&lt;tag&gt;" in result  # Escaped parts preserved
        assert "&amp; text" in result  # Unescaped & escaped

    def test_invalid_entity_reference_handled(self):
        """Test that invalid entity refs are escaped."""
        xml = "<root>&invalid; &another</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        # Invalid entities should have their & escaped
        assert "&amp;invalid;" in result or "invalid" in result
        assert "&amp;another" in result or "another" in result

    def test_cdata_still_works_for_code(self):
        """Test that CDATA wrapping works for code tags with auto_wrap_cdata enabled."""
        xml = "<code>if (a && b) { }</code>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)
        # Should use CDATA for code with &&
        assert "<![CDATA[" in result
        assert "if (a && b)" in result

    def test_cdata_for_multiple_unescaped_chars(self):
        """Test CDATA wrapping for code tags with special chars."""
        xml = "<code>5 < 10 & 10 > 5</code>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)
        # Should use CDATA for multiple unescaped chars in code tag
        assert "<![CDATA[" in result

    def test_single_unescaped_char_escaped_not_cdata(self):
        """Test that single unescaped chars are escaped, not wrapped in CDATA."""
        xml = "<root>AT&T company</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert result == "<root>AT&amp;T company</root>"
        assert "<![CDATA[" not in result

    def test_escape_in_nested_elements(self):
        """Test escaping in nested elements."""
        xml = "<root><a>x &lt; y</a><b>m & n</b></root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert "&lt;" in result  # Preserved
        assert "&amp;" in result  # Added
        assert "&amp;lt;" not in result  # No double-escape

    def test_entity_escaping_with_malformed_input(self):
        """Test entity escaping with malformed input."""
        xml = "<root attr=unquoted>text & more</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert 'attr="unquoted"' in result  # Attribute fixed
        assert "&amp; more" in result or "<![CDATA[" in result  # Entity escaped or wrapped

    def test_engine_direct_usage(self):
        """Test using XMLRepairEngine directly."""
        engine = XMLRepairEngine()
        xml = "<root>R&D</root>"
        repaired_xml, _ = engine.repair_xml(xml)
        assert "&amp;D" in repaired_xml

    def test_apostrophe_entity(self):
        """Test apostrophe entity preservation."""
        xml = "<root>It&apos;s working</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert "&apos;" in result
        assert "&amp;apos;" not in result  # No double-escape

    def test_quote_entity(self):
        """Test quote entity preservation."""
        xml = "<root>He said &quot;hello&quot;</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert "&quot;" in result
        assert "&amp;quot;" not in result  # No double-escape

    def test_multiple_numeric_entities(self):
        """Test multiple numeric entities."""
        xml = "<root>&#65;&#66;&#67;</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert "&#65;" in result
        assert "&#66;" in result
        assert "&#67;" in result
        assert "&amp;#" not in result  # No double-escape

    def test_combined_with_truncation(self):
        """Test entity escaping with truncation repair."""
        xml = "<root>A & B"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert "</root>" in result  # Truncation fixed
        assert "&amp;" in result  # Entity escaped
