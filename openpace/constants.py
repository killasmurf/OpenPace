"""
Clinical and Technical Constants for OpenPace

This module centralizes all magic numbers and thresholds used throughout the application.
Values are based on standard pacemaker specifications and clinical guidelines.

Sources:
- FDA Guidance for Cardiac Pacemakers (2022)
- Heart Rhythm Society Guidelines
- Manufacturer specifications (Medtronic, Boston Scientific, Abbott)
"""

from typing import Dict, List


# =============================================================================
# BATTERY THRESHOLDS
# =============================================================================

class BatteryThresholds:
    """
    Battery voltage thresholds for different states.

    Based on lithium-iodide battery chemistry used in most modern pacemakers.
    """

    # Normal operation range (Volts)
    NOMINAL_VOLTAGE = 2.8  # New battery voltage (typical range: 2.7-2.9V)
    MINIMUM_NORMAL = 2.5   # Minimum voltage for normal operation

    # Warning thresholds (Volts)
    ERI_THRESHOLD = 2.2    # Elective Replacement Indicator
    EOL_THRESHOLD = 2.0    # End of Life (critical - device may stop)

    # Color coding thresholds for UI
    GREEN_THRESHOLD = 2.5   # Normal/healthy range (green)
    YELLOW_THRESHOLD = 2.3  # Warning range (yellow/amber)
    # Below 2.3V = red (critical)

    # Source: Medtronic Technical Manual 2023, Boston Scientific CRM Reference
    VOLTAGE_DESCRIPTIONS: Dict[str, str] = {
        'NOMINAL': 'Normal battery operation - no action required',
        'DEPLETING': 'Battery depleting normally - monitor at regular intervals',
        'WARNING': 'Battery approaching ERI - plan replacement within 6-12 months',
        'ERI': 'Elective Replacement Indicator - schedule replacement within 3 months',
        'EOL': 'End of Life - urgent replacement required (device may enter safety mode)'
    }


# =============================================================================
# LEAD IMPEDANCE THRESHOLDS
# =============================================================================

class ImpedanceThresholds:
    """
    Lead impedance thresholds for fracture/failure detection.

    Normal lead impedance varies by manufacturer and lead model.
    """

    # Normal impedance range (Ohms)
    NORMAL_MIN = 200      # Minimum normal impedance
    NORMAL_MAX = 1500     # Maximum normal impedance

    # Abnormal conditions (Ohms)
    FRACTURE_THRESHOLD = 2000     # Above this suggests lead fracture (open circuit)
    INSULATION_FAILURE = 150      # Below this suggests insulation failure (short circuit)

    # Impedance change detection
    SUDDEN_CHANGE_PERCENT = 30    # 30% change from baseline suggests problem
    GRADUAL_CHANGE_PERCENT = 50   # 50% change over time requires investigation

    # Source: HRS Expert Consensus on Lead Performance (2022)


# =============================================================================
# EGM (ELECTROGRAM) PROCESSING CONSTANTS
# =============================================================================

class EGMConstants:
    """Constants for electrogram signal processing."""

    # Common sample rates (Hz)
    COMMON_SAMPLE_RATES: List[int] = [256, 512, 1000, 2000]
    DEFAULT_SAMPLE_RATE = 512  # Most common for pacemaker EGMs

    # Bandpass filter parameters (Hz)
    BANDPASS_LOW_CUTOFF = 0.5     # Removes DC drift and baseline wander
    BANDPASS_HIGH_CUTOFF = 100    # Removes high-frequency noise and artifacts

    # Peak detection parameters
    MIN_RR_INTERVAL_MS = 200      # Minimum time between R-peaks (300 bpm max)
    MAX_RR_INTERVAL_MS = 2000     # Maximum reasonable RR interval (30 bpm min)
    DEFAULT_MIN_PEAK_DISTANCE_MS = 200  # Default for peak detection

    # Signal characteristics
    TYPICAL_EGM_RANGE_UV = 5000   # Typical EGM amplitude range (±5mV = ±5000μV)

    # Binary format header sizes (bytes)
    TYPICAL_HEADER_SIZE = 64
    MEDTRONIC_HEADER_SIZE = 128
    BSC_HEADER_SIZE = 256
    ABBOTT_HEADER_SIZE = 64

    # EGM strip typical durations (seconds)
    MIN_STRIP_DURATION = 5
    MAX_STRIP_DURATION = 30
    DEFAULT_STRIP_DURATION = 10

    # Butterworth filter order
    FILTER_ORDER = 4


