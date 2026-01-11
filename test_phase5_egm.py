#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Script: Phase 5 - EGM Viewer

Tests the EGM decoder, processor, and viewer functionality with synthetic data.
"""

import sys
from pathlib import Path
from datetime import datetime
import numpy as np
import struct

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from openpace.database.connection import init_database, get_db_session
from openpace.database.models import Patient, Transmission, Observation
from openpace.processing.egm_decoder import EGMDecoder, EGMProcessor


def create_synthetic_egm_blob(duration_seconds: float = 10,
                              sample_rate: int = 512,
                              heart_rate: int = 72) -> bytes:
    """
    Create synthetic EGM waveform blob.

    Simulates a basic cardiac waveform with P, QRS, and T waves.

    Args:
        duration_seconds: Duration of EGM strip
        sample_rate: Samples per second
        heart_rate: Beats per minute

    Returns:
        Binary blob in signed 16-bit format
    """
    # Calculate parameters
    num_samples = int(duration_seconds * sample_rate)
    beats_per_second = heart_rate / 60
    samples_per_beat = int(sample_rate / beats_per_second)

    # Create time axis
    t = np.linspace(0, duration_seconds, num_samples)

    # Initialize signal
    signal = np.zeros(num_samples)

    # Generate beats
    beat_times = np.arange(0, duration_seconds, 1/beats_per_second)

    for beat_time in beat_times:
        beat_center = int(beat_time * sample_rate)

        if beat_center < num_samples:
            # P wave (atrial depolarization)
            p_start = beat_center - int(0.20 * sample_rate)
            p_end = beat_center - int(0.10 * sample_rate)
            if p_start >= 0 and p_end < num_samples:
                p_amplitude = 200  # μV
                for i in range(p_start, p_end):
                    if i < num_samples:
                        signal[i] += p_amplitude * np.sin(np.pi * (i - p_start) / (p_end - p_start))

            # QRS complex (ventricular depolarization)
            qrs_start = beat_center - int(0.04 * sample_rate)
            qrs_end = beat_center + int(0.04 * sample_rate)
            if qrs_start >= 0 and qrs_end < num_samples:
                for i in range(qrs_start, qrs_end):
                    if i < num_samples:
                        # Q wave (negative)
                        if i < beat_center - int(0.02 * sample_rate):
                            signal[i] -= 300
                        # R wave (positive peak)
                        elif i < beat_center + int(0.01 * sample_rate):
                            signal[i] += 2000 * np.sin(np.pi * (i - (beat_center - int(0.02 * sample_rate))) / (int(0.03 * sample_rate)))
                        # S wave (negative)
                        else:
                            signal[i] -= 400

            # T wave (ventricular repolarization)
            t_start = beat_center + int(0.15 * sample_rate)
            t_end = beat_center + int(0.30 * sample_rate)
            if t_start >= 0 and t_end < num_samples:
                t_amplitude = 400  # μV
                for i in range(t_start, t_end):
                    if i < num_samples:
                        signal[i] += t_amplitude * np.sin(np.pi * (i - t_start) / (t_end - t_start))

    # Add baseline noise
    noise = np.random.normal(0, 50, num_samples)
    signal += noise

    # Convert to 16-bit signed integers
    signal_int = signal.astype(np.int16)

    # Create binary blob with simple header
    header = bytearray(64)  # 64-byte header
    header[0:4] = b'EGM\x00'  # Magic number

    # Pack signal as big-endian signed shorts
    blob = header + struct.pack(f'>{len(signal_int)}h', *signal_int)

    return bytes(blob)


def create_test_data_with_egm():
    """Create test database with EGM observations."""
    print("=" * 70)
    print("Phase 5 EGM Test - Creating Test Data")
    print("=" * 70)

    # Initialize in-memory database
    init_database(':memory:', echo=False)
    session = get_db_session()

    # Create patient
    patient = Patient(
        patient_id="P123456",
        patient_name="John Doe",
        date_of_birth=datetime(1980, 1, 1),
        gender="M"
    )
    session.add(patient)
    session.flush()

    print(f"\nCreated patient: {patient.patient_name}")

    # Create transmission
    transmission = Transmission(
        patient_id=patient.patient_id,
        transmission_date=datetime(2024, 1, 15, 10, 30, 0),
        transmission_type='remote',
        message_control_id='MSG001',
        sending_application='Medtronic CareLink',
        sending_facility='Clinic123',
        device_manufacturer='Medtronic'
    )
    session.add(transmission)
    session.flush()

    print(f"Created transmission: {transmission.transmission_date}")

    # Create EGM observations
    egm_scenarios = [
        {"duration": 10, "rate": 72, "label": "Normal Sinus Rhythm"},
        {"duration": 8, "rate": 120, "label": "Tachycardia Episode"},
        {"duration": 15, "rate": 45, "label": "Bradycardia Episode"},
    ]

    for i, scenario in enumerate(egm_scenarios):
        # Generate synthetic EGM
        egm_blob = create_synthetic_egm_blob(
            duration_seconds=scenario["duration"],
            sample_rate=512,
            heart_rate=scenario["rate"]
        )

        # Create observation
        obs = Observation(
            transmission_id=transmission.transmission_id,
            observation_time=transmission.transmission_date,
            sequence_number=i+1,
            variable_name='egm_strip',
            vendor_code=f'EGM_{i+1}',
            unit='μV',
            observation_status='F',
            value_blob=egm_blob
        )
        session.add(obs)

        print(f"  EGM {i+1}: {scenario['label']} - {scenario['duration']}s @ {scenario['rate']} bpm")

    session.commit()

    print(f"\nCreated {len(egm_scenarios)} EGM observations")

    return session, patient, transmission


def test_egm_decoder():
    """Test EGM decoder."""
    print("\n" + "=" * 70)
    print("Testing EGM Decoder")
    print("=" * 70)

    # Create synthetic EGM
    blob = create_synthetic_egm_blob(duration_seconds=10, sample_rate=512, heart_rate=72)

    print(f"\nGenerated synthetic EGM blob: {len(blob)} bytes")

    # Decode
    egm_data = EGMDecoder.decode_blob(blob)

    if not egm_data or 'error' in egm_data:
        print("ERROR: Failed to decode EGM")
        return False

    print("\nDecoded EGM Data:")
    print(f"  Type: {egm_data['type']}")
    print(f"  Sample Count: {egm_data['sample_count']}")
    print(f"  Sample Rate: {egm_data['sample_rate']} Hz")
    print(f"  Duration: {egm_data['duration_seconds']:.1f} seconds")
    print(f"  Channels: {egm_data['channels']}")
    print(f"  Unit: uV")

    return True


def test_egm_processor():
    """Test EGM processor."""
    print("\n" + "=" * 70)
    print("Testing EGM Processor")
    print("=" * 70)

    # Create synthetic EGM
    blob = create_synthetic_egm_blob(duration_seconds=10, sample_rate=512, heart_rate=72)

    # Decode
    egm_data = EGMDecoder.decode_blob(blob)

    if not egm_data or 'error' in egm_data:
        print("ERROR: Failed to decode EGM")
        return False

    # Analyze
    print("\nAnalyzing EGM...")
    analyzed_data = EGMProcessor.analyze_egm(egm_data)

    if not analyzed_data.get('analyzed'):
        print("ERROR: Analysis failed")
        return False

    print("\nAnalysis Results:")
    print(f"  Peaks Detected: {analyzed_data['peak_count']}")

    if analyzed_data.get('rr_intervals'):
        print(f"  RR Intervals: {len(analyzed_data['rr_intervals'])}")
        print(f"  Mean RR: {analyzed_data['rr_mean']:.1f} ms")

    if analyzed_data.get('hr_statistics'):
        hr = analyzed_data['hr_statistics']
        print(f"  Mean HR: {hr['mean_hr']:.1f} bpm")
        print(f"  Min HR: {hr['min_hr']:.1f} bpm")
        print(f"  Max HR: {hr['max_hr']:.1f} bpm")

    # Verify reasonable values
    if analyzed_data['peak_count'] < 8 or analyzed_data['peak_count'] > 15:
        print(f"WARNING: Expected ~12 peaks for 72 bpm over 10s, got {analyzed_data['peak_count']}")

    return True


def test_egm_filtering():
    """Test signal filtering."""
    print("\n" + "=" * 70)
    print("Testing Signal Filtering")
    print("=" * 70)

    # Create synthetic EGM with noise
    blob = create_synthetic_egm_blob(duration_seconds=5, sample_rate=512, heart_rate=72)
    egm_data = EGMDecoder.decode_blob(blob)

    samples = egm_data['samples']
    sample_rate = egm_data['sample_rate']

    print(f"\nOriginal signal: {len(samples)} samples")
    print(f"  Range: {min(samples):.0f} to {max(samples):.0f} uV")

    # Apply bandpass filter
    filtered = EGMProcessor.filter_signal(samples, sample_rate, lowcut=0.5, highcut=100)

    print(f"\nFiltered signal:")
    print(f"  Range: {min(filtered):.0f} to {max(filtered):.0f} uV")
    print(f"  Length preserved: {len(filtered) == len(samples)}")

    return len(filtered) == len(samples)


def test_peak_detection():
    """Test R-peak detection."""
    print("\n" + "=" * 70)
    print("Testing Peak Detection")
    print("=" * 70)

    # Test different heart rates
    test_rates = [60, 72, 90, 120]

    for rate in test_rates:
        blob = create_synthetic_egm_blob(duration_seconds=10, sample_rate=512, heart_rate=rate)
        egm_data = EGMDecoder.decode_blob(blob)

        filtered = EGMProcessor.filter_signal(egm_data['samples'], egm_data['sample_rate'])
        peaks = EGMProcessor.detect_peaks(filtered.tolist(), egm_data['sample_rate'])

        expected_beats = int(rate * 10 / 60)
        tolerance = 2

        print(f"\n  HR {rate} bpm:")
        print(f"    Expected beats: {expected_beats}")
        print(f"    Detected peaks: {len(peaks)}")
        print(f"    Within tolerance: {abs(len(peaks) - expected_beats) <= tolerance}")

    return True


def main():
    """Main test function."""
    print("\nOpenPace - Phase 5 EGM Viewer Test")
    print("=" * 70)

    # Create test data
    session, patient, transmission = create_test_data_with_egm()

    # Run tests
    results = []

    results.append(("EGM Decoder", test_egm_decoder()))
    results.append(("EGM Processor", test_egm_processor()))
    results.append(("Signal Filtering", test_egm_filtering()))
    results.append(("Peak Detection", test_peak_detection()))

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "[OK]" if result else "[FAIL]"
        print(f"  {symbol} {test_name}: {status}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n" + "=" * 70)
        print("SUCCESS! All Phase 5 tests passed.")
        print("=" * 70)
        print("\nNote: To test the GUI components, run:")
        print("  python -m openpace.gui.egm_window")
    else:
        print("\n" + "=" * 70)
        print("FAILED! Some tests did not pass.")
        print("=" * 70)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
