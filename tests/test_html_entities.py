"""Tests for HTML entity handling (v0.6.0)."""

import pytest

from xenon.entities import (
    convert_html_entities_to_numeric,
    convert_html_entities_to_unicode,
    detect_html_entities,
    normalize_entities,
)


class TestHTMLEntities:
    """Test HTML entity handling."""

    def test_convert_common_entities_to_numeric(self):
        """Test converting common HTML entities to numeric."""
        text = "Price: &euro;50 &mdash; &copy;2024"
        result = convert_html_entities_to_numeric(text)

        assert "&#8364;" in result  # €
        assert "&#8212;" in result  # —
        assert "&#169;" in result  # ©
        assert "&euro;" not in result
        assert "&mdash;" not in result
        assert "&copy;" not in result

    def test_preserve_xml_entities(self):
        """Test that XML entities are preserved."""
        text = "Value &lt; 10 &amp; &nbsp;OK"
        result = convert_html_entities_to_numeric(text, preserve_xml_entities=True)

        assert "&lt;" in result  # Preserved
        assert "&amp;" in result  # Preserved
        assert "&#160;" in result  # nbsp converted
        assert "&nbsp;" not in result

    def test_convert_entities_to_unicode(self):
        """Test converting entities to Unicode characters."""
        text = "&euro;50 &mdash; &copy;2024"
        result = convert_html_entities_to_unicode(text)

        assert "€50" in result
        assert "—" in result
        assert "©2024" in result

    def test_unknown_entity_left_alone(self):
        """Test that unknown entities are left as-is."""
        text = "&euro;50 &unknownentity; &anotherbad;"
        result = convert_html_entities_to_numeric(text)

        assert "&#8364;" in result  # euro converted
        assert "&unknownentity;" in result  # Unknown left as-is
        assert "&anotherbad;" in result

    def test_normalize_entities_numeric_mode(self):
        """Test entity normalization to numeric format."""
        text = "&lt;test&gt; &copy;2024 &#169;2024"
        result = normalize_entities(text, mode="numeric")

        assert "&lt;" in result  # XML entity preserved
        assert "&gt;" in result
        assert "&#169;" in result  # copy converted and already numeric preserved

    def test_normalize_entities_unicode_mode(self):
        """Test entity normalization to Unicode."""
        text = "&#8364;50 &euro;50 &amp;test"
        result = normalize_entities(text, mode="unicode")

        assert "€50" in result
        # XML entities should be preserved (this is tricky, might need adjustment)

    def test_detect_html_entities(self):
        """Test HTML entity detection."""
        text = "&copy;2024 &mdash; &copy;XYZ &nbsp; &lt;test&gt;"
        entities = detect_html_entities(text)

        assert "copy" in entities
        assert entities["copy"] == 2  # Appears twice
        assert "mdash" in entities
        assert entities["mdash"] == 1
        assert "nbsp" in entities
        # XML entities (lt, gt) should not be in the dict
        assert "lt" not in entities
        assert "gt" not in entities

    def test_nbsp_entity(self):
        """Test non-breaking space entity."""
        text = "word1&nbsp;word2"
        result = convert_html_entities_to_numeric(text)

        assert "&#160;" in result

    def test_mathematical_entities(self):
        """Test mathematical entity conversion."""
        text = "5 &times; 3 = 15, 10 &divide; 2 = 5, &plusmn;1"
        result = convert_html_entities_to_numeric(text)

        assert "&#215;" in result  # ×  # noqa: RUF003
        assert "&#247;" in result  # ÷
        assert "&#177;" in result  # ±

    def test_quotation_entities(self):
        """Test quotation mark entities."""
        text = "&ldquo;Hello&rdquo; and &lsquo;world&rsquo;"
        result = convert_html_entities_to_numeric(text)

        assert "&#8220;" in result  # "
        assert "&#8221;" in result  # "
        assert "&#8216;" in result  # '
        assert "&#8217;" in result  # '

    def test_arrow_entities(self):
        """Test arrow entities."""
        text = "&larr; &rarr; &uarr; &darr;"
        result = convert_html_entities_to_numeric(text)

        assert "&#8592;" in result  # ←
        assert "&#8594;" in result  # →
        assert "&#8593;" in result  # ↑
        assert "&#8595;" in result  # ↓

    def test_greek_letter_entities(self):
        """Test Greek letter entities."""
        text = "&alpha;, &beta;, &gamma;, &pi;"
        result = convert_html_entities_to_numeric(text)

        assert "&#945;" in result  # α  # noqa: RUF003
        assert "&#946;" in result  # β
        assert "&#947;" in result  # γ  # noqa: RUF003
        assert "&#960;" in result  # π

    def test_mixed_entities_in_xml(self):
        """Test handling mixed entities in XML context."""
        text = "<root>Price: &euro;50 &amp; value &lt; 100</root>"
        result = convert_html_entities_to_numeric(text, preserve_xml_entities=True)

        assert "&#8364;" in result  # euro converted
        assert "&amp;" in result  # XML entity preserved
        assert "&lt;" in result  # XML entity preserved
