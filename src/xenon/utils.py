"""Utility functions for Xenon XML repair library."""

import re
from typing import TYPE_CHECKING, Any, Callable, Iterator, List, Optional, Tuple

from .encoding import detect_encoding
from .reporting import RepairReport

if TYPE_CHECKING:
    from .trust import TrustLevel


def decode_xml(xml_bytes: bytes, encoding: Optional[str] = None) -> str:
    """
    Decode XML bytes to string, auto-detecting encoding if not specified.

    Args:
        xml_bytes: Raw XML bytes
        encoding: Optional encoding (auto-detected if None)

    Returns:
        Decoded XML string

    Example:
        >>> xml_bytes = b'<?xml version="1.0"?><root>data</root>'
        >>> decode_xml(xml_bytes)
        '<?xml version="1.0"?><root>data</root>'
    """
    if encoding is None:
        detected_encoding, _confidence = detect_encoding(xml_bytes)
        encoding = detected_encoding

    try:
        return xml_bytes.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        # Fallback to UTF-8 with error replacement
        return xml_bytes.decode("utf-8", errors="replace")


def batch_repair(
    xml_strings: List[str],
    *,
    show_progress: bool = False,
    on_error: str = "skip",
    **repair_kwargs: Any,
) -> List[Tuple[str, Optional[Exception]]]:
    """
    Repair multiple XML strings in batch with error handling.

    Args:
        xml_strings: List of XML strings to repair
        show_progress: Show progress indicator (default: False)
        on_error: What to do on error - 'skip', 'raise', or 'return_empty'
                  (default: 'skip')
        **repair_kwargs: Additional arguments passed to repair_xml_safe()

    Returns:
        List of (repaired_xml, error) tuples. Error is None on success.

    Example:
        >>> xml_batch = ['<root>valid</root>', '<root>invalid', '<bad><xml']
        >>> results = batch_repair(xml_batch)
        >>> for xml, error in results:
        ...     if error:
        ...         print(f"Failed: {error}")
        ...     else:
        ...         print(f"Success: {xml}")
    """
    from . import repair_xml_safe
    from .exceptions import XenonException

    results: List[Tuple[str, Optional[Exception]]] = []
    total = len(xml_strings)

    for i, xml_string in enumerate(xml_strings):
        if show_progress and i % 100 == 0:
            print(f"Processing {i}/{total}...", end="\r")

        try:
            repaired = repair_xml_safe(xml_string, **repair_kwargs)
            results.append((repaired, None))
        except XenonException as e:
            if on_error == "raise":
                raise
            elif on_error == "return_empty":
                results.append(("", e))
            else:  # skip
                results.append((xml_string, e))

    if show_progress:
        print(f"Completed {total}/{total}")

    return results


def batch_repair_with_reports(
    xml_strings: List[str],
    trust: "TrustLevel",
    *,
    show_progress: bool = False,
    filter_func: Optional[Callable[[RepairReport], bool]] = None,
) -> List[Tuple[str, RepairReport]]:
    """
    Repair multiple XML strings and get detailed reports.

    Args:
        xml_strings: List of XML strings to repair
        trust: Trust level of input sources
        show_progress: Show progress indicator (default: False)
        filter_func: Optional function to filter which results to return
                     based on the report (e.g., only return if repairs were made)

    Returns:
        List of (repaired_xml, report) tuples

    Example:
        >>> from xenon import TrustLevel
        >>> xml_batch = ['<root>test', '<item>data</item>']
        >>> results = batch_repair_with_reports(xml_batch, trust=TrustLevel.TRUSTED)
        >>> # Only get results where repairs were made
        >>> results_with_fixes = batch_repair_with_reports(
        ...     xml_batch,
        ...     trust=TrustLevel.TRUSTED,
        ...     filter_func=lambda r: len(r) > 0
        ... )
    """
    from . import repair_xml_with_report

    results = []
    total = len(xml_strings)

    for i, xml_string in enumerate(xml_strings):
        if show_progress and i % 100 == 0:
            print(f"Processing {i}/{total}...", end="\r")

        repaired, report = repair_xml_with_report(xml_string, trust=trust)

        if filter_func is None or filter_func(report):
            results.append((repaired, report))

    if show_progress:
        print(f"Completed {total}/{total}")

    return results


