"""
Custom exceptions for Xenon XML repair library.

This module provides a hierarchy of exceptions that make it easy to handle
different types of errors that can occur during XML repair operations.
"""

from typing import Optional, Tuple


class XenonException(Exception):  # noqa: N818
    """
    Base exception for all Xenon-related errors.

    All custom exceptions in Xenon inherit from this class, making it easy
    to catch all Xenon-specific errors with a single except clause.

    Attributes:
        line: Optional line number where the error occurred
        column: Optional column number where the error occurred
        context: Optional surrounding text for context
    """

    def __init__(
        self,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
        context: Optional[str] = None,
    ):
        """
        Initialize exception with enhanced error context.

        Args:
            message: Error message
            line: Line number where error occurred (1-indexed)
            column: Column number where error occurred (1-indexed)
            context: Surrounding text for context
        """
        self.line = line
        self.column = column
        self.context = context

        # Build enhanced message
        enhanced_message = message
        if line is not None:
            enhanced_message = f"{message} (line {line}"
            if column is not None:
                enhanced_message += f", column {column}"
            enhanced_message += ")"

        if context:
            enhanced_message += f"\n  Context: {context!r}"

        super().__init__(enhanced_message)


class ValidationError(XenonException):
    """
    Raised when input validation fails.

    This exception indicates that the input provided to a Xenon function
    is invalid (wrong type, empty when required, too large, etc.).

    Examples:
        - Passing None instead of a string
        - Passing an integer or list instead of a string
        - Passing an empty string when allow_empty=False
        - Input exceeds maximum size limit
    """

    pass


class MalformedXMLError(XenonException):
    """
    Raised when XML is too malformed to repair (strict mode only).

    This exception is only raised in strict mode when the repair process
    produces output that is still not valid XML.

    In default mode, Xenon will attempt to repair any XML and return
    the best-effort result without raising this exception.
    """

    pass


class RepairError(XenonException):
    """
    Raised when the repair process encounters an unrecoverable error.

    This indicates an internal error during the repair process that
    prevented completion. This may indicate a bug in Xenon.

    If you encounter this error, please report it with the input XML
    that caused it.
    """

    pass


class SecurityError(XenonException):
    """
    Raised when security limits are exceeded (v1.0.0).

    This exception indicates that the XML input has triggered security
    protections such as:
    - Maximum nesting depth exceeded (DoS prevention)
    - Entity expansion limit exceeded (billion laughs attack)
    - Other security circuit breakers

    The specific limit and recommended action will be in the error message.

    Examples:
        - XML nested deeper than max_depth for the trust level
        - Excessive entity expansion detected
        - Input size exceeds safety threshold
    """

    pass


def get_context_snippet(text: str, position: int, max_length: int = 50) -> str:
    """
    Extract a context snippet around a position in text.

    Args:
        text: The full text
        position: Character position (0-indexed)
        max_length: Maximum length of context snippet

    Returns:
        Context snippet with position marker

    Example:
        >>> get_context_snippet("Hello world test", 6, 20)
        'Hello world...'
    """
    if not text or position < 0 or position >= len(text):
        return ""

    # Get surrounding context
    start = max(0, position - max_length // 2)
    end = min(len(text), position + max_length // 2)
    snippet = text[start:end]

    # Add ellipsis if truncated
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return snippet.strip()


def get_line_column(text: str, position: int) -> Tuple[int, int]:
    """
    Convert character position to line and column numbers.

    Args:
        text: The full text
        position: Character position (0-indexed)

    Returns:
        Tuple of (line, column) both 1-indexed

    Example:
        >>> get_line_column("line1\\nline2\\nline3", 8)
        (2, 3)
    """
    if not text or position < 0:
        return (1, 1)

    # Count newlines before position
    lines_before = text[:position].count("\n")
    line = lines_before + 1

    # Find start of current line
    line_start = text.rfind("\n", 0, position) + 1
    column = position - line_start + 1

    return (line, column)


__all__ = [
    "MalformedXMLError",
    "RepairError",
    "SecurityError",
    "ValidationError",
    "XenonException",
    "get_context_snippet",
    "get_line_column",
]
