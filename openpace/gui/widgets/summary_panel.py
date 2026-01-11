"""
Statistical Summary Panel Widget

Displays comprehensive statistical summaries and clinical recommendations
for battery, lead impedance, and arrhythmia burden analyses.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QGroupBox, QScrollArea, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from openpace.database.models import LongitudinalTrend
from openpace.analysis.battery_analyzer import BatteryAnalyzer
from openpace.analysis.impedance_analyzer import ImpedanceAnalyzer
from openpace.analysis.arrhythmia_analyzer import ArrhythmiaAnalyzer


class SummaryPanel(QWidget):
    """
    Statistical summary panel displaying key metrics and recommendations.

    Shows analysis results for battery, leads, and arrhythmia burden with
    color-coded status indicators and clinical recommendations.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Device Summary")

        # Data
        self.patient_name = None
        self.last_transmission = None

        # Setup UI
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Patient info header
        self.patient_label = QLabel("No patient selected")
        self.patient_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(self.patient_label)

        self.date_label = QLabel("")
        self.date_label.setStyleSheet("font-size: 11px; color: gray; padding: 2px;")
        layout.addWidget(self.date_label)

        # Scroll area for summary content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout()
        scroll_content.setLayout(self.scroll_layout)
        scroll.setWidget(scroll_content)

        layout.addWidget(scroll)

        # Summary sections
        self.battery_group = self._create_battery_section()
        self.scroll_layout.addWidget(self.battery_group)

        self.leads_group = self._create_leads_section()
        self.scroll_layout.addWidget(self.leads_group)

        self.arrhythmia_group = self._create_arrhythmia_section()
        self.scroll_layout.addWidget(self.arrhythmia_group)

        self.scroll_layout.addStretch()

    def _create_battery_section(self) -> QGroupBox:
        """Create battery status section."""
        group = QGroupBox("Battery Status")
        layout = QVBoxLayout()
        group.setLayout(layout)

        self.battery_voltage_label = QLabel("--")
        self.battery_eri_label = QLabel("--")
        self.battery_depletion_label = QLabel("--")
        self.battery_recommendation_label = QLabel("--")

        self._add_metric_row(layout, "Current Voltage:", self.battery_voltage_label)
        self._add_metric_row(layout, "Years to ERI:", self.battery_eri_label)
        self._add_metric_row(layout, "Depletion Rate:", self.battery_depletion_label)
        self._add_recommendation_row(layout, self.battery_recommendation_label)

        return group

    def _create_leads_section(self) -> QGroupBox:
        """Create lead status section."""
        group = QGroupBox("Lead Status")
        layout = QVBoxLayout()
        group.setLayout(layout)

        self.lead_atrial_label = QLabel("--")
        self.lead_ventricular_label = QLabel("--")
        self.lead_lv_label = QLabel("--")
        self.lead_anomaly_label = QLabel("--")

        self._add_metric_row(layout, "Atrial:", self.lead_atrial_label)
        self._add_metric_row(layout, "Ventricular:", self.lead_ventricular_label)
        self._add_metric_row(layout, "LV:", self.lead_lv_label)
        self._add_recommendation_row(layout, self.lead_anomaly_label)

        return group

    def _create_arrhythmia_section(self) -> QGroupBox:
        """Create arrhythmia burden section."""
        group = QGroupBox("Arrhythmia Burden")
        layout = QVBoxLayout()
        group.setLayout(layout)

        self.burden_current_label = QLabel("--")
        self.burden_mean_label = QLabel("--")
        self.burden_trend_label = QLabel("--")
        self.burden_recommendation_label = QLabel("--")

        self._add_metric_row(layout, "Current:", self.burden_current_label)
        self._add_metric_row(layout, "Mean:", self.burden_mean_label)
        self._add_metric_row(layout, "Trend:", self.burden_trend_label)
        self._add_recommendation_row(layout, self.burden_recommendation_label)

        return group

    def _add_metric_row(self, layout: QVBoxLayout, label_text: str, value_label: QLabel):
        """Add a metric row to the layout."""
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setStyleSheet("font-weight: bold;")
        label.setMinimumWidth(120)
        row.addWidget(label)
        row.addWidget(value_label)
        row.addStretch()
        layout.addLayout(row)

    def _add_recommendation_row(self, layout: QVBoxLayout, value_label: QLabel):
        """Add a recommendation row."""
        layout.addWidget(QLabel("Recommendation:"))
        value_label.setWordWrap(True)
        value_label.setStyleSheet("padding: 5px; border-left: 3px solid #999; margin-left: 10px;")
        layout.addWidget(value_label)
        layout.addSpacing(10)

    def update_patient_info(self, patient_name: str, last_transmission: Optional[datetime] = None):
        """Update patient information header."""
        self.patient_name = patient_name
        self.last_transmission = last_transmission

        self.patient_label.setText(f"Patient: {patient_name}")

        if last_transmission:
            self.date_label.setText(
                f"Last Transmission: {last_transmission.strftime('%Y-%m-%d %H:%M')}"
            )
        else:
            self.date_label.setText("No transmissions")

    def update_battery_analysis(self, trend: LongitudinalTrend):
        """Update battery section with analysis results."""
        try:
            analysis = BatteryAnalyzer.analyze_depletion(trend)

            if 'error' in analysis:
                self._set_error_state(self.battery_voltage_label, analysis['error'])
                return

            # Current voltage with color coding
            voltage = analysis['current_voltage']
            color = BatteryAnalyzer.get_status_color(voltage)
            self.battery_voltage_label.setText(
                f"<span style='color: {color}; font-weight: bold;'>{voltage:.2f}V</span>"
            )

            # Years to ERI
            years_to_eri = analysis.get('years_to_eri')
            if years_to_eri:
                if years_to_eri < 0:
                    self.battery_eri_label.setText(
                        "<span style='color: red; font-weight: bold;'>ERI REACHED</span>"
                    )
                else:
                    self.battery_eri_label.setText(f"{years_to_eri:.1f} years")
            else:
                self.battery_eri_label.setText("N/A")

            # Depletion rate
            depletion = analysis['depletion_rate_v_per_year']
            self.battery_depletion_label.setText(f"{abs(depletion):.3f} V/year")

            # Recommendation
            recommendation = BatteryAnalyzer.get_recommendation(analysis)
            self._set_recommendation(self.battery_recommendation_label, recommendation, color)

        except Exception as e:
            self._set_error_state(self.battery_voltage_label, str(e))

    def update_lead_analysis(self, trends: Dict[str, LongitudinalTrend]):
        """Update lead section with analysis results."""
        try:
            atrial_trend = trends.get('lead_impedance_atrial')
            ventricular_trend = trends.get('lead_impedance_ventricular')
            lv_trend = trends.get('lead_impedance_lv')

            # Analyze each lead
            if atrial_trend:
                analysis = ImpedanceAnalyzer.analyze_trend(atrial_trend)
                self._update_lead_display(
                    self.lead_atrial_label,
                    analysis,
                    "Atrial"
                )
            else:
                self.lead_atrial_label.setText("No data")

            if ventricular_trend:
                analysis = ImpedanceAnalyzer.analyze_trend(ventricular_trend)
                self._update_lead_display(
                    self.lead_ventricular_label,
                    analysis,
                    "Ventricular"
                )
            else:
                self.lead_ventricular_label.setText("No data")

            if lv_trend:
                analysis = ImpedanceAnalyzer.analyze_trend(lv_trend)
                self._update_lead_display(
                    self.lead_lv_label,
                    analysis,
                    "LV"
                )
            else:
                self.lead_lv_label.setText("No data")

            # Overall anomaly status
            all_anomalies = []
            for trend in [atrial_trend, ventricular_trend, lv_trend]:
                if trend:
                    all_anomalies.extend(ImpedanceAnalyzer.detect_anomalies(trend))

            if all_anomalies:
                critical_count = len([a for a in all_anomalies if a['severity'] == 'critical'])
                if critical_count > 0:
                    self._set_recommendation(
                        self.lead_anomaly_label,
                        f"CRITICAL: {critical_count} lead anomalies detected. Review immediately.",
                        'red'
                    )
                else:
                    self._set_recommendation(
                        self.lead_anomaly_label,
                        f"{len(all_anomalies)} anomalies detected. Monitor closely.",
                        'orange'
                    )
            else:
                self._set_recommendation(
                    self.lead_anomaly_label,
                    "All leads functioning normally.",
                    'green'
                )

        except Exception as e:
            self._set_error_state(self.lead_atrial_label, str(e))

    def _update_lead_display(self, label: QLabel, analysis: Dict[str, Any], lead_name: str):
        """Update individual lead display."""
        impedance = analysis['current_impedance']
        stability = analysis['stability']
        status = analysis['overall_status']

        # Color based on status
        color_map = {
            'normal': 'green',
            'monitor': 'orange',
            'warning': 'orange',
            'critical': 'red'
        }
        color = color_map.get(status, 'black')

        label.setText(
            f"<span style='color: {color};'>{impedance:.0f} Ohms "
            f"(Stability: {stability['score']:.0f})</span>"
        )

    def update_arrhythmia_analysis(self, trend: LongitudinalTrend):
        """Update arrhythmia section with analysis results."""
        try:
            analysis = ArrhythmiaAnalyzer.calculate_burden_statistics(trend)

            if 'error' in analysis:
                self._set_error_state(self.burden_current_label, analysis['error'])
                return

            # Current burden with color
            current = analysis['current_burden']
            color = self._get_burden_color(current)
            self.burden_current_label.setText(
                f"<span style='color: {color}; font-weight: bold;'>{current:.1f}%</span>"
            )

            # Mean burden
            mean = analysis['mean_burden']
            self.burden_mean_label.setText(f"{mean:.1f}%")

            # Trend
            trend_dir = analysis['trend']['direction']
            trend_icon = {'increasing': '↑', 'decreasing': '↓', 'stable': '→'}.get(trend_dir, '?')
            self.burden_trend_label.setText(f"{trend_icon} {trend_dir.title()}")

            # Recommendation
            recommendation = ArrhythmiaAnalyzer.get_recommendation(analysis)
            self._set_recommendation(self.burden_recommendation_label, recommendation, color)

        except Exception as e:
            self._set_error_state(self.burden_current_label, str(e))

    def _get_burden_color(self, burden: float) -> str:
        """Get color for burden level."""
        if burden < ArrhythmiaAnalyzer.LOW_BURDEN:
            return 'green'
        elif burden < ArrhythmiaAnalyzer.MODERATE_BURDEN:
            return 'orange'
        else:
            return 'red'

    def _set_recommendation(self, label: QLabel, text: str, color: str):
        """Set recommendation text with color."""
        label.setText(text)
        label.setStyleSheet(
            f"padding: 5px; border-left: 3px solid {color}; "
            f"margin-left: 10px; background-color: rgba(0,0,0,0.05);"
        )

    def _set_error_state(self, label: QLabel, error_msg: str):
        """Set error state for a label."""
        label.setText(f"<span style='color: gray;'>Error: {error_msg}</span>")

    def clear(self):
        """Clear all summary data."""
        self.patient_label.setText("No patient selected")
        self.date_label.setText("")

        for label in [self.battery_voltage_label, self.battery_eri_label,
                     self.battery_depletion_label, self.battery_recommendation_label,
                     self.lead_atrial_label, self.lead_ventricular_label,
                     self.lead_lv_label, self.lead_anomaly_label,
                     self.burden_current_label, self.burden_mean_label,
                     self.burden_trend_label, self.burden_recommendation_label]:
            label.setText("--")