def stream_repair(
    xml_iterator: Iterator[str], **repair_kwargs: Any
) -> Iterator[Tuple[str, Optional[Exception]]]:
    """
    Repair XML strings from an iterator (for streaming/large datasets).

    Args:
        xml_iterator: Iterator yielding XML strings
        **repair_kwargs: Additional arguments passed to repair_xml_safe()

    Yields:
        (repaired_xml, error) tuples. Error is None on success.

    Example:
        >>> def xml_generator():
        ...     yield '<root>item1</root>'
        ...     yield '<root>item2'
        ...     yield '<root>item3</root>'
        >>> for repaired, error in stream_repair(xml_generator()):
        ...     if not error:
        ...         print(repaired)
    """
    from . import repair_xml_safe
    from .exceptions import XenonException

    for xml_string in xml_iterator:
        try:
            repaired = repair_xml_safe(xml_string, **repair_kwargs)
            yield (repaired, None)
        except XenonException as e:
            yield (xml_string, e)


def validate_xml_structure(xml_string: str) -> Tuple[bool, List[str]]:
    """
    Validate XML structure and return detailed issues.

    This is a lightweight validation that checks for common structural issues
    without full XML parsing.

    Args:
        xml_string: XML string to validate

    Returns:
        (is_valid, issues) tuple where issues is a list of problem descriptions

    Example:
        >>> xml = '<root><item>unclosed'
        >>> is_valid, issues = validate_xml_structure(xml)
        >>> print(is_valid)
        False
        >>> print(issues)
        ['Missing closing tag for: item', 'Missing closing tag for: root']
    """
    issues = []

    # Check for obvious structural problems
    if not xml_string.strip():
        issues.append("Empty XML string")
        return False, issues

    if "<" not in xml_string or ">" not in xml_string:
        issues.append("No XML tags found")
        return False, issues

    # Simple tag balance check
    open_tags = re.findall(r"<([a-zA-Z_:][\w\-.:]*)", xml_string)
    close_tags = re.findall(r"</([a-zA-Z_:][\w\-.:]*)", xml_string)

    # Filter out self-closing tags and special tags
    open_tags = [t for t in open_tags if not xml_string.count(f"<{t}/>")]

    if len(open_tags) > len(close_tags):
        issues.append(f"More opening tags ({len(open_tags)}) than closing tags ({len(close_tags)})")

    if len(close_tags) > len(open_tags):
        issues.append(f"More closing tags ({len(close_tags)}) than opening tags ({len(open_tags)})")

    # Check for unescaped entities
    # Simple check for & not followed by entity pattern
    unescaped = re.findall(r"&(?![a-zA-Z]+;|#\d+;|#x[0-9a-fA-F]+;)", xml_string)
    if unescaped:
        issues.append(f"Found {len(unescaped)} unescaped ampersands")

    # Check for unquoted attributes (simple heuristic)
    unquoted = re.findall(r'\s+\w+=[^"\'\s>][^\s>]*', xml_string)
    if unquoted:
        issues.append(f"Found {len(unquoted)} potentially unquoted attributes")

    is_valid = len(issues) == 0
    return is_valid, issues


def extract_text_content(xml_string: str) -> str:
    """
    Extract all text content from XML, removing tags.

    This is a simple text extraction - not a full parser.

    Args:
        xml_string: XML string

    Returns:
        Plain text content with tags removed

    Example:
        >>> xml = '<root><item>Hello</item><item>World</item></root>'
        >>> extract_text_content(xml)
        'HelloWorld'
    """
    # Remove CDATA sections but keep their content
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", xml_string, flags=re.DOTALL)

    # Remove comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Remove processing instructions
    text = re.sub(r"<\?.*?\?>", "", text, flags=re.DOTALL)

    # Remove DOCTYPE
    text = re.sub(r"<!DOCTYPE.*?>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove all tags
    text = re.sub(r"<[^>]+>", "", text)

    return text
