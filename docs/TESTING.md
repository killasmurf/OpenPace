# OpenPace Testing Guide

Comprehensive guide for testing the OpenPace application.

## Table of Contents

- [Overview](#overview)
- [Test Architecture](#test-architecture)
- [Quick Start](#quick-start)
- [Test Categories](#test-categories)
- [Writing Tests](#writing-tests)
- [Running Tests](#running-tests)
- [Coverage](#coverage)
- [CI/CD Integration](#cicd-integration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

OpenPace uses a comprehensive testing strategy to ensure code quality, reliability, and maintainability. The test suite covers:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interaction between components
- **GUI Tests**: Test user interface components
- **Database Tests**: Test data persistence and integrity
- **End-to-End Tests**: Test complete workflows

### Testing Stack

- **pytest**: Test framework and runner
- **pytest-qt**: PyQt6 GUI testing support
- **pytest-cov**: Code coverage reporting
- **SQLAlchemy**: Database testing with in-memory SQLite
- **unittest.mock**: Mocking and patching

## Test Architecture

```
OpenPace Testing Architecture
┌─────────────────────────────────────────────────────────┐
│                    Test Harness                         │
│  (conftest.py - Fixtures & Configuration)               │
└─────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
    ┌──────────┐         ┌──────────┐        ┌──────────┐
    │ Database │         │   HL7    │        │   GUI    │
    │  Tests   │         │  Tests   │        │  Tests   │
    └──────────┘         └──────────┘        └──────────┘
           │                    │                    │
           ▼                    ▼                    ▼
    ┌──────────┐         ┌──────────┐        ┌──────────┐
    │  Models  │         │ Parser   │        │ Widgets  │
    │Connection│         │Translator│        │  Views   │
    └──────────┘         └──────────┘        └──────────┘
```

## Quick Start

### Installation

```bash
# Install test dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e ".[dev]"
```

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=openpace --cov-report=html
```

### View Coverage Report

```bash
# Generate and open HTML report
pytest --cov=openpace --cov-report=html
python -m http.server 8000 -d htmlcov
# Open http://localhost:8000 in browser
```

## Test Categories

### 1. Database Tests

**Location**: `tests/test_database/`

Test database models, relationships, and connection management.

```bash
# Run all database tests
pytest tests/test_database/

# Run specific model tests
pytest tests/test_database/test_models.py

# Run connection tests
pytest tests/test_database/test_connection.py
```

**Coverage Areas**:
- Model creation and validation
- Foreign key constraints
- Cascade deletes
- JSON field handling
- Index creation
- Transaction management
- Connection pooling

### 2. HL7 Parser Tests

**Location**: `tests/test_hl7/`

Test HL7 message parsing and vendor translation.

```bash
# Run all HL7 tests
pytest tests/test_hl7/

# Run parser tests
pytest tests/test_hl7/test_parser.py
```

**Coverage Areas**:
- MSH segment parsing
- PID segment parsing
- OBR/OBX segment parsing
- Vendor code translation
- Binary data extraction
- Error handling

### 3. GUI Tests

**Location**: `tests/test_gui/`

Test user interface components and interactions.

```bash
# Run all GUI tests
pytest tests/test_gui/

# Run main window tests
pytest tests/test_gui/test_main_window.py
```

**Coverage Areas**:
- Window initialization
- Menu bar functionality
- Toolbar actions
- Status bar updates
- User interactions
- Signal/slot connections

### 4. Integration Tests

Test complete workflows and component interactions.

```bash
# Run integration tests
pytest -m integration
```

**Coverage Areas**:
- HL7 import → Database storage
- Database → GUI display
- Analysis → Visualization
- Export workflows

## Writing Tests

### Test Structure

Follow the **Arrange-Act-Assert** pattern:

```python
def test_example():
    # Arrange: Set up test data and dependencies
    patient = Patient(patient_id="TEST001", ...)

    # Act: Execute the code being tested
    result = patient.get_full_name()

    # Assert: Verify the expected outcome
    assert result == "JOHN DOE"
```

### Using Fixtures

Fixtures provide reusable test data and setup:

```python
def test_with_database(db_session):
    """Use database session fixture."""
    patient = Patient(patient_id="TEST001", ...)
    db_session.add(patient)
    db_session.commit()

    # Test database operations
    retrieved = db_session.query(Patient).first()
    assert retrieved.patient_id == "TEST001"


def test_with_hl7_message(sample_hl7_oru_r01):
    """Use sample HL7 message fixture."""
    assert "MSH|" in sample_hl7_oru_r01
    assert "PID|" in sample_hl7_oru_r01
```

### Available Fixtures

See `tests/conftest.py` for all available fixtures:

| Fixture | Description |
|---------|-------------|
| `db_session` | Database session (auto-rollback) |
| `test_db_engine` | SQLAlchemy engine |
| `temp_db_file` | Temporary database file |
| `temp_test_dir` | Temporary directory |
| `qapp` | QApplication instance |
| `sample_hl7_oru_r01` | Sample HL7 message |
| `sample_patient_data` | Sample patient dictionary |
| `mock_hl7_file` | Temporary HL7 file |

### Parametrized Tests

Test multiple inputs efficiently:

```python
@pytest.mark.parametrize("input,expected", [
    ("DDDR", True),
    ("DDD", True),
    ("VVI", True),
    ("INVALID", False),
])
def test_pacing_mode_validation(input, expected):
    result = validate_pacing_mode(input)
    assert result == expected
```

### Testing Exceptions

```python
def test_invalid_patient_id():
    """Test that invalid patient ID raises ValueError."""
    with pytest.raises(ValueError, match="Invalid patient ID"):
        Patient(patient_id="")
```

### Mocking

Use mocks for external dependencies:

```python
from unittest.mock import Mock, patch

def test_file_import_with_mock():
    """Test file import with mocked file operations."""
    with patch('builtins.open', Mock(return_value=io.StringIO("MSH|..."))):
        result = import_hl7_file("fake_file.hl7")
        assert result is not None
```

### GUI Testing

Test PyQt6 components with pytest-qt:

```python
def test_button_click(qapp, qtbot):
    """Test button click interaction."""
    from PyQt6.QtWidgets import QPushButton
    from PyQt6.QtCore import Qt

    button = QPushButton("Click Me")
    qtbot.addWidget(button)

    # Track signal emission
    with qtbot.waitSignal(button.clicked, timeout=1000):
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
```

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_database/test_models.py

# Run specific test class
pytest tests/test_database/test_models.py::TestPatientModel

# Run specific test method
pytest tests/test_database/test_models.py::TestPatientModel::test_create_patient_basic
```

### Using Markers

```bash
# Run only unit tests
pytest -m unit

# Run all except slow tests
pytest -m "not slow"

# Run database OR HL7 tests
pytest -m "database or hl7"

# List all markers
pytest --markers
```

### Pattern Matching

```bash
# Run tests matching pattern
pytest -k "patient"

# Run tests NOT matching pattern
pytest -k "not integration"

# Multiple patterns
pytest -k "patient and database"
```

### Test Selection

```bash
# Run only failed tests from last run
pytest --lf

# Run failed tests first, then all
pytest --ff

# Stop after first failure
pytest -x

# Stop after N failures
pytest --maxfail=3
```

### Output Options

```bash
# Show local variables on failure
pytest --showlocals

# Show print statements
pytest -s

# Capture logs
pytest --log-cli-level=INFO

# Show test durations
pytest --durations=10
```

### Debugging

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger on first failure
pytest -x --pdb

# Set breakpoint in test
def test_example():
    import pdb; pdb.set_trace()
    # Test code here
```

## Coverage

### Generate Coverage Report

```bash
# Terminal report
pytest --cov=openpace --cov-report=term-missing

# HTML report
pytest --cov=openpace --cov-report=html

# XML report (for CI)
pytest --cov=openpace --cov-report=xml

# All formats
pytest --cov=openpace --cov-report=term-missing --cov-report=html --cov-report=xml
```

### Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| Overall | 80% | TBD |
| Database | 90% | TBD |
| HL7 Parser | 85% | TBD |
| GUI | 70% | TBD |
| Analysis | 90% | TBD |

### Viewing Coverage

```bash
# View HTML report
python -m http.server 8000 -d htmlcov
# Open http://localhost:8000

# View terminal report
coverage report

# Show missing lines
coverage report -m
```

## CI/CD Integration

### GitHub Actions

Tests run automatically on:
- Push to main/master/develop
- Pull requests
- Nightly schedule (2 AM UTC)

Configuration: `.github/workflows/tests.yml`

### Pre-commit Hooks

Install pre-commit hooks to run tests before commits:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

Configuration: `.pre-commit-config.yaml`

### Coverage Reports

Coverage reports are:
- Generated on every CI run
- Uploaded to Codecov
- Commented on pull requests
- Failing if below 70%

## Best Practices

### 1. Test Independence

Each test should be independent:

```python
# Good: Independent test
def test_patient_creation(db_session):
    patient = Patient(patient_id="TEST001", ...)
    db_session.add(patient)
    db_session.commit()
    # Test completes independently

# Bad: Depends on previous test
def test_patient_update():
    # Assumes patient from previous test exists
    patient = db_session.query(Patient).first()
```

### 2. Clear Test Names

Use descriptive names:

```python
# Good
def test_patient_creation_with_valid_data_succeeds():
    ...

# Bad
def test1():
    ...
```

### 3. One Logical Assertion

Focus each test on one behavior:

```python
# Good: Tests one aspect
def test_patient_full_name():
    patient = Patient(first_name="John", last_name="Doe")
    assert patient.get_full_name() == "John Doe"

# Good: Multiple asserts for same behavior
def test_patient_creation():
    patient = Patient(patient_id="TEST001", ...)
    assert patient.id is not None
    assert patient.patient_id == "TEST001"  # Part of creation
```

### 4. Fast Tests

Keep unit tests fast:

```python
# Good: Fast unit test
def test_patient_validation():
    assert validate_patient_id("TEST001") is True

# Consider separate suite: Slow integration test
@pytest.mark.slow
def test_import_large_hl7_file():
    # Import 1000 messages
```

### 5. Use Fixtures

Reuse setup code:

```python
# Good: Use fixture
def test_transmission_creation(db_session, sample_patient_data):
    patient = Patient(**sample_patient_data)
    ...

# Bad: Duplicate setup
def test_transmission_creation(db_session):
    patient = Patient(
        patient_id="TEST001",
        last_name_hash="DOE",
        ...
    )
```

### 6. Test Edge Cases

Include boundary conditions:

```python
def test_battery_voltage_validation():
    # Normal case
    assert validate_battery_voltage(2.75) is True

    # Edge cases
    assert validate_battery_voltage(0) is False
    assert validate_battery_voltage(-1) is False
    assert validate_battery_voltage(5.0) is False
    assert validate_battery_voltage(None) is False
```

### 7. Meaningful Assertions

Use specific assertions:

```python
# Good
assert patient.patient_id == "TEST001"

# Less good
assert patient.patient_id  # Just tests truthiness
```

## Troubleshooting

### Common Issues

#### Qt Platform Plugin Error

```
qt.qpa.plugin: Could not find the Qt platform plugin "windows"
```

**Solutions**:
```bash
# Set offscreen platform
export QT_QPA_PLATFORM=offscreen

# Or in pytest.ini
[pytest]
env = QT_QPA_PLATFORM=offscreen
```

#### Database Locked

```
sqlite3.OperationalError: database is locked
```

**Solutions**:
- Ensure all sessions are properly closed
- Use fixtures that auto-rollback
- Check for unclosed transactions

#### Import Errors

```
ModuleNotFoundError: No module named 'openpace'
```

**Solutions**:
```bash
# Install in development mode
pip install -e .

# Or run from project root
cd /path/to/OpenPace
pytest
```

#### Slow Tests

**Solutions**:
```bash
# Find slow tests
pytest --durations=10

# Skip slow tests
pytest -m "not slow"

# Run in parallel (install pytest-xdist)
pytest -n auto
```

### Getting Help

- Check [tests/README.md](../tests/README.md)
- Review [CONTRIBUTING.md](../CONTRIBUTING.md)
- Search [GitHub Issues](https://github.com/yourusername/openpace/issues)
- Ask in project discussions

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-qt Documentation](https://pytest-qt.readthedocs.io/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html)
- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)

---

**Last Updated**: 2024-01-11
**Maintainer**: OpenPace Development Team
