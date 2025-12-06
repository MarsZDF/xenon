"""
Tests for robust attribute parsing with the new optimized parser.
"""

from xenon.attribute_parser import fix_malformed_attributes


def test_weird_attribute_names():
    """Test attributes with weird characters in name."""
    # <div attr<name=value> -> parser receives "div attr<name=value"
    # Should probably clean this up or at least handle it gracefully
    # The regex parser would likely skip it or match 'attr' and leave '<name' as garbage?
    # New manual parser might accept 'attr<name'.
    tag = "div attr<name=value"
    fixed, _ = fix_malformed_attributes(tag)
    # We check what it produces.
    # If it produces <div attr<name="value">, that's technically invalid XML but repaired according to logic.
    # Ideally we want valid XML names.
    assert '="' in fixed


def test_space_around_equals():
    """Test attr = val."""
    tag = "div class = foo"
    fixed, _ = fix_malformed_attributes(tag)
    assert 'class="foo"' in fixed


def test_boolean_at_end():
    """Test boolean attribute at end of tag."""
    tag = "input type=checkbox checked"
    fixed, _ = fix_malformed_attributes(tag)
    assert 'type="checkbox"' in fixed
    assert "checked" in fixed


def test_garbage_between_attributes():
    """Test garbage or extra spaces."""
    tag = "div id=1 ,, class=main"
    fixed, _ = fix_malformed_attributes(tag)
    assert 'id="1"' in fixed
    assert 'class="main"' in fixed
    # Garbage might be preserved or stripped depending on logic
    # Our manual parser preserves unknown tokens as-is (appends them)
    assert ",," in fixed


def test_unclosed_quote_at_end():
    """Test unclosed quote at very end."""
    tag = 'div class="foo'
    fixed, _ = fix_malformed_attributes(tag)
    # Should close the quote
    assert 'class="foo"' in fixed


def test_attribute_value_with_equals():
    """Test unquoted value containing equals (if possible?)"""
    # If unquoted, usually stops at space.
    # tag attr=a=b
    tag = "div data=a=b"
    fixed, _ = fix_malformed_attributes(tag)
    # Should be data="a=b"
    assert 'data="a=b"' in fixed
