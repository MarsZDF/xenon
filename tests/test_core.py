import unittest
import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from xenon import repair_xml, parse_xml


class TestXenonCore(unittest.TestCase):
    """Essential tests for core XML repair functionality."""

    def test_truncation(self):
        """Test handling of truncated XML."""
        malformed = '<root><user name="alice"'
        expected = '<root><user name="alice"></user></root>'
        result = repair_xml(malformed)
        self.assertEqual(result, expected)

    def test_malformed_attributes(self):
        """Test fixing unquoted attribute values."""
        malformed = '<item id=123 type=product name=widget>'
        expected = '<item id="123" type="product" name="widget"></item>'
        result = repair_xml(malformed)
        self.assertEqual(result, expected)

    def test_unescaped_entities(self):
        """Test escaping unescaped & and < in text content."""
        malformed = '<text>A & B < C</text>'
        expected = '<text>A &amp; B &lt; C</text>'
        result = repair_xml(malformed)
        self.assertEqual(result, expected)

    def test_conversational_fluff(self):
        """Test removal of conversational text around XML."""
        malformed = 'Here is the XML: <root><message>Hello</message></root> Hope this helps!'
        expected = '<root><message>Hello</message></root>'
        result = repair_xml(malformed)
        self.assertEqual(result, expected)

    def test_self_closing_tags(self):
        """Test handling of self-closing tags."""
        malformed = '<root><item id=123/><item id=456/></root>'
        expected = '<root><item id="123"/><item id="456"/></root>'
        result = repair_xml(malformed)
        self.assertEqual(result, expected)

    def test_parse_xml_simple(self):
        """Test parsing simple XML to dictionary."""
        xml = '<root><message>Hello World</message></root>'
        expected = {
            'root': {
                'message': 'Hello World'
            }
        }
        result = parse_xml(xml)
        self.assertEqual(result, expected)

    def test_parse_xml_with_attributes(self):
        """Test parsing XML with attributes to dictionary."""
        xml = '<root><user id="123" name="John">Active</user></root>'
        result = parse_xml(xml)

        user_data = result['root']['user']
        self.assertEqual(user_data['@attributes']['id'], '123')
        self.assertEqual(user_data['@attributes']['name'], 'John')
        self.assertEqual(user_data['#text'], 'Active')

    def test_complex_malformed_xml(self):
        """Test complex case with multiple issues combined."""
        malformed = 'Here is your data: <root><users><user id=1 name=john><email>john@example.com</email><status>active & verified'
        expected = '<root><users><user id="1" name="john"><email>john@example.com</email><status>active &amp; verified</status></user></users></root>'
        result = repair_xml(malformed)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
