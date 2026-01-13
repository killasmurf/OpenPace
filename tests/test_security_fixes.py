"""
Test suite for security fixes in OpenPace

Tests for:
- HL7 message validation (size limits, format validation)
- Input sanitization (patient IDs, names)
- File validation (path traversal, size limits)
- SQL injection prevention
"""

import pytest
import tempfile
import os
from pathlib import Path
from openpace.hl7.parser import DataSanitizer, HL7Parser
from openpace.exceptions import (
    HL7ValidationError,
    PatientIDValidationError,
    ValidationError,
    FileValidationError,
)
from openpace.constants import FileLimits
from openpace.gui.main_window import MainWindow
from openpace.database.models import Patient
from sqlalchemy.orm import Session


# =============================================================================
# DATA SANITIZER TESTS
# =============================================================================


class TestDataSanitizer:
    """Test DataSanitizer class for input validation and sanitization."""

    def test_sanitize_valid_patient_id(self):
        """Test sanitization of valid patient IDs."""
        valid_ids = [
            "PT12345",
            "PATIENT-001",
            "USER_123",
            "ID.123.456",
            "ABC-123_456.789",
        ]
        for patient_id in valid_ids:
            result = DataSanitizer.sanitize_patient_id(patient_id)
            assert result == patient_id
            assert len(result) <= FileLimits.MAX_PATIENT_ID_LENGTH

    def test_sanitize_patient_id_removes_control_chars(self):
        """Test that control characters are removed from patient IDs."""
        # Patient ID with control characters (null, newline, etc.)
        dirty_id = "PT\x0012345\n\r"
        clean_id = DataSanitizer.sanitize_patient_id(dirty_id)
        assert clean_id == "PT12345"
        assert '\x00' not in clean_id
        assert '\n' not in clean_id
        assert '\r' not in clean_id

    def test_sanitize_patient_id_rejects_empty(self):
        """Test that empty patient IDs are rejected."""
        with pytest.raises(PatientIDValidationError, match="cannot be empty"):
            DataSanitizer.sanitize_patient_id("")

    def test_sanitize_patient_id_rejects_too_long(self):
        """Test that overly long patient IDs are rejected."""
        long_id = "A" * (FileLimits.MAX_PATIENT_ID_LENGTH + 1)
        with pytest.raises(PatientIDValidationError, match="exceeds maximum length"):
            DataSanitizer.sanitize_patient_id(long_id)

    def test_sanitize_patient_id_rejects_invalid_chars(self):
        """Test that patient IDs with invalid characters are rejected."""
        invalid_ids = [
            "PT;DROP TABLE patients;--",  # SQL injection attempt
            "PT<script>alert('xss')</script>",  # XSS attempt
            "PT@12345",  # @ not allowed
            "PT#12345",  # # not allowed
            "PT$12345",  # $ not allowed
            "PT%12345",  # % not allowed
            "PT&12345",  # & not allowed
            "PT*12345",  # * not allowed
            "PT(12345)",  # parentheses not allowed
            "PT[12345]",  # brackets not allowed
            "PT{12345}",  # braces not allowed
        ]
        for patient_id in invalid_ids:
            with pytest.raises(PatientIDValidationError, match="invalid characters"):
                DataSanitizer.sanitize_patient_id(patient_id)

    def test_sanitize_valid_patient_name(self):
        """Test sanitization of valid patient names."""
        valid_names = [
            "John Doe",
            "Mary-Jane Smith",
            "O'Brien",
            "José García",
            "Smith, Jr.",
            "Dr. Jane Doe",
        ]
        for name in valid_names:
            result = DataSanitizer.sanitize_patient_name(name)
            assert result == name.strip()
            assert len(result) <= FileLimits.MAX_PATIENT_NAME_LENGTH

    def test_sanitize_patient_name_removes_control_chars(self):
        """Test that control characters are removed from patient names."""
        dirty_name = "John\x00Doe\n\r"
        clean_name = DataSanitizer.sanitize_patient_name(dirty_name)
        assert clean_name == "JohnDoe"
        assert '\x00' not in clean_name
        assert '\n' not in clean_name

    def test_sanitize_patient_name_rejects_too_long(self):
        """Test that overly long patient names are rejected."""
        long_name = "A" * (FileLimits.MAX_PATIENT_NAME_LENGTH + 1)
        with pytest.raises(ValidationError, match="exceeds maximum length"):
            DataSanitizer.sanitize_patient_name(long_name)

    def test_sanitize_patient_name_rejects_invalid_chars(self):
        """Test that patient names with invalid characters are rejected."""
        invalid_names = [
            "John<script>Doe",  # XSS attempt
            "John;DROP TABLE;",  # SQL injection attempt
            "John@Doe",  # @ not allowed
            "John#Doe",  # # not allowed
            "John$Doe",  # $ not allowed
        ]
        for name in invalid_names:
            with pytest.raises(ValidationError, match="invalid characters"):
                DataSanitizer.sanitize_patient_name(name)

    def test_sanitize_text_field(self):
        """Test general text field sanitization."""
        text = "Normal observation text"
        result = DataSanitizer.sanitize_text_field(text)
        assert result == text

    def test_sanitize_text_field_removes_control_chars(self):
        """Test that control characters are removed from text fields."""
        dirty_text = "Test\x00\x01\x02Text\n\r"
        clean_text = DataSanitizer.sanitize_text_field(dirty_text)
        assert '\x00' not in clean_text
        assert '\x01' not in clean_text
        assert '\x02' not in clean_text

    def test_sanitize_text_field_enforces_length_limit(self):
        """Test that text fields enforce length limits."""
        long_text = "A" * 600
        with pytest.raises(ValidationError, match="exceeds maximum length"):
            DataSanitizer.sanitize_text_field(long_text, max_length=500)


