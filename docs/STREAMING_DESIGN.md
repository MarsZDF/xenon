# Streaming XML Repair - Design Document

## Problem Statement

**User**: Alex (AI Engineer)
**Use Case**: RAG pipeline with streaming LLM responses

**Current bottleneck:**
```python
# Today - forces buffering entire response
completion = ""
for chunk in llm.stream():
    completion += chunk

repaired = repair_xml(completion)  # ❌ All latency added at end
return repaired
```

**Desired:**
```python
# Tomorrow - zero latency addition
for chunk in llm.stream():
    for safe_chunk in streaming_repair.feed(chunk):
        yield safe_chunk  # ✅ Stream through immediately
```

## Architecture

### State Machine

```
┌─────────────┐
│   INITIAL   │ Buffer until first '<'
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  IN_TEXT    │ Accumulate text, escape entities
└──────┬──────┘
       │ '<' found
       ▼
┌─────────────┐
│   IN_TAG    │ Buffer until '>' or '/>'
└──────┬──────┘
       │ '>' found
       ▼
┌─────────────┐
│  TAG_COMPLETE│ Repair & yield, update stack
└──────┬──────┘
       │
       └──────► Back to IN_TEXT or IN_TAG
```

### What Can Stream Immediately

✅ **Safe to yield:**
- Complete tags: `<item>value</item>`
- Self-closing tags: `<br/>`
- Text content between complete tags
- Processing instructions: `<?xml version="1.0"?>`
- Comments: `<!-- comment -->`
- CDATA sections: `<![CDATA[...]]>`

❌ **Must buffer:**
- Incomplete tags: `<user name="jo` (wait for `>`)
- Last N tokens (might be incomplete at EOF)
- Conversational prefix (until first `<` found)

### Implementation Complexity

**Low complexity (can reuse existing):**
- Attribute quoting: `repair_attributes()` ✓
- Entity escaping: `escape_entities()` ✓
- Tag sanitization: `sanitize_tag_name()` ✓

**Medium complexity (new logic):**
- State machine for streaming
- Buffer management
- Split detection (tag boundaries)

**High complexity (fundamental limitations):**
- Typo detection: Can't use Levenshtein until we see closing tag
- Multiple root detection: Can't know if there are multiple until end
- Conversational fluff: Must buffer initial chunks

## API Design

### Option 1: Generator-based (Simple)

```python
from xenon.streaming import StreamingXMLRepair

repairer = StreamingXMLRepair()

for chunk in llm_stream():
    for safe_xml in repairer.feed(chunk):
        yield safe_xml

# Signal end of stream
for final_xml in repairer.finalize():
    yield final_xml
```

### Option 2: Context Manager (Cleaner)

```python
from xenon.streaming import StreamingXMLRepair

with StreamingXMLRepair() as repairer:
    for chunk in llm_stream():
        yield from repairer.feed(chunk)
    # finalize() called automatically
```

### Option 3: Async Support

```python
async def stream_repair(llm_stream):
    async with StreamingXMLRepair() as repairer:
        async for chunk in llm_stream:
            async for safe_xml in repairer.feed(chunk):
                yield safe_xml
```

## Limitations vs Batch Mode

| Feature | Batch Mode | Streaming Mode |
|---------|------------|----------------|
| Attribute quoting | ✅ | ✅ |
| Entity escaping | ✅ | ✅ |
| Truncation repair | ✅ | ✅ |
| Conversational fluff | ✅ | ⚠️ Buffers until first tag |
| Tag typo detection | ✅ | ❌ Greedy, no Levenshtein |
| Multiple root wrapping | ✅ | ⚠️ Only at finalize() |
| Namespace injection | ✅ | ⚠️ Only on first tag |

## Implementation Plan

### Phase 1: Core Streaming (v0.7.0)
- `StreamingXMLRepair` class
- State machine implementation
- Tag completion detection
- Attribute repair (reuse existing)
- Entity escaping (reuse existing)
- Basic tests (200+ test cases)

