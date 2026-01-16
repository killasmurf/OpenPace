# OpenPace Security Quick Reference

**For Developers:** Essential security practices when working with OpenPace

---

## 1. Input Validation - ALWAYS USE DataSanitizer

### Patient IDs
```python
from openpace.hl7.parser import DataSanitizer
from openpace.exceptions import PatientIDValidationError

# ALWAYS sanitize patient IDs before use
try:
    clean_patient_id = DataSanitizer.sanitize_patient_id(user_input)
    # Now safe to use in database queries
except PatientIDValidationError as e:
    logger.error(f"Invalid patient ID: {e}")
    # Handle error appropriately
```

### Patient Names
```python
from openpace.hl7.parser import DataSanitizer
from openpace.exceptions import ValidationError

# ALWAYS sanitize patient names
try:
    clean_name = DataSanitizer.sanitize_patient_name(user_input)
    # Now safe to store
except ValidationError as e:
    logger.error(f"Invalid patient name: {e}")
```

### Text Fields
```python
from openpace.hl7.parser import DataSanitizer

# Sanitize any text field that comes from user input or external sources
clean_text = DataSanitizer.sanitize_text_field(
    user_input,
    max_length=500  # Use appropriate limit from FileLimits
)
```

---

## 2. File Operations - ALWAYS Validate

### Importing Files
```python
from pathlib import Path
from openpace.exceptions import FileValidationError
from openpace.constants import FileLimits

def safe_file_import(file_path: str):
    # Step 1: Resolve symlinks and validate path
    try:
        resolved_path = Path(file_path).resolve(strict=True)
    except Exception as e:
        raise FileValidationError(f"Invalid file path: {e}")

    # Step 2: Verify it's a regular file
    if not resolved_path.is_file():
        raise FileValidationError("Not a regular file")

    # Step 3: Check file size
    file_size = resolved_path.stat().st_size
    if file_size > FileLimits.MAX_IMPORT_FILE_SIZE:
        raise FileValidationError("File too large")

    # Step 4: Read with size limit
    with open(resolved_path, 'r') as f:
        content = f.read(FileLimits.MAX_IMPORT_FILE_SIZE + 1)

    # Step 5: Double-check size
    if len(content.encode('utf-8')) > FileLimits.MAX_IMPORT_FILE_SIZE:
        raise FileValidationError("Content too large")

    return content
```

---

## 3. Database Queries - ALWAYS Use ORM

### ✅ CORRECT - Using SQLAlchemy ORM
```python
from openpace.database.models import Patient

# Parameterized query - SAFE
patient = session.query(Patient).filter_by(patient_id=patient_id).first()

# Complex query with joins - SAFE
from openpace.database.models import Observation, Transmission

observations = session.query(Observation).join(
    Observation.transmission
).filter(
    Observation.transmission.has(patient_id=patient_id),
    Observation.variable_name == variable_name
).all()
```

### ❌ INCORRECT - Using Raw SQL
```python
# NEVER DO THIS - Vulnerable to SQL injection
query = f"SELECT * FROM patients WHERE patient_id = '{patient_id}'"
result = session.execute(query)  # DANGEROUS!
```

---

## 4. HL7 Message Parsing - ALWAYS Validate

### Parsing HL7 Messages
```python
from openpace.hl7.parser import HL7Parser
from openpace.exceptions import HL7ValidationError

parser = HL7Parser(db_session)

try:
    # Validation happens automatically in parse_message()
    transmission = parser.parse_message(hl7_message_text, filename=source_file)
    logger.info(f"Successfully parsed transmission {transmission.transmission_id}")
except HL7ValidationError as e:
    logger.error(f"HL7 validation failed: {e}")
    # Handle invalid HL7 message
```

### Manual Validation (if needed)
```python
from openpace.hl7.parser import HL7Parser

parser = HL7Parser(db_session)

try:
    # Validate before processing
    parser.validate_hl7_message(hl7_message_text)
    # Message is valid, proceed with processing
except HL7ValidationError as e:
    logger.error(f"Invalid HL7 message: {e}")
```

---

## 5. Error Handling - ALWAYS Be Specific

### Import Operation Error Handling
```python
from openpace.exceptions import (
    FileValidationError,
    HL7ValidationError,
    ValidationError,
    PatientIDValidationError
)

try:
    # Your import logic here
    validate_file(file_path)
    content = read_file(file_path)
    transmission = parse_hl7(content)

except FileValidationError as e:
    logger.error(f"File validation failed: {e}")
    show_user_error("Invalid file", str(e))

except HL7ValidationError as e:
    logger.error(f"HL7 validation failed: {e}")
    show_user_error("Invalid HL7 format", str(e))

except ValidationError as e:
    logger.error(f"Data validation failed: {e}")
    show_user_error("Invalid data", str(e))

except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    show_user_error("Import failed", "An unexpected error occurred")
```

---

## 6. Security Limits - USE Constants

### Always Use FileLimits
```python
from openpace.constants import FileLimits

# File size validation
if file_size > FileLimits.MAX_IMPORT_FILE_SIZE:
    raise FileValidationError("File too large")

# String length validation
if len(patient_id) > FileLimits.MAX_PATIENT_ID_LENGTH:
    raise ValidationError("Patient ID too long")

# Message size validation
if message_size > FileLimits.MAX_HL7_MESSAGE_SIZE:
    raise HL7ValidationError("HL7 message too large")
```

