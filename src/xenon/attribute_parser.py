"""
Attribute parsing and repair utilities.

Handles extraction and repair of XML attributes, including fixing unquoted values,
escaping special characters, and handling duplicates.
"""

import re
from typing import List, Match, Set, Tuple

from .reporting import RepairAction, RepairType


def escape_attribute_value(
    value: str, quote_char: str = '"', aggressive_escape: bool = False
) -> str:
    """
    Escape special characters in attribute values.

    Escapes &, <, >, and the quote character used to delimit the attribute.
    Avoids double-escaping already valid entity references.

    Args:
        value: Attribute value to escape
        quote_char: Quote character surrounding the attribute (' or ")
        aggressive_escape: If True, aggressively escape dangerous characters (XSS prevention)

    Returns:
        Escaped attribute value
    """
    # Pattern to match valid entity references
    valid_entity_pattern = r"&(?:lt|gt|amp|quot|apos|#\d+|#x[0-9a-fA-F]+);"

    # Find all valid entities and temporarily replace them with placeholders
    entities = []

    def save_entity(match: Match[str]) -> str:
        entities.append(match.group(0))
        return f"\x00ENTITY{len(entities) - 1}\x00"

    value = re.sub(valid_entity_pattern, save_entity, value)

    # Escape special characters
    value = value.replace("&", "&amp;")
    value = value.replace("<", "&lt;")
    value = value.replace(">", "&gt;")

    if aggressive_escape:
        value = value.replace("'", "&apos;")
        value = value.replace('"', "&quot;")
        value = value.replace("/", "&#x2F;")
        value = value.replace(" ", "&#x20;")
        value = value.replace("\t", "&#x09;")
        value = value.replace("\n", "&#x0A;")
        value = value.replace("\r", "&#x0D;")
    else:
        # Escape the quote character being used
        value = value.replace('"', "&quot;") if quote_char == '"' else value.replace("'", "&apos;")

    # Restore the valid entities
    for i, entity in enumerate(entities):
        value = value.replace(f"\x00ENTITY{i}\x00", entity)

    return value


# Pre-compiled regex for attribute parsing
# Matches: name = "value" OR name = 'value' OR name = value
ATTR_PATTERN = re.compile(
    r"""
    \s+                         # Required whitespace before attribute
    (?P<name>[a-zA-Z_:][\w:.-]*) # Attribute name
    \s*=\s*                     # Equals sign with optional whitespace
    (?P<value>
        "(?P<v_double>[^"]*)"|  # Double-quoted value
        '(?P<v_single>[^']*)'|  # Single-quoted value
        (?P<v_unquoted>[^\s=]+) # Unquoted value
    )
    """,
    re.VERBOSE,
)


def fix_malformed_attributes(
    tag_content: str, aggressive_escape: bool = False
) -> Tuple[str, List[RepairAction]]:
    """
    Parse and fix malformed attributes in a tag.

    Handles:
    - Unquoted attribute values (key=value)
    - Missing quotes
    - Duplicate attributes
    - Escaping special characters in values

    Args:
        tag_content: Content inside the tag (e.g., "tag attr=val")
        aggressive_escape: Whether to use aggressive escaping for XSS protection

    Returns:
        Tuple of (repaired_content, list of repair actions)
    """
    content = tag_content.strip()

    # Fast path: no equals sign means no attributes (or boolean attributes which we ignore/preserve as text)
    if "=" not in content:
        return content, []

    # Extract tag name first (everything before the first space)
    # Manual scan is faster than regex or split for just finding first space
    n = len(content)
    i = 0
    while i < n and not content[i].isspace():
        i += 1

    tag_name = content[:i]

    # If we reached end, no attributes
    if i == n:
        return content, []

    return _fix_attributes_manual(content, tag_name, i, aggressive_escape)


def _fix_attributes_manual(
    content: str, tag_name: str, start_pos: int, aggressive_escape: bool
) -> Tuple[str, List[RepairAction]]:
    actions: List[RepairAction] = []
    result = [tag_name]
    seen_attrs: Set[str] = set()
    n = len(content)
    i = start_pos

    while i < n:
        # Skip whitespace
        while i < n and content[i].isspace():
            i += 1

        if i >= n:
            break

        attr_start = i

        # Find attribute name (fast scan until space or =)
        while i < n and content[i] not in " =":
            i += 1

        if i >= n or content[i] != "=":
            # Not a key=value, check if we stopped at space before =
            if i < n and content[i].isspace():
                # Look ahead for =
                j = i
                while j < n and content[j].isspace():
                    j += 1
                if j < n and content[j] == "=":
                    # It is an attribute: attr = val
                    attr_name = content[attr_start:i]
                    i = j + 1  # Skip =
                else:
                    # Boolean attribute or garbage, just copy
                    result.append(" ")
                    result.append(content[attr_start:i])
                    # If we stopped at i, continue from there
                    continue
            else:
                # Garbage or boolean at end
                result.append(" ")
                result.append(content[attr_start:])
                break
        else:
            # Found =
            attr_name = content[attr_start:i]
            i += 1

        attr_name_lower = attr_name.lower()

        # Duplicate check
        if attr_name_lower in seen_attrs:
            actions.append(
                RepairAction(
                    RepairType.DUPLICATE_ATTRIBUTE,
                    f"Removed duplicate attribute '{attr_name_lower}'",
                    location=tag_name,
                )
            )
            # Skip value
            if i < n and content[i] in "\"'":
                q = content[i]
                i += 1
                while i < n and content[i] != q:
                    i += 1
                if i < n:
                    i += 1
            else:
                # Unquoted value, skip until space
                while i < n and not content[i].isspace():
                    i += 1
            continue

        seen_attrs.add(attr_name_lower)

        # Skip whitespace before value
        while i < n and content[i].isspace():
            i += 1

        # Handle value
        # Check for quoted value
        if i < n and content[i] in "\"'":
            q = content[i]
            val_start = i + 1
            val_end = content.find(q, val_start)

            if val_end == -1:
                # Unclosed quote
                val = content[val_start:]
                i = n
            else:
                val = content[val_start:val_end]
                i = val_end + 1

            escaped = escape_attribute_value(val, q, aggressive_escape)
            result.append(f" {attr_name}={q}{escaped}{q}")
        else:
            # Unquoted or empty
            # Check if empty (next char is space or end)
            if i >= n or content[i].isspace():
                # Empty value: attr=
                result.append(f' {attr_name}=""')
                continue

            val_start = i
            # Find end of unquoted value (space)
            while i < n and not content[i].isspace():
                i += 1
            val = content[val_start:i]

            escaped = escape_attribute_value(val, '"', aggressive_escape)
            actions.append(
                RepairAction(
                    RepairType.MALFORMED_ATTRIBUTE,
                    f"Added quotes to unquoted attribute '{attr_name}'",
                    location=tag_name,
                    before=f"{attr_name}={val}",
                    after=f'{attr_name}="{escaped}"',
                )
            )
            result.append(f' {attr_name}="{escaped}"')

    return "".join(result), actions