# =============================================================================
# STATISTICAL ANALYSIS THRESHOLDS
# =============================================================================

class StatisticalThresholds:
    """Thresholds for statistical analysis and confidence levels."""

    # Regression confidence thresholds
    HIGH_R_SQUARED = 0.9          # R² > 0.9 indicates excellent fit
    MEDIUM_R_SQUARED = 0.7        # R² > 0.7 indicates good fit

    # P-value thresholds
    SIGNIFICANT_P_VALUE = 0.05    # p < 0.05 = statistically significant
    MARGINAL_P_VALUE = 0.1        # p < 0.1 = marginally significant

    # Minimum data points for analysis
    MIN_POINTS_TREND_ANALYSIS = 3    # Minimum for linear regression
    MIN_POINTS_HIGH_CONFIDENCE = 5   # Minimum for high-confidence prediction
    MIN_POINTS_ROBUST_ANALYSIS = 10  # Recommended for robust analysis

    # Time-based thresholds
    DAYS_PER_YEAR = 365.25        # Account for leap years
    SECONDS_PER_DAY = 86400
    MS_PER_SECOND = 1000
    MS_PER_MINUTE = 60000


# =============================================================================
# FILE SIZE AND VALIDATION LIMITS
# =============================================================================

class FileLimits:
    """Limits for file imports and data validation."""

    # File size limits (bytes)
    MAX_HL7_MESSAGE_SIZE = 50 * 1024 * 1024   # 50 MB
    MAX_IMPORT_FILE_SIZE = 50 * 1024 * 1024   # 50 MB
    MIN_HL7_MESSAGE_SIZE = 100                # Minimum viable HL7 message

    # Binary blob limits
    MIN_BINARY_BLOB_SIZE = 100                # Minimum for valid binary data

    # String length limits
    MAX_PATIENT_ID_LENGTH = 100
    MAX_PATIENT_NAME_LENGTH = 200
    MAX_OBSERVATION_TEXT_LENGTH = 500


# =============================================================================
# TIME WINDOWS AND INTERVALS
# =============================================================================

class TimeWindows:
    """Time windows for analysis and caching."""

    # Cache time-to-live (seconds)
    TREND_CACHE_TTL_SECONDS = 3600        # 1 hour
    ANALYSIS_CACHE_TTL_SECONDS = 1800     # 30 minutes

    # Prediction timeframes
    ERI_WARNING_MONTHS = 6                # Warn when ERI predicted within 6 months
    ERI_URGENT_MONTHS = 3                 # Urgent when ERI predicted within 3 months


# =============================================================================
# HEART RATE LIMITS
# =============================================================================

class HeartRateLimits:
    """Normal and abnormal heart rate thresholds."""

    # Physiological limits (beats per minute)
    MIN_PHYSIOLOGICAL_HR = 30      # Below this is severe bradycardia
    MAX_PHYSIOLOGICAL_HR = 300     # Above this is likely artifact

    # Normal range (bpm)
    NORMAL_RESTING_MIN = 60
    NORMAL_RESTING_MAX = 100

    # Clinical thresholds (bpm)
    BRADYCARDIA_THRESHOLD = 60     # Below this is bradycardia
    TACHYCARDIA_THRESHOLD = 100    # Above this is tachycardia


# =============================================================================
# UI CONFIGURATION DEFAULTS
# =============================================================================

class UIDefaults:
    """Default values for UI components."""

    # Window dimensions (pixels)
    DEFAULT_WINDOW_WIDTH = 1400
    DEFAULT_WINDOW_HEIGHT = 900
    MIN_WINDOW_WIDTH = 800
    MIN_WINDOW_HEIGHT = 600

    # Chart/plot defaults
    DEFAULT_PLOT_DPI = 100
    MAX_PLOT_POINTS = 10000        # Downsample if more points for performance


# =============================================================================
# VENDOR-SPECIFIC CONSTANTS
# =============================================================================

class VendorConstants:
    """Vendor-specific constants and identifiers."""

    SUPPORTED_VENDORS: List[str] = [
        'Medtronic',
        'Boston Scientific',
        'Abbott',
        'Biotronik',
        'Generic'
    ]

    # Default vendor when not detected
    DEFAULT_VENDOR = 'Generic'
