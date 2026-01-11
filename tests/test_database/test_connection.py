"""
Test suite for OpenPace database connection management.

Tests cover:
- Database initialization
- Connection pooling
- Session management
- Migration handling
- Error handling
"""

import os
from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from openpace.database.connection import DatabaseManager
from openpace.database.models import (
    Analysis,
    ArrhythmiaEpisode,
    DeviceParameter,
    LongitudinalTrend,
    Observation,
    Patient,
    Transmission,
)


class TestDatabaseManager:
    """Test suite for DatabaseManager class."""

    def test_init_in_memory_database(self):
        """Test initializing an in-memory database."""
        db_manager = DatabaseManager(db_path=":memory:")
        assert db_manager.engine is not None

        # Verify all tables are created
        inspector = inspect(db_manager.engine)
        tables = inspector.get_table_names()

        expected_tables = [
            "patients",
            "transmissions",
            "observations",
            "longitudinal_trends",
            "arrhythmia_episodes",
            "device_parameters",
            "analyses"
        ]

        for table in expected_tables:
            assert table in tables

    def test_init_file_database(self, temp_db_file):
        """Test initializing a file-based database."""
        db_manager = DatabaseManager(db_path=str(temp_db_file))
        assert db_manager.engine is not None
        assert temp_db_file.exists()

        # Verify database file is valid
        inspector = inspect(db_manager.engine)
        assert len(inspector.get_table_names()) > 0

    def test_get_session(self):
        """Test getting a database session."""
        db_manager = DatabaseManager(db_path=":memory:")
        session = db_manager.get_session()

        assert session is not None
        assert hasattr(session, "query")
        assert hasattr(session, "add")
        assert hasattr(session, "commit")

        session.close()

    def test_session_independence(self):
        """Test that multiple sessions are independent."""
        db_manager = DatabaseManager(db_path=":memory:")

        session1 = db_manager.get_session()
        session2 = db_manager.get_session()

        assert session1 is not session2

        session1.close()
        session2.close()

    def test_foreign_key_constraints_enabled(self):
        """Test that foreign key constraints are enabled."""
        db_manager = DatabaseManager(db_path=":memory:")
        session = db_manager.get_session()

        # Try to create transmission without patient (should fail)
        from datetime import datetime
        from sqlalchemy.exc import IntegrityError

        transmission = Transmission(
            patient_id=99999,  # Non-existent patient
            transmission_date=datetime.now(),
            device_model="TEST",
            device_serial="123",
            raw_hl7="TEST"
        )
        session.add(transmission)

        with pytest.raises(IntegrityError):
            session.commit()

        session.close()

    def test_database_indexes_created(self):
        """Test that database indexes are created."""
        db_manager = DatabaseManager(db_path=":memory:")
        inspector = inspect(db_manager.engine)

        # Check indexes on patients table
        patient_indexes = inspector.get_indexes("patients")
        index_columns = [idx["column_names"] for idx in patient_indexes]
        assert ["patient_id"] in index_columns

        # Check indexes on observations table
        observation_indexes = inspector.get_indexes("observations")
        obs_index_columns = [idx["column_names"] for idx in observation_indexes]
        assert ["variable_name"] in obs_index_columns

    def test_close_connection(self):
        """Test closing database connection."""
        db_manager = DatabaseManager(db_path=":memory:")
        session = db_manager.get_session()

        # Close manager
        db_manager.close()

        # Attempting to use session after close should raise error
        with pytest.raises(Exception):
            session.query(Patient).all()

    def test_context_manager(self):
        """Test using DatabaseManager as context manager."""
        with DatabaseManager(db_path=":memory:") as db_manager:
            session = db_manager.get_session()
            patient = Patient(
                patient_id="CTX001",
                last_name_hash="CONTEXT",
                first_name_hash="TEST",
                date_of_birth_offset=0
            )
            session.add(patient)
            session.commit()
            session.close()

        # After context, connection should be closed
        assert db_manager.engine.pool.checkedout() == 0


