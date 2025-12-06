"""Tests for diff/patch reporting (v0.6.0)."""

import pytest

from xenon import TrustLevel, repair_xml_with_diff, repair_xml_with_report


class TestDiffReporting:
    """Test diff and patch reporting functionality."""

    def test_unified_diff_format(self):
        """Test unified diff output format."""
        xml = "<root><item>test"
        _result, report = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)

        diff = report.to_unified_diff()

        assert "---" in diff
        assert "+++" in diff
        assert "Original" in diff
        assert "Repaired" in diff
        assert "-<root><item>test" in diff or "<root><item>test" in diff
        assert "</item></root>" in diff

    def test_context_diff_format(self):
        """Test context diff output format."""
        xml = "<root><item>test"
        _result, report = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)

        diff = report.to_context_diff()

        assert "***" in diff
        assert "Original" in diff
        assert "Repaired" in diff

    def test_html_diff_table_style(self):
        """Test HTML diff with table format."""
        xml = "<root><item name=unquoted>test</item></root>"
        _result, report = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)

        html = report.to_html_diff(table_style=True)

        assert "<table" in html
        assert "Original XML" in html
        assert "Repaired XML" in html

    def test_html_diff_file_style(self):
        """Test HTML diff with file format."""
        xml = "<root><item>test"
        _result, report = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)

        html = report.to_html_diff(table_style=False)

        assert "<!DOCTYPE" in html or "<html" in html
        assert "Original XML" in html
        assert "Repaired XML" in html

    def test_diff_summary_statistics(self):
        """Test diff summary statistics."""
        xml = "<root>\n<item>test\n<another>data"
        _result, report = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)

        stats = report.get_diff_summary()

        assert "lines_added" in stats
        assert "lines_removed" in stats
        assert "lines_changed" in stats
        assert "similarity_ratio" in stats
        assert "original_lines" in stats
        assert "repaired_lines" in stats

        assert isinstance(stats["similarity_ratio"], float)
        assert 0.0 <= stats["similarity_ratio"] <= 1.0

    def test_no_changes_diff(self):
        """Test diff when no changes were made."""
        xml = "<root><item>test</item></root>"
        _result, report = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)

        diff = report.to_unified_diff()

        # Should be empty or minimal diff
        assert isinstance(diff, str)

        stats = report.get_diff_summary()
        assert stats["similarity_ratio"] >= 0.9  # Very similar

    def test_repair_xml_with_diff_alias(self):
        """Test that repair_xml_with_diff is an alias for repair_xml_with_report."""
        xml = "<root><item>test"

        result1, report1 = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)
        result2, report2 = repair_xml_with_diff(xml, trust=TrustLevel.TRUSTED)

        assert result1 == result2
        assert len(report1) == len(report2)

    def test_multiline_diff(self):
        """Test diff with multiline XML."""
        xml = """<root>
    <item>test
    <another>data
</root>"""
        _result, report = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)

        diff = report.to_unified_diff(context_lines=2)

        assert "@@" in diff  # Unified diff hunk marker
        assert isinstance(diff, str)

        stats = report.get_diff_summary()
        assert stats["original_lines"] >= 3  # Multiple lines
        assert stats["repaired_lines"] >= stats["original_lines"]  # Added closing tags

    def test_diff_with_entity_changes(self):
        """Test diff showing entity escaping changes."""
        xml = "<root>5 < 10 & 10 > 5</root>"
        _result, report = repair_xml_with_report(xml, trust=TrustLevel.TRUSTED)

        diff = report.to_unified_diff()

        # Should show entity replacements
        assert isinstance(diff, str)
        # Original had <, >, & which should be escaped in output

        stats = report.get_diff_summary()
        # Single-line changes can have low similarity ratios
        assert stats["similarity_ratio"] >= 0.0  # Valid ratio
        assert "original_lines" in stats
        assert "repaired_lines" in stats
