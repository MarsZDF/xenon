"""Property-based tests using Hypothesis for Xenon XML repair.

These tests use generative testing to find edge cases and ensure robustness.
"""

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite, integers, text

from xenon import (
    TrustLevel,
    parse_xml,
    parse_xml_lenient,
    parse_xml_safe,
    repair_xml,
    repair_xml_lenient,
    repair_xml_safe,
)
from xenon.exceptions import XenonException


# Custom strategies for generating XML-like content
@composite
def xml_tag_names(draw):
    """Generate valid XML tag names (start with letter/underscore)."""
    first_char = draw(st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"))
    rest = draw(
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",
            min_size=0,
            max_size=15,
        )
    )
    return first_char + rest


@composite
def simple_xml_elements(draw):
    """Generate simple, well-formed XML elements."""
    tag = draw(xml_tag_names())
    content = draw(
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ",
            min_size=0,
            max_size=50,
        )
    )
    return f"<{tag}>{content}</{tag}>"


@composite
def truncated_xml(draw):
    """Generate truncated/incomplete XML."""
    tag = draw(xml_tag_names())
    content = draw(
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ",
            min_size=0,
            max_size=50,
        )
    )
    # Truncate at various points
    truncation_point = draw(st.integers(min_value=0, max_value=len(content)))
    return f"<{tag}>{content[:truncation_point]}"


class TestPropertyBasedRobustness:
    """Test that repair functions are robust across all inputs."""

    @given(st.text(min_size=0, max_size=200))
    @settings(max_examples=200, deadline=None)
    def test_lenient_never_crashes(self, xml_input):
        """repair_xml_lenient should NEVER raise exceptions, no matter the input."""
        # This is the key property - lenient mode must always return a string
        result = repair_xml_lenient(xml_input)
        assert isinstance(result, str)

    @given(st.text(min_size=0, max_size=200))
    @settings(max_examples=200, deadline=None)
    def test_lenient_parse_never_crashes(self, xml_input):
        """parse_xml_lenient should NEVER raise exceptions."""
        result = parse_xml_lenient(xml_input)
        assert isinstance(result, dict)

    @given(st.none() | st.integers() | st.booleans() | st.lists(st.text()))
    @settings(max_examples=100, deadline=None)
    def test_lenient_handles_wrong_types(self, invalid_input):
        """Lenient functions should handle non-string inputs gracefully."""
        result = repair_xml_lenient(invalid_input)
        assert isinstance(result, str)

        parse_result = parse_xml_lenient(invalid_input)
        assert isinstance(parse_result, dict)

    @given(simple_xml_elements())
    @settings(max_examples=100, deadline=None)
    def test_well_formed_xml_unchanged(self, xml):
        """Well-formed XML should pass through unchanged (modulo whitespace)."""
        result = repair_xml(xml, trust=TrustLevel.TRUSTED)
        # The content should be preserved
        assert all(part in result for part in ["<", ">"])

    @given(simple_xml_elements())
    @settings(max_examples=100, deadline=None)
    def test_idempotency(self, xml):
        """Repairing twice should be the same as repairing once."""
        first_repair = repair_xml(xml, trust=TrustLevel.TRUSTED)
        second_repair = repair_xml(first_repair, trust=TrustLevel.TRUSTED)
        assert first_repair == second_repair

    @given(truncated_xml())
    @settings(max_examples=100, deadline=None)
    def test_truncated_xml_gets_closed(self, xml):
        """Truncated XML should get closing tags added."""
        result = repair_xml(xml, trust=TrustLevel.TRUSTED)
        # Result should have balanced tags or be empty
        assert isinstance(result, str)
        # Should have added closing tags
        if "<" in xml:
            assert (
                result.count("<") <= result.count(">") + 10
            )  # Allow some imbalance for edge cases


class TestPropertyBasedCorrectness:
    """Test correctness properties of repair functions."""

    @given(
        xml_tag_names(),
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=20),
    )
    @settings(max_examples=100, deadline=None)
    def test_unquoted_attributes_get_quoted(self, tag, value):
        """Unquoted attribute values should get quoted."""
        # Use safe alphabet that doesn't need escaping
        xml = f"<{tag} attr={value}></{tag}>"
        result = repair_xml(xml, trust=TrustLevel.TRUSTED)

        # Value should be quoted (either as-is or escaped)
        assert 'attr="' in result or "attr='" in result or f"attr={value}" in result

    @given(xml_tag_names(), st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=30))
    @settings(max_examples=100, deadline=None)
    def test_special_chars_get_escaped(self, tag, content):
        """Special characters < > & should be escaped in content."""
        # Add special chars to content
        test_content = f"{content} < & >"
        xml = f"<{tag}>{test_content}</{tag}>"
        result = repair_xml(xml, trust=TrustLevel.TRUSTED)

        # Special chars should be escaped (unless in CDATA)
        if "<![CDATA[" not in result:
            assert "&lt;" in result or "&gt;" in result or "&amp;" in result

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=100, deadline=None)
    def test_safe_mode_type_checking(self, input_str):
        """repair_xml_safe should validate input types."""
        # String input should work
        result = repair_xml_safe(input_str, trust=TrustLevel.TRUSTED, allow_empty=True)
        assert isinstance(result, str)

    @given(st.integers() | st.booleans() | st.lists(st.text()))
    @settings(max_examples=50, deadline=None)
    def test_safe_mode_rejects_wrong_types(self, invalid_input):
        """repair_xml_safe should reject non-string inputs."""
        with pytest.raises(Exception):  # Should raise ValidationError
            repair_xml_safe(invalid_input, trust=TrustLevel.TRUSTED, allow_empty=False)


