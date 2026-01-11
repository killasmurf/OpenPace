"""
Pytest configuration and shared fixtures for OpenPace test suite.

This module provides:
- Database fixtures (in-memory SQLite)
- Sample data fixtures
- GUI application fixtures (for pytest-qt)
- HL7 message fixtures
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest
try:
    from PyQt6.QtWidgets import QApplication
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from openpace.database.models import Base


@pytest.fixture(scope="session")
def qapp():
    """
    Create a QApplication instance for GUI testing.

    This fixture is session-scoped to avoid creating multiple QApplication
    instances which causes Qt errors.
    """
    if not HAS_PYQT:
        pytest.skip("PyQt6 not installed")
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def test_db_engine():
    """
    Create an in-memory SQLite database engine for testing.

    Yields:
        Engine: SQLAlchemy engine connected to in-memory SQLite database
    """
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_db_engine) -> Generator[Session, None, None]:
    """
    Create a database session for testing.

    The session is automatically rolled back after each test to ensure
    test isolation.

    Args:
        test_db_engine: SQLAlchemy engine fixture

    Yields:
        Session: SQLAlchemy session for database operations
    """
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def temp_db_file() -> Generator[Path, None, None]:
    """
    Create a temporary database file for testing file-based operations.

    Yields:
        Path: Path to temporary database file
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        yield tmp_path
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@pytest.fixture
def sample_hl7_oru_r01() -> str:
    """
    Sample HL7 ORU^R01 message for pacemaker data.

    This is a simplified example with anonymized data for testing.

    Returns:
        str: HL7 message in standard HL7 format
    """
    return """MSH|^~\\&|PACEMAKER^1.0|MEDTRONIC|OPENPACE|CLINIC|20240115120000||ORU^R01|MSG00001|P|2.5.1|||AL|AL|USA
PID|1||TEST001^^^CLINIC^MR||DOE^JOHN^A||19600101|M|||123 MAIN ST^^ANYTOWN^CA^12345^USA|||||||123456789
PV1|1|O|CARDIO^^^^CLINIC||||1234^SMITH^JANE^M^^^MD|1234^SMITH^JANE^M^^^MD|||||||||1234^SMITH^JANE^M^^^MD||VIS001|||||||||||||||||||||||||20240115120000
OBR|1|ORD001|SPEC001|DEVICE_INTERROGATION^Device Interrogation^LN|||20240115120000|||||||||1234^SMITH^JANE^M^^^MD
OBX|1|ST|DEVICE_MODEL^Device Model^LN||ADVISA DR MRI A3DR01|||||F|||20240115120000
OBX|2|ST|DEVICE_SERIAL^Device Serial Number^LN||PMC123456|||||F|||20240115120000
OBX|3|NM|BATTERY_VOLTAGE^Battery Voltage^LN||2.78|V|2.5-2.8||||F|||20240115120000
OBX|4|NM|BATTERY_IMPEDANCE^Battery Impedance^LN||5500|Ohm|<10000||||F|||20240115120000
OBX|5|NM|RA_LEAD_IMPEDANCE^RA Lead Impedance^LN||520|Ohm|200-1500||||F|||20240115120000
OBX|6|NM|RV_LEAD_IMPEDANCE^RV Lead Impedance^LN||680|Ohm|200-1500||||F|||20240115120000
OBX|7|NM|PACING_PERCENT_A^Atrial Pacing Percent^LN||15.2|%|||||F|||20240115120000
OBX|8|NM|PACING_PERCENT_V^Ventricular Pacing Percent^LN||98.5|%|||||F|||20240115120000
OBX|9|NM|HEART_RATE_AVG^Average Heart Rate^LN||72|bpm|||||F|||20240115120000
OBX|10|ST|MODE^Pacing Mode^LN||DDDR|||||F|||20240115120000
OBX|11|NM|LOWER_RATE_LIMIT^Lower Rate Limit^LN||60|bpm|||||F|||20240115120000
OBX|12|NM|UPPER_RATE_LIMIT^Upper Rate Limit^LN||130|bpm|||||F|||20240115120000
OBX|13|NM|AF_BURDEN^Atrial Fibrillation Burden^LN||2.3|%|||||F|||20240115120000
"""


