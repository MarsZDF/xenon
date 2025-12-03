"""Tests for validation functions."""

import pytest

from xenon.exceptions import ValidationError
from xenon.validation import validate_repaired_output, validate_xml_input


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
