#!/usr/bin/env python3
"""
Validation script for security fixes in OpenPace.

This script validates that all security features are properly implemented:
- DataSanitizer class
- HL7 message validation
- File validation
- Input sanitization

Run this script to verify security fixes without requiring pytest.
"""

import sys
import os
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openpace.hl7.parser import DataSanitizer, HL7Parser
from openpace.exceptions import (
    HL7ValidationError,
    PatientIDValidationError,
    ValidationError,
    FileValidationError,
)
from openpace.constants import FileLimits


def test_data_sanitizer():
    """Test DataSanitizer class."""
    print("\n=== Testing DataSanitizer ===")

    # Test 1: Valid patient ID
    try:
        result = DataSanitizer.sanitize_patient_id("PT12345")
        print(f"✓ Valid patient ID accepted: {result}")
    except Exception as e:
        print(f"✗ Valid patient ID rejected: {e}")
        return False

    # Test 2: SQL injection attempt in patient ID
    try:
        DataSanitizer.sanitize_patient_id("PT123'; DROP TABLE patients;--")
        print("✗ SQL injection attempt was NOT blocked!")
        return False
    except PatientIDValidationError:
        print("✓ SQL injection attempt blocked in patient ID")

    # Test 3: Control characters removed
    try:
        result = DataSanitizer.sanitize_patient_id("PT\x0012345")
        assert '\x00' not in result
        print(f"✓ Control characters removed: 'PT\\x0012345' -> '{result}'")
    except Exception as e:
        print(f"✗ Control character removal failed: {e}")
        return False

    # Test 4: Patient name with valid characters
    try:
        result = DataSanitizer.sanitize_patient_name("John Doe")
        assert result == "John Doe"
        print(f"✓ Valid patient name accepted: {result}")
    except Exception as e:
        print(f"✗ Valid patient name rejected: {e}")
        return False

    # Test 5: XSS attempt in patient name
    try:
        DataSanitizer.sanitize_patient_name("John<script>alert('xss')</script>")
        print("✗ XSS attempt was NOT blocked in patient name!")
        return False
    except ValidationError:
        print("✓ XSS attempt blocked in patient name")

    # Test 6: Text field sanitization
    try:
        result = DataSanitizer.sanitize_text_field("Normal text")
        assert result == "Normal text"
        print(f"✓ Normal text accepted: {result}")
    except Exception as e:
        print(f"✗ Normal text rejected: {e}")
        return False

    # Test 7: Text field length limit
    try:
        long_text = "A" * 600
        DataSanitizer.sanitize_text_field(long_text, max_length=500)
        print("✗ Long text was NOT rejected!")
        return False
    except ValidationError:
        print("✓ Long text rejected (length limit enforced)")

    return True


def test_hl7_validation():
    """Test HL7 message validation."""
    print("\n=== Testing HL7 Message Validation ===")

    # Create a mock database session (we won't actually use it)
    class MockSession:
        pass

    parser = HL7Parser(MockSession(), anonymize=False)

    # Test 1: Empty message rejected
    try:
        parser.validate_hl7_message("")
        print("✗ Empty message was NOT rejected!")
        return False
    except HL7ValidationError:
        print("✓ Empty message rejected")

    # Test 2: Message without MSH segment rejected
    try:
        parser.validate_hl7_message("PID|1||PT12345||" + "X" * 200)
        print("✗ Message without MSH was NOT rejected!")
        return False
    except HL7ValidationError:
        print("✓ Message without MSH segment rejected")

    # Test 3: Message without PID segment rejected
    try:
        parser.validate_hl7_message("MSH|^~\\&|APP|FAC|||||ORU^R01|||2.5\r" + "X" * 200)
        print("✗ Message without PID was NOT rejected!")
        return False
    except HL7ValidationError:
        print("✓ Message without PID segment rejected")

    # Test 4: Valid message structure accepted
    try:
        valid_message = (
            "MSH|^~\\&|APP|FAC|RCV|RCV_FAC|20240101120000||ORU^R01|MSG001|P|2.5\r"
            "PID|1||PT12345||Doe^John||19800101|M|||\r"
            "OBX|1|NM|73990-7^Battery Voltage^LN||2.65|V|2.2-2.8|N|||F\r"
        )
        parser.validate_hl7_message(valid_message)
        print("✓ Valid message structure accepted")
    except Exception as e:
        print(f"✗ Valid message rejected: {e}")
        return False

    # Test 5: Oversized message rejected (DoS prevention)
    try:
        oversized = "MSH|^~\\&|" + "A" * (FileLimits.MAX_HL7_MESSAGE_SIZE + 1000)
        parser.validate_hl7_message(oversized)
        print("✗ Oversized message was NOT rejected!")
        return False
    except HL7ValidationError:
        print("✓ Oversized message rejected (DoS prevention)")

    return True