### Available Limits
```python
FileLimits.MAX_HL7_MESSAGE_SIZE        # 50 MB
FileLimits.MAX_IMPORT_FILE_SIZE        # 50 MB
FileLimits.MIN_HL7_MESSAGE_SIZE        # 100 bytes
FileLimits.MAX_PATIENT_ID_LENGTH       # 100 chars
FileLimits.MAX_PATIENT_NAME_LENGTH     # 200 chars
FileLimits.MAX_OBSERVATION_TEXT_LENGTH # 500 chars
```

---

## 7. Logging - ALWAYS Log Security Events

### Security Event Logging
```python
import logging
logger = logging.getLogger(__name__)

# Log validation successes (INFO level)
logger.info(f"File validation passed: {file_path} ({file_size} bytes)")

# Log validation failures (ERROR level)
logger.error(f"File validation failed: {error_message}")

# Log security events (WARNING level)
logger.warning(f"Suspicious activity detected: {details}")

# Log exceptions with stack trace (EXCEPTION level)
try:
    risky_operation()
except Exception as e:
    logger.exception(f"Operation failed: {e}")
```

---

## 8. Common Attack Patterns - Know What to Block

### SQL Injection Patterns
```
PT123'; DROP TABLE patients; --
PT123" OR "1"="1
PT123; DELETE FROM patients WHERE 1=1; --
PT123' UNION SELECT * FROM patients--
```
**Defense:** DataSanitizer.sanitize_patient_id() + SQLAlchemy ORM

### Path Traversal Patterns
```
../../etc/passwd
../../../sensitive_data.db
/etc/shadow
..\..\windows\system32\config\sam
```
**Defense:** Path.resolve(strict=True) + file type validation

### Control Characters
```
PT\x00123\x1F456
Patient\x0AName\x0D
Data\x1B[31m (ANSI escape codes)
```
**Defense:** DataSanitizer removes control characters

### Large File DoS
```
File size: 500 MB, 1 GB, etc.
```
**Defense:** File size limits (50 MB max)

---

## 9. Code Review Checklist

When reviewing code, check for:

- [ ] User input is validated with DataSanitizer
- [ ] File operations use path validation
- [ ] Database queries use SQLAlchemy ORM (no raw SQL)
- [ ] File sizes are checked against FileLimits
- [ ] Error handling uses specific exception types
- [ ] Security events are logged
- [ ] No hardcoded security limits (use constants)
- [ ] Symlinks are resolved in file operations
- [ ] Control characters are removed from text
- [ ] Length limits are enforced

---

## 10. Testing Your Code

### Test Security Controls
```python
def test_my_feature():
    # Test with valid input
    result = my_function("PT12345")
    assert result is not None

    # Test with SQL injection attempt
    with pytest.raises(ValidationError):
        my_function("PT123'; DROP TABLE patients; --")

    # Test with oversized input
    with pytest.raises(ValidationError):
        my_function("A" * 1000)

    # Test with control characters
    with pytest.raises(ValidationError):
        my_function("PT\x00123")

    # Test with empty input
    with pytest.raises(ValidationError):
        my_function("")
```

---

## 11. Quick Security Checklist

Before committing code, ask yourself:

1. **Input Validation**
   - [ ] All user inputs validated?
   - [ ] DataSanitizer used where appropriate?
   - [ ] Length limits enforced?

2. **File Operations**
   - [ ] File paths validated?
   - [ ] Symlinks resolved?
   - [ ] File sizes checked?

3. **Database Queries**
   - [ ] Using SQLAlchemy ORM?
   - [ ] No raw SQL queries?
   - [ ] Inputs sanitized before queries?

4. **Error Handling**
   - [ ] Specific exception types used?
   - [ ] Errors logged appropriately?
   - [ ] User-friendly error messages?

5. **Security Constants**
   - [ ] Using FileLimits constants?
   - [ ] No hardcoded limits?

---

## 12. Resources

### Documentation
- Full Security Audit: `security_audit_report.md`
- Implementation Summary: `SECURITY_FIXES_SUMMARY.md`
- Validation Script: `security_validation.py`

### Key Files
- Constants: `openpace/constants.py`
- Exceptions: `openpace/exceptions.py`
- Data Sanitizer: `openpace/hl7/parser.py` (lines 34-170)
- File Validation: `openpace/gui/main_window.py` (lines 204-252)

### Running Tests
```bash
# Run security validation suite
python3 security_validation.py

# Run all unit tests
pytest tests/

# Run specific security tests
pytest tests/test_hl7_parser.py -k security
```

---

## 13. Getting Help

### Security Questions
1. Check this quick reference
2. Read the full security audit report
3. Review the implementation summary
4. Check the code examples in the repository

### Reporting Security Issues
- Check if it's already fixed (review security docs)
- Create a detailed bug report with:
  - Description of the vulnerability
  - Steps to reproduce
  - Potential impact
  - Suggested fix (if applicable)

---

**Remember: Security is everyone's responsibility!**

When in doubt:
- Validate all inputs
- Use existing security functions
- Log security events
- Ask for code review

**Last Updated:** 2026-01-12