# =============================================================================
# HL7 MESSAGE VALIDATION TESTS
# =============================================================================


class TestHL7MessageValidation:
    """Test HL7 message validation in parser."""

    def test_validate_empty_message(self, db_session):
        """Test that empty messages are rejected."""
        parser = HL7Parser(db_session)
        with pytest.raises(HL7ValidationError, match="cannot be empty"):
            parser.validate_hl7_message("")

    def test_validate_too_small_message(self, db_session):
        """Test that messages below minimum size are rejected."""
        parser = HL7Parser(db_session)
        tiny_message = "MSH|^~\\&|"  # Too small to be valid
        with pytest.raises(HL7ValidationError, match="too small"):
            parser.validate_hl7_message(tiny_message)

    def test_validate_too_large_message(self, db_session):
        """Test that messages exceeding 50MB are rejected (DoS prevention)."""
        parser = HL7Parser(db_session)
        # Create a message larger than 50MB
        large_message = "MSH|^~\\&|" + "A" * (FileLimits.MAX_HL7_MESSAGE_SIZE + 1000)
        with pytest.raises(HL7ValidationError, match="too large"):
            parser.validate_hl7_message(large_message)

    def test_validate_missing_msh_segment(self, db_session):
        """Test that messages not starting with MSH are rejected."""
        parser = HL7Parser(db_session)
        invalid_message = "PID|1||PT12345||Doe^John||19800101|M|||" + "X" * 200
        with pytest.raises(HL7ValidationError, match="must start with 'MSH'"):
            parser.validate_hl7_message(invalid_message)

    def test_validate_missing_pid_segment(self, db_session):
        """Test that messages without PID segment are rejected."""
        parser = HL7Parser(db_session)
        invalid_message = "MSH|^~\\&|SENDING_APP|FACILITY|||||ORU^R01|||2.5\r" + "X" * 200
        with pytest.raises(HL7ValidationError, match="missing required PID"):
            parser.validate_hl7_message(invalid_message)

    def test_validate_valid_message_structure(self, db_session):
        """Test that valid HL7 messages pass validation."""
        parser = HL7Parser(db_session)
        valid_message = (
            "MSH|^~\\&|SENDING_APP|FACILITY|RECEIVING_APP|RECEIVING_FACILITY|"
            "20240101120000||ORU^R01|MSG001|P|2.5\r"
            "PID|1||PT12345||Doe^John||19800101|M|||\r"
            "OBX|1|NM|73990-7^Battery Voltage^LN||2.65|V|2.2-2.8|N|||F\r"
        )
        # Should not raise any exception
        parser.validate_hl7_message(valid_message)


