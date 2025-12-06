"""Security filtering component for Xenon XML repair engine."""

import re
from typing import ClassVar, List, Optional

from .config import SecurityFlags, XMLRepairConfig


class XMLSecurityFilter:
    """
    Handles security features like stripping dangerous content.

    Separates security concerns from core repair logic.
    """

    # Patterns for dangerous processing instructions
    DANGEROUS_PI_PATTERNS: ClassVar[List[str]] = [
        "php",
        "asp",
        "jsp",
        "ruby",
        "python",
        "perl",
        "exec",
    ]

    # Dangerous tags for XSS prevention
    DANGEROUS_TAGS: ClassVar[List[str]] = [
        "script",
        "iframe",
        "object",
        "embed",
        "applet",
        "meta",
        "link",
        "style",
    ]

    def __init__(self, config: XMLRepairConfig):
        """
        Initialize security filter with configuration.

        Args:
            config: XMLRepairConfig instance
        """
        self.config = config

    def is_dangerous_pi(self, pi_content: str) -> bool:
        """
        Check if processing instruction contains dangerous code patterns.

        This method ALWAYS checks if content is dangerous, regardless of whether
        the STRIP_DANGEROUS_PIS flag is enabled. The flag controls whether we
        ACT on dangerous content, not whether we CHECK for it.

        Args:
            pi_content: The PI content (e.g., "<?php echo 'hi'; ?>")

        Returns:
            True if PI looks like executable code
        """
        pi_lower = pi_content.lower()
        return any(f"<?{pattern}" in pi_lower for pattern in self.DANGEROUS_PI_PATTERNS)

    def is_dangerous_tag(self, tag_name: str) -> bool:
        """
        Check if tag name is potentially dangerous for XSS.

        This method ALWAYS checks if content is dangerous, regardless of whether
        the STRIP_DANGEROUS_TAGS flag is enabled.

        Args:
            tag_name: The tag name to check

        Returns:
            True if tag is in dangerous list
        """
        tag_lower = tag_name.lower().split()[0] if tag_name else ""
        return tag_lower in self.DANGEROUS_TAGS

    def contains_external_entity(self, doctype: str) -> bool:
        """
        Check if DOCTYPE contains external entity declarations.

        This method ALWAYS checks if content is dangerous, regardless of whether
        the STRIP_EXTERNAL_ENTITIES flag is enabled.

        Args:
            doctype: The DOCTYPE content

        Returns:
            True if external entities are present
        """
        doctype_upper = doctype.upper()
        return "SYSTEM" in doctype_upper or "PUBLIC" in doctype_upper

    def should_strip_dangerous_pi(self, pi_content: str) -> bool:
        """
        Check if we should strip this PI (combines check + flag).

        Args:
            pi_content: The PI content

        Returns:
            True if we should strip it
        """
        return self.config.has_security_feature(
            SecurityFlags.STRIP_DANGEROUS_PIS
        ) and self.is_dangerous_pi(pi_content)

    def should_strip_dangerous_tag(self, tag_name: str) -> bool:
        """
        Check if we should strip this tag (combines check + flag).

        Args:
            tag_name: The tag name

        Returns:
            True if we should strip it
        """
        return self.config.has_security_feature(
            SecurityFlags.STRIP_DANGEROUS_TAGS
        ) and self.is_dangerous_tag(tag_name)

    def strip_external_entities_from_text(self, text: str) -> str:
        """
        Strip DOCTYPE declarations from text if security feature enabled.

        Args:
            text: Text potentially containing DOCTYPE

        Returns:
            Text with DOCTYPE declarations removed (if enabled)
        """
        if not self.config.has_security_feature(SecurityFlags.STRIP_EXTERNAL_ENTITIES):
            return text

        # Remove DOCTYPE declarations (may contain external entities)
        return re.sub(r"<!DOCTYPE(?:[^>\[]|\[.*?\])*>", "", text, flags=re.DOTALL | re.IGNORECASE)


def check_max_depth(current_depth: int, max_depth: Optional[int]) -> None:
    """
    Check if current nesting depth exceeds max_depth limit.

    Args:
        current_depth: Current depth level
        max_depth: Maximum allowed depth (None = unlimited)

    Raises:
        SecurityError: If depth exceeds max_depth
    """
    if max_depth is not None and current_depth > max_depth:
        from .exceptions import SecurityError

        raise SecurityError(
            f"Maximum nesting depth {max_depth} exceeded. "
            f"Current depth: {current_depth}. "
            f"This may indicate a DoS attack via malicious input, "
            f"runaway LLM generation, or legitimate deep nesting. "
            f"Override with max_depth={current_depth + 1000} if this is expected."
        )
