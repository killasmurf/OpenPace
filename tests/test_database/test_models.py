"""
Test suite for OpenPace database models.

Tests cover:
- Model creation and validation
- Relationships and foreign keys
- Cascade deletes
- JSON field handling
- Index creation
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from openpace.database.models import (
    Analysis,
    ArrhythmiaEpisode,
    DeviceParameter,
    LongitudinalTrend,
    Observation,
    Patient,
    Transmission,
)


class TestPatientModel:
    """Test suite for Patient model."""

    def test_create_patient_basic(self, db_session):
        """Test creating a basic patient record."""
        patient = Patient(
            patient_id="TEST001",
            last_name_hash="DOE",
            first_name_hash="JOHN",
            date_of_birth_offset=0,
            anonymized=False
        )
        db_session.add(patient)
        db_session.commit()

        assert patient.id is not None
        assert patient.patient_id == "TEST001"
        assert patient.last_name_hash == "DOE"
        assert patient.anonymized is False

    def test_create_patient_with_notes(self, db_session):
        """Test creating a patient with notes."""
        patient = Patient(
            patient_id="TEST002",
            last_name_hash="SMITH",
            first_name_hash="JANE",
            date_of_birth_offset=0,
            anonymized=False,
            notes="Test patient with notes"
        )
        db_session.add(patient)
        db_session.commit()

        assert patient.notes == "Test patient with notes"

    def test_patient_unique_constraint(self, db_session):
        """Test that patient_id must be unique."""
        patient1 = Patient(
            patient_id="TEST001",
            last_name_hash="DOE",
            first_name_hash="JOHN",
            date_of_birth_offset=0
        )
        patient2 = Patient(
            patient_id="TEST001",
            last_name_hash="SMITH",
            first_name_hash="JANE",
            date_of_birth_offset=0
        )

        db_session.add(patient1)
        db_session.commit()

        db_session.add(patient2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_patient_anonymization_flag(self, db_session):
        """Test anonymization flag functionality."""
        patient = Patient(
            patient_id="TEST003",
            last_name_hash="ANON",
            first_name_hash="PATIENT",
            date_of_birth_offset=30,
            anonymized=True
        )
        db_session.add(patient)
        db_session.commit()

        assert patient.anonymized is True
        assert patient.date_of_birth_offset == 30

    def test_patient_cascade_delete(self, db_session):
        """Test that deleting patient cascades to related records."""
        patient = Patient(
            patient_id="TEST004",
            last_name_hash="CASCADE",
            first_name_hash="TEST",
            date_of_birth_offset=0
        )
        db_session.add(patient)
        db_session.commit()

        transmission = Transmission(
            patient_id=patient.id,
            transmission_date=datetime.now(),
            device_model="TEST_DEVICE",
            device_serial="TEST123",
            raw_hl7="TEST"
        )
        db_session.add(transmission)
        db_session.commit()

        transmission_id = transmission.id

        # Delete patient
        db_session.delete(patient)
        db_session.commit()

        # Verify transmission is also deleted
        assert db_session.query(Transmission).filter_by(id=transmission_id).first() is None


class TestTransmissionModel:
    """Test suite for Transmission model."""

    def test_create_transmission(self, db_session, sample_patient_data):
        """Test creating a transmission record."""
        patient = Patient(**sample_patient_data)
        db_session.add(patient)
        db_session.commit()

        transmission = Transmission(
            patient_id=patient.id,
            transmission_date=datetime(2024, 1, 15, 12, 0, 0),
            device_model="ADVISA DR MRI A3DR01",
            device_serial="PMC123456",
            raw_hl7="MSH|...|",
            import_source="test_file.hl7"
        )
        db_session.add(transmission)
        db_session.commit()

        assert transmission.id is not None
        assert transmission.patient_id == patient.id
        assert transmission.device_model == "ADVISA DR MRI A3DR01"
        assert transmission.device_serial == "PMC123456"

    def test_transmission_patient_relationship(self, db_session):
        """Test relationship between Transmission and Patient."""
        patient = Patient(
            patient_id="TEST005",
            last_name_hash="REL",
            first_name_hash="TEST",
            date_of_birth_offset=0
        )
        db_session.add(patient)
        db_session.commit()

        transmission = Transmission(
            patient_id=patient.id,
            transmission_date=datetime.now(),
            device_model="TEST",
            device_serial="123",
            raw_hl7="TEST"
        )
        db_session.add(transmission)
        db_session.commit()

        # Test relationship access
        assert transmission.patient == patient
        assert transmission in patient.transmissions

    def test_transmission_requires_patient(self, db_session):
        """Test that transmission requires a valid patient_id."""
        transmission = Transmission(
            patient_id=99999,  # Non-existent patient
            transmission_date=datetime.now(),
            device_model="TEST",
            device_serial="123",
            raw_hl7="TEST"
        )
        db_session.add(transmission)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_transmission_metadata_json(self, db_session):
        """Test JSON metadata field."""
        patient = Patient(
            patient_id="TEST006",
            last_name_hash="JSON",
            first_name_hash="TEST",
            date_of_birth_offset=0
        )
        db_session.add(patient)
        db_session.commit()

        metadata = {
            "vendor": "Medtronic",
            "clinic": "Test Clinic",
            "technician": "Test Tech"
        }

        transmission = Transmission(
            patient_id=patient.id,
            transmission_date=datetime.now(),
            device_model="TEST",
            device_serial="123",
            raw_hl7="TEST",
            metadata=metadata
        )
        db_session.add(transmission)
        db_session.commit()

        # Retrieve and verify JSON
        retrieved = db_session.query(Transmission).filter_by(id=transmission.id).first()
        assert retrieved.metadata == metadata
        assert retrieved.metadata["vendor"] == "Medtronic"


class TestObservationModel:
    """Test suite for Observation model."""

    def test_create_observation_numeric(self, db_session):
        """Test creating a numeric observation."""
        patient = Patient(
            patient_id="TEST007",
            last_name_hash="OBS",
            first_name_hash="TEST",
            date_of_birth_offset=0
        )
        db_session.add(patient)
        db_session.commit()

        transmission = Transmission(
            patient_id=patient.id,
            transmission_date=datetime.now(),
            device_model="TEST",
            device_serial="123",
            raw_hl7="TEST"
        )
        db_session.add(transmission)
        db_session.commit()

        observation = Observation(
            transmission_id=transmission.id,
            observation_id="OBX001",
            variable_name="BATTERY_VOLTAGE",
            variable_code="BATTERY_VOLTAGE",
            value_string="2.78",
            value_numeric=2.78,
            units="V",
            reference_range="2.5-2.8",
            observation_timestamp=datetime.now()
        )
        db_session.add(observation)
        db_session.commit()

        assert observation.id is not None
        assert observation.value_numeric == 2.78
        assert observation.units == "V"

    def test_create_observation_string(self, db_session):
        """Test creating a string observation."""
        patient = Patient(
            patient_id="TEST008",
            last_name_hash="STR",
            first_name_hash="OBS",
            date_of_birth_offset=0
        )
        db_session.add(patient)
        db_session.commit()

        transmission = Transmission(
            patient_id=patient.id,
            transmission_date=datetime.now(),
            device_model="TEST",
            device_serial="123",
            raw_hl7="TEST"
        )
        db_session.add(transmission)
        db_session.commit()

        observation = Observation(
            transmission_id=transmission.id,
            observation_id="OBX002",
            variable_name="PACING_MODE",
            variable_code="MODE",
            value_string="DDDR",
            observation_timestamp=datetime.now()
        )
        db_session.add(observation)
        db_session.commit()

        assert observation.value_string == "DDDR"
        assert observation.value_numeric is None

    def test_observation_egm_data(self, db_session):
        """Test observation with EGM binary data."""
        patient = Patient(
            patient_id="TEST009",
            last_name_hash="EGM",
            first_name_hash="TEST",
            date_of_birth_offset=0
        )
        db_session.add(patient)
        db_session.commit()

        transmission = Transmission(
            patient_id=patient.id,
            transmission_date=datetime.now(),
            device_model="TEST",
            device_serial="123",
            raw_hl7="TEST"
        )
        db_session.add(transmission)
        db_session.commit()

        egm_data = b"Binary EGM data sample"
        observation = Observation(
            transmission_id=transmission.id,
            observation_id="OBX003",
            variable_name="EGM_STRIP",
            variable_code="EGM",
            value_string="BASE64_ENCODED",
            egm_data=egm_data,
            observation_timestamp=datetime.now()
        )
        db_session.add(observation)
        db_session.commit()

        retrieved = db_session.query(Observation).filter_by(id=observation.id).first()
        assert retrieved.egm_data == egm_data


class TestLongitudinalTrendModel:
    """Test suite for LongitudinalTrend model."""

    def test_create_longitudinal_trend(self, db_session):
        """Test creating longitudinal trend data."""
        patient = Patient(
            patient_id="TEST010",
            last_name_hash="TREND",
            first_name_hash="TEST",
            date_of_birth_offset=0
        )
        db_session.add(patient)
        db_session.commit()

        trend = LongitudinalTrend(
            patient_id=patient.id,
            variable_name="BATTERY_VOLTAGE",
            timestamp=datetime.now(),
            value_numeric=2.78,
            units="V"
        )
        db_session.add(trend)
        db_session.commit()

        assert trend.id is not None
        assert trend.variable_name == "BATTERY_VOLTAGE"
        assert trend.value_numeric == 2.78

    def test_longitudinal_trend_series(self, db_session):
        """Test creating a series of trend data points."""
        patient = Patient(
            patient_id="TEST011",
            last_name_hash="SERIES",
            first_name_hash="TEST",
            date_of_birth_offset=0
        )
        db_session.add(patient)
        db_session.commit()

        # Create multiple data points
        base_date = datetime(2024, 1, 1)
        for i in range(5):
            trend = LongitudinalTrend(
                patient_id=patient.id,
                variable_name="BATTERY_VOLTAGE",
                timestamp=base_date + timedelta(days=i * 30),
                value_numeric=2.80 - (i * 0.01),
                units="V"
            )
            db_session.add(trend)
        db_session.commit()

        # Query trends
        trends = db_session.query(LongitudinalTrend).filter_by(
            patient_id=patient.id
        ).order_by(LongitudinalTrend.timestamp).all()

        assert len(trends) == 5
        assert trends[0].value_numeric == 2.80
        assert trends[4].value_numeric == 2.76


class TestArrhythmiaEpisodeModel:
    """Test suite for ArrhythmiaEpisode model."""

    def test_create_arrhythmia_episode(self, db_session):
        """Test creating an arrhythmia episode."""
        patient = Patient(
            patient_id="TEST012",
            last_name_hash="ARRHYTHMIA",
            first_name_hash="TEST",
            date_of_birth_offset=0
        )
        db_session.add(patient)
        db_session.commit()

        transmission = Transmission(
            patient_id=patient.id,
            transmission_date=datetime.now(),
            device_model="TEST",
            device_serial="123",
            raw_hl7="TEST"
        )
        db_session.add(transmission)
        db_session.commit()

        episode = ArrhythmiaEpisode(
            transmission_id=transmission.id,
            episode_type="AF",
            start_timestamp=datetime(2024, 1, 10, 8, 30, 0),
            duration_seconds=320,
            average_hr=145,
            max_hr=160
        )
        db_session.add(episode)
        db_session.commit()

        assert episode.id is not None
        assert episode.episode_type == "AF"
        assert episode.duration_seconds == 320
        assert episode.average_hr == 145

    def test_arrhythmia_episode_with_egm(self, db_session):
        """Test arrhythmia episode with associated EGM data."""
        patient = Patient(
            patient_id="TEST013",
            last_name_hash="EGM_EPISODE",
            first_name_hash="TEST",
            date_of_birth_offset=0
        )
        db_session.add(patient)
        db_session.commit()

        transmission = Transmission(
            patient_id=patient.id,
            transmission_date=datetime.now(),
            device_model="TEST",
            device_serial="123",
            raw_hl7="TEST"
        )
        db_session.add(transmission)
        db_session.commit()

        egm_data = b"AF episode EGM binary data"
        episode = ArrhythmiaEpisode(
            transmission_id=transmission.id,
            episode_type="AF",
            start_timestamp=datetime.now(),
            duration_seconds=1800,
            average_hr=138,
            egm_strip=egm_data
        )
        db_session.add(episode)
        db_session.commit()

        retrieved = db_session.query(ArrhythmiaEpisode).filter_by(id=episode.id).first()
        assert retrieved.egm_strip == egm_data


class TestDeviceParameterModel:
    """Test suite for DeviceParameter model."""

    def test_create_device_parameter(self, db_session):
        """Test creating device parameter record."""
        patient = Patient(
            patient_id="TEST014",
            last_name_hash="PARAM",
            first_name_hash="TEST",
            date_of_birth_offset=0
        )
        db_session.add(patient)
        db_session.commit()

        transmission = Transmission(
            patient_id=patient.id,
            transmission_date=datetime.now(),
            device_model="TEST",
            device_serial="123",
            raw_hl7="TEST"
        )
        db_session.add(transmission)
        db_session.commit()

        param = DeviceParameter(
            transmission_id=transmission.id,
            parameter_name="LOWER_RATE_LIMIT",
            parameter_value="60",
            units="bpm"
        )
        db_session.add(param)
        db_session.commit()

        assert param.id is not None
        assert param.parameter_name == "LOWER_RATE_LIMIT"
        assert param.parameter_value == "60"
        assert param.units == "bpm"


class TestAnalysisModel:
    """Test suite for Analysis model."""

    def test_create_analysis(self, db_session):
        """Test creating analysis record."""
        patient = Patient(
            patient_id="TEST015",
            last_name_hash="ANALYSIS",
            first_name_hash="TEST",
            date_of_birth_offset=0
        )
        db_session.add(patient)
        db_session.commit()

        analysis_results = {
            "battery_trend": "declining",
            "estimated_replacement_date": "2024-12-01",
            "lead_status": "normal"
        }

        analysis = Analysis(
            patient_id=patient.id,
            analysis_type="BATTERY_TREND",
            analysis_timestamp=datetime.now(),
            results=analysis_results
        )
        db_session.add(analysis)
        db_session.commit()

        assert analysis.id is not None
        assert analysis.analysis_type == "BATTERY_TREND"
        assert analysis.results["battery_trend"] == "declining"

    def test_analysis_version_tracking(self, db_session):
        """Test analysis version tracking."""
        patient = Patient(
            patient_id="TEST016",
            last_name_hash="VERSION",
            first_name_hash="TEST",
            date_of_birth_offset=0
        )
        db_session.add(patient)
        db_session.commit()

        analysis = Analysis(
            patient_id=patient.id,
            analysis_type="AF_BURDEN",
            analysis_timestamp=datetime.now(),
            results={"burden": 2.3},
            algorithm_version="1.0.0"
        )
        db_session.add(analysis)
        db_session.commit()

        assert analysis.algorithm_version == "1.0.0"
