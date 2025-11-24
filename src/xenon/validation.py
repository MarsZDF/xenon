"""
Input validation utilities for Xenon XML repair library.

This module provides functions to validate inputs before processing,
catching common errors early with helpful error messages.
"""

from typing import Any
from .exceptions import ValidationError


# Default maximum input size: 100MB
# This prevents DoS attacks with extremely large inputs
DEFAULT_MAX_SIZE = 100 * 1024 * 1024


def validate_xml_input(
    xml_input: Any,
    allow_empty: bool = False,
    max_size: int = DEFAULT_MAX_SIZE
) -> None:
    """
    Validate XML input before processing.

    Args:
        xml_input: The input to validate (should be a string)
        allow_empty: If True, accept empty strings. If False, raise ValidationError
        max_size: Maximum allowed input size in bytes. Set to None to disable

    Raises:
        ValidationError: If input is invalid

    Examples:
        >>> validate_xml_input('<root></root>')  # OK
        >>> validate_xml_input('')  # Raises ValidationError
        >>> validate_xml_input('', allow_empty=True)  # OK
        >>> validate_xml_input(None)  # Raises ValidationError
        >>> validate_xml_input(123)  # Raises ValidationError
    """
    # Type validation
    if not isinstance(xml_input, str):
        type_name = type(xml_input).__name__
        raise ValidationError(
            f"Expected string input, got {type_name}. "
            f"XML input must be a string, not {type_name}."
        )

    # Empty/whitespace validation
    if not xml_input.strip():
        if not allow_empty:
            raise ValidationError(
                "Input is empty or contains only whitespace. "
                "Provide valid XML content to repair, or use allow_empty=True."
            )

    # Size validation (if enabled)
    if max_size is not None and len(xml_input) > max_size:
        size_mb = len(xml_input) / (1024 * 1024)
        max_mb = max_size / (1024 * 1024)
        raise ValidationError(
            f"Input too large ({size_mb:.2f}MB). "
            f"Maximum allowed size is {max_mb:.2f}MB. "
            f"Use max_size parameter to increase limit if needed."
        )


def validate_repaired_output(
    repaired: str,
    original: str
) -> None:
    """
    Validate that repaired XML meets basic quality standards.

    This is used in strict mode to ensure the output has basic XML structure.
    Does NOT validate full XML spec compliance - just basic sanity checks.

    Args:
        repaired: The repaired XML string
        original: The original input (for context in error messages)

    Raises:
        ValidationError: If repaired output fails basic sanity checks

    Examples:
        >>> validate_repaired_output('<root></root>', '<root>')  # OK
        >>> validate_repaired_output('', '<root>')  # Raises
        >>> validate_repaired_output('plain text', '<root>')  # Raises
    """
    # Check output is not empty
    if not repaired.strip():
        raise ValidationError(
            "Repair produced empty output. "
            "Original input may not contain valid XML structure."
        )

    # Check for basic XML structure (at least one tag)
    if '<' not in repaired or '>' not in repaired:
        preview = repaired[:100] if len(repaired) > 100 else repaired
        raise ValidationError(
            f"Repair produced invalid output without XML tags: {repr(preview)}... "
            f"Original input may not be XML."
        )

    # Note: We intentionally don't validate full XML spec compliance here
    # because that would require xml.etree.ElementTree, adding a dependency
    # Users can optionally do their own validation with ET if needed
