import re
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Match, Optional, Tuple

from .attribute_parser import fix_malformed_attributes
from .config import RepairFlags, SecurityFlags, XMLRepairConfig
from .preprocessor import XMLPreprocessor
from .reporting import RepairReport, RepairType
from .security import XMLSecurityFilter, check_max_depth

if TYPE_CHECKING:
    from .audit import AuditLogger
    from .reporting import RepairReport
    from .trust import TrustLevel


class XMLToken:
    def __init__(self, token_type: str, content: str, position: int = 0):
        self.type = token_type
        self.content = content
        self.position = position


class XMLParseState:
    def __init__(self) -> None:
        self.position = 0
        self.stack: List[str] = []
        self.tokens: List[XMLToken] = []
        self.in_tag = False
        self.current_tag = ""
        self.in_quotes = False
        self.quote_char = ""


class XMLRepairEngine:
    # Common namespace URIs for auto-injection
    COMMON_NAMESPACES: ClassVar[Dict[str, str]] = {
        "soap": "http://schemas.xmlsoap.org/soap/envelope/",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsd": "http://www.w3.org/2001/XMLSchema",
        "xs": "http://www.w3.org/2001/XMLSchema",
    }

    def __init__(
        self,
        config: Optional[XMLRepairConfig] = None,
        # Backward compatible parameters
        match_threshold: int = 2,
        strip_dangerous_pis: bool = False,
        strip_external_entities: bool = False,
        strip_dangerous_tags: bool = False,
        escape_unsafe_attributes: bool = False,
        wrap_multiple_roots: bool = False,
        sanitize_invalid_tags: bool = False,
        fix_namespace_syntax: bool = False,
        auto_wrap_cdata: bool = False,
        max_depth: Optional[int] = None,
        schema_content: Optional[str] = None,
        audit_logger: Optional["AuditLogger"] = None,
        trust_level: Optional[str] = None,
    ):
        """
        Initialize XML repair engine.

        You can pass either a XMLRepairConfig object (recommended) or individual
        boolean parameters (backward compatible).

        Args:
            config: XMLRepairConfig instance (optional, recommended for clarity)
            match_threshold: Maximum Levenshtein distance to consider tags as matching.
                            Default is 2 (allows up to 2 character differences).
            strip_dangerous_pis: Strip processing instructions that look like code (php, asp, jsp).
                                Default False for backward compatibility.
            strip_external_entities: Strip external entity declarations (XXE prevention).
                                    Default False for backward compatibility.
            strip_dangerous_tags: Strip potentially dangerous tags (script, iframe, object, embed).
                                 Default False for backward compatibility.
            escape_unsafe_attributes: Aggressively escape attribute values to prevent XSS.
                                     Default False for backward compatibility.
            wrap_multiple_roots: Wrap multiple root elements in synthetic <document> root.
                                Default False for backward compatibility.
            sanitize_invalid_tags: Fix invalid XML tag names (e.g., <123> → <tag_123>).
                                  Default False for backward compatibility.
            fix_namespace_syntax: Fix invalid namespace syntax (e.g., <bad::ns> → <bad_ns>).
                                 Default False for backward compatibility.
            auto_wrap_cdata: Automatically wrap code-like content in CDATA sections.
                            Detects tags like <code>, <script>, <pre> with special characters.
                            Default False for backward compatibility.
            max_depth: Maximum XML nesting depth allowed. Prevents DoS attacks via deeply nested XML.
                      None = unlimited (default for backward compatibility).
                      Recommended: 1000 for untrusted input, 10000 for internal use.
            schema_content: Content of the schema (XSD or DTD) for post-repair validation.
            trust_level: The trust level used for configuration (e.g., "untrusted", "internal").
                        Used primarily for audit logging.

        Examples:
            >>> # Using config object (recommended)
            >>> from xenon.config import XMLRepairConfig, SecurityFlags, RepairFlags
            >>> config = XMLRepairConfig(
            ...     security=SecurityFlags.STRIP_DANGEROUS_PIS | SecurityFlags.STRIP_EXTERNAL_ENTITIES,
            ...     repair=RepairFlags.SANITIZE_INVALID_TAGS
            ... )
            >>> engine = XMLRepairEngine(config)

            >>> # Using individual parameters (backward compatible)
            >>> engine = XMLRepairEngine(strip_dangerous_pis=True, sanitize_invalid_tags=True)
        """
        # Create config from parameters if not provided
        if config is None:
            config = XMLRepairConfig.from_booleans(
                match_threshold=match_threshold,
                strip_dangerous_pis=strip_dangerous_pis,
                strip_external_entities=strip_external_entities,
                strip_dangerous_tags=strip_dangerous_tags,
                escape_unsafe_attributes=escape_unsafe_attributes,
                wrap_multiple_roots=wrap_multiple_roots,
                sanitize_invalid_tags=sanitize_invalid_tags,
                fix_namespace_syntax=fix_namespace_syntax,
                auto_wrap_cdata=auto_wrap_cdata,
                schema_content=schema_content,
                audit_logger=audit_logger,
                trust_level=trust_level,
            )

        self.config = config
        self.state = XMLParseState()
        self.max_depth = max_depth

        # Initialize components
        self.preprocessor = XMLPreprocessor(config)
        self.security_filter = XMLSecurityFilter(config)
        self.audit_logger = config.audit_logger

        # Backward compatibility properties
        self.match_threshold = config.match_threshold
        self.strip_dangerous_pis = config.has_security_feature(SecurityFlags.STRIP_DANGEROUS_PIS)
        self.strip_external_entities = config.has_security_feature(
            SecurityFlags.STRIP_EXTERNAL_ENTITIES
        )
        self.strip_dangerous_tags = config.has_security_feature(SecurityFlags.STRIP_DANGEROUS_TAGS)
        self.escape_unsafe_attributes = config.has_security_feature(
            SecurityFlags.ESCAPE_UNSAFE_ATTRIBUTES
        )
        self.wrap_multiple_roots = config.has_repair_feature(RepairFlags.WRAP_MULTIPLE_ROOTS)
        self.sanitize_invalid_tags = config.has_repair_feature(RepairFlags.SANITIZE_INVALID_TAGS)
        self.fix_namespace_syntax = config.has_repair_feature(RepairFlags.FIX_NAMESPACE_SYNTAX)
        self.auto_wrap_cdata = config.has_repair_feature(RepairFlags.AUTO_WRAP_CDATA)
        self.schema_content = config.schema_content

    @classmethod
    def from_trust_level(
        cls, trust: "TrustLevel", audit_logger: Optional["AuditLogger"] = None
    ) -> "XMLRepairEngine":
        """
        Create XMLRepairEngine configured for a specific trust level.

        This factory method creates an engine with security settings appropriate
        for the given trust level. It's the recommended way to create engines
        when you want trust-based security presets.

        Args:
            trust: TrustLevel indicating the security posture to use
            audit_logger: Optional AuditLogger for security auditing

        Returns:
            XMLRepairEngine configured with appropriate security settings

        Examples:
            >>> from xenon import XMLRepairEngine, TrustLevel
            >>>
            >>> # Maximum security for untrusted input
            >>> engine = XMLRepairEngine.from_trust_level(TrustLevel.UNTRUSTED)
            >>> engine.strip_dangerous_pis
            True
            >>>
            >>> # No security overhead for trusted input
            >>> engine = XMLRepairEngine.from_trust_level(TrustLevel.TRUSTED)
            >>> engine.strip_dangerous_pis
            False
        """
        from xenon.trust import get_security_config

        config_obj = get_security_config(trust, audit_logger=audit_logger)

        return cls(
            strip_dangerous_pis=config_obj.strip_dangerous_pis,
            strip_external_entities=config_obj.strip_external_entities,
            strip_dangerous_tags=config_obj.strip_dangerous_tags,
            escape_unsafe_attributes=config_obj.escape_unsafe_attributes,
            max_depth=config_obj.max_depth,
            schema_content=None,  # from_trust_level doesn't provide a schema content by default
            audit_logger=config_obj.audit_logger,
            trust_level=trust.value,
        )

    def is_dangerous_pi(self, pi_content: str) -> bool:
        """
        Check if processing instruction contains dangerous code patterns.

        Args:
            pi_content: The PI content (e.g., "<?php echo 'hi'; ?>")

        Returns:
            True if PI looks like executable code
        """
        return self.security_filter.is_dangerous_pi(pi_content)

    def is_dangerous_tag(self, tag_name: str) -> bool:
        """
        Check if tag name is potentially dangerous for XSS.

        Args:
            tag_name: The tag name to check

        Returns:
            True if tag is in dangerous list
        """
        return self.security_filter.is_dangerous_tag(tag_name)

    def contains_external_entity(self, doctype: str) -> bool:
        """
        Check if DOCTYPE contains external entity declarations.

        Args:
            doctype: DOCTYPE content to check

        Returns:
            True if contains SYSTEM or PUBLIC entity declarations
        """
        return self.security_filter.contains_external_entity(doctype)

    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings.

        Uses dynamic programming. Fast for short strings (typical tag names).
        Time complexity: O(m*n) where m, n are string lengths.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Minimum number of edits (insertions, deletions, substitutions) needed
        """
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        # Use rolling array optimization to save memory
        previous_row = list(range(len(s2) + 1))

        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Cost of insertions, deletions, or substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def find_best_matching_tag(
        self, closing_tag: str, tag_stack: List[Tuple[str, str]]
    ) -> Optional[Tuple[int, str, int]]:
        """
        Find the best matching tag in the stack for a closing tag.

        Uses Levenshtein distance to find tags that are "close enough".

        Args:
            closing_tag: The closing tag name (lowercase)
            tag_stack: Stack of (original_case, lowercase) tag tuples

        Returns:
            Tuple of (stack_index, original_tag_name, distance) or None if no good match
        """
        if not tag_stack:
            return None

        best_match = None
        best_distance = float("inf")
        best_index = -1

        # Search from top of stack (most recent) to bottom
        for i in range(len(tag_stack) - 1, -1, -1):
            original_tag, tag_lower = tag_stack[i]

            # Exact match (case-insensitive) - return immediately
            if tag_lower == closing_tag:
                return (i, original_tag, 0)

            # Calculate similarity
            distance = self.levenshtein_distance(tag_lower, closing_tag)

            # Keep track of best match
            if distance < best_distance:
                best_distance = distance
                best_match = original_tag
                best_index = i

        # Only return match if within threshold
        if best_distance <= self.match_threshold and best_match is not None:
            return (best_index, best_match, int(best_distance))

        return None

    def extract_xml_content(self, text: str) -> str:
        text = text.strip()

        # Security: Strip DOCTYPE declarations if enabled
        text = self.security_filter.strip_external_entities_from_text(text)

        # Handle XML declarations and processing instructions
        xml_start = -1

        # Look for XML declaration first
        if text.startswith("<?xml"):
            xml_start = 0
        else:
            # Find first < that starts XML-like content
            for i, char in enumerate(text):
                if char == "<" and i + 1 < len(text):
                    next_char = text[i + 1]
                    # Valid XML tag starts: <letter, <_, <:, </, <?, or <!
                    if next_char.isalpha() or next_char in "_:/!?":
                        xml_start = i
                        break

        if xml_start == -1:
            # No XML-like content found, return as-is
            return text

        # For conversational fluff detection, we need to be smarter about where XML ends
        # Look for patterns that suggest end of XML and start of conversation
        xml_end = len(text)

        # Common patterns that indicate end of XML
        end_patterns = [
            r"\s+(Hope\s+this\s+helps|Let\s+me\s+know|That\s+should)",
            r"\s+(Please\s+let\s+me\s+know|Is\s+this\s+what)",
            r"\s*\n\s*[A-Z][^<]*$",  # Newline followed by sentence not containing <
        ]

        # Optimization: Only search in the last 2000 characters for large inputs
        # Conversational fluff at the end rarely exceeds this length
        search_text = text[xml_start:]
        search_offset = xml_start

        if len(search_text) > 2000:
            search_offset = xml_start + len(search_text) - 2000
            search_text = text[search_offset:]

        # Only trim if we find clear conversational patterns
        for pattern in end_patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                potential_end = search_offset + match.start()
                # Make sure we end at a > if possible
                for i in range(potential_end - 1, xml_start, -1):
                    if text[i] == ">":
                        xml_end = i + 1
                        break
                break

        return text[xml_start:xml_end]

    def extract_namespaces(self, xml: str) -> Dict[str, str]:
        """
        Extract namespace prefixes used in XML.

        Returns dict mapping prefix to namespace URI for known prefixes.
        """
        import re

        namespaces = {}

        # Find all namespace prefixes (prefix:tagname pattern)
        prefix_pattern = r"</?([a-zA-Z][a-zA-Z0-9]*):([a-zA-Z][a-zA-Z0-9]*)"
        matches = re.findall(prefix_pattern, xml)

        for prefix, _ in matches:
            if prefix in self.COMMON_NAMESPACES and prefix not in namespaces:
                namespaces[prefix] = self.COMMON_NAMESPACES[prefix]

        return namespaces

    def inject_namespace_declarations(self, root_tag: str, namespaces: Dict[str, str]) -> str:
        """
        Inject namespace declarations into root tag.

        Args:
            root_tag: The root tag content (e.g., "root" or "root attr='val'")
            namespaces: Dict mapping prefix to namespace URI

        Returns:
            Updated root tag with xmlns declarations
        """
        if not namespaces:
            return root_tag

        # Build xmlns declarations
        xmlns_decls = []
        for prefix, uri in namespaces.items():
            xmlns_decls.append(f'xmlns:{prefix}="{uri}"')

        # Insert xmlns after tag name
        parts = root_tag.split(None, 1)
        tag_name = parts[0]

        if len(parts) > 1:
            # Has attributes, insert xmlns before them
            return f"{tag_name} {' '.join(xmlns_decls)} {parts[1]}"
        else:
            # No attributes, just add xmlns
            return f"{tag_name} {' '.join(xmlns_decls)}"

    def escape_entities(self, text: str, aggressive_escape: bool = False) -> Tuple[str, bool]:
        """
        Escape special XML characters in text content.

        Escapes &, <, and > but avoids double-escaping already valid entity references.
        """
        original_text = text
        # Pattern to match valid entity references
        # Matches: &lt; &gt; &amp; &quot; &apos; &#digits; &#xhex;
        import re

        valid_entity_pattern = r"&(?:lt|gt|amp|quot|apos|#\d+|#x[0-9a-fA-F]+);"

        # Find all valid entities and temporarily replace them with placeholders
        entities = []

        def save_entity(match: Match[str]) -> str:
            entities.append(match.group(0))
            return f"\x00ENTITY{len(entities) - 1}\x00"

        text = re.sub(valid_entity_pattern, save_entity, text)

        # Now escape the remaining special characters
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")

        if aggressive_escape:
            text = text.replace("'", "&apos;")
            text = text.replace("/", "&#x2F;")
            text = text.replace(" ", "&#x20;")
            text = text.replace("\t", "&#x09;")
            text = text.replace("\n", "&#x0A;")
            text = text.replace("\r", "&#x0D;")

        # Restore the valid entities
        for i, entity in enumerate(entities):
            text = text.replace(f"\x00ENTITY{i}\x00", entity)

        return text, text != original_text

    def tokenize(self, xml_string: str) -> List[XMLToken]:
        tokens = []
        i = 0

        while i < len(xml_string):
            if xml_string[i] == "<":
                # Check if this is actually a tag or just < in text
                if i + 1 >= len(xml_string):
                    # Just a < at end, treat as text
                    tokens.append(XMLToken("text", "<", i))
                    i += 1
                    continue

                next_char = xml_string[i + 1]
                # Valid tag start characters: letters, _, :, /, ?, !
                if not (next_char.isalpha() or next_char in "_:/!?"):
                    # Not a tag start, treat as text content
                    text_start = i

                    # Optimization: Use find to skip ahead
                    while i < len(xml_string):
                        next_lt = xml_string.find("<", i + 1)
                        if next_lt == -1:
                            i = len(xml_string)
                            break

                        # Check if this < starts a tag
                        if next_lt + 1 < len(xml_string):
                            nc = xml_string[next_lt + 1]
                            if nc.isalpha() or nc in "_:/!?":
                                i = next_lt
                                break
                        i = next_lt + 1  # This < was text, continue searching

                    text_content = xml_string[text_start:i]
                    if text_content:
                        tokens.append(XMLToken("text", text_content, text_start))
                    continue

                # Handle XML declaration/processing instruction
                if xml_string[i : i + 5] == "<?xml" or xml_string[i : i + 2] == "<?":
                    # Find end of processing instruction
                    pi_end = xml_string.find("?>", i + 2)
                    if pi_end != -1:
                        pi_end += 2
                        pi_content = xml_string[i:pi_end]
                        tokens.append(XMLToken("processing_instruction", pi_content, i))
                        i = pi_end
                        continue
                    else:
                        # Malformed PI, treat as incomplete tag
                        tokens.append(XMLToken("incomplete_tag", xml_string[i + 1 :], i))
                        break

                # Handle DOCTYPE, comments, and CDATA
                if xml_string[i : i + 2] == "<!":
                    # Check for comments <!--
                    if xml_string[i : i + 4] == "<!--":
                        comment_end = xml_string.find("-->", i + 4)
                        if comment_end != -1:
                            comment_end += 3
                            comment_content = xml_string[i:comment_end]
                            tokens.append(XMLToken("comment", comment_content, i))
                            i = comment_end
                            continue
                    # Check for CDATA <![CDATA[
                    elif xml_string[i : i + 9] == "<![CDATA[":
                        cdata_end = xml_string.find("]]>", i + 9)
                        if cdata_end != -1:
                            cdata_end += 3
                            cdata_content = xml_string[i:cdata_end]
                            tokens.append(XMLToken("cdata", cdata_content, i))
                            i = cdata_end
                            continue
                    # Check for DOCTYPE
                    elif xml_string[i : i + 9].upper() == "<!DOCTYPE":
                        # Find end of DOCTYPE (may include internal subset with [])
                        doctype_end = i + 9
                        in_bracket = False
                        while doctype_end < len(xml_string):
                            if xml_string[doctype_end] == "[":
                                in_bracket = True
                            elif xml_string[doctype_end] == "]":
                                in_bracket = False
                            elif xml_string[doctype_end] == ">" and not in_bracket:
                                doctype_end += 1
                                break
                            doctype_end += 1
                        doctype_content = xml_string[i:doctype_end]
                        tokens.append(XMLToken("doctype", doctype_content, i))
                        i = doctype_end
                        continue

                # Start of regular tag
                tag_end = i + 1
                in_quotes = False
                quote_char = None

                while tag_end < len(xml_string):
                    char = xml_string[tag_end]

                    if not in_quotes:
                        if char in ['"', "'"]:
                            in_quotes = True
                            quote_char = char
                        elif char == ">":
                            tag_end += 1
                            break
                    else:
                        if char == quote_char:
                            in_quotes = False
                            quote_char = None

                    tag_end += 1

                tag_content = xml_string[i:tag_end]

                if tag_content.endswith(">"):
                    # Complete tag
                    if tag_content.startswith("</"):
                        # Closing tag
                        tag_name = tag_content[2:-1].strip()
                        tokens.append(XMLToken("close_tag", tag_name, i))
                    elif tag_content.endswith("/>"):
                        # Self-closing tag
                        tag_content_inner = tag_content[1:-2].strip()
                        tokens.append(XMLToken("self_closing_tag", tag_content_inner, i))
                    else:
                        # Opening tag
                        tag_content_inner = tag_content[1:-1].strip()
                        tag_name = (
                            tag_content_inner.split()[0]
                            if tag_content_inner.split()
                            else tag_content_inner
                        )
                        tokens.append(XMLToken("open_tag", tag_content_inner, i))
                        tokens.append(XMLToken("tag_name", tag_name, i))
                else:
                    # Incomplete tag (truncated) - include everything to end
                    tag_content_inner = xml_string[i + 1 :].strip()
                    if tag_content_inner:
                        tag_name = (
                            tag_content_inner.split()[0]
                            if tag_content_inner.split()
                            else tag_content_inner
                        )
                        tokens.append(XMLToken("incomplete_tag", tag_content_inner, i))
                        tokens.append(XMLToken("tag_name", tag_name, i))
                    break  # End of input, truncated

                i = tag_end
            else:
                # Text content
                text_start = i
                # Optimization: Use find instead of loop
                next_lt = xml_string.find("<", i)
                i = len(xml_string) if next_lt == -1 else next_lt

                text_content = xml_string[text_start:i]
                if text_content.strip():
                    # Don't escape here, do it during output
                    tokens.append(XMLToken("text", text_content, text_start))
                elif text_content:  # Preserve whitespace
                    tokens.append(XMLToken("whitespace", text_content, text_start))

        return tokens

    def repair_xml(self, xml_string: str) -> Tuple[str, "RepairReport"]:
        # Instantiate report object to track repairs
        report = RepairReport(
            original_xml=xml_string,
            repaired_xml="",  # This will be set at the end
        )

        # Step 1: Preprocess invalid tag names & namespace syntax (single pass)
        # This must happen before extract_xml_content so the tokenizer can recognize the tags
        xml_string, preprocess_actions = self.preprocessor.preprocess(xml_string)
        if preprocess_actions:
            report.actions.extend(preprocess_actions)

        # Step 2: Extract XML content from conversational fluff
        cleaned_xml = self.extract_xml_content(xml_string)
        if len(cleaned_xml) < len(xml_string):
            report.add_action(
                RepairType.CONVERSATIONAL_FLUFF,
                "Removed conversational fluff from document",
            )

        # Step 1.6: Extract namespaces before tokenization
        namespaces = self.extract_namespaces(cleaned_xml)

        # Step 2: Tokenize and parse with stack-based approach
        tokens = self.tokenize(cleaned_xml)

        # Step 3: Rebuild XML with proper closing tags
        result = []
        tag_stack = []  # Stack stores tuples of (original_case, lowercase) for case-insensitive matching
        dangerous_tag_stack = []  # Track dangerous tags to skip their content
        first_open_tag = True  # Track first tag for namespace injection
        text_buffer: List[str] = []  # Buffer for collecting text content in CDATA candidate tags
        in_cdata_candidate = False  # Are we currently inside a CDATA candidate tag?
        i = 0

        def flush_text_buffer() -> None:
            """Flush buffered text content, wrapping in CDATA if needed."""
            nonlocal text_buffer, in_cdata_candidate, result
            if not text_buffer:
                return

            # Combine all buffered text
            combined_text = "".join(text_buffer)
            text_buffer = []

            # Check if we should wrap in CDATA
            if (
                in_cdata_candidate
                and self.auto_wrap_cdata
                and self.preprocessor.needs_cdata_wrapping(combined_text)
            ):
                result.append(self.preprocessor.wrap_cdata(combined_text))
            else:
                # Escape entities normally
                escaped_text, _ = self.escape_entities(
                    combined_text, aggressive_escape=self.escape_unsafe_attributes
                )
                result.append(escaped_text)

        while i < len(tokens):
            token = tokens[i]

            if token.type == "processing_instruction":
                # Security: Skip dangerous processing instructions if enabled
                if self.security_filter.should_strip_dangerous_pi(token.content):
                    report.add_action(
                        RepairType.DANGEROUS_PI_STRIPPED,
                        "Removed dangerous processing instruction",
                        before=token.content,
                    )
                    # Skip this token - don't add to output
                    i += 1
                    continue
                result.append(token.content)
            elif token.type == "open_tag":
                # Flush any buffered text before opening a new tag
                flush_text_buffer()

                # Extract tag name for stack (store both original and lowercase)
                tag_name = None
                if i + 1 < len(tokens) and tokens[i + 1].type == "tag_name":
                    tag_name = tokens[i + 1].content

                # Security: Skip dangerous tags if enabled
                if tag_name and self.security_filter.should_strip_dangerous_tag(tag_name):
                    report.add_action(
                        RepairType.DANGEROUS_TAG_STRIPPED,
                        f"Removed dangerous tag <{tag_name}> but preserved its content",
                        before=f"<{token.content}>",
                    )
                    # Skip this tag but process content
                    dangerous_tag_stack.append((tag_name, tag_name.lower()))
                    if i + 1 < len(tokens) and tokens[i + 1].type == "tag_name":
                        i += 1  # Skip the tag_name token
                    i += 1
                    continue

                # Fix attributes and report
                fixed_content, attr_actions = fix_malformed_attributes(
                    token.content, aggressive_escape=self.escape_unsafe_attributes
                )
                if attr_actions:
                    report.actions.extend(attr_actions)

                # Inject namespaces into first open tag (root element)
                if first_open_tag and namespaces:
                    updated_content = self.inject_namespace_declarations(fixed_content, namespaces)
                    result.append(f"<{updated_content}>")
                    first_open_tag = False
                else:
                    result.append(f"<{fixed_content}>")
                    first_open_tag = False

                if tag_name:
                    tag_stack.append((tag_name, tag_name.lower()))
                    check_max_depth(len(tag_stack), self.max_depth)
                    # Check if this is a CDATA candidate tag
                    in_cdata_candidate = self.preprocessor.is_cdata_candidate(tag_name)
                    i += 1  # Skip the tag_name token
                    # Don't fall through to i += 1 at end of loop - we already incremented
            elif token.type == "close_tag":
                # Flush any buffered text before closing tag
                flush_text_buffer()
                in_cdata_candidate = False  # Reset flag when leaving the tag

                # Mismatched tag detection with similarity matching
                closing_tag_lower = token.content.lower()

                # Security: Check if this is closing a dangerous tag
                handled_dangerous = False
                if self.strip_dangerous_tags and dangerous_tag_stack:
                    # Check if this closes a dangerous tag
                    for idx, (_dtag, dtag_lower) in enumerate(dangerous_tag_stack):
                        if dtag_lower == closing_tag_lower:
                            # Remove from dangerous stack and skip output
                            dangerous_tag_stack.pop(idx)
                            handled_dangerous = True
                            break

                # If we handled a dangerous tag, skip the rest of close_tag processing
                if handled_dangerous:
                    i += 1
                    continue

                # Try to find best matching tag in stack
                match_result = self.find_best_matching_tag(closing_tag_lower, tag_stack)

                if match_result:
                    stack_index, _matched_tag, distance = match_result

                    # Close the matched tag and all tags opened after it
                    # (They were left unclosed due to the mismatch)
                    tags_to_close = []
                    while len(tag_stack) > stack_index:
                        tags_to_close.append(tag_stack.pop()[0])

                    if distance > 0:
                        report.add_action(
                            RepairType.TAG_TYPO,
                            f"Corrected closing tag typo '</{token.content}>' to '</{tags_to_close[-1]}>'",
                            before=f"</{token.content}>",
                            after=f"</{tags_to_close[-1]}>",
                        )

                    if len(tags_to_close) > 1:
                        closed_tags_str = "".join([f"</{t}>" for t in tags_to_close])
                        report.add_action(
                            RepairType.TRUNCATION,
                            f"Closed {len(tags_to_close) - 1} unclosed parent tags due to mismatched tag correction",
                            after=closed_tags_str,
                        )

                    # Output all the closing tags
                    for tag in tags_to_close:
                        result.append(f"</{tag}>")
                else:
                    # No good match found, output as-is
                    # This might be an extra closing tag or severely mismatched
                    result.append(f"</{token.content}>")
            elif token.type == "self_closing_tag":
                flush_text_buffer()
                fixed_content, attr_actions = fix_malformed_attributes(
                    token.content, aggressive_escape=self.escape_unsafe_attributes
                )
                if attr_actions:
                    report.actions.extend(attr_actions)
                result.append(f"<{fixed_content}/>")
            elif token.type == "incomplete_tag":
                flush_text_buffer()

                fixed_content, attr_actions = fix_malformed_attributes(
                    token.content, aggressive_escape=self.escape_unsafe_attributes
                )
                if attr_actions:
                    report.actions.extend(attr_actions)

                # Handle truncated tags
                # Inject namespaces into first tag if needed
                if first_open_tag and namespaces:
                    updated_content = self.inject_namespace_declarations(fixed_content, namespaces)
                    result.append(f"<{updated_content}>")
                    first_open_tag = False
                else:
                    result.append(f"<{fixed_content}>")
                    first_open_tag = False

                if i + 1 < len(tokens) and tokens[i + 1].type == "tag_name":
                    tag_name = tokens[i + 1].content
                    tag_stack.append((tag_name, tag_name.lower()))
                    check_max_depth(len(tag_stack), self.max_depth)
                    i += 1  # Skip the tag_name token
            elif token.type == "text":
                # Buffer text content if we're in a CDATA candidate tag
                # Otherwise, escape and output immediately
                if in_cdata_candidate and self.auto_wrap_cdata:
                    text_buffer.append(token.content)
                else:
                    escaped_text, was_changed = self.escape_entities(
                        token.content, aggressive_escape=self.escape_unsafe_attributes
                    )
                    if was_changed:
                        report.add_action(
                            RepairType.UNESCAPED_ENTITY,
                            "Escaped special characters in text content",
                            before=token.content,
                            after=escaped_text,
                        )
                    result.append(escaped_text)
            elif token.type == "whitespace":
                # Buffer whitespace if we're collecting CDATA content
                if in_cdata_candidate and self.auto_wrap_cdata:
                    text_buffer.append(token.content)
                else:
                    result.append(token.content)
            elif token.type == "doctype":
                # DOCTYPE declarations are preserved unless security flag is set
                # (They were already stripped in extract_xml_content if flag was set)
                result.append(token.content)
            elif token.type == "comment":
                # Comments are preserved
                result.append(token.content)
            elif token.type == "cdata":
                # CDATA sections are preserved
                result.append(token.content)

            i += 1

        # Flush any remaining buffered text
        flush_text_buffer()

        # Step 4: Close any remaining open tags
        if tag_stack:
            # Create a description of the tags being closed for the report
            tags_to_close_str = "".join([f"</{tag[0]}>" for tag in reversed(tag_stack)])
            report.add_action(
                RepairType.TRUNCATION,
                f"Added {len(tag_stack)} missing closing tags due to document truncation.",
                location="end of document",
                after=tags_to_close_str,
            )
        while tag_stack:
            tag_name = tag_stack.pop()[0]  # Use original case
            result.append(f"</{tag_name}>")

        repaired = "".join(result)

        # Step 5: Wrap multiple roots if requested
        if self.wrap_multiple_roots:
            repaired = self._wrap_multiple_roots(repaired)

        report.repaired_xml = repaired

        # Step 6: Audit logging (if enabled)
        if self.audit_logger:
            # We need to map RepairReport actions to simple strings
            actions_taken = [f"{a.repair_type.name}: {a.description}" for a in report.actions]
            # We don't have a "Threat" object from the parser directly, as parser handles
            # threats via actions (e.g. DANGEROUS_TAG_STRIPPED).
            # However, the ThreatDetector (if we used it separately) would give threats.
            # For now, let's map specific repair types to "detected threats" for the log.

            # Implicit threat detection from actions
            threats_detected = []
            for action in report.actions:
                if action.repair_type in (
                    RepairType.DANGEROUS_PI_STRIPPED,
                    RepairType.DANGEROUS_TAG_STRIPPED,
                    RepairType.EXTERNAL_ENTITY_STRIPPED,
                ):
                    threats_detected.append(action.repair_type.name)

            # Note: We don't pass raw 'Threat' objects here because parser doesn't use ThreatDetector
            # directly in this flow (it uses SecurityFilter). We could enhance this later.
            # For now, we log the actions.

            # We'll create a dummy list of threats for the logger signature for now,
            # or update the logger to accept strings. The AuditLogger expects List[Threat].
            # This is a bit of a mismatch. Ideally, parser should use ThreatDetector.

            # Let's just use the ThreatDetector to analyze the INPUT if logging is enabled!
            # This gives us proper Threat objects.
            from .audit import ThreatDetector

            detector = ThreatDetector()
            detected_threats = detector.detect_threats(xml_string)

            self.audit_logger.log_repair_operation(
                xml_input=xml_string,
                xml_output=repaired,
                trust_level=self.config.trust_level or "unknown",
                threats=detected_threats,
                actions_taken=actions_taken,
                security_flags={
                    "strip_pis": self.strip_dangerous_pis,
                    "strip_entities": self.strip_external_entities,
                    "strip_tags": self.strip_dangerous_tags,
                },
            )

        return repaired, report

    def _wrap_multiple_roots(self, xml_string: str) -> str:
        """
        Detect and wrap multiple root elements in a synthetic <document> root.

        Args:
            xml_string: The repaired XML string

        Returns:
            XML string with single root (wrapped if necessary)
        """
        # Tokenize to count root-level elements
        tokens = self.tokenize(xml_string)

        # Track depth and count root elements
        depth = 0
        root_count = 0
        has_top_level_text = False
        xml_declaration = None
        pis_before_root = []

        for token in tokens:
            if token.type == "processing_instruction":
                if token.content.startswith("<?xml"):
                    xml_declaration = token.content
                elif depth == 0:
                    pis_before_root.append(token.content)
            elif token.type == "open_tag" or token.type == "incomplete_tag":
                if depth == 0:
                    root_count += 1
                depth += 1
            elif token.type == "close_tag":
                depth -= 1
            elif token.type == "self_closing_tag":
                if depth == 0:
                    root_count += 1
            elif token.type == "text" and depth == 0:
                if token.content.strip():  # Non-whitespace text at top level
                    has_top_level_text = True
            elif token.type in ("comment", "doctype", "cdata") and depth == 0:
                # These at top level also indicate need for wrapping
                pass

        # Only wrap if we have multiple roots OR top-level text
        if root_count <= 1 and not has_top_level_text:
            return xml_string

        # Build wrapped version
        result = []

        # Preserve XML declaration if present
        if xml_declaration:
            result.append(xml_declaration)
            result.append("\n")

        # Preserve processing instructions before root
        for pi in pis_before_root:
            result.append(pi)
            result.append("\n")

        # Add synthetic root
        result.append("<document>")

        # Add the content (strip any leading/trailing XML declaration and PIs)
        content = xml_string
        if xml_declaration:
            content = content.replace(xml_declaration, "", 1)
        for pi in pis_before_root:
            content = content.replace(pi, "", 1)

        result.append(content.strip())
        result.append("</document>")

        return "".join(result)

    def xml_to_dict(self, xml_string: str) -> Dict[str, Any]:
        # Simple XML to dict converter
        repaired_xml, _ = self.repair_xml(xml_string)
        return self._parse_xml_to_dict(repaired_xml)

    def _parse_xml_to_dict(self, xml_string: str) -> Dict[str, Any]:
        tokens = self.tokenize(xml_string)
        return self._build_dict_from_tokens(tokens)

    def _build_dict_from_tokens(self, tokens: List[XMLToken]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        stack = [result]
        current_element = None
        text_buffer: List[str] = []

        i = 0
        while i < len(tokens):
            token = tokens[i]

            if token.type == "open_tag":
                # Parse tag with attributes
                tag_content = token.content
                parts = tag_content.split()
                tag_name = parts[0] if parts else tag_content

                new_element = {}

                # Parse attributes
                if len(parts) > 1:
                    attr_text = " ".join(parts[1:])
                    attrs = self._parse_attributes(attr_text)
                    if attrs:
                        new_element["@attributes"] = attrs

                # Add to current level
                current_dict = stack[-1]
                if tag_name in current_dict:
                    # Convert to list if multiple elements with same name
                    if not isinstance(current_dict[tag_name], list):
                        current_dict[tag_name] = [current_dict[tag_name]]
                    current_dict[tag_name].append(new_element)
                else:
                    current_dict[tag_name] = new_element

                stack.append(new_element)
                current_element = tag_name

            elif token.type == "close_tag":
                # Add accumulated text if any
                if text_buffer:
                    text_content = "".join(text_buffer).strip()
                    if text_content and len(stack) > 1 and current_element is not None:
                        current_dict = stack[-1]
                        if not current_dict:  # Empty dict, just add text
                            stack[-2][current_element] = text_content
                        else:  # Has attributes, add text content
                            current_dict["#text"] = text_content
                    text_buffer = []

                if len(stack) > 1:
                    stack.pop()

            elif token.type == "self_closing_tag":
                tag_content = token.content
                parts = tag_content.split()
                tag_name = parts[0] if parts else tag_content

                element_data = {}

                # Parse attributes
                if len(parts) > 1:
                    attr_text = " ".join(parts[1:])
                    attrs = self._parse_attributes(attr_text)
                    if attrs:
                        element_data = attrs

                # Add to current level
                current_dict = stack[-1]
                if tag_name in current_dict:
                    if not isinstance(current_dict[tag_name], list):
                        current_dict[tag_name] = [current_dict[tag_name]]
                    current_dict[tag_name].append(element_data)
                else:
                    current_dict[tag_name] = element_data

            elif token.type == "text":
                text_buffer.append(token.content)

            i += 1

        return result

    def _parse_attributes(self, attr_text: str) -> Dict[str, str]:
        attrs = {}
        # Simple attribute parser
        attr_pattern = r'(\w+)=(["\'])([^"\']*?)\2'
        matches = re.findall(attr_pattern, attr_text)

        for match in matches:
            attr_name, _quote, attr_value = match
            attrs[attr_name] = attr_value

        return attrs
