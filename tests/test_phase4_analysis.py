#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Script: Phase 4 - Analysis & Reports

Tests the analysis engines and PDF report generation functionality.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from openpace.database.connection import init_database, get_db_session
from openpace.database.models import Patient, Transmission, Observation
from openpace.processing.trend_calculator import TrendCalculator
from openpace.analysis.battery_analyzer import BatteryAnalyzer
from openpace.analysis.impedance_analyzer import ImpedanceAnalyzer
from openpace.analysis.arrhythmia_analyzer import ArrhythmiaAnalyzer
from openpace.export.pdf_report import PDFReportGenerator


def create_test_data():
    """Create test data with multiple transmissions."""
    print("=" * 70)
    print("Phase 4 Analysis Test - Creating Test Data")
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

    # Create 5 transmissions over 2 years
    base_date = datetime(2022, 1, 15, 12, 0, 0)
    transmissions = []

    for i in range(5):
        trans_date = base_date + timedelta(days=180 * i)  # Every 6 months

        transmission = Transmission(
            patient_id=patient.patient_id,
            transmission_date=trans_date,
            transmission_type='remote',
            message_control_id=f'MSG00{i+1}',
            sending_application='Medtronic CareLink',
            sending_facility='Clinic123',
            device_manufacturer='Medtronic',
            device_model='Azure XT DR',
            device_serial=f'SN{1000+i}'
        )
        session.add(transmission)
        session.flush()

        # Add battery voltage observation (declining over time)
        battery_voltage = 2.8 - (i * 0.15)  # Declining from 2.8V to 2.2V
        obs_battery = Observation(
            transmission_id=transmission.transmission_id,
            observation_time=trans_date,
            sequence_number=1,
            variable_name='battery_voltage',
            loinc_code='73990-7',
            vendor_code='73990-7',
            unit='V',
            reference_range='2.2-2.8',
            abnormal_flag='N' if battery_voltage >= 2.3 else 'L',
            value_numeric=battery_voltage
        )
        session.add(obs_battery)

        # Add atrial impedance (stable with slight variation)
        atrial_impedance = 625 + (i * 10) - 20
        obs_atrial = Observation(
            transmission_id=transmission.transmission_id,
            observation_time=trans_date,
            sequence_number=2,
            variable_name='lead_impedance_atrial',
            loinc_code='8889-8',
            vendor_code='8889-8',
            unit='Ohm',
            reference_range='200-1500',
            abnormal_flag='N',
            value_numeric=atrial_impedance
        )
        session.add(obs_atrial)

        # Add ventricular impedance
        ventricular_impedance = 485 + (i * 12)
        obs_ventricular = Observation(
            transmission_id=transmission.transmission_id,
            observation_time=trans_date,
            sequence_number=3,
            variable_name='lead_impedance_ventricular',
            loinc_code='8890-6',
            vendor_code='8890-6',
            unit='Ohm',
            reference_range='200-1500',
            abnormal_flag='N',
            value_numeric=ventricular_impedance
        )
        session.add(obs_ventricular)

        # Add AFib burden (increasing over time)
        afib_burden = 5.0 + (i * 4.0)  # Increasing from 5% to 21%
        obs_burden = Observation(
            transmission_id=transmission.transmission_id,
            observation_time=trans_date,
            sequence_number=4,
            variable_name='afib_burden_percent',
            loinc_code='89269-2',
            vendor_code='89269-2',
            unit='%',
            reference_range='0-100',
            abnormal_flag='H' if afib_burden > 20 else 'N',
            value_numeric=afib_burden
        )
        session.add(obs_burden)

        transmissions.append(transmission)
        print(f"  Transmission {i+1}: {trans_date.strftime('%Y-%m-%d')} - "
              f"Battery: {battery_voltage:.2f}V, AFib: {afib_burden:.1f}%")

    session.commit()

    print(f"\nCreated {len(transmissions)} transmissions")

    return session, patient, transmissions


def test_battery_analyzer(session, patient_id):
    """Test battery analyzer."""
    print("\n" + "=" * 70)
    print("Testing Battery Analyzer")
    print("=" * 70)

    calculator = TrendCalculator(session)
    trend = calculator.calculate_trend(patient_id, 'battery_voltage')

    if not trend:
        print("ERROR: No battery trend calculated")
        return False

    print(f"\nTrend data points: {len(trend.values)}")
    print(f"Value range: {trend.min_value:.2f}V - {trend.max_value:.2f}V")

    # Analyze depletion
    analysis = BatteryAnalyzer.analyze_depletion(trend)

    print("\nBattery Analysis Results:")
    print(f"  Current Voltage: {analysis['current_voltage']:.2f}V")
    print(f"  Depletion Rate: {abs(analysis['depletion_rate_v_per_year']):.3f} V/year")
    print(f"  Years to ERI: {analysis['years_to_eri']:.1f}" if analysis['years_to_eri'] else "  Years to ERI: N/A")
    print(f"  Predicted ERI Date: {analysis['predicted_eri_date']}" if analysis['predicted_eri_date'] else "  Predicted ERI Date: N/A")
    print(f"  Remaining Capacity: {analysis['remaining_capacity_percent']:.1f}%")
    print(f"  Confidence: {analysis['confidence']}")

    recommendation = BatteryAnalyzer.get_recommendation(analysis)
    print(f"\nRecommendation: {recommendation}")

    return True


