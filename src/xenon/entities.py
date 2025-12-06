"""HTML entity handling for Xenon XML repair."""

import html
import re
from typing import Dict, Match

# Common HTML entities that LLMs might use
HTML_ENTITIES = {
    # Typography
    "nbsp": "\u00a0",  # non-breaking space
    "copy": "\u00a9",  # ©
    "reg": "\u00ae",  # ®
    "trade": "\u2122",  # ™
    "euro": "\u20ac",  # €
    "pound": "\u00a3",  # £
    "yen": "\u00a5",  # ¥
    "cent": "\u00a2",  # ¢
    # Dashes and quotes
    "ndash": "\u2013",  # –  # noqa: RUF003
    "mdash": "\u2014",  # —
    "lsquo": "\u2018",  # '
    "rsquo": "\u2019",  # '
    "sbquo": "\u201a",  # ‚  # noqa: RUF003
    "ldquo": "\u201c",  # "
    "rdquo": "\u201d",  # "
    "bdquo": "\u201e",  # „
    # Math and symbols
    "times": "\u00d7",  # ×  # noqa: RUF003
    "divide": "\u00f7",  # ÷
    "plusmn": "\u00b1",  # ±
    "deg": "\u00b0",  # °
    "micro": "\u00b5",  # µ
    "para": "\u00b6",  # ¶
    "middot": "\u00b7",  # ·
    "frac14": "\u00bc",  # ¼
    "frac12": "\u00bd",  # ½
    "frac34": "\u00be",  # ¾
    # Arrows
    "larr": "\u2190",  # ←
    "rarr": "\u2192",  # →
    "uarr": "\u2191",  # ↑
    "darr": "\u2193",  # ↓
    # Greek letters (common ones)
    "alpha": "\u03b1",
    "beta": "\u03b2",
    "gamma": "\u03b3",
    "delta": "\u03b4",
    "pi": "\u03c0",
    "sigma": "\u03c3",
    # Special characters
    "sect": "\u00a7",  # §
    "hellip": "\u2026",  # …
    "bull": "\u2022",  # •
}


def convert_html_entities_to_numeric(text: str, preserve_xml_entities: bool = True) -> str:
    """
    Convert HTML entities to numeric character references for XML compatibility.

    Args:
        text: Text containing HTML entities
        preserve_xml_entities: If True, don't convert &lt; &gt; &amp; &quot; &apos;

    Returns:
        Text with HTML entities converted to numeric references

    Examples:
        >>> convert_html_entities_to_numeric("Price: &euro;50 &mdash; &copy;2024")
        'Price: &#8364;50 &#8212; &#169;2024'

        >>> convert_html_entities_to_numeric("Value &lt; 10 &amp; &nbsp;OK")
        'Value &lt; 10 &amp; &#160;OK'
    """
    xml_entities = {"lt", "gt", "amp", "quot", "apos"}

    def replace_entity(match: Match[str]) -> str:
        entity_name = match.group(1)

        # Preserve XML entities if requested
        if preserve_xml_entities and entity_name in xml_entities:
            return match.group(0)

        # Convert HTML entity to character
        if entity_name in HTML_ENTITIES:
            char = HTML_ENTITIES[entity_name]
            return f"&#{ord(char)};"

        # If unknown, leave as-is
        return match.group(0)

    # Replace named entities
    result = re.sub(r"&([a-zA-Z]+);", replace_entity, text)

    return result


def convert_html_entities_to_unicode(text: str, preserve_xml_entities: bool = True) -> str:
    """
    Convert HTML entities to Unicode characters.

    Args:
        text: Text containing HTML entities
        preserve_xml_entities: If True, don't convert &lt; &gt; &amp; &quot; &apos;

    Returns:
        Text with HTML entities converted to Unicode

    Examples:
        >>> convert_html_entities_to_unicode("&euro;50 &mdash; &copy;2024")
        '€50 — ©2024'
    """
    xml_entities = {"lt", "gt", "amp", "quot", "apos"}

    def replace_entity(match: Match[str]) -> str:
        entity_name = match.group(1)

        # Preserve XML entities if requested
        if preserve_xml_entities and entity_name in xml_entities:
            return match.group(0)

        # Convert HTML entity to character
        if entity_name in HTML_ENTITIES:
            return HTML_ENTITIES[entity_name]

        # If unknown, leave as-is
        return match.group(0)

    # Replace named entities
    result = re.sub(r"&([a-zA-Z]+);", replace_entity, text)

    return result


def normalize_entities(text: str, mode: str = "numeric") -> str:
    """
    Normalize all entities in text to a consistent format.

    Args:
        text: Text with mixed entity formats
        mode: Target format - "numeric" or "unicode"

    Returns:
        Text with normalized entities

    Examples:
        >>> normalize_entities("&lt;test&gt; &copy;2024", mode="numeric")
        '&lt;test&gt; &#169;2024'

        >>> normalize_entities("&#8364;50 &euro;50", mode="unicode")
        '€50 €50'
    """
    if mode == "numeric":
        # First convert HTML entities to numeric
        result = convert_html_entities_to_numeric(text, preserve_xml_entities=True)
        return result
    elif mode == "unicode":
        # Convert everything to Unicode
        result = convert_html_entities_to_unicode(text, preserve_xml_entities=True)
        # Also decode numeric entities
        result = html.unescape(result)
        # But preserve XML entities (they might be intentional)
        result = result.replace("<", "&lt;")
        result = result.replace(">", "&gt;")
        result = result.replace("&", "&amp;")
        return result
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'numeric' or 'unicode'")


def detect_html_entities(text: str) -> Dict[str, int]:
    """
    Detect HTML entities in text and count occurrences.

    Args:
        text: Text to analyze

    Returns:
        Dictionary mapping entity names to occurrence counts

    Example:
        >>> detect_html_entities("&copy;2024 &mdash; &copy;XYZ")
        {'copy': 2, 'mdash': 1}
    """
    entities: Dict[str, int] = {}
    xml_entities = {"lt", "gt", "amp", "quot", "apos"}

    for match in re.finditer(r"&([a-zA-Z]+);", text):
        entity_name = match.group(1)
        # Skip XML entities
        if entity_name in xml_entities:
            continue
        # Only count known HTML entities
        if entity_name in HTML_ENTITIES:
            entities[entity_name] = entities.get(entity_name, 0) + 1

    return entities
