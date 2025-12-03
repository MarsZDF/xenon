"""Tests for mismatched tag detection using Levenshtein distance."""

import pytest

from xenon import TrustLevel, repair_xml, repair_xml_safe


class TestMismatchedTags:
    """Test suite for mismatched tag detection feature."""

    def test_single_character_typo(self):
        """Test fixing a single character typo in closing tag."""
        xml = "<mismatched>content</mismatchd>"
        result = repair_xml(xml, trust=TrustLevel.TRUSTED)
        assert result == "<mismatched>content</mismatched>"

    def test_transposition_typo(self):
        """Test fixing letter transposition (2 char distance)."""
        xml = "<item>stuff</itme>"
        result = repair_xml(xml, trust=TrustLevel.TRUSTED)
        assert result == "<item>stuff</item>"

    def test_missing_character(self):
        """Test fixing missing character in closing tag."""
        xml = "<veryLongTagName>content</veryLongTagNam>"
        result = repair_xml(xml, trust=TrustLevel.TRUSTED)
        assert result == "<veryLongTagName>content</veryLongTagName>"

    def test_case_insensitive_still_works(self):
        """Test that case-insensitive matching still works (distance=0)."""
        xml = "<CamelCase>XML is case sensitive</camelcase>"
        result = repair_xml(xml, trust=TrustLevel.TRUSTED)
        assert result == "<CamelCase>XML is case sensitive</CamelCase>"

    def test_nested_with_typo(self):
        """Test nested tags with typo in inner closing tag."""
        xml = "<root><item>data</itme></root>"
        result = repair_xml(xml, trust=TrustLevel.TRUSTED)
        assert result == "<root><item>data</item></root>"

    def test_multiple_typos(self):
        """Test multiple mismatched tags in same document."""
        xml = "<root><item>one</itm><thing>two</thng></root>"
        result = repair_xml(xml, trust=TrustLevel.TRUSTED)
        assert "</item>" in result
        assert "</thing>" in result
        assert "</root>" in result

    def test_beyond_threshold_not_matched(self):
        """Test that tags beyond threshold (>2 distance) are not auto-matched."""
        xml = "<opening>content</completely_different>"
        result = repair_xml(xml, trust=TrustLevel.TRUSTED)
        # Should keep the wrong closing tag and auto-close opening
        assert "</completely_different>" in result
        assert "</opening>" in result

    def test_exact_match_preferred_over_similar(self):
        """Test that exact matches are preferred over similar ones."""
        xml = "<item><item2>content</item>"
        result = repair_xml(xml, trust=TrustLevel.TRUSTED)
        # Should match the first <item>, not <item2> (distance=1)
        assert result == "<item><item2>content</item2></item>"

    def test_closest_match_on_stack(self):
        """Test that closest matching tag on stack is used."""
        xml = "<outer><middle><inner>text</inne></middle></outer>"
        result = repair_xml(xml, trust=TrustLevel.TRUSTED)
        assert "</inner>" in result
        assert "</middle>" in result
        assert "</outer>" in result

    def test_real_world_llm_typos(self):
        """Test real-world LLM output with typos."""
        xml = """<users>
    <user id=123>
        <role>Admin</role>
    </usr>
    <user id=456>
        <role>User</role>
    </user>
</usrs>"""
        result = repair_xml(xml, trust=TrustLevel.TRUSTED)
        # Both typos should be fixed
        assert "</user>" in result
        assert "</users>" in result
        # Attributes should be quoted
        assert 'id="123"' in result

    def test_performance_many_mismatches(self):
        """Test that performance is acceptable with many mismatches."""
        import time

        # Create 30 nested tags with all closing tags having 1-char typo
        open_tags = "".join([f"<tag{i}>" for i in range(30)])
        close_tags = "".join([f"</tag{i}x>" for i in range(29, -1, -1)])
        xml = open_tags + "content" + close_tags

        start = time.time()
        result = repair_xml(xml, trust=TrustLevel.TRUSTED)
        elapsed = time.time() - start

        # Should complete in under 50ms (generous for CI/slower machines)
        assert elapsed < 0.05, f"Performance test failed: took {elapsed * 1000:.2f}ms"
        # All tags should be corrected
        for i in range(30):
            assert f"</tag{i}>" in result

    def test_safe_mode_with_mismatches(self):
        """Test that mismatched tag detection works with safe mode."""
        xml = "<root><item>data</itme></root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert result == "<root><item>data</item></root>"

    def test_threshold_configurable(self):
        """Test that threshold is configurable (future feature)."""
        # This tests the internal API - threshold defaults to 2
        from xenon.parser import XMLRepairEngine

        engine = XMLRepairEngine(match_threshold=1)
        assert engine.match_threshold == 1

    def test_levenshtein_distance(self):
        """Test Levenshtein distance calculation."""
        from xenon.parser import XMLRepairEngine

        engine = XMLRepairEngine()

        # Exact match
        assert engine.levenshtein_distance("abc", "abc") == 0

        # Single substitution
        assert engine.levenshtein_distance("abc", "adc") == 1

        # Single deletion
        assert engine.levenshtein_distance("abc", "ab") == 1

        # Single insertion
        assert engine.levenshtein_distance("abc", "abcd") == 1

        # Transposition (2 operations)
        assert engine.levenshtein_distance("item", "itme") == 2

        # Completely different
        assert engine.levenshtein_distance("abc", "xyz") >= 3

    def test_no_false_positives(self):
        """Test that valid XML is not modified incorrectly."""
        xml = "<root><item>one</item><item>two</item></root>"
        result = repair_xml(xml, trust=TrustLevel.TRUSTED)
        assert result == xml  # Should be unchanged
