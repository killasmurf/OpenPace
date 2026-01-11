"""
Data Normalization Layer

Converts vendor-specific data into standardized formats with consistent units,
validates ranges, and applies quality checks.
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class UnitConverter:
    """
    Converts between different units for pacemaker observations.

    Ensures all data is stored in standard units regardless of vendor format.
    """

    # Standard units for each observation type
    STANDARD_UNITS = {
        'battery_voltage': 'V',
        'battery_percent': '%',
        'lead_impedance_atrial': 'Ohm',
        'lead_impedance_ventricular': 'Ohm',
        'lead_impedance_lv': 'Ohm',
        'afib_burden_percent': '%',
        'heart_rate': 'bpm',
        'heart_rate_mean': 'bpm',
        'heart_rate_max': 'bpm',
        'heart_rate_min': 'bpm',
        'pacing_percent_atrial': '%',
        'pacing_percent_ventricular': '%',
        'pacing_percent_biventricular': '%',
        'lower_rate_limit': 'bpm',
        'upper_rate_limit': 'bpm',
        'av_delay': 'ms',
        'atrial_sensitivity': 'mV',
        'ventricular_sensitivity': 'mV',
    }

    # Conversion factors: source_unit -> (multiplier, target_unit)
    CONVERSION_FACTORS = {
        # Voltage
        ('mV', 'V'): 0.001,
        ('V', 'mV'): 1000,

        # Impedance
        ('kOhm', 'Ohm'): 1000,
        ('Ohm', 'kOhm'): 0.001,

        # Time
        ('s', 'ms'): 1000,
        ('ms', 's'): 0.001,
        ('min', 's'): 60,
        ('s', 'min'): 1/60,

        # Percentage (sometimes expressed as decimal)
        ('decimal', '%'): 100,
        ('%', 'decimal'): 0.01,
    }

    @classmethod
    def convert(cls, value: float, from_unit: str, to_unit: str) -> float:
        """
        Convert a value from one unit to another.

        Args:
            value: Numeric value to convert
            from_unit: Source unit
            to_unit: Target unit

        Returns:
            Converted value

        Raises:
            ValueError: If conversion is not supported
        """
        if from_unit == to_unit:
            return value

        # Try direct conversion
        key = (from_unit, to_unit)
        if key in cls.CONVERSION_FACTORS:
            return value * cls.CONVERSION_FACTORS[key]

        # Try reverse conversion
        reverse_key = (to_unit, from_unit)
        if reverse_key in cls.CONVERSION_FACTORS:
            return value / cls.CONVERSION_FACTORS[reverse_key]

        raise ValueError(f"No conversion available from {from_unit} to {to_unit}")

    @classmethod
    def normalize(cls, variable_name: str, value: float, unit: str) -> Tuple[float, str]:
        """
        Normalize a value to standard units for the given variable.

        Args:
            variable_name: Universal variable name
            value: Numeric value
            unit: Current unit

        Returns:
            Tuple of (normalized_value, standard_unit)
        """
        standard_unit = cls.STANDARD_UNITS.get(variable_name)

        if not standard_unit:
            # No standard unit defined, return as-is
            return value, unit

        if unit == standard_unit:
            return value, unit

        try:
            normalized_value = cls.convert(value, unit, standard_unit)
            return normalized_value, standard_unit
        except ValueError:
            logger.warning(f"Could not convert {variable_name} from {unit} to {standard_unit}")
            return value, unit


class DataQualityValidator:
    """
    Validates observation data for quality and plausibility.

    Detects out-of-range values, physiological impossibilities, and data anomalies.
    """

    # Normal ranges for observations (min, max)
    NORMAL_RANGES = {
        'battery_voltage': (2.0, 3.5),  # Volts
        'battery_percent': (0, 100),
        'lead_impedance_atrial': (200, 1500),  # Ohms
        'lead_impedance_ventricular': (200, 1500),
        'lead_impedance_lv': (200, 1500),
        'afib_burden_percent': (0, 100),
        'heart_rate': (30, 200),  # bpm
        'heart_rate_mean': (40, 150),
        'heart_rate_max': (50, 250),
        'heart_rate_min': (30, 100),
        'pacing_percent_atrial': (0, 100),
        'pacing_percent_ventricular': (0, 100),
        'pacing_percent_biventricular': (0, 100),
        'lower_rate_limit': (30, 100),
        'upper_rate_limit': (100, 180),
        'av_delay': (0, 400),  # ms
    }

    # Critical ranges (outside these = device malfunction or data error)
    CRITICAL_RANGES = {
        'battery_voltage': (1.5, 4.0),
        'lead_impedance_atrial': (50, 3000),
        'lead_impedance_ventricular': (50, 3000),
        'heart_rate': (20, 300),
    }

    @classmethod
    def validate(cls, variable_name: str, value: float) -> Dict[str, Any]:
        """
        Validate a single observation value.

        Args:
            variable_name: Universal variable name
            value: Numeric value (in standard units)

        Returns:
            Dictionary with validation results:
                - is_valid: bool
                - in_normal_range: bool
                - in_critical_range: bool
                - flags: list of quality flags
                - severity: 'normal', 'warning', 'critical'
        """
        flags = []
        severity = 'normal'

        # Check critical range
        critical_range = cls.CRITICAL_RANGES.get(variable_name)
        in_critical_range = True
        if critical_range:
            min_val, max_val = critical_range
            if value < min_val or value > max_val:
                flags.append('OUTSIDE_CRITICAL_RANGE')
                severity = 'critical'
                in_critical_range = False

        # Check normal range
        normal_range = cls.NORMAL_RANGES.get(variable_name)
        in_normal_range = True
        if normal_range:
            min_val, max_val = normal_range
            if value < min_val:
                flags.append('BELOW_NORMAL_RANGE')
                if severity == 'normal':
                    severity = 'warning'
                in_normal_range = False
            elif value > max_val:
                flags.append('ABOVE_NORMAL_RANGE')
                if severity == 'normal':
                    severity = 'warning'
                in_normal_range = False

        # Variable-specific validation
        if variable_name == 'battery_voltage' and value < 2.2:
            flags.append('LOW_BATTERY_ERI')
            severity = 'critical'

        if variable_name.startswith('lead_impedance'):
            if value > 1500:
                flags.append('POSSIBLE_LEAD_FRACTURE')
                severity = 'critical'
            elif value < 200:
                flags.append('POSSIBLE_INSULATION_FAILURE')
                severity = 'critical'

        if variable_name == 'afib_burden_percent' and value > 20:
            flags.append('HIGH_AFIB_BURDEN')
            severity = 'warning'

        is_valid = len(flags) == 0 or severity != 'critical'

        return {
            'is_valid': is_valid,
            'in_normal_range': in_normal_range,
            'in_critical_range': in_critical_range,
            'flags': flags,
            'severity': severity,
        }


class DataNormalizer:
    """
    Main data normalization coordinator.

    Applies unit conversion, validation, and enrichment to observations.
    """

    def __init__(self):
        self.unit_converter = UnitConverter()
        self.validator = DataQualityValidator()

    def normalize_observation(self, observation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a single observation.

        Args:
            observation_data: Dictionary with:
                - variable_name: str
                - value_numeric: float
                - unit: str

        Returns:
            Enriched observation data with:
                - normalized_value: float
                - standard_unit: str
                - validation_result: dict
                - quality_flags: list
        """
        variable_name = observation_data.get('variable_name')
        value = observation_data.get('value_numeric')
        unit = observation_data.get('unit')

        if not variable_name or value is None:
            return observation_data

        # Normalize units
        normalized_value, standard_unit = self.unit_converter.normalize(
            variable_name, value, unit or ''
        )

        # Validate
        validation_result = self.validator.validate(variable_name, normalized_value)

        # Enrich observation data
        return {
            **observation_data,
            'normalized_value': normalized_value,
            'standard_unit': standard_unit,
            'validation_result': validation_result,
            'quality_flags': validation_result['flags'],
            'severity': validation_result['severity'],
        }

    def normalize_batch(self, observations: list) -> list:
        """
        Normalize a batch of observations.

        Args:
            observations: List of observation dictionaries

        Returns:
            List of normalized observation dictionaries
        """
        return [self.normalize_observation(obs) for obs in observations]
