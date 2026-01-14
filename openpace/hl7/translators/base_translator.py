"""
Base Vendor Translator

Abstract base class for vendor-specific HL7 code translations.

Each pacemaker manufacturer uses different proprietary codes in OBX segments.
Translators map these vendor codes to universal variable names.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict


class VendorTranslator(ABC):
    """
    Abstract base class for vendor-specific translators.

    Subclasses implement mapping logic for specific manufacturers
    (Medtronic, Boston Scientific, Abbott, Biotronik).
    """

    def __init__(self):
        self.vendor_name = "Generic"

    @abstractmethod
    def map_observation_id(self, vendor_code: str, observation_text: str = "") -> Optional[str]:
        """
        Map vendor-specific observation code to universal variable name.

        Args:
            vendor_code: Vendor's proprietary code or LOINC code
            observation_text: Human-readable text from OBX-3

        Returns:
            Universal variable name (e.g., "battery_voltage") or None if unknown
        """
        pass

    @abstractmethod
    def decode_egm(self, blob: bytes) -> Optional[Dict]:
        """
        Decode vendor-specific EGM blob format.

        Args:
            blob: Base64-decoded binary EGM data

        Returns:
            Dictionary with:
                - samples: List of voltage samples (mV)
                - sample_rate: Samples per second (Hz)
                - channels: List of channel names
            Or None if unable to decode
        """
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__}(vendor={self.vendor_name})>"


class GenericTranslator(VendorTranslator):
    """
    Generic translator using standard LOINC codes.

    Fallback for unknown vendors or standardized HL7 messages.
    """

    # Standard LOINC code mappings
    # Source: https://loinc.org/
    LOINC_MAP = {
        # Battery observations
        "73990-7": "battery_voltage",
        "73991-5": "battery_eri_date",
        "73992-3": "battery_impedance",

        # Lead impedance
        "8889-8": "lead_impedance_atrial",
        "8890-6": "lead_impedance_ventricular",
        "8891-4": "lead_impedance_rv",
        "8892-2": "lead_impedance_lv",

        # Arrhythmia burden
        "89269-2": "afib_burden_percent",
        "89270-0": "vt_burden_percent",
        "89271-8": "svt_burden_percent",

        # Heart rate
        "8867-4": "heart_rate",
        "8893-0": "heart_rate_max",
        "8894-8": "heart_rate_min",
        "8895-5": "heart_rate_mean",

        # Pacing
        "8896-3": "pacing_percent_atrial",
        "8897-1": "pacing_percent_ventricular",
        "8898-9": "pacing_percent_biventricular",

        # EGM/Waveforms
        "11524-6": "egm_strip",
        "11525-3": "ecg_waveform",
        "18750-0": "cardiac_ep_report",  # Cardiac Electrophysiology Report (PDF)

        # Device parameters
        "8899-7": "lower_rate_limit",
        "8900-3": "upper_rate_limit",
        "8901-1": "pacing_mode",

        # Sensing
        "8902-9": "atrial_sensitivity",
        "8903-7": "ventricular_sensitivity",
    }

    def __init__(self):
        super().__init__()
        self.vendor_name = "Generic"

    def map_observation_id(self, vendor_code: str, observation_text: str = "") -> Optional[str]:
        """
        Map LOINC code to universal variable.

        Args:
            vendor_code: LOINC code or vendor-specific code
            observation_text: Observation description

        Returns:
            Universal variable name or None
        """
        # Direct LOINC lookup
        if vendor_code in self.LOINC_MAP:
            return self.LOINC_MAP[vendor_code]

        # Try direct vendor code as lowercase (for simple text codes)
        code_lower = vendor_code.lower()

        # Check if vendor code is already a reasonable variable name
        # (e.g., "BATTERY_VOLTAGE" -> "battery_voltage")
        if code_lower in ['battery_voltage', 'battery_current', 'battery_impedance',
                          'ra_lead_impedance', 'rv_lead_impedance', 'lv_lead_impedance',
                          'atrial_sensing', 'ventricular_sensing',
                          'a_pace_threshold', 'v_pace_threshold',
                          'af_episode_count', 'vt_episode_count',
                          'device_model', 'device_serial', 'longevity_estimate']:
            return code_lower

        # Try to infer from observation text
        text_lower = observation_text.lower()

        if "battery" in text_lower and "voltage" in text_lower:
            return "battery_voltage"
        elif "battery" in text_lower and "current" in text_lower:
            return "battery_current"
        elif "impedance" in text_lower and ("atrial" in text_lower or "ra" in text_lower):
            return "lead_impedance_atrial"
        elif "impedance" in text_lower and ("ventricular" in text_lower or "rv" in text_lower):
            return "lead_impedance_ventricular"
        elif "afib" in text_lower or "atrial fib" in text_lower or "af episode" in text_lower:
            return "afib_burden_percent"
        elif "pacing" in text_lower and "percent" in text_lower:
            return "pacing_percent_ventricular"
        elif "longevity" in text_lower or "battery" in text_lower and "estimate" in text_lower:
            return "longevity_estimate"
        elif "device" in text_lower and "model" in text_lower:
            return "device_model"
        elif "device" in text_lower and "serial" in text_lower:
            return "device_serial"
        elif "sensing" in text_lower and "atrial" in text_lower:
            return "atrial_sensing"
        elif "sensing" in text_lower and "ventricular" in text_lower:
            return "ventricular_sensing"
        elif "threshold" in text_lower and "atrial" in text_lower:
            return "atrial_pacing_threshold"
        elif "threshold" in text_lower and "ventricular" in text_lower:
            return "ventricular_pacing_threshold"

        return None

    def decode_egm(self, blob: bytes) -> Optional[Dict]:
        """
        Generic EGM decoder - attempts to parse common formats.

        Args:
            blob: Binary EGM data

        Returns:
            Decoded EGM data or None
        """
        # Check if blob is a PDF
        if blob.startswith(b'%PDF'):
            return {
                'type': 'pdf',
                'size': len(blob),
                'note': 'EGM embedded in PDF - requires vendor-specific extraction'
            }

        # Generic binary data - return metadata only
        return {
            'type': 'binary',
            'size': len(blob),
            'note': 'Vendor-specific decoder required'
        }


def get_translator(vendor: str) -> VendorTranslator:
    """
    Factory function to get appropriate translator for a vendor.

    Args:
        vendor: Vendor name (Medtronic, Boston Scientific, Abbott, Biotronik, etc.)

    Returns:
        VendorTranslator instance
    """
    vendor_upper = vendor.upper()

    if "MEDTRONIC" in vendor_upper:
        from openpace.hl7.translators.medtronic import MedtronicTranslator
        return MedtronicTranslator()
    elif "BOSTON" in vendor_upper or "BSC" in vendor_upper or "LATITUDE" in vendor_upper:
        from openpace.hl7.translators.boston_scientific import BostonScientificTranslator
        return BostonScientificTranslator()
    elif "ABBOTT" in vendor_upper or "SJM" in vendor_upper:
        # from openpace.hl7.translators.abbott import AbbottTranslator
        # return AbbottTranslator()
        # Placeholder - use generic for now
        return GenericTranslator()
    elif "BIOTRONIK" in vendor_upper:
        # from openpace.hl7.translators.biotronik import BiotronikTranslator
        # return BiotronikTranslator()
        # Placeholder - use generic for now
        return GenericTranslator()
    else:
        return GenericTranslator()
