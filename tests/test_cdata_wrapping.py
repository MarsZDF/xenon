"""Tests for CDATA wrapping feature."""

import pytest

from xenon import TrustLevel, XMLRepairEngine, repair_xml_safe
from xenon.config import RepairFlags, XMLRepairConfig


class TestCDATAWrapping:
    """Test automatic CDATA wrapping for code-like content."""

    def test_cdata_wraps_code_tag_with_special_chars(self):
        """CDATA should wrap <code> tags containing special XML characters."""
        xml = "<code>if (x < 5 && y > 3) { return true; }</code>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        assert "<![CDATA[if (x < 5 && y > 3) { return true; }]]>" in result
        assert "<code>" in result
        assert "</code>" in result

    def test_cdata_wraps_script_tag(self):
        """CDATA should wrap <script> tags with special characters."""
        xml = "<script>var x = 5 < 10 && y > 3;</script>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        assert "<![CDATA[var x = 5 < 10 && y > 3;]]>" in result

    def test_cdata_wraps_pre_tag(self):
        """CDATA should wrap <pre> tags with special characters."""
        xml = "<pre>for (i = 0; i < n; i++) { arr[i] = i & 0xFF; }</pre>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        assert "<![CDATA[" in result
        assert "]]>" in result

    def test_cdata_wraps_sql_tag(self):
        """CDATA should wrap <sql> tags with special characters."""
        xml = "<sql>SELECT * FROM users WHERE age > 18 AND status = 'active'</sql>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        assert "<![CDATA[" in result

    def test_cdata_does_not_wrap_simple_text(self):
        """CDATA should not wrap content without enough special characters."""
        xml = "<code>simple text</code>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        # Should just escape normally, no CDATA
        assert "<![CDATA[" not in result
        assert result == "<code>simple text</code>"

    def test_cdata_does_not_wrap_when_disabled(self):
        """CDATA should not wrap when feature is disabled."""
        xml = "<code>if (x < 5 && y > 3) { return true; }</code>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=False)

        # Should escape entities instead
        assert "<![CDATA[" not in result
        assert "&lt;" in result or "&amp;" in result

    def test_cdata_does_not_wrap_non_code_tags(self):
        """CDATA should not wrap regular tags like <div>, <span>, <p>."""
        xml = "<div>if (x < 5 && y > 3) { return true; }</div>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        # Not a code tag, so should escape even with special chars
        assert "<![CDATA[" not in result
        assert "&lt;" in result or "&amp;" in result

    def test_cdata_handles_embedded_cdata_terminator(self):
        """CDATA should handle ]]> in content by splitting CDATA sections."""
        xml = '<code>char* end = strstr(buf, "]]>");</code>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        # Should escape the ]]> properly
        assert "<![CDATA[" in result
        # The ]]> in content should be split: ]]]]><![CDATA[>
        assert "]]]]><![CDATA[>" in result

    def test_cdata_with_multiple_code_blocks(self):
        """CDATA should wrap multiple code blocks independently."""
        xml = """<root>
            <code>if (x < 5) { foo(); }</code>
            <text>Normal text</text>
            <script>var x = y && z;</script>
        </root>"""
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        # Should have 2 CDATA sections
        assert result.count("<![CDATA[") == 2
        assert result.count("]]>") == 2

    def test_cdata_with_nested_tags(self):
        """CDATA wrapping should work correctly with nested tags."""
        xml = "<root><code>x < 5 && y > 3</code></root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        assert "<root>" in result
        assert "<code><![CDATA[x < 5 && y > 3]]></code>" in result
        assert "</root>" in result

    def test_cdata_with_config_api(self):
        """CDATA should work with XMLRepairConfig API."""
        config = XMLRepairConfig(repair=RepairFlags.AUTO_WRAP_CDATA)
        engine = XMLRepairEngine(config)

        xml = "<code>if (x < 5 && y > 3) { return; }</code>"
        repaired_xml, _ = engine.repair_xml(xml)

        assert "<![CDATA[" in repaired_xml

    def test_cdata_combined_with_other_features(self):
        """CDATA should work alongside other repair features."""
        xml = "<root><code>value > threshold</code></root>"
        result = repair_xml_safe(
            xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True, wrap_multiple_roots=False
        )

        # Should wrap CDATA for code content
        assert "<![CDATA[value > threshold]]>" in result

    def test_cdata_all_candidate_tags(self):
        """Verify all CDATA candidate tags are recognized."""
        candidate_tags = [
            "code",
            "script",
            "pre",
            "source",
            "sql",
            "query",
            "formula",
            "expression",
            "xpath",
            "regex",
        ]

        for tag in candidate_tags:
            xml = f"<{tag}>x < 5 && y > 3</{tag}>"
            result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)
            assert "<![CDATA[" in result, f"Tag <{tag}> should trigger CDATA wrapping"

    def test_cdata_case_insensitive_tags(self):
        """CDATA detection should be case-insensitive."""
        xml = "<CODE>x < 5 && y > 3</CODE>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        assert "<![CDATA[" in result

    def test_cdata_empty_content(self):
        """CDATA should not wrap empty or whitespace-only content."""
        xml = "<code>   </code>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        assert "<![CDATA[" not in result

    def test_cdata_single_special_char(self):
        """CDATA should wrap code content with special characters."""
        xml = "<code>hello & world</code>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        # Even 1 ampersand in code tag triggers CDATA
        assert "<![CDATA[hello & world]]>" in result

    def test_cdata_threshold_with_comparison(self):
        """CDATA should wrap code with comparison operators."""
        xml = "<code>x < 5</code>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        # Has < comparison - should wrap
        assert "<![CDATA[x < 5]]>" in result

    def test_cdata_with_braces(self):
        """CDATA should wrap code with comparison operators."""
        xml = "<code>function() { if (x > 5) return {}; }</code>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        # Has > comparison operator, should trigger CDATA
        assert "<![CDATA[function() { if (x > 5) return {}; }]]>" in result

    def test_cdata_preserves_existing_cdata(self):
        """Existing CDATA sections should be preserved."""
        xml = "<code><![CDATA[x < 5]]></code>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        # Should preserve the existing CDATA
        assert "<![CDATA[x < 5]]>" in result

    def test_cdata_real_world_javascript(self):
        """Test with real-world JavaScript code."""
        js_code = """
        function validate(x) {
            if (x > 0 && x < 100) {
                return { valid: true, msg: "OK" };
            }
            return { valid: false };
        }
        """.strip()

        xml = f"<script>{js_code}</script>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        assert "<![CDATA[" in result
        assert js_code in result
        # Should not escape the content
        assert "&lt;" not in result
        assert "&gt;" not in result

    def test_cdata_real_world_sql(self):
        """Test with real-world SQL query."""
        sql = "SELECT * FROM users WHERE age > 18 AND status = 'active' AND (role = 'admin' OR role = 'moderator')"

        xml = f"<query>{sql}</query>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        assert "<![CDATA[" in result
        assert sql in result

    def test_cdata_real_world_xpath(self):
        """Test with XPath expression."""
        xpath = "//div[@class='content' and position() > 1]/span[text() != '']"

        xml = f"<xpath>{xpath}</xpath>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        assert "<![CDATA[" in result
        assert xpath in result