class TestDatabaseTransactions:
    """Test transaction handling."""

    def test_transaction_commit(self):
        """Test successful transaction commit."""
        db_manager = DatabaseManager(db_path=":memory:")
        session = db_manager.get_session()

        patient = Patient(
            patient_id="TX001",
            last_name_hash="COMMIT",
            first_name_hash="TEST",
            date_of_birth_offset=0
        )
        session.add(patient)
        session.commit()

        # Verify data persisted
        retrieved = session.query(Patient).filter_by(patient_id="TX001").first()
        assert retrieved is not None
        assert retrieved.last_name_hash == "COMMIT"

        session.close()

    def test_transaction_rollback(self):
        """Test transaction rollback."""
        db_manager = DatabaseManager(db_path=":memory:")
        session = db_manager.get_session()

        patient = Patient(
            patient_id="TX002",
            last_name_hash="ROLLBACK",
            first_name_hash="TEST",
            date_of_birth_offset=0
        )
        session.add(patient)

        # Rollback instead of commit
        session.rollback()

        # Verify data not persisted
        retrieved = session.query(Patient).filter_by(patient_id="TX002").first()
        assert retrieved is None

        session.close()

    def test_transaction_isolation(self):
        """Test transaction isolation between sessions."""
        db_manager = DatabaseManager(db_path=":memory:")

        session1 = db_manager.get_session()
        session2 = db_manager.get_session()

        # Add patient in session1 but don't commit
        patient = Patient(
            patient_id="TX003",
            last_name_hash="ISOLATION",
            first_name_hash="TEST",
            date_of_birth_offset=0
        )
        session1.add(patient)

        # Session2 should not see uncommitted data
        retrieved = session2.query(Patient).filter_by(patient_id="TX003").first()
        assert retrieved is None

        # After commit, session2 should see it
        session1.commit()
        session2.expire_all()  # Refresh session2
        retrieved = session2.query(Patient).filter_by(patient_id="TX003").first()
        assert retrieved is not None

        session1.close()
        session2.close()


class TestDatabaseErrors:
    """Test error handling."""

    def test_invalid_database_path(self):
        """Test handling of invalid database path."""
        invalid_path = "/invalid/path/that/does/not/exist/db.sqlite"

        with pytest.raises(Exception):
            db_manager = DatabaseManager(db_path=invalid_path)
            session = db_manager.get_session()
            session.query(Patient).all()

    def test_duplicate_key_error(self):
        """Test handling of duplicate key constraint violation."""
        db_manager = DatabaseManager(db_path=":memory:")
        session = db_manager.get_session()

        patient1 = Patient(
            patient_id="DUP001",
            last_name_hash="DUPLICATE",
            first_name_hash="TEST1",
            date_of_birth_offset=0
        )
        session.add(patient1)
        session.commit()

        patient2 = Patient(
            patient_id="DUP001",  # Same ID
            last_name_hash="DUPLICATE",
            first_name_hash="TEST2",
            date_of_birth_offset=0
        )
        session.add(patient2)

        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            session.commit()

        session.close()


class TestDatabaseConfiguration:
    """Test database configuration options."""

    def test_echo_mode(self):
        """Test enabling SQL echo mode."""
        db_manager = DatabaseManager(db_path=":memory:", echo=True)
        assert db_manager.engine.echo is True

    def test_default_echo_mode(self):
        """Test default echo mode is disabled."""
        db_manager = DatabaseManager(db_path=":memory:")
        assert db_manager.engine.echo is False

    def test_connection_pool_size(self):
        """Test connection pool configuration."""
        db_manager = DatabaseManager(db_path=":memory:")

        # SQLite uses NullPool by default for file/memory databases
        # Just verify we can create multiple sessions
        sessions = [db_manager.get_session() for _ in range(5)]

        assert len(sessions) == 5
        for session in sessions:
            session.close()