@pytest.fixture
def sample_hl7_multiple_segments() -> str:
    """
    Sample HL7 message with multiple OBR/OBX segments for testing complex parsing.

    Returns:
        str: HL7 message with arrhythmia episodes
    """
    return """MSH|^~\\&|PACEMAKER^1.0|BOSTON_SCIENTIFIC|OPENPACE|CLINIC|20240115120000||ORU^R01|MSG00002|P|2.5.1|||AL|AL|USA
PID|1||TEST002^^^CLINIC^MR||SMITH^JANE^B||19650515|F|||456 ELM ST^^TESTCITY^NY^67890^USA
OBR|1|ORD002|SPEC002|ARRHYTHMIA_LOG^Arrhythmia Log^LN|||20240115120000
OBX|1|NM|AF_EPISODE_COUNT^AF Episode Count^LN||5|episodes|||||F|||20240115120000
OBX|2|TS|AF_EPISODE_1_START^AF Episode 1 Start^LN||20240110083000|||||F|||20240115120000
OBX|3|NM|AF_EPISODE_1_DURATION^AF Episode 1 Duration^LN||320|seconds|||||F|||20240115120000
OBX|4|NM|AF_EPISODE_1_HR_AVG^AF Episode 1 Avg HR^LN||145|bpm|||||F|||20240115120000
OBR|2|ORD003|SPEC003|EGM^Electrogram^LN|||20240115120000
OBX|1|ED|EGM_STRIP_1^EGM Strip 1^LN||^APPLICATION^BASE64^SGVsbG8gV29ybGQgLSBUaGlzIGlzIGEgc2FtcGxlIEVHTSBkYXRh|||||F|||20240115120000
"""


@pytest.fixture
def sample_patient_data() -> dict:
    """
    Sample patient demographic data for database testing.

    Returns:
        dict: Patient data dictionary
    """
    return {
        "patient_id": "TEST001",
        "last_name_hash": "DOE",
        "first_name_hash": "JOHN",
        "date_of_birth_offset": 0,
        "anonymized": False,
        "notes": "Test patient for unit testing"
    }


@pytest.fixture
def sample_transmission_data() -> dict:
    """
    Sample transmission data for database testing.

    Returns:
        dict: Transmission data dictionary
    """
    return {
        "transmission_date": "2024-01-15 12:00:00",
        "device_model": "ADVISA DR MRI A3DR01",
        "device_serial": "PMC123456",
        "raw_hl7": "MSH|...|",
        "import_source": "test_file.hl7"
    }


@pytest.fixture
def sample_observation_data() -> dict:
    """
    Sample observation data for database testing.

    Returns:
        dict: Observation data dictionary
    """
    return {
        "observation_id": "OBX001",
        "variable_name": "BATTERY_VOLTAGE",
        "variable_code": "BATTERY_VOLTAGE",
        "value_string": "2.78",
        "value_numeric": 2.78,
        "units": "V",
        "reference_range": "2.5-2.8",
        "observation_timestamp": "2024-01-15 12:00:00"
    }


@pytest.fixture
def temp_test_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for file-based testing.

    Yields:
        Path: Path to temporary directory
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_hl7_file(temp_test_dir, sample_hl7_oru_r01) -> Path:
    """
    Create a temporary HL7 file for import testing.

    Args:
        temp_test_dir: Temporary directory fixture
        sample_hl7_oru_r01: Sample HL7 message fixture

    Returns:
        Path: Path to temporary HL7 file
    """
    hl7_file = temp_test_dir / "test_message.hl7"
    hl7_file.write_text(sample_hl7_oru_r01, encoding="utf-8")
    return hl7_file


@pytest.fixture(autouse=True)
def reset_env_vars():
    """
    Reset environment variables before each test to ensure clean state.

    This fixture automatically runs before each test.
    """
    # Store original environment
    original_env = os.environ.copy()

    # Clear OpenPace-specific environment variables
    env_vars_to_clear = [
        "OPENPACE_DB_PATH",
        "OPENPACE_ANONYMIZE",
        "OPENPACE_LOG_LEVEL",
        "OPENPACE_IMPORT_PATH",
        "OPENPACE_EXPORT_PATH"
    ]

    for var in env_vars_to_clear:
        os.environ.pop(var, None)

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
