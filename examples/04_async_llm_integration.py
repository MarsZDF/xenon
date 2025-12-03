"""
Async LLM Integration Examples for Xenon.

This module demonstrates how to integrate Xenon's async streaming repair
with popular async LLM SDKs (OpenAI, Anthropic, LangChain).

These examples show real-world usage patterns for production applications.
"""

import asyncio
from typing import AsyncIterator

from xenon import TrustLevel
from xenon.streaming import StreamingXMLRepair


# =============================================================================
# Example 1: OpenAI Async Streaming
# =============================================================================


async def openai_xml_streaming_example():
    """
    Example: Repair XML from OpenAI streaming chat completion.

    This pattern works with OpenAI's async streaming API, ensuring
    malformed XML is repaired token-by-token as it arrives.
    """
    print("=" * 80)
    print("Example 1: OpenAI Async Streaming")
    print("=" * 80)

    # NOTE: Requires: pip install openai
    # Uncomment to use with real OpenAI API:
    """
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key="your-api-key")

    # Request XML from GPT-4
    stream = await client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an XML generator. Output only valid XML."},
            {"role": "user", "content": "Generate an XML document with user data"}
        ],
        stream=True
    )

    # Repair XML as it streams in
    async with StreamingXMLRepair(trust=TrustLevel.UNTRUSTED) as repairer:
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                async for safe_xml in repairer.feed_async(content):
                    print(safe_xml, end='', flush=True)

    print()  # Newline after stream completes
    """

    # Simulated OpenAI stream for demonstration
    async def mock_openai_stream() -> AsyncIterator[str]:
        """Simulate OpenAI streaming response."""
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
        async for chunk in mock_openai_stream():
            async for safe_xml in repairer.feed_async(chunk):
                print(safe_xml, end="", flush=True)

    print("\n" + "-" * 40)
    print("✅ Stream completed and finalized\n")


# =============================================================================
# Example 2: Anthropic Claude Async Streaming
# =============================================================================


async def anthropic_xml_streaming_example():
    """
    Example: Repair XML from Anthropic Claude streaming.

    Demonstrates integration with Anthropic's async message stream API.
    """
    print("=" * 80)
    print("Example 2: Anthropic Claude Async Streaming")
    print("=" * 80)

    # NOTE: Requires: pip install anthropic
    # Uncomment to use with real Anthropic API:
    """
    import anthropic

    client = anthropic.AsyncAnthropic(api_key="your-api-key")

    async with client.messages.stream(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": "Generate XML for a product catalog with 3 items"}
        ]
    ) as stream:
        async with StreamingXMLRepair(trust=TrustLevel.UNTRUSTED) as repairer:
            async for text in stream.text_stream:
                async for safe_xml in repairer.feed_async(text):
                    print(safe_xml, end='', flush=True)

    print()
    """

    # Simulated Claude stream for demonstration
    async def mock_claude_stream() -> AsyncIterator[str]:
        """Simulate Claude streaming response."""
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

    print("\nStreaming repaired XML:")
    print("-" * 40)

    async with StreamingXMLRepair(trust=TrustLevel.UNTRUSTED) as repairer:
        async for chunk in mock_claude_stream():
            async for safe_xml in repairer.feed_async(chunk):
                print(safe_xml, end="", flush=True)

    print("\n" + "-" * 40)
    print("✅ Stream completed\n")


# =============================================================================
# Example 3: LangChain Async Integration
# =============================================================================


async def langchain_xml_repair_example():
    """
    Example: Use Xenon in LangChain async chains.

    Shows how to create a custom LangChain runnable that repairs XML.
    """
    print("=" * 80)
    print("Example 3: LangChain Async Chain with XML Repair")
    print("=" * 80)

    # NOTE: Requires: pip install langchain langchain-openai
    # Uncomment to use with real LangChain:
    """
    from langchain_openai import ChatOpenAI
    from langchain.schema import HumanMessage
    from langchain.schema.runnable import RunnableLambda

    # Create LLM
    llm = ChatOpenAI(model="gpt-4", streaming=True)

    # Custom XML repair runnable
    async def repair_xml_streaming(message_stream):
        async with StreamingXMLRepair(trust=TrustLevel.UNTRUSTED) as repairer:
            async for chunk in message_stream:
                if hasattr(chunk, 'content'):
                    async for safe_xml in repairer.feed_async(chunk.content):
                        yield safe_xml

    # Build chain: LLM -> XML Repair
    chain = llm | RunnableLambda(repair_xml_streaming)

    # Execute
    async for repaired_chunk in chain.astream(
        HumanMessage(content="Generate XML for a todo list")
    ):
        print(repaired_chunk, end='', flush=True)

    print()
    """

    # Simulated LangChain stream for demonstration
    async def mock_langchain_llm_stream():
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

    print("\nLangChain chain output (with XML repair):")
    print("-" * 40)

    async with StreamingXMLRepair(trust=TrustLevel.UNTRUSTED) as repairer:
        async for chunk in mock_langchain_llm_stream():
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
    tasks = [
        process_llm_stream(stream_id, chunks) for stream_id, chunks in streams.items()
    ]

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
    print(f"Throughput:          {chunks_processed/elapsed:.0f} chunks/sec")
    print(f"Throughput:          {bytes_processed/elapsed/1024:.1f} KB/sec")
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
    await openai_xml_streaming_example()
    await anthropic_xml_streaming_example()
    await langchain_xml_repair_example()
    await concurrent_stream_repair_example()
    await error_handling_example()
    await performance_monitoring_example()

    print("=" * 80)
    print(" All examples completed successfully! ")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
