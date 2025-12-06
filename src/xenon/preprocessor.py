"""XML preprocessing component for tag and namespace fixes."""

import re
from typing import Dict, List, Match, Tuple

from .config import RepairFlags, XMLRepairConfig
from .reporting import RepairAction, RepairType


class XMLPreprocessor:
    """
    Handles preprocessing of XML to fix invalid tag names and namespace syntax.

    This consolidates all preprocessing transformations into a single pass for efficiency.
    """

    def __init__(self, config: XMLRepairConfig):
        """
        Initialize preprocessor with configuration.

        Args:
            config: XMLRepairConfig instance
        """
        self.config = config
        self.tag_name_map: Dict[str, str] = {}  # Cache for sanitized names

    def preprocess(self, xml_string: str) -> Tuple[str, List["RepairAction"]]:
        """
        Apply all enabled preprocessing transformations in a single pass.

        This is more efficient than multiple regex passes.

        Args:
            xml_string: XML to preprocess

        Returns:
            Preprocessed XML string and a list of actions taken.
        """
        if not self._needs_preprocessing():
            return xml_string, []

        return self._single_pass_transform(xml_string)

    def _needs_preprocessing(self) -> bool:
        """Check if any preprocessing is needed."""
        return self.config.has_repair_feature(
            RepairFlags.SANITIZE_INVALID_TAGS
        ) or self.config.has_repair_feature(RepairFlags.FIX_NAMESPACE_SYNTAX)

    def _single_pass_transform(self, xml_string: str) -> Tuple[str, List["RepairAction"]]:
        """
        Single-pass transformation applying all enabled fixes.

        This is much more efficient than multiple regex passes.
        """
        actions: List[RepairAction] = []
        tag_pattern = r"<(/?)([^>]+?)(/?)>"

        def transform_tag(match: Match[str]) -> str:
            slash, inner_content, self_closing = match.groups()
            inner_content = inner_content.strip()

            # Skip special tags (comments, CDATA, DOCTYPE, PIs)
            if inner_content.startswith("!") or inner_content.startswith("?"):
                return match.group(0)

            # Extract tag name and attributes
            tag_name, rest = self._extract_tag_name(inner_content)
            original_name = tag_name
            current_name = tag_name

            # 1. Fix namespace syntax (if enabled)
            if self.config.has_repair_feature(RepairFlags.FIX_NAMESPACE_SYNTAX):
                fixed_ns_name = self._fix_namespace_syntax(current_name)
                if fixed_ns_name != current_name:
                    actions.append(
                        RepairAction(
                            repair_type=RepairType.INVALID_NAMESPACE,
                            description=f"Fixed invalid namespace syntax in tag '{current_name}'",
                            before=current_name,
                            after=fixed_ns_name,
                        )
                    )
                    current_name = fixed_ns_name

            # 2. Sanitize invalid tag names (if enabled)
            if self.config.has_repair_feature(RepairFlags.SANITIZE_INVALID_TAGS):
                sanitized_name = self._sanitize_tag_name(current_name)
                if sanitized_name != current_name:
                    actions.append(
                        RepairAction(
                            repair_type=RepairType.INVALID_TAG_NAME,
                            description=f"Sanitized invalid tag name '{current_name}'",
                            before=current_name,
                            after=sanitized_name,
                        )
                    )
                    current_name = sanitized_name

            # Rebuild tag if name was changed
            if current_name != original_name:
                if rest:
                    return f"<{slash}{current_name} {rest.lstrip()}{self_closing}>"
                else:
                    return f"<{slash}{current_name}{self_closing}>"

            return match.group(0)

        result = re.sub(tag_pattern, transform_tag, xml_string)
        return result, actions

    def _extract_tag_name(self, inner_content: str) -> Tuple[str, str]:
        """
        Extract tag name from tag content.

        Returns:
            (tag_name, rest_of_content)
        """
        equals_pos = inner_content.find("=")

        if equals_pos == -1:
            # No attributes, entire content is tag name
            return inner_content, ""
        else:
            # Has attributes, find where tag name ends
            space_pos = inner_content.find(" ")
            if space_pos != -1 and space_pos < equals_pos:
                tag_name = inner_content[:space_pos]
                rest = inner_content[space_pos:]
            else:
                tag_name = inner_content[:equals_pos].strip()
                rest = inner_content[equals_pos:]
            return tag_name, rest

    def _sanitize_tag_name(self, tag_name: str) -> str:
        """
        Sanitize invalid XML tag name to make it valid.

        Examples:
            <123> → <tag_123>
            <tag name> → <tag_name>
            <-invalid> → <tag_-invalid>
        """
        if not tag_name:
            return "tag"

        # Check cache
        if tag_name in self.tag_name_map:
            return self.tag_name_map[tag_name]

        original = tag_name

        # Replace spaces with underscores
        tag_name = tag_name.replace(" ", "_")

        # Remove invalid characters (keep only alphanumeric, _, -, ., :)
        tag_name = re.sub(r"[^a-zA-Z0-9_\-.:]+", "", tag_name)

        # Ensure starts with valid character (letter, _, or :)
        if tag_name and not (tag_name[0].isalpha() or tag_name[0] in "_:"):
            tag_name = "tag_" + tag_name

        # Fallback if empty after cleaning
        if not tag_name:
            tag_name = "tag"

        # Cache the result
        self.tag_name_map[original] = tag_name

        return tag_name

    def _is_valid_tag_name(self, tag_name: str) -> bool:
        """Check if tag name is valid per XML spec."""
        if not tag_name:
            return False

        # Must start with letter, underscore, or colon
        if not (tag_name[0].isalpha() or tag_name[0] in "_:"):
            return False

        # Check remaining characters
        return bool(re.match(r"^[a-zA-Z_:][\w\-.:]*$", tag_name))

    def _fix_namespace_syntax(self, tag_name: str) -> str:
        """
        Fix invalid namespace syntax in a tag name.

        Valid: prefix:localname (exactly one colon)
        Invalid patterns fixed:
        - bad::ns → bad_ns
        - :tag → c_tag
        - tag: → tag
        - ns1:ns2:tag → ns1:ns2_tag
        """
        if ":" not in tag_name:
            return tag_name

        colon_count = tag_name.count(":")

        # Single colon - check for edge cases
        if colon_count == 1:
            if tag_name.startswith(":"):
                return "c_" + tag_name[1:] if len(tag_name) > 1 else "tag"
            elif tag_name.endswith(":"):
                return tag_name[:-1]
            else:
                # Valid namespace syntax
                parts = tag_name.split(":")
                if len(parts) == 2 and parts[0] and parts[1]:
                    return tag_name
                elif not parts[0]:
                    return "c_" + parts[1]
                elif not parts[1]:
                    return parts[0]

        # Multiple colons - filter empty parts and rebuild
        parts = [p for p in tag_name.split(":") if p]

        if len(parts) == 0:
            return "tag"
        elif len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            # Had issues (consecutive colons, edge cases)
            if "::" in tag_name or tag_name.startswith(":") or tag_name.endswith(":"):
                return "_".join(parts)
            return tag_name
        else:
            # More than 2 parts: keep first colon, join rest with underscore
            return parts[0] + ":" + "_".join(parts[1:])

    def is_cdata_candidate(self, tag_name: str) -> bool:
        """
        Check if tag is a candidate for CDATA wrapping.

        Args:
            tag_name: The tag name to check

        Returns:
            True if tag commonly contains code or special characters
        """
        cdata_tags = {
            "code",
            "script",
            "pre",
            "source",
            "sql",
            "query",
            "formula",
            "expression",
            "xpath",
            "regex",
        }
        return tag_name.lower() in cdata_tags

    def needs_cdata_wrapping(self, text: str) -> bool:
        """Check if text content contains characters that need CDATA wrapping."""
        special_chars = {"<", ">", "&"}
        return any(char in text for char in special_chars)

    def wrap_cdata(self, text: str) -> str:
        """
        Wrap text in CDATA section with security fix for ]]> breakout.

        SECURITY: Escape ]]> to prevent CDATA injection attacks.
        """
        # Escape ]]> to prevent CDATA breakout
        safe_text = text.replace("]]>", "]]]]><![CDATA[>")
        return f"<![CDATA[{safe_text}]]>"
