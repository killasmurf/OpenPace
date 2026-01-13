"""
EGM (Electrogram) Decoder

Decodes and processes electrogram waveforms from pacemaker transmissions.
Includes signal processing, peak detection, and RR interval calculation.
"""

from typing import Dict, List, Optional, Tuple, Any
import struct
import base64
import logging
import numpy as np
from scipy import signal

from openpace.constants import EGMConstants
from openpace.exceptions import EGMDecodeError

logger = logging.getLogger(__name__)


class EGMDecoder:
    """
    Decodes vendor-specific EGM blob formats and extracts waveform data.

    Supports multiple encoding formats:
    - Raw binary (signed 16-bit integers)
    - PDF embedded waveforms
    - XML/HL7 CDA format
    - Vendor-specific compressed formats
    """

    @staticmethod
    def decode_blob(blob: bytes, vendor: str = 'Generic') -> Optional[Dict[str, Any]]:
        """
        Decode EGM blob based on format detection.

        Args:
            blob: Binary EGM data
            vendor: Device manufacturer

        Returns:
            Dictionary with decoded EGM data or None
        """
        if not blob or len(blob) == 0:
            return None

        # Detect format
        if blob.startswith(b'%PDF'):
            return EGMDecoder._decode_pdf_egm(blob)
        elif blob.startswith(b'<?xml') or blob.startswith(b'<'):
            return EGMDecoder._decode_xml_egm(blob)
        else:
            # Assume raw binary
            return EGMDecoder._decode_binary_egm(blob, vendor)

    @staticmethod
    def _decode_binary_egm(blob: bytes, vendor: str) -> Dict[str, Any]:
        """
        Decode raw binary EGM format.

        Typical structure:
        - Header (64-256 bytes): metadata, sample rate, channel count
        - Samples: 16-bit signed integers (big or little endian)

        Args:
            blob: Binary data
            vendor: Manufacturer name

        Returns:
            Decoded EGM dictionary
        """
        if len(blob) < EGMConstants.TYPICAL_HEADER_SIZE:
            return {'error': 'Blob too small for valid EGM', 'size': len(blob)}

        try:
            # Simple heuristic: try both endianness
            # Most medical devices use big-endian
            samples_be = EGMDecoder._parse_samples(blob, byteorder='big')
            samples_le = EGMDecoder._parse_samples(blob, byteorder='little')

            # Choose based on which gives more reasonable values
            # EGM typically ranges from -5mV to +5mV (or -5000 to +5000 in μV)
            samples = samples_be
            if max(abs(min(samples_le)), abs(max(samples_le))) < max(abs(min(samples_be)), abs(max(samples_be))):
                samples = samples_le

            # Typical sample rates: 256Hz, 512Hz, 1000Hz
            # Estimate based on blob size
            sample_rate = EGMDecoder._estimate_sample_rate(len(samples))

            return {
                'type': 'binary',
                'vendor': vendor,
                'samples': samples.tolist(),
                'sample_count': len(samples),
                'sample_rate': sample_rate,
                'duration_seconds': len(samples) / sample_rate,
                'channels': ['Combined'],  # Single channel assumed
                'unit': 'μV',  # Microvolts
            }

        except Exception as e:
            logger.error(f"Failed to decode binary EGM: {e}")
            return {'error': str(e), 'size': len(blob)}

    @staticmethod
    def _parse_samples(blob: bytes, byteorder: str,
                      header_size: int = EGMConstants.TYPICAL_HEADER_SIZE) -> np.ndarray:
        """
        Parse samples from binary blob.

        Args:
            blob: Binary data
            byteorder: 'big' or 'little'
            header_size: Bytes to skip at start

        Returns:
            Numpy array of samples
        """
        samples_data = blob[header_size:]
        sample_count = len(samples_data) // 2

        if byteorder == 'big':
            format_char = '>h'  # Big-endian signed short
        else:
            format_char = '<h'  # Little-endian signed short

        samples = []
        for i in range(sample_count):
            offset = i * 2
            if offset + 2 <= len(samples_data):
                value = struct.unpack(format_char, samples_data[offset:offset+2])[0]
                samples.append(value)

        return np.array(samples)

    @staticmethod
    def _estimate_sample_rate(sample_count: int) -> int:
        """
        Estimate sample rate based on sample count.

        EGM strips are typically 5-30 seconds long.

        Args:
            sample_count: Number of samples

        Returns:
            Estimated sample rate in Hz
        """
        # Assume typical strip duration
        assumed_duration = EGMConstants.DEFAULT_STRIP_DURATION
        estimated_rate = sample_count / assumed_duration

        # Find closest common rate
        closest_rate = min(
            EGMConstants.COMMON_SAMPLE_RATES,
            key=lambda r: abs(r - estimated_rate)
        )
        return closest_rate

    @staticmethod
    def _decode_pdf_egm(blob: bytes) -> Dict[str, Any]:
        """
        Decode EGM embedded in PDF.

        This is a placeholder - full PDF parsing requires PyPDF2 or similar.

        Args:
            blob: PDF binary data

        Returns:
            Metadata about PDF
        """
        return {
            'type': 'pdf',
            'size': len(blob),
            'note': 'PDF format - requires specialized PDF parser for waveform extraction'
        }

    @staticmethod
    def _decode_xml_egm(blob: bytes) -> Dict[str, Any]:
        """
        Decode EGM in XML/HL7 CDA format.

        This is a placeholder - full XML parsing requires lxml.

        Args:
            blob: XML binary data

        Returns:
            Metadata about XML
        """
        return {
            'type': 'xml',
            'size': len(blob),
            'note': 'HL7 CDA XML format - requires XML parser'
        }


