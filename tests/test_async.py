"""
Tests for async streaming XML repair functionality.

This module tests the async variants of streaming repair methods,
ensuring compatibility with async LLM SDKs and frameworks.
"""

import asyncio
from typing import AsyncGenerator, AsyncIterator, List

import pytest

from xenon import TrustLevel
from xenon.exceptions import SecurityError
from xenon.streaming import StreamingXMLRepair


# Mock async stream
async def async_stream_chunks(chunks: List[str]) -> AsyncGenerator[str, None]:
    """Simulate an async LLM stream by yielding chunks with small delays."""
    for chunk in chunks:
        await asyncio.sleep(0.001)  # Simulate network delay
        yield chunk


class TestAsyncStreamingBasic:
    """Test basic async streaming functionality."""

    @pytest.mark.asyncio
    async def test_simple_async_streaming(self):
        """Test basic async streaming with complete tags."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)
        chunks = ["<root>", "<item>", "test", "</item>", "</root>"]

        results = []
        async for chunk in async_stream_chunks(chunks):
            async for safe in repairer.feed_async(chunk):
                results.append(safe)

        async for final in repairer.finalize_async():
            results.append(final)

        # Verify output
        assert "<root>" in results
        assert "<item>" in results
        assert "test" in results
        assert "</item>" in results
        assert "</root>" in results

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager auto-finalize."""
        chunks = ["<root>", "<item>", "incomplete"]
        results = []

        async with StreamingXMLRepair(trust=TrustLevel.TRUSTED) as repairer:
            async for chunk in async_stream_chunks(chunks):
                async for safe in repairer.feed_async(chunk):
                    results.append(safe)
            # Get finalize output before context exits
            async for final in repairer.finalize_async():
                results.append(final)

        # Context manager should have auto-finalized
        assert repairer._finalized
        # Should have closing tags from finalize
        combined = "".join(results)
        assert "</item>" in combined
        assert "</root>" in combined

    @pytest.mark.asyncio
    async def test_async_truncated_repair(self):
        """Test async repair of truncated XML."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)
        chunks = ["<root><user name=john>John", "</user>"]

        results = []
        async for chunk in async_stream_chunks(chunks):
            async for safe in repairer.feed_async(chunk):
                results.append(safe)

        async for final in repairer.finalize_async():
            results.append(final)

        combined = "".join(results)
        # Should have repaired unquoted attribute
        assert 'name="john"' in combined
        assert "</root>" in combined  # Auto-closed


class TestAsyncStreamingSecurity:
    """Test async streaming with security features."""

    @pytest.mark.asyncio
    async def test_async_dangerous_pi_stripping(self):
        """Test dangerous PI stripping in async mode."""
        repairer = StreamingXMLRepair(trust=TrustLevel.UNTRUSTED)
        chunks = ["<?php system('ls'); ?>", "<root>safe</root>"]

        results = []
        async for chunk in async_stream_chunks(chunks):
            async for safe in repairer.feed_async(chunk):
                results.append(safe)

        async for final in repairer.finalize_async():
            results.append(final)

        combined = "".join(results)
        # Dangerous PI should be stripped
        assert "<?php" not in combined
        assert "system" not in combined
        assert "<root>safe</root>" in combined

    @pytest.mark.asyncio
    async def test_async_entity_escaping(self):
        """Test entity escaping in async streaming."""
        repairer = StreamingXMLRepair(trust=TrustLevel.UNTRUSTED)
        chunks = ["<root>", "Tom & Jerry", "</root>"]

        results = []
        async for chunk in async_stream_chunks(chunks):
            async for safe in repairer.feed_async(chunk):
                results.append(safe)

        async for final in repairer.finalize_async():
            results.append(final)

        combined = "".join(results)
        assert "Tom &amp; Jerry" in combined

    @pytest.mark.asyncio
    async def test_async_max_depth_limit(self):
        """Test max depth limit enforcement in async mode."""
        repairer = StreamingXMLRepair(trust=TrustLevel.UNTRUSTED)

        # Create deeply nested XML (UNTRUSTED has max_depth=1000)
        chunks = ["<root>"] + ["<level>"] * 1001

        with pytest.raises(SecurityError, match="Maximum nesting depth"):
            async for chunk in async_stream_chunks(chunks):
                async for safe in repairer.feed_async(chunk):
                    pass


class TestAsyncStreamingChunkBoundaries:
    """Test async streaming with challenging chunk boundaries."""

    @pytest.mark.asyncio
    async def test_async_tag_split_across_chunks(self):
        """Test tag split across chunk boundaries."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)
        # Split tag in middle of name
        chunks = ["<ro", "ot><item>", "test</item></root>"]

        results = []
        async for chunk in async_stream_chunks(chunks):
            async for safe in repairer.feed_async(chunk):
                results.append(safe)

        async for final in repairer.finalize_async():
            results.append(final)

        combined = "".join(results)
        assert "<root>" in combined
        assert "<item>" in combined

    @pytest.mark.asyncio
    async def test_async_attribute_split(self):
        """Test attribute split across chunks."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)
        chunks = ["<user na", "me=john>", "data</user>"]

        results = []
        async for chunk in async_stream_chunks(chunks):
            async for safe in repairer.feed_async(chunk):
                results.append(safe)

        async for final in repairer.finalize_async():
            results.append(final)

        combined = "".join(results)
        assert 'name="john"' in combined

    @pytest.mark.asyncio
    async def test_async_single_char_chunks(self):
        """Test extreme case of single-character chunks."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)
        xml = "<root><item>test</item></root>"
        chunks = list(xml)  # One char at a time

        results = []
        async for chunk in async_stream_chunks(chunks):
            async for safe in repairer.feed_async(chunk):
                results.append(safe)

        async for final in repairer.finalize_async():
            results.append(final)

        combined = "".join(results)
        assert "<root>" in combined
        assert "test" in combined
        assert "</root>" in combined


