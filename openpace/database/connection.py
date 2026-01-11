"""
Database Connection Management

Handles SQLite database initialization and session management.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from openpace.database.models import Base


class DatabaseManager:
    """
    Manages database connection and session lifecycle.

    Provides singleton pattern for database access throughout the application.
    """

    _instance = None
    _engine = None
    _session_factory = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    def initialize(self, database_path: str = None, echo: bool = False):
        """
        Initialize the database connection.

        Args:
            database_path: Path to SQLite database file. If None, uses default.
            echo: If True, SQLAlchemy will log all SQL statements.
        """
        if database_path is None:
            # Default database location in user's home directory
            database_path = self._get_default_database_path()

        # Ensure directory exists
        db_dir = Path(database_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # Create engine
        database_url = f"sqlite:///{database_path}"
        self._engine = create_engine(
            database_url,
            echo=echo,
            # Use StaticPool for SQLite to avoid threading issues
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        # Enable foreign key constraints for SQLite
        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # Create all tables
        Base.metadata.create_all(self._engine)

        # Create session factory
        self._session_factory = sessionmaker(bind=self._engine)

    def _get_default_database_path(self) -> str:
        """
        Get the default database path.

        Returns:
            Path to database file in user's home directory.
        """
        home_dir = Path.home()
        app_data_dir = home_dir / ".openpace"
        app_data_dir.mkdir(exist_ok=True)
        return str(app_data_dir / "openpace.db")

    def get_session(self) -> Session:
        """
        Create a new database session.

        Returns:
            SQLAlchemy Session object.

        Raises:
            RuntimeError: If database has not been initialized.
        """
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._session_factory()

    def close(self):
        """
        Close the database connection.
        """
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @property
    def engine(self):
        """Get the SQLAlchemy engine."""
        return self._engine

    @property
    def is_initialized(self) -> bool:
        """Check if database is initialized."""
        return self._engine is not None


# Global database manager instance
db_manager = DatabaseManager()


def get_db_session() -> Session:
    """
    Convenience function to get a database session.

    Returns:
        SQLAlchemy Session object.
    """
    return db_manager.get_session()


def init_database(database_path: str = None, echo: bool = False):
    """
    Initialize the database.

    Args:
        database_path: Path to SQLite database file. If None, uses default.
        echo: If True, SQLAlchemy will log all SQL statements.
    """
    db_manager.initialize(database_path, echo)


def close_database():
    """
    Close the database connection.
    """
    db_manager.close()
