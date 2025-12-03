"""Tests for streaming XML repair functionality (v0.7.0)."""

import pytest

from xenon import TrustLevel
from xenon.streaming import StreamingXMLRepair, StreamState


class TestStreamingBasics:
    """Test basic streaming functionality."""

    def test_simple_complete_xml(self):
        """Test streaming complete well-formed XML."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        result = list(repairer.feed("<root><item>test</item></root>"))
        assert "<root>" in result
        assert "<item>" in result
        assert "test" in result
        assert "</item>" in result
        assert "</root>" in result

    def test_streaming_in_chunks(self):
        """Test XML split across multiple chunks."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        chunks = ["<root>", "<item>", "test", "</item>", "</root>"]
        results = []
        for chunk in chunks:
            results.extend(repairer.feed(chunk))

        assert "<root>" in results
        assert "<item>" in results
        assert "</item>" in results
        assert "</root>" in results

    def test_empty_input(self):
        """Test handling empty input."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        result = list(repairer.feed(""))
        assert len(result) == 0

        final = list(repairer.finalize())
        assert len(final) == 0

    def test_context_manager(self):
        """Test context manager auto-finalize."""
        results = []
        with StreamingXMLRepair(trust=TrustLevel.TRUSTED) as repairer:
            results.extend(repairer.feed("<root><item>test"))

        # Should have auto-finalized
        assert repairer._finalized

    def test_cannot_feed_after_finalize(self):
        """Test that feeding after finalize raises error."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)
        list(repairer.finalize())

        with pytest.raises(RuntimeError, match="Cannot feed after finalize"):
            list(repairer.feed("<more>xml</more>"))


class TestConversationalFluff:
    """Test stripping conversational fluff."""

    def test_strip_prefix_text(self):
        """Test stripping text before first tag."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = list(repairer.feed("Sure, here's the XML:\n\n<root>data</root>"))

        # Should NOT include the conversational prefix
        assert "Sure" not in "".join(results)
        assert "here's" not in "".join(results)
        assert "<root>" in results
        assert "data" in results

    def test_strip_prefix_across_chunks(self):
        """Test stripping prefix split across chunks."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = []
        results.extend(repairer.feed("Sure, here's"))
        results.extend(repairer.feed(" the XML: "))
        results.extend(repairer.feed("<root>data</root>"))

        # Should NOT include conversational text
        assert "Sure" not in "".join(results)
        assert "<root>" in results

    def test_no_xml_found(self):
        """Test handling input with no XML tags."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = list(repairer.feed("Just plain text, no XML here."))
        final = list(repairer.finalize())

        # Should return empty (never found XML)
        assert len(results) == 0
        assert len(final) == 0


class TestTruncation:
    """Test repairing truncated XML."""

    def test_truncated_tag(self):
        """Test incomplete tag at end of stream."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        list(repairer.feed("<root><item>test"))
        final = list(repairer.finalize())

        # Should close open tags
        assert "</item>" in final
        assert "</root>" in final

    def test_truncated_in_tag_name(self):
        """Test truncation mid-tag-name."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        list(repairer.feed("<root><ite"))
        final = list(repairer.finalize())

        # Should attempt to close
        assert "</ite>" in final or "<ite>" in final
        assert "</root>" in final

    def test_truncated_in_attribute(self):
        """Test truncation mid-attribute."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        list(repairer.feed("<root><item name="))
        final = list(repairer.finalize())

        # Should close as best as possible
        assert "</item>" in final or "<item" in "".join(final)
        assert "</root>" in final

    def test_deeply_nested_truncation(self):
        """Test closing multiple unclosed tags."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        list(repairer.feed("<root><level1><level2><level3>data"))
        final = list(repairer.finalize())

        # Should close all open tags
        assert "</level3>" in final
        assert "</level2>" in final
        assert "</level1>" in final
        assert "</root>" in final


class TestAttributes:
    """Test attribute repair in streaming mode."""

    def test_unquoted_attribute(self):
        """Test quoting unquoted attributes."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = list(repairer.feed("<item name=test>value</item>"))

        # Should quote the attribute
        xml = "".join(results)
        assert 'name="test"' in xml or "name='test'" in xml

    def test_unquoted_attribute_split(self):
        """Test unquoted attribute split across chunks."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = []
        results.extend(repairer.feed("<item name="))
        results.extend(repairer.feed("test>value</item>"))

        xml = "".join(results)
        assert 'name="test"' in xml or "name='test'" in xml

    def test_multiple_attributes(self):
        """Test multiple unquoted attributes."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = list(repairer.feed("<item id=1 name=test category=electronics>"))

        xml = "".join(results)
        # All should be quoted
        assert 'id="1"' in xml or "id='1'" in xml
        assert 'name="test"' in xml or "name='test'" in xml


