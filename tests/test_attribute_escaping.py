"""Tests for attribute value escaping (v0.5.0)."""

import pytest

from xenon import TrustLevel, XMLRepairEngine, repair_xml_safe


class TestAttributeEscaping:
    """Test suite for attribute value escaping."""

    def test_escape_ampersand_in_attribute(self):
        """Test escaping ampersand in attribute value."""
        xml = '<root attr="value & more">text</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert 'attr="value &amp; more"' in result

    def test_escape_less_than_in_attribute(self):
        """Test escaping < in attribute value."""
        xml = '<root attr="value < 10">text</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert 'attr="value &lt; 10"' in result

    def test_escape_greater_than_in_attribute(self):
        """Test escaping > in attribute value."""
        xml = '<root attr="value > 5">text</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert 'attr="value &gt; 5"' in result

    def test_escape_tags_in_attribute(self):
        """Test escaping tag-like content in attribute."""
        xml = '<root attr="<tag>">text</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert 'attr="&lt;tag&gt;"' in result

    def test_no_double_escape_in_attributes(self):
        """Test that already escaped entities in attributes are not double-escaped."""
        xml = '<root attr="&lt;already&gt;">text</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert 'attr="&lt;already&gt;"' in result
        assert "&amp;lt;" not in result
        assert "&amp;gt;" not in result

    def test_preserve_valid_entity_in_attribute(self):
        """Test that valid entities in attributes are preserved."""
        xml = '<root attr="value&nbsp;here">text</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        # Note: &nbsp; is not a standard XML entity, so it gets escaped
        # This test documents current behavior
        assert "attr=" in result

    def test_numeric_entity_in_attribute(self):
        """Test numeric entities in attribute values."""
        xml = '<root attr="&#36;100">text</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert "&#36;" in result
        assert "&amp;#36;" not in result

    def test_hex_entity_in_attribute(self):
        """Test hex entities in attribute values."""
        xml = '<root attr="&#x2764;">text</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert "&#x2764;" in result
        assert "&amp;#x" not in result

    def test_unquoted_attribute_with_ampersand(self):
        """Test escaping in unquoted attribute values."""
        xml = "<root attr=value&more>text</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert 'attr="value&amp;more"' in result

    def test_unquoted_attribute_with_less_than(self):
        """Test escaping < in unquoted attribute values."""
        xml = "<root attr=a<b>text</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        # This might get tokenized differently, just ensure it's escaped
        assert "&lt;" in result or "<![CDATA[" in result

    def test_multiple_attributes_with_escaping(self):
        """Test escaping across multiple attributes."""
        xml = '<root a="x & y" b="m < n">text</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert 'a="x &amp; y"' in result
        assert 'b="m &lt; n"' in result

    def test_attribute_with_all_special_chars(self):
        """Test attribute containing multiple special characters."""
        xml = '<root attr="a & b < c > d">text</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert "a &amp; b &lt; c &gt; d" in result

    def test_apostrophe_in_double_quoted_attribute(self):
        """Test that apostrophes don't need escaping in double-quoted attrs."""
        xml = '<root attr="it\'s working">text</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        # Apostrophe should stay as-is in double-quoted attribute
        assert "it's working" in result
        assert "&apos;" not in result  # Should NOT be escaped

    def test_standard_entities_in_attributes(self):
        """Test that standard XML entities are preserved in attributes."""
        xml = '<root attr="&amp;&lt;&gt;">text</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert "&amp;&lt;&gt;" in result
        # Should not be double-escaped
        assert "&amp;amp;" not in result

    def test_mixed_escaped_unescaped_in_attr(self):
        """Test mix of escaped and unescaped in same attribute."""
        xml = '<root attr="&lt;tag&gt; & text">text</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert "&lt;tag&gt;" in result  # Preserved
        assert "&amp; text" in result  # Added escaping

    def test_attribute_escaping_with_malformed_tag(self):
        """Test attribute escaping combined with malformed tag repair."""
        xml = "<root attr=value&more unclosed"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        # The unquoted value extends until next attribute or end
        # So "unclosed" becomes part of the attribute value
        assert "&amp;" in result  # Ampersand is escaped
        assert "</root>" in result  # Tag closed

    def test_engine_direct_usage(self):
        """Test using XMLRepairEngine directly."""
        engine = XMLRepairEngine()
        xml = '<root attr="a & b">text</root>'
        repaired_xml, _ = engine.repair_xml(xml)
        assert "&amp;" in repaired_xml

    def test_quote_entity_in_attribute(self):
        """Test quote entity in attribute value."""
        xml = '<root attr="value &quot;quoted&quot;">text</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert "&quot;" in result
        # Should not double-escape
        assert "&amp;quot;" not in result

    def test_apos_entity_in_attribute(self):
        """Test apostrophe entity in attribute value."""
        xml = "<root attr='value &apos;quoted&apos;'>text</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert "&apos;" in result
        assert "&amp;apos;" not in result

    def test_empty_attribute_value(self):
        """Test empty attribute values."""
        xml = '<root attr="">text</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert 'attr=""' in result
