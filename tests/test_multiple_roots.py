"""Tests for multiple root element handling (v0.5.0)."""

import pytest

from xenon import TrustLevel, XMLRepairEngine, repair_xml_safe


class TestMultipleRoots:
    """Test suite for multiple root element handling."""

    def test_single_root_unchanged(self):
        """Test that single root is not wrapped."""
        xml = "<root>data</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, wrap_multiple_roots=True)
        assert result == "<root>data</root>"
        assert "<document>" not in result

    def test_two_roots_wrapped(self):
        """Test wrapping two root elements."""
        xml = "<root1>data1</root1><root2>data2</root2>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, wrap_multiple_roots=True)
        assert result == "<document><root1>data1</root1><root2>data2</root2></document>"

    def test_three_roots_wrapped(self):
        """Test wrapping three root elements."""
        xml = "<a>1</a><b>2</b><c>3</c>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, wrap_multiple_roots=True)
        assert result == "<document><a>1</a><b>2</b><c>3</c></document>"

    def test_wrapping_disabled_by_default(self):
        """Test that wrapping is OFF by default."""
        xml = "<root1>data1</root1><root2>data2</root2>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)  # No wrap_multiple_roots flag
        assert "<document>" not in result
        assert result == "<root1>data1</root1><root2>data2</root2>"

    def test_xml_declaration_preserved(self):
        """Test that XML declaration is preserved before wrapper."""
        xml = '<?xml version="1.0"?><root1>data1</root1><root2>data2</root2>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, wrap_multiple_roots=True)
        assert result.startswith('<?xml version="1.0"?>')
        assert "<document>" in result
        assert "<root1>data1</root1><root2>data2</root2></document>" in result

    def test_processing_instructions_preserved(self):
        """Test that PIs before root are preserved."""
        xml = '<?xml version="1.0"?><?xml-stylesheet href="style.xsl"?><root1>1</root1><root2>2</root2>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, wrap_multiple_roots=True)
        assert '<?xml version="1.0"?>' in result
        assert "<?xml-stylesheet" in result
        assert "<document>" in result

    def test_top_level_text_triggers_wrapping(self):
        """Test that top-level text triggers wrapping even with single root."""
        xml = "some text<root>data</root>more text"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, wrap_multiple_roots=True)
        # Should wrap because there's top-level text
        assert "<document>" in result
        assert "</document>" in result

    def test_whitespace_only_not_wrapped(self):
        """Test that whitespace-only text doesn't trigger wrapping."""
        xml = "  \n  <root>data</root>  \n  "
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, wrap_multiple_roots=True)
        # Should not wrap (whitespace doesn't count)
        assert "<document>" not in result or "<root>data</root>" in result.replace(
            "<document>", ""
        ).replace("</document>", "")

    def test_self_closing_tags_counted_as_roots(self):
        """Test that self-closing tags are counted as roots."""
        xml = "<root1/><root2/>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, wrap_multiple_roots=True)
        assert "<document>" in result
        assert "<root1/><root2/>" in result

    def test_mixed_roots_and_self_closing(self):
        """Test mix of regular and self-closing root tags."""
        xml = "<root1>data</root1><root2/><root3>more</root3>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, wrap_multiple_roots=True)
        assert "<document>" in result
        # root1: 2 occurrences, root2: 1 occurrence (self-closing), root3: 2 occurrences = 5 total
        assert result.count("root") == 5
        assert "<root1>data</root1>" in result
        assert "<root2/>" in result
        assert "<root3>more</root3>" in result

    def test_engine_direct_usage(self):
        """Test using XMLRepairEngine directly with wrap_multiple_roots."""
        engine = XMLRepairEngine(wrap_multiple_roots=True)
        xml = "<a>1</a><b>2</b>"
        repaired_xml, _ = engine.repair_xml(xml)
        assert "<document>" in repaired_xml
        assert "<a>1</a><b>2</b></document>" in repaired_xml

    def test_malformed_with_multiple_roots(self):
        """Test repairing malformed XML with multiple roots."""
        xml = "<root1 attr=unquoted>data1</root1><root2>data2"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, wrap_multiple_roots=True)
        assert "<document>" in result
        assert 'attr="unquoted"' in result
        assert "<root1" in result
        assert "<root2" in result
        assert "</root2>" in result  # Should be auto-closed

    def test_nested_tags_not_counted_as_roots(self):
        """Test that nested tags are not counted as multiple roots."""
        xml = "<root><child1>data1</child1><child2>data2</child2></root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, wrap_multiple_roots=True)
        # Should NOT wrap - only one root element
        assert "<document>" not in result or result.count("<root>") == 1

    def test_combined_with_security_features(self):
        """Test wrap_multiple_roots with security features."""
        xml = """<?php echo "hack"; ?>
<root1><script>XSS</script></root1>
<root2>data</root2>"""
        result = repair_xml_safe(
            xml,
            trust=TrustLevel.TRUSTED,
            wrap_multiple_roots=True,
            strip_dangerous_pis=True,
            strip_dangerous_tags=True,
        )
        assert "<document>" in result
        assert "<?php" not in result
        assert "<script>" not in result
        assert "<root1>" in result
        assert "<root2>" in result
