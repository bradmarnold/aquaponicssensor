# Aquaponics Sensor System - Makefile
# ====================================

# Default Python executable
PYTHON ?= python3
PIP ?= pip3

# Directories
PI_DIR = pi
TESTS_DIR = tests
E2E_DIR = e2e
SCRIPTS_DIR = scripts

# Virtual environment
VENV_DIR = venv
VENV_PYTHON = $(VENV_DIR)/bin/python
VENV_PIP = $(VENV_DIR)/bin/pip

# Default target
.PHONY: help
help:
	@echo "Aquaponics Sensor System - Build Commands"
	@echo "========================================="
	@echo ""
	@echo "Setup:"
	@echo "  make setup          Install all dependencies (Python + Node.js)"
	@echo "  make venv           Create Python virtual environment"
	@echo "  make install-py     Install Python dependencies"
	@echo "  make install-e2e    Install E2E test dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make serve          Start local development server"
	@echo "  make data           Generate sample data for testing"
	@echo "  make coach          Generate sample coaching advice"
	@echo ""
	@echo "Testing:"
	@echo "  make test           Run all Python tests"
	@echo "  make test-unit      Run unit tests only"
	@echo "  make test-cov       Run tests with coverage report"
	@echo "  make e2e            Run end-to-end tests"
	@echo "  make e2e-headed     Run E2E tests in headed mode"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           Run code linting (ruff)"
	@echo "  make format         Format code (black)"
	@echo "  make type           Run type checking (mypy)"
	@echo "  make check          Run all code quality checks"
	@echo ""
	@echo "CI/CD:"
	@echo "  make ci             Run all CI checks (lint + type + test + e2e)"
	@echo "  make clean          Clean up temporary files"
	@echo ""
	@echo "Sensor Operations:"
	@echo "  make sensor-test    Test sensor reading (mock mode)"
	@echo "  make sensor-once    Take one sensor reading"
	@echo "  make validate       Validate data and coach JSON schemas"

# Setup targets
.PHONY: setup
setup: venv install-py install-e2e
	@echo "✓ Setup complete!"
	@echo "  Run 'make serve' to start development server"
	@echo "  Run 'make test' to run tests"
	@echo "  Run 'make e2e' to run end-to-end tests"

.PHONY: venv
venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating Python virtual environment..."; \
		$(PYTHON) -m venv $(VENV_DIR); \
		echo "✓ Virtual environment created"; \
	else \
		echo "✓ Virtual environment already exists"; \
	fi

.PHONY: install-py
install-py: venv
	@echo "Installing Python dependencies..."
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install pytest jsonschema ruff black mypy
	@echo "✓ Python dependencies installed"

.PHONY: install-e2e
install-e2e:
	@echo "Installing E2E test dependencies..."
	cd $(E2E_DIR) && npm install
	cd $(E2E_DIR) && npx playwright install --with-deps
	@echo "✓ E2E dependencies installed"

# Development targets
.PHONY: serve
serve:
	@echo "Starting development server..."
	$(PYTHON) $(SCRIPTS_DIR)/serve_static.py

.PHONY: data
data:
	@echo "Generating sample data..."
	$(PYTHON) $(SCRIPTS_DIR)/generate_dummy_data.py --realistic --days 7
	@echo "✓ Sample data generated in data.json"

.PHONY: coach
coach:
	@echo "Generating sample coaching advice..."
	@echo "Note: This requires OPENAI_API_KEY environment variable"
	$(PYTHON) $(PI_DIR)/coach.py || echo "⚠ Coach generation failed (likely missing API key)"

# Testing targets
.PHONY: test
test: venv
	@echo "Running Python tests..."
	$(VENV_PYTHON) -m pytest $(TESTS_DIR) -v

.PHONY: test-unit
test-unit: venv
	@echo "Running unit tests..."
	$(VENV_PYTHON) -m pytest $(TESTS_DIR) -v -k "not integration"

