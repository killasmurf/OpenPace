# OpenPace Test Suite

Comprehensive test suite for the OpenPace pacemaker data analysis application.

## Overview

The OpenPace test suite provides automated testing for all major components including:
- Database models and connections
- HL7 message parsing
- GUI components
- Data processing and analysis
- Privacy and anonymization features

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── run_tests.py               # Test runner script
├── README.md                  # This file
├── sample_data/               # Sample HL7 files for testing
│   ├── medtronic_sample.hl7
│   ├── boston_scientific_sample.hl7
│   └── abbott_sample.hl7
├── test_database/             # Database tests
│   ├── test_models.py         # ORM model tests
│   └── test_connection.py     # Connection management tests
├── test_hl7/                  # HL7 parser tests
│   └── test_parser.py         # Parser and translator tests
└── test_gui/                  # GUI tests
    └── test_main_window.py    # Main window tests
```

## Running Tests

### Quick Start

Run all tests:
```bash
pytest
```

Run with coverage report:
```bash
pytest --cov=openpace --cov-report=html
```

### Using the Test Runner

The test runner script provides convenient shortcuts:

```bash
# Run all tests
python tests/run_tests.py --all

# Run specific test categories
python tests/run_tests.py --database
python tests/run_tests.py --gui
python tests/run_tests.py --hl7

# Run with coverage report
python tests/run_tests.py --all --coverage

# Run tests without coverage (faster)
python tests/run_tests.py --all --no-cov

# Run only smoke tests
python tests/run_tests.py --smoke

# Re-run only failed tests
python tests/run_tests.py --failed

# List all test markers
python tests/run_tests.py --markers
```

### Running Specific Tests

Run a specific test file:
```bash
pytest tests/test_database/test_models.py
```

Run a specific test class:
```bash
pytest tests/test_database/test_models.py::TestPatientModel
```

Run a specific test method:
```bash
pytest tests/test_database/test_models.py::TestPatientModel::test_create_patient_basic
```

Run tests matching a pattern:
```bash
pytest -k "patient"
```

## Test Markers

Tests are organized using markers:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (slower, test multiple components)
- `@pytest.mark.database` - Tests requiring database
- `@pytest.mark.gui` - Tests requiring GUI/display
- `@pytest.mark.hl7` - Tests for HL7 parsing
- `@pytest.mark.slow` - Slow tests (can be excluded)
- `@pytest.mark.smoke` - Smoke tests for quick validation

Run tests by marker:
```bash
# Run only unit tests
pytest -m unit

# Run all except slow tests
pytest -m "not slow"

# Run database and HL7 tests
pytest -m "database or hl7"
```

## Coverage Reports

Coverage reports are generated in multiple formats:

- **Terminal**: Shows coverage summary in console
- **HTML**: Detailed interactive report in `htmlcov/index.html`
- **XML**: Machine-readable report for CI/CD in `coverage.xml`

View HTML coverage report:
```bash
# After running tests with coverage
python -m http.server 8000 -d htmlcov
# Then open http://localhost:8000 in browser
```

Target coverage: **80%+** overall, with focus on:
- Database integrity (HL7→DB pipeline)
- Analysis algorithms
- Privacy/anonymization features
- Error handling

## Writing Tests

### Test Structure

Follow this structure for new tests:

```python
import pytest
from openpace.module import Component


class TestComponent:
    """Test suite for Component."""

    def test_basic_functionality(self):
        """Test basic component functionality."""
        component = Component()
        result = component.do_something()
        assert result == expected_value

    def test_error_handling(self):
        """Test component error handling."""
        component = Component()
        with pytest.raises(ValueError):
            component.do_invalid_thing()
```

### Using Fixtures

Common fixtures are available in `conftest.py`:

```python
def test_with_database(db_session):
    """Test using database session."""
    from openpace.database.models import Patient

    patient = Patient(patient_id="TEST", ...)
    db_session.add(patient)
    db_session.commit()
    # Session automatically rolled back after test

