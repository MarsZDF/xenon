"""Repair reporting and diagnostics for Xenon XML repair engine."""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum


class RepairType(Enum):
    """Types of repairs performed."""
    TRUNCATION = "truncation"
    CONVERSATIONAL_FLUFF = "conversational_fluff"
    MALFORMED_ATTRIBUTE = "malformed_attribute"
    UNESCAPED_ENTITY = "unescaped_entity"
    CDATA_WRAPPED = "cdata_wrapped"
    TAG_TYPO = "tag_typo"
    TAG_CASE_MISMATCH = "tag_case_mismatch"
    NAMESPACE_INJECTED = "namespace_injected"
    DUPLICATE_ATTRIBUTE = "duplicate_attribute"
    INVALID_TAG_NAME = "invalid_tag_name"
    INVALID_NAMESPACE = "invalid_namespace"
    MULTIPLE_ROOTS = "multiple_roots"
    DANGEROUS_PI_STRIPPED = "dangerous_pi_stripped"
    DANGEROUS_TAG_STRIPPED = "dangerous_tag_stripped"
    EXTERNAL_ENTITY_STRIPPED = "external_entity_stripped"


@dataclass
class RepairAction:
    """Represents a single repair action taken."""

    repair_type: RepairType
    description: str
    location: str = ""  # Optional location info (line number, tag name, etc.)
    before: str = ""    # Optional: what it looked like before
    after: str = ""     # Optional: what it looks like after

    def __str__(self) -> str:
        """Human-readable representation."""
        parts = [f"[{self.repair_type.value}] {self.description}"]
        if self.location:
            parts.append(f"at {self.location}")
        if self.before:
            parts.append(f"'{self.before}' → '{self.after}'")
        return " ".join(parts)


@dataclass
class RepairReport:
    """
    Comprehensive report of all repairs performed on XML.

    This provides full transparency into what Xenon fixed, making it easier
    to debug issues and understand LLM failure modes.

    Example:
        >>> from xenon import repair_xml_with_report
        >>> result, report = repair_xml_with_report('<root><item')
        >>> print(report.summary())
        Performed 1 repair:
        - Added closing tags for truncation
        >>> print(report.actions[0])
        [truncation] Added closing tags: </item></root>
    """

    original_xml: str
    repaired_xml: str
    actions: List[RepairAction] = field(default_factory=list)

    def add_action(
        self,
        repair_type: RepairType,
        description: str,
        location: str = "",
        before: str = "",
        after: str = ""
    ) -> None:
        """Add a repair action to the report."""
        self.actions.append(RepairAction(
            repair_type=repair_type,
            description=description,
            location=location,
            before=before,
            after=after
        ))

    def summary(self) -> str:
        """Get a human-readable summary of all repairs."""
        if not self.actions:
            return "No repairs needed - XML was already well-formed."

        lines = [f"Performed {len(self.actions)} repair(s):"]
        for action in self.actions:
            lines.append(f"  - {action}")
        return "\n".join(lines)

    def by_type(self) -> Dict[RepairType, List[RepairAction]]:
        """Group actions by repair type."""
        grouped: Dict[RepairType, List[RepairAction]] = {}
        for action in self.actions:
            if action.repair_type not in grouped:
                grouped[action.repair_type] = []
            grouped[action.repair_type].append(action)
        return grouped

    def statistics(self) -> Dict[str, int]:
        """Get statistics about repairs performed."""
        stats = {
            "total_repairs": len(self.actions),
            "input_size": len(self.original_xml),
            "output_size": len(self.repaired_xml),
        }

        # Count by type
        for repair_type in RepairType:
            count = sum(1 for a in self.actions if a.repair_type == repair_type)
            if count > 0:
                stats[f"{repair_type.value}_count"] = count

        return stats

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "original_length": len(self.original_xml),
            "repaired_length": len(self.repaired_xml),
            "repair_count": len(self.actions),
            "actions": [
                {
                    "type": action.repair_type.value,
                    "description": action.description,
                    "location": action.location,
                    "before": action.before,
                    "after": action.after,
                }
                for action in self.actions
            ],
            "statistics": self.statistics()
        }

    def has_security_issues(self) -> bool:
        """Check if any security-related repairs were performed."""
        security_types = {
            RepairType.DANGEROUS_PI_STRIPPED,
            RepairType.DANGEROUS_TAG_STRIPPED,
            RepairType.EXTERNAL_ENTITY_STRIPPED,
        }
        return any(a.repair_type in security_types for a in self.actions)

    def __bool__(self) -> bool:
        """Report is truthy if any repairs were performed."""
        return len(self.actions) > 0

    def __len__(self) -> int:
        """Number of repairs performed."""
        return len(self.actions)