.PHONY: test-cov
test-cov: venv
	@echo "Running tests with coverage..."
	$(VENV_PYTHON) -m pytest $(TESTS_DIR) --cov=$(PI_DIR) --cov-report=html --cov-report=term

.PHONY: e2e
e2e:
	@echo "Running end-to-end tests..."
	cd $(E2E_DIR) && npm test

.PHONY: e2e-headed
e2e-headed:
	@echo "Running E2E tests in headed mode..."
	cd $(E2E_DIR) && npm run test:headed

# Code quality targets
.PHONY: lint
lint: venv
	@echo "Running code linting..."
	$(VENV_PYTHON) -m ruff check $(PI_DIR) $(TESTS_DIR) $(SCRIPTS_DIR)

.PHONY: format
format: venv
	@echo "Formatting code..."
	$(VENV_PYTHON) -m black $(PI_DIR) $(TESTS_DIR) $(SCRIPTS_DIR)
	$(VENV_PYTHON) -m ruff check --fix $(PI_DIR) $(TESTS_DIR) $(SCRIPTS_DIR)

.PHONY: type
type: venv
	@echo "Running type checking..."
	$(VENV_PYTHON) -m mypy $(PI_DIR) --ignore-missing-imports

.PHONY: check
check: lint type
	@echo "✓ All code quality checks passed"

# CI/CD targets
.PHONY: ci
ci: check test e2e
	@echo "✓ All CI checks passed"

.PHONY: clean
clean:
	@echo "Cleaning up temporary files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true
	rm -rf $(E2E_DIR)/test-results/ $(E2E_DIR)/playwright-report/ 2>/dev/null || true
	@echo "✓ Cleanup complete"

# Sensor operation targets
.PHONY: sensor-test
sensor-test: venv
	@echo "Testing sensor reading (mock mode)..."
	MOCK_HARDWARE=1 $(VENV_PYTHON) $(PI_DIR)/sensor_logger.py --once

.PHONY: sensor-once
sensor-once: venv
	@echo "Taking one sensor reading..."
	$(VENV_PYTHON) $(PI_DIR)/sensor_logger.py --once

.PHONY: validate
validate: venv
	@echo "Validating JSON schemas..."
	$(VENV_PYTHON) -m pytest $(TESTS_DIR)/test_data_schema.py -v
	$(VENV_PYTHON) -m pytest $(TESTS_DIR)/test_coach_schema.py -v
	@echo "✓ Schema validation complete"

# Help for individual targets
.PHONY: help-setup
help-setup:
	@echo "Setup Commands:"
	@echo "  make setup      - Complete setup (Python + Node.js dependencies)"
	@echo "  make venv       - Create Python virtual environment only"
	@echo "  make install-py - Install Python dependencies only"
	@echo "  make install-e2e- Install E2E test dependencies only"

.PHONY: help-dev
help-dev:
	@echo "Development Commands:"
	@echo "  make serve      - Start HTTP server on localhost:8000"
	@echo "  make data       - Generate realistic sample data for 7 days"
	@echo "  make coach      - Generate coaching advice (requires OpenAI API key)"

.PHONY: help-test
help-test:
	@echo "Testing Commands:"
	@echo "  make test       - Run all Python unit tests"
	@echo "  make test-cov   - Run tests with coverage report"
	@echo "  make e2e        - Run Playwright end-to-end tests"
	@echo "  make e2e-headed - Run E2E tests with browser visible"
	@echo "  make validate   - Validate JSON schemas"

.PHONY: help-quality
help-quality:
	@echo "Code Quality Commands:"
	@echo "  make lint       - Check code style with ruff"
	@echo "  make format     - Auto-format code with black + ruff"
	@echo "  make type       - Type check with mypy"
	@echo "  make check      - Run all quality checks"

# Dependencies for targets
$(VENV_DIR): venv

install-py: $(VENV_DIR)

test: install-py

e2e: install-e2e

lint: install-py

format: install-py

type: install-py