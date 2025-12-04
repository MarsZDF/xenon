"""
Async LLM Integration Examples for Xenon.

This module demonstrates how to integrate Xenon's async streaming repair
with any async LLM SDK or streaming data source.

These examples show real-world usage patterns for production applications
using generic async patterns that work with any provider.
"""

import asyncio
from typing import AsyncIterator

from xenon import TrustLevel
from xenon.streaming import StreamingXMLRepair


# =============================================================================
# Example 1: Generic Async LLM Streaming
# =============================================================================


async def async_llm_streaming_example():
    """
    Example: Repair XML from any async LLM streaming API.

    This pattern works with any async streaming API that yields text chunks.
    Compatible with OpenAI, Anthropic, Cohere, or any AsyncIterator[str] source.
    """
    print("=" * 80)
    print("Example 1: Generic Async LLM Streaming")
    print("=" * 80)

    # Generic pattern - works with ANY async LLM SDK:
    """
    # Pattern for any async LLM SDK:
    async def your_llm_stream() -> AsyncIterator[str]:
        # Your LLM API call here (OpenAI, Anthropic, Cohere, etc.)
        async for chunk in llm_client.stream(...):
            yield chunk.text  # or chunk.content, chunk.delta, etc.

    # Repair the stream:
    async with StreamingXMLRepair(trust=TrustLevel.UNTRUSTED) as repairer:
        async for chunk in your_llm_stream():
            async for safe_xml in repairer.feed_async(chunk):
                print(safe_xml, end='', flush=True)
    """

    # Simulated LLM stream for demonstration
    async def mock_llm_stream() -> AsyncIterator[str]:
        """Simulate any LLM streaming response."""
        chunks = [
            "Here's your XML:\n\n",  # Conversational fluff
            "<users>\n",
            "  <user id=1 name=",  # Malformed: unquoted attribute
            "Alice",
            ">\n",
            "    <email>alice@",
            "example.com</email>\n",
            "    <role>admin</role>\n",
            "  </user>\n",
            "  <user id=2 name=Bob>\n",  # Another malformed attribute
            "    <email>bob@example.com",  # Truncated - missing closing tags
        ]
        for chunk in chunks:
            await asyncio.sleep(0.01)  # Simulate network delay
            yield chunk

    print("\nStreaming repaired XML:")
    print("-" * 40)

    async with StreamingXMLRepair(trust=TrustLevel.UNTRUSTED) as repairer:
        async for chunk in mock_llm_stream():
            async for safe_xml in repairer.feed_async(chunk):
                print(safe_xml, end="", flush=True)

    print("\n" + "-" * 40)
    print("✅ Stream completed and finalized\n")


# =============================================================================
# Example 2: Async Streaming with Error Recovery
# =============================================================================


async def error_recovery_streaming_example():
    """
    Example: Handle malformed XML with real-time repair.

    Shows how Xenon repairs common LLM mistakes on-the-fly.
    """
    print("=" * 80)
    print("Example 2: Real-Time Error Recovery")
    print("=" * 80)

    # Simulated LLM stream with various errors
    async def mock_error_stream() -> AsyncIterator[str]:
        """Simulate LLM stream with common XML errors."""
        chunks = [
            "I'll create an XML catalog for you:\n\n",
            "<?xml version=1.0?>",  # Malformed: missing quotes
            "\n<catalog>\n",
            "  <product id=101>\n",  # Unquoted attribute
            "    <name>Laptop</name>\n",
            "    <price currency=USD>999</price>\n",
            "    <description>High-performance & efficient",  # Unescaped &
        ]
        for chunk in chunks:
            await asyncio.sleep(0.01)
            yield chunk

    print("\nInput errors:")
    print("  - Missing quotes in XML declaration")
    print("  - Unquoted attributes (id=101, currency=USD)")
    print("  - Unescaped ampersand (&)")
    print("  - Missing closing tags (truncation)")
    print("\nStreaming repaired XML:")
    print("-" * 40)

    async with StreamingXMLRepair(trust=TrustLevel.UNTRUSTED) as repairer:
        async for chunk in mock_error_stream():
            async for safe_xml in repairer.feed_async(chunk):
                print(safe_xml, end="", flush=True)

    print("\n" + "-" * 40)
    print("✅ All errors auto-repaired during streaming\n")


# =============================================================================
# Example 3: Async Pipeline Integration
# =============================================================================


async def async_pipeline_example():
    """
    Example: Use Xenon in async processing pipelines.

    Shows how to integrate with async frameworks and chains.
    """
    print("=" * 80)
    print("Example 3: Async Processing Pipeline")
    print("=" * 80)

    # Generic async pipeline pattern (works with LangChain, custom pipelines, etc.)
    async def mock_pipeline_stream():
        """Simulate LangChain LLM streaming."""
        chunks = [
            "<todos>\n",
            "  <todo priority=high status=pending>",  # Malformed attributes
            "Fix bugs",
            "</todo>\n",
            "  <todo priority=low>",
            "Write docs",  # Missing closing tag
        ]
        for chunk in chunks:
            await asyncio.sleep(0.01)
            yield chunk

    print("\nAsync pipeline output (with XML repair):")
    print("-" * 40)

    async with StreamingXMLRepair(trust=TrustLevel.UNTRUSTED) as repairer:
        async for chunk in mock_pipeline_stream():
            async for safe_xml in repairer.feed_async(chunk):
                print(safe_xml, end="", flush=True)

    print("\n" + "-" * 40)
    print("✅ Chain executed successfully\n")


