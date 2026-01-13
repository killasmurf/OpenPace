"""
Custom Exceptions for OpenPace

This module defines custom exception classes for consistent error handling
throughout the application. Using specific exceptions makes error handling
more precise and debugging easier.
"""


class OpenPaceError(Exception):
    """
    Base exception for all OpenPace errors.

    All custom exceptions in OpenPace should inherit from this base class.
    This allows catching all OpenPace-specific errors with a single except clause.
    """
    pass


# =============================================================================
# DATA PARSING ERRORS
# =============================================================================

class ParseError(OpenPaceError):
    """Base exception for parsing errors."""
    pass


class HL7ParseError(ParseError):
    """
    Raised when HL7 message parsing fails.

    Examples:
    - Malformed HL7 message structure
    - Missing required segments (MSH, PID)
    - Invalid field formats
    """
    pass


class HL7ValidationError(ParseError):
    """
    Raised when HL7 message validation fails.

    Examples:
    - Message exceeds size limits
    - Invalid message type
    - Required fields missing
    """
    pass


class EGMDecodeError(ParseError):
    """
    Raised when EGM (electrogram) blob decoding fails.

    Examples:
    - Unrecognized binary format
    - Corrupted waveform data
    - Invalid sample count
    """
    pass


# =============================================================================
# DATABASE ERRORS
# =============================================================================

class DatabaseError(OpenPaceError):
    """
    Base exception for database operations.

    Examples:
    - Connection failures
    - Transaction errors
    - Constraint violations
    """
    pass


class DatabaseConnectionError(DatabaseError):
    """
    Raised when database connection fails.

    Examples:
    - Cannot open database file
    - Database file is locked
    - Insufficient permissions
    """
    pass


class DatabaseIntegrityError(DatabaseError):
    """
    Raised when database integrity constraints are violated.

    Examples:
    - Duplicate primary key
    - Foreign key violation
    - Unique constraint violation
    """
    pass


class TransactionError(DatabaseError):
    """
    Raised when database transaction fails.

    Examples:
    - Rollback failure
    - Commit failure
    - Deadlock detected
    """
    pass


# =============================================================================
# VALIDATION ERRORS
# =============================================================================

class ValidationError(OpenPaceError):
    """
    Raised when input validation fails.

    Examples:
    - Invalid patient ID format
    - Patient name contains invalid characters
    - File path traversal attempt
    - Data exceeds allowed limits
    """
    pass


class PatientIDValidationError(ValidationError):
    """
    Raised when patient ID validation fails.

    Examples:
    - Empty patient ID
    - Invalid characters in patient ID
    - Patient ID exceeds maximum length
    """
    pass


class FileValidationError(ValidationError):
    """
    Raised when file validation fails.

    Examples:
    - File too large
    - File path not allowed
    - File not found
    - Invalid file type
    """
    pass


# =============================================================================
# ANALYSIS ERRORS
# =============================================================================

class AnalysisError(OpenPaceError):
    """
    Base exception for analysis operations.

    Examples:
    - Insufficient data for analysis
    - Statistical computation failed
    - Invalid analysis parameters
    """
    pass


class InsufficientDataError(AnalysisError):
    """
    Raised when there is insufficient data for analysis.

    Examples:
    - Less than 3 data points for regression
    - No observations for requested variable
    - Empty trend data
    """

    def __init__(self, message: str, required_points: int = None, actual_points: int = None):
        """
        Initialize with data point information.

        Args:
            message: Error description
            required_points: Minimum required data points
            actual_points: Actual data points available
        """
        super().__init__(message)
        self.required_points = required_points
        self.actual_points = actual_points


class StatisticalError(AnalysisError):
    """
    Raised when statistical computation fails.

    Examples:
    - Regression failed to converge
    - Singular matrix in calculation
    - Division by zero in statistics
    """
    pass


# =============================================================================
# CONFIGURATION ERRORS
# =============================================================================

class ConfigurationError(OpenPaceError):
    """
    Raised when configuration is invalid.

    Examples:
    - Missing required configuration parameter
    - Invalid configuration value
    - Configuration file not found or corrupted
    """
    pass


# =============================================================================
# IMPORT/EXPORT ERRORS
# =============================================================================

class ImportError(OpenPaceError):
    """
    Raised when data import fails.

    Note: Renamed from builtin ImportError context.
    """
    pass


class ExportError(OpenPaceError):
    """
    Raised when data export fails.

    Examples:
    - Cannot write to output file
    - Invalid export format requested
    - Data serialization failed
    """
    pass


# =============================================================================
# SECURITY ERRORS
# =============================================================================

class SecurityError(OpenPaceError):
    """
    Base exception for security-related errors.

    Examples:
    - Encryption/decryption failures
    - Permission denied
    - Authentication failures
    """
    pass


class EncryptionError(SecurityError):
    """
    Raised when encryption operations fail.

    Examples:
    - Invalid encryption key
    - Encryption algorithm failed
    - Corrupted encrypted data
    """
    pass


class PermissionError(SecurityError):
    """
    Raised when permission check fails.

    Examples:
    - User lacks permission to access resource
    - File permissions insufficient
    """
    pass


# =============================================================================
# VENDOR-SPECIFIC ERRORS
# =============================================================================

class VendorError(OpenPaceError):
    """
    Base exception for vendor-specific operations.

    Examples:
    - Unknown vendor format
    - Vendor-specific decoding failed
    """
    pass


class UnknownVendorError(VendorError):
    """
    Raised when device vendor cannot be determined.

    Examples:
    - Vendor string not recognized
    - No vendor information in transmission
    """
    pass


class VendorFormatError(VendorError):
    """
    Raised when vendor-specific format is invalid.

    Examples:
    - Medtronic binary format unrecognized
    - Boston Scientific proprietary format corrupted
    """
    pass


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_validation_error(field_name: str, value: any, reason: str) -> str:
    """
    Format a consistent validation error message.

    Args:
        field_name: Name of the field that failed validation
        value: The invalid value (will be truncated if long)
        reason: Reason for validation failure

    Returns:
        Formatted error message

    Example:
        >>> format_validation_error("patient_id", "ABC@123", "contains invalid characters")
        "Validation failed for 'patient_id': contains invalid characters (value: 'ABC@123')"
    """
    # Truncate long values
    value_str = str(value)
    if len(value_str) > 100:
        value_str = value_str[:97] + "..."

    return f"Validation failed for '{field_name}': {reason} (value: '{value_str}')"
