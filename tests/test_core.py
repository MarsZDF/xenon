import os
import sys
import unittest

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from xenon import TrustLevel, parse_xml, repair_xml


class TestXenonCore(unittest.TestCase):
    """Essential tests for core XML repair functionality."""

    def test_truncation(self):
        """Test handling of truncated XML."""
        malformed = '<root><user name="alice"'
        expected = '<root><user name="alice"></user></root>'
        result = repair_xml(malformed, trust=TrustLevel.TRUSTED)
        self.assertEqual(result, expected)

    def test_malformed_attributes(self):
        """Test fixing unquoted attribute values."""
        malformed = "<item id=123 type=product name=widget>"
        expected = '<item id="123" type="product" name="widget"></item>'
        result = repair_xml(malformed, trust=TrustLevel.TRUSTED)
        self.assertEqual(result, expected)

    def test_unescaped_entities(self):
        """Test escaping unescaped & and < in text content."""
        malformed = "<text>A & B < C</text>"
        expected = "<text>A &amp; B &lt; C</text>"
        result = repair_xml(malformed, trust=TrustLevel.TRUSTED)
        self.assertEqual(result, expected)

    def test_conversational_fluff(self):
        """Test removal of conversational text around XML."""
        malformed = "Here is the XML: <root><message>Hello</message></root> Hope this helps!"
        expected = "<root><message>Hello</message></root>"
        result = repair_xml(malformed, trust=TrustLevel.TRUSTED)
        self.assertEqual(result, expected)

    def test_self_closing_tags(self):
        """Test handling of self-closing tags."""
        malformed = "<root><item id=123/><item id=456/></root>"
        expected = '<root><item id="123"/><item id="456"/></root>'
        result = repair_xml(malformed, trust=TrustLevel.TRUSTED)
        self.assertEqual(result, expected)

    def test_parse_xml_simple(self):
        """Test parsing simple XML to dictionary."""
        xml = "<root><message>Hello World</message></root>"
        expected = {"root": {"message": "Hello World"}}
        result = parse_xml(xml, trust=TrustLevel.TRUSTED)
        self.assertEqual(result, expected)

    def test_parse_xml_with_attributes(self):
        """Test parsing XML with attributes to dictionary."""
        xml = '<root><user id="123" name="John">Active</user></root>'
        result = parse_xml(xml, trust=TrustLevel.TRUSTED)

        user_data = result["root"]["user"]
        self.assertEqual(user_data["@attributes"]["id"], "123")
        self.assertEqual(user_data["@attributes"]["name"], "John")
        self.assertEqual(user_data["#text"], "Active")

    def test_complex_malformed_xml(self):
        """Test complex case with multiple issues combined."""
        malformed = "Here is your data: <root><users><user id=1 name=john><email>john@example.com</email><status>active & verified"
        expected = '<root><users><user id="1" name="john"><email>john@example.com</email><status>active &amp; verified</status></user></users></root>'
        result = repair_xml(malformed, trust=TrustLevel.TRUSTED)
        self.assertEqual(result, expected)

    def test_cdata_wrapping(self):
        """Test automatic CDATA wrapping for code content."""
        from xenon import repair_xml_safe

        malformed = "<code>function test() { return x && y; }</code>"
        result = repair_xml_safe(malformed, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)
        # Should wrap in CDATA because contains & special characters
        self.assertIn("<![CDATA[", result)
        self.assertIn("function test()", result)
        self.assertIn("]]>", result)

    def test_case_insensitive_tags(self):
        """Test case-insensitive tag matching uses opening tag's case."""
        malformed = "<Root><Item>text</item></Root>"
        expected = "<Root><Item>text</Item></Root>"
        result = repair_xml(malformed, trust=TrustLevel.TRUSTED)
        self.assertEqual(result, expected)

    def test_namespace_injection(self):
        """Test automatic namespace declaration injection."""
        malformed = "<soap:Envelope><soap:Body>test</soap:Body></soap:Envelope>"
        result = repair_xml(malformed, trust=TrustLevel.TRUSTED)
        # Should inject xmlns:soap declaration
        self.assertIn("xmlns:soap=", result)
        self.assertIn("http://schemas.xmlsoap.org/soap/envelope/", result)

    def test_duplicate_attributes(self):
        """Test duplicate attribute removal (keeps first occurrence)."""
        malformed = '<item id="1" name="foo" id="2">'
        result = repair_xml(malformed, trust=TrustLevel.TRUSTED)
        # Should only have one id attribute
        self.assertEqual(result.count("id="), 1)
        self.assertIn('id="1"', result)
        self.assertNotIn('id="2"', result)

    # Security tests
    def test_cdata_breakout_security(self):
        """Test CDATA ]]> breakout prevention."""
        malformed = "<code>]]>malicious</code>"
        result = repair_xml(malformed, trust=TrustLevel.TRUSTED)
        # Should not have unescaped ]]> that breaks CDATA
        if "<![CDATA[" in result:
            # If CDATA was used, ensure ]]> is properly escaped
            self.assertIn("]]]]><![CDATA[>", result)

    def test_duplicate_attr_first_wins(self):
        """Security test: Verify first duplicate attribute value is used."""
        malformed = '<user role="admin" name="alice" role="user">'
        result = repair_xml(malformed, trust=TrustLevel.TRUSTED)
        # First role value should be preserved
        self.assertIn('role="admin"', result)
        self.assertNotIn('role="user"', result)

    def test_namespace_no_xxe(self):
        """Security test: Verify namespace injection doesn't introduce entities."""
        malformed = "<xsi:root>test</xsi:root>"
        result = repair_xml(malformed, trust=TrustLevel.TRUSTED)
        # Should not contain entity declarations
        self.assertNotIn("<!ENTITY", result)
        self.assertNotIn("<!DOCTYPE", result)


if __name__ == "__main__":
    unittest.main()
