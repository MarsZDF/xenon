"""Tests for validation functions."""

import pytest

from xenon.exceptions import ValidationError
from xenon.validation import validate_repaired_output, validate_with_schema, validate_xml_input


class TestInputValidation:
    """Tests for validate_xml_input."""

    def test_max_size_ok(self):
        """Test that input smaller than max_size passes."""
        validate_xml_input("a" * 100, max_size=200)  # Should not raise

    def test_max_size_exceeded_bytes(self):
        """Test that input larger than max_size raises ValidationError (bytes format)."""
        with pytest.raises(ValidationError) as excinfo:
            validate_xml_input("a" * 100, max_size=50)
        assert "Input too large (100 bytes)" in str(excinfo.value)
        assert "Maximum allowed size is 50 bytes" in str(excinfo.value)

    def test_max_size_exceeded_kb(self):
        """Test that input larger than max_size raises ValidationError (KB format)."""
        with pytest.raises(ValidationError) as excinfo:
            validate_xml_input("a" * 2000, max_size=1024)
        assert "Input too large (1.95KB)" in str(excinfo.value)
        assert "Maximum allowed size is 1.00KB" in str(excinfo.value)

    def test_max_size_exceeded_mb(self):
        """Test that input larger than max_size raises ValidationError (MB format)."""
        with pytest.raises(ValidationError) as excinfo:
            validate_xml_input("a" * 2 * 1024 * 1024, max_size=1 * 1024 * 1024)
        assert "Input too large (2.00MB)" in str(excinfo.value)
        assert "Maximum allowed size is 1.00MB" in str(excinfo.value)

    def test_none_input_raises(self):
        """Test that None input raises a specific error."""
        with pytest.raises(ValidationError) as excinfo:
            validate_xml_input(None)
        assert "XML input cannot be None" in str(excinfo.value)

    def test_wrong_type_input_raises(self):
        """Test that non-string input raises a specific error."""
        with pytest.raises(ValidationError) as excinfo:
            validate_xml_input(12345)
        assert "must be a string, got int instead" in str(excinfo.value)


class TestOutputValidation:
    """Tests for validate_repaired_output."""

    def test_valid_output_passes(self):
        """Test that valid repaired output passes."""
        validate_repaired_output("<root></root>", "<root>")  # Should not raise

    def test_empty_output_raises(self):
        """Test that empty output raises ValidationError."""
        with pytest.raises(ValidationError) as excinfo:
            validate_repaired_output("   ", "<root>")
        assert "Repair produced empty output" in str(excinfo.value)

    def test_no_tags_output_raises(self):
        """Test that output without tags raises ValidationError."""
        with pytest.raises(ValidationError) as excinfo:
            validate_repaired_output("just some plain text", "<root>")
        assert "invalid output without XML tags" in str(excinfo.value)


_lxml_installed = False
try:
    from lxml import etree

    _lxml_installed = True
except ImportError:
    pass


@pytest.mark.skipif(not _lxml_installed, reason="lxml not installed")
class TestSchemaValidation:
    """Tests for validate_with_schema function."""

    # XSD Schema content
    XSD_SCHEMA = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="root">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="item" type="xs:string"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>"""

    # DTD Schema content
    DTD_SCHEMA = """<!ELEMENT root (item)>
<!ELEMENT item (#PCDATA)>"""

    def test_valid_xml_against_xsd(self):
        """Test valid XML passes XSD validation."""
        xml = "<root><item>test</item></root>"
        validate_with_schema(xml, self.XSD_SCHEMA)  # Should not raise

    def test_invalid_xml_against_xsd(self):
        """Test invalid XML raises ValidationError for XSD."""
        xml = "<root><wrong_item>test</wrong_item></root>"
        with pytest.raises(ValidationError) as excinfo:
            validate_with_schema(xml, self.XSD_SCHEMA)
        assert "Schema validation failed" in str(excinfo.value)
        assert "Element 'wrong_item': This element is not expected. Expected is ( item )." in str(
            excinfo.value
        )

    def test_valid_xml_against_dtd(self):
        """Test valid XML passes DTD validation."""
        xml = f"""<!DOCTYPE root [
{self.DTD_SCHEMA}
]>
<root><item>test</item></root>"""
        validate_with_schema(xml, self.DTD_SCHEMA)  # Should not raise

    def test_invalid_xml_against_dtd(self):
        """Test invalid XML raises ValidationError for DTD."""
        xml = f"""<!DOCTYPE root [
{self.DTD_SCHEMA}
]>
<root><wrong_item>test</wrong_item></root>"""
        with pytest.raises(ValidationError) as excinfo:
            validate_with_schema(xml, self.DTD_SCHEMA)
        assert "DTD validation failed" in str(excinfo.value)
        assert "Element root content does not follow the DTD" in str(excinfo.value)


@pytest.mark.skipif(_lxml_installed, reason="lxml is installed")
class TestSchemaValidationNoLXML:
    """Tests validate_with_schema behavior when lxml is not installed."""

    def test_lxml_not_installed_raises_importerror(self):
        """Test that ImportError is raised if lxml is not installed."""
        # To simulate lxml not installed, we temporarily remove it from sys.modules
        # This is a bit hacky but works for testing optional dependency behavior
        import sys

        if "lxml" in sys.modules:
            _lxml = sys.modules["lxml"]
            del sys.modules["lxml"]
        if "lxml.etree" in sys.modules:
            _lxml_etree = sys.modules["lxml.etree"]
            del sys.modules["lxml.etree"]

        try:
            with pytest.raises(ImportError) as excinfo:
                validate_with_schema("<root/>", "<xs:schema/>")
            assert "requires the 'lxml' library" in str(excinfo.value)
        finally:
            # Restore lxml if it was originally there
            if "lxml" in locals():
                sys.modules["lxml"] = _lxml
            if "lxml.etree" in locals():
                sys.modules["lxml.etree"] = _lxml_etree
