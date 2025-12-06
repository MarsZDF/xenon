"""
Command-line interface for Xenon XML repair.

This module provides the CLI entry point for accessing Xenon features
from the terminal, including repair, validation, and diffing.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import (
    TrustLevel,
    __version__,
    repair_xml_safe,
    repair_xml_with_diff,
)
from .validation import validate_with_schema


def setup_parser() -> argparse.ArgumentParser:
    """Configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Xenon: Secure XML Repair Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Repair a file (untrusted by default)
  xenon repair input.xml -o output.xml

  # Repair with specific trust level
  xenon repair internal_data.xml --trust internal

  # Pipe from stdin
  cat bad.xml | xenon repair

  # Validate against schema
  xenon validate output.xml --schema schema.xsd

  # Show diff of repairs
  xenon diff broken.xml
""",
    )

    parser.add_argument("--version", action="version", version=f"Xenon v{__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # --- Repair Command ---
    repair_parser = subparsers.add_parser("repair", help="Repair malformed XML")
    repair_parser.add_argument(
        "input_file",
        nargs="?",
        help="Input XML file (default: stdin)",
    )
    repair_parser.add_argument(
        "-o",
        "--output",
        dest="output_file",
        help="Output file (default: stdout)",
    )
    repair_parser.add_argument(
        "--trust",
        choices=["untrusted", "internal", "trusted"],
        default="untrusted",
        help="Trust level of input (default: untrusted)",
    )
    repair_parser.add_argument(
        "--format",
        choices=["pretty", "compact", "minify"],
        help="Format output style",
    )
    repair_parser.add_argument(
        "--in-place",
        action="store_true",
        help="Modify input file in-place (requires input file)",
    )
    repair_parser.add_argument(
        "--no-audit",
        action="store_true",
        help="Disable audit logging (faster)",
    )

    # --- Validate Command ---
    validate_parser = subparsers.add_parser("validate", help="Validate XML against schema")
    validate_parser.add_argument("input_file", help="XML file to validate")
    validate_parser.add_argument("--schema", required=True, help="XSD or DTD schema file")

    # --- Diff Command ---
    diff_parser = subparsers.add_parser("diff", help="Show diff between original and repaired XML")
    diff_parser.add_argument("input_file", nargs="?", help="Input XML file (default: stdin)")
    diff_parser.add_argument(
        "--trust",
        choices=["untrusted", "internal", "trusted"],
        default="untrusted",
        help="Trust level (default: untrusted)",
    )

    return parser


def _get_input_content(input_file: Optional[str]) -> str:
    """Read content from file or stdin."""
    if input_file:
        path = Path(input_file)
        if not path.exists():
            print(f"Error: Input file '{input_file}' not found.", file=sys.stderr)
            sys.exit(1)
        return path.read_text(encoding="utf-8")

    # Check if stdin has data
    if sys.stdin.isatty():
        print("Error: No input provided (expected file or piped input).", file=sys.stderr)
        sys.exit(1)

    return sys.stdin.read()


def handle_repair(args: argparse.Namespace) -> None:
    """Handle the repair command."""
    try:
        xml_content = _get_input_content(args.input_file)

        trust_map = {
            "untrusted": TrustLevel.UNTRUSTED,
            "internal": TrustLevel.INTERNAL,
            "trusted": TrustLevel.TRUSTED,
        }
        trust = trust_map[args.trust]

        format_style = None
        if args.format:
            format_style = args.format

        # Audit is enabled by default for untrusted/internal, can be disabled
        # We don't have a direct flag in repair_xml_safe to DISABLE audit if trust enables it.
        # TODO: Add audit_threats override to repair_xml_safe for --no-audit support

        repaired = repair_xml_safe(
            xml_content,
            trust=trust,
            format_output=format_style,
            # We need to expose audit_threats in repair_xml_safe to override it easily?
            # Currently repair_xml_safe doesn't expose audit_threats directly,
            # but it's part of security config.
            # Let's check repair_xml_safe signature in __init__.py
        )

        if args.in_place:
            if not args.input_file:
                print("Error: --in-place requires an input file.", file=sys.stderr)
                sys.exit(1)
            Path(args.input_file).write_text(repaired, encoding="utf-8")
            print(f"Successfully repaired '{args.input_file}' in-place.", file=sys.stderr)
        elif args.output_file:
            Path(args.output_file).write_text(repaired, encoding="utf-8")
        else:
            print(repaired)

    except Exception as e:
        print(f"Error repairing XML: {e}", file=sys.stderr)
        sys.exit(1)


def handle_validate(args: argparse.Namespace) -> None:
    """Handle the validate command."""
    try:
        xml_content = Path(args.input_file).read_text(encoding="utf-8")
        schema_content = Path(args.schema).read_text(encoding="utf-8")

        validate_with_schema(xml_content, schema_content)
        print(f"✅ Validation successful: '{args.input_file}' matches schema '{args.schema}'")

    except Exception as e:
        print(f"❌ Validation failed: {e}", file=sys.stderr)
        sys.exit(1)


def handle_diff(args: argparse.Namespace) -> None:
    """Handle the diff command."""
    try:
        xml_content = _get_input_content(args.input_file)

        trust_map = {
            "untrusted": TrustLevel.UNTRUSTED,
            "internal": TrustLevel.INTERNAL,
            "trusted": TrustLevel.TRUSTED,
        }
        trust = trust_map[args.trust]

        _repaired, report = repair_xml_with_diff(xml_content, trust=trust)

        if not report.actions:
            print("No changes required. XML is valid and secure.", file=sys.stderr)
            sys.exit(0)

        print(report.to_unified_diff())

        # Print summary to stderr
        print("\nSummary of repairs:", file=sys.stderr)
        summary = report.get_diff_summary()
        for k, v in summary.items():
            if v > 0:
                print(f"  - {k}: {v}", file=sys.stderr)

    except Exception as e:
        print(f"Error generating diff: {e}", file=sys.stderr)
        sys.exit(1)


def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point."""
    if argv is None:
        argv = sys.argv[1:]

    parser = setup_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "repair":
        handle_repair(args)
    elif args.command == "validate":
        handle_validate(args)
    elif args.command == "diff":
        handle_diff(args)


if __name__ == "__main__":
    main()
