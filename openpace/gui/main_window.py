"""
OpenPace Main Window

The primary application window for OpenPace, featuring:
- Patient selector
- Timeline view (macro)
- Episode viewer (micro)
- Menu bar and toolbars
"""

import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMenuBar,
    QMenu,
    QStatusBar,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from openpace.database.connection import init_database, get_db_session
from openpace.hl7.parser import HL7Parser
from openpace.database.models import Transmission
from openpace.gui.widgets.timeline_view import TimelineView
from openpace.gui.widgets.settings_panel import SettingsPanel
from openpace.gui.layouts import LayoutMode, LayoutSerializer
from openpace.exceptions import (
    FileValidationError,
    HL7ValidationError,
    ValidationError,
    format_validation_error
)
from openpace.constants import FileLimits

# Configure logging
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window for OpenPace.

    Provides the OSCAR-style interface with timeline and episode viewers.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenPace - Pacemaker Data Analyzer")
        self.setGeometry(100, 100, 1400, 900)

        # Initialize database
        init_database()
        self.db_session = get_db_session()

        # Initialize UI
        self._create_menu_bar()
        self._create_toolbar()
        self._create_central_widget()
        self._create_status_bar()

    def _create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        import_action = QAction("&Import HL7 Data...", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self._import_data)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        # Panels submenu
        panels_menu = view_menu.addMenu("&Panels")

        self.battery_panel_action = QAction("Battery Voltage", self)
        self.battery_panel_action.setCheckable(True)
        self.battery_panel_action.setChecked(True)
        self.battery_panel_action.triggered.connect(lambda checked: self.timeline_view.toggle_panel('battery', checked))
        panels_menu.addAction(self.battery_panel_action)

        self.atrial_panel_action = QAction("Atrial Lead Impedance", self)
        self.atrial_panel_action.setCheckable(True)
        self.atrial_panel_action.setChecked(True)
        self.atrial_panel_action.triggered.connect(lambda checked: self.timeline_view.toggle_panel('atrial_impedance', checked))
        panels_menu.addAction(self.atrial_panel_action)

        self.vent_panel_action = QAction("Ventricular Lead Impedance", self)
        self.vent_panel_action.setCheckable(True)
        self.vent_panel_action.setChecked(True)
        self.vent_panel_action.triggered.connect(lambda checked: self.timeline_view.toggle_panel('vent_impedance', checked))
        panels_menu.addAction(self.vent_panel_action)

        self.burden_panel_action = QAction("Arrhythmia Burden", self)
        self.burden_panel_action.setCheckable(True)
        self.burden_panel_action.setChecked(True)
        self.burden_panel_action.triggered.connect(lambda checked: self.timeline_view.toggle_panel('burden', checked))
        panels_menu.addAction(self.burden_panel_action)

        self.settings_panel_action = QAction("Device Settings", self)
        self.settings_panel_action.setCheckable(True)
        self.settings_panel_action.setChecked(True)
        self.settings_panel_action.triggered.connect(lambda checked: self.timeline_view.toggle_panel('settings', checked))
        panels_menu.addAction(self.settings_panel_action)

        self.device_settings_panel_action = QAction("Device Settings (Fixed/Operator)", self)
        self.device_settings_panel_action.setCheckable(True)
        self.device_settings_panel_action.setChecked(True)
        self.device_settings_panel_action.triggered.connect(lambda checked: self.timeline_view.toggle_panel('device_settings', checked))
        panels_menu.addAction(self.device_settings_panel_action)

        self.heart_rate_panel_action = QAction("Heart Rate Timeline", self)
        self.heart_rate_panel_action.setCheckable(True)
        self.heart_rate_panel_action.setChecked(True)
        self.heart_rate_panel_action.triggered.connect(lambda checked: self.timeline_view.toggle_panel('heart_rate', checked))
        panels_menu.addAction(self.heart_rate_panel_action)

        view_menu.addSeparator()

        # Layout submenu
        layout_menu = view_menu.addMenu("&Layout")

        # Layout modes
        modes_menu = layout_menu.addMenu("Layout &Mode")

        self.vertical_layout_action = QAction("Vertical (Stacked)", self)
        self.vertical_layout_action.setCheckable(True)
        self.vertical_layout_action.setChecked(True)
        self.vertical_layout_action.setShortcut("Ctrl+1")
        self.vertical_layout_action.triggered.connect(self._set_vertical_layout)
        modes_menu.addAction(self.vertical_layout_action)

        self.horizontal_layout_action = QAction("Horizontal (Side-by-Side)", self)
        self.horizontal_layout_action.setCheckable(True)
        self.horizontal_layout_action.setChecked(False)
        self.horizontal_layout_action.setShortcut("Ctrl+2")
        self.horizontal_layout_action.triggered.connect(self._set_horizontal_layout)
        modes_menu.addAction(self.horizontal_layout_action)

        self.free_grid_layout_action = QAction("Free Grid", self)
        self.free_grid_layout_action.setCheckable(True)
        self.free_grid_layout_action.setChecked(False)
        self.free_grid_layout_action.setShortcut("Ctrl+3")
        self.free_grid_layout_action.triggered.connect(self._set_free_grid_layout)
        modes_menu.addAction(self.free_grid_layout_action)

        layout_menu.addSeparator()

        # Edit mode toggle
        self.edit_layout_action = QAction("&Edit Layout Mode", self)
        self.edit_layout_action.setCheckable(True)
        self.edit_layout_action.setChecked(True)
        self.edit_layout_action.setShortcut("Ctrl+E")
        self.edit_layout_action.setToolTip("Enable/disable panel dragging and resizing")
        self.edit_layout_action.triggered.connect(self._toggle_edit_mode)
        layout_menu.addAction(self.edit_layout_action)

        # Lock all panels action
        self.lock_all_panels_action = QAction("&Lock All Panels", self)
        self.lock_all_panels_action.triggered.connect(self._lock_all_panels)
        layout_menu.addAction(self.lock_all_panels_action)

        layout_menu.addSeparator()

        # Layout management actions
        save_layout_action = QAction("&Save Layout As...", self)
        save_layout_action.setShortcut("Ctrl+Shift+S")
        save_layout_action.triggered.connect(self._save_layout)
        layout_menu.addAction(save_layout_action)

        load_layout_action = QAction("&Load Layout...", self)
        load_layout_action.setShortcut("Ctrl+Shift+L")
        load_layout_action.triggered.connect(self._load_layout)
        layout_menu.addAction(load_layout_action)

        reset_layout_action = QAction("&Reset to Default", self)
        reset_layout_action.triggered.connect(self._reset_layout)
        layout_menu.addAction(reset_layout_action)

        layout_menu.addSeparator()

        # Grid settings
        grid_settings_action = QAction("&Grid Settings...", self)
        grid_settings_action.triggered.connect(self._show_grid_settings)
        layout_menu.addAction(grid_settings_action)

        view_menu.addSeparator()

        settings_window_action = QAction("Device Settings &Window", self)
        settings_window_action.setShortcut("Ctrl+S")
        settings_window_action.triggered.connect(self._show_settings_window)
        view_menu.addAction(settings_window_action)

        # Analysis menu
        analysis_menu = menubar.addMenu("&Analysis")

        battery_action = QAction("&Battery Trend Analysis", self)
        analysis_menu.addAction(battery_action)

        impedance_action = QAction("&Lead Impedance Analysis", self)
        analysis_menu.addAction(impedance_action)

        burden_action = QAction("A&rrhythmia Burden", self)
        analysis_menu.addAction(burden_action)

        # Privacy menu
        privacy_menu = menubar.addMenu("&Privacy")

        anonymize_action = QAction("&Anonymization Mode", self)
        anonymize_action.setCheckable(True)
        anonymize_action.setChecked(False)
        anonymize_action.triggered.connect(self._toggle_anonymization)
        privacy_menu.addAction(anonymize_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About OpenPace", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self):
        """Create the main toolbar."""
        toolbar = self.addToolBar("Main Toolbar")

        # Add toolbar actions
        import_btn = QPushButton("Import Data")
        import_btn.clicked.connect(self._import_data)
        toolbar.addWidget(import_btn)

    def _create_central_widget(self):
        """Create the central widget with timeline and episode views."""
        # Create timeline view as central widget
        self.timeline_view = TimelineView(self.db_session)
        self.setCentralWidget(self.timeline_view)

        # Connect panel visibility signals to menu actions (for synchronization)
        self.timeline_view.battery_visibility_changed.connect(self.battery_panel_action.setChecked)
        self.timeline_view.atrial_impedance_visibility_changed.connect(self.atrial_panel_action.setChecked)
        self.timeline_view.vent_impedance_visibility_changed.connect(self.vent_panel_action.setChecked)
        self.timeline_view.burden_visibility_changed.connect(self.burden_panel_action.setChecked)
        self.timeline_view.settings_visibility_changed.connect(self.settings_panel_action.setChecked)
        self.timeline_view.device_settings_visibility_changed.connect(self.device_settings_panel_action.setChecked)
        self.timeline_view.heart_rate_visibility_changed.connect(self.heart_rate_panel_action.setChecked)

    def _create_status_bar(self):
        """Create the status bar."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage("Ready")

    def _validate_import_file(self, file_path: str) -> None:
        """
        Validate file for import to prevent security vulnerabilities.

        Prevents:
        - Path traversal attacks
        - DoS through large files
        - Symlink attacks

        Args:
            file_path: Path to file to validate

        Raises:
            FileValidationError: If file fails validation
        """
        # Resolve path to prevent symlink attacks
        try:
            resolved_path = Path(file_path).resolve(strict=True)
        except Exception as e:
            raise FileValidationError(f"Invalid file path: {e}")

        # Check if file exists
        if not resolved_path.exists():
            raise FileValidationError(f"File does not exist: {file_path}")

        # Check if it's a regular file (not a directory or special file)
        if not resolved_path.is_file():
            raise FileValidationError(f"Path is not a regular file: {file_path}")

        # Check file size to prevent DoS
        file_size = resolved_path.stat().st_size
        if file_size > FileLimits.MAX_IMPORT_FILE_SIZE:
            raise FileValidationError(
                f"File too large ({file_size} bytes). "
                f"Maximum allowed: {FileLimits.MAX_IMPORT_FILE_SIZE} bytes (50 MB)"
            )

        if file_size < FileLimits.MIN_HL7_MESSAGE_SIZE:
            raise FileValidationError(
                f"File too small ({file_size} bytes). "
                f"Minimum size: {FileLimits.MIN_HL7_MESSAGE_SIZE} bytes"
            )

        # Validate file extension (optional but recommended)
        allowed_extensions = ['.hl7', '.txt']
        if resolved_path.suffix.lower() not in allowed_extensions:
            logger.warning(f"Importing file with unusual extension: {resolved_path.suffix}")

        logger.info(f"File validation passed: {file_path} ({file_size} bytes)")

    # Slot methods
    def _import_data(self):
        """Handle data import action with comprehensive security validation."""
        # Open file dialog - allow multiple file selection
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import HL7 Data",
            "",
            "HL7 Files (*.hl7 *.dat);;Text Files (*.txt);;All Files (*)"
        )

        if not file_paths:
            return

        # Track results for summary
        successful_imports = []
        failed_imports = []

        # Create parser once for all files
        parser = HL7Parser(self.db_session, anonymize=False)

        for file_path in file_paths:
            try:
                # Validate file before reading (security check)
                self._validate_import_file(file_path)

                # Read HL7 file with size limit enforced
                with open(file_path, 'r', encoding='utf-8') as f:
                    hl7_message = f.read(FileLimits.MAX_IMPORT_FILE_SIZE + 1)

                # Double-check size after reading
                if len(hl7_message.encode('utf-8')) > FileLimits.MAX_IMPORT_FILE_SIZE:
                    raise FileValidationError("File exceeds maximum allowed size")

                # Parse HL7 message (parser has additional validation)
                transmission = parser.parse_message(hl7_message, filename=file_path)

                successful_imports.append({
                    'file': os.path.basename(file_path),
                    'transmission_id': transmission.transmission_id,
                    'patient': transmission.patient.patient_name,
                    'observations': len(transmission.observations)
                })
                logger.info(f"Successfully imported HL7 file: {file_path}")

            except FileValidationError as e:
                logger.error(f"File validation failed for {file_path}: {e}")
                failed_imports.append({'file': os.path.basename(file_path), 'error': f"File validation: {str(e)}"})

            except HL7ValidationError as e:
                logger.error(f"HL7 validation failed for {file_path}: {e}")
                failed_imports.append({'file': os.path.basename(file_path), 'error': f"HL7 validation: {str(e)}"})

            except ValidationError as e:
                logger.error(f"Data validation failed for {file_path}: {e}")
                failed_imports.append({'file': os.path.basename(file_path), 'error': f"Data validation: {str(e)}"})

            except Exception as e:
                logger.exception(f"Import failed for {file_path}: {e}")
                failed_imports.append({'file': os.path.basename(file_path), 'error': str(e)})

        # Show summary message
        if successful_imports or failed_imports:
            self._show_import_summary(successful_imports, failed_imports)

        # Refresh timeline view
        if successful_imports:
            self.timeline_view.patient_selector.load_patients()
            self.statusBar().showMessage(
                f"Imported {len(successful_imports)} file(s), {len(failed_imports)} failed", 5000
            )

    def _show_import_summary(self, successful: list, failed: list):
        """Show a summary dialog of import results."""
        message_parts = []

        if successful:
            message_parts.append(f"Successfully imported {len(successful)} file(s):\n")
            for item in successful:
                message_parts.append(
                    f"  • {item['file']}: {item['observations']} observations"
                )

        if failed:
            if successful:
                message_parts.append("\n")
            message_parts.append(f"Failed to import {len(failed)} file(s):\n")
            for item in failed:
                message_parts.append(f"  • {item['file']}: {item['error']}")

        message = "\n".join(message_parts)

        if failed and not successful:
            QMessageBox.critical(self, "Import Failed", message)
        elif failed:
            QMessageBox.warning(self, "Import Complete (with errors)", message)
        else:
            QMessageBox.information(self, "Import Successful", message)

    def _toggle_anonymization(self, checked):
        """Toggle anonymization mode."""
        mode = "ON" if checked else "OFF"
        self.statusBar().showMessage(f"Anonymization mode: {mode}")

    def _set_vertical_layout(self):
        """Set vertical (stacked) panel layout."""
        self.timeline_view.set_orientation(Qt.Orientation.Vertical)
        self.vertical_layout_action.setChecked(True)
        self.horizontal_layout_action.setChecked(False)
        self.free_grid_layout_action.setChecked(False)
        self.statusBar().showMessage("Layout: Vertical (Stacked)", 3000)

    def _set_horizontal_layout(self):
        """Set horizontal (side-by-side) panel layout."""
        self.timeline_view.set_orientation(Qt.Orientation.Horizontal)
        self.vertical_layout_action.setChecked(False)
        self.horizontal_layout_action.setChecked(True)
        self.free_grid_layout_action.setChecked(False)
        self.statusBar().showMessage("Layout: Horizontal (Side-by-Side)", 3000)

    def _set_free_grid_layout(self):
        """Set free grid panel layout."""
        self.timeline_view.set_layout_mode(LayoutMode.FREE_GRID)
        self.vertical_layout_action.setChecked(False)
        self.horizontal_layout_action.setChecked(False)
        self.free_grid_layout_action.setChecked(True)
        self.statusBar().showMessage("Layout: Free Grid", 3000)

    def _toggle_edit_mode(self, enabled: bool):
        """Toggle layout editing mode."""
        self.timeline_view.set_edit_mode(enabled)
        mode = "enabled" if enabled else "disabled"
        self.statusBar().showMessage(f"Layout editing {mode}", 3000)

    def _lock_all_panels(self):
        """Lock all panels to prevent movement."""
        self.timeline_view.set_edit_mode(False)
        self.edit_layout_action.setChecked(False)
        self.statusBar().showMessage("All panels locked", 3000)

    def _save_layout(self):
        """Save current layout as a preset."""
        from PyQt6.QtWidgets import QInputDialog

        # Get preset name from user
        preset_name, ok = QInputDialog.getText(
            self,
            "Save Layout",
            "Enter a name for this layout preset:"
        )

        if ok and preset_name:
            # Get current layout
            layout_data = self.timeline_view.save_layout()

            # Save as preset
            if LayoutSerializer.save_preset(layout_data, preset_name):
                QMessageBox.information(
                    self,
                    "Layout Saved",
                    f"Layout '{preset_name}' saved successfully."
                )
                self.statusBar().showMessage(f"Layout '{preset_name}' saved", 3000)
            else:
                QMessageBox.warning(
                    self,
                    "Save Failed",
                    f"Failed to save layout '{preset_name}'."
                )

    def _load_layout(self):
        """Load a saved layout preset."""
        from PyQt6.QtWidgets import QInputDialog

        # Get list of available presets
        presets = LayoutSerializer.list_presets()

        if not presets:
            QMessageBox.information(
                self,
                "No Presets",
                "No saved layout presets found. Use 'Save Layout As...' to create one."
            )
            return

        # Let user select a preset
        preset_name, ok = QInputDialog.getItem(
            self,
            "Load Layout",
            "Select a layout preset to load:",
            presets,
            0,
            False
        )

        if ok and preset_name:
            # Load preset
            layout_data = LayoutSerializer.load_preset(preset_name)

            if layout_data:
                self.timeline_view.restore_layout(layout_data)
                QMessageBox.information(
                    self,
                    "Layout Loaded",
                    f"Layout '{preset_name}' loaded successfully."
                )
                self.statusBar().showMessage(f"Layout '{preset_name}' loaded", 3000)
            else:
                QMessageBox.warning(
                    self,
                    "Load Failed",
                    f"Failed to load layout '{preset_name}'."
                )

    def _reset_layout(self):
        """Reset layout to default."""
        reply = QMessageBox.question(
            self,
            "Reset Layout",
            "Reset panel layout to default? This will discard your current layout.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Get default layout based on current mode
            mode = self.timeline_view.get_layout_mode()

            if mode == LayoutMode.HORIZONTAL:
                layout_data = LayoutSerializer.create_default_horizontal_layout()
            else:
                layout_data = LayoutSerializer.create_default_vertical_layout()

            self.timeline_view.restore_layout(layout_data)
            self.statusBar().showMessage("Layout reset to default", 3000)

    def _show_grid_settings(self):
        """Show grid settings dialog."""
        from openpace.gui.dialogs.grid_settings_dialog import GridSettingsDialog

        # Create and show dialog
        dialog = GridSettingsDialog(self)
        if dialog.exec():
            # Settings were saved, apply them
            self.statusBar().showMessage("Grid settings updated", 3000)

    def _show_settings_window(self):
        """Show device settings in a separate window."""
        # Get current patient's most recent transmission
        current_patient_id = self.timeline_view.patient_selector.get_current_patient_id()

        if not current_patient_id:
            QMessageBox.information(
                self,
                "No Patient Selected",
                "Please select a patient first to view device settings."
            )
            return

        # Query most recent transmission
        most_recent_transmission = self.db_session.query(Transmission).filter_by(
            patient_id=current_patient_id
        ).order_by(Transmission.transmission_date.desc()).first()

        if not most_recent_transmission:
            QMessageBox.information(
                self,
                "No Data",
                "No transmission data available for this patient."
            )
            return

        # Create settings window
        settings_window = QWidget()
        settings_window.setWindowTitle(
            f"Device Settings - {most_recent_transmission.patient.patient_name}"
        )
        settings_window.setGeometry(150, 150, 700, 600)

        layout = QVBoxLayout()
        settings_window.setLayout(layout)

        # Create settings panel
        settings_panel = SettingsPanel()
        settings_panel.load_transmission(most_recent_transmission)
        layout.addWidget(settings_panel)

        # Add close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(settings_window.close)
        layout.addWidget(close_btn)

        # Show window
        settings_window.show()

        # Keep reference to prevent garbage collection
        if not hasattr(self, '_settings_windows'):
            self._settings_windows = []
        self._settings_windows.append(settings_window)

    def _show_about(self):
        """Show about dialog."""
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "About OpenPace",
            "<h2>OpenPace v0.1.0</h2>"
            "<p>Pacemaker Data Analysis & Visualization Platform</p>"
            "<p>Inspired by OSCAR for CPAP data</p>"
            "<p><b>Educational Use Only</b></p>"
            "<p>Built with Python & PyQt6</p>",
        )
