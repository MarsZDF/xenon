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
        if quote_char == '"':
            value = value.replace('"', "&quot;")
        else:  # single quote
            value = value.replace("'", "&apos;")

    # Restore the valid entities
    for i, entity in enumerate(entities):
        value = value.replace(f"\x00ENTITY{i}\x00", entity)

    return value


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
    actions: List[RepairAction] = []
    content = tag_content.strip()

    # Extract tag name first (everything before the first = or first space followed by word=)
    tag_name = ""
    attr_start_pos = 0
    i = 0

    # Read the tag name (first word)
    while i < len(content) and not content[i].isspace():
        i += 1

    if i < len(content):
        tag_name = content[:i]
        # Skip whitespace after tag name
        while i < len(content) and content[i].isspace():
            i += 1
        attr_start_pos = i
    else:
        # No attributes, just tag name
        return content, []

    # Now parse attributes
    result = [tag_name]
    seen_attrs: Set[str] = set()  # Track attributes to remove duplicates
    i = attr_start_pos

    while i < len(content):
        # Skip whitespace
        while i < len(content) and content[i].isspace():
            i += 1

        if i >= len(content):
            break

        # Look for attribute pattern: name=value
        attr_start = i

        # Find attribute name
        while i < len(content) and (content[i].isalnum() or content[i] in "_-:"):
            i += 1

        if i >= len(content) or content[i] != "=":
            # Not an attribute, just copy the rest
            result.append(" ")
            result.append(content[attr_start:])
            break

        attr_name = content[attr_start:i]
        attr_name_lower = attr_name.lower()  # Case-insensitive duplicate check
        i += 1  # Skip the '='

        # Skip if this is a duplicate attribute
        if attr_name_lower in seen_attrs:
            actions.append(
                RepairAction(
                    repair_type=RepairType.DUPLICATE_ATTRIBUTE,
                    description=f"Removed duplicate attribute '{attr_name_lower}'",
                    location=tag_name,
                )
            )
            # Parse the value but don't add to result
            if i < len(content) and content[i] in ['"', "'"]:
                quote_char = content[i]
                i += 1
                while i < len(content) and content[i] != quote_char:
                    i += 1
                if i < len(content):
                    i += 1
            else:
                # Unquoted value
                while i < len(content):
                    if content[i].isspace():
                        j = i
                        while j < len(content) and content[j].isspace():
                            j += 1
                        if j < len(content):
                            k = j
                            while k < len(content) and (
                                content[k].isalnum() or content[k] in "-_:"
                            ):
                                k += 1
                            if k < len(content) and content[k] == "=":
                                break
                    i += 1
            continue

        seen_attrs.add(attr_name_lower)

        if i >= len(content):
            result.append(f' {attr_name}="')
            break

        # Handle the value
        if content[i] in ['"', "'"]:
            # Already quoted, find the end quote
            quote_char = content[i]
            value_start = i + 1  # Start after the opening quote
            i += 1
            while i < len(content) and content[i] != quote_char:
                i += 1
            value = content[value_start:i]  # Value without quotes
            if i < len(content):
                i += 1  # Skip the closing quote
            # Escape the value and add with quotes
            escaped_value = escape_attribute_value(
                value, quote_char, aggressive_escape=aggressive_escape
            )
            result.append(f" {attr_name}={quote_char}{escaped_value}{quote_char}")
        else:
            # Unquoted value, collect until next attribute or end
            value_start = i

            # Collect value until we hit the next attribute (word=) or end
            while i < len(content):
                if content[i].isspace():
                    # Look ahead to see if this is the start of a new attribute
                    j = i
                    while j < len(content) and content[j].isspace():
                        j += 1

                    # Check if we have word= pattern ahead
                    if j < len(content):
                        while j < len(content) and (content[j].isalnum() or content[j] in "-_:"):
                            j += 1
                        if j < len(content) and content[j] == "=":
                            # This is a new attribute, stop here
                            break
                i += 1

            value = content[value_start:i].strip()
            # Report this action
            escaped_value = escape_attribute_value(value, '"', aggressive_escape=aggressive_escape)
            actions.append(
                RepairAction(
                    repair_type=RepairType.MALFORMED_ATTRIBUTE,
                    description=f"Added quotes to unquoted attribute '{attr_name}'",
                    location=tag_name,
                    before=f"{attr_name}={value}",
                    after=f'{attr_name}="{escaped_value}"',
                )
            )
            result.append(f' {attr_name}="{escaped_value}"')

    return "".join(result), actions
