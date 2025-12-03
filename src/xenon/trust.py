"""
Trust levels for secure-by-default XML repair.

This module defines trust levels that determine security features applied
during XML repair. Trust levels make security decisions explicit and help
prevent accidental exposure to injection attacks.
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from xenon.audit import AuditLogger, SecurityMetrics


class TrustLevel(Enum):
    """
    Trust level of XML input source.

    Trust levels automatically configure security features appropriate for
    the source. Making trust explicit forces security thinking at point of use.

    Examples:
        >>> from xenon import repair_xml
        >>> from xenon.trust import TrustLevel
        >>>
        >>> # LLM output - maximum security
        >>> repair_xml(llm_response, trust=TrustLevel.UNTRUSTED)
        >>>
        >>> # Internal service - balanced security
        >>> repair_xml(service_xml, trust=TrustLevel.INTERNAL)
        >>>
        >>> # Test fixture - no overhead
        >>> repair_xml(TEST_XML, trust=TrustLevel.TRUSTED)
    """

    UNTRUSTED = "untrusted"
    """
    Use for: LLM output, user uploads, external APIs, any untrusted source.

    Security features:
        - Strip dangerous processing instructions (PHP, ASP, JSP): YES
        - Strip external entity declarations (XXE prevention): YES
        - Strip dangerous tags (script, iframe, etc.): YES
        - Max nesting depth: 1000 (DoS prevention)
        - Validate output structure: YES
        - Performance impact: ~15-20% slower than TRUSTED

    When to use:
        - Any XML from outside your control
        - LLM-generated content
        - User file uploads
        - Third-party API responses
        - Web scraping results
    """

    INTERNAL = "internal"
    """
    Use for: Internal services, trusted microservices, configuration files.

    Security features:
        - Strip dangerous processing instructions: NO
        - Strip external entity declarations: YES (defense in depth)
        - Strip dangerous tags: NO
        - Max nesting depth: 10000
        - Validate output structure: NO
        - Performance impact: ~5% slower than TRUSTED

    When to use:
        - XML from internal services you control
        - Configuration files you wrote
        - Database exports from your systems
        - Inter-service communication
    """

    TRUSTED = "trusted"
    """
    Use for: Hardcoded literals, test fixtures, known-good data.

    Security features:
        - All security checks: DISABLED
        - Max nesting depth: None (unlimited)
        - Validate output structure: NO
        - Performance impact: Baseline (fastest)

    When to use:
        - String literals in code
        - Test fixtures
        - Generated XML you just created
        - XML from previous xenon repair

    WARNING: Never use TRUSTED for external input, even if you "trust" the source.
    """


@dataclass
class SecurityConfig:
    """
    Security configuration derived from trust level.

    This is generated automatically based on TrustLevel and should not
    be constructed directly in most cases.
    """

    trust_level: TrustLevel
    strip_dangerous_pis: bool
    strip_external_entities: bool
    strip_dangerous_tags: bool
    max_depth: Optional[int]
    strict: bool
    audit_threats: bool
    audit_logger: Optional["AuditLogger"] = None
    metrics: Optional["SecurityMetrics"] = None

    def __str__(self) -> str:
        """Human-readable security configuration."""
        return (
            f"SecurityConfig(trust={self.trust_level.value}, "
            f"strip_pis={self.strip_dangerous_pis}, "
            f"strip_entities={self.strip_external_entities}, "
            f"strip_tags={self.strip_dangerous_tags}, "
            f"max_depth={self.max_depth}, "
            f"strict={self.strict}, "
            f"audit={self.audit_threats})"
        )


def get_security_config(
    trust: TrustLevel,
    # Allow overrides
    strip_dangerous_pis: Optional[bool] = None,
    strip_external_entities: Optional[bool] = None,
    strip_dangerous_tags: Optional[bool] = None,
    max_depth: Optional[int] = None,
    strict: Optional[bool] = None,
    audit_threats: Optional[bool] = None,
) -> SecurityConfig:
    """
    Get security configuration for a trust level.

    Args:
        trust: Trust level of the input
        strip_dangerous_pis: Override default for processing instructions
        strip_external_entities: Override default for external entities
        strip_dangerous_tags: Override default for dangerous tags
        max_depth: Override default max nesting depth
        strict: Override default strict validation
        audit_threats: Override default threat auditing

    Returns:
        SecurityConfig with appropriate settings

    Examples:
        >>> # Use defaults for trust level
        >>> config = get_security_config(TrustLevel.UNTRUSTED)
        >>> config.max_depth
        1000

        >>> # Override specific setting
        >>> config = get_security_config(
        ...     TrustLevel.UNTRUSTED,
        ...     max_depth=5000
        ... )
        >>> config.max_depth
        5000
    """
    # Trust level defaults
    if trust == TrustLevel.UNTRUSTED:
        defaults = SecurityConfig(
            trust_level=trust,
            strip_dangerous_pis=True,
            strip_external_entities=True,
            strip_dangerous_tags=True,
            max_depth=1000,
            strict=True,
            audit_threats=True,
        )
    elif trust == TrustLevel.INTERNAL:
        defaults = SecurityConfig(
            trust_level=trust,
            strip_dangerous_pis=False,
            strip_external_entities=True,  # Defense in depth
            strip_dangerous_tags=False,
            max_depth=10000,
            strict=False,
            audit_threats=False,
        )
    else:  # TRUSTED
        defaults = SecurityConfig(
            trust_level=trust,
            strip_dangerous_pis=False,
            strip_external_entities=False,
            strip_dangerous_tags=False,
            max_depth=None,
            strict=False,
            audit_threats=False,
        )

    # Apply overrides
    if strip_dangerous_pis is not None:
        defaults.strip_dangerous_pis = strip_dangerous_pis
    if strip_external_entities is not None:
        defaults.strip_external_entities = strip_external_entities
    if strip_dangerous_tags is not None:
        defaults.strip_dangerous_tags = strip_dangerous_tags
    if max_depth is not None:
        defaults.max_depth = max_depth
    if strict is not None:
        defaults.strict = strict
    if audit_threats is not None:
        defaults.audit_threats = audit_threats

    return defaults


__all__ = ["TrustLevel", "SecurityConfig", "get_security_config"]
