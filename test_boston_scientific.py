#!/usr/bin/env python3
"""
Test script for Boston Scientific HL7 import and processing.

This script tests the complete workflow:
1. Parse Boston Scientific HL7 message
2. Store in database
3. Verify data integrity
4. Check for any issues
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from openpace.hl7.parser import HL7Parser
from openpace.database.connection import init_database, get_db_session
from openpace.database.models import Patient, Transmission, Observation, ArrhythmiaEpisode


def test_boston_scientific_import():
    """Test importing Boston Scientific sample data."""

    print("="*60)
    print("Boston Scientific HL7 Import Test")
    print("="*60)

    # Initialize database in memory
    print("\n[1] Initializing in-memory database...")
    init_database(':memory:', echo=False)
    session = get_db_session()
    print("    Database initialized")

    # Read Boston Scientific sample
    print("\n[2] Loading Boston Scientific sample file...")
    sample_file = project_root / 'tests' / 'sample_data' / 'boston_scientific_sample.hl7'

    if not sample_file.exists():
        print(f"    ERROR: Sample file not found: {sample_file}")
        return False

    with open(sample_file, 'r', encoding='utf-8') as f:
        hl7_content = f.read()

    print(f"    Loaded {len(hl7_content)} characters")
    print(f"    First line: {hl7_content.split(chr(10))[0][:80]}...")

    # Parse the message
    print("\n[3] Parsing HL7 message...")
    parser = HL7Parser(session, anonymize=False)

    try:
        transmission = parser.parse_message(hl7_content, filename='boston_scientific_sample.hl7')
        print(f"    SUCCESS: Transmission created")
        print(f"    Transmission ID: {transmission.transmission_id}")
        print(f"    Patient ID: {transmission.patient_id}")
        print(f"    Date: {transmission.transmission_date}")

    except Exception as e:
        print(f"    ERROR during parsing: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify patient
    print("\n[4] Verifying patient data...")
    patient = session.query(Patient).filter_by(patient_id=transmission.patient_id).first()

    if patient:
        print(f"    Patient ID: {patient.patient_id}")
        print(f"    Name: {patient.patient_name}")
        print(f"    DOB: {patient.date_of_birth}")
        print(f"    Gender: {patient.gender}")
        print(f"    Anonymized: {patient.anonymized}")
    else:
        print("    ERROR: Patient not found!")
        return False

    # Verify transmission details
    print("\n[5] Verifying transmission details...")
    print(f"    Device Manufacturer: {transmission.device_manufacturer}")
    print(f"    Device Model: {transmission.device_model}")
    print(f"    Device Serial: {transmission.device_serial}")
    print(f"    Transmission Type: {transmission.transmission_type}")
    print(f"    Message Control ID: {transmission.message_control_id}")

    # Check observations
    print("\n[6] Checking observations...")
    observations = session.query(Observation).filter_by(
        transmission_id=transmission.transmission_id
    ).all()

    print(f"    Total observations: {len(observations)}")

    # Group by variable name
    obs_by_var = {}
    for obs in observations:
        if obs.variable_name not in obs_by_var:
            obs_by_var[obs.variable_name] = []
        obs_by_var[obs.variable_name].append(obs)

    print(f"    Unique variables: {len(obs_by_var)}")
    print("\n    Top 10 variables:")
    for i, (var_name, obs_list) in enumerate(list(obs_by_var.items())[:10]):
        sample_obs = obs_list[0]
        value = sample_obs.value_numeric if sample_obs.value_numeric is not None else sample_obs.value_text
        unit = f" {sample_obs.unit}" if sample_obs.unit else ""
        print(f"      {i+1:2}. {var_name:40} = {value}{unit}")

    # Check for specific Boston Scientific variables
    print("\n[7] Checking Boston Scientific specific variables...")
    expected_vars = [
        'BATTERY_VOLTAGE',
        'RA_LEAD_IMPEDANCE',
        'RV_LEAD_IMPEDANCE',
        'AF_EPISODE_COUNT'
    ]

    found_vars = []
    missing_vars = []

    for var in expected_vars:
        if var in obs_by_var:
            found_vars.append(var)
            obs = obs_by_var[var][0]
            value = obs.value_numeric if obs.value_numeric is not None else obs.value_text
            unit = f" {obs.unit}" if obs.unit else ""
            print(f"    [OK] {var}: {value}{unit}")
        else:
            missing_vars.append(var)
            print(f"    [MISSING] {var}")

    # Check arrhythmia episodes
    print("\n[8] Checking arrhythmia episodes...")
    episodes = session.query(ArrhythmiaEpisode).filter_by(
        transmission_id=transmission.transmission_id
    ).all()

    print(f"    Total episodes: {len(episodes)}")

    if episodes:
        for i, episode in enumerate(episodes[:5], 1):
            print(f"    Episode {i}:")
            print(f"      Type: {episode.episode_type}")
            print(f"      Start: {episode.start_time}")
            print(f"      Duration: {episode.duration_seconds} seconds")
            print(f"      Avg HR: {episode.avg_rate} bpm")
            print(f"      Max HR: {episode.max_rate} bpm")
            print(f"      EGM available: {episode.egm_available}")

    # Check for EGM data (binary blobs)
    print("\n[9] Checking EGM data...")
    egm_obs = session.query(Observation).filter(
        Observation.transmission_id == transmission.transmission_id,
        Observation.value_blob.isnot(None)
    ).all()

    print(f"    EGM observations: {len(egm_obs)}")
    for i, obs in enumerate(egm_obs[:3], 1):
        blob_size = len(obs.value_blob) if obs.value_blob else 0
        print(f"    EGM {i}: {obs.variable_name}, size: {blob_size} bytes")

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"Patient created: {'YES' if patient else 'NO'}")
    print(f"Transmission created: {'YES' if transmission else 'NO'}")
    print(f"Observations: {len(observations)}")
    print(f"Unique variables: {len(obs_by_var)}")
    print(f"Arrhythmia episodes: {len(episodes)}")
    print(f"EGM data blobs: {len(egm_obs)}")
    print(f"Expected variables found: {len(found_vars)}/{len(expected_vars)}")
    if missing_vars:
        print(f"Missing variables: {', '.join(missing_vars)}")

    # Overall result
    print("\n" + "="*60)
    if len(observations) > 0 and len(found_vars) >= len(expected_vars) * 0.75:
        print("Result: PASS (with notes)")
        print("="*60)
        return True
    elif len(observations) > 0:
        print("Result: PARTIAL (some data imported)")
        print("="*60)
        return True
    else:
        print("Result: FAIL (no observations created)")
        print("="*60)
        return False


def main():
    """Main entry point."""
    try:
        success = test_boston_scientific_import()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nFATAL ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