class EGMProcessor:
    """
    Signal processing for EGM waveforms.

    Includes filtering, peak detection, and interval calculation.
    """

    @staticmethod
    def filter_signal(samples: List[float], sample_rate: int,
                     lowcut: float = EGMConstants.BANDPASS_LOW_CUTOFF,
                     highcut: float = EGMConstants.BANDPASS_HIGH_CUTOFF) -> np.ndarray:
        """
        Apply bandpass filter to remove noise.

        Args:
            samples: Raw EGM samples
            sample_rate: Samples per second
            lowcut: Low cutoff frequency (Hz)
            highcut: High cutoff frequency (Hz)

        Returns:
            Filtered signal as numpy array
        """
        try:
            # Convert to numpy array
            signal_array = np.array(samples)

            # Design bandpass filter
            nyquist = sample_rate / 2
            low = lowcut / nyquist
            high = highcut / nyquist

            # Butterworth filter
            b, a = signal.butter(EGMConstants.FILTER_ORDER, [low, high], btype='band')

            # Apply filter
            filtered = signal.filtfilt(b, a, signal_array)

            return filtered

        except Exception as e:
            logger.error(f"Failed to filter signal: {e}")
            return np.array(samples)

    @staticmethod
    def detect_peaks(samples: List[float], sample_rate: int,
                    min_distance_ms: int = EGMConstants.DEFAULT_MIN_PEAK_DISTANCE_MS) -> List[int]:
        """
        Detect R-peaks (QRS complexes) in EGM.

        Args:
            samples: EGM samples
            sample_rate: Samples per second
            min_distance_ms: Minimum time between peaks (milliseconds)

        Returns:
            List of peak indices
        """
        try:
            signal_array = np.array(samples)

            # Convert min distance to samples
            min_distance_samples = int((min_distance_ms / 1000) * sample_rate)

            # Find peaks
            peaks, _ = signal.find_peaks(
                signal_array,
                distance=min_distance_samples,
                prominence=np.std(signal_array) * 0.5  # Adaptive threshold
            )

            return peaks.tolist()

        except Exception as e:
            logger.error(f"Failed to detect peaks: {e}")
            return []

    @staticmethod
    def calculate_rr_intervals(peaks: List[int], sample_rate: int) -> List[float]:
        """
        Calculate RR intervals from peak indices.

        Args:
            peaks: List of peak indices
            sample_rate: Samples per second

        Returns:
            List of RR intervals in milliseconds
        """
        if len(peaks) < 2:
            return []

        rr_intervals = []
        for i in range(1, len(peaks)):
            interval_samples = peaks[i] - peaks[i-1]
            interval_ms = (interval_samples / sample_rate) * 1000
            rr_intervals.append(interval_ms)

        return rr_intervals

    @staticmethod
    def calculate_heart_rate(rr_intervals: List[float]) -> Dict[str, float]:
        """
        Calculate heart rate statistics from RR intervals.

        Args:
            rr_intervals: RR intervals in milliseconds

        Returns:
            Dictionary with HR statistics (bpm)
        """
        if not rr_intervals:
            return {}

        # Convert RR intervals to heart rates
        # HR (bpm) = 60000 ms/min / RR_interval_ms
        from openpace.constants import StatisticalThresholds
        heart_rates = [StatisticalThresholds.MS_PER_MINUTE / rr for rr in rr_intervals if rr > 0]

        if not heart_rates:
            return {}

        return {
            'mean_hr': np.mean(heart_rates),
            'min_hr': np.min(heart_rates),
            'max_hr': np.max(heart_rates),
            'std_hr': np.std(heart_rates),
            'median_hr': np.median(heart_rates),
        }

    @staticmethod
    def analyze_egm(egm_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete EGM analysis pipeline.

        Args:
            egm_data: Decoded EGM dictionary from EGMDecoder

        Returns:
            Enhanced EGM dictionary with analysis results
        """
        if 'samples' not in egm_data or 'sample_rate' not in egm_data:
            return egm_data

        samples = egm_data['samples']
        sample_rate = egm_data['sample_rate']

        # Filter signal
        filtered_samples = EGMProcessor.filter_signal(samples, sample_rate)

        # Detect peaks
        peaks = EGMProcessor.detect_peaks(filtered_samples.tolist(), sample_rate)

        # Calculate RR intervals
        rr_intervals = EGMProcessor.calculate_rr_intervals(peaks, sample_rate)

        # Calculate HR statistics
        hr_stats = EGMProcessor.calculate_heart_rate(rr_intervals)

        # Add analysis results
        return {
            **egm_data,
            'filtered_samples': filtered_samples.tolist(),
            'peaks': peaks,
            'peak_count': len(peaks),
            'rr_intervals': rr_intervals,
            'rr_mean': np.mean(rr_intervals) if rr_intervals else None,
            'rr_std': np.std(rr_intervals) if rr_intervals else None,
            'hr_statistics': hr_stats,
            'analyzed': True,
        }
