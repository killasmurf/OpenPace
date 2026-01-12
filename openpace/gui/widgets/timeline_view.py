"""
Timeline View - OSCAR-Style Layout

Combines all trend widgets into a cohesive timeline visualization.
Displays battery, impedance, and burden trends in synchronized view.
Supports collapsible panels and size adjustment.
"""

from typing import Optional, Dict, List
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QScrollArea, QGroupBox,
    QSplitter, QToolButton, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon
from sqlalchemy.orm import Session

from openpace.database.models import Patient, Transmission, LongitudinalTrend
from openpace.processing.trend_calculator import TrendCalculator
from .battery_widget import BatteryTrendWidget
from .impedance_widget import ImpedanceTrendWidget
from .burden_widget import BurdenWidget
from .settings_panel import SettingsPanel


class CollapsiblePanel(QWidget):
    """
    A collapsible panel that can be expanded/collapsed.

    Signals:
        visibility_changed: Emitted when panel is shown/hidden
    """

    visibility_changed = pyqtSignal(bool)  # True if visible

    def __init__(self, title: str, content_widget: QWidget, parent=None):
        super().__init__(parent)
        self.title = title
        self.content_widget = content_widget
        self.is_collapsed = False

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # Header with collapse button
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #e0e0e0;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
        """)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 5)
        header.setLayout(header_layout)

        # Collapse/expand button
        self.collapse_btn = QToolButton()
        self.collapse_btn.setText("▼")
        self.collapse_btn.setCheckable(True)
        self.collapse_btn.setChecked(False)
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        self.collapse_btn.setFixedSize(20, 20)
        header_layout.addWidget(self.collapse_btn)

        # Title label
        title_label = QLabel(self.title)
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Close button
        self.close_btn = QToolButton()
        self.close_btn.setText("✕")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.clicked.connect(self.hide_panel)
        header_layout.addWidget(self.close_btn)

        layout.addWidget(header)

        # Content container
        self.content_container = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(5, 5, 5, 5)
        self.content_container.setLayout(content_layout)
        content_layout.addWidget(self.content_widget)

        layout.addWidget(self.content_container)

    def toggle_collapse(self):
        """Toggle the collapsed state."""
        self.is_collapsed = self.collapse_btn.isChecked()

        if self.is_collapsed:
            self.content_container.hide()
            self.collapse_btn.setText("▶")
        else:
            self.content_container.show()
            self.collapse_btn.setText("▼")

    def hide_panel(self):
        """Hide the entire panel."""
        self.hide()
        self.visibility_changed.emit(False)

    def show_panel(self):
        """Show the panel."""
        self.show()
        self.visibility_changed.emit(True)

    def set_collapsed(self, collapsed: bool):
        """Set the collapsed state programmatically."""
        if collapsed != self.is_collapsed:
            self.collapse_btn.setChecked(collapsed)
            self.toggle_collapse()


class PatientSelectorWidget(QWidget):
    """
    Patient and date range selector widget.

    Signals:
        patient_selected: Emitted when patient selection changes
    """

    patient_selected = pyqtSignal(str)  # patient_id

    def __init__(self, db_session: Session, parent=None):
        super().__init__(parent)
        self.session = db_session
        self.current_patient_id = None

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QHBoxLayout()
        self.setLayout(layout)

        # Patient selector
        layout.addWidget(QLabel("Patient:"))

        self.patient_combo = QComboBox()
        self.patient_combo.currentIndexChanged.connect(self._on_patient_changed)
        layout.addWidget(self.patient_combo)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_patients)
        layout.addWidget(self.refresh_btn)

        layout.addStretch()

        # Load initial patient list
        self.load_patients()

    def load_patients(self):
        """Load patient list from database."""
        self.patient_combo.clear()

        try:
            patients = self.session.query(Patient).all()

            for patient in patients:
                display_name = patient.anonymized_id if patient.anonymized else patient.patient_name
                self.patient_combo.addItem(display_name, patient.patient_id)

            if patients:
                self.patient_combo.setCurrentIndex(0)

        except Exception as e:
            print(f"Error loading patients: {e}")

    def _on_patient_changed(self, index: int):
        """Handle patient selection change."""
        if index >= 0:
            patient_id = self.patient_combo.itemData(index)
            if patient_id:
                self.current_patient_id = patient_id
                self.patient_selected.emit(patient_id)

    def get_current_patient_id(self) -> Optional[str]:
        """Get currently selected patient ID."""
        return self.current_patient_id


class TimelineView(QWidget):
    """
    Main timeline view widget.

    OSCAR-style layout with collapsible, resizable trend panels.
    """

    # Signals for panel visibility changes (for menu synchronization)
    battery_visibility_changed = pyqtSignal(bool)
    atrial_impedance_visibility_changed = pyqtSignal(bool)
    vent_impedance_visibility_changed = pyqtSignal(bool)
    burden_visibility_changed = pyqtSignal(bool)
    settings_visibility_changed = pyqtSignal(bool)

    def __init__(self, db_session: Session, parent=None):
        super().__init__(parent)
        self.session = db_session
        self.current_patient_id = None

        # Dictionary to track panels
        self.panels = {}

        # Current orientation
        self.current_orientation = Qt.Orientation.Vertical

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)

        # Patient selector at top
        self.patient_selector = PatientSelectorWidget(self.session)
        self.patient_selector.patient_selected.connect(self.load_patient_data)
        layout.addWidget(self.patient_selector)

        # Splitter for resizable panels
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(4)
        self.splitter.setChildrenCollapsible(False)

        # Create trend widgets
        self.battery_widget = BatteryTrendWidget()
        self.atrial_impedance_widget = ImpedanceTrendWidget()
        self.vent_impedance_widget = ImpedanceTrendWidget()
        self.burden_widget = BurdenWidget()
        self.settings_panel = SettingsPanel()

        # Create collapsible panels
        self.battery_panel = CollapsiblePanel("Battery Voltage", self.battery_widget)
        self.battery_panel.visibility_changed.connect(self.battery_visibility_changed.emit)
        self.panels['battery'] = self.battery_panel
        self.splitter.addWidget(self.battery_panel)

        self.atrial_panel = CollapsiblePanel("Atrial Lead Impedance", self.atrial_impedance_widget)
        self.atrial_panel.visibility_changed.connect(self.atrial_impedance_visibility_changed.emit)
        self.panels['atrial_impedance'] = self.atrial_panel
        self.splitter.addWidget(self.atrial_panel)

        self.vent_panel = CollapsiblePanel("Ventricular Lead Impedance", self.vent_impedance_widget)
        self.vent_panel.visibility_changed.connect(self.vent_impedance_visibility_changed.emit)
        self.panels['vent_impedance'] = self.vent_panel
        self.splitter.addWidget(self.vent_panel)

        self.burden_panel = CollapsiblePanel("Arrhythmia Burden", self.burden_widget)
        self.burden_panel.visibility_changed.connect(self.burden_visibility_changed.emit)
        self.panels['burden'] = self.burden_panel
        self.splitter.addWidget(self.burden_panel)

        self.settings_panel_widget = CollapsiblePanel("Device Settings", self.settings_panel)
        self.settings_panel_widget.visibility_changed.connect(self.settings_visibility_changed.emit)
        self.panels['settings'] = self.settings_panel_widget
        self.splitter.addWidget(self.settings_panel_widget)

        # Set initial sizes (equal distribution)
        sizes = [200] * 5
        self.splitter.setSizes(sizes)

        layout.addWidget(self.splitter)

    def show_panel(self, panel_name: str):
        """Show a specific panel by name."""
        if panel_name in self.panels:
            self.panels[panel_name].show_panel()

    def hide_panel(self, panel_name: str):
        """Hide a specific panel by name."""
        if panel_name in self.panels:
            self.panels[panel_name].hide_panel()

    def toggle_panel(self, panel_name: str, visible: bool):
        """Toggle panel visibility."""
        if visible:
            self.show_panel(panel_name)
        else:
            self.hide_panel(panel_name)

    def set_orientation(self, orientation: Qt.Orientation):
        """
        Change the orientation of the panel layout.

        Args:
            orientation: Qt.Orientation.Vertical or Qt.Orientation.Horizontal
        """
        if orientation == self.current_orientation:
            return

        self.current_orientation = orientation

        # Get current panel sizes before changing orientation
        current_sizes = self.splitter.sizes()

        # Change splitter orientation
        self.splitter.setOrientation(orientation)

        # Restore sizes (they'll be applied to the new orientation)
        if len(current_sizes) == 5:
            self.splitter.setSizes(current_sizes)

    def load_patient_data(self, patient_id: str):
        """
        Load and display data for selected patient.

        Args:
            patient_id: Patient identifier
        """
        self.current_patient_id = patient_id

        try:
            # Query trends for this patient
            trends = self.session.query(LongitudinalTrend).filter_by(
                patient_id=patient_id
            ).all()

            # If no trends, calculate them
            if not trends:
                print(f"No pre-computed trends found, calculating...")
                calculator = TrendCalculator(self.session)
                trends = calculator.calculate_all_trends(patient_id)

            # Organize trends by variable
            trends_by_var = {t.variable_name: t for t in trends}

            # Load battery trend
            if 'battery_voltage' in trends_by_var:
                trend = trends_by_var['battery_voltage']
                time_points = [datetime.fromisoformat(tp) for tp in trend.time_points]
                self.battery_widget.set_data(time_points, trend.values)

            # Load atrial impedance
            if 'lead_impedance_atrial' in trends_by_var:
                trend = trends_by_var['lead_impedance_atrial']
                time_points = [datetime.fromisoformat(tp) for tp in trend.time_points]
                self.atrial_impedance_widget.set_data("Atrial", time_points, trend.values)

            # Load ventricular impedance
            if 'lead_impedance_ventricular' in trends_by_var:
                trend = trends_by_var['lead_impedance_ventricular']
                time_points = [datetime.fromisoformat(tp) for tp in trend.time_points]
                self.vent_impedance_widget.set_data("Ventricular", time_points, trend.values)

            # Load AFib burden
            if 'afib_burden_percent' in trends_by_var:
                trend = trends_by_var['afib_burden_percent']
                time_points = [datetime.fromisoformat(tp) for tp in trend.time_points]
                self.burden_widget.set_data("AFib", time_points, trend.values)

            # Load device settings from most recent transmission
            most_recent_transmission = self.session.query(Transmission).filter_by(
                patient_id=patient_id
            ).order_by(Transmission.transmission_date.desc()).first()

            if most_recent_transmission:
                self.settings_panel.load_transmission(most_recent_transmission)
            else:
                self.settings_panel.clear()

        except Exception as e:
            print(f"Error loading patient data: {e}")
            import traceback
            traceback.print_exc()

    def clear_all(self):
        """Clear all chart data."""
        self.battery_widget.clear()
        self.atrial_impedance_widget.clear()
        self.vent_impedance_widget.clear()
        self.burden_widget.clear()
        self.settings_panel.clear()
