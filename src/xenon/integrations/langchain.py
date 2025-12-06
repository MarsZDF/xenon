"""
LangChain integration for Xenon.

Provides a robust XML output parser for LangChain chains.
"""

from typing import Any, Dict, Optional, Union

try:
    from langchain_core.exceptions import OutputParserException
    from langchain_core.output_parsers import BaseOutputParser
except ImportError:
    # Create dummy classes if langchain is not installed
    # so this file can be imported without crashing (for type checking etc)
    class BaseOutputParser:  # type: ignore
        """Dummy BaseOutputParser."""

        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

    class OutputParserException(Exception):  # type: ignore  # noqa: N818
        """Dummy OutputParserException."""

        pass


from xenon import TrustLevel, parse_xml_safe, repair_xml_safe


class XenonXMLOutputParser(BaseOutputParser):  # type: ignore
    """
    A LangChain OutputParser that uses Xenon to repair and parse XML.

    It can return either the repaired XML string or a parsed dictionary.

    Usage:
        from xenon.integrations.langchain import XenonXMLOutputParser
        from xenon import TrustLevel

        parser = XenonXMLOutputParser(
            trust=TrustLevel.UNTRUSTED,
            return_dict=True
        )
        result = parser.parse(llm_output)
    """

    trust: TrustLevel = TrustLevel.UNTRUSTED
    return_dict: bool = True
    """If True, returns a dict. If False, returns the repaired XML string."""

    # Xenon configuration options
    strip_dangerous_pis: Optional[bool] = None
    strip_external_entities: Optional[bool] = None
    strip_dangerous_tags: Optional[bool] = None
    strict: bool = False

    def parse(self, text: str) -> Union[str, Dict[str, Any]]:
        """
        Parse the output of an LLM call.

        Args:
            text: The output of the LLM call.

        Returns:
            The parsed XML (dict or string).
        """
        try:
            if self.return_dict:
                return parse_xml_safe(
                    text,
                    trust=self.trust,
                    strict=self.strict,
                    strip_dangerous_pis=self.strip_dangerous_pis,
                    strip_external_entities=self.strip_external_entities,
                    strip_dangerous_tags=self.strip_dangerous_tags,
                )
            else:
                return repair_xml_safe(
                    text,
                    trust=self.trust,
                    strict=self.strict,
                    strip_dangerous_pis=self.strip_dangerous_pis,
                    strip_external_entities=self.strip_external_entities,
                    strip_dangerous_tags=self.strip_dangerous_tags,
                )
        except Exception as e:
            raise OutputParserException(f"Xenon failed to repair/parse XML: {e}") from e

    @property
    def _type(self) -> str:
        return "xenon_xml_output_parser"
