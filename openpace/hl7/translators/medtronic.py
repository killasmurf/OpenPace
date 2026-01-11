"""
Medtronic CareLink Translator

Maps Medtronic-specific HL7 codes to universal variables.

Medtronic uses a combination of LOINC codes and proprietary MDC
(Medical Device Communication) codes in their CareLink transmissions.
"""

from typing import Optional, Dict
from openpace.hl7.translators.base_translator import VendorTranslator, GenericTranslator


class MedtronicTranslator(VendorTranslator):
    """
    Translator for Medtronic CareLink HL7 messages.

    Handles Medtronic-specific observation codes and EGM formats.
    """

    # Medtronic-specific code mappings
    # These are examples - actual codes may vary by device model
    MEDTRONIC_CODES = {
        # Battery codes
        "MDC_BATTERY_VOLTAGE": "battery_voltage",
        "MDC_BATTERY_REMAINING": "battery_percent",
        "MDC_BATTERY_ERI": "battery_eri_date",
        "MDC_BATTERY_STATUS": "battery_status",

        # Lead impedance codes
        "MDC_IMP_ATRIAL": "lead_impedance_atrial",
        "MDC_IMP_RV": "lead_impedance_ventricular",
        "MDC_IMP_LV": "lead_impedance_lv",
        "MDC_IMP_RA": "lead_impedance_atrial",
        "MDC_LEAD_IMP_A": "lead_impedance_atrial",
        "MDC_LEAD_IMP_V": "lead_impedance_ventricular",

        # Arrhythmia burden
        "MDC_AFIB_BURDEN": "afib_burden_percent",
        "MDC_AFL_BURDEN": "aflutter_burden_percent",
        "MDC_VT_EPISODES": "vt_episode_count",
        "MDC_SVT_EPISODES": "svt_episode_count",

        # Heart rate statistics
        "MDC_HR_AVERAGE": "heart_rate_mean",
        "MDC_HR_MAX": "heart_rate_max",
        "MDC_HR_MIN": "heart_rate_min",
        "MDC_HR_REST": "heart_rate_resting",

        # Pacing statistics
        "MDC_PACE_PCT_A": "pacing_percent_atrial",
        "MDC_PACE_PCT_V": "pacing_percent_ventricular",
        "MDC_PACE_PCT_BIV": "pacing_percent_biventricular",
        "MDC_PACE_BURDEN": "pacing_burden_total",

        # Device parameters
        "MDC_RATE_LOWER": "lower_rate_limit",
        "MDC_RATE_UPPER": "upper_rate_limit",
        "MDC_MODE": "pacing_mode",
        "MDC_AV_DELAY": "av_delay",

        # Sensing thresholds
        "MDC_SENSE_A": "atrial_sensitivity",
        "MDC_SENSE_V": "ventricular_sensitivity",

        # EGM/Episodes
        "MDC_EGM_STRIP": "egm_strip",
        "MDC_EPISODE_DATA": "episode_data",

        # Activity/Rate Response
        "MDC_ACTIVITY_LEVEL": "activity_level",
        "MDC_RATE_RESPONSE": "rate_response_status",

        # Alerts
        "MDC_ALERT_COUNT": "alert_count",
        "MDC_LEAD_NOISE": "lead_noise_detected",
    }

    def __init__(self):
        super().__init__()
        self.vendor_name = "Medtronic"
        # Fallback to generic translator for LOINC codes
        self.generic_translator = GenericTranslator()

    def map_observation_id(self, vendor_code: str, observation_text: str = "") -> Optional[str]:
        """
        Map Medtronic code to universal variable.

        Args:
            vendor_code: Medtronic MDC code or LOINC code
            observation_text: Human-readable description

        Returns:
            Universal variable name or None
        """
        # Check Medtronic-specific codes first
        if vendor_code in self.MEDTRONIC_CODES:
            return self.MEDTRONIC_CODES[vendor_code]

        # Check if it's a LOINC code (format: XXXXX-X)
        if '-' in vendor_code and vendor_code.replace('-', '').isdigit():
            # Use generic translator for LOINC codes
            return self.generic_translator.map_observation_id(vendor_code, observation_text)

        # Try to infer from observation text
        text_lower = observation_text.lower()

        # Battery-related
        if "battery" in text_lower:
            if "voltage" in text_lower or "volts" in text_lower:
                return "battery_voltage"
            elif "eri" in text_lower or "replacement" in text_lower:
                return "battery_eri_date"
            elif "remaining" in text_lower or "percent" in text_lower:
                return "battery_percent"
            else:
                return "battery_status"

        # Lead impedance
        elif "impedance" in text_lower or "ohm" in text_lower:
            if "atrial" in text_lower or "ra" in text_lower or " a " in text_lower:
                return "lead_impedance_atrial"
            elif "ventricular" in text_lower or "rv" in text_lower or " v " in text_lower:
                return "lead_impedance_ventricular"
            elif "lv" in text_lower or "left" in text_lower:
                return "lead_impedance_lv"
            else:
                return "lead_impedance_ventricular"  # Default to RV

        # Arrhythmia
        elif "afib" in text_lower or "atrial fib" in text_lower:
            if "burden" in text_lower or "percent" in text_lower or "%" in text_lower:
                return "afib_burden_percent"
            else:
                return "afib_episode_count"
        elif "aflutter" in text_lower or "atrial flutter" in text_lower:
            return "aflutter_burden_percent"
        elif "vt" in text_lower or "ventricular tach" in text_lower:
            return "vt_episode_count"
        elif "svt" in text_lower:
            return "svt_episode_count"

        # Pacing
        elif "pacing" in text_lower and "percent" in text_lower:
            if "atrial" in text_lower:
                return "pacing_percent_atrial"
            elif "ventricular" in text_lower:
                return "pacing_percent_ventricular"
            elif "biv" in text_lower or "biventricular" in text_lower:
                return "pacing_percent_biventricular"
            else:
                return "pacing_burden_total"

        # Heart rate
        elif "heart rate" in text_lower or "hr" in text_lower:
            if "average" in text_lower or "mean" in text_lower:
                return "heart_rate_mean"
            elif "max" in text_lower or "maximum" in text_lower:
                return "heart_rate_max"
            elif "min" in text_lower or "minimum" in text_lower:
                return "heart_rate_min"
            else:
                return "heart_rate"

        # EGM
        elif "egm" in text_lower or "electrogram" in text_lower:
            return "egm_strip"

        # Unknown
        return None

    def decode_egm(self, blob: bytes) -> Optional[Dict]:
        """
        Decode Medtronic-specific EGM blob format.

        Medtronic EGMs can be in various formats:
        1. PDF with embedded waveforms
        2. Binary with header + samples
        3. XML/HL7 CDA format

        Args:
            blob: Base64-decoded binary EGM data

        Returns:
            Decoded EGM data or None
        """
        # Check if PDF
        if blob.startswith(b'%PDF'):
            return {
                'type': 'pdf',
                'vendor': 'Medtronic',
                'size': len(blob),
                'note': 'PDF format - requires PDF parsing for waveform extraction'
            }

        # Check if XML/CDA
        if blob.startswith(b'<?xml') or blob.startswith(b'<'):
            return {
                'type': 'xml',
                'vendor': 'Medtronic',
                'size': len(blob),
                'note': 'HL7 CDA format - requires XML parsing'
            }

        # Attempt to parse binary format
        # Medtronic binary EGM typically has:
        # - Header (device info, timestamp, sample rate)
        # - Channel count
        # - Samples (2-byte signed integers, usually)

        if len(blob) < 100:
            # Too small to be valid EGM
            return None

        try:
            # This is a simplified parser - actual format varies by device
            # Real implementation would need detailed Medtronic format specs

            # Assume header is first 64 bytes
            header = blob[:64]

            # Assume samples start at byte 64, 2-byte signed integers
            samples_data = blob[64:]
            sample_count = len(samples_data) // 2

            # Parse as signed 16-bit integers (big-endian typical for medical devices)
            import struct
            samples = []
            for i in range(sample_count):
                offset = i * 2
                if offset + 2 <= len(samples_data):
                    value = struct.unpack('>h', samples_data[offset:offset+2])[0]
                    samples.append(value)

            # Typical Medtronic sample rate is 1000 Hz or 512 Hz
            sample_rate = 1000  # Hz - would be in header

            return {
                'type': 'binary',
                'vendor': 'Medtronic',
                'samples': samples,
                'sample_rate': sample_rate,
                'sample_count': len(samples),
                'channels': ['Atrial', 'Ventricular'],  # Typical
                'note': 'Simplified parsing - may need device-specific adjustments'
            }

        except Exception as e:
            return {
                'type': 'binary',
                'vendor': 'Medtronic',
                'size': len(blob),
                'error': str(e),
                'note': 'Failed to parse - format may be device-specific'
            }

    def __repr__(self):
        return f"<MedtronicTranslator(vendor={self.vendor_name})>"
