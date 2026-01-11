"""
EGM Window

Combined window for browsing and viewing electrogram episodes.
Integrates episode selector and EGM viewer in a single interface.
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QSplitter, QMenuBar, QMenu, QStatusBar)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from sqlalchemy.orm import Session

from openpace.gui.widgets.episode_selector import EpisodeSelectorWidget
from openpace.gui.widgets.egm_viewer import EGMViewerWidget


class EGMWindow(QMainWindow):
    """
    Main window for EGM episode viewing.

    Combines episode list selector with interactive waveform viewer.
    Provides tools for measurement, annotation, and export.
    """

    def __init__(self, session: Session = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OpenPace - EGM Viewer")
        self.setGeometry(100, 100, 1400, 800)

        # Data
        self.session = session
        self.current_patient_id = None

        # Setup UI
        self._init_ui()
        self._create_menu_bar()

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _init_ui(self):
        """Initialize the user interface."""
        # Central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout()
        central_widget.setLayout(layout)

        # Horizontal splitter (episode list | viewer)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left: Episode selector
        self.episode_selector = EpisodeSelectorWidget()
        self.episode_selector.episode_selected.connect(self._on_episode_selected)
        if self.session:
            self.episode_selector.set_session(self.session)
        splitter.addWidget(self.episode_selector)

        # Right: EGM viewer
        self.egm_viewer = EGMViewerWidget()
        splitter.addWidget(self.egm_viewer)

        # Set splitter proportions (30% list, 70% viewer)
        splitter.setSizes([300, 900])

    def _create_menu_bar(self):
        """Create menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        load_action = QAction("&Load Patient", self)
        load_action.triggered.connect(self._load_patient)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        export_action = QAction("&Export Image", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.egm_viewer._export_image)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        close_action = QAction("&Close", self)
        close_action.setShortcut("Ctrl+W")
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.egm_viewer._zoom_in)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.egm_viewer._zoom_out)
        view_menu.addAction(zoom_out_action)

        zoom_reset_action = QAction("&Reset Zoom", self)
        zoom_reset_action.setShortcut("Ctrl+0")
        zoom_reset_action.triggered.connect(self.egm_viewer._zoom_reset)
        view_menu.addAction(zoom_reset_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        add_caliper_action = QAction("Add &Caliper", self)
        add_caliper_action.setShortcut("Ctrl+L")
        add_caliper_action.triggered.connect(self.egm_viewer._add_caliper)
        tools_menu.addAction(add_caliper_action)

        clear_calipers_action = QAction("&Clear Calipers", self)
        clear_calipers_action.triggered.connect(self.egm_viewer._clear_calipers)
        tools_menu.addAction(clear_calipers_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def set_session(self, session: Session):
        """
        Set database session.

        Args:
            session: SQLAlchemy session
        """
        self.session = session
        self.episode_selector.set_session(session)

    def load_patient(self, patient_id: str):
        """
        Load episodes for a patient.

        Args:
            patient_id: Patient identifier
        """
        self.current_patient_id = patient_id
        self.episode_selector.load_episodes(patient_id)
        self.status_bar.showMessage(f"Loaded episodes for patient: {patient_id}")

    def _on_episode_selected(self, observation):
        """Handle episode selection."""
        try:
            self.egm_viewer.load_egm(observation)
            trans_date = observation.transmission.transmission_date
            self.status_bar.showMessage(
                f"Viewing episode from {trans_date.strftime('%Y-%m-%d %H:%M')}"
            )
        except Exception as e:
            self.status_bar.showMessage(f"Error loading episode: {str(e)}")

    def _load_patient(self):
        """Show patient selection dialog (placeholder)."""
        from PyQt6.QtWidgets import QInputDialog

        patient_id, ok = QInputDialog.getText(
            self,
            "Load Patient",
            "Enter Patient ID:"
        )

        if ok and patient_id:
            self.load_patient(patient_id)

    def _show_about(self):
        """Show about dialog."""
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "About EGM Viewer",
            "<h3>OpenPace EGM Viewer</h3>"
            "<p>Interactive electrogram waveform viewer for pacemaker data analysis.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>High-resolution waveform display</li>"
            "<li>R-peak detection and marking</li>"
            "<li>RR interval tachogram</li>"
            "<li>Measurement calipers</li>"
            "<li>Signal filtering controls</li>"
            "<li>Export capabilities</li>"
            "</ul>"
            "<p><i>Version 1.0 - Educational Use Only</i></p>"
        )
