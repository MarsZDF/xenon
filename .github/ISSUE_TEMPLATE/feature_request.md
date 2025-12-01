---
name: Feature Request
about: Suggest a new feature or enhancement
title: '[FEATURE] '
labels: enhancement
assignees: ''
---

## Feature Description
A clear and concise description of the feature you'd like to see.

## Use Case
Describe the problem this feature would solve or the scenario where it would be useful.

**Example:**
"I'm parsing LLM-generated XML that contains [specific pattern]. Currently, Xenon handles it as [current behavior], but it would be better if it could [desired behavior]."

## Proposed Solution
If you have ideas on how this could be implemented, describe them here.

```python
# Example of how you envision using this feature
from xenon import repair_xml_safe

result = repair_xml_safe(
    xml_input,
    new_feature_flag=True  # Your proposed feature
)
```

## Alternatives Considered
Have you considered any alternative solutions or workarounds?

## Additional Context
- Is this a common LLM failure mode you've encountered?
- Are there any XML specifications or best practices this relates to?
- Would you be willing to contribute a PR for this feature?
- Add any other context, screenshots, or examples here.
