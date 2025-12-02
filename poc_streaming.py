#!/usr/bin/env python3
"""
Proof of concept for streaming XML repair.
This validates the design is feasible before full implementation.
"""

from enum import Enum
from typing import Iterator


class State(Enum):
    INITIAL = "initial"  # Before first tag
    IN_TEXT = "in_text"  # Between tags
    IN_TAG = "in_tag"  # Inside a tag


class StreamingXMLRepairPOC:
    """Minimal proof-of-concept for streaming XML repair."""

    def __init__(self):
        self.buffer = ""
        self.state = State.INITIAL
        self.tag_stack = []
        self.saw_first_tag = False

    def feed(self, chunk: str) -> Iterator[str]:
        """Feed a chunk of XML, yield safe repaired pieces."""
        self.buffer += chunk

        while True:
            if self.state == State.INITIAL:
                # Strip conversational fluff - buffer until first '<'
                idx = self.buffer.find("<")
                if idx == -1:
                    # No tag yet, keep buffering (don't yield junk)
                    break

                # Found first tag, discard everything before it
                if idx > 0:
                    # Optionally log what we stripped
                    pass
                self.buffer = self.buffer[idx:]
                self.state = State.IN_TEXT
                self.saw_first_tag = True

            elif self.state == State.IN_TEXT:
                # Look for next tag
                idx = self.buffer.find("<")
                if idx == -1:
                    # No tag found - might be at chunk boundary
                    # Keep a safety margin (last few chars might be "<" arriving)
                    if len(self.buffer) > 10:
                        # Safe to yield most of it
                        text = self.buffer[:-5]
                        self.buffer = self.buffer[-5:]
                        if text:
                            yield self._escape_entities(text)
                    break

                # Yield text before tag
                if idx > 0:
                    text = self.buffer[:idx]
                    yield self._escape_entities(text)
                    self.buffer = self.buffer[idx:]

                self.state = State.IN_TAG

            elif self.state == State.IN_TAG:
                # Look for tag end
                end = self.buffer.find(">")
                if end == -1:
                    # Incomplete tag - need more input
                    break

                # Complete tag found
                tag_str = self.buffer[: end + 1]
                self.buffer = self.buffer[end + 1 :]

                # Repair and yield
                repaired = self._repair_tag(tag_str)
                if repaired:
                    yield repaired

                self.state = State.IN_TEXT

    def finalize(self) -> Iterator[str]:
        """Call when stream ends - close open tags."""
        # Handle remaining buffer
        if self.buffer:
            if self.state == State.IN_TAG:
                # Incomplete tag - try to repair it
                repaired = self._repair_incomplete_tag(self.buffer)
                if repaired:
                    yield repaired
            elif self.state == State.IN_TEXT:
                # Text content
                if self.buffer.strip():
                    yield self._escape_entities(self.buffer)

        # Close unclosed tags
        while self.tag_stack:
            tag = self.tag_stack.pop()
            yield f"</{tag}>"

    def _repair_tag(self, tag_str: str) -> str:
        """Repair a complete tag."""
        tag_str = tag_str.strip()

        # Skip special tags
        if tag_str.startswith("<?") or tag_str.startswith("<!"):
            return tag_str

        # Self-closing tag
        if tag_str.endswith("/>"):
            # Could add attribute quoting here
            return tag_str

        # Closing tag
        if tag_str.startswith("</"):
            tag_name = tag_str[2:-1].strip()
            # Pop from stack
            if self.tag_stack and self.tag_stack[-1] == tag_name:
                self.tag_stack.pop()
            return tag_str

        # Opening tag - extract name and track in stack
        tag_content = tag_str[1:-1].strip()
        parts = tag_content.split(None, 1)
        tag_name = parts[0] if parts else tag_content

        self.tag_stack.append(tag_name)

        # Could add attribute quoting here
        return tag_str

    def _repair_incomplete_tag(self, tag_str: str) -> str:
        """Repair an incomplete tag (at EOF)."""
        tag_str = tag_str.strip()

        # If it looks like an opening tag
        if tag_str.startswith("<") and not tag_str.startswith("</"):
            # Close the tag
            if not tag_str.endswith(">"):
                tag_str += ">"

            # Extract tag name
            tag_content = tag_str[1:-1].strip()
            parts = tag_content.split(None, 1)
            tag_name = parts[0] if parts else tag_content

            self.tag_stack.append(tag_name)

        return tag_str

    def _escape_entities(self, text: str) -> str:
        """Basic entity escaping."""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text


# Demo
if __name__ == "__main__":
    print("=== Streaming XML Repair POC ===\n")

    # Simulate LLM streaming chunks
    llm_chunks = [
        "Sure, here's the",
        " XML you requested:\n\n",
        "<root>",
        "<user name=",
        'john>',
        "<email>john@",
        "example.com</",
        "email>",
        "</user>",
        "<user name=jane>",
        "<email>jane@ex",
    ]  # Truncated!

    print("📥 Simulating LLM stream with truncation:\n")

    repairer = StreamingXMLRepairPOC()

    print("📤 Yielding repaired chunks:\n")
    for i, chunk in enumerate(llm_chunks):
        print(f"  Chunk {i+1}: {chunk!r}")
        for safe_xml in repairer.feed(chunk):
            print(f"    ✓ Yield: {safe_xml!r}")

    print("\n🔚 Finalizing (closing open tags):\n")
    for final_xml in repairer.finalize():
        print(f"    ✓ Yield: {final_xml!r}")

    print("\n" + "=" * 50)
    print("✅ POC demonstrates streaming is feasible!")
    print("=" * 50)