def test_file_limits():
    """Test file size limits are properly defined."""
    print("\n=== Testing File Limits Constants ===")

    try:
        assert FileLimits.MAX_HL7_MESSAGE_SIZE == 50 * 1024 * 1024
        print(f"✓ MAX_HL7_MESSAGE_SIZE = {FileLimits.MAX_HL7_MESSAGE_SIZE} bytes (50 MB)")

        assert FileLimits.MAX_IMPORT_FILE_SIZE == 50 * 1024 * 1024
        print(f"✓ MAX_IMPORT_FILE_SIZE = {FileLimits.MAX_IMPORT_FILE_SIZE} bytes (50 MB)")

        assert FileLimits.MIN_HL7_MESSAGE_SIZE == 100
        print(f"✓ MIN_HL7_MESSAGE_SIZE = {FileLimits.MIN_HL7_MESSAGE_SIZE} bytes")

        assert FileLimits.MAX_PATIENT_ID_LENGTH == 100
        print(f"✓ MAX_PATIENT_ID_LENGTH = {FileLimits.MAX_PATIENT_ID_LENGTH}")

        assert FileLimits.MAX_PATIENT_NAME_LENGTH == 200
        print(f"✓ MAX_PATIENT_NAME_LENGTH = {FileLimits.MAX_PATIENT_NAME_LENGTH}")

        assert FileLimits.MAX_OBSERVATION_TEXT_LENGTH == 500
        print(f"✓ MAX_OBSERVATION_TEXT_LENGTH = {FileLimits.MAX_OBSERVATION_TEXT_LENGTH}")

        return True
    except AssertionError as e:
        print(f"✗ File limits not properly configured: {e}")
        return False


def test_exception_classes():
    """Test that exception classes are properly defined."""
    print("\n=== Testing Exception Classes ===")

    try:
        # Test that exceptions can be raised and caught
        try:
            raise HL7ValidationError("Test HL7 validation error")
        except HL7ValidationError:
            print("✓ HL7ValidationError can be raised and caught")

        try:
            raise PatientIDValidationError("Test patient ID error")
        except PatientIDValidationError:
            print("✓ PatientIDValidationError can be raised and caught")

        try:
            raise FileValidationError("Test file validation error")
        except FileValidationError:
            print("✓ FileValidationError can be raised and caught")

        try:
            raise ValidationError("Test general validation error")
        except ValidationError:
            print("✓ ValidationError can be raised and caught")

        return True
    except Exception as e:
        print(f"✗ Exception handling failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print("=" * 70)
    print("OpenPace Security Fixes Validation")
    print("=" * 70)

    results = []

    results.append(("Exception Classes", test_exception_classes()))
    results.append(("File Limits", test_file_limits()))
    results.append(("DataSanitizer", test_data_sanitizer()))
    results.append(("HL7 Validation", test_hl7_validation()))

    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    all_passed = True
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 70)

    if all_passed:
        print("\n✓ All security validations PASSED!")
        print("\nSecurity features successfully implemented:")
        print("  • DataSanitizer class with input validation")
        print("  • HL7 message size and format validation")
        print("  • SQL injection prevention")
        print("  • XSS attack prevention")
        print("  • DoS prevention through size limits")
        print("  • Control character filtering")
        return 0
    else:
        print("\n✗ Some security validations FAILED!")
        print("Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