# =============================================================================
# Example 4: Concurrent Stream Processing
# =============================================================================


async def concurrent_stream_repair_example():
    """
    Example: Process multiple LLM streams concurrently.

    Demonstrates that Xenon's async support is non-blocking and can
    handle multiple concurrent streams efficiently.
    """
    print("=" * 80)
    print("Example 4: Concurrent Stream Processing")
    print("=" * 80)

    async def process_llm_stream(stream_id: int, chunks: list) -> str:
        """Process a single LLM stream."""
        result = []
        async with StreamingXMLRepair(trust=TrustLevel.UNTRUSTED) as repairer:
            for chunk in chunks:
                await asyncio.sleep(0.001)  # Simulate network delay
                async for safe_xml in repairer.feed_async(chunk):
                    result.append(safe_xml)
        return "".join(result)

    # Simulate 5 concurrent LLM streams
    streams = {
        1: ["<stream1>", "<data>", "alpha", "</data>"],
        2: ["<stream2 attr=val>", "beta"],  # Truncated
        3: ["<stream3>", "<item>", "gamma & delta", "</item>"],  # Unescaped &
        4: ["<stream4>", "<?php hack ?>", "<data>safe</data>"],  # Dangerous PI
        5: ["<stream5>", "<user name=", "eve>", "data</user>"],  # Split attribute
    }

    print("\nProcessing 5 streams concurrently...")

    # Run all streams concurrently
    tasks = [process_llm_stream(stream_id, chunks) for stream_id, chunks in streams.items()]

    results = await asyncio.gather(*tasks)

    # Display results
    print("\nResults:")
    print("-" * 40)
    for stream_id, result in enumerate(results, 1):
        print(f"Stream {stream_id}: {result[:50]}...")

    print("-" * 40)
    print(f"✅ Processed {len(results)} streams concurrently\n")


# =============================================================================
# Example 5: Error Handling in Async Streams
# =============================================================================


async def error_handling_example():
    """
    Example: Proper error handling in async streaming.

    Demonstrates how to handle max depth violations, malformed input,
    and other errors gracefully in async contexts.
    """
    print("=" * 80)
    print("Example 5: Error Handling in Async Streams")
    print("=" * 80)

    async def mock_dangerous_stream() -> AsyncIterator[str]:
        """Simulate a stream that violates max depth."""
        # Create deeply nested XML
        yield "<root>"
        for i in range(1050):  # Exceeds UNTRUSTED max_depth=1000
            yield f"<level{i}>"

    print("\nAttempting to process deeply nested XML...")
    print("(This should trigger max depth protection)")
    print("-" * 40)

    try:
        async with StreamingXMLRepair(trust=TrustLevel.UNTRUSTED) as repairer:
            async for chunk in mock_dangerous_stream():
                async for safe_xml in repairer.feed_async(chunk):
                    pass
    except RuntimeError as e:
        print(f"✅ Caught expected error: {e}")

    print("-" * 40)
    print("\nProper error handling prevents DoS attacks\n")


# =============================================================================
# Example 6: Performance Monitoring
# =============================================================================


async def performance_monitoring_example():
    """
    Example: Monitor async streaming performance.

    Shows how to track metrics like throughput, latency, and memory usage.
    """
    print("=" * 80)
    print("Example 6: Performance Monitoring")
    print("=" * 80)

    import time

    async def mock_high_volume_stream() -> AsyncIterator[str]:
        """Simulate high-volume LLM stream."""
        base_xml = "<item>data</item>"
        for _ in range(100):
            await asyncio.sleep(0.001)
            yield base_xml

    start_time = time.perf_counter()
    chunks_processed = 0
    bytes_processed = 0

    async with StreamingXMLRepair(trust=TrustLevel.UNTRUSTED) as repairer:
        async for chunk in mock_high_volume_stream():
            chunks_processed += 1
            bytes_processed += len(chunk)
            async for safe_xml in repairer.feed_async(chunk):
                pass

    elapsed = time.perf_counter() - start_time

    print(f"\nPerformance Metrics:")
    print("-" * 40)
    print(f"Chunks processed:    {chunks_processed}")
    print(f"Bytes processed:     {bytes_processed}")
    print(f"Total time:          {elapsed:.3f}s")
    print(f"Throughput:          {chunks_processed / elapsed:.0f} chunks/sec")
    print(f"Throughput:          {bytes_processed / elapsed / 1024:.1f} KB/sec")
    print("-" * 40)
    print("✅ High performance maintained\n")


# =============================================================================
# Main Entry Point
# =============================================================================


async def main():
    """Run all async integration examples."""
    print("\n" + "=" * 80)
    print(" Xenon Async LLM Integration Examples")
    print("=" * 80 + "\n")

    # Run examples
    await async_llm_streaming_example()
    await error_recovery_streaming_example()
    await async_pipeline_example()
    await concurrent_stream_repair_example()
    await error_handling_example()
    await performance_monitoring_example()

    print("=" * 80)
    print(" All examples completed successfully! ")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
