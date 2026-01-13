"""
Configuration Management for OpenPace

This module provides a centralized configuration system for OpenPace.
Configuration can be loaded from JSON files, environment variables, or defaults.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    path: Optional[str] = None  # None = use default (~/.openpace/openpace.db)
    echo_sql: bool = False      # Log all SQL statements
    encryption_key: Optional[str] = None  # Encryption key for database
    pool_size: int = 5          # Connection pool size
    max_overflow: int = 10      # Maximum overflow connections

    def get_path(self) -> Path:
        """
        Get database path, using default if not specified.

        Returns:
            Path to database file
        """
        if self.path:
            return Path(self.path)
        else:
            return Path.home() / ".openpace" / "openpace.db"


@dataclass
class LoggingConfig:
    """Logging configuration settings."""

    level: str = "INFO"         # Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_dir: Optional[str] = None  # Directory for log files (None = ~/.openpace/logs)
    console_output: bool = True    # Output logs to console
    file_output: bool = True       # Output logs to file
    max_file_size_mb: int = 10     # Maximum log file size before rotation
    backup_count: int = 5          # Number of backup log files to keep

    def get_log_dir(self) -> Path:
        """
        Get log directory, using default if not specified.

        Returns:
            Path to log directory
        """
        if self.log_dir:
            return Path(self.log_dir)
        else:
            return Path.home() / ".openpace" / "logs"


@dataclass
class SecurityConfig:
    """Security and privacy configuration settings."""

    anonymize_by_default: bool = False       # Anonymize patient names by default
    max_import_file_size_mb: int = 50        # Maximum file size for imports
    require_encryption: bool = False         # Require database encryption
    enable_audit_log: bool = True            # Log all data access operations
    password_protected: bool = False         # Require password to open app
    auto_lock_minutes: int = 0               # Auto-lock after inactivity (0 = disabled)


@dataclass
class UIConfig:
    """User interface configuration settings."""

    theme: str = "default"                   # UI theme: default, dark, light
    default_window_width: int = 1400         # Default window width in pixels
    default_window_height: int = 900         # Default window height in pixels
    show_splash_screen: bool = True          # Show splash screen on startup
    remember_window_position: bool = True    # Remember window position/size
    plot_dpi: int = 100                      # Plot resolution (DPI)
    max_plot_points: int = 10000             # Downsample plots with more points
    language: str = "en"                     # Interface language

    # Panel layout settings
    use_grid_layout: bool = True             # Use new grid layout system
    save_panel_layouts: bool = True          # Save panel layout preferences
    panel_layouts: Dict[str, Any] = field(default_factory=dict)  # Stored panel layouts
    default_layout_mode: str = "vertical"    # Default layout: vertical, horizontal, free_grid
    panel_min_height: int = 150              # Minimum panel height in pixels
    panel_min_width: int = 200               # Minimum panel width in pixels
    grid_rows: int = 12                      # Number of grid rows
    grid_cols: int = 12                      # Number of grid columns
    snap_to_grid: bool = True                # Snap panels to grid when dragging


@dataclass
class AnalysisConfig:
    """Analysis and computation configuration settings."""

    trend_cache_ttl_hours: int = 1           # Cache trends for this many hours
    analysis_cache_ttl_minutes: int = 30     # Cache analysis results
    auto_calculate_trends: bool = True       # Auto-calculate trends on import
    min_points_for_prediction: int = 3       # Minimum data points for predictions
    confidence_threshold: str = "medium"     # Required confidence: low, medium, high


@dataclass
class ExportConfig:
    """Export and reporting configuration settings."""

    default_format: str = "pdf"              # Default export format: pdf, xlsx, csv
    include_timestamps: bool = True          # Include timestamps in exports
    include_metadata: bool = True            # Include metadata in exports
    compress_exports: bool = False           # Compress exported files


@dataclass
class OpenPaceConfig:
    """
    Main OpenPace configuration class.

    This class holds all configuration settings for the application.
    Settings can be loaded from a JSON file or use defaults.
    """

    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    export: ExportConfig = field(default_factory=ExportConfig)

    @classmethod
    def load_from_file(cls, config_path: Optional[Path] = None) -> 'OpenPaceConfig':
        """
        Load configuration from JSON file.

        If the file doesn't exist, a default configuration will be created
        and saved to the specified path.

        Args:
            config_path: Path to config file (default: ~/.openpace/config.json)

        Returns:
            OpenPaceConfig instance

        Example:
            >>> config = OpenPaceConfig.load_from_file()
            >>> config.database.echo_sql = True
            >>> config.save_to_file()
        """
        if config_path is None:
            config_path = Path.home() / ".openpace" / "config.json"

        # Create parent directory if needed
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # If config doesn't exist, create default
        if not config_path.exists():
            logger.info(f"Configuration file not found. Creating default: {config_path}")
            config = cls.default()
            config.save_to_file(config_path)
            return config

        # Load existing config
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)

            logger.info(f"Loaded configuration from: {config_path}")

            return cls(
                database=DatabaseConfig(**data.get('database', {})),
                logging=LoggingConfig(**data.get('logging', {})),
                security=SecurityConfig(**data.get('security', {})),
                ui=UIConfig(**data.get('ui', {})),
                analysis=AnalysisConfig(**data.get('analysis', {})),
                export=ExportConfig(**data.get('export', {}))
            )

        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            logger.info("Using default configuration")
            return cls.default()

    @classmethod
    def load_from_env(cls) -> 'OpenPaceConfig':
        """
        Load configuration from environment variables.

        Environment variables should be prefixed with OPENPACE_
        and use double underscores for nested values.

        Examples:
            OPENPACE_DATABASE_PATH=/path/to/db.db
            OPENPACE_LOGGING_LEVEL=DEBUG
            OPENPACE_SECURITY_ANONYMIZE_BY_DEFAULT=true

        Returns:
            OpenPaceConfig instance with values from environment
        """
        config = cls.default()

        # Database config
        if os.getenv('OPENPACE_DATABASE_PATH'):
            config.database.path = os.getenv('OPENPACE_DATABASE_PATH')
        if os.getenv('OPENPACE_DATABASE_ECHO_SQL'):
            config.database.echo_sql = os.getenv('OPENPACE_DATABASE_ECHO_SQL').lower() == 'true'
        if os.getenv('OPENPACE_DATABASE_ENCRYPTION_KEY'):
            config.database.encryption_key = os.getenv('OPENPACE_DATABASE_ENCRYPTION_KEY')

        # Logging config
        if os.getenv('OPENPACE_LOGGING_LEVEL'):
            config.logging.level = os.getenv('OPENPACE_LOGGING_LEVEL')
        if os.getenv('OPENPACE_LOGGING_LOG_DIR'):
            config.logging.log_dir = os.getenv('OPENPACE_LOGGING_LOG_DIR')

        # Security config
        if os.getenv('OPENPACE_SECURITY_ANONYMIZE_BY_DEFAULT'):
            config.security.anonymize_by_default = \
                os.getenv('OPENPACE_SECURITY_ANONYMIZE_BY_DEFAULT').lower() == 'true'
        if os.getenv('OPENPACE_SECURITY_REQUIRE_ENCRYPTION'):
            config.security.require_encryption = \
                os.getenv('OPENPACE_SECURITY_REQUIRE_ENCRYPTION').lower() == 'true'

        logger.info("Loaded configuration from environment variables")
        return config

    @classmethod
    def default(cls) -> 'OpenPaceConfig':
        """
        Create default configuration.

        Returns:
            OpenPaceConfig with default values
        """
        return cls(
            database=DatabaseConfig(),
            logging=LoggingConfig(),
            security=SecurityConfig(),
            ui=UIConfig(),
            analysis=AnalysisConfig(),
            export=ExportConfig()
        )

    def save_to_file(self, config_path: Optional[Path] = None):
        """
        Save configuration to JSON file.

        Args:
            config_path: Path to save config (default: ~/.openpace/config.json)

        Example:
            >>> config = OpenPaceConfig.default()
            >>> config.database.echo_sql = True
            >>> config.save_to_file()
        """
        if config_path is None:
            config_path = Path.home() / ".openpace" / "config.json"

        # Create parent directory
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dictionary
        data = {
            'database': asdict(self.database),
            'logging': asdict(self.logging),
            'security': asdict(self.security),
            'ui': asdict(self.ui),
            'analysis': asdict(self.analysis),
            'export': asdict(self.export)
        }

        # Save to file
        try:
            with open(config_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Configuration saved to: {config_path}")

        except Exception as e:
            logger.error(f"Failed to save config to {config_path}: {e}")
            raise

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {
            'database': asdict(self.database),
            'logging': asdict(self.logging),
            'security': asdict(self.security),
            'ui': asdict(self.ui),
            'analysis': asdict(self.analysis),
            'export': asdict(self.export)
        }

    def validate(self) -> bool:
        """
        Validate configuration settings.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate logging level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.logging.level.upper() not in valid_levels:
            raise ValueError(
                f"Invalid logging level: {self.logging.level}. "
                f"Must be one of: {', '.join(valid_levels)}"
            )

        # Validate UI theme
        valid_themes = ['default', 'dark', 'light']
        if self.ui.theme not in valid_themes:
            raise ValueError(
                f"Invalid UI theme: {self.ui.theme}. "
                f"Must be one of: {', '.join(valid_themes)}"
            )

        # Validate confidence threshold
        valid_confidence = ['low', 'medium', 'high']
        if self.analysis.confidence_threshold not in valid_confidence:
            raise ValueError(
                f"Invalid confidence threshold: {self.analysis.confidence_threshold}. "
                f"Must be one of: {', '.join(valid_confidence)}"
            )

        # Validate export format
        valid_formats = ['pdf', 'xlsx', 'csv', 'json']
        if self.export.default_format not in valid_formats:
            raise ValueError(
                f"Invalid export format: {self.export.default_format}. "
                f"Must be one of: {', '.join(valid_formats)}"
            )

        # Validate numeric ranges
        if self.ui.default_window_width < 800:
            raise ValueError("Window width must be at least 800 pixels")

        if self.ui.default_window_height < 600:
            raise ValueError("Window height must be at least 600 pixels")

        if self.security.max_import_file_size_mb < 1:
            raise ValueError("Max import file size must be at least 1 MB")

        if self.analysis.min_points_for_prediction < 2:
            raise ValueError("Minimum points for prediction must be at least 2")

        return True


# Global configuration instance
_config: Optional[OpenPaceConfig] = None


def get_config() -> OpenPaceConfig:
    """
    Get global configuration instance.

    Returns:
        OpenPaceConfig singleton instance

    Example:
        >>> from openpace.config import get_config
        >>> config = get_config()
        >>> print(config.database.path)
    """
    global _config
    if _config is None:
        # Try loading from environment first, then file
        if os.getenv('OPENPACE_USE_ENV_CONFIG'):
            _config = OpenPaceConfig.load_from_env()
        else:
            _config = OpenPaceConfig.load_from_file()
    return _config


def set_config(config: OpenPaceConfig):
    """
    Set global configuration instance.

    Args:
        config: OpenPaceConfig instance to use globally

    Example:
        >>> from openpace.config import OpenPaceConfig, set_config
        >>> config = OpenPaceConfig.default()
        >>> config.database.echo_sql = True
        >>> set_config(config)
    """
    global _config
    _config = config
