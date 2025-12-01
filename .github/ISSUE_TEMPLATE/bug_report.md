---
name: Bug Report
about: Report a bug or unexpected behavior
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description
A clear and concise description of what the bug is.

## To Reproduce
Steps to reproduce the behavior:
1. Install xenon version: `X.X.X`
2. Run this code:
```python
from xenon import repair_xml

xml = "..."  # Your problematic XML
result = repair_xml(xml)
```
3. See error / unexpected output

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened. Include the full error message or unexpected output:
```
Paste error message or output here
```

## Input XML
Please provide the XML input that causes the issue (sanitize if sensitive):
```xml
<your>xml here</your>
```

## Environment
- Xenon version: [e.g. 0.5.0]
- Python version: [e.g. 3.10.5]
- Operating System: [e.g. Ubuntu 22.04, macOS 14.0, Windows 11]
- Installation method: [pip, GitHub, local]

## Additional Context
Add any other context about the problem here. For example:
- Does this happen with all XML inputs or just specific patterns?
- Is this a regression from a previous version?
- Any workarounds you've found?
