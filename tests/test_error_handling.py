import os
import sys
import unittest

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from xenon import (
    TrustLevel,
    ValidationError,
    parse_xml_safe,
    repair_xml_lenient,
    repair_xml_safe,
)


class TestErrorHandling(unittest.TestCase):
    """Essential error handling tests for alpha release."""

    def test_invalid_input_raises_validation_error(self):
        """Test that invalid input raises ValidationError with helpful message."""
        # None input
        with self.assertRaises(ValidationError) as cm:
            repair_xml_safe(None, trust=TrustLevel.TRUSTED)
        self.assertIn("cannot be None", str(cm.exception))

        # Wrong type
        with self.assertRaises(ValidationError) as cm:
            repair_xml_safe(123, trust=TrustLevel.TRUSTED)
        self.assertIn("must be a string", str(cm.exception))

    def test_empty_string_handling(self):
        """Test empty string validation and allow_empty flag."""
        # Empty raises by default
        with self.assertRaises(ValidationError):
            repair_xml_safe("", trust=TrustLevel.TRUSTED)

        # Works with allow_empty=True
        result = repair_xml_safe("", trust=TrustLevel.TRUSTED, allow_empty=True)
        self.assertEqual(result, "")

    def test_safe_mode_repairs_xml(self):
        """Test that safe mode repairs malformed XML correctly."""
        result = repair_xml_safe("<root><item", trust=TrustLevel.TRUSTED)
        self.assertEqual(result, "<root><item></item></root>")

    def test_parse_xml_safe(self):
        """Test that parse_xml_safe works correctly."""
        result = parse_xml_safe("<root><item>test</item></root>", trust=TrustLevel.TRUSTED)
        self.assertEqual(result, {"root": {"item": "test"}})

    def test_lenient_mode_never_raises(self):
        """Test that lenient mode never raises exceptions."""
        # Should handle any input gracefully
        self.assertEqual(repair_xml_lenient(None), "")
        self.assertEqual(repair_xml_lenient(123), "123")
        self.assertEqual(repair_xml_lenient("<root><item"), "<root><item></item></root>")


if __name__ == "__main__":
    unittest.main()
