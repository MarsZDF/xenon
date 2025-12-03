#!/usr/bin/env python3
"""Quick script to add trust parameter to remaining test files."""

import re
from pathlib import Path

# Files that still need updating based on test failures
files_to_fix = [
    "tests/test_security.py",
    "tests/test_reporting.py",
    "tests/test_property_based.py",
    "tests/test_namespace_validation.py",
    "tests/test_multiple_roots.py",
    "tests/test_invalid_tag_names.py",
    "tests/test_diff_reporting.py",
]

def fix_file(filepath):
    """Add trust parameter to function calls in a test file."""
    path = Path(filepath)
    if not path.exists():
        print(f"Skipping {filepath} - not found")
        return

    content = path.read_text()
    original = content

    # Add TrustLevel import if not present
    if "from xenon import TrustLevel" not in content and "import TrustLevel" not in content:
        # Find the xenon import line and add TrustLevel
        if "from xenon import" in content:
            # Add TrustLevel to existing import
            content = re.sub(
                r'from xenon import ([^\n]+)',
                lambda m: f'from xenon import {m.group(1)}, TrustLevel' if 'TrustLevel' not in m.group(1) else m.group(0),
                content,
                count=1
            )
        elif "import xenon" in content:
            # Add separate import after
            content = re.sub(
                r'(import xenon\n)',
                r'\1from xenon import TrustLevel\n',
                content,
                count=1
            )

    # Fix repair_xml( calls
    content = re.sub(
        r'\brepair_xml\(([^,)]+)\)(?!\s*#.*trust)',
        r'repair_xml(\1, trust=TrustLevel.TRUSTED)',
        content
    )

    # Fix repair_xml_safe( calls - need to handle existing keyword args
    content = re.sub(
        r'\brepair_xml_safe\(([^,)]+)\)(?!\s*#.*trust)',
        r'repair_xml_safe(\1, trust=TrustLevel.TRUSTED)',
        content
    )
    content = re.sub(
        r'\brepair_xml_safe\(([^,)]+),\s*(?!trust)',
        r'repair_xml_safe(\1, trust=TrustLevel.TRUSTED, ',
        content
    )

    # Fix parse_xml( calls
    content = re.sub(
        r'\bparse_xml\(([^,)]+)\)(?!\s*#.*trust)',
        r'parse_xml(\1, trust=TrustLevel.TRUSTED)',
        content
    )

    # Fix parse_xml_safe( calls
    content = re.sub(
        r'\bparse_xml_safe\(([^,)]+)\)(?!\s*#.*trust)',
        r'parse_xml_safe(\1, trust=TrustLevel.TRUSTED)',
        content
    )
    content = re.sub(
        r'\bparse_xml_safe\(([^,)]+),\s*(?!trust)',
        r'parse_xml_safe(\1, trust=TrustLevel.TRUSTED, ',
        content
    )

    # Fix repair_xml_with_report( calls
    content = re.sub(
        r'\brepair_xml_with_report\(([^,)]+)\)(?!\s*#.*trust)',
        r'repair_xml_with_report(\1, trust=TrustLevel.TRUSTED)',
        content
    )

    # Fix repair_xml_with_diff( calls (alias)
    content = re.sub(
        r'\brepair_xml_with_diff\(([^,)]+)\)(?!\s*#.*trust)',
        r'repair_xml_with_diff(\1, trust=TrustLevel.TRUSTED)',
        content
    )

    # Fix batch_repair( calls
    content = re.sub(
        r'\bbatch_repair\(([^,)]+)\)(?!\s*#.*trust)',
        r'batch_repair(\1, trust=TrustLevel.TRUSTED)',
        content
    )
    content = re.sub(
        r'\bbatch_repair\(([^,)]+),\s*(?!trust)',
        r'batch_repair(\1, trust=TrustLevel.TRUSTED, ',
        content
    )

    # Fix batch_repair_with_reports( calls
    content = re.sub(
        r'\bbatch_repair_with_reports\(([^,)]+)\)(?!\s*#.*trust)',
        r'batch_repair_with_reports(\1, trust=TrustLevel.TRUSTED)',
        content
    )
    content = re.sub(
        r'\bbatch_repair_with_reports\(([^,)]+),\s*(?!trust)',
        r'batch_repair_with_reports(\1, trust=TrustLevel.TRUSTED, ',
        content
    )

    # Fix stream_repair( calls
    content = re.sub(
        r'\bstream_repair\(([^,)]+)\)(?!\s*#.*trust)',
        r'stream_repair(\1, trust=TrustLevel.TRUSTED)',
        content
    )
    content = re.sub(
        r'\bstream_repair\(([^,)]+),\s*(?!trust)',
        r'stream_repair(\1, trust=TrustLevel.TRUSTED, ',
        content
    )

    if content != original:
        path.write_text(content)
        print(f"✓ Updated {filepath}")
        return True
    else:
        print(f"  No changes needed for {filepath}")
        return False

if __name__ == "__main__":
    print("Fixing test files...")
    updated = 0
    for filepath in files_to_fix:
        if fix_file(filepath):
            updated += 1
    print(f"\nUpdated {updated}/{len(files_to_fix)} files")

# Additional files found during testing
files_to_fix.extend([
    "tests/test_attribute_escaping.py",
    "tests/test_benchmarks.py",
])
