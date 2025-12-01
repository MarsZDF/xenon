# Contributing to Xenon

Thank you for your interest in contributing to Xenon! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Code Style](#code-style)
- [Release Process](#release-process)

## Code of Conduct

This project follows a simple code of conduct: be respectful, constructive, and professional. We're all here to build better software together.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/xenon.git
   cd xenon
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/MarsZDF/xenon.git
   ```

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git

### Install Development Dependencies

```bash
# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (optional but recommended)
pre-commit install
```

### Development Dependencies

Xenon uses these development tools:
- **pytest**: Testing framework
- **pytest-cov**: Coverage reporting
- **pytest-benchmark**: Performance testing
- **hypothesis**: Property-based testing
- **ruff**: Linting and formatting
- **mypy**: Type checking
- **pre-commit**: Git hooks for code quality

## Making Changes

### Before You Start

1. **Check existing issues** to see if your idea is already being discussed
2. **Open an issue** for significant changes to discuss the approach
3. **Keep changes focused**: One feature or fix per PR

### Creating a Branch

```bash
# Update your fork
git fetch upstream
git checkout main
git merge upstream/main

# Create a feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

### Making Commits

- Write clear, concise commit messages
- Reference issue numbers where applicable
- Keep commits atomic (one logical change per commit)

Good commit message examples:
```
Add CDATA wrapping feature for code tags

Fix #123: Handle malformed attributes with multiple spaces

Update README with CDATA usage examples
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_cdata_wrapping.py

# Run with coverage report
pytest --cov=xenon --cov-report=html

# Run property-based tests (these take longer)
pytest tests/test_property_based.py -v
```

### Writing Tests

- **Unit tests**: Test individual functions and methods
- **Integration tests**: Test feature workflows end-to-end
- **Property-based tests**: Use Hypothesis for edge case discovery
- **Coverage**: Aim for 80%+ coverage on new code

Test file naming convention:
- `test_*.py` for unit/integration tests
- `test_property_based.py` for Hypothesis tests

Example test:
```python
def test_cdata_wraps_code_content():
    """Test that code tags with special chars get CDATA wrapped."""
    xml = "<code>if (x < 5) { return; }</code>"
    result = repair_xml_safe(xml, auto_wrap_cdata=True)

    assert "<![CDATA[" in result
    assert "if (x < 5)" in result
```

## Submitting Changes

### Before Submitting

1. **Run the full test suite**:
   ```bash
   pytest tests/
   ```

2. **Check code style**:
   ```bash
   ruff check src/ tests/
   ruff format --check src/ tests/
   ```

3. **Run type checking** (optional, not required to pass):
   ```bash
   mypy src/xenon
   ```

4. **Update documentation** if you changed the API

### Pull Request Process

1. **Push your changes**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Open a Pull Request** on GitHub with:
   - Clear title describing the change
   - Description of what changed and why
   - Link to related issues
   - Screenshots/examples if applicable

3. **PR template** (use this structure):
   ```markdown
   ## Summary
   Brief description of changes

   ## Changes
   - Added X feature
   - Fixed Y bug
   - Updated Z documentation

   ## Testing
   - [ ] Added tests for new functionality
   - [ ] All tests pass locally
   - [ ] Updated documentation

   Fixes #123
   ```

4. **Respond to review feedback** promptly and professionally

### CI/CD Pipeline

Your PR will automatically trigger:
- Tests on Python 3.8-3.12
- Linting with ruff
- Type checking with mypy (informational)
- Security scanning with bandit
- Coverage reporting

All tests must pass before merging.

## Code Style

### Python Style

We use **ruff** for linting and formatting (replaces black, isort, flake8):

```bash
# Format code
ruff format src/ tests/

# Check for issues
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/
```

### Key Guidelines

- **Line length**: 100 characters (configured in `pyproject.toml`)
- **Imports**: Automatically sorted by ruff
- **Docstrings**: Use for public functions/classes
- **Type hints**: Encouraged but not required (we support Python 3.8+)
- **Comments**: Explain *why*, not *what*

### Docstring Format

```python
def repair_xml_safe(
    xml_string: str,
    strict: bool = False,
    allow_empty: bool = False
) -> str:
    """
    Safely repair XML with comprehensive error handling.

    This function provides the same repair capabilities as repair_xml(),
    but with robust error handling and input validation.

    Args:
        xml_string: The potentially malformed XML string to repair
        strict: If True, validate repaired output
        allow_empty: If True, accept empty input

    Returns:
        Repaired XML string

    Raises:
        ValidationError: If input is invalid

    Example:
        >>> repair_xml_safe('<root><item', strict=True)
        '<root><item></item></root>'
    """
```

## Adding New Features

### Feature Design Checklist

- [ ] Does this solve a real LLM XML problem?
- [ ] Is the API intuitive and backward compatible?
- [ ] Have you considered edge cases?
- [ ] Is the feature opt-in (not breaking existing code)?
- [ ] Is it documented with examples?

### Feature Implementation Checklist

- [ ] Implementation in `src/xenon/`
- [ ] Comprehensive tests (unit + integration)
- [ ] Property-based tests if applicable
- [ ] Documentation in README
- [ ] Example in `examples/` or docstrings
- [ ] Update `__all__` exports if adding public API

## Release Process

(For maintainers)

1. Update version in `pyproject.toml` and `src/xenon/__init__.py`
2. Update `CHANGELOG.md`
3. Create release commit: `git commit -m "Version X.Y.Z"`
4. Tag release: `git tag vX.Y.Z`
5. Push: `git push && git push --tags`
6. Build and publish to PyPI:
   ```bash
   python -m build
   twine upload dist/*
   ```

## Getting Help

- **Questions**: Open a GitHub Discussion or create an issue with the "question" label
- **Bugs**: Use the bug report template
- **Features**: Use the feature request template

## Recognition

Contributors will be recognized in:
- GitHub contributors page
- `AUTHORS.md` (coming soon)
- Release notes for significant contributions

Thank you for contributing to Xenon!
