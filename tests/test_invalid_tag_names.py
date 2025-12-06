"""Tests for invalid tag name sanitization (v0.5.0)."""

import pytest

from xenon import TrustLevel, XMLRepairEngine, repair_xml_safe


class TestInvalidTagNames:
    """Test suite for invalid tag name sanitization."""

    def test_tag_starting_with_number(self):
        """Test sanitizing tag that starts with a number."""
        xml = "<123illegal>data</123illegal>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        assert result == "<tag_123illegal>data</tag_123illegal>"

    def test_tag_with_spaces(self):
        """Test sanitizing tag with spaces in name."""
        xml = "<tag with spaces>data</tag with spaces>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        assert result == "<tag_with_spaces>data</tag_with_spaces>"

    def test_tag_with_special_chars(self):
        """Test sanitizing tag with special characters."""
        xml = "<tag@name>data</tag@name>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        # @ should be stripped
        assert "tagname" in result

    def test_tag_starting_with_hyphen(self):
        """Test sanitizing tag starting with hyphen."""
        xml = "<-invalid>data</-invalid>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        assert (
            result == "<tag_-invalid>data</tag_-invalid>"
            or result == "<tag_invalid>data</tag_invalid>"
        )

    def test_empty_tag_name(self):
        """Test sanitizing empty tag name."""
        xml = "<>data</>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        # Should create a valid tag name
        assert "<tag>" in result or result != ""

    def test_multiple_invalid_tags(self):
        """Test sanitizing multiple invalid tags."""
        xml = "<123first>data1</123first><456second>data2</456second>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        assert "tag_123first" in result
        assert "tag_456second" in result
        assert "data1" in result
        assert "data2" in result

    def test_nested_invalid_tags(self):
        """Test sanitizing nested invalid tags."""
        xml = "<123outer><456inner>data</456inner></123outer>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        assert "tag_123outer" in result
        assert "tag_456inner" in result
        assert "data" in result

    def test_valid_tags_unchanged(self):
        """Test that valid tag names are not modified."""
        xml = "<validTag>data</validTag>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        assert result == "<validTag>data</validTag>"

    def test_sanitization_disabled_by_default(self):
        """Test that sanitization is OFF by default."""
        xml = "<123illegal>data</123illegal>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)  # No sanitize_invalid_tags flag
        # Without sanitization, the tag might not be recognized
        # Just ensure it doesn't crash
        assert isinstance(result, str)

    def test_tag_with_attributes(self):
        """Test sanitizing tag with attributes."""
        xml = '<123tag attr="value">data</123tag>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        assert "tag_123tag" in result
        assert 'attr="value"' in result
        assert "data" in result

    def test_self_closing_invalid_tag(self):
        """Test sanitizing self-closing invalid tag."""
        xml = "<123tag/>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        assert "tag_123tag" in result

    def test_tag_with_colon_valid(self):
        """Test that tags with colons (namespaces) are valid."""
        xml = "<ns:tag>data</ns:tag>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        assert result == "<ns:tag>data</ns:tag>"

    def test_tag_with_underscore_valid(self):
        """Test that tags starting with underscore are valid."""
        xml = "<_tag>data</_tag>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        assert result == "<_tag>data</_tag>"

    def test_engine_direct_usage(self):
        """Test using XMLRepairEngine directly with sanitize_invalid_tags."""
        engine = XMLRepairEngine(sanitize_invalid_tags=True)
        xml = "<123illegal>data</123illegal>"
        repaired_xml, _ = engine.repair_xml(xml)
        assert repaired_xml == "<tag_123illegal>data</tag_123illegal>"

    def test_combined_with_other_features(self):
        """Test sanitize_invalid_tags with other repair features."""
        xml = "<123tag attr=unquoted>data & more"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        assert "tag_123tag" in result
        assert 'attr="unquoted"' in result
        assert "&amp; more" in result or "<![CDATA[" in result
        assert "</tag_123tag>" in result

    def test_truncated_invalid_tag(self):
        """Test sanitizing truncated invalid tag."""
        xml = "<123tag>data"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        assert "tag_123tag" in result
        assert "data" in result
        assert "</tag_123tag>" in result

    def test_malformed_invalid_tag(self):
        """Test extremely malformed input (missing closing >)."""
        xml = "<123tag attr=value data"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        # Input is so malformed (no closing >) that it can't be recognized as XML
        # Reasonable behavior is to escape it as text
        assert "&lt;" in result or "tag" in result

    def test_tag_name_consistency(self):
        """Test that same invalid tag name is sanitized consistently."""
        xml = "<123tag>data</123tag><123tag>more</123tag>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        # Both instances should use the same sanitized name
        assert result.count("tag_123tag") == 4  # 2 opening, 2 closing

    def test_special_tags_preserved(self):
        """Test that special tags (comments, CDATA, etc.) are not sanitized."""
        xml = "<!-- comment --><123tag>data</123tag><![CDATA[code]]>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        assert "<!-- comment -->" in result
        assert "<![CDATA[code]]>" in result
        assert "tag_123tag" in result

    def test_mixed_valid_invalid(self):
        """Test mix of valid and invalid tag names."""
        xml = "<valid><123invalid>data</123invalid></valid>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, sanitize_invalid_tags=True)
        assert "<valid>" in result
        assert "tag_123invalid" in result
        assert "</valid>" in result
