"""
Streaming XML repair for real-time LLM output.

This module provides streaming XML repair capabilities that allow processing
XML as it's generated token-by-token, eliminating latency in RAG pipelines.

Supports both synchronous and asynchronous streaming for compatibility with
modern async LLM SDKs (OpenAI, Anthropic, LangChain).

Synchronous Example:
    >>> from xenon.streaming import StreamingXMLRepair
    >>> from xenon import TrustLevel
    >>>
    >>> # Context manager (recommended)
    >>> with StreamingXMLRepair(trust=TrustLevel.UNTRUSTED) as repairer:
    ...     for chunk in llm_stream():
    ...         for safe_xml in repairer.feed(chunk):
    ...             yield safe_xml
    ...     # finalize() called automatically
    >>>
    >>> # Manual control
    >>> repairer = StreamingXMLRepair(trust=TrustLevel.UNTRUSTED)
    >>> for chunk in llm_stream():
    ...     for safe_xml in repairer.feed(chunk):
    ...         yield safe_xml
    >>> for final_xml in repairer.finalize():
    ...     yield final_xml

Asynchronous Example:
    >>> import asyncio
    >>> from xenon.streaming import StreamingXMLRepair
    >>> from xenon import TrustLevel
    >>>
    >>> # Async context manager (recommended)
    >>> async def repair_llm_stream():
    ...     async with StreamingXMLRepair(trust=TrustLevel.UNTRUSTED) as repairer:
    ...         async for chunk in openai.ChatCompletion.acreate(stream=True):
    ...             async for safe_xml in repairer.feed_async(chunk):
    ...                 yield safe_xml
    ...     # finalize_async() called automatically
    >>>
    >>> # Manual async control
    >>> async def repair_manual():
    ...     repairer = StreamingXMLRepair(trust=TrustLevel.UNTRUSTED)
    ...     async for chunk in llm_async_stream():
    ...         async for safe_xml in repairer.feed_async(chunk):
    ...             yield safe_xml
    ...     async for final_xml in repairer.finalize_async():
    ...         yield final_xml
"""

import asyncio
from enum import Enum
from typing import Any, AsyncIterator, Iterator, List, Optional, Tuple, Type

from .attribute_parser import fix_malformed_attributes
from .config import XMLRepairConfig
from .parser import XMLRepairEngine
from .security import check_max_depth
from .trust import TrustLevel, get_security_config


class StreamState(Enum):
    """States for the streaming XML repair state machine."""

    INITIAL = "initial"  # Before first tag (stripping conversational fluff)
    IN_TEXT = "in_text"  # Between tags (text content)
    IN_TAG = "in_tag"  # Inside a tag (buffering until >)
    IN_COMMENT = "in_comment"  # Inside <!-- ... -->
    IN_CDATA = "in_cdata"  # Inside <![CDATA[ ... ]]>
    IN_PI = "in_pi"  # Inside <?...?>


