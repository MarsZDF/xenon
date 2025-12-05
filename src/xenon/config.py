"""Configuration classes for Xenon XML repair engine."""

from dataclasses import dataclass
from enum import Flag, auto
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .audit import AuditLogger, SecurityMetrics


class SecurityFlags(Flag):
    """Security feature flags."""

    NONE = 0
    STRIP_DANGEROUS_PIS = auto()
    STRIP_EXTERNAL_ENTITIES = auto()
    STRIP_DANGEROUS_TAGS = auto()
    ESCAPE_UNSAFE_ATTRIBUTES = auto()


class RepairFlags(Flag):
    """Repair feature flags."""

    NONE = 0
    WRAP_MULTIPLE_ROOTS = auto()
    SANITIZE_INVALID_TAGS = auto()
    FIX_NAMESPACE_SYNTAX = auto()
    AUTO_WRAP_CDATA = auto()


@dataclass
class XMLRepairConfig:
    """
    Configuration for XML repair engine.

    This provides a cleaner alternative to passing many boolean parameters.
    You can still use individual boolean parameters for backward compatibility.

    Examples:
        >>> # Using flags (recommended for multiple features)
        >>> config = XMLRepairConfig(
        ...     security=SecurityFlags.STRIP_DANGEROUS_PIS | SecurityFlags.STRIP_EXTERNAL_ENTITIES,
        ...     repair=RepairFlags.SANITIZE_INVALID_TAGS | RepairFlags.FIX_NAMESPACE_SYNTAX
        ... )

        >>> # Using individual booleans (backward compatible)
        >>> config = XMLRepairConfig.from_booleans(
        ...     strip_dangerous_pis=True,
        ...     sanitize_invalid_tags=True
        ... )
    """

    match_threshold: int = 2
    security: SecurityFlags = SecurityFlags.NONE
    repair: RepairFlags = RepairFlags.NONE
    schema_content: Optional[str] = None
    audit_logger: Optional["AuditLogger"] = None
    metrics: Optional["SecurityMetrics"] = None
    trust_level: Optional[str] = None

    @classmethod
    def from_booleans(
        cls,
        match_threshold: int = 2,
        strip_dangerous_pis: bool = False,
        strip_external_entities: bool = False,
        strip_dangerous_tags: bool = False,
        escape_unsafe_attributes: bool = False,
        wrap_multiple_roots: bool = False,
        sanitize_invalid_tags: bool = False,
        fix_namespace_syntax: bool = False,
        auto_wrap_cdata: bool = False,
        schema_content: Optional[str] = None,
        audit_logger: Optional["AuditLogger"] = None,
        trust_level: Optional[str] = None,
    ) -> "XMLRepairConfig":
        """
        Create config from individual boolean parameters.

        This provides backward compatibility with the old constructor signature.
        """
        security = SecurityFlags.NONE
        if strip_dangerous_pis:
            security |= SecurityFlags.STRIP_DANGEROUS_PIS
        if strip_external_entities:
            security |= SecurityFlags.STRIP_EXTERNAL_ENTITIES
        if strip_dangerous_tags:
            security |= SecurityFlags.STRIP_DANGEROUS_TAGS
        if escape_unsafe_attributes:
            security |= SecurityFlags.ESCAPE_UNSAFE_ATTRIBUTES

        repair = RepairFlags.NONE
        if wrap_multiple_roots:
            repair |= RepairFlags.WRAP_MULTIPLE_ROOTS
        if sanitize_invalid_tags:
            repair |= RepairFlags.SANITIZE_INVALID_TAGS
        if fix_namespace_syntax:
            repair |= RepairFlags.FIX_NAMESPACE_SYNTAX
        if auto_wrap_cdata:
            repair |= RepairFlags.AUTO_WRAP_CDATA

        return cls(
            match_threshold=match_threshold,
            security=security,
            repair=repair,
            schema_content=schema_content,
            audit_logger=audit_logger,
            trust_level=trust_level,
        )

    def has_security_feature(self, flag: SecurityFlags) -> bool:
        """Check if a security feature is enabled."""
        return bool(self.security & flag)

    def has_repair_feature(self, flag: RepairFlags) -> bool:
        """Check if a repair feature is enabled."""
        return bool(self.repair & flag)

    def has_any_feature(self) -> bool:
        """Check if any non-default features are enabled."""
        return self.security != SecurityFlags.NONE or self.repair != RepairFlags.NONE
