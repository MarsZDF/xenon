"""Repair reporting and diagnostics for Xenon XML repair engine."""

import difflib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


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
    before: str = ""  # Optional: what it looked like before
    after: str = ""  # Optional: what it looks like after

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
        after: str = "",
    ) -> None:
        """Add a repair action to the report."""
        self.actions.append(
            RepairAction(
                repair_type=repair_type,
                description=description,
                location=location,
                before=before,
                after=after,
            )
        )

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
            "statistics": self.statistics(),
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

    def to_unified_diff(self, context_lines: int = 3) -> str:
        """
        Generate unified diff format showing changes.

        Args:
            context_lines: Number of context lines to show around changes

        Returns:
            Unified diff string in standard format

        Example:
            >>> result, report = repair_xml_with_report('<root><item')
            >>> print(report.to_unified_diff())
            --- Original
            +++ Repaired
            @@ -1 +1 @@
            -<root><item
            +<root><item></item></root>
        """
        original_lines = self.original_xml.splitlines(keepends=True)
        repaired_lines = self.repaired_xml.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            repaired_lines,
            fromfile="Original",
            tofile="Repaired",
            lineterm="",
            n=context_lines,
        )

        return "\n".join(diff)

    def to_context_diff(self, context_lines: int = 3) -> str:
        """
        Generate context diff format showing changes.

        Args:
            context_lines: Number of context lines to show around changes

        Returns:
            Context diff string

        Example:
            >>> result, report = repair_xml_with_report('<root><item')
            >>> print(report.to_context_diff())
        """
        original_lines = self.original_xml.splitlines(keepends=True)
        repaired_lines = self.repaired_xml.splitlines(keepends=True)

        diff = difflib.context_diff(
            original_lines,
            repaired_lines,
            fromfile="Original",
            tofile="Repaired",
            lineterm="",
            n=context_lines,
        )

        return "\n".join(diff)

    def to_html_diff(self, table_style: bool = True) -> str:
        """
        Generate HTML diff with color-coded changes.

        Args:
            table_style: If True, use table format; if False, use inline format

        Returns:
            HTML string with visual diff

        Example:
            >>> result, report = repair_xml_with_report('<root><item')
            >>> html = report.to_html_diff()
            >>> with open('diff.html', 'w') as f:
            ...     f.write(html)
        """
        original_lines = self.original_xml.splitlines()
        repaired_lines = self.repaired_xml.splitlines()

        differ = difflib.HtmlDiff(tabsize=2, wrapcolumn=80)

        if table_style:
            html = differ.make_table(
                original_lines,
                repaired_lines,
                fromdesc="Original XML",
                todesc="Repaired XML",
                context=True,
                numlines=3,
            )
        else:
            html = differ.make_file(
                original_lines,
                repaired_lines,
                fromdesc="Original XML",
                todesc="Repaired XML",
                context=True,
                numlines=3,
            )

        return html

    def get_diff_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about the diff.

        Returns:
            Dictionary with diff statistics

        Example:
            >>> result, report = repair_xml_with_report(xml)
            >>> stats = report.get_diff_summary()
            >>> print(f"Lines added: {stats['lines_added']}")
        """
        original_lines = self.original_xml.splitlines()
        repaired_lines = self.repaired_xml.splitlines()

        matcher = difflib.SequenceMatcher(None, original_lines, repaired_lines)

        lines_added = 0
        lines_removed = 0
        lines_changed = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "insert":
                lines_added += j2 - j1
            elif tag == "delete":
                lines_removed += i2 - i1
            elif tag == "replace":
                lines_changed += max(i2 - i1, j2 - j1)

        return {
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "lines_changed": lines_changed,
            "similarity_ratio": matcher.ratio(),
            "original_lines": len(original_lines),
            "repaired_lines": len(repaired_lines),
        }
