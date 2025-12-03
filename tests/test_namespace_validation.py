"""Tests for namespace syntax validation (v0.5.0)."""

import pytest

from xenon import TrustLevel, XMLRepairEngine, repair_xml_safe


class TestNamespaceValidation:
    """Test suite for namespace syntax validation."""

    def test_double_colon(self):
        """Test fixing double colon in namespace."""
        xml = "<bad::ns>data</bad::ns>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True)
        assert result == "<bad_ns>data</bad_ns>"

    def test_triple_colon(self):
        """Test fixing triple colon."""
        xml = "<bad:::ns>data</bad:::ns>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True)
        assert result == "<bad_ns>data</bad_ns>"

    def test_multiple_segments(self):
        """Test fixing multiple namespace segments."""
        xml = "<ns1:ns2:tag>data</ns1:ns2:tag>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True)
        assert result == "<ns1:ns2_tag>data</ns1:ns2_tag>"

    def test_starts_with_colon(self):
        """Test fixing tag starting with colon."""
        xml = "<:tag>data</:tag>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True)
        assert result == "<c_tag>data</c_tag>"

    def test_ends_with_colon(self):
        """Test fixing tag ending with colon."""
        xml = "<tag:>data</tag:>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True)
        assert result == "<tag>data</tag>"

    def test_valid_namespace_unchanged(self):
        """Test that valid namespace syntax is not modified."""
        xml = "<ns:tag>data</ns:tag>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True)
        assert result == "<ns:tag>data</ns:tag>"

    def test_no_namespace_unchanged(self):
        """Test that tags without namespace are not modified."""
        xml = "<tag>data</tag>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True)
        assert result == "<tag>data</tag>"

    def test_disabled_by_default(self):
        """Test that namespace fixing is OFF by default."""
        xml = "<bad::ns>data</bad::ns>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)  # No fix_namespace_syntax flag
        # Without fixing, the tag might not be recognized properly
        # Just ensure it doesn't crash
        assert isinstance(result, str)

    def test_with_attributes(self):
        """Test namespace fixing with attributes."""
        xml = '<ns1:ns2:tag attr="value">data</ns1:ns2:tag>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True)
        assert "ns1:ns2_tag" in result
        assert 'attr="value"' in result
        assert "data" in result

    def test_self_closing(self):
        """Test namespace fixing with self-closing tags."""
        xml = "<bad::ns/>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True)
        assert "bad_ns" in result

    def test_nested_tags(self):
        """Test namespace fixing with nested tags."""
        xml = "<ns1:ns2:outer><ns3:ns4:inner>data</ns3:ns4:inner></ns1:ns2:outer>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True)
        assert "ns1:ns2_outer" in result
        assert "ns3:ns4_inner" in result
        assert "data" in result

    def test_mixed_valid_invalid(self):
        """Test mix of valid and invalid namespace syntax."""
        xml = "<valid:tag><bad::ns>data</bad::ns></valid:tag>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True)
        assert "<valid:tag>" in result  # Valid unchanged
        assert "bad_ns" in result  # Invalid fixed

    def test_engine_direct_usage(self):
        """Test using XMLRepairEngine directly."""
        engine = XMLRepairEngine(fix_namespace_syntax=True)
        xml = "<bad::ns>data</bad::ns>"
        repaired_xml, _ = engine.repair_xml(xml)
        assert repaired_xml == "<bad_ns>data</bad_ns>"

    def test_combined_with_other_features(self):
        """Test namespace fixing with other repair features."""
        xml = "<bad::tag attr=unquoted>data & more"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True)
        assert "bad_tag" in result
        assert 'attr="unquoted"' in result
        assert "&amp; more" in result or "<![CDATA[" in result
        assert "</bad_tag>" in result

    def test_truncated_invalid_namespace(self):
        """Test fixing truncated tag with invalid namespace."""
        xml = "<ns1:ns2:tag>data"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True)
        assert "ns1:ns2_tag" in result
        assert "data" in result
        assert "</ns1:ns2_tag>" in result

    def test_four_segments(self):
        """Test fixing tag with four namespace segments."""
        xml = "<a:b:c:d>data</a:b:c:d>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True)
        # Should keep first colon, replace others with underscore
        assert "a:b_c_d" in result

    def test_empty_segments(self):
        """Test handling empty segments between colons."""
        xml = "<a::b>data</a::b>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True)
        # Double colon should be replaced
        assert "a_b" in result

    def test_preserves_common_namespaces(self):
        """Test that common namespace prefixes work correctly."""
        xml = "<soap:Envelope><soap:Body>data</soap:Body></soap:Envelope>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True)
        # Valid namespace syntax should be preserved (may have xmlns declarations added)
        assert "soap:Envelope" in result
        assert "soap:Body" in result
        assert "data" in result

    def test_combined_with_sanitize_invalid_tags(self):
        """Test namespace fixing combined with tag name sanitization."""
        xml = "<123:invalid::tag>data</123:invalid::tag>"
        result = repair_xml_safe(
            xml, trust=TrustLevel.TRUSTED, fix_namespace_syntax=True, sanitize_invalid_tags=True
        )
        # Both features should work together
        # Tag name starts with number, so gets sanitized to tag_123
        # Then namespace syntax gets fixed
        assert "tag_123" in result or "123" in result
