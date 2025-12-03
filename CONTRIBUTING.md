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

### Commit Message Guidelines

This project follows the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification. This is a lightweight convention on top of commit messages that provides an easy set of rules for creating an explicit commit history. This allows for automation of versioning and changelogs.

A pre-commit hook is installed to enforce this format.

**Format:**

`<type>[optional scope]: <description>`

**Common Types:**

*   **`feat`**: A new feature for the user. (Triggers a `MINOR` version bump).
*   **`fix`**: A bug fix for the user. (Triggers a `PATCH` version bump).
*   **`docs`**: Documentation only changes.
*   **`style`**: Changes that do not affect the meaning of the code (white-space, formatting, etc).
*   **`refactor`**: A code change that neither fixes a bug nor adds a feature.
*   **`perf`**: A code change that improves performance.
*   **`test`**: Adding missing tests or correcting existing tests.
*   **`ci`**: Changes to our CI configuration files and scripts.
*   **`build`**: Changes that affect the build system or external dependencies.

**Breaking Changes:**

For a change that introduces a breaking change to the API, the commit body must contain a `BREAKING CHANGE:` footer. This will trigger a `MAJOR` version bump.

**Example:**

```
feat(api): change repair_xml to return a tuple

This is a new feature that provides more detailed output.

BREAKING CHANGE: `repair_xml` now returns a `(str, Report)` tuple instead of a string.
```

## Testing

### Running Tests
.  
.  
.  
# ... (rest of the file remains the same until Release Process)
# ...

## Release Process (Automated)

The release process is fully automated using [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) and `python-semantic-release`.

When a commit is merged to `main`, the CI/CD pipeline will automatically:
1. Analyze the commit messages.
2. Determine the correct new version number.
3. Update the version in `pyproject.toml` and `src/xenon/__init__.py`.
4. Generate a `CHANGELOG.md`.
5. Commit the new version and changelog.
6. Create a new Git tag and a GitHub Release.

## Getting Help

- **Questions**: Open a GitHub Discussion or create an issue with the "question" label

## Recognition

Contributors will be recognized in:
- GitHub contributors page
- `AUTHORS.md` (coming soon)
- Release notes for significant contributions

Thank you for contributing to Xenon!
