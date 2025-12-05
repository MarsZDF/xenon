"""Tests for the Xenon CLI."""

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from xenon.cli import main

# Sample XML for testing
BROKEN_XML = "<root><item>unclosed"
VALID_XML = "<root><item>test</item></root>"
SCHEMA_XSD = """<?xml version=\"1.0\"?>
<xs:schema xmlns:xs=\"http://www.w3.org/2001/XMLSchema\">
  <xs:element name=\"root\">
    <xs:complexType>
      <xs:sequence>
        <xs:element name=\"item\" type=\"xs:string\"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""


@pytest.fixture
def input_file(tmp_path):
    f = tmp_path / "input.xml"
    f.write_text(BROKEN_XML, encoding="utf-8")
    return f


@pytest.fixture
def valid_file(tmp_path):
    f = tmp_path / "valid.xml"
    f.write_text(VALID_XML, encoding="utf-8")
    return f


@pytest.fixture
def schema_file(tmp_path):
    f = tmp_path / "schema.xsd"
    f.write_text(SCHEMA_XSD, encoding="utf-8")
    return f


def test_cli_help(capsys):
    """Test that --help prints usage."""
    with pytest.raises(SystemExit):
        main(["--help"])

    captured = capsys.readouterr()
    assert "Xenon: Secure XML Repair Tool" in captured.out
    assert "repair" in captured.out
    assert "validate" in captured.out
    assert "diff" in captured.out


def test_cli_version(capsys):
    """Test that --version prints version."""
    with pytest.raises(SystemExit):
        main(["--version"])

    captured = capsys.readouterr()
    assert "Xenon v" in captured.out


def test_repair_file_to_stdout(input_file, capsys):
    """Test repairing a file to stdout."""
    main(["repair", str(input_file)])

    captured = capsys.readouterr()
    assert "<root><item>unclosed</item></root>" in captured.out


def test_repair_file_to_file(input_file, tmp_path):
    """Test repairing a file to an output file."""
    output = tmp_path / "output.xml"
    main(["repair", str(input_file), "-o", str(output)])

    assert output.exists()
    assert output.read_text(encoding="utf-8") == "<root><item>unclosed</item></root>"


def test_repair_in_place(tmp_path):
    """Test repairing a file in-place."""
    f = tmp_path / "inplace.xml"
    f.write_text(BROKEN_XML, encoding="utf-8")

    main(["repair", str(f), "--in-place"])

    assert f.read_text(encoding="utf-8") == "<root><item>unclosed</item></root>"


def test_repair_in_place_requires_file(capsys):
    """Test that --in-place fails without input file."""
    with pytest.raises(SystemExit) as excinfo:
        main(["repair", "--in-place"])

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    # Argument parser might catch this first or our check
    # Since input_file is positional optional, argparse allows it missing.
    # Our logic handles the error.
    assert "Error" in captured.err or "requires an input file" in captured.err


def test_repair_stdin(capsys):
    """Test repairing from stdin."""
    with patch("sys.stdin", StringIO(BROKEN_XML)):
        # We need to mock isatty to return False (piped input)
        sys.stdin.isatty = MagicMock(return_value=False)
        main(["repair"])

    captured = capsys.readouterr()
    assert "<root><item>unclosed</item></root>" in captured.out


def test_validate_success(valid_file, schema_file, capsys):
    """Test successful validation."""
    try:
        import lxml
    except ImportError:
        pytest.skip("lxml not installed")

    main(["validate", str(valid_file), "--schema", str(schema_file)])

    captured = capsys.readouterr()
    assert "Validation successful" in captured.out


def test_validate_failure(input_file, schema_file, capsys):
    """Test failed validation."""
    try:
        import lxml
    except ImportError:
        pytest.skip("lxml not installed")

    with pytest.raises(SystemExit) as excinfo:
        main(["validate", str(input_file), "--schema", str(schema_file)])

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Validation failed" in captured.err


def test_diff_output(input_file, capsys):
    """Test diff command output."""
    main(["diff", str(input_file)])

    captured = capsys.readouterr()
    assert "--- Original" in captured.out
    assert "+++ Repaired" in captured.out
    # Should show the added closing tags
    assert "+<root><item>unclosed</item></root>" in captured.out


def test_format_pretty(input_file, capsys):
    """Test repair with formatting."""
    main(["repair", str(input_file), "--format", "pretty"])

    captured = capsys.readouterr()
    assert "\n  <item>" in captured.out  # Indentation check
