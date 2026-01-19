#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Script: HL7 Import to Database

Quick test to verify HL7 parsing and database storage works end-to-end.
"""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from openpace.database.connection import init_database, get_db_session
from openpace.database.models import Patient, Transmission, Observation
from openpace.hl7.parser import HL7Parser


def main():
    print("=" * 60)
    print("OpenPace - HL7 Import Test")
    print("=" * 60)

    # Initialize database (in-memory for testing)
    print("\n[1/5] Initializing database...")
    init_database(':memory:', echo=False)
    session = get_db_session()
    print("✓ Database initialized")

    # Load sample HL7 file
    print("\n[2/5] Loading sample HL7 file...")
    sample_path = Path("tests/sample_data/medtronic_sample.hl7")
    
    if not sample_path.exists():
        print(f"✗ Sample file not found: {sample_path}")
        return 1
    
    with open(sample_path, 'r') as f:
        hl7_message = f.read()
    
    print(f"✓ Loaded {len(hl7_message)} bytes from {sample_path.name}")

    # Parse HL7 message
    print("\n[3/5] Parsing HL7 message...")
    parser = HL7Parser(session, anonymize=False)
    
    try:
        transmission = parser.parse_message(hl7_message, filename=str(sample_path))
        print(f"✓ Transmission {transmission.transmission_id} created")
    except Exception as e:
        print(f"✗ Parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Query database
    print("\n[4/5] Querying database...")
    
    patients = session.query(Patient).all()
    transmissions = session.query(Transmission).all()
    observations = session.query(Observation).all()
    
    print(f"✓ Found {len(patients)} patient(s)")
    print(f"✓ Found {len(transmissions)} transmission(s)")
    print(f"✓ Found {len(observations)} observation(s)")

    # Display results
    print("\n[5/5] Displaying results...")
    print("\n" + "-" * 60)
    print("PATIENTS:")
    print("-" * 60)
    for patient in patients:
        print(f"  ID: {patient.patient_id}")
        print(f"  Name: {patient.patient_name}")
        print(f"  DOB: {patient.date_of_birth}")
        print(f"  Gender: {patient.gender}")
    
    print("\n" + "-" * 60)
    print("TRANSMISSIONS:")
    print("-" * 60)
    for trans in transmissions:
        print(f"  ID: {trans.transmission_id}")
        print(f"  Date: {trans.transmission_date}")
        print(f"  Manufacturer: {trans.device_manufacturer}")
        print(f"  Type: {trans.transmission_type}")
        print(f"  Observations: {len(trans.observations)}")
    
    print("\n" + "-" * 60)
    print("OBSERVATIONS (Sample):")
    print("-" * 60)
    for obs in observations[:10]:  # Show first 10
        value = obs.value_numeric if obs.value_numeric is not None else obs.value_text
        print(f"  {obs.variable_name}: {value} {obs.unit or ''}")
    
    if len(observations) > 10:
        print(f"  ... and {len(observations) - 10} more observations")

    print("\n" + "=" * 60)
    print("✓ End-to-end test PASSED!")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
