"""
Timeline View - OSCAR-Style Layout

Combines all trend widgets into a cohesive timeline visualization.
Displays battery, impedance, and burden trends in synchronized view.
"""

from typing import Optional, Dict, List
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QScrollArea, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from sqlalchemy.orm import Session

from openpace.database.models import Patient, Transmission, LongitudinalTrend
from openpace.processing.trend_calculator import TrendCalculator
from .battery_widget import BatteryTrendWidget
from .impedance_widget import ImpedanceTrendWidget
from .burden_widget import BurdenWidget


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

    OSCAR-style layout with stacked trend charts.
    """

    def __init__(self, db_session: Session, parent=None):
        super().__init__(parent)
        self.session = db_session
        self.current_patient_id = None

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Patient selector at top
        self.patient_selector = PatientSelectorWidget(self.session)
        self.patient_selector.patient_selected.connect(self.load_patient_data)
        layout.addWidget(self.patient_selector)

        # Scrollable area for charts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container for charts
        charts_container = QWidget()
        charts_layout = QVBoxLayout()
        charts_container.setLayout(charts_layout)

        # Battery trend
        battery_group = QGroupBox("Battery Voltage")
        battery_layout = QVBoxLayout()
        battery_group.setLayout(battery_layout)
        self.battery_widget = BatteryTrendWidget()
        battery_layout.addWidget(self.battery_widget)
        charts_layout.addWidget(battery_group)

        # Atrial impedance
        atrial_imp_group = QGroupBox("Atrial Lead Impedance")
        atrial_imp_layout = QVBoxLayout()
        atrial_imp_group.setLayout(atrial_imp_layout)
        self.atrial_impedance_widget = ImpedanceTrendWidget()
        atrial_imp_layout.addWidget(self.atrial_impedance_widget)
        charts_layout.addWidget(atrial_imp_group)

        # Ventricular impedance
        vent_imp_group = QGroupBox("Ventricular Lead Impedance")
        vent_imp_layout = QVBoxLayout()
        vent_imp_group.setLayout(vent_imp_layout)
        self.vent_impedance_widget = ImpedanceTrendWidget()
        vent_imp_layout.addWidget(self.vent_impedance_widget)
        charts_layout.addWidget(vent_imp_group)

        # AFib burden
        burden_group = QGroupBox("Arrhythmia Burden")
        burden_layout = QVBoxLayout()
        burden_group.setLayout(burden_layout)
        self.burden_widget = BurdenWidget()
        burden_layout.addWidget(self.burden_widget)
        charts_layout.addWidget(burden_group)

        scroll.setWidget(charts_container)
        layout.addWidget(scroll)

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
