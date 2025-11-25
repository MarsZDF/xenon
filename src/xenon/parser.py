import re
from typing import List, Dict, Any, Optional, Tuple, Union


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
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'xsd': 'http://www.w3.org/2001/XMLSchema',
        'xs': 'http://www.w3.org/2001/XMLSchema',
    }

    def __init__(self):
        self.state = XMLParseState()
        
    def extract_xml_content(self, text: str) -> str:
        text = text.strip()
        
        # Handle XML declarations and processing instructions
        xml_start = -1
        
        # Look for XML declaration first
        if text.startswith('<?xml'):
            xml_start = 0
        else:
            # Find first < that starts XML-like content
            for i, char in enumerate(text):
                if char == '<' and i + 1 < len(text):
                    next_char = text[i + 1]
                    # Valid XML tag starts: <letter, </, or <?
                    if next_char.isalpha() or next_char == '/' or next_char == '?':
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
            r'\s+(Hope\s+this\s+helps|Let\s+me\s+know|That\s+should)',
            r'\s+(Please\s+let\s+me\s+know|Is\s+this\s+what)',
            r'\s*\n\s*[A-Z][^<]*$',  # Newline followed by sentence not containing <
        ]
        
        # Only trim if we find clear conversational patterns
        for pattern in end_patterns:
            match = re.search(pattern, text[xml_start:], re.IGNORECASE)
            if match:
                potential_end = xml_start + match.start()
                # Make sure we end at a > if possible
                for i in range(potential_end - 1, xml_start, -1):
                    if text[i] == '>':
                        xml_end = i + 1
                        break
                break
            
        return text[xml_start:xml_end]
    
    def fix_malformed_attributes(self, tag_content: str) -> str:
        # Fix unquoted attribute values by parsing more carefully
        content = tag_content.strip()

        # Extract tag name first (everything before the first = or first space followed by word=)
        tag_name = ''
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
            while i < len(content) and (content[i].isalnum() or content[i] in '_-:'):
                i += 1

            if i >= len(content) or content[i] != '=':
                # Not an attribute, just copy the rest
                result.append(' ')
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
                                while k < len(content) and (content[k].isalnum() or content[k] in '_-:'):
                                    k += 1
                                if k < len(content) and content[k] == '=':
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
                value_start = i
                i += 1
                while i < len(content) and content[i] != quote_char:
                    i += 1
                if i < len(content):
                    i += 1  # Include the closing quote
                    result.append(f' {attr_name}={content[value_start:i]}')
                else:
                    # Truncated quote, add closing quote
                    result.append(f' {attr_name}={content[value_start:]}{quote_char}')
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
                            attr_ahead_start = j
                            while j < len(content) and (content[j].isalnum() or content[j] in '_-:'):
                                j += 1
                            if j < len(content) and content[j] == '=':
                                # This is a new attribute, stop here
                                break
                    i += 1

                value = content[value_start:i].strip()
                result.append(f' {attr_name}="{value}"')

        return ''.join(result)
    
    def detect_cdata_needed(self, text: str) -> bool:
        """
        Detect if text content should be wrapped in CDATA.

        Heuristics:
        - Contains >= 3 special XML chars (<, >, &)
        - Contains code keywords (if, for, while, function, class, def, var, let, const)
        - Has existing CDATA markers
        """
        if not text or len(text) < 3:
            return False

        # Check if already has CDATA
        if '<![CDATA[' in text:
            return False

        # Count special characters
        special_count = text.count('<') + text.count('>') + text.count('&')
        if special_count >= 3:
            return True

        # Check for code keywords (case-insensitive)
        code_keywords = ['if(', 'for(', 'while(', 'function', 'class ', 'def ',
                        'var ', 'let ', 'const ', 'return ', '&&', '||', '!=', '==']
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
        safe_text = text.replace(']]>', ']]]]><![CDATA[>')
        return f'<![CDATA[{safe_text}]]>'

    def extract_namespaces(self, xml: str) -> Dict[str, str]:
        """
        Extract namespace prefixes used in XML.

        Returns dict mapping prefix to namespace URI for known prefixes.
        """
        import re

        namespaces = {}

        # Find all namespace prefixes (prefix:tagname pattern)
        prefix_pattern = r'</?([a-zA-Z][a-zA-Z0-9]*):([a-zA-Z][a-zA-Z0-9]*)'
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
        # Only escape & and < in text content (not in tags)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        return text
    
    def tokenize(self, xml_string: str) -> List[XMLToken]:
        tokens = []
        i = 0
        
        while i < len(xml_string):
            if xml_string[i] == '<':
                # Check if this is actually a tag or just < in text
                if i + 1 >= len(xml_string):
                    # Just a < at end, treat as text
                    tokens.append(XMLToken('text', '<', i))
                    i += 1
                    continue
                    
                next_char = xml_string[i + 1]
                if not (next_char.isalpha() or next_char == '/' or next_char == '?'):
                    # Not a tag start, treat as text content
                    text_start = i
                    while i < len(xml_string) and (xml_string[i] != '<' or 
                                                   (i + 1 < len(xml_string) and not (xml_string[i + 1].isalpha() or xml_string[i + 1] == '/' or xml_string[i + 1] == '?'))):
                        i += 1
                    text_content = xml_string[text_start:i]
                    if text_content:
                        tokens.append(XMLToken('text', text_content, text_start))
                    continue
                
                # Handle XML declaration/processing instruction
                if xml_string[i:i+5] == '<?xml' or xml_string[i:i+2] == '<?':
                    # Find end of processing instruction
                    pi_end = xml_string.find('?>', i + 2)
                    if pi_end != -1:
                        pi_end += 2
                        pi_content = xml_string[i:pi_end]
                        tokens.append(XMLToken('processing_instruction', pi_content, i))
                        i = pi_end
                        continue
                    else:
                        # Malformed PI, treat as incomplete tag
                        tokens.append(XMLToken('incomplete_tag', xml_string[i+1:], i))
                        break
                
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
                        elif char == '>':
                            tag_end += 1
                            break
                    else:
                        if char == quote_char:
                            in_quotes = False
                            quote_char = None
                    
                    tag_end += 1
                
                tag_content = xml_string[i:tag_end]
                
                if tag_content.endswith('>'):
                    # Complete tag
                    if tag_content.startswith('</'):
                        # Closing tag
                        tag_name = tag_content[2:-1].strip()
                        tokens.append(XMLToken('close_tag', tag_name, i))
                    elif tag_content.endswith('/>'):
                        # Self-closing tag
                        tag_content_inner = tag_content[1:-2].strip()
                        tag_content_inner = self.fix_malformed_attributes(tag_content_inner)
                        tokens.append(XMLToken('self_closing_tag', tag_content_inner, i))
                    else:
                        # Opening tag
                        tag_content_inner = tag_content[1:-1].strip()
                        tag_content_inner = self.fix_malformed_attributes(tag_content_inner)
                        tag_name = tag_content_inner.split()[0] if tag_content_inner.split() else tag_content_inner
                        tokens.append(XMLToken('open_tag', tag_content_inner, i))
                        tokens.append(XMLToken('tag_name', tag_name, i))
                else:
                    # Incomplete tag (truncated) - include everything to end
                    tag_content_inner = xml_string[i+1:].strip()
                    if tag_content_inner:
                        tag_content_inner = self.fix_malformed_attributes(tag_content_inner)
                        tag_name = tag_content_inner.split()[0] if tag_content_inner.split() else tag_content_inner
                        tokens.append(XMLToken('incomplete_tag', tag_content_inner, i))
                        tokens.append(XMLToken('tag_name', tag_name, i))
                    break  # End of input, truncated
                
                i = tag_end
            else:
                # Text content
                text_start = i
                while i < len(xml_string) and xml_string[i] != '<':
                    i += 1
                
                text_content = xml_string[text_start:i]
                if text_content.strip():
                    # Don't escape here, do it during output
                    tokens.append(XMLToken('text', text_content, text_start))
                elif text_content:  # Preserve whitespace
                    tokens.append(XMLToken('whitespace', text_content, text_start))
        
        return tokens
    
    def repair_xml(self, xml_string: str) -> str:
        # Step 1: Extract XML content from conversational fluff
        cleaned_xml = self.extract_xml_content(xml_string)

        # Step 1.5: Extract namespaces before tokenization
        namespaces = self.extract_namespaces(cleaned_xml)

        # Step 2: Tokenize and parse with stack-based approach
        tokens = self.tokenize(cleaned_xml)

        # Step 3: Rebuild XML with proper closing tags
        result = []
        tag_stack = []  # Stack stores tuples of (original_case, lowercase) for case-insensitive matching
        first_open_tag = True  # Track first tag for namespace injection
        i = 0

        while i < len(tokens):
            token = tokens[i]

            if token.type == 'processing_instruction':
                result.append(token.content)
            elif token.type == 'open_tag':
                # Inject namespaces into first open tag (root element)
                if first_open_tag and namespaces:
                    updated_content = self.inject_namespace_declarations(token.content, namespaces)
                    result.append(f'<{updated_content}>')
                    first_open_tag = False
                else:
                    result.append(f'<{token.content}>')
                    first_open_tag = False

                # Extract tag name for stack (store both original and lowercase)
                if i + 1 < len(tokens) and tokens[i + 1].type == 'tag_name':
                    tag_name = tokens[i + 1].content
                    tag_stack.append((tag_name, tag_name.lower()))
                    i += 1  # Skip the tag_name token
            elif token.type == 'close_tag':
                # Case-insensitive tag matching - use opening tag's case
                closing_tag_lower = token.content.lower()
                if tag_stack and tag_stack[-1][1] == closing_tag_lower:
                    original_tag_name = tag_stack.pop()[0]
                    result.append(f'</{original_tag_name}>')
                else:
                    result.append(f'</{token.content}>')
            elif token.type == 'self_closing_tag':
                result.append(f'<{token.content}/>')
            elif token.type == 'incomplete_tag':
                # Handle truncated tags
                # Inject namespaces into first tag if needed
                if first_open_tag and namespaces:
                    updated_content = self.inject_namespace_declarations(token.content, namespaces)
                    result.append(f'<{updated_content}>')
                    first_open_tag = False
                else:
                    result.append(f'<{token.content}>')
                    first_open_tag = False

                if i + 1 < len(tokens) and tokens[i + 1].type == 'tag_name':
                    tag_name = tokens[i + 1].content
                    tag_stack.append((tag_name, tag_name.lower()))
                    i += 1  # Skip the tag_name token
            elif token.type == 'text':
                # Check if text needs CDATA wrapping (code, special chars)
                if self.detect_cdata_needed(token.content):
                    result.append(self.wrap_in_cdata(token.content))
                else:
                    escaped_text = self.escape_entities(token.content)
                    result.append(escaped_text)
            elif token.type == 'whitespace':
                result.append(token.content)
            
            i += 1
        
        # Step 4: Close any remaining open tags
        while tag_stack:
            tag_name = tag_stack.pop()[0]  # Use original case
            result.append(f'</{tag_name}>')
        
        return ''.join(result)
    
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
            
            if token.type == 'open_tag':
                # Parse tag with attributes
                tag_content = token.content
                parts = tag_content.split()
                tag_name = parts[0] if parts else tag_content
                
                new_element = {}
                
                # Parse attributes
                if len(parts) > 1:
                    attr_text = ' '.join(parts[1:])
                    attrs = self._parse_attributes(attr_text)
                    if attrs:
                        new_element['@attributes'] = attrs
                
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
                
            elif token.type == 'close_tag':
                # Add accumulated text if any
                if text_buffer:
                    text_content = ''.join(text_buffer).strip()
                    if text_content and len(stack) > 1:
                        current_dict = stack[-1]
                        if not current_dict:  # Empty dict, just add text
                            stack[-2][current_element] = text_content
                        else:  # Has attributes, add text content
                            current_dict['#text'] = text_content
                    text_buffer = []
                
                if len(stack) > 1:
                    stack.pop()
                    
            elif token.type == 'self_closing_tag':
                tag_content = token.content
                parts = tag_content.split()
                tag_name = parts[0] if parts else tag_content
                
                element_data = {}
                
                # Parse attributes
                if len(parts) > 1:
                    attr_text = ' '.join(parts[1:])
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
                    
            elif token.type == 'text':
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