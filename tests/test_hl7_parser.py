"""
Unit tests for HL7 Parser

Tests the parsing of HL7 ORU^R01 messages.
"""

import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openpace.database.models import Base, Patient, Transmission, Observation
from openpace.hl7.parser import HL7Parser


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_hl7_medtronic():
    """Load Medtronic sample HL7 message."""
    sample_path = Path(__file__).parent / 'sample_data' / 'medtronic_sample.hl7'
    with open(sample_path, 'r') as f:
        return f.read()


@pytest.fixture
def sample_hl7_generic():
    """Load generic LOINC sample HL7 message."""
    sample_path = Path(__file__).parent / 'sample_data' / 'generic_loinc_sample.hl7'
    with open(sample_path, 'r') as f:
        return f.read()


def test_parse_medtronic_message(db_session, sample_hl7_medtronic):
    """Test parsing of Medtronic CareLink message."""
    parser = HL7Parser(db_session, anonymize=False)
    transmission = parser.parse_message(sample_hl7_medtronic, filename="medtronic_sample.hl7")

    assert transmission is not None
    assert transmission.transmission_id is not None
    assert transmission.device_manufacturer == 'Medtronic'
    assert transmission.transmission_type == 'remote'

    # Check patient was created
    patient = db_session.query(Patient).filter_by(patient_id='P123456').first()
    assert patient is not None
    assert patient.patient_name == 'John Doe'
    assert patient.gender == 'M'

    # Check observations were created
    observations = db_session.query(Observation).filter_by(
        transmission_id=transmission.transmission_id
    ).all()

    assert len(observations) > 0

    # Check specific observations
    battery_obs = [o for o in observations if o.variable_name == 'battery_voltage']
    assert len(battery_obs) == 1
    assert battery_obs[0].value_numeric == 2.65
    assert battery_obs[0].unit == 'V'

    impedance_obs = [o for o in observations if o.variable_name == 'lead_impedance_atrial']
    assert len(impedance_obs) == 1
    assert impedance_obs[0].value_numeric == 625
    assert impedance_obs[0].unit == 'Ohm'

    afib_obs = [o for o in observations if o.variable_name == 'afib_burden_percent']
    assert len(afib_obs) == 1
    assert afib_obs[0].value_numeric == 12.5
    assert afib_obs[0].abnormal_flag == 'H'  # High


def test_parse_generic_message(db_session, sample_hl7_generic):
    """Test parsing of generic LOINC message."""
    parser = HL7Parser(db_session, anonymize=False)
    transmission = parser.parse_message(sample_hl7_generic, filename="generic_sample.hl7")

    assert transmission is not None
    assert transmission.device_manufacturer == 'Generic'
    assert transmission.transmission_type == 'in_clinic'

    # Check observations
    observations = db_session.query(Observation).filter_by(
        transmission_id=transmission.transmission_id
    ).all()

    assert len(observations) > 0

    # Verify LOINC codes mapped correctly
    pacing_obs = [o for o in observations if o.variable_name == 'pacing_percent_ventricular']
    assert len(pacing_obs) == 1
    assert pacing_obs[0].value_numeric == 92.3
    assert pacing_obs[0].loinc_code == '8897-1'


def test_anonymization_mode(db_session, sample_hl7_medtronic):
    """Test that anonymization mode strips PII."""
    parser = HL7Parser(db_session, anonymize=True)
    transmission = parser.parse_message(sample_hl7_medtronic)

    patient = db_session.query(Patient).first()
    assert patient is not None
    assert patient.anonymized == True
    assert patient.patient_name is None
    assert patient.date_of_birth is None
    assert patient.anonymized_id is not None
    assert patient.anonymized_id.startswith('Patient_')


def test_multiple_transmissions_same_patient(db_session, sample_hl7_medtronic):
    """Test that multiple transmissions link to the same patient."""
    parser = HL7Parser(db_session, anonymize=False)

    # Parse same message twice
    trans1 = parser.parse_message(sample_hl7_medtronic, filename="msg1.hl7")
    trans2 = parser.parse_message(sample_hl7_medtronic, filename="msg2.hl7")

    # Should have only one patient
    patient_count = db_session.query(Patient).count()
    assert patient_count == 1

    # But two transmissions
    transmission_count = db_session.query(Transmission).count()
    assert transmission_count == 2

    # Both linked to same patient
    assert trans1.patient_id == trans2.patient_id


def test_invalid_hl7_message(db_session):
    """Test handling of invalid HL7 message."""
    parser = HL7Parser(db_session)

    with pytest.raises(ValueError):
        parser.parse_message("This is not a valid HL7 message")


def test_wrong_message_type(db_session):
    """Test handling of non-ORU message type."""
    # ADT message (patient administration)
    adt_message = "MSH|^~\&|APP|FACILITY|||20240116||ADT^A01|MSG001|P|2.5"

    parser = HL7Parser(db_session)

    with pytest.raises(ValueError, match="Expected ORU"):
        parser.parse_message(adt_message)