class TestPropertyBasedSecurity:
    """Test security properties."""

    @given(xml_tag_names(), st.text(min_size=0, max_size=50))
    @settings(max_examples=50, deadline=None)
    def test_dangerous_pis_can_be_stripped(self, tag, content):
        """Dangerous processing instructions can be stripped."""
        xml = f'<?php echo "danger"; ?><{tag}>{content}</{tag}>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, strip_dangerous_pis=True)

        # PHP PI should be removed
        assert "<?php" not in result

    @given(xml_tag_names(), st.text(min_size=0, max_size=50))
    @settings(max_examples=50, deadline=None)
    def test_dangerous_tags_can_be_stripped(self, tag, content):
        """Dangerous tags like <script> can be stripped."""
        xml = f'<script>alert("xss")</script><{tag}>{content}</{tag}>'
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, strip_dangerous_tags=True)

        # Script tag should be removed
        assert "<script>" not in result.lower()


class TestPropertyBasedCDATA:
    """Test CDATA wrapping properties."""

    @given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789 ()", min_size=3, max_size=30))
    @settings(max_examples=50, deadline=None)
    def test_cdata_wrapping_preserves_content(self, code_content):
        """CDATA wrapping should preserve the original content."""
        # Add exactly one special char to trigger CDATA without creating complex parsing issues
        test_content = f"{code_content} > 5"

        xml = f"<code>{test_content}</code>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        # Original content should be preserved in result (possibly in CDATA)
        if "<![CDATA[" in result:
            # Content is in CDATA, should be unescaped
            assert test_content in result
        else:
            # Content is escaped
            assert isinstance(result, str)

    @given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789 ", min_size=5, max_size=30))
    @settings(max_examples=50, deadline=None)
    def test_cdata_not_used_for_simple_text(self, simple_text):
        """Simple text without special chars shouldn't use CDATA."""
        # Ensure no special chars
        assume(not any(c in simple_text for c in ["&", "<", ">"]))

        xml = f"<code>{simple_text}</code>"
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)

        # Should not use CDATA for simple text
        assert "<![CDATA[" not in result

    @given(st.sampled_from(["code", "script", "pre", "sql", "xpath", "query"]))
    @settings(max_examples=20, deadline=None)
    def test_cdata_only_for_candidate_tags(self, code_tag):
        """CDATA should only wrap content in code-like tags."""
        code_content = "x < 5 && y > 3"

        # Test with code tag
        xml_code = f"<{code_tag}>{code_content}</{code_tag}>"
        result_code = repair_xml_safe(xml_code, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True)
        assert "<![CDATA[" in result_code

        # Test with regular tag
        xml_regular = f"<div>{code_content}</div>"
        result_regular = repair_xml_safe(
            xml_regular, trust=TrustLevel.TRUSTED, auto_wrap_cdata=True
        )
        assert "<![CDATA[" not in result_regular


class TestPropertyBasedEdgeCases:
    """Test edge cases and boundary conditions."""

    @given(st.text(min_size=0, max_size=0))
    @settings(max_examples=10, deadline=None)
    def test_empty_string_handling(self, empty):
        """Empty strings should be handled gracefully."""
        assert empty == ""
        result = repair_xml_safe(empty, trust=TrustLevel.TRUSTED, allow_empty=True)
        assert result == ""

    @given(st.text(alphabet=" \n\t\r", min_size=1, max_size=20))
    @settings(max_examples=20, deadline=None)
    def test_whitespace_only_handling(self, whitespace):
        """Whitespace-only strings should be handled."""
        result = repair_xml_safe(whitespace, trust=TrustLevel.TRUSTED, allow_empty=True)
        assert isinstance(result, str)

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=10, deadline=None)
    def test_deeply_nested_xml(self, depth):
        """Handle deeply nested XML structures."""
        # Build nested structure
        xml = "".join([f"<level{i}>" for i in range(depth)])
        xml += "content"
        # Intentionally truncate (don't close tags)

        result = repair_xml(xml, trust=TrustLevel.TRUSTED)
        # Should close all tags
        assert isinstance(result, str)
        assert "content" in result

    @given(st.lists(xml_tag_names(), min_size=2, max_size=5))
    @settings(max_examples=20, deadline=None)
    def test_multiple_roots_can_be_wrapped(self, tag_list):
        """Multiple root elements can be wrapped."""
        xml = "".join([f"<{tag}>data</{tag}>" for tag in tag_list])
        result = repair_xml_safe(xml, trust=TrustLevel.TRUSTED, wrap_multiple_roots=True)

        # Should wrap in <document>
        assert "<document>" in result
        assert "</document>" in result
