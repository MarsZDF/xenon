import re
from typing import Any, Dict, List, Optional, Tuple

from .config import RepairFlags, SecurityFlags, XMLRepairConfig
from .preprocessor import XMLPreprocessor
from .security import XMLSecurityFilter


class XMLToken:
    def __init__(self, token_type: str, content: str, position: int = 0):
        self.type = token_type
        self.content = content
        self.position = position


class XMLParseState:
    def __init__(self):
        self.position = 0
        self.stack: List[str] = []
        self.tokens: List[XMLToken] = []
        self.in_tag = False
        self.current_tag = ""
        self.in_quotes = False
        self.quote_char = ""


class XMLRepairEngine:
    # Common namespace URIs for auto-injection
    COMMON_NAMESPACES = {
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
        wrap_multiple_roots: bool = False,
        sanitize_invalid_tags: bool = False,
        fix_namespace_syntax: bool = False,
        auto_wrap_cdata: bool = False,
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
            wrap_multiple_roots: Wrap multiple root elements in synthetic <document> root.
                                Default False for backward compatibility.
            sanitize_invalid_tags: Fix invalid XML tag names (e.g., <123> → <tag_123>).
                                  Default False for backward compatibility.
            fix_namespace_syntax: Fix invalid namespace syntax (e.g., <bad::ns> → <bad_ns>).
                                 Default False for backward compatibility.
            auto_wrap_cdata: Automatically wrap code-like content in CDATA sections.
                            Detects tags like <code>, <script>, <pre> with special characters.
                            Default False for backward compatibility.

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
                wrap_multiple_roots=wrap_multiple_roots,
                sanitize_invalid_tags=sanitize_invalid_tags,
                fix_namespace_syntax=fix_namespace_syntax,
                auto_wrap_cdata=auto_wrap_cdata,
            )

        self.config = config
        self.state = XMLParseState()

        # Initialize components
        self.preprocessor = XMLPreprocessor(config)
        self.security_filter = XMLSecurityFilter(config)

        # Backward compatibility properties
        self.match_threshold = config.match_threshold
        self.strip_dangerous_pis = config.has_security_feature(SecurityFlags.STRIP_DANGEROUS_PIS)
        self.strip_external_entities = config.has_security_feature(
            SecurityFlags.STRIP_EXTERNAL_ENTITIES
        )
        self.strip_dangerous_tags = config.has_security_feature(SecurityFlags.STRIP_DANGEROUS_TAGS)
        self.wrap_multiple_roots = config.has_repair_feature(RepairFlags.WRAP_MULTIPLE_ROOTS)
        self.sanitize_invalid_tags = config.has_repair_feature(RepairFlags.SANITIZE_INVALID_TAGS)
        self.fix_namespace_syntax = config.has_repair_feature(RepairFlags.FIX_NAMESPACE_SYNTAX)
        self.auto_wrap_cdata = config.has_repair_feature(RepairFlags.AUTO_WRAP_CDATA)

        # Tags that commonly contain code or special characters
        self.CDATA_CANDIDATE_TAGS = {
            "code",
            "script",
            "pre",
            "source",
            "sql",
            "query",
            "formula",
            "expression",
            "xpath",
            "regex",
        }

    def _is_cdata_candidate_tag(self, tag_name: str) -> bool:
        """
        Check if tag name is a candidate for CDATA wrapping.

        Args:
            tag_name: The tag name to check

        Returns:
            True if tag commonly contains code or special characters
        """
        return tag_name.lower() in self.CDATA_CANDIDATE_TAGS

    def _content_needs_cdata(self, content: str) -> bool:
        """
        Check if content contains characters that benefit from CDATA wrapping.

        CDATA is useful when content has special XML characters that
        would otherwise need escaping. For code-like content, even a single
        special character is worth wrapping to preserve readability.

        Args:
            content: The text content to check

        Returns:
            True if content has special characters
        """
        if not content or content.isspace():
            return False

        # For code content, be liberal - even 1 special char benefits from CDATA
        # This is different from regular text where escaping is fine
        special_chars = {"<", ">", "&"}

        for char in special_chars:
            if char in content:
                return True

        return False

    def _wrap_in_cdata(self, content: str) -> str:
        """
        Wrap content in CDATA section.

        Handles edge case where content already contains ]]> by splitting it.

        Args:
            content: The content to wrap

        Returns:
            Content wrapped in CDATA section
        """
        # Handle ]]> in content by splitting the CDATA
        # ]]> ends CDATA, so we need to escape it as ]]]]><![CDATA[>
        if "]]>" in content:
            content = content.replace("]]>", "]]]]><![CDATA[>")

        return f"<![CDATA[{content}]]>"

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
        previous_row = range(len(s2) + 1)

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
        if best_distance <= self.match_threshold:
            return (best_index, best_match, best_distance)

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

        # Only trim if we find clear conversational patterns
        for pattern in end_patterns:
            match = re.search(pattern, text[xml_start:], re.IGNORECASE)
            if match:
                potential_end = xml_start + match.start()
                # Make sure we end at a > if possible
                for i in range(potential_end - 1, xml_start, -1):
                    if text[i] == ">":
                        xml_end = i + 1
                        break
                break

        return text[xml_start:xml_end]

    def fix_malformed_attributes(self, tag_content: str) -> str:
        # Fix unquoted attribute values by parsing more carefully
        content = tag_content.strip()

        # Extract tag name first (everything before the first = or first space followed by word=)
        tag_name = ""
        attr_start_pos = 0
        i = 0

        # Read the tag name (first word)
        while i < len(content) and not content[i].isspace():
            i += 1

        if i < len(content):
            tag_name = content[:i]
            # Skip whitespace after tag name
            while i < len(content) and content[i].isspace():
                i += 1
            attr_start_pos = i
        else:
            # No attributes, just tag name
            return content

        # Now parse attributes
        result = [tag_name]
        seen_attrs = set()  # Track attributes to remove duplicates
        i = attr_start_pos

        while i < len(content):
            # Skip whitespace
            while i < len(content) and content[i].isspace():
                i += 1

            if i >= len(content):
                break

            # Look for attribute pattern: name=value
            attr_start = i

            # Find attribute name
            while i < len(content) and (content[i].isalnum() or content[i] in "_-:"):
                i += 1

            if i >= len(content) or content[i] != "=":
                # Not an attribute, just copy the rest
                result.append(" ")
                result.append(content[attr_start:])
                break

            attr_name = content[attr_start:i]
            attr_name_lower = attr_name.lower()  # Case-insensitive duplicate check
            i += 1  # Skip the '='

            # Skip if this is a duplicate attribute
            if attr_name_lower in seen_attrs:
                # Parse the value but don't add to result
                if i < len(content) and content[i] in ['"', "'"]:
                    quote_char = content[i]
                    i += 1
                    while i < len(content) and content[i] != quote_char:
                        i += 1
                    if i < len(content):
                        i += 1
                else:
                    # Unquoted value
                    while i < len(content):
                        if content[i].isspace():
                            j = i
                            while j < len(content) and content[j].isspace():
                                j += 1
                            if j < len(content):
                                k = j
                                while k < len(content) and (
                                    content[k].isalnum() or content[k] in "_-:"
                                ):
                                    k += 1
                                if k < len(content) and content[k] == "=":
                                    break
                        i += 1
                continue

            seen_attrs.add(attr_name_lower)

            if i >= len(content):
                result.append(f' {attr_name}="')
                break

            # Handle the value
            if content[i] in ['"', "'"]:
                # Already quoted, find the end quote
                quote_char = content[i]
                value_start = i + 1  # Start after the opening quote
                i += 1
                while i < len(content) and content[i] != quote_char:
                    i += 1
                value = content[value_start:i]  # Value without quotes
                if i < len(content):
                    i += 1  # Skip the closing quote
                # Escape the value and add with quotes
                escaped_value = self.escape_attribute_value(value, quote_char)
                result.append(f" {attr_name}={quote_char}{escaped_value}{quote_char}")
            else:
                # Unquoted value, collect until next attribute or end
                value_start = i

                # Collect value until we hit the next attribute (word=) or end
                while i < len(content):
                    if content[i].isspace():
                        # Look ahead to see if this is the start of a new attribute
                        j = i
                        while j < len(content) and content[j].isspace():
                            j += 1

                        # Check if we have word= pattern ahead
                        if j < len(content):
                            while j < len(content) and (
                                content[j].isalnum() or content[j] in "_-:"
                            ):
                                j += 1
                            if j < len(content) and content[j] == "=":
                                # This is a new attribute, stop here
                                break
                    i += 1

                value = content[value_start:i].strip()
                # Escape the value before adding
                escaped_value = self.escape_attribute_value(value, '"')
                result.append(f' {attr_name}="{escaped_value}"')

        return "".join(result)

    def detect_cdata_needed(self, text: str) -> bool:
        """
        Detect if text content should be wrapped in CDATA.

        Heuristics:
        - Contains >= 3 unescaped special XML chars (<, >, &)
        - Contains code keywords (if, for, while, function, class, def, var, let, const)
        - Has existing CDATA markers
        """
        if not text or len(text) < 3:
            return False

        # Check if already has CDATA
        if "<![CDATA[" in text:
            return False

        # Count special characters, but exclude valid entity references
        import re

        # Remove valid entities before counting
        valid_entity_pattern = r"&(?:lt|gt|amp|quot|apos|#\d+|#x[0-9a-fA-F]+);"
        text_without_entities = re.sub(valid_entity_pattern, "", text)

        special_count = (
            text_without_entities.count("<")
            + text_without_entities.count(">")
            + text_without_entities.count("&")
        )
        if special_count >= 3:
            return True

        # Check for code keywords (case-insensitive)
        code_keywords = [
            "if(",
            "for(",
            "while(",
            "function",
            "class ",
            "def ",
            "var ",
            "let ",
            "const ",
            "return ",
            "&&",
            "||",
            "!=",
            "==",
        ]
        text_lower = text.lower()
        for keyword in code_keywords:
            if keyword in text_lower:
                return True

        return False

    def wrap_in_cdata(self, text: str) -> str:
        """
        Wrap text in CDATA section with security fix for ]]> breakout.

        SECURITY: Escape ]]> to prevent CDATA injection attacks.
        """
        # Escape ]]> to prevent CDATA breakout
        safe_text = text.replace("]]>", "]]]]><![CDATA[>")
        return f"<![CDATA[{safe_text}]]>"

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

    def escape_entities(self, text: str) -> str:
        """
        Escape special XML characters in text content.

        Escapes &, <, and > but avoids double-escaping already valid entity references.
        """
        # Pattern to match valid entity references
        # Matches: &lt; &gt; &amp; &quot; &apos; &#digits; &#xhex;
        import re

        valid_entity_pattern = r"&(?:lt|gt|amp|quot|apos|#\d+|#x[0-9a-fA-F]+);"

        # Find all valid entities and temporarily replace them with placeholders
        entities = []

        def save_entity(match):
            entities.append(match.group(0))
            return f"\x00ENTITY{len(entities) - 1}\x00"

        text = re.sub(valid_entity_pattern, save_entity, text)

        # Now escape the remaining special characters
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")

        # Restore the valid entities
        for i, entity in enumerate(entities):
            text = text.replace(f"\x00ENTITY{i}\x00", entity)

        return text

    def escape_attribute_value(self, value: str, quote_char: str = '"') -> str:
        """
        Escape special characters in attribute values.

        Escapes &, <, >, and the quote character used to delimit the attribute.
        Avoids double-escaping already valid entity references.
        """
        # Pattern to match valid entity references
        import re

        valid_entity_pattern = r"&(?:lt|gt|amp|quot|apos|#\d+|#x[0-9a-fA-F]+);"

        # Find all valid entities and temporarily replace them with placeholders
        entities = []

        def save_entity(match):
            entities.append(match.group(0))
            return f"\x00ENTITY{len(entities) - 1}\x00"

        value = re.sub(valid_entity_pattern, save_entity, value)

        # Escape special characters
        value = value.replace("&", "&amp;")
        value = value.replace("<", "&lt;")
        value = value.replace(">", "&gt;")

        # Escape the quote character being used
        if quote_char == '"':
            value = value.replace('"', "&quot;")
        else:  # single quote
            value = value.replace("'", "&apos;")

        # Restore the valid entities
        for i, entity in enumerate(entities):
            value = value.replace(f"\x00ENTITY{i}\x00", entity)

        return value

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
                    while i < len(xml_string) and (
                        xml_string[i] != "<"
                        or (
                            i + 1 < len(xml_string)
                            and not (xml_string[i + 1].isalpha() or xml_string[i + 1] in "_:/!?")
                        )
                    ):
                        i += 1
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
                        tag_content_inner = self.fix_malformed_attributes(tag_content_inner)
                        tokens.append(XMLToken("self_closing_tag", tag_content_inner, i))
                    else:
                        # Opening tag
                        tag_content_inner = tag_content[1:-1].strip()
                        tag_content_inner = self.fix_malformed_attributes(tag_content_inner)
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
                        tag_content_inner = self.fix_malformed_attributes(tag_content_inner)
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
                while i < len(xml_string) and xml_string[i] != "<":
                    i += 1

                text_content = xml_string[text_start:i]
                if text_content.strip():
                    # Don't escape here, do it during output
                    tokens.append(XMLToken("text", text_content, text_start))
                elif text_content:  # Preserve whitespace
                    tokens.append(XMLToken("whitespace", text_content, text_start))

        return tokens

    def repair_xml(self, xml_string: str) -> str:
        # Step 1: Preprocess invalid tag names & namespace syntax (single pass)
        # This must happen before extract_xml_content so the tokenizer can recognize the tags
        xml_string = self.preprocessor.preprocess(xml_string)

        # Step 2: Extract XML content from conversational fluff
        cleaned_xml = self.extract_xml_content(xml_string)

        # Step 1.6: Extract namespaces before tokenization
        namespaces = self.extract_namespaces(cleaned_xml)

        # Step 2: Tokenize and parse with stack-based approach
        tokens = self.tokenize(cleaned_xml)

        # Step 3: Rebuild XML with proper closing tags
        result = []
        tag_stack = []  # Stack stores tuples of (original_case, lowercase) for case-insensitive matching
        dangerous_tag_stack = []  # Track dangerous tags to skip their content
        first_open_tag = True  # Track first tag for namespace injection
        text_buffer = []  # Buffer for collecting text content in CDATA candidate tags
        in_cdata_candidate = False  # Are we currently inside a CDATA candidate tag?
        i = 0

        def flush_text_buffer():
            """Flush buffered text content, wrapping in CDATA if needed."""
            nonlocal text_buffer, in_cdata_candidate, result
            if not text_buffer:
                return

            # Combine all buffered text
            combined_text = "".join(text_buffer)
            text_buffer = []

            # Check if we should wrap in CDATA
            if in_cdata_candidate and self.auto_wrap_cdata and self._content_needs_cdata(combined_text):
                result.append(self._wrap_in_cdata(combined_text))
            else:
                # Escape entities normally
                result.append(self.escape_entities(combined_text))

        while i < len(tokens):
            token = tokens[i]

            if token.type == "processing_instruction":
                # Security: Skip dangerous processing instructions if enabled
                if self.security_filter.should_strip_dangerous_pi(token.content):
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
                    # Skip this tag but process content
                    dangerous_tag_stack.append((tag_name, tag_name.lower()))
                    if i + 1 < len(tokens) and tokens[i + 1].type == "tag_name":
                        i += 1  # Skip the tag_name token
                    i += 1
                    continue

                # Inject namespaces into first open tag (root element)
                if first_open_tag and namespaces:
                    updated_content = self.inject_namespace_declarations(token.content, namespaces)
                    result.append(f"<{updated_content}>")
                    first_open_tag = False
                else:
                    result.append(f"<{token.content}>")
                    first_open_tag = False

                if tag_name:
                    tag_stack.append((tag_name, tag_name.lower()))
                    # Check if this is a CDATA candidate tag
                    in_cdata_candidate = self._is_cdata_candidate_tag(tag_name)
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
                    stack_index, matched_tag, distance = match_result

                    # Close the matched tag and all tags opened after it
                    # (They were left unclosed due to the mismatch)
                    tags_to_close = []
                    while len(tag_stack) > stack_index:
                        tags_to_close.append(tag_stack.pop()[0])

                    # Output all the closing tags
                    for tag in tags_to_close:
                        result.append(f"</{tag}>")
                else:
                    # No good match found, output as-is
                    # This might be an extra closing tag or severely mismatched
                    result.append(f"</{token.content}>")
            elif token.type == "self_closing_tag":
                flush_text_buffer()
                result.append(f"<{token.content}/>")
            elif token.type == "incomplete_tag":
                flush_text_buffer()
                # Handle truncated tags
                # Inject namespaces into first tag if needed
                if first_open_tag and namespaces:
                    updated_content = self.inject_namespace_declarations(token.content, namespaces)
                    result.append(f"<{updated_content}>")
                    first_open_tag = False
                else:
                    result.append(f"<{token.content}>")
                    first_open_tag = False

                if i + 1 < len(tokens) and tokens[i + 1].type == "tag_name":
                    tag_name = tokens[i + 1].content
                    tag_stack.append((tag_name, tag_name.lower()))
                    i += 1  # Skip the tag_name token
            elif token.type == "text":
                # Buffer text content if we're in a CDATA candidate tag
                # Otherwise, escape and output immediately
                if in_cdata_candidate and self.auto_wrap_cdata:
                    text_buffer.append(token.content)
                else:
                    escaped_text = self.escape_entities(token.content)
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
        while tag_stack:
            tag_name = tag_stack.pop()[0]  # Use original case
            result.append(f"</{tag_name}>")

        repaired = "".join(result)

        # Step 5: Wrap multiple roots if requested
        if self.wrap_multiple_roots:
            repaired = self._wrap_multiple_roots(repaired)

        return repaired

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
        repaired_xml = self.repair_xml(xml_string)
        return self._parse_xml_to_dict(repaired_xml)

    def _parse_xml_to_dict(self, xml_string: str) -> Dict[str, Any]:
        tokens = self.tokenize(xml_string)
        return self._build_dict_from_tokens(tokens)

    def _build_dict_from_tokens(self, tokens: List[XMLToken]) -> Dict[str, Any]:
        result = {}
        stack = [result]
        current_element = None
        text_buffer = []

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
                    if text_content and len(stack) > 1:
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
            attr_name, quote, attr_value = match
            attrs[attr_name] = attr_value

        return attrs