# =============================================================================
# FILE VALIDATION TESTS
# =============================================================================


class TestFileValidation:
    """Test file validation in main_window."""

    def test_validate_nonexistent_file(self, qtbot):
        """Test that nonexistent files are rejected."""
        window = MainWindow()
        qtbot.addWidget(window)

        nonexistent_path = "/tmp/nonexistent_file_12345.hl7"
        with pytest.raises(FileValidationError, match="does not exist"):
            window._validate_import_file(nonexistent_path)

    def test_validate_directory_path(self, qtbot):
        """Test that directories are rejected."""
        window = MainWindow()
        qtbot.addWidget(window)

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileValidationError, match="not a regular file"):
                window._validate_import_file(tmpdir)

    def test_validate_too_large_file(self, qtbot):
        """Test that files exceeding size limits are rejected (DoS prevention)."""
        window = MainWindow()
        qtbot.addWidget(window)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.hl7', delete=False) as f:
            # Write just enough data to exceed limit (in chunks to avoid memory issues)
            chunk_size = 1024 * 1024  # 1 MB chunks
            chunks_needed = (FileLimits.MAX_IMPORT_FILE_SIZE // chunk_size) + 2
            for _ in range(chunks_needed):
                f.write("A" * chunk_size)
            temp_path = f.name

        try:
            with pytest.raises(FileValidationError, match="too large"):
                window._validate_import_file(temp_path)
        finally:
            os.unlink(temp_path)

    def test_validate_too_small_file(self, qtbot):
        """Test that files below minimum size are rejected."""
        window = MainWindow()
        qtbot.addWidget(window)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.hl7', delete=False) as f:
            f.write("MSH")  # Too small
            temp_path = f.name

        try:
            with pytest.raises(FileValidationError, match="too small"):
                window._validate_import_file(temp_path)
        finally:
            os.unlink(temp_path)

    def test_validate_symlink_attack(self, qtbot):
        """Test that symlinks are resolved to prevent attacks."""
        window = MainWindow()
        qtbot.addWidget(window)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.hl7', delete=False) as f:
            f.write("MSH|^~\\&|" + "X" * 200)
            temp_path = f.name

        symlink_path = temp_path + ".link"

        try:
            os.symlink(temp_path, symlink_path)
            # Should resolve the symlink and validate the actual file
            window._validate_import_file(symlink_path)
        finally:
            if os.path.exists(symlink_path):
                os.unlink(symlink_path)
            os.unlink(temp_path)

    def test_validate_valid_file(self, qtbot):
        """Test that valid files pass validation."""
        window = MainWindow()
        qtbot.addWidget(window)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.hl7', delete=False) as f:
            f.write(
                "MSH|^~\\&|SENDING_APP|FACILITY|RECEIVING_APP|RECEIVING_FACILITY|"
                "20240101120000||ORU^R01|MSG001|P|2.5\r"
                "PID|1||PT12345||Doe^John||19800101|M|||\r"
            )
            temp_path = f.name

        try:
            # Should not raise any exception
            window._validate_import_file(temp_path)
        finally:
            os.unlink(temp_path)


# =============================================================================
# SQL INJECTION PREVENTION TESTS
# =============================================================================


class TestSQLInjectionPrevention:
    """Test that SQL injection attacks are prevented."""

    def test_sql_injection_in_patient_id(self, db_session):
        """Test that SQL injection attempts in patient ID are blocked."""
        # Attempt to inject SQL through patient ID
        sql_injection_attempts = [
            "PT123'; DROP TABLE patients; --",
            "PT123' OR '1'='1",
            "PT123'; DELETE FROM patients WHERE '1'='1",
            "PT123' UNION SELECT * FROM patients --",
        ]

        for malicious_id in sql_injection_attempts:
            # Should raise validation error, not execute SQL
            with pytest.raises(PatientIDValidationError):
                DataSanitizer.sanitize_patient_id(malicious_id)

    def test_safe_database_query_with_sanitized_id(self, db_session):
        """Test that sanitized IDs work safely with database queries."""
        # Create a patient with a normal ID
        patient = Patient(
            patient_id="PT12345",
            patient_name="John Doe",
            anonymized=False,
        )
        db_session.add(patient)
        db_session.commit()

        # Query using the sanitized ID (SQLAlchemy parameterization prevents injection)
        safe_id = DataSanitizer.sanitize_patient_id("PT12345")
        result = db_session.query(Patient).filter_by(patient_id=safe_id).first()

        assert result is not None
        assert result.patient_id == "PT12345"
        assert result.patient_name == "John Doe"

    def test_malicious_patient_name_rejected(self):
        """Test that malicious patient names are rejected."""
        malicious_names = [
            "John'; DROP TABLE patients; --",
            "John<script>alert('XSS')</script>",
            "John' OR '1'='1",
        ]

        for name in malicious_names:
            with pytest.raises(ValidationError):
                DataSanitizer.sanitize_patient_name(name)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestSecurityIntegration:
    """Integration tests for end-to-end security validation."""

    def test_parse_message_with_malicious_patient_id(self, db_session):
        """Test that HL7 messages with malicious patient IDs are rejected."""
        parser = HL7Parser(db_session)

        malicious_message = (
            "MSH|^~\\&|SENDING_APP|FACILITY|RECEIVING_APP|RECEIVING_FACILITY|"
            "20240101120000||ORU^R01|MSG001|P|2.5\r"
            "PID|1||PT123'; DROP TABLE patients; --||Doe^John||19800101|M|||\r"
            "OBX|1|NM|73990-7^Battery Voltage^LN||2.65|V|2.2-2.8|N|||F\r"
        )

        # Should raise validation error during parsing
        with pytest.raises(PatientIDValidationError):
            parser.parse_message(malicious_message)

    def test_parse_oversized_message_rejected(self, db_session):
        """Test that oversized HL7 messages are rejected before parsing."""
        parser = HL7Parser(db_session)

        # Create an oversized message
        oversized_message = (
            "MSH|^~\\&|SENDING_APP|FACILITY|RECEIVING_APP|RECEIVING_FACILITY|"
            "20240101120000||ORU^R01|MSG001|P|2.5\r"
            "PID|1||PT12345||Doe^John||19800101|M|||\r"
            + "A" * (FileLimits.MAX_HL7_MESSAGE_SIZE + 1000)
        )

        # Should be rejected during validation, before attempting to parse
        with pytest.raises(HL7ValidationError, match="too large"):
            parser.parse_message(oversized_message)

    def test_valid_message_parses_successfully(self, db_session):
        """Test that valid, sanitized messages parse successfully."""
        parser = HL7Parser(db_session)

        valid_message = (
            "MSH|^~\\&|MEDTRONIC-CARELINK|FACILITY001|RECEIVING_APP|RECEIVING_FACILITY|"
            "20240115103000||ORU^R01|MSG123456|P|2.5\r"
            "PID|1||PT-12345||Doe^John||19800515|M|||\r"
            "OBR|1|||REMOTE||||||||||||||||||||||F\r"
            "OBX|1|NM|73990-7^Battery Voltage^LN||2.65|V|2.2-2.8|N|||F\r"
            "OBX|2|NM|8889-8^Atrial Lead Impedance^LN||625|Ohm|200-1500|N|||F\r"
        )

        # Should parse successfully without raising exceptions
        transmission = parser.parse_message(valid_message)

        assert transmission is not None
        assert transmission.patient_id == "PT-12345"
        assert transmission.patient.patient_name == "John Doe"
        assert len(transmission.observations) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