### Phase 2: Edge Cases (v0.7.1)
- CDATA handling
- Comment handling
- Processing instruction handling
- Split boundary detection
- Stress tests with various chunk sizes

### Phase 3: Advanced Features (v0.7.2)
- Async support
- Configuration options
- Performance optimization
- Benchmark suite

## Estimated Effort

**Development Time:** 6-8 hours
- Core streaming logic: 3 hours
- Integration with existing repair: 2 hours
- Edge case handling: 1 hour
- Testing: 2-3 hours

**Lines of Code:**
- `src/xenon/streaming.py`: ~400 lines
- `tests/test_streaming.py`: ~600 lines
- Documentation: ~200 lines

**Complexity Rating:** 7/10
- Not trivial, but feasible
- Can reuse 60% of existing repair logic
- Main challenge is state management

## Example Implementation Sketch

```python
class StreamingXMLRepair:
    def __init__(self, **config):
        self.buffer = ""
        self.state = State.INITIAL
        self.tag_stack = []
        self.config = config
        self.saw_first_tag = False

    def feed(self, chunk: str) -> Iterator[str]:
        """Feed chunk, yield safe XML."""
        self.buffer += chunk

        while True:
            if self.state == State.INITIAL:
                # Strip conversational fluff
                idx = self.buffer.find('<')
                if idx == -1:
                    # No tag yet, keep buffering
                    break
                # Found first tag, discard prefix
                self.buffer = self.buffer[idx:]
                self.state = State.IN_TEXT

            elif self.state == State.IN_TEXT:
                idx = self.buffer.find('<')
                if idx == -1:
                    # No tag found, might be at boundary
                    if len(self.buffer) > MAX_TEXT_BUFFER:
                        # Safe to yield most of it
                        text = self.buffer[:-SAFETY_MARGIN]
                        self.buffer = self.buffer[-SAFETY_MARGIN:]
                        yield self.escape_entities(text)
                    break

                # Yield text before tag
                if idx > 0:
                    yield self.escape_entities(self.buffer[:idx])
                    self.buffer = self.buffer[idx:]

                self.state = State.IN_TAG

            elif self.state == State.IN_TAG:
                # Look for tag end
                end = self.buffer.find('>')
                if end == -1:
                    # Incomplete tag
                    break

                # Complete tag found
                tag_str = self.buffer[:end+1]
                self.buffer = self.buffer[end+1:]

                # Repair and yield
                repaired = self.repair_tag(tag_str)
                yield repaired

                self.state = State.IN_TEXT

    def finalize(self) -> Iterator[str]:
        """Close open tags."""
        # Handle remaining buffer
        if self.buffer:
            if self.state == State.IN_TAG:
                yield self.repair_incomplete_tag(self.buffer)
            else:
                yield self.escape_entities(self.buffer)

        # Close unclosed tags
        while self.tag_stack:
            tag = self.tag_stack.pop()
            yield f"</{tag}>"
```

## Decision: Include in v0.7.0?

**Recommendation: YES ✅**

**Reasons:**
1. **High impact**: Solves real production pain point
2. **Feasible scope**: 6-8 hours for experienced dev
3. **Reuses existing code**: 60% of repair logic already exists
4. **Market differentiator**: No other XML repair library does this
5. **Growing demand**: Streaming is the future of LLM apps

**Trade-offs accepted:**
- Won't fix typos as well as batch mode (acceptable)
- Requires finalize() call (good API design)
- Slightly more complex for users (but better perf)

## Next Steps

1. ✅ Create design document (this file)
2. ⏳ Get user feedback on API design
3. ⏳ Implement `StreamingXMLRepair` class
4. ⏳ Add comprehensive tests
5. ⏳ Update documentation
6. ⏳ Add to v0.7.0 roadmap

---

**Status**: Draft - Awaiting approval
**Target Release**: v0.7.0
**Priority**: High
**Difficulty**: Medium (7/10)
