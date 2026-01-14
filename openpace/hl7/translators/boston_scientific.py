"""
Boston Scientific LATITUDE Translator

Maps Boston Scientific MDC_IDC codes to universal variable names.
Supports ICD and pacemaker data from LATITUDE remote monitoring system.
"""

from typing import Optional, Dict
from openpace.hl7.translators.base_translator import VendorTranslator


class BostonScientificTranslator(VendorTranslator):
    """
    Translator for Boston Scientific LATITUDE HL7 messages.

    Maps MDC_IDC (Medical Device Communication - Implantable Cardiac Device)
    codes to universal variable names used throughout OpenPace.
    """

    # Fixed device settings (DEV_) - cannot be changed by operator
    DEVICE_INFO_CODES = {
        "720897": "device_type",
        "720898": "device_model",
        "720899": "device_serial",
        "720900": "device_manufacturer",
        "720901": "device_implant_date",
    }

    # Lead information
    LEAD_INFO_CODES = {
        "720961": "lead_model",
        "720962": "lead_serial",
        "720963": "lead_manufacturer",
        "720964": "lead_implant_date",
        "720965": "lead_polarity_type",
        "720966": "lead_location",
    }

    # Session information
    SESSION_CODES = {
        "721025": "session_datetime",
        "721026": "session_type",
        "721033": "session_clinic_name",
    }

    # Operator-defined brady settings (SET_BRADY_)
    BRADY_SETTING_CODES = {
        "730752": "set_brady_mode",
        "730880": "set_brady_lowrate",
        "731136": "set_brady_max_tracking_rate",
        "731200": "set_brady_max_sensor_rate",
        "731265": "set_brady_sav_delay_high",
        "731266": "set_brady_sav_delay_low",
        "731329": "set_brady_pav_delay_high",
        "731330": "set_brady_pav_delay_low",
        "731072": "set_brady_sensor_type",
        "731392": "set_brady_at_mode_switch_mode",
        "731456": "set_brady_at_mode_switch_rate",
    }

    # Operator-defined tachycardia settings (SET_TACHYTHERAPY_)
    TACHY_SETTING_CODES = {
        "731520": "set_tachy_vstat",
    }

    # Operator-defined zone settings (SET_ZONE_)
    # Note: These codes are per-zone, with sub-ID in OBX-4
    ZONE_SETTING_CODES = {
        "731648": "set_zone_type",
        "731712": "set_zone_vendor_type",
        "731776": "set_zone_status",
        "731840": "set_zone_detection_interval",
        "732097": "set_zone_atp_type_1",
        "732098": "set_zone_atp_type_2",
        "732161": "set_zone_num_atp_seqs_1",
        "732162": "set_zone_num_atp_seqs_2",
        "732225": "set_zone_shock_energy_1",
        "732226": "set_zone_shock_energy_2",
        "732227": "set_zone_shock_energy_3",
        "732289": "set_zone_num_shocks_1",
        "732290": "set_zone_num_shocks_2",
        "732291": "set_zone_num_shocks_3",
    }

    # Operator-defined lead channel sensing settings (SET_LEADCHNL_*_SENSING_)
    LEADCHNL_SENSING_CODES = {
        "729536": "set_leadchnl_ra_sensing_sensitivity",
        "729537": "set_leadchnl_rv_sensing_sensitivity",
        "729600": "set_leadchnl_ra_sensing_polarity",
        "729601": "set_leadchnl_rv_sensing_polarity",
        "729920": "set_leadchnl_ra_sensing_adaptation",
        "729921": "set_leadchnl_rv_sensing_adaptation",
    }

    # Operator-defined lead channel pacing settings (SET_LEADCHNL_*_PACING_)
    LEADCHNL_PACING_CODES = {
        "729984": "set_leadchnl_ra_pacing_amplitude",
        "729985": "set_leadchnl_rv_pacing_amplitude",
        "730048": "set_leadchnl_ra_pacing_pulsewidth",
        "730049": "set_leadchnl_rv_pacing_pulsewidth",
        "730112": "set_leadchnl_ra_pacing_polarity",
        "730113": "set_leadchnl_rv_pacing_polarity",
        "730432": "set_leadchnl_ra_pacing_capture_mode",
        "730433": "set_leadchnl_rv_pacing_capture_mode",
    }

    # Measurement codes (MSMT_) - device-reported measurements
    # Maps to UNIVERSAL variable names for widget compatibility
    BATTERY_MSMT_CODES = {
        "721216": "msmt_battery_datetime",
        "721280": "battery_status",
        "721472": "battery_longevity",  # Universal name
        "721536": "battery_percentage",  # Universal name
    }

    CAPACITOR_MSMT_CODES = {
        "721664": "msmt_cap_charge_datetime",
        "721728": "capacitor_charge_time",
        "721856": "msmt_cap_charge_type",
    }

    LEADCHNL_MSMT_CODES = {
        "721921": "msmt_leadchnl_ra_datetime",
        "721925": "msmt_leadchnl_rv_datetime",
        "722051": "atrial_sensing_amplitude",
        "722055": "ventricular_sensing_amplitude",
        "722112": "msmt_leadchnl_ra_sensing_polarity",
        "722113": "msmt_leadchnl_rv_sensing_polarity",
        "722176": "atrial_pacing_threshold",
        "722177": "ventricular_pacing_threshold",
        "722240": "msmt_leadchnl_ra_pacing_threshold_pulsewidth",
        "722241": "msmt_leadchnl_rv_pacing_threshold_pulsewidth",
        "722304": "msmt_leadchnl_ra_pacing_threshold_method",
        "722305": "msmt_leadchnl_rv_pacing_threshold_method",
        "722368": "msmt_leadchnl_ra_pacing_threshold_polarity",
        "722369": "msmt_leadchnl_rv_pacing_threshold_polarity",
        "722432": "lead_impedance_atrial",  # Universal name for widgets
        "722433": "lead_impedance_ventricular",  # Universal name for widgets
        "722496": "msmt_leadchnl_ra_impedance_polarity",
        "722497": "msmt_leadchnl_rv_impedance_polarity",
    }

    HV_CHANNEL_MSMT_CODES = {
        "722560": "msmt_leadhvchnl_datetime",
        "722624": "msmt_leadhvchnl_impedance",
        "722688": "msmt_leadhvchnl_measurement_type",
    }

    # Statistics codes (STAT_)
    # Maps to UNIVERSAL variable names for widget compatibility
    STAT_CODES = {
        "737489": "stat_datetime_start",
        "737490": "stat_datetime_end",
        "737505": "stat_brady_datetime_start",
        "737506": "stat_brady_datetime_end",
        "737520": "pacing_percent_atrial",  # Universal name
        "737536": "pacing_percent_ventricular",  # Universal name
        "737665": "stat_at_datetime_start",
        "737666": "stat_at_datetime_end",
        "737696": "afib_burden_percent",  # Universal name for widgets
        "737824": "shocks_delivered_recent",
        "737840": "shocks_delivered_total",
        "737856": "shocks_aborted_recent",
        "737872": "shocks_aborted_total",
        "737888": "atp_delivered_recent",
        "737904": "atp_delivered_total",
        "737921": "stat_tachy_total_datetime_start",
        "737922": "stat_tachy_total_datetime_end",
        "737937": "stat_tachy_recent_datetime_start",
        "737938": "stat_tachy_recent_datetime_end",
        "737952": "stat_episode_type",
        "737984": "stat_episode_vendor_type",
        "738000": "episode_count_recent",
        "738017": "stat_episode_recent_count_datetime_start",
        "738018": "stat_episode_recent_count_datetime_end",
    }

    # Episode codes (EPISODE_)
    EPISODE_CODES = {
        "739536": "episode_id",
        "739552": "episode_datetime",
        "739568": "episode_type",
        "739600": "episode_vendor_type",
        "739680": "episode_detection_therapy_details",
        "739712": "episode_duration",
    }

    def __init__(self):
        super().__init__()
        self.vendor_name = "Boston Scientific"

        # Combine all code mappings
        self._code_map = {}
        self._code_map.update(self.DEVICE_INFO_CODES)
        self._code_map.update(self.LEAD_INFO_CODES)
        self._code_map.update(self.SESSION_CODES)
        self._code_map.update(self.BRADY_SETTING_CODES)
        self._code_map.update(self.TACHY_SETTING_CODES)
        self._code_map.update(self.ZONE_SETTING_CODES)
        self._code_map.update(self.LEADCHNL_SENSING_CODES)
        self._code_map.update(self.LEADCHNL_PACING_CODES)
        self._code_map.update(self.BATTERY_MSMT_CODES)
        self._code_map.update(self.CAPACITOR_MSMT_CODES)
        self._code_map.update(self.LEADCHNL_MSMT_CODES)
        self._code_map.update(self.HV_CHANNEL_MSMT_CODES)
        self._code_map.update(self.STAT_CODES)
        self._code_map.update(self.EPISODE_CODES)

    def map_observation_id(self, vendor_code: str, observation_text: str = "") -> Optional[str]:
        """
        Map Boston Scientific MDC_IDC code to universal variable name.

        Args:
            vendor_code: MDC_IDC numeric code (e.g., "720897")
            observation_text: Human-readable text from OBX-3

        Returns:
            Universal variable name or None if unknown
        """
        # Direct code lookup
        if vendor_code in self._code_map:
            return self._code_map[vendor_code]

        # Try to infer from observation text for unknown codes
        text_lower = observation_text.lower()

        # Battery-related
        if "battery" in text_lower:
            if "voltage" in text_lower:
                return "battery_voltage"
            elif "status" in text_lower:
                return "battery_status"
            elif "longevity" in text_lower:
                return "battery_longevity"

        # Lead impedance
        if "impedance" in text_lower:
            if "ra" in text_lower or "atrial" in text_lower:
                return "lead_impedance_atrial"
            elif "rv" in text_lower or "ventricular" in text_lower:
                return "lead_impedance_ventricular"

        # Pacing percentage
        if "pacing" in text_lower and "percent" in text_lower:
            if "atrial" in text_lower or "ra" in text_lower:
                return "pacing_percent_atrial"
            elif "ventricular" in text_lower or "rv" in text_lower:
                return "pacing_percent_ventricular"

        # AF burden
        if "burden" in text_lower and ("af" in text_lower or "atrial" in text_lower):
            return "afib_burden_percent"

        return None

    def decode_egm(self, blob: bytes) -> Optional[Dict]:
        """
        Decode Boston Scientific EGM blob format.

        Boston Scientific typically stores EGM data as PDF documents
        or in proprietary binary format.

        Args:
            blob: Base64-decoded binary EGM data

        Returns:
            Dictionary with decoded EGM data or metadata
        """
        # Check for PDF format
        if blob.startswith(b'%PDF'):
            return {
                'type': 'pdf',
                'size': len(blob),
                'vendor': 'Boston Scientific',
                'note': 'EGM embedded in PDF document'
            }

        # Check for XML format (some BSC exports)
        if blob.startswith(b'<?xml'):
            return {
                'type': 'xml',
                'size': len(blob),
                'vendor': 'Boston Scientific',
                'note': 'EGM in XML format'
            }

        # Unknown binary format
        return {
            'type': 'binary',
            'size': len(blob),
            'vendor': 'Boston Scientific',
            'note': 'Proprietary BSC EGM format - requires vendor SDK'
        }

    @classmethod
    def is_fixed_setting(cls, variable_name: str) -> bool:
        """
        Check if a variable represents a fixed (device) setting.

        Fixed settings are device constants that cannot be changed
        by the operator (e.g., model, serial, implant date).

        Args:
            variable_name: Universal variable name

        Returns:
            True if this is a fixed setting
        """
        fixed_prefixes = ['device_', 'lead_model', 'lead_serial', 'lead_manufacturer',
                          'lead_implant', 'lead_polarity_type', 'lead_location']
        return any(variable_name.startswith(prefix) for prefix in fixed_prefixes)

    @classmethod
    def is_operator_setting(cls, variable_name: str) -> bool:
        """
        Check if a variable represents an operator-defined setting.

        Operator settings are programmed parameters that clinicians
        can change (e.g., pacing mode, rates, sensitivities).

        Args:
            variable_name: Universal variable name

        Returns:
            True if this is an operator-defined setting
        """
        operator_prefixes = ['set_brady_', 'set_tachy_', 'set_zone_', 'set_leadchnl_']
        return any(variable_name.startswith(prefix) for prefix in operator_prefixes)

    @classmethod
    def is_measurement(cls, variable_name: str) -> bool:
        """
        Check if a variable represents a measurement.

        Measurements are device-reported values that are observed,
        not programmed (e.g., battery voltage, lead impedance).

        Args:
            variable_name: Universal variable name

        Returns:
            True if this is a measurement
        """
        measurement_prefixes = ['msmt_', 'stat_', 'episode_']
        return any(variable_name.startswith(prefix) for prefix in measurement_prefixes)

    @classmethod
    def get_setting_category(cls, variable_name: str) -> str:
        """
        Get the category of a setting for UI grouping.

        Args:
            variable_name: Universal variable name

        Returns:
            Category string: 'device', 'brady', 'tachy', 'zone', 'sensing', 'pacing',
                           'battery', 'lead_msmt', 'stats', 'episode', or 'other'
        """
        if variable_name.startswith('device_'):
            return 'device'
        elif variable_name.startswith('lead_') and not variable_name.startswith('lead_impedance'):
            return 'lead_info'
        elif variable_name.startswith('set_brady_'):
            return 'brady'
        elif variable_name.startswith('set_tachy_'):
            return 'tachy'
        elif variable_name.startswith('set_zone_'):
            return 'zone'
        elif 'sensing' in variable_name:
            return 'sensing'
        elif 'pacing' in variable_name and 'set_' in variable_name:
            return 'pacing'
        elif 'battery' in variable_name or 'cap_charge' in variable_name:
            return 'battery'
        elif variable_name.startswith('msmt_leadchnl_') or variable_name.startswith('msmt_leadhvchnl_'):
            return 'lead_msmt'
        elif variable_name.startswith('stat_'):
            return 'stats'
        elif variable_name.startswith('episode_'):
            return 'episode'
        else:
            return 'other'