class StreamingXMLRepair:
    """
    Streaming XML repair that processes chunks in real-time.

    This class maintains an internal state machine and buffer to repair XML
    as it's being generated, yielding safe XML chunks as soon as complete
    tags are detected.

    Features:
        - Near-zero latency: Yields XML as tags complete
        - Constant memory: Only buffers incomplete elements
        - Chunk-aware: Handles tag boundaries split across chunks
        - Production-ready: Integrates all xenon repair features

    Limitations vs batch mode:
        - No typo detection: Can't use Levenshtein (no lookahead)
        - Greedy closing: Closes tags as seen, no backtracking
        - Multiple roots: Only detectable at finalize()

    State Machine:
        The parser uses a 6-state machine to track parsing position:

        INITIAL --[find '<']-> IN_TEXT
        IN_TEXT --[find '<']-> IN_TAG | IN_COMMENT | IN_CDATA | IN_PI
        IN_TAG --[find '>']-> IN_TEXT
        IN_COMMENT --[find '-->']-> IN_TEXT
        IN_CDATA --[find ']]>']-> IN_TEXT
        IN_PI --[find '?>']-> IN_TEXT

        States:
            - INITIAL: Before first tag (strips conversational fluff)
            - IN_TEXT: Between tags (text content)
            - IN_TAG: Inside <tag> (buffering until >)
            - IN_COMMENT: Inside <!-- ... --> (pass through)
            - IN_CDATA: Inside <![CDATA[ ... ]]> (pass through)
            - IN_PI: Inside <?...?> (processing instruction)

    Args:
        trust: Trust level of input source (UNTRUSTED for LLMs, INTERNAL for services, TRUSTED for literals)
        buffer_safety_margin: Bytes to keep when yielding text (default: 10)

    Example:
        >>> from xenon import TrustLevel
        >>> repairer = StreamingXMLRepair(trust=TrustLevel.UNTRUSTED)
        >>> for chunk in ["<root><item>", "test</item></root>"]:
        ...     for safe in repairer.feed(chunk):
        ...         print(safe)
        <root>
        <item>
        test
        </item>
        </root>
        >>> for final in repairer.finalize():
        ...     print(final)
    """

    def __init__(
        self,
        trust: TrustLevel,
        buffer_safety_margin: int = 10,
    ):
        """Initialize streaming repairer with trust-based security."""
        # Get security configuration from trust level
        security_config = get_security_config(trust)

        self.trust = trust
        self.buffer_safety_margin = buffer_safety_margin
        self.max_depth = security_config.max_depth

        # State
        self.state = StreamState.INITIAL
        self.buffer = ""
        self.tag_stack: List[Tuple[str, str]] = []  # (original, lowercase)
        self.saw_first_tag = False

        # Create repair engine with trust-based security settings
        repair_config = XMLRepairConfig.from_booleans(
            strip_dangerous_pis=security_config.strip_dangerous_pis,
            strip_external_entities=security_config.strip_external_entities,
            strip_dangerous_tags=security_config.strip_dangerous_tags,
        )
        self._repair_engine = XMLRepairEngine(
            repair_config,
            max_depth=security_config.max_depth,
        )

        # Track if finalize was called
        self._finalized = False

    def feed(self, chunk: str) -> Iterator[str]:
        """
        Feed a chunk of XML, yield safe repaired pieces.

        This method processes the input chunk through the state machine,
        buffering incomplete elements and yielding complete, repaired XML
        as soon as it's safe to do so.

        Args:
            chunk: String chunk from LLM or other source

        Yields:
            Safe XML strings that can be immediately output

        Example:
            >>> from xenon import TrustLevel
            >>> repairer = StreamingXMLRepair(trust=TrustLevel.UNTRUSTED)
            >>> for safe in repairer.feed("<root><user name="):
            ...     print(f"Got: {safe}")
            Got: <root>
            >>> for safe in repairer.feed('john>John</user></root>'):
            ...     print(f"Got: {safe}")
            Got: <user name="john">
            Got: John
            Got: </user>
            Got: </root>
        """
        if self._finalized:
            raise RuntimeError("Cannot feed after finalize() was called")

        self.buffer += chunk

        # Process buffer through state machine
        yield from self._process_buffer()

    def finalize(self) -> Iterator[str]:
        """
        Finalize stream and close any open tags.

        This must be called when the stream ends to handle any buffered
        content and close unclosed tags. If using context manager, this
        is called automatically.

        Yields:
            Final XML pieces (remaining buffer + closing tags)

        Example:
            >>> from xenon import TrustLevel
            >>> repairer = StreamingXMLRepair(trust=TrustLevel.UNTRUSTED)
            >>> list(repairer.feed("<root><item>test"))
            ['<root>', '<item>']
            >>> list(repairer.finalize())
            ['test', '</item>', '</root>']
        """
        if self._finalized:
            return

        self._finalized = True

        # Handle remaining buffer
        if self.buffer:
            if self.state == StreamState.IN_TAG:
                # Incomplete tag at EOF - try to close it
                repaired = self._repair_incomplete_tag(self.buffer)
                if repaired:
                    yield repaired
                self.buffer = ""

            elif self.state == StreamState.IN_TEXT:
                # Text content at EOF
                if self.buffer.strip():
                    escaped_text, _ = self._repair_engine.escape_entities(self.buffer)
                    yield escaped_text
                self.buffer = ""

            elif self.state == StreamState.INITIAL:
                # Never found XML - just return empty or buffer
                # (conversational response with no XML)
                pass

        # Close unclosed tags
        while self.tag_stack:
            tag_name_original, _ = self.tag_stack.pop()
            yield f"</{tag_name_original}>"

    async def feed_async(self, chunk: str) -> AsyncIterator[str]:
        """
        Async variant of feed() for native async/await integration.

        This method is designed for use with async LLM SDKs like OpenAI, Anthropic,
        and LangChain async chains. It yields the same results as feed() but is
        compatible with async for loops.

        Args:
            chunk: String chunk from async LLM stream

        Yields:
            Safe XML strings that can be immediately output

        Example:
            >>> import asyncio
            >>> from xenon import TrustLevel
            >>> async def process_llm_stream():
            ...     repairer = StreamingXMLRepair(trust=TrustLevel.UNTRUSTED)
            ...     async for chunk in openai_async_stream():
            ...         async for safe_xml in repairer.feed_async(chunk):
            ...             print(f"Got: {safe_xml}")
            ...     async for final in repairer.finalize_async():
            ...         print(f"Final: {final}")
        """
        # Process synchronously (CPU-bound, no I/O)
        # But yield control to event loop between chunks
        for result in self.feed(chunk):
            yield result
            # Yield control to event loop for responsiveness
            await asyncio.sleep(0)

    async def finalize_async(self) -> AsyncIterator[str]:
        """
        Async variant of finalize() for async context managers.

        Finalizes the stream and closes any open tags, yielding results
        asynchronously for compatibility with async code.

        Yields:
            Final XML pieces (remaining buffer + closing tags)

        Example:
            >>> async def process():
            ...     async with StreamingXMLRepair(trust=TrustLevel.UNTRUSTED) as repairer:
            ...         async for chunk in llm_stream:
            ...             async for safe in repairer.feed_async(chunk):
            ...                 yield safe
            ...     # finalize_async() called automatically by async context manager
        """
        for result in self.finalize():
            yield result
            await asyncio.sleep(0)

    def __enter__(self) -> "StreamingXMLRepair":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Context manager exit - auto-finalize."""
        if not self._finalized:
            # Consume finalize output (caller should have already yielded it)
            list(self.finalize())

    async def __aenter__(self) -> "StreamingXMLRepair":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Async context manager exit - auto-finalize asynchronously."""
        if not self._finalized:
            # Consume finalize output asynchronously
            async for _ in self.finalize_async():
                pass

    def _is_valid_tag_start(self, char: str) -> bool:
        """
        Check if a character is valid for the start of an XML tag name.

        Args:
            char: Character to check

        Returns:
            True if valid tag start character (letter, underscore, colon, slash, !, ?)
        """
        return char.isalpha() or char in "_:/!?"

    def _check_max_depth(self) -> None:
        """
        Check if current nesting depth exceeds max_depth limit.

        Raises:
            SecurityError: If depth exceeds max_depth
        """
        check_max_depth(len(self.tag_stack), self.max_depth)

    def _process_buffer(self) -> Iterator[str]:
        """Process buffer through state machine."""
        while True:
            if self.state == StreamState.INITIAL:
                # Strip conversational fluff - buffer until first '<'
                idx = self.buffer.find("<")
                if idx == -1:
                    # No tag yet, keep buffering (discard non-XML junk later)
                    break

                # Found first tag, discard everything before it
                self.buffer = self.buffer[idx:]
                self.state = StreamState.IN_TEXT
                self.saw_first_tag = True

            elif self.state == StreamState.IN_TEXT:
                # Look for next tag or special construct
                idx = self.buffer.find("<")
                if idx == -1:
                    # No tag found - might be at chunk boundary
                    # Keep a safety margin in case '<' is arriving next
                    if len(self.buffer) > self.buffer_safety_margin:
                        text = self.buffer[: -self.buffer_safety_margin]
                        self.buffer = self.buffer[-self.buffer_safety_margin :]
                        if text:
                            escaped_text, _ = self._repair_engine.escape_entities(text)
                            yield escaped_text
                    break

                # Yield text before tag
                if idx > 0:
                    text = self.buffer[:idx]
                    escaped_text, _ = self._repair_engine.escape_entities(text)
                    yield escaped_text
                    self.buffer = self.buffer[idx:]

                # Check what kind of tag/construct this is
                if self.buffer.startswith("<!--"):
                    self.state = StreamState.IN_COMMENT
                elif self.buffer.startswith("<![CDATA["):
                    self.state = StreamState.IN_CDATA
                elif self.buffer.startswith("<?"):
                    self.state = StreamState.IN_PI
                else:
                    self.state = StreamState.IN_TAG

            elif self.state == StreamState.IN_COMMENT:
                # Look for comment end
                end = self.buffer.find("-->")
                if end == -1:
                    break  # Need more input

                # Complete comment
                comment = self.buffer[: end + 3]
                self.buffer = self.buffer[end + 3 :]
                yield comment  # Comments pass through as-is
                self.state = StreamState.IN_TEXT

            elif self.state == StreamState.IN_CDATA:
                # Look for CDATA end
                end = self.buffer.find("]]>")
                if end == -1:
                    break  # Need more input

                # Complete CDATA
                cdata = self.buffer[: end + 3]
                self.buffer = self.buffer[end + 3 :]
                yield cdata  # CDATA passes through as-is
                self.state = StreamState.IN_TEXT

            elif self.state == StreamState.IN_PI:
                # Look for PI end
                end = self.buffer.find("?>")
                if end == -1:
                    break  # Need more input

                # Complete PI
                pi = self.buffer[: end + 2]
                self.buffer = self.buffer[end + 2 :]

                # Filter dangerous PIs if configured
                if (
                    self._repair_engine.strip_dangerous_pis
                    and self._repair_engine.security_filter.is_dangerous_pi(pi)
                ):
                    # Skip dangerous PI (don't yield it)
                    pass
                else:
                    yield pi

                self.state = StreamState.IN_TEXT

            elif self.state == StreamState.IN_TAG:
                # Look for tag end
                end = self.buffer.find(">")
                if end == -1:
                    # Incomplete tag - need more input
                    # But check if this looks like invalid tag (e.g., "<10" from "5 < 10")
                    if len(self.buffer) > 1:
                        first_char = self.buffer[1]
                        if not self._is_valid_tag_start(first_char):
                            # This looks like a false start (e.g., "< 10" treated as tag)
                            # Yield "<" as text and continue
                            yield "&lt;"
                            self.buffer = self.buffer[1:]
                            self.state = StreamState.IN_TEXT
                            continue
                    break

                # Complete tag found
                tag_str = self.buffer[: end + 1]
                self.buffer = self.buffer[end + 1 :]

                # Check if this is a valid tag pattern before processing
                if len(tag_str) > 2:
                    first_char = tag_str[1]
                    if not self._is_valid_tag_start(first_char):
                        # Not a valid tag - treat < as escaped text
                        yield "&lt;"
                        self.buffer = tag_str[1:] + self.buffer
                        self.state = StreamState.IN_TEXT
                        continue

                # Repair and yield
                repaired = self._repair_tag(tag_str)
                if repaired:
                    yield repaired

                self.state = StreamState.IN_TEXT

    def _repair_tag(self, tag_str: str) -> str:
        """
        Repair a complete tag.

        Applies attribute quoting, entity escaping, and tracks tag stack.
        """
        tag_str = tag_str.strip()
        if not tag_str:
            return ""

        # Self-closing tag
        if tag_str.endswith("/>"):
            # Repair attributes
            return self._repair_self_closing_tag(tag_str)

        # Closing tag
        if tag_str.startswith("</"):
            tag_name = tag_str[2:-1].strip()
            # Pop from stack if it matches
            if self.tag_stack:
                stack_name_original, stack_name_lower = self.tag_stack[-1]
                if stack_name_lower == tag_name.lower():
                    self.tag_stack.pop()
                    return f"</{stack_name_original}>"
            # Tag doesn't match stack - still yield it (greedy mode)
            return tag_str

        # Opening tag - extract name, repair attributes, track in stack
        tag_content = tag_str[1:-1].strip()

        # Repair attributes using existing engine
        repaired_content, _ = fix_malformed_attributes(
            tag_content, aggressive_escape=self._repair_engine.escape_unsafe_attributes
        )
        repaired = f"<{repaired_content}>"

        # Extract tag name to track
        parts = tag_content.split(None, 1)
        tag_name = parts[0] if parts else tag_content

        # Track in stack (original case, lowercase for matching)
        self.tag_stack.append((tag_name, tag_name.lower()))
        self._check_max_depth()

        return repaired

    def _repair_self_closing_tag(self, tag_str: str) -> str:
        """Repair self-closing tag attributes."""
        # Extract content without < and />
        tag_content = tag_str[1:-2].strip()
        repaired_content, _ = fix_malformed_attributes(
            tag_content, aggressive_escape=self._repair_engine.escape_unsafe_attributes
        )
        return f"<{repaired_content}/>"

    def _repair_incomplete_tag(self, tag_str: str) -> str:
        """
        Repair an incomplete tag at EOF.

        If tag looks like it was truncated, try to close it.
        """
        tag_str = tag_str.strip()
        if not tag_str:
            return ""

        # If it looks like an opening tag without '>'
        if tag_str.startswith("<") and not tag_str.startswith("</"):
            # Try to close it
            if not tag_str.endswith(">"):
                tag_str += ">"

            # Repair attributes
            tag_content = tag_str[1:-1].strip()
            repaired_content, _ = fix_malformed_attributes(
                tag_content, aggressive_escape=self._repair_engine.escape_unsafe_attributes
            )
            tag_str = f"<{repaired_content}>"

            # Extract tag name to track
            parts = tag_content.split(None, 1)
            tag_name = parts[0] if parts else tag_content

            # Track in stack
            self.tag_stack.append((tag_name, tag_name.lower()))
            self._check_max_depth()

            return tag_str

        return tag_str