def test_with_hl7_data(sample_hl7_oru_r01):
    """Test using sample HL7 message."""
    # sample_hl7_oru_r01 contains a complete HL7 message
    assert "MSH|" in sample_hl7_oru_r01

def test_gui_component(qapp, qtbot):
    """Test GUI component."""
    from openpace.gui.main_window import MainWindow

    window = MainWindow()
    window.show()
    qtbot.addWidget(window)
    # Test GUI interactions
```

### Available Fixtures

- `db_session` - Database session (auto-rollback)
- `test_db_engine` - SQLAlchemy engine
- `temp_db_file` - Temporary database file
- `temp_test_dir` - Temporary directory
- `qapp` - QApplication instance for GUI tests
- `sample_hl7_oru_r01` - Sample HL7 message
- `sample_hl7_multiple_segments` - Complex HL7 message
- `sample_patient_data` - Sample patient dictionary
- `sample_transmission_data` - Sample transmission dictionary
- `sample_observation_data` - Sample observation dictionary
- `mock_hl7_file` - Temporary HL7 file

## GUI Testing

GUI tests use `pytest-qt` for PyQt6 testing:

```python
def test_button_click(qapp, qtbot):
    """Test button click interaction."""
    from PyQt6.QtWidgets import QPushButton

    button = QPushButton("Click Me")
    qtbot.addWidget(button)

    clicked = False
    def on_click():
        nonlocal clicked
        clicked = True

    button.clicked.connect(on_click)
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)

    assert clicked
```

## Continuous Integration

Tests run automatically on:
- Every commit (via pre-commit hook)
- Every pull request
- Scheduled nightly builds

CI pipeline:
1. Install dependencies
2. Run linters (black, flake8, mypy)
3. Run test suite with coverage
4. Generate coverage report
5. Upload coverage to reporting service
6. Fail if coverage < 70%

## Debugging Tests

Run with verbose output:
```bash
pytest -vv
```

Show local variables in failures:
```bash
pytest --showlocals
```

Drop into debugger on failure:
```bash
pytest --pdb
```

Show print statements:
```bash
pytest -s
```

## Performance

Run tests with timing:
```bash
pytest --durations=10
```

This shows the 10 slowest tests, helpful for optimization.

## Best Practices

1. **Test Independence**: Each test should be independent and not rely on other tests
2. **Clear Names**: Use descriptive test names that explain what is being tested
3. **One Assertion**: Prefer one logical assertion per test (but multiple assert statements are OK)
4. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification phases
5. **Mock External Dependencies**: Use mocks for external services, file I/O, etc.
6. **Test Edge Cases**: Include tests for boundary conditions and error cases
7. **Keep Tests Fast**: Unit tests should run in milliseconds
8. **Update Tests**: When fixing bugs, add a test that reproduces the bug first

## Troubleshooting

### Common Issues

**Qt Platform Plugin Error**:
```
qt.qpa.plugin: Could not find the Qt platform plugin "windows"
```
Solution: Ensure PyQt6 is properly installed, or set `QT_QPA_PLATFORM=offscreen`

**Database Locked**:
```
sqlite3.OperationalError: database is locked
```
Solution: Ensure all database sessions are properly closed, use fixtures

**Import Errors**:
```
ModuleNotFoundError: No module named 'openpace'
```
Solution: Run tests from project root, or install package in development mode:
```bash
pip install -e .
```

## Contributing

When adding new features:
1. Write tests first (TDD)
2. Ensure tests pass: `pytest`
3. Check coverage: `pytest --cov=openpace`
4. Run linters: `black . && flake8 && mypy openpace`
5. Update this README if adding new test categories

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-qt Documentation](https://pytest-qt.readthedocs.io/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)
- [Coverage.py](https://coverage.readthedocs.io/)

## Contact

For questions about testing, please see:
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [GitHub Issues](https://github.com/yourusername/openpace/issues) - Bug reports and feature requests