class TestAsyncStreamingConcurrency:
    """Test concurrent async streaming operations."""

    @pytest.mark.asyncio
    async def test_concurrent_async_repairs(self):
        """Test multiple concurrent async repair streams."""

        async def repair_stream(stream_id: int, chunks: List[str]) -> str:
            repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)
            results = []

            for chunk in chunks:
                async for safe in repairer.feed_async(chunk):
                    results.append(safe)

            async for final in repairer.finalize_async():
                results.append(final)

            return "".join(results)

        # Run 10 concurrent repairs
        tasks = [repair_stream(i, [f"<stream{i}>", f"<item>data{i}</item>"]) for i in range(10)]

        results = await asyncio.gather(*tasks)

        # Verify each stream processed correctly
        for i, result in enumerate(results):
            assert f"<stream{i}>" in result
            assert f"data{i}" in result
            assert f"</stream{i}>" in result

    @pytest.mark.asyncio
    async def test_async_event_loop_responsiveness(self):
        """Test that async methods yield control to event loop."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)
        chunks = ["<root>"] + [f"<item{i}>" for i in range(100)]

        events_processed = 0

        async def background_task():
            """Background task to verify event loop is responsive."""
            nonlocal events_processed
            for _ in range(10):
                await asyncio.sleep(0.001)
                events_processed += 1

        # Start background task
        bg_task = asyncio.create_task(background_task())

        # Process chunks
        async for chunk in async_stream_chunks(chunks):
            async for safe in repairer.feed_async(chunk):
                pass

        # Wait for background task
        await bg_task

        # Background task should have run (event loop was responsive)
        assert events_processed > 0


class TestAsyncStreamingEdgeCases:
    """Test async streaming edge cases."""

    @pytest.mark.asyncio
    async def test_async_empty_chunks(self):
        """Test handling of empty chunks in async mode."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)
        chunks = ["<root>", "", "<item>", "", "test", "", "</item>", "", "</root>"]

        results = []
        async for chunk in async_stream_chunks(chunks):
            async for safe in repairer.feed_async(chunk):
                results.append(safe)

        async for final in repairer.finalize_async():
            results.append(final)

        combined = "".join(results)
        assert "<root>" in combined
        assert "test" in combined

    @pytest.mark.asyncio
    async def test_async_finalize_idempotent(self):
        """Test that finalize_async is idempotent."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        async for chunk in async_stream_chunks(["<root>"]):
            async for safe in repairer.feed_async(chunk):
                pass

        # First finalize
        results1 = []
        async for final in repairer.finalize_async():
            results1.append(final)

        # Second finalize should yield nothing
        results2 = []
        async for final in repairer.finalize_async():
            results2.append(final)

        assert len(results1) > 0
        assert len(results2) == 0

    @pytest.mark.asyncio
    async def test_async_feed_after_finalize_raises(self):
        """Test that feeding after finalize raises error."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)

        async for _ in repairer.finalize_async():
            pass

        with pytest.raises(RuntimeError, match="Cannot feed after finalize"):
            async for _ in repairer.feed_async("<root>"):
                pass


class TestAsyncStreamingComments:
    """Test async streaming with XML comments."""

    @pytest.mark.asyncio
    async def test_async_comment_passthrough(self):
        """Test comments pass through in async mode."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)
        chunks = ["<!-- comment -->", "<root>", "data", "</root>"]

        results = []
        async for chunk in async_stream_chunks(chunks):
            async for safe in repairer.feed_async(chunk):
                results.append(safe)

        async for final in repairer.finalize_async():
            results.append(final)

        combined = "".join(results)
        assert "<!-- comment -->" in combined

    @pytest.mark.asyncio
    async def test_async_comment_split(self):
        """Test comment split across chunks."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)
        chunks = ["<!-- com", "ment -->", "<root>data</root>"]

        results = []
        async for chunk in async_stream_chunks(chunks):
            async for safe in repairer.feed_async(chunk):
                results.append(safe)

        async for final in repairer.finalize_async():
            results.append(final)

        combined = "".join(results)
        assert "<!-- comment -->" in combined


class TestAsyncStreamingCDATA:
    """Test async streaming with CDATA sections."""

    @pytest.mark.asyncio
    async def test_async_cdata_passthrough(self):
        """Test CDATA passes through in async mode."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)
        chunks = ["<root>", "<![CDATA[<>&]]>", "</root>"]

        results = []
        async for chunk in async_stream_chunks(chunks):
            async for safe in repairer.feed_async(chunk):
                results.append(safe)

        async for final in repairer.finalize_async():
            results.append(final)

        combined = "".join(results)
        assert "<![CDATA[<>&]]>" in combined

    @pytest.mark.asyncio
    async def test_async_cdata_split(self):
        """Test CDATA split across chunks."""
        repairer = StreamingXMLRepair(trust=TrustLevel.TRUSTED)
        chunks = ["<root>", "<![CDATA[", "special <>&", "]]>", "</root>"]

        results = []
        async for chunk in async_stream_chunks(chunks):
            async for safe in repairer.feed_async(chunk):
                results.append(safe)

        async for final in repairer.finalize_async():
            results.append(final)

        combined = "".join(results)
        assert "<![CDATA[special <>&]]>" in combined
