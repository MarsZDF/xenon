.PHONY: help check fix test lint format typecheck clean all

# Default target
help:
	@echo "Xenon Development Commands:"
	@echo ""
	@echo "  make check      - Run all checks (lint, format, type, test)"
	@echo "  make fix        - Auto-fix issues (lint + format)"
	@echo "  make test       - Run test suite"
	@echo "  make lint       - Run ruff linting"
	@echo "  make format     - Run ruff formatting"
	@echo "  make typecheck  - Run mypy type checking"
	@echo "  make clean      - Clean cache files"
	@echo ""
	@echo "Quick workflow:"
	@echo "  make fix && make check    # Fix issues then verify"

# Run all checks (what CI runs)
check: lint format typecheck test
	@echo ""
	@echo "✅ All checks passed! Safe to push."

# Auto-fix what can be fixed
fix:
	@echo "🔧 Auto-fixing issues..."
	ruff check src/ tests/ --fix
	ruff format src/ tests/
	@echo "✅ Auto-fix complete. Run 'make check' to verify."

# Run tests with coverage
test:
	@echo "🧪 Running tests..."
	python -m pytest tests/ -q --tb=line

# Ruff linting (check only)
lint:
	@echo "🔍 Linting..."
	ruff check src/ tests/

# Ruff formatting (check only)
format:
	@echo "📝 Checking formatting..."
	ruff format --check src/ tests/

# Mypy type checking
typecheck:
	@echo "🔬 Type checking..."
	mypy src/xenon --strict

# Clean cache files
clean:
	@echo "🧹 Cleaning cache files..."
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Clean complete."

# Run everything (fix + check)
all: fix check
