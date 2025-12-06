"""Encoding detection and normalization for Xenon."""

import re
import unicodedata
from typing import Tuple, Union


def detect_encoding(data: Union[bytes, str]) -> Tuple[str, float]:
    """
    Detect encoding of XML data.

    Checks (in order):
    1. BOM (Byte Order Mark)
    2. XML declaration encoding attribute
    3. Common patterns for UTF-8/UTF-16/Latin-1

    Args:
        data: XML data as bytes or string

    Returns:
        Tuple of (encoding_name, confidence) where confidence is 0.0-1.0

    Examples:
        >>> detect_encoding(b'<?xml version="1.0" encoding="UTF-8"?><root/>')
        ('utf-8', 1.0)

        >>> detect_encoding(b'\\xef\\xbb\\xbf<root/>') # UTF-8 BOM
        ('utf-8-sig', 1.0)
    """
    if isinstance(data, str):
        # Already decoded, assume UTF-8
        return ("utf-8", 0.8)

    # Check for BOM (Byte Order Mark)
    if data.startswith(b"\xef\xbb\xbf"):
        return ("utf-8-sig", 1.0)
    elif data.startswith(b"\xff\xfe"):
        return ("utf-16-le", 1.0)
    elif data.startswith(b"\xfe\xff"):
        return ("utf-16-be", 1.0)
    elif data.startswith(b"\x00\x00\xfe\xff"):
        return ("utf-32-be", 1.0)
    elif data.startswith(b"\xff\xfe\x00\x00"):
        return ("utf-32-le", 1.0)

    # Try to decode as UTF-8 to find XML declaration
    try:
        decoded = data.decode("utf-8", errors="ignore")
        encoding_match = re.search(r'<\?xml[^>]+encoding\s*=\s*["\']([^"\']+)["\']', decoded)
        if encoding_match:
            declared_encoding = encoding_match.group(1).lower()
            # Verify it's a valid encoding name
            try:
                "test".encode(declared_encoding)
                return (declared_encoding, 0.9)
            except (LookupError, ValueError):
                # Invalid encoding name, fall through
                pass
    except UnicodeDecodeError:
        pass

    # Try common encodings and score them
    encodings_to_try = [
        ("utf-8", 0.7),
        ("latin-1", 0.5),
        ("cp1252", 0.5),  # Windows Latin-1
        ("iso-8859-1", 0.5),
    ]

    for encoding, base_confidence in encodings_to_try:
        try:
            decoded = data.decode(encoding)
            # Higher confidence if no replacement characters
            if "\ufffd" not in decoded:
                return (encoding, base_confidence)
        except (UnicodeDecodeError, LookupError):
            continue

    # Fallback: latin-1 (accepts all bytes)
    return ("latin-1", 0.3)


def normalize_encoding(
    data: Union[bytes, str], target_encoding: str = "utf-8", normalize_unicode: bool = True
) -> str:
    """
    Normalize data to target encoding and optionally normalize Unicode.

    Args:
        data: Input data (bytes or string)
        target_encoding: Target encoding (default: utf-8)
        normalize_unicode: If True, apply Unicode NFC normalization

    Returns:
        Normalized string

    Examples:
        >>> normalize_encoding(b'<root>caf\\xc3\\xa9</root>')  # UTF-8 café
        '<root>café</root>'

        >>> normalize_encoding(b'<root>caf\\xe9</root>')  # Latin-1 café
        '<root>café</root>'
    """
    # Decode if bytes
    if isinstance(data, bytes):
        detected_encoding, confidence = detect_encoding(data)

        # If confidence is low, try multiple encodings
        if confidence < 0.7:
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    text = data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                # Fallback: decode with errors='replace'
                text = data.decode(detected_encoding, errors="replace")
        else:
            try:
                text = data.decode(detected_encoding)
            except UnicodeDecodeError:
                text = data.decode(detected_encoding, errors="replace")
    else:
        text = data

    # Apply Unicode normalization if requested
    if normalize_unicode:
        text = unicodedata.normalize("NFC", text)

    return text


def strip_bom(data: Union[bytes, str]) -> Union[bytes, str]:
    """
    Remove BOM (Byte Order Mark) from data.

    Args:
        data: Input data

    Returns:
        Data with BOM removed

    Examples:
        >>> strip_bom(b'\\xef\\xbb\\xbf<root/>')
        b'<root/>'

        >>> strip_bom('\\ufeff<root/>')
        '<root/>'
    """
    if isinstance(data, bytes):
        # Remove common BOMs
        if data.startswith(b"\xef\xbb\xbf"):  # UTF-8
            return data[3:]
        elif data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):  # UTF-16
            return data[2:]
        elif data.startswith(b"\x00\x00\xfe\xff") or data.startswith(b"\xff\xfe\x00\x00"):  # UTF-32
            return data[4:]
    elif isinstance(data, str) and data.startswith("\ufeff"):
        # Remove Unicode BOM character
        return data[1:]

    return data


def fix_xml_declaration_encoding(xml_string: str, actual_encoding: str = "utf-8") -> str:
    """
    Fix XML declaration to match actual encoding.

    Args:
        xml_string: XML string
        actual_encoding: The actual encoding of the content

    Returns:
        XML with corrected encoding declaration

    Examples:
        >>> fix_xml_declaration_encoding(
        ...     '<?xml version="1.0" encoding="iso-8859-1"?><root/>',
        ...     'utf-8'
        ... )
        '<?xml version="1.0" encoding="utf-8"?><root/>'

        >>> fix_xml_declaration_encoding('<root/>', 'utf-8')
        '<root/>'
    """
    # Find XML declaration
    match = re.match(r'(<\?xml[^>]+encoding\s*=\s*["\'])([^"\']+)(["\'][^>]*\?>)', xml_string)

    if match:
        # Replace encoding value
        new_declaration = f"{match.group(1)}{actual_encoding}{match.group(3)}"
        return new_declaration + xml_string[match.end() :]
    else:
        # No encoding declaration, return as-is
        return xml_string


def add_xml_declaration(xml_string: str, encoding: str = "utf-8", version: str = "1.0") -> str:
    """
    Add XML declaration if missing.

    Args:
        xml_string: XML string
        encoding: Encoding to declare
        version: XML version

    Returns:
        XML with declaration

    Examples:
        >>> add_xml_declaration('<root/>')
        '<?xml version="1.0" encoding="utf-8"?><root/>'
    """
    # Check if already has declaration
    if xml_string.strip().startswith("<?xml"):
        return xml_string

    declaration = f'<?xml version="{version}" encoding="{encoding}"?>\n'
    return declaration + xml_string


def normalize_line_endings(text: str, style: str = "unix") -> str:
    """
    Normalize line endings to consistent format.

    Args:
        text: Text with mixed line endings
        style: "unix" (\\n), "windows" (\\r\\n), or "mac" (\\r)

    Returns:
        Text with normalized line endings

    Examples:
        >>> normalize_line_endings('line1\\r\\nline2\\nline3\\r', 'unix')
        'line1\\nline2\\nline3\\n'
    """
    # First normalize all to \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Then convert to target style
    if style == "windows":
        return text.replace("\n", "\r\n")
    elif style == "mac":
        return text.replace("\n", "\r")
    else:  # unix
        return text
