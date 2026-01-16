# Team Metrics Dashboard - Makefile
# Quick commands for development and code quality

.PHONY: help format lint test clean install all check

# Default target
help:
	@echo "Team Metrics Dashboard - Available Commands:"
	@echo ""
	@echo "  make install     - Install all dependencies (including dev tools)"
	@echo "  make format      - Auto-format code with black and isort"
	@echo "  make lint        - Run pylint linter"
	@echo "  make typecheck   - Run mypy type checker"
	@echo "  make test        - Run pytest with coverage"
	@echo "  make check       - Run all quality checks (format + lint + typecheck + test)"
	@echo "  make clean       - Remove Python cache files and build artifacts"
	@echo "  make all         - Install deps, format, and run all checks"
	@echo ""

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	pip install black isort pylint mypy pytest pytest-cov
	@echo "✅ Dependencies installed!"

# Format code
format:
	@echo "🎨 Formatting code with black..."
	black src/ collect_data.py list_jira_filters.py validate_config.py analyze_releases.py
	@echo "📐 Organizing imports with isort..."
	isort src/ collect_data.py list_jira_filters.py validate_config.py analyze_releases.py
	@echo "✅ Code formatted!"

# Run linter
lint:
	@echo "🔍 Running pylint..."
	pylint src/ || true
	@echo "✅ Linting complete!"

# Run type checker
typecheck:
	@echo "📝 Running mypy type checker..."
	mypy src/ --show-error-codes || true
	@echo "✅ Type checking complete!"

# Run tests
test:
	@echo "🧪 Running tests..."
	pytest tests/unit/test_date_ranges.py tests/unit/test_config.py tests/unit/test_performance_score.py -v --cov=src --cov-report=term-missing
	@echo "✅ Tests complete!"

# Run all checks
check: format lint typecheck test
	@echo ""
	@echo "✅ All quality checks complete!"
	@echo ""

# Clean cache files
clean:
	@echo "🧹 Cleaning cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage
	@echo "✅ Cache files cleaned!"

# Do everything
all: install format check
	@echo ""
	@echo "🎉 All tasks complete!"
	@echo ""

# Quick format check (don't modify files)
format-check:
	@echo "🎨 Checking code formatting..."
	black --check --diff src/ collect_data.py list_jira_filters.py validate_config.py analyze_releases.py
	isort --check-only --diff src/ collect_data.py list_jira_filters.py validate_config.py analyze_releases.py
	@echo "✅ Format check complete!"

# Install pre-commit hooks
pre-commit-install:
	@echo "🪝 Installing pre-commit hooks..."
	pip install pre-commit
	pre-commit install
	@echo "✅ Pre-commit hooks installed!"

# Run pre-commit on all files
pre-commit-run:
	@echo "🪝 Running pre-commit on all files..."
	pre-commit run --all-files
	@echo "✅ Pre-commit checks complete!"
