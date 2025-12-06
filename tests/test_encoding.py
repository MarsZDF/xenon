"""Tests for encoding detection and normalization (v0.6.0)."""

import pytest

from xenon.encoding import (
    add_xml_declaration,
    detect_encoding,
    fix_xml_declaration_encoding,
    normalize_encoding,
    normalize_line_endings,
    strip_bom,
)


class TestEncodingDetection:
    """Test encoding detection functionality."""

    def test_detect_utf8_bom(self):
        """Test detection of UTF-8 BOM."""
        data = b"\xef\xbb\xbf<root/>"
        encoding, confidence = detect_encoding(data)

        assert encoding == "utf-8-sig"
        assert confidence == 1.0

    def test_detect_utf16_le_bom(self):
        """Test detection of UTF-16 LE BOM."""
        data = b"\xff\xfe<\x00r\x00o\x00o\x00t\x00/\x00>"
        encoding, confidence = detect_encoding(data)

        assert encoding == "utf-16-le"
        assert confidence == 1.0

    def test_detect_utf16_be_bom(self):
        """Test detection of UTF-16 BE BOM."""
        data = b"\xfe\xff\x00<\x00r\x00o\x00o\x00t\x00/\x00>"
        encoding, confidence = detect_encoding(data)

        assert encoding == "utf-16-be"
        assert confidence == 1.0

    def test_detect_from_xml_declaration(self):
        """Test detection from XML declaration."""
        data = b'<?xml version="1.0" encoding="UTF-8"?><root/>'
        encoding, confidence = detect_encoding(data)

        assert encoding.lower() == "utf-8"
        assert confidence >= 0.8

    def test_detect_string_input(self):
        """Test detection when input is already a string."""
        data = "<root>test</root>"
        encoding, confidence = detect_encoding(data)

        assert encoding == "utf-8"
        assert confidence >= 0.0

    def test_detect_utf8_without_bom(self):
        """Test UTF-8 detection without BOM."""
        data = "<root>café</root>".encode()
        encoding, _confidence = detect_encoding(data)

        assert encoding.lower() == "utf-8"

    def test_detect_latin1(self):
        """Test Latin-1 detection."""
        data = "<root>caf\xe9</root>".encode("latin-1")
        encoding, _confidence = detect_encoding(data)

        # Should detect some encoding (exact one may vary)
        assert encoding in ["latin-1", "iso-8859-1", "cp1252", "utf-8"]


class TestEncodingNormalization:
    """Test encoding normalization."""

    def test_normalize_utf8_bytes(self):
        """Test normalizing UTF-8 bytes to string."""
        data = "café".encode()
        result = normalize_encoding(data)

        assert result == "café"
        assert isinstance(result, str)

    def test_normalize_latin1_bytes(self):
        """Test normalizing Latin-1 bytes to string."""
        data = b"caf\xe9"  # Latin-1 café
        result = normalize_encoding(data)

        assert "caf" in result
        assert isinstance(result, str)

    def test_normalize_string_input(self):
        """Test normalizing string input."""
        data = "café"
        result = normalize_encoding(data)

        assert result == "café"

    def test_normalize_with_unicode_normalization(self):
        """Test Unicode NFC normalization."""
        # é can be represented as single char or e + combining accent
        data_combined = "caf\u00e9"  # Single char é
        data_decomposed = "cafe\u0301"  # e + combining accent

        result1 = normalize_encoding(data_combined, normalize_unicode=True)
        result2 = normalize_encoding(data_decomposed, normalize_unicode=True)

        # Both should normalize to the same form
        assert result1 == result2

    def test_normalize_without_unicode_normalization(self):
        """Test without Unicode normalization."""
        data = "café"
        result = normalize_encoding(data, normalize_unicode=False)

        assert result == "café"


class TestBOMHandling:
    """Test BOM (Byte Order Mark) handling."""

    def test_strip_utf8_bom_bytes(self):
        """Test stripping UTF-8 BOM from bytes."""
        data = b"\xef\xbb\xbf<root/>"
        result = strip_bom(data)

        assert result == b"<root/>"
        assert not result.startswith(b"\xef\xbb\xbf")

    def test_strip_utf16_le_bom(self):
        """Test stripping UTF-16 LE BOM."""
        data = b"\xff\xfe<root/>"
        result = strip_bom(data)

        assert result == b"<root/>"

    def test_strip_utf16_be_bom(self):
        """Test stripping UTF-16 BE BOM."""
        data = b"\xfe\xff<root/>"
        result = strip_bom(data)

        assert result == b"<root/>"

    def test_strip_bom_string(self):
        """Test stripping BOM from string."""
        data = "\ufeff<root/>"
        result = strip_bom(data)

        assert result == "<root/>"

    def test_strip_bom_no_bom_present(self):
        """Test stripping BOM when none is present."""
        data = b"<root/>"
        result = strip_bom(data)

        assert result == b"<root/>"


class TestXMLDeclaration:
    """Test XML declaration handling."""

    def test_fix_xml_declaration_encoding(self):
        """Test fixing XML declaration encoding."""
        xml = '<?xml version="1.0" encoding="iso-8859-1"?><root/>'
        result = fix_xml_declaration_encoding(xml, "utf-8")

        assert 'encoding="utf-8"' in result
        assert 'encoding="iso-8859-1"' not in result

    def test_fix_declaration_no_encoding(self):
        """Test when XML has no declaration."""
        xml = "<root/>"
        result = fix_xml_declaration_encoding(xml, "utf-8")

        assert result == "<root/>"

    def test_add_xml_declaration(self):
        """Test adding XML declaration."""
        xml = "<root/>"
        result = add_xml_declaration(xml)

        assert '<?xml version="1.0" encoding="utf-8"?>' in result
        assert "<root/>" in result

    def test_add_declaration_custom_encoding(self):
        """Test adding declaration with custom encoding."""
        xml = "<root/>"
        result = add_xml_declaration(xml, encoding="latin-1")

        assert 'encoding="latin-1"' in result

    def test_add_declaration_already_present(self):
        """Test adding declaration when already present."""
        xml = '<?xml version="1.0"?><root/>'
        result = add_xml_declaration(xml)

        # Should not add another declaration
        assert xml == result


class TestLineEndings:
    """Test line ending normalization."""

    def test_normalize_to_unix(self):
        """Test normalizing to Unix line endings."""
        text = "line1\r\nline2\rline3\n"
        result = normalize_line_endings(text, "unix")

        assert result == "line1\nline2\nline3\n"
        assert "\r" not in result

    def test_normalize_to_windows(self):
        """Test normalizing to Windows line endings."""
        text = "line1\nline2\rline3\r\n"
        result = normalize_line_endings(text, "windows")

        assert result == "line1\r\nline2\r\nline3\r\n"
        assert result.count("\r\n") == 3

    def test_normalize_to_mac(self):
        """Test normalizing to Mac (old) line endings."""
        text = "line1\nline2\r\nline3"
        result = normalize_line_endings(text, "mac")

        assert "\n" not in result or result.count("\n") == 0
        assert result.count("\r") >= 2
