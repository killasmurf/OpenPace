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
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction


class MainWindow(QMainWindow):
    """
    Main application window for OpenPace.

    Provides the OSCAR-style interface with timeline and episode viewers.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OpenPace - Pacemaker Data Analyzer")
        self.setGeometry(100, 100, 1400, 900)

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

        timeline_action = QAction("&Timeline View", self)
        timeline_action.setCheckable(True)
        timeline_action.setChecked(True)
        view_menu.addAction(timeline_action)

        episode_action = QAction("&Episode Viewer", self)
        episode_action.setCheckable(True)
        episode_action.setChecked(True)
        view_menu.addAction(episode_action)

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
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Placeholder welcome message
        welcome_label = QLabel("Welcome to OpenPace")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("font-size: 24px; font-weight: bold; padding: 50px;")
        layout.addWidget(welcome_label)

        info_label = QLabel(
            "Pacemaker Data Analysis & Visualization Platform\n\n"
            "Click 'Import Data' to load HL7 ORU^R01 messages"
        )
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("font-size: 14px; color: gray;")
        layout.addWidget(info_label)

    def _create_status_bar(self):
        """Create the status bar."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage("Ready")

    # Slot methods
    def _import_data(self):
        """Handle data import action."""
        self.statusBar().showMessage("Import data functionality coming soon...")

    def _toggle_anonymization(self, checked):
        """Toggle anonymization mode."""
        mode = "ON" if checked else "OFF"
        self.statusBar().showMessage(f"Anonymization mode: {mode}")

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
