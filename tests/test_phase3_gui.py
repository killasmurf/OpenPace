#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Script: Phase 3 - GUI with Timeline View

Tests the PyQt6 GUI with sample data to ensure visualization works correctly.
This script imports sample data and verifies the timeline view displays properly.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from openpace.database.connection import init_database, get_db_session
from openpace.database.models import Patient, Transmission, Observation
from openpace.hl7.parser import HL7Parser
from openpace.processing.trend_calculator import TrendCalculator


def setup_test_database():
    """Set up test database with sample data."""
    print("=" * 60)
    print("Phase 3 GUI Test - Database Setup")
    print("=" * 60)

    # Initialize in-memory database
    init_database(':memory:', echo=False)
    session = get_db_session()

    # Load sample HL7 file
    sample_path = Path("tests/sample_data/medtronic_sample.hl7")

    if not sample_path.exists():
        print(f"Error: Sample file not found: {sample_path}")
        return None

    print(f"\n[1/3] Loading sample HL7 file...")
    with open(sample_path, 'r') as f:
        hl7_message = f.read()

    # Parse and import
    print("[2/3] Parsing HL7 message...")
    parser = HL7Parser(session, anonymize=False)
    transmission = parser.parse_message(hl7_message, filename=str(sample_path))

    print(f"  Patient: {transmission.patient.patient_name}")
    print(f"  Observations: {len(transmission.observations)}")

    # Calculate trends
    print("[3/3] Calculating longitudinal trends...")
    calculator = TrendCalculator(session)
    trends = calculator.calculate_all_trends(transmission.patient_id)

    print(f"  Computed {len(trends)} trends")
    for trend in trends:
        print(f"    - {trend.variable_name}: {len(trend.values)} data points")

    print("\nDatabase setup complete!")
    print("=" * 60)

    return session


def main():
    """Main test function."""
    print("\nOpenPace - Phase 3 GUI Test")
    print("This will launch the GUI with sample data.")
    print("Close the window when done testing.\n")

    # Setup database
    session = setup_test_database()

    if session is None:
        print("Failed to setup database")
        return 1

    # Launch GUI
    print("\n[GUI] Launching OpenPace GUI...")
    from PyQt6.QtWidgets import QApplication
    from openpace.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("OpenPace")

    window = MainWindow()
    window.show()

    print("[GUI] GUI launched successfully!")
    print("[GUI] You should see:")
    print("  - Timeline view with battery, impedance, and burden charts")
    print("  - Patient selector with 'John Doe'")
    print("  - Menu bar with Import Data option")
    print("\n[GUI] Close the window to exit...")

    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
