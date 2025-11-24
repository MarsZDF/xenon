"""
Custom exceptions for Xenon XML repair library.

This module provides a hierarchy of exceptions that make it easy to handle
different types of errors that can occur during XML repair operations.
"""


class XenonException(Exception):
    """
    Base exception for all Xenon-related errors.

    All custom exceptions in Xenon inherit from this class, making it easy
    to catch all Xenon-specific errors with a single except clause.
    """
    pass


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
