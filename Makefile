# Makefile for OpenPace development tasks

.PHONY: help install test test-all test-unit test-integration test-gui test-database coverage clean lint format type-check pre-commit docs

# Default target
help:
	@echo "OpenPace Development Commands"
	@echo "============================="
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install development dependencies"
	@echo "  make pre-commit    Install pre-commit hooks"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run all tests"
	@echo "  make test-unit     Run unit tests only"
	@echo "  make test-database Run database tests"
	@echo "  make test-gui      Run GUI tests"
	@echo "  make test-hl7      Run HL7 parser tests"
	@echo "  make coverage      Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          Run linters (flake8)"
	@echo "  make format        Format code with black"
	@echo "  make type-check    Run mypy type checking"
	@echo "  make check         Run all quality checks"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         Remove build artifacts and cache"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs          Build documentation"

# Installation
install:
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -e .
	@echo "✓ Installation complete"

install-dev:
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -e ".[dev]"
	@echo "✓ Development installation complete"

# Pre-commit hooks
pre-commit:
	pip install pre-commit
	pre-commit install
	@echo "✓ Pre-commit hooks installed"

# Testing
test:
	pytest tests/ -v

test-all:
	pytest tests/ -v --cov=openpace --cov-report=term-missing

test-unit:
	pytest tests/ -v -m unit

test-integration:
	pytest tests/ -v -m integration

test-database:
	pytest tests/test_database/ -v

test-gui:
	pytest tests/test_gui/ -v

test-hl7:
	pytest tests/test_hl7/ -v

test-smoke:
	pytest tests/ -v -m smoke

test-failed:
	pytest --lf -v

# Coverage
coverage:
	pytest tests/ --cov=openpace --cov-report=html --cov-report=term-missing
	@echo "✓ Coverage report generated in htmlcov/"

coverage-report:
	python -m http.server 8000 -d htmlcov

# Code quality
lint:
	flake8 openpace tests --max-line-length=100 --extend-ignore=E203,W503
	@echo "✓ Linting complete"

format:
	black openpace tests
	isort openpace tests --profile black
	@echo "✓ Code formatting complete"

format-check:
	black --check openpace tests
	isort --check-only openpace tests --profile black

type-check:
	mypy openpace --ignore-missing-imports
	@echo "✓ Type checking complete"

check: format-check lint type-check
	@echo "✓ All quality checks passed"

# Security
security:
	bandit -r openpace -c pyproject.toml
	safety check
	@echo "✓ Security checks complete"

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	find . -type f -name "coverage.xml" -delete
	rm -rf build/ dist/
	@echo "✓ Cleanup complete"

# Documentation
docs:
	cd docs && sphinx-build -b html . _build/html
	@echo "✓ Documentation built in docs/_build/html/"

docs-serve:
	python -m http.server 8000 -d docs/_build/html

# Database
db-init:
	python -c "from openpace.database.connection import DatabaseManager; DatabaseManager().init_db()"
	@echo "✓ Database initialized"

db-reset:
	rm -f ~/.openpace/openpace.db
	$(MAKE) db-init
	@echo "✓ Database reset"

# Development
run:
	python main.py

run-debug:
	python main.py --debug

# Git helpers
git-status:
	git status

git-check:
	git diff --check
	@echo "✓ No whitespace errors"

# CI/CD simulation
ci: clean install check test-all
	@echo "✓ CI pipeline simulation complete"
