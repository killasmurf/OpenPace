#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Script: Settings Panel Widget

Tests the pacemaker settings panel with synthetic data.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from openpace.database.connection import init_database, get_db_session
from openpace.database.models import Patient, Transmission, Observation
from openpace.gui.widgets.settings_panel import SettingsPanel


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


def main():
    """Main test function."""
    print("\nOpenPace - Settings Panel Widget Test")
    print("=" * 70)

    # Create test data
    session, transmission = create_test_transmission_with_settings()

    # Create Qt application
    app = QApplication(sys.argv)

    # Create main window
    window = QMainWindow()
    window.setWindowTitle("OpenPace - Settings Panel Test")
    window.setGeometry(100, 100, 800, 600)

    # Create central widget
    central_widget = QWidget()
    layout = QVBoxLayout()
    central_widget.setLayout(layout)
    window.setCentralWidget(central_widget)

    # Create settings panel
    settings_panel = SettingsPanel()
    layout.addWidget(settings_panel)

    # Load test transmission
    settings_panel.load_transmission(transmission)

    # Show window
    window.show()

    print("=" * 70)
    print("Settings Panel Test Window Opened")
    print("=" * 70)
    print("\nDisplay shows:")
    print("  - Device Information (Medtronic Advisa DR MRI)")
    print("  - Bradycardia Pacing Settings (DDDR mode, rates, AV delays)")
    print("  - Sensing Configuration (sensitivities, adaptation)")
    print("  - Lead Channel Settings (amplitudes, pulse widths, polarities)")
    print("  - Advanced Features (magnet response, capture management)")
    print("\nClose the window to exit.")
    print("=" * 70)

    # Test text export
    print("\n\nEXPORTED SETTINGS (TEXT FORMAT):")
    print(settings_panel.export_settings_text())

    # Run application
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