class TestEntities:
    """Test entity escaping in streaming mode."""

    def test_escape_ampersand(self):
        """Test escaping & in text content."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = list(repairer.feed("<root>A & B</root>"))

        xml = "".join(results)
        assert "&amp;" in xml

    def test_escape_less_than(self):
        """Test escaping < in text content."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = list(repairer.feed("<root>5 < 10</root>"))

        xml = "".join(results)
        assert "&lt;" in xml

    def test_escape_greater_than(self):
        """Test escaping > in text content."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = list(repairer.feed("<root>10 > 5</root>"))

        xml = "".join(results)
        assert "&gt;" in xml

    def test_entities_across_chunks(self):
        """Test entity escaping when split across chunks."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = []
        results.extend(repairer.feed("<root>A "))
        results.extend(repairer.feed("& B</root>"))

        xml = "".join(results)
        assert "&amp;" in xml


class TestSpecialConstructs:
    """Test handling comments, CDATA, processing instructions."""

    def test_comment_passthrough(self):
        """Test comments pass through unchanged."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = list(repairer.feed("<root><!-- comment --><item/></root>"))

        xml = "".join(results)
        assert "<!-- comment -->" in xml

    def test_cdata_passthrough(self):
        """Test CDATA passes through unchanged."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = list(repairer.feed("<root><![CDATA[<>&]]></root>"))

        xml = "".join(results)
        assert "<![CDATA[<>&]]>" in xml

    def test_processing_instruction(self):
        """Test PI passes through."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = list(repairer.feed('<?xml version="1.0"?><root/>'))

        xml = "".join(results)
        assert '<?xml version="1.0"?>' in xml

    def test_comment_split_across_chunks(self):
        """Test comment split across chunks."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = []
        results.extend(repairer.feed("<root><!-- comm"))
        results.extend(repairer.feed("ent --></root>"))

        xml = "".join(results)
        assert "<!-- comment -->" in xml

    def test_cdata_split_across_chunks(self):
        """Test CDATA split across chunks."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = []
        results.extend(repairer.feed("<root><![CDATA["))
        results.extend(repairer.feed("data]]></root>"))

        xml = "".join(results)
        assert "<![CDATA[data]]>" in xml


class TestChunkBoundaries:
    """Test handling various chunk boundary scenarios."""

    def test_tag_split_at_opening(self):
        """Test tag split at '<'."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = []
        results.extend(repairer.feed("<root>data"))
        results.extend(repairer.feed("<item>test</item></root>"))

        xml = "".join(results)
        assert "<root>" in xml
        assert "<item>" in xml

    def test_tag_split_in_name(self):
        """Test tag split in middle of name."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = []
        results.extend(repairer.feed("<root><it"))
        results.extend(repairer.feed("em>test</item></root>"))

        xml = "".join(results)
        assert "<item>" in xml

    def test_tag_split_before_closing(self):
        """Test tag split just before '>'."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = []
        results.extend(repairer.feed("<root><item"))
        results.extend(repairer.feed(">test</item></root>"))

        xml = "".join(results)
        assert "<item>" in xml

    def test_closing_tag_split(self):
        """Test closing tag split."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = []
        results.extend(repairer.feed("<root><item>test</it"))
        results.extend(repairer.feed("em></root>"))

        xml = "".join(results)
        assert "</item>" in xml

    def test_self_closing_split(self):
        """Test self-closing tag split."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = []
        results.extend(repairer.feed("<root><item /"))
        results.extend(repairer.feed("></root>"))

        xml = "".join(results)
        assert "<item />" in xml or "<item/>" in xml

    def test_attribute_value_split(self):
        """Test attribute value split across chunks."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = []
        results.extend(repairer.feed('<root><item name="joh'))
        results.extend(repairer.feed('n">test</item></root>'))

        xml = "".join(results)
        assert 'name="john"' in xml

    def test_text_content_split(self):
        """Test text content split across many chunks."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = []
        results.extend(repairer.feed("<root>"))
        results.extend(repairer.feed("This "))
        results.extend(repairer.feed("is "))
        results.extend(repairer.feed("text"))
        results.extend(repairer.feed("</root>"))

        xml = "".join(results)
        assert "This" in xml
        assert "is" in xml
        assert "text" in xml

    def test_single_character_chunks(self):
        """Test extreme case: one character per chunk."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        xml_string = "<root><item>test</item></root>"
        results = []
        for char in xml_string:
            results.extend(repairer.feed(char))
        results.extend(repairer.finalize())

        xml = "".join(results)
        assert "<root>" in xml
        assert "<item>" in xml
        assert "test" in xml
        assert "</item>" in xml
        assert "</root>" in xml


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_tag(self):
        """Test empty tag."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = list(repairer.feed("<root><item></item></root>"))

        xml = "".join(results)
        assert "<item>" in xml
        assert "</item>" in xml

    def test_whitespace_only_content(self):
        """Test tag with only whitespace."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = list(repairer.feed("<root>   </root>"))

        xml = "".join(results)
        assert "<root>" in xml
        assert "</root>" in xml

    def test_nested_same_tags(self):
        """Test nested tags with same name."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = list(repairer.feed("<item><item>nested</item></item>"))

        xml = "".join(results)
        # Should handle nested same-name tags
        assert xml.count("<item>") == 2
        assert xml.count("</item>") == 2

    def test_case_insensitive_matching(self):
        """Test case-insensitive tag matching."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        results = list(repairer.feed("<Root><Item>test</item></root>"))

        xml = "".join(results)
        # Should match case-insensitively
        assert "</item>" in xml or "</Item>" in xml

    def test_very_long_text_content(self):
        """Test handling very long text content."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        long_text = "A" * 10000
        results = list(repairer.feed(f"<root>{long_text}</root>"))

        xml = "".join(results)
        assert long_text in xml

    def test_many_nested_levels(self):
        """Test deeply nested XML."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        depth = 20
        opening = "".join([f"<level{i}>" for i in range(depth)])
        closing = "".join([f"</level{i}>" for i in range(depth - 1, -1, -1)])

        results = list(repairer.feed(f"{opening}data{closing}"))

        xml = "".join(results)
        assert "data" in xml
        # All tags should be present
        for i in range(depth):
            assert f"<level{i}>" in xml
            assert f"</level{i}>" in xml


class TestRealWorldScenarios:
    """Test realistic LLM streaming scenarios."""

    def test_chatgpt_style_response(self):
        """Test typical ChatGPT streaming response."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        chunks = [
            "Here's the product catalog in XML format:\n\n",
            "<catalog>",
            "\n  <product id=",
            "A001>",
            "\n    <name>Laptop</name>",
            "\n    <price>999.99</price>",
            "\n  </product>",
            "\n</catalog>",
        ]

        results = []
        for chunk in chunks:
            results.extend(repairer.feed(chunk))
        results.extend(repairer.finalize())

        xml = "".join(results)
        assert "<catalog>" in xml
        assert "<product" in xml
        assert "<name>Laptop</name>" in xml
        assert "</catalog>" in xml

    def test_truncated_llm_response(self):
        """Test LLM that hit token limit."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        chunks = [
            "<users>",
            '<user id="1">',
            "<name>Alice</name>",
            '<user id="2">',
            "<name>Bob",  # Truncated!
        ]

        results = []
        for chunk in chunks:
            results.extend(repairer.feed(chunk))
        results.extend(repairer.finalize())

        xml = "".join(results)
        # Should close all open tags
        assert "</name>" in xml
        assert xml.count("</user>") == 2
        assert "</users>" in xml

    def test_malformed_llm_attributes(self):
        """Test LLM that forgets to quote attributes."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        chunks = [
            "<products>",
            "<product id=123 category=electronics>",
            "<name>Phone</name>",
            "</product>",
            "</products>",
        ]

        results = []
        for chunk in chunks:
            results.extend(repairer.feed(chunk))

        xml = "".join(results)
        # Attributes should be quoted
        assert 'id="123"' in xml or "id='123'" in xml
        assert "category=" in xml


