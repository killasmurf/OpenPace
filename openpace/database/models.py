"""
Database Models for OpenPace

SQLAlchemy ORM models for storing pacemaker data from HL7 messages.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Date,
    Text,
    LargeBinary,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Patient(Base):
    """
    Patient information from HL7 PID segment.

    Supports anonymization mode where real names/DOB are stripped.
    """

    __tablename__ = "patients"

    patient_id = Column(String(100), primary_key=True)
    anonymized = Column(Boolean, default=False, nullable=False)
    anonymized_id = Column(String(50), nullable=True)  # e.g., "Patient_001"

    # Demographics (may be null in anonymized mode)
    patient_name = Column(String(200), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(1), nullable=True)  # M, F, O, U

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    transmissions = relationship("Transmission", back_populates="patient", cascade="all, delete-orphan")

    def __repr__(self):
        display_name = self.anonymized_id if self.anonymized else self.patient_name
        return f"<Patient(id={self.patient_id}, name={display_name})>"


class Transmission(Base):
    """
    A single HL7 ORU^R01 message transmission.

    Represents one remote monitoring report or in-clinic interrogation.
    """

    __tablename__ = "transmissions"

    transmission_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(100), ForeignKey("patients.patient_id"), nullable=False)

    # Transmission metadata (from MSH segment)
    transmission_date = Column(DateTime, nullable=False)
    transmission_type = Column(String(50), nullable=True)  # "remote" or "in_clinic"
    message_control_id = Column(String(100), nullable=True)
    sending_application = Column(String(100), nullable=True)
    sending_facility = Column(String(100), nullable=True)

    # Device information (from OBR or OBX segments)
    device_manufacturer = Column(String(100), nullable=True)
    device_model = Column(String(100), nullable=True)
    device_serial = Column(String(100), nullable=True)
    device_firmware = Column(String(50), nullable=True)

    # Import metadata
    hl7_filename = Column(String(500), nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="transmissions")
    observations = relationship("Observation", back_populates="transmission", cascade="all, delete-orphan")
    episodes = relationship("ArrhythmiaEpisode", back_populates="transmission", cascade="all, delete-orphan")

    # Indexes for performance
    __table_args__ = (
        Index("idx_transmission_patient_date", "patient_id", "transmission_date"),
    )

    def __repr__(self):
        return f"<Transmission(id={self.transmission_id}, patient={self.patient_id}, date={self.transmission_date})>"


class Observation(Base):
    """
    Individual observation from HL7 OBX segment.

    Stores both raw vendor codes and normalized universal variables.
    """

    __tablename__ = "observations"

    observation_id = Column(Integer, primary_key=True, autoincrement=True)
    transmission_id = Column(Integer, ForeignKey("transmissions.transmission_id"), nullable=False)

    # Observation metadata
    observation_time = Column(DateTime, nullable=False)
    sequence_number = Column(Integer, nullable=True)  # OBX sequence in message

    # Variable identification
    variable_name = Column(String(100), nullable=False)  # Universal variable (e.g., "battery_voltage")
    loinc_code = Column(String(20), nullable=True)
    vendor_code = Column(String(100), nullable=True)  # Original vendor-specific code

    # Value (one of these will be populated based on data type)
    value_numeric = Column(Float, nullable=True)
    value_text = Column(Text, nullable=True)
    value_blob = Column(LargeBinary, nullable=True)  # For base64-decoded EGM data

    # Metadata
    unit = Column(String(50), nullable=True)
    reference_range = Column(String(100), nullable=True)
    abnormal_flag = Column(String(10), nullable=True)  # N (normal), H (high), L (low), etc.
    observation_status = Column(String(1), nullable=True)  # F (final), P (preliminary), etc.

    # Relationships
    transmission = relationship("Transmission", back_populates="observations")

    # Indexes for performance
    __table_args__ = (
        Index("idx_observation_variable", "variable_name"),
        Index("idx_observation_time", "observation_time"),
        Index("idx_observation_transmission", "transmission_id"),
    )

    def __repr__(self):
        value = self.value_numeric if self.value_numeric is not None else self.value_text
        return f"<Observation(id={self.observation_id}, var={self.variable_name}, value={value})>"


class LongitudinalTrend(Base):
    """
    Pre-computed longitudinal trends for fast visualization.

    Aggregates observations over time for specific variables.
    """

    __tablename__ = "longitudinal_trends"

    trend_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(100), ForeignKey("patients.patient_id"), nullable=False)

    variable_name = Column(String(100), nullable=False)

    # Time series data (stored as JSON arrays)
    time_points = Column(JSON, nullable=False)  # Array of ISO timestamps
    values = Column(JSON, nullable=False)  # Array of numeric values

    # Statistics
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    mean_value = Column(Float, nullable=True)
    std_dev = Column(Float, nullable=True)

    # Timestamps
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_trend_patient_variable", "patient_id", "variable_name"),
    )

    def __repr__(self):
        return f"<LongitudinalTrend(patient={self.patient_id}, var={self.variable_name}, points={len(self.time_points)})>"


class ArrhythmiaEpisode(Base):
    """
    Discrete arrhythmia episodes detected from HL7 data.

    Links to EGM strips when available.
    """

    __tablename__ = "arrhythmia_episodes"

    episode_id = Column(Integer, primary_key=True, autoincrement=True)
    transmission_id = Column(Integer, ForeignKey("transmissions.transmission_id"), nullable=False)

    # Episode metadata
    episode_type = Column(String(50), nullable=False)  # "AFib", "VT", "SVT", "AFL", etc.
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Clinical parameters
    max_rate = Column(Integer, nullable=True)  # bpm
    min_rate = Column(Integer, nullable=True)  # bpm
    avg_rate = Column(Integer, nullable=True)  # bpm
    burden_percent = Column(Float, nullable=True)  # For AFib burden calculations

    # Severity
    severity = Column(String(20), nullable=True)  # "info", "warning", "critical"

    # EGM data reference
    egm_blob_id = Column(Integer, nullable=True)  # Links to Observation with EGM blob
    egm_available = Column(Boolean, default=False, nullable=False)

    # Additional metadata
    episode_metadata = Column(JSON, nullable=True)  # Flexible storage for vendor-specific data

    # Relationships
    transmission = relationship("Transmission", back_populates="episodes")

    # Indexes
    __table_args__ = (
        Index("idx_episode_type", "episode_type"),
        Index("idx_episode_time", "start_time"),
        Index("idx_episode_transmission", "transmission_id"),
    )

    def __repr__(self):
        return f"<ArrhythmiaEpisode(id={self.episode_id}, type={self.episode_type}, start={self.start_time})>"


class DeviceParameter(Base):
    """
    Device programming parameters from HL7 messages.

    Stores mode, rate limits, and other programmable settings.
    """

    __tablename__ = "device_parameters"

    parameter_id = Column(Integer, primary_key=True, autoincrement=True)
    transmission_id = Column(Integer, ForeignKey("transmissions.transmission_id"), nullable=False)

    # Parameter identification
    parameter_name = Column(String(100), nullable=False)
    parameter_value = Column(String(200), nullable=True)
    parameter_unit = Column(String(50), nullable=True)

    # Categorization
    category = Column(String(50), nullable=True)  # "pacing", "sensing", "mode", etc.

    # Timestamps
    recorded_at = Column(DateTime, nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_param_transmission", "transmission_id"),
        Index("idx_param_name", "parameter_name"),
    )

    def __repr__(self):
        return f"<DeviceParameter(name={self.parameter_name}, value={self.parameter_value})>"


class Analysis(Base):
    """
    Stored analysis results.

    Caches computed analyses like battery depletion trends, fracture detection, etc.
    """

    __tablename__ = "analyses"

    analysis_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(100), ForeignKey("patients.patient_id"), nullable=False)

    # Analysis metadata
    analysis_type = Column(String(100), nullable=False)  # "battery_trend", "lead_fracture", etc.
    analysis_name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)

    # Results (stored as JSON)
    results = Column(JSON, nullable=False)

    # Time range analyzed
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Timestamps
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_analysis_patient_type", "patient_id", "analysis_type"),
    )

    def __repr__(self):
        return f"<Analysis(id={self.analysis_id}, type={self.analysis_type}, patient={self.patient_id})>"
