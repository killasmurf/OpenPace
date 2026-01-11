# OpenPace Testing - Quick Reference Card

## Common Commands

### Run Tests
```bash
# All tests
pytest

# Specific category
pytest tests/test_database/
pytest tests/test_gui/
pytest tests/test_hl7/

# With coverage
pytest --cov=openpace --cov-report=html

# Using Makefile
make test
make coverage
```

### Test Selection
```bash
# By marker
pytest -m database
pytest -m "not slow"

# By pattern
pytest -k "patient"

# Specific test
pytest tests/test_database/test_models.py::TestPatientModel::test_create_patient_basic

# Failed tests only
pytest --lf
```

### Coverage
```bash
# Generate HTML report
pytest --cov=openpace --cov-report=html

# View report
python -m http.server 8000 -d htmlcov

# Check threshold
coverage report --fail-under=80
```

### Debugging
```bash
# Verbose output
pytest -v

# Show local variables
pytest --showlocals

# Stop on first failure
pytest -x

# Debug on failure
pytest --pdb

# Show print statements
pytest -s
```

### Using Test Runner
```bash
python tests/run_tests.py --all
python tests/run_tests.py --database
python tests/run_tests.py --gui
python tests/run_tests.py --coverage
python tests/run_tests.py --failed
```

## Makefile Shortcuts

```bash
make install          # Install dependencies
make test             # Run all tests
make test-database    # Database tests only
make test-gui         # GUI tests only
make coverage         # Generate coverage report
make lint             # Run linters
make format           # Format code
make check            # All quality checks
make clean            # Clean artifacts
make ci               # Simulate CI pipeline
```

## Test Markers

```python
@pytest.mark.unit          # Unit test
@pytest.mark.integration   # Integration test
@pytest.mark.database      # Database test
@pytest.mark.gui           # GUI test
@pytest.mark.hl7           # HL7 parser test
@pytest.mark.slow          # Slow test
@pytest.mark.smoke         # Smoke test
```

## Common Fixtures

```python
def test_example(db_session):              # Database session
def test_example(qapp, qtbot):            # GUI testing
def test_example(sample_hl7_oru_r01):     # Sample HL7 message
def test_example(temp_db_file):           # Temp database file
def test_example(temp_test_dir):          # Temp directory
def test_example(mock_hl7_file):          # Temp HL7 file
def test_example(sample_patient_data):    # Sample patient dict
```

## Writing Tests

### Basic Test Structure
```python
def test_example():
    # Arrange
    patient = Patient(patient_id="TEST", ...)

    # Act
    result = patient.get_full_name()

    # Assert
    assert result == "JOHN DOE"
```

### Test with Fixture
```python
def test_with_database(db_session):
    patient = Patient(patient_id="TEST", ...)
    db_session.add(patient)
    db_session.commit()

    retrieved = db_session.query(Patient).first()
    assert retrieved is not None
```

### Test Exception
```python
def test_error():
    with pytest.raises(ValueError, match="Invalid"):
        function_that_raises()
```

### Parametrized Test
```python
@pytest.mark.parametrize("input,expected", [
    ("DDD", True),
    ("INVALID", False),
])
def test_validation(input, expected):
    assert validate(input) == expected
```

### GUI Test
```python
def test_button(qapp, qtbot):
    from PyQt6.QtCore import Qt
    button = QPushButton("Click")
    qtbot.addWidget(button)
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
```

## File Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── run_tests.py                   # Test runner
├── sample_data/                   # Test data files
│   ├── medtronic_sample.hl7
│   ├── boston_scientific_sample.hl7
│   └── abbott_sample.hl7
├── test_database/                 # Database tests
│   ├── test_models.py
│   └── test_connection.py
├── test_hl7/                      # HL7 parser tests
│   └── test_parser.py
└── test_gui/                      # GUI tests
    └── test_main_window.py
```

## CI/CD

### GitHub Actions
- Runs on: Push, PR, Nightly
- Platforms: Ubuntu, Windows, macOS
- Python: 3.11, 3.12
- Reports: Coverage uploaded to Codecov

### Pre-commit Hooks
```bash
# Install
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

## Troubleshooting

### Qt Platform Error
```bash
export QT_QPA_PLATFORM=offscreen
```

### Database Locked
- Use fixtures (auto-rollback)
- Close all sessions properly

### Import Error
```bash
pip install -e .
```

### Slow Tests
```bash
pytest --durations=10  # Find slow tests
pytest -m "not slow"   # Skip slow tests
```

## Coverage Targets

| Component | Target |
|-----------|--------|
| Overall   | 80%    |
| Database  | 90%    |
| HL7       | 85%    |
| GUI       | 70%    |
| Analysis  | 90%    |

## Key Directories

- `tests/` - All test files
- `htmlcov/` - Coverage HTML reports
- `.github/workflows/` - CI/CD configs
- `docs/` - Documentation

## Documentation

- `tests/README.md` - Test suite overview
- `docs/TESTING.md` - Comprehensive guide
- `TEST_HARNESS_SUMMARY.md` - Implementation details
- `TESTING_QUICK_REFERENCE.md` - This file

## Example Workflow

```bash
# 1. Make changes to code
vim openpace/database/models.py

# 2. Run relevant tests
pytest tests/test_database/

# 3. Check coverage
pytest tests/test_database/ --cov=openpace.database

# 4. Format code
make format

# 5. Run all checks
make check

# 6. Commit (pre-commit runs automatically)
git add .
git commit -m "Update database models"
```

---

**Keep this file handy for quick reference during development!**
