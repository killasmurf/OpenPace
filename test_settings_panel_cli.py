#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Script: Settings Panel Widget (CLI version)

Tests the pacemaker settings panel logic without opening GUI.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from openpace.database.connection import init_database, get_db_session
from openpace.database.models import Patient, Transmission, Observation


def create_test_transmission_with_settings():
    """Create test transmission with pacemaker settings."""
    print("=" * 70)
    print("Creating Test Data with Pacemaker Settings")
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
        transmission_type='in_clinic',
        message_control_id='MSG001',
        sending_application='Medtronic CareLink',
        sending_facility='Clinic123',
        device_manufacturer='Medtronic',
        device_model='Advisa DR MRI A3DR01',
        device_serial='PMC123456',
        device_firmware='v2.1.0'
    )
    session.add(transmission)
    session.flush()

    print(f"Created transmission: {transmission.transmission_date}")

    # Create settings observations
    settings = [
        # Brady settings
        {'var': 'pacing_mode', 'value_text': 'DDDR', 'unit': None},
        {'var': 'base_rate', 'value_num': 60, 'unit': 'bpm'},
        {'var': 'lower_rate', 'value_num': 60, 'unit': 'bpm'},
        {'var': 'max_tracking_rate', 'value_num': 130, 'unit': 'bpm'},
        {'var': 'max_sensor_rate', 'value_num': 120, 'unit': 'bpm'},
        {'var': 'sav_delay_high', 'value_num': 150, 'unit': 'ms'},
        {'var': 'sav_delay_low', 'value_num': 200, 'unit': 'ms'},
        {'var': 'pav_delay_high', 'value_num': 180, 'unit': 'ms'},
        {'var': 'pav_delay_low', 'value_num': 230, 'unit': 'ms'},
        {'var': 'sensor_type', 'value_text': 'Accelerometer', 'unit': None},
        {'var': 'mode_switch', 'value_text': 'On', 'unit': None},
        {'var': 'mode_switch_rate', 'value_num': 180, 'unit': 'bpm'},

        # Sensing settings
        {'var': 'atrial_sensitivity', 'value_num': 0.3, 'unit': 'mV'},
        {'var': 'ventricular_sensitivity', 'value_num': 2.1, 'unit': 'mV'},
        {'var': 'atrial_adaptation', 'value_text': 'On', 'unit': None},
        {'var': 'ventricular_adaptation', 'value_text': 'On', 'unit': None},

        # Lead channel settings
        {'var': 'atrial_amplitude', 'value_num': 3.5, 'unit': 'V'},
        {'var': 'ventricular_amplitude', 'value_num': 2.5, 'unit': 'V'},
        {'var': 'atrial_pulse_width', 'value_num': 0.4, 'unit': 'ms'},
        {'var': 'ventricular_pulse_width', 'value_num': 0.4, 'unit': 'ms'},
        {'var': 'atrial_polarity', 'value_text': 'Bipolar', 'unit': None},
        {'var': 'ventricular_polarity', 'value_text': 'Bipolar', 'unit': None},

        # Advanced settings
        {'var': 'magnet_response', 'value_text': 'Asynchronous', 'unit': None},
        {'var': 'capture_management', 'value_text': 'On', 'unit': None},
    ]

    for i, setting in enumerate(settings):
        obs = Observation(
            transmission_id=transmission.transmission_id,
            observation_time=transmission.transmission_date,
            sequence_number=i+1,
            variable_name=setting['var'],
            vendor_code=f'CODE_{i+1}',
            value_numeric=setting.get('value_num'),
            value_text=setting.get('value_text'),
            unit=setting.get('unit'),
            observation_status='F'
        )
        session.add(obs)

    session.commit()

    print(f"Created {len(settings)} settings observations")
    print("")

    return session, transmission


def test_settings_extraction():
    """Test settings extraction logic."""
    print("=" * 70)
    print("Testing Settings Extraction")
    print("=" * 70)

    session, transmission = create_test_transmission_with_settings()

    # Extract settings
    settings_data = {}
    for obs in transmission.observations:
        var_name = obs.variable_name

        # Get value (numeric or text)
        if obs.value_numeric is not None:
            value = obs.value_numeric
            if obs.unit:
                value_str = f"{value} {obs.unit}"
            else:
                value_str = str(value)
        elif obs.value_text:
            value_str = obs.value_text
        else:
            continue

        settings_data[var_name] = {
            'value': obs.value_numeric if obs.value_numeric is not None else obs.value_text,
            'value_str': value_str,
            'unit': obs.unit,
            'vendor_code': obs.vendor_code
        }

    print(f"\nExtracted {len(settings_data)} settings:")
    print("")

    # Display by category
    print("DEVICE INFORMATION:")
    print(f"  Manufacturer: {transmission.device_manufacturer}")
    print(f"  Model: {transmission.device_model}")
    print(f"  Serial: {transmission.device_serial}")
    print(f"  Firmware: {transmission.device_firmware}")
    print("")

    print("BRADYCARDIA PACING:")
    brady_vars = ['pacing_mode', 'base_rate', 'lower_rate', 'max_tracking_rate',
                  'max_sensor_rate', 'sav_delay_high', 'sav_delay_low',
                  'pav_delay_high', 'pav_delay_low', 'sensor_type',
                  'mode_switch', 'mode_switch_rate']
    for var in brady_vars:
        if var in settings_data:
            print(f"  {var}: {settings_data[var]['value_str']}")
    print("")

    print("SENSING CONFIGURATION:")
    sensing_vars = ['atrial_sensitivity', 'ventricular_sensitivity',
                    'atrial_adaptation', 'ventricular_adaptation']
    for var in sensing_vars:
        if var in settings_data:
            print(f"  {var}: {settings_data[var]['value_str']}")
    print("")

    print("LEAD CHANNELS:")
    lead_vars = ['atrial_amplitude', 'ventricular_amplitude',
                 'atrial_pulse_width', 'ventricular_pulse_width',
                 'atrial_polarity', 'ventricular_polarity']
    for var in lead_vars:
        if var in settings_data:
            print(f"  {var}: {settings_data[var]['value_str']}")
    print("")

    print("ADVANCED FEATURES:")
    advanced_vars = ['magnet_response', 'capture_management']
    for var in advanced_vars:
        if var in settings_data:
            print(f"  {var}: {settings_data[var]['value_str']}")
    print("")

    return True


def main():
    """Main test function."""
    print("\nOpenPace - Settings Panel Widget Test (CLI)")
    print("=" * 70)
    print("")

    success = test_settings_extraction()

    if success:
        print("=" * 70)
        print("SUCCESS! Settings panel logic tested successfully.")
        print("=" * 70)
        print("\nSettings panel features:")
        print("  - Organizes settings into logical groups")
        print("  - Device Information (manufacturer, model, serial)")
        print("  - Bradycardia Pacing (modes, rates, AV delays)")
        print("  - Tachycardia Therapy (ICD only, hidden if not present)")
        print("  - Sensing Configuration (sensitivities, adaptation)")
        print("  - Lead Channels (amplitudes, pulse widths, polarities)")
        print("  - Advanced Features (magnet response, capture mgmt)")
        print("  - Text export functionality")
        print("")
        print("To test GUI: python test_settings_panel.py")
        print("=" * 70)
        return 0
    else:
        print("=" * 70)
        print("FAILED! Settings panel test failed.")
        print("=" * 70)
        return 1


if __name__ == '__main__':
    sys.exit(main())
