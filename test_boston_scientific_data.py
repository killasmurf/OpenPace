#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Script: Boston Scientific LATITUDE Data

Tests the OpenPace system with real Boston Scientific LATITUDE HL7 data
from the csc.1002050604.1.dat file.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from openpace.database.connection import init_database, get_db_session
from openpace.database.models import Patient, Transmission, Observation
from openpace.hl7.parser import HL7Parser
from openpace.processing.trend_calculator import TrendCalculator
from openpace.analysis.battery_analyzer import BatteryAnalyzer
from openpace.analysis.impedance_analyzer import ImpedanceAnalyzer
from openpace.analysis.arrhythmia_analyzer import ArrhythmiaAnalyzer


def test_boston_scientific_file():
    """Test with Boston Scientific LATITUDE data file."""
    print("=" * 80)
    print("Testing OpenPace with Boston Scientific LATITUDE Data")
    print("=" * 80)

    # Initialize database
    print("\n[1/6] Initializing database...")
    init_database(':memory:', echo=False)
    session = get_db_session()
    print("  Database initialized")

    # Load HL7 file
    data_file = Path("tests/sample_data/csc.1002050604.1.dat")

    if not data_file.exists():
        print(f"ERROR: File not found: {data_file}")
        return False

    print(f"\n[2/6] Loading HL7 file: {data_file.name}")
    print(f"  File size: {data_file.stat().st_size / 1024:.1f} KB")

    try:
        with open(data_file, 'r', encoding='utf-8', errors='ignore') as f:
            hl7_content = f.read()
    except Exception as e:
        print(f"ERROR reading file: {e}")
        return False

    # Parse HL7 message
    print("\n[3/6] Parsing HL7 message...")
    parser = HL7Parser(session, anonymize=False)

    try:
        transmission = parser.parse_message(hl7_content, filename=str(data_file))
    except Exception as e:
        print(f"ERROR parsing HL7: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Display parsed results
    print("\n  Transmission Details:")
    print(f"    ID: {transmission.transmission_id}")
    print(f"    Date: {transmission.transmission_date}")
    print(f"    Type: {transmission.transmission_type}")
    print(f"    Manufacturer: {transmission.device_manufacturer}")
    print(f"    Model: {transmission.device_model or 'Not specified'}")
    print(f"    Serial: {transmission.device_serial or 'Not specified'}")
    print(f"    Sending App: {transmission.sending_application}")
    print(f"    Sending Facility: {transmission.sending_facility}")

    print("\n  Patient Details:")
    patient = transmission.patient
    print(f"    ID: {patient.patient_id}")
    print(f"    Name: {patient.patient_name}")
    print(f"    DOB: {patient.date_of_birth}")
    print(f"    Gender: {patient.gender}")

    print(f"\n  Observations: {len(transmission.observations)}")

    # Analyze observations
    print("\n[4/6] Analyzing observations...")

    observation_types = {}
    for obs in transmission.observations:
        var_name = obs.variable_name or "unknown"
        if var_name not in observation_types:
            observation_types[var_name] = []
        observation_types[var_name].append(obs)

    print(f"\n  Found {len(observation_types)} unique observation types:")
    for var_name, obs_list in sorted(observation_types.items()):
        sample_obs = obs_list[0]
        if sample_obs.value_numeric is not None:
            print(f"    - {var_name}: {sample_obs.value_numeric} {sample_obs.unit or ''}")
        elif sample_obs.value_text:
            print(f"    - {var_name}: {sample_obs.value_text}")
        elif sample_obs.value_blob:
            print(f"    - {var_name}: Binary data ({len(sample_obs.value_blob)} bytes)")
        else:
            print(f"    - {var_name}: (no value)")

    # Calculate trends
    print("\n[5/6] Calculating trends...")
    calculator = TrendCalculator(session)
    trends = calculator.calculate_all_trends(patient.patient_id)

    print(f"\n  Computed {len(trends)} trends:")
    for trend in trends:
        print(f"    - {trend.variable_name}:")
        print(f"      Data points: {len(trend.values)}")
        print(f"      Range: {trend.min_value:.2f} - {trend.max_value:.2f}")
        print(f"      Mean: {trend.mean_value:.2f}")

    # Run analysis if we have sufficient trends
    print("\n[6/6] Running clinical analysis...")

    analysis_results = {}

    # Battery analysis
    battery_trend = next((t for t in trends if t.variable_name == 'battery_voltage'), None)
    if battery_trend and len(battery_trend.values) >= 2:
        try:
            battery_analysis = BatteryAnalyzer.analyze_depletion(battery_trend)
            analysis_results['battery'] = battery_analysis
            print("\n  Battery Analysis:")
            print(f"    Current Voltage: {battery_analysis['current_voltage']:.2f}V")
            if battery_analysis.get('years_to_eri'):
                print(f"    Years to ERI: {battery_analysis['years_to_eri']:.1f}")
            print(f"    Recommendation: {BatteryAnalyzer.get_recommendation(battery_analysis)}")
        except Exception as e:
            print(f"  Battery analysis error: {e}")

    # Impedance analysis
    impedance_trends = [t for t in trends if 'impedance' in t.variable_name.lower()]
    if impedance_trends:
        print("\n  Lead Impedance Analysis:")
        for imp_trend in impedance_trends:
            if len(imp_trend.values) >= 2:
                try:
                    imp_analysis = ImpedanceAnalyzer.analyze_trend(imp_trend)
                    lead_name = imp_trend.variable_name.replace('lead_impedance_', '').title()
                    print(f"    {lead_name} Lead:")
                    print(f"      Current: {imp_analysis['current_impedance']:.0f} Ohms")
                    print(f"      Stability: {imp_analysis['stability']['score']:.0f}/100 ({imp_analysis['stability']['rating']})")
                    print(f"      Status: {imp_analysis['overall_status'].upper()}")
                except Exception as e:
                    print(f"    {imp_trend.variable_name} error: {e}")

    # Arrhythmia analysis
    burden_trend = next((t for t in trends if 'burden' in t.variable_name.lower() or 'afib' in t.variable_name.lower()), None)
    if burden_trend and len(burden_trend.values) >= 2:
        try:
            burden_analysis = ArrhythmiaAnalyzer.calculate_burden_statistics(burden_trend)
            analysis_results['arrhythmia'] = burden_analysis
            print("\n  Arrhythmia Burden Analysis:")
            print(f"    Current Burden: {burden_analysis['current_burden']:.1f}%")
            print(f"    Mean Burden: {burden_analysis['mean_burden']:.1f}%")
            print(f"    Classification: {burden_analysis['classification']['type'].title()}")
            print(f"    Recommendation: {ArrhythmiaAnalyzer.get_recommendation(burden_analysis)}")
        except Exception as e:
            print(f"  Arrhythmia analysis error: {e}")

    # Check for EGM data
    egm_observations = [obs for obs in transmission.observations if obs.value_blob]
    if egm_observations:
        print(f"\n  EGM Episodes: {len(egm_observations)} found")
        for i, obs in enumerate(egm_observations[:3], 1):  # Show first 3
            print(f"    Episode {i}: {len(obs.value_blob)} bytes")

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"  Patient: {patient.patient_name} ({patient.patient_id})")
    print(f"  Transmissions: 1")
    print(f"  Observations: {len(transmission.observations)}")
    print(f"  Trends: {len(trends)}")
    print(f"  EGM Episodes: {len(egm_observations)}")
    print(f"  Analyses: {len(analysis_results)}")

    success = len(transmission.observations) > 0

    if success:
        print("\n" + "=" * 80)
        print("SUCCESS! Boston Scientific data processed successfully.")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("WARNING! No observations were parsed.")
        print("=" * 80)

    return success


def main():
    """Main test function."""
    print("\nOpenPace - Boston Scientific LATITUDE Data Test")
    print("Testing with real device data from csc.1002050604.1.dat")
    print()

    success = test_boston_scientific_file()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
