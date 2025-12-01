"""XML formatting utilities for Xenon."""

import re
import xml.dom.minidom  # nosec B408 - Only used on already-repaired XML
from typing import Literal

FormatStyle = Literal["pretty", "compact", "minify"]


def format_xml(
    xml_string: str,
    style: FormatStyle = "pretty",
    indent: str = "  ",
    max_line_length: int = 100,
    preserve_whitespace: bool = False,
) -> str:
    """
    Format XML with various styles.

    Args:
        xml_string: The XML string to format
        style: Formatting style - "pretty", "compact", or "minify"
        indent: Indentation string (default: 2 spaces)
        max_line_length: Maximum line length for wrapping (pretty mode only)
        preserve_whitespace: If True, preserve significant whitespace

    Returns:
        Formatted XML string

    Raises:
        ValueError: If XML is invalid or style is unknown

    Examples:
        >>> xml = '<root><item>test</item></root>'
        >>> print(format_xml(xml, style='pretty'))
        <root>
          <item>test</item>
        </root>

        >>> print(format_xml(xml, style='minify'))
        <root><item>test</item></root>
    """
    if not xml_string.strip():
        return xml_string

    if style == "minify":
        return _minify_xml(xml_string, preserve_whitespace)
    elif style == "compact":
        return _compact_xml(xml_string, preserve_whitespace)
    elif style == "pretty":
        return _pretty_print_xml(xml_string, indent, max_line_length)
    else:
        raise ValueError(f"Unknown format style: {style}. Use 'pretty', 'compact', or 'minify'")


def _minify_xml(xml_string: str, preserve_whitespace: bool = False) -> str:
    """
    Minify XML by removing all unnecessary whitespace.

    Args:
        xml_string: XML to minify
        preserve_whitespace: If True, only remove inter-element whitespace

    Returns:
        Minified XML string
    """
    if preserve_whitespace:
        # Only remove whitespace between tags
        result = re.sub(r">\s+<", "><", xml_string)
        return result.strip()
    else:
        # Remove all whitespace between tags and inside tags (aggressive)
        result = re.sub(r">\s+<", "><", xml_string)
        # Remove whitespace around attributes
        result = re.sub(r"\s+", " ", result)
        # Remove space after opening tag bracket
        result = re.sub(r"<\s+", "<", result)
        # Remove space before closing tag bracket
        result = re.sub(r"\s+>", ">", result)
        return result.strip()


def _compact_xml(xml_string: str, preserve_whitespace: bool = False) -> str:
    """
    Compact XML - one tag per line, minimal indentation.

    Args:
        xml_string: XML to compact
        preserve_whitespace: If True, preserve text content whitespace

    Returns:
        Compacted XML string
    """
    # Remove inter-element whitespace
    result = re.sub(r">\s+<", ">\n<", xml_string)
    if not preserve_whitespace:
        # Normalize whitespace in text content
        lines = result.split("\n")
        result = "\n".join(line.strip() for line in lines if line.strip())
    return result


def _pretty_print_xml(xml_string: str, indent: str = "  ", max_line_length: int = 100) -> str:
    """
    Pretty-print XML with proper indentation.

    Uses xml.dom.minidom for robust parsing and formatting.

    Args:
        xml_string: XML to format
        indent: Indentation string
        max_line_length: Maximum line length (currently advisory)

    Returns:
        Pretty-printed XML string
    """
    try:
        # Parse with minidom
        # Note: This is safe because format_xml() is only used on already-repaired XML
        dom = xml.dom.minidom.parseString(xml_string)  # nosec B318

        # Pretty print with custom indent
        pretty = dom.toprettyxml(indent=indent, encoding=None)

        # Remove extra blank lines that minidom adds
        lines = [line for line in pretty.split("\n") if line.strip()]

        result = "\n".join(lines)

        # Remove XML declaration if it wasn't in original
        if not xml_string.strip().startswith("<?xml"):
            result = re.sub(r"<\?xml[^>]+\?>\n?", "", result)

        return result

    except Exception:
        # Fallback: simple indentation if minidom fails
        return _simple_indent(xml_string, indent)


def _simple_indent(xml_string: str, indent: str = "  ") -> str:
    """
    Simple indentation fallback when minidom fails.

    Args:
        xml_string: XML to indent
        indent: Indentation string

    Returns:
        Indented XML string
    """
    level = 0
    result = []

    # Split by tags
    parts = re.split(r"(<[^>]+>)", xml_string)

    for part in parts:
        if not part.strip():
            continue

        if part.startswith("</"):
            # Closing tag - decrease indent
            level -= 1
            result.append(indent * level + part)
        elif part.startswith("<"):
            # Opening or self-closing tag
            result.append(indent * level + part)
            if not part.endswith("/>") and not part.startswith("<?") and not part.startswith("<!"):
                level += 1
        else:
            # Text content
            text = part.strip()
            if text:
                result.append(indent * level + text)

    return "\n".join(result)


def preserve_formatting(xml_string: str) -> str:
    """
    Normalize formatting while preserving intentional structure.

    This is useful when you want to clean up messy LLM output
    without completely reformatting it.

    Args:
        xml_string: XML to normalize

    Returns:
        Normalized XML
    """
    # Normalize line endings
    result = xml_string.replace("\r\n", "\n").replace("\r", "\n")

    # Remove trailing whitespace from each line
    lines = [line.rstrip() for line in result.split("\n")]

    # Remove excess blank lines (max 1 blank line)
    normalized_lines = []
    prev_blank = False

    for line in lines:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue  # Skip consecutive blank lines
        normalized_lines.append(line)
        prev_blank = is_blank

    return "\n".join(normalized_lines)