class TestPerformance:
    """Test performance characteristics."""

    def test_constant_memory_usage(self):
        """Test that buffer doesn't grow unbounded."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        # Feed many chunks of text
        for _ in range(1000):
            list(repairer.feed("<item>data</item>"))

        # Buffer should stay small
        assert len(repairer.buffer) < 100

    def test_large_tag_buffering(self):
        """Test handling tags with very long attribute values."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        long_value = "x" * 1000
        results = list(repairer.feed(f'<item data="{long_value}">test</item>'))

        xml = "".join(results)
        assert long_value in xml


class TestStateTransitions:
    """Test state machine transitions."""

    def test_initial_to_text(self):
        """Test transition from INITIAL to IN_TEXT."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        assert repairer.state == StreamState.INITIAL

        list(repairer.feed("<root>"))

        assert repairer.state == StreamState.IN_TEXT

    def test_text_to_tag(self):
        """Test transition from IN_TEXT to IN_TAG."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        list(repairer.feed("<root>"))
        assert repairer.state == StreamState.IN_TEXT

        list(repairer.feed("<item"))
        assert repairer.state == StreamState.IN_TAG

    def test_tag_to_text(self):
        """Test transition from IN_TAG to IN_TEXT."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        list(repairer.feed("<root><item>"))

        assert repairer.state == StreamState.IN_TEXT

    def test_comment_state(self):
        """Test IN_COMMENT state."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        list(repairer.feed("<root><!--"))

        assert repairer.state == StreamState.IN_COMMENT

    def test_cdata_state(self):
        """Test IN_CDATA state."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        list(repairer.feed("<root><![CDATA["))

        assert repairer.state == StreamState.IN_CDATA
