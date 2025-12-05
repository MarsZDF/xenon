"""Tests for LangChain integration."""

from typing import Any, Dict, Union
from unittest.mock import MagicMock, patch

import pytest

# Check if langchain is installed (simulated for test environment)
# In a real scenario, we'd use a try-import
HAS_LANGCHAIN = True


class TestLangChainIntegration:
    """Test LangChain integration."""

    def test_imports_without_langchain(self):
        """Test that module can be imported even if langchain is missing."""
        with patch.dict(
            "sys.modules", {"langchain_core": None, "langchain_core.output_parsers": None}
        ):
            # Force reload or import fresh
            import sys

            if "xenon.integrations.langchain" in sys.modules:
                del sys.modules["xenon.integrations.langchain"]

            from xenon.integrations.langchain import XenonXMLOutputParser

            # Should be our dummy class
            assert XenonXMLOutputParser.__name__ == "XenonXMLOutputParser"

    def test_parser_initialization(self):
        """Test initializing the parser."""
        from xenon import TrustLevel
        from xenon.integrations.langchain import XenonXMLOutputParser

        parser = XenonXMLOutputParser(trust=TrustLevel.UNTRUSTED)
        assert parser.trust == TrustLevel.UNTRUSTED
        assert parser.return_dict is True

    def test_parse_returns_dict(self):
        """Test parsing returning a dictionary."""
        from xenon import TrustLevel
        from xenon.integrations.langchain import XenonXMLOutputParser

        parser = XenonXMLOutputParser(trust=TrustLevel.UNTRUSTED, return_dict=True)
        xml_input = "<root><item>value</item></root>"

        result = parser.parse(xml_input)

        assert isinstance(result, dict)
        assert result["root"]["item"] == "value"

    def test_parse_returns_string(self):
        """Test parsing returning a string."""
        from xenon import TrustLevel
        from xenon.integrations.langchain import XenonXMLOutputParser

        parser = XenonXMLOutputParser(trust=TrustLevel.UNTRUSTED, return_dict=False)
        xml_input = "<root><item>value</item>"  # Truncated

        result = parser.parse(xml_input)

        assert isinstance(result, str)
        assert result == "<root><item>value</item></root>"

    def test_parse_handles_error(self):
        """Test that parser raises OutputParserException on failure."""
        from xenon import TrustLevel
        from xenon.integrations.langchain import OutputParserException, XenonXMLOutputParser

        # Mock parse_xml_safe to raise an exception
        with patch("xenon.integrations.langchain.parse_xml_safe", side_effect=Exception("Boom")):
            parser = XenonXMLOutputParser(trust=TrustLevel.UNTRUSTED)

            with pytest.raises(OutputParserException) as exc:
                parser.parse("<root>")

            assert "Xenon failed to repair/parse XML" in str(exc.value)
