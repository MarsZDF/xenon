"""Tests for security features (v0.4.0)."""

import pytest

from xenon import XMLRepairEngine, repair_xml_safe


class TestSecurityFeatures:
    """Test suite for security features added in v0.4.0."""

    def test_dangerous_pi_stripping_php(self):
        """Test stripping of PHP processing instructions."""
        xml = '<?php system("whoami"); ?><root>data</root>'
        result = repair_xml_safe(xml, strip_dangerous_pis=True)
        assert "<?php" not in result
        assert "<root>data</root>" in result

    def test_dangerous_pi_stripping_asp(self):
        """Test stripping of ASP processing instructions."""
        xml = '<?asp Response.Write("hacked") ?><root>data</root>'
        result = repair_xml_safe(xml, strip_dangerous_pis=True)
        assert "<?asp" not in result
        assert "<root>data</root>" in result

    def test_dangerous_pi_stripping_jsp(self):
        """Test stripping of JSP processing instructions."""
        xml = '<?jsp out.println("hacked"); ?><root>data</root>'
        result = repair_xml_safe(xml, strip_dangerous_pis=True)
        assert "<?jsp" not in result
        assert "<root>data</root>" in result

    def test_safe_pi_preserved(self):
        """Test that safe PIs like xml-stylesheet are preserved."""
        xml = '<?xml-stylesheet type="text/xsl" href="style.xsl"?><root>data</root>'
        result = repair_xml_safe(xml, strip_dangerous_pis=True)
        assert "<?xml-stylesheet" in result
        assert "<root>data</root>" in result

    def test_dangerous_pi_disabled_by_default(self):
        """Test that dangerous PI stripping is OFF by default."""
        xml = '<?php echo "test"; ?><root>data</root>'
        result = repair_xml_safe(xml)  # No strip_dangerous_pis flag
        assert "<?php" in result  # Should be preserved

    def test_external_entity_stripping(self):
        """Test stripping of DOCTYPE with external entities."""
        xml = """<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root>&xxe;</root>"""
        result = repair_xml_safe(xml, strip_external_entities=True)
        assert "<!DOCTYPE" not in result
        assert "SYSTEM" not in result
        assert "<root>" in result

    def test_external_entity_public(self):
        """Test stripping of PUBLIC entity declarations."""
        xml = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0//EN" "http://example.com">
<root>data</root>"""
        result = repair_xml_safe(xml, strip_external_entities=True)
        assert "<!DOCTYPE" not in result
        assert "PUBLIC" not in result
        assert "<root>data</root>" in result

    def test_external_entity_disabled_by_default(self):
        """Test that entity stripping is OFF by default."""
        xml = "<!DOCTYPE root><root>data</root>"
        result = repair_xml_safe(xml)  # No strip_external_entities flag
        assert "<!DOCTYPE" in result  # Should be preserved

    def test_dangerous_tags_script(self):
        """Test stripping of script tags."""
        xml = '<root><script>alert("XSS")</script><data>clean</data></root>'
        result = repair_xml_safe(xml, strip_dangerous_tags=True)
        assert "<script>" not in result
        assert "</script>" not in result
        assert 'alert("XSS")' in result  # Content preserved, tags stripped
        assert "<data>clean</data>" in result

    def test_dangerous_tags_iframe(self):
        """Test stripping of iframe tags."""
        xml = '<root><iframe src="evil.com"></iframe><data>clean</data></root>'
        result = repair_xml_safe(xml, strip_dangerous_tags=True)
        assert "<iframe" not in result
        assert "</iframe>" not in result
        assert "<data>clean</data>" in result

    def test_dangerous_tags_object(self):
        """Test stripping of object tags."""
        xml = '<root><object data="evil.swf"></object><data>clean</data></root>'
        result = repair_xml_safe(xml, strip_dangerous_tags=True)
        assert "<object" not in result
        assert "</object>" not in result
        assert "<data>clean</data>" in result

    def test_dangerous_tags_embed(self):
        """Test stripping of embed tags."""
        xml = '<root><embed src="evil.swf"></embed><data>clean</data></root>'
        result = repair_xml_safe(xml, strip_dangerous_tags=True)
        assert "<embed" not in result
        assert "</embed>" not in result
        assert "<data>clean</data>" in result

    def test_dangerous_tags_disabled_by_default(self):
        """Test that dangerous tag stripping is OFF by default."""
        xml = "<root><script>code</script></root>"
        result = repair_xml_safe(xml)  # No strip_dangerous_tags flag
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
            xml, strip_dangerous_pis=True, strip_external_entities=True, strip_dangerous_tags=True
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
        result = repair_xml_safe(xml, strip_dangerous_pis=True, strip_dangerous_tags=True)
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
        result = engine.repair_xml(xml)
        assert "<?php" not in result
        assert "<script>" not in result
        assert "<root>" in result

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
        result = repair_xml_safe(xml)
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
        result = repair_xml_safe(xxe_xml, strip_external_entities=True)
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
        result = repair_xml_safe(xss_xml, strip_dangerous_tags=True)
        assert "<script>" not in result
        assert "</script>" not in result
        # Content should still be there, just tags stripped
        assert "alert(document.cookie)" in result
        assert "<safe>This is clean content</safe>" in result
