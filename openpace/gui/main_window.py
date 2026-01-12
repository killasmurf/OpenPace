"""
OpenPace Main Window

The primary application window for OpenPace, featuring:
- Patient selector
- Timeline view (macro)
- Episode viewer (micro)
- Menu bar and toolbars
"""

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

    def _create_status_bar(self):
        """Create the status bar."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage("Ready")

    # Slot methods
    def _import_data(self):
        """Handle data import action."""
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import HL7 Data",
            "",
            "HL7 Files (*.hl7);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Read HL7 file
            with open(file_path, 'r') as f:
                hl7_message = f.read()

            # Parse HL7 message
            parser = HL7Parser(self.db_session, anonymize=False)
            transmission = parser.parse_message(hl7_message, filename=file_path)

            # Show success message
            QMessageBox.information(
                self,
                "Import Successful",
                f"Successfully imported transmission {transmission.transmission_id}\n"
                f"Patient: {transmission.patient.patient_name}\n"
                f"Observations: {len(transmission.observations)}"
            )

            # Refresh timeline view
            self.timeline_view.patient_selector.load_patients()

            self.statusBar().showMessage(f"Imported: {file_path}", 5000)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Import Error",
                f"Failed to import HL7 file:\n{str(e)}"
            )
            self.statusBar().showMessage("Import failed", 5000)

    def _toggle_anonymization(self, checked):
        """Toggle anonymization mode."""
        mode = "ON" if checked else "OFF"
        self.statusBar().showMessage(f"Anonymization mode: {mode}")

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
