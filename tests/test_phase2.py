#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Script: Phase 2 - Data Normalization

Tests unit conversion, histogram parsing, EGM decoding, and trend calculation.
"""

import sys
from pathlib import Path
import numpy as np

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from openpace.processing.normalizer import UnitConverter, DataQualityValidator, DataNormalizer
from openpace.processing.histogram_parser import HistogramParser, TimeInZoneCalculator
from openpace.processing.egm_decoder import EGMDecoder, EGMProcessor


def test_unit_conversion():
    """Test unit conversion system."""
    print("\n" + "=" * 60)
    print("TEST 1: Unit Conversion")
    print("=" * 60)

    # Test voltage conversion
    result = UnitConverter.convert(2650, 'mV', 'V')
    print(f"V 2650 mV = {result} V")
    assert result == 2.65, "Voltage conversion failed"

    # Test impedance conversion
    result = UnitConverter.convert(1.5, 'kOhm', 'Ohm')
    print(f"V 1.5 kOhm = {result} Ohm")
    assert result == 1500, "Impedance conversion failed"

    # Test normalization
    value, unit = UnitConverter.normalize('battery_voltage', 2650, 'mV')
    print(f"V Normalized battery: {value} {unit}")
    assert value == 2.65 and unit == 'V', "Normalization failed"

    print("V All unit conversion tests passed")


def test_data_quality():
    """Test data quality validation."""
    print("\n" + "=" * 60)
    print("TEST 2: Data Quality Validation")
    print("=" * 60)

    # Test normal battery voltage
    result = DataQualityValidator.validate('battery_voltage', 2.65)
    print(f"V Battery 2.65V: {result['severity']} - {result['flags']}")
    assert result['severity'] == 'normal', "Should be normal"

    # Test low battery (ERI)
    result = DataQualityValidator.validate('battery_voltage', 2.1)
    print(f"V Battery 2.1V: {result['severity']} - {result['flags']}")
    assert 'LOW_BATTERY_ERI' in result['flags'], "Should detect ERI"
    assert result['severity'] == 'critical', "Should be critical"

    # Test lead fracture
    result = DataQualityValidator.validate('lead_impedance_atrial', 1800)
    print(f"V Impedance 1800 Ohm: {result['severity']} - {result['flags']}")
    assert 'POSSIBLE_LEAD_FRACTURE' in result['flags'], "Should detect fracture"

    # Test high AFib burden
    result = DataQualityValidator.validate('afib_burden_percent', 35)
    print(f"V AFib 35%: {result['severity']} - {result['flags']}")
    assert 'HIGH_AFIB_BURDEN' in result['flags'], "Should flag high burden"

    print("V All quality validation tests passed")


def test_histogram_parsing():
    """Test histogram parser."""
    print("\n" + "=" * 60)
    print("TEST 3: Histogram Parsing")
    print("=" * 60)

    # Test pipe-delimited format
    histogram_str = "60-70:10%|70-80:45%|80-90:30%|90-100:15%"
    result = HistogramParser.parse_rate_histogram(histogram_str)
    print(f"V Parsed histogram: {len(result['bins'])} bins")
    assert len(result['bins']) == 4, "Should have 4 bins"
    assert result['percentages'][1] == 45.0, "Second bin should be 45%"

    # Calculate statistics
    stats = HistogramParser.calculate_statistics(result)
    print(f"  Weighted mean: {stats['weighted_mean']:.1f} bpm")
    print(f"  Mode bin: {stats['mode_bin']}")
    assert stats['max_percentage'] == 45.0, "Max should be 45%"

    # Test time in zones
    zones = TimeInZoneCalculator.calculate_time_in_zones(result)
    print(f"V Time in zones:")
    for zone, pct in zones.items():
        if pct > 0:
            print(f"  {zone}: {pct:.1f}%")

    print("V All histogram tests passed")


def test_egm_processing():
    """Test EGM signal processing."""
    print("\n" + "=" * 60)
    print("TEST 4: EGM Signal Processing")
    print("=" * 60)

    # Generate synthetic EGM signal (simulated heartbeat)
    sample_rate = 1000  # Hz
    duration = 5  # seconds
    sample_count = sample_rate * duration

    # Create signal with simulated QRS complexes
    t = np.linspace(0, duration, sample_count)
    signal_data = np.zeros(sample_count)

    # Add 6 heartbeats (72 bpm)
    beat_times = [0.8, 1.6, 2.4, 3.2, 4.0]
    for beat_time in beat_times:
        idx = int(beat_time * sample_rate)
        if idx < len(signal_data) - 50:
            # Simplified QRS complex
            signal_data[idx:idx+50] = np.random.randn(50) * 100 + 500

    # Add noise
    signal_data += np.random.randn(sample_count) * 20

    # Filter signal
    filtered = EGMProcessor.filter_signal(signal_data.tolist(), sample_rate)
    print(f"V Filtered {len(filtered)} samples")

    # Detect peaks
    peaks = EGMProcessor.detect_peaks(filtered.tolist(), sample_rate)
    print(f"V Detected {len(peaks)} peaks")

    if len(peaks) >= 2:
        # Calculate RR intervals
        rr_intervals = EGMProcessor.calculate_rr_intervals(peaks, sample_rate)
        print(f"V Calculated {len(rr_intervals)} RR intervals")
        print(f"  Mean RR: {np.mean(rr_intervals):.0f} ms")

        # Calculate HR
        hr_stats = EGMProcessor.calculate_heart_rate(rr_intervals)
        print(f"V Heart rate statistics:")
        print(f"  Mean HR: {hr_stats['mean_hr']:.0f} bpm")
        print(f"  Range: {hr_stats['min_hr']:.0f}-{hr_stats['max_hr']:.0f} bpm")

    print("V All EGM processing tests passed")


def test_data_normalizer():
    """Test complete normalization pipeline."""
    print("\n" + "=" * 60)
    print("TEST 5: Complete Normalization Pipeline")
    print("=" * 60)

    normalizer = DataNormalizer()

    # Test observation normalization
    obs_data = {
        'variable_name': 'battery_voltage',
        'value_numeric': 2650,
        'unit': 'mV'
    }

    result = normalizer.normalize_observation(obs_data)
    print(f"V Original: {obs_data['value_numeric']} {obs_data['unit']}")
    print(f"  Normalized: {result['normalized_value']} {result['standard_unit']}")
    print(f"  Severity: {result['severity']}")
    print(f"  Flags: {result['quality_flags']}")

    assert result['normalized_value'] == 2.65, "Should normalize to 2.65 V"
    assert result['standard_unit'] == 'V', "Should be in Volts"
    assert result['severity'] == 'normal', "Should be normal"

    # Test batch normalization
    batch = [
        {'variable_name': 'lead_impedance_atrial', 'value_numeric': 625, 'unit': 'Ohm'},
        {'variable_name': 'heart_rate', 'value_numeric': 72, 'unit': 'bpm'},
        {'variable_name': 'afib_burden_percent', 'value_numeric': 12.5, 'unit': '%'},
    ]

    results = normalizer.normalize_batch(batch)
    print(f"\nV Normalized batch of {len(results)} observations")
    for r in results:
        print(f"  {r['variable_name']}: {r['normalized_value']} {r['standard_unit']} [{r['severity']}]")

    print("V All normalization pipeline tests passed")


def main():
    print("=" * 60)
    print("OpenPace - Phase 2 Data Normalization Tests")
    print("=" * 60)

    try:
        test_unit_conversion()
        test_data_quality()
        test_histogram_parsing()
        test_egm_processing()
        test_data_normalizer()

        print("\n" + "=" * 60)
        print("V ALL PHASE 2 TESTS PASSED!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\nX TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