def test_impedance_analyzer(session, patient_id):
    """Test impedance analyzer."""
    print("\n" + "=" * 70)
    print("Testing Impedance Analyzer")
    print("=" * 70)

    calculator = TrendCalculator(session)

    for lead_name in ['lead_impedance_atrial', 'lead_impedance_ventricular']:
        trend = calculator.calculate_trend(patient_id, lead_name)

        if not trend:
            continue

        print(f"\n{lead_name.replace('lead_impedance_', '').title()} Lead:")
        print(f"  Data points: {len(trend.values)}")
        print(f"  Range: {trend.min_value:.0f} - {trend.max_value:.0f} Ohms")

        # Full analysis
        analysis = ImpedanceAnalyzer.analyze_trend(trend)

        print(f"  Current: {analysis['current_impedance']:.0f} Ohms")
        print(f"  Stability Score: {analysis['stability']['score']:.0f}/100 ({analysis['stability']['rating']})")
        print(f"  Anomalies: {analysis['anomaly_count']}")
        print(f"  Status: {analysis['overall_status'].upper()}")
        print(f"  Recommendation: {analysis['recommendation']}")

    return True


def test_arrhythmia_analyzer(session, patient_id):
    """Test arrhythmia analyzer."""
    print("\n" + "=" * 70)
    print("Testing Arrhythmia Analyzer")
    print("=" * 70)

    calculator = TrendCalculator(session)
    trend = calculator.calculate_trend(patient_id, 'afib_burden_percent')

    if not trend:
        print("ERROR: No AFib burden trend calculated")
        return False

    print(f"\nTrend data points: {len(trend.values)}")

    # Analyze burden
    analysis = ArrhythmiaAnalyzer.calculate_burden_statistics(trend)

    print("\nArrhythmia Burden Analysis:")
    print(f"  Current Burden: {analysis['current_burden']:.1f}%")
    print(f"  Mean Burden: {analysis['mean_burden']:.1f}%")
    print(f"  Maximum Burden: {analysis['max_burden']:.1f}%")
    print(f"  Trend Direction: {analysis['trend']['direction'].title()}")
    print(f"  Classification: {analysis['classification']['type'].title()} ({analysis['classification']['severity']})")

    recommendation = ArrhythmiaAnalyzer.get_recommendation(analysis)
    print(f"\nRecommendation: {recommendation}")

    return True


def test_pdf_report(session, patient, transmissions):
    """Test PDF report generation."""
    print("\n" + "=" * 70)
    print("Testing PDF Report Generator")
    print("=" * 70)

    # Calculate all trends
    calculator = TrendCalculator(session)
    all_trends = calculator.calculate_all_trends(patient.patient_id)

    trends_dict = {trend.variable_name: trend for trend in all_trends}

    print(f"\nGenerating PDF report with {len(trends_dict)} trends...")

    # Generate report
    generator = PDFReportGenerator()
    output_path = "test_phase4_report.pdf"

    try:
        result_path = generator.generate_report(
            patient=patient,
            transmissions=transmissions,
            trends=trends_dict,
            output_path=output_path,
            anonymize=False
        )

        print(f"SUCCESS: PDF report generated at: {result_path}")
        print(f"File size: {Path(result_path).stat().st_size / 1024:.1f} KB")
        return True

    except Exception as e:
        print(f"ERROR generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print("\nOpenPace - Phase 4 Analysis & Reports Test")
    print("=" * 70)

    # Create test data
    session, patient, transmissions = create_test_data()

    # Run tests
    results = []

    results.append(("Battery Analyzer", test_battery_analyzer(session, patient.patient_id)))
    results.append(("Impedance Analyzer", test_impedance_analyzer(session, patient.patient_id)))
    results.append(("Arrhythmia Analyzer", test_arrhythmia_analyzer(session, patient.patient_id)))
    results.append(("PDF Report Generator", test_pdf_report(session, patient, transmissions)))

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
        print("SUCCESS! All Phase 4 tests passed.")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("FAILED! Some tests did not pass.")
        print("=" * 70)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
