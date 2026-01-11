"""
Lead Impedance Trend Widget

Displays lead impedance over time with anomaly detection markers.
Shows normal range bands and alerts for fractures/failures.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import pyqtgraph as pg
import numpy as np

from openpace.processing.trend_calculator import LeadImpedanceTrendAnalyzer


class ImpedanceTrendWidget(QWidget):
    """
    Widget displaying lead impedance trend over time.

    Features:
    - Line plot of impedance vs time
    - Normal range bands (200-1500 Ohms)
    - Anomaly markers (fractures, failures)
    - Stability score display
    - Multiple lead support (atrial, ventricular, LV)
    """

    NORMAL_MIN = 200  # Ohms
    NORMAL_MAX = 1500  # Ohms

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lead Impedance Trend")

        # Data
        self.time_points = []
        self.impedances = []
        self.lead_name = "Lead"
        self.anomalies = []
        self.stability_score = None

        # Setup UI
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Title
        self.title_label = QLabel("Lead Impedance Trend")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.title_label)

        # Info label (stability, anomalies)
        self.info_label = QLabel("No data")
        self.info_label.setStyleSheet("font-size: 11px; color: gray;")
        layout.addWidget(self.info_label)

        # Plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Axis labels
        self.plot_widget.setLabel('left', 'Impedance', units='Ohms')
        self.plot_widget.setLabel('bottom', 'Date')

        # Enable mouse interaction
        self.plot_widget.setMouseEnabled(x=True, y=False)

        layout.addWidget(self.plot_widget)

        # Legend
        self.plot_widget.addLegend()

    def set_data(self, lead_name: str, time_points: List[datetime], impedances: List[float]):
        """
        Set lead impedance data.

        Args:
            lead_name: Name of lead (e.g., "Atrial", "Ventricular", "LV")
            time_points: List of datetime objects
            impedances: List of impedance values (Ohms)
        """
        self.lead_name = lead_name
        self.time_points = time_points
        self.impedances = impedances

        # Update title
        self.title_label.setText(f"{lead_name} Lead Impedance Trend")

        # Convert datetimes to timestamps
        timestamps = [dt.timestamp() for dt in time_points]

        # Clear previous plots
        self.plot_widget.clear()

        if len(timestamps) == 0:
            self.info_label.setText("No data")
            return

        # Plot normal range bands
        self._plot_normal_range(timestamps)

        # Plot impedance line
        self._plot_impedance_line(timestamps, impedances)

        # Analyze for anomalies
        if len(impedances) >= 2:
            self._analyze_anomalies(time_points, impedances)
            self._plot_anomalies(timestamps)

        # Configure time axis
        self._configure_time_axis(timestamps)

        # Auto-range
        self.plot_widget.autoRange()

    def _plot_normal_range(self, timestamps: List[float]):
        """
        Plot normal impedance range as shaded area.

        Args:
            timestamps: X-axis values
        """
        if len(timestamps) < 2:
            return

        # Create fill between min and max
        fill = pg.FillBetweenItem(
            curve1=pg.PlotCurveItem([timestamps[0], timestamps[-1]], [self.NORMAL_MIN, self.NORMAL_MIN]),
            curve2=pg.PlotCurveItem([timestamps[0], timestamps[-1]], [self.NORMAL_MAX, self.NORMAL_MAX]),
            brush=(0, 255, 0, 30)  # Light green
        )
        self.plot_widget.addItem(fill)

        # Add range labels
        pen = pg.mkPen(color=(0, 150, 0), width=1, style=Qt.PenStyle.DashLine)
        self.plot_widget.plot(
            [timestamps[0], timestamps[-1]],
            [self.NORMAL_MIN, self.NORMAL_MIN],
            pen=pen,
            name='Normal Range'
        )
        self.plot_widget.plot(
            [timestamps[0], timestamps[-1]],
            [self.NORMAL_MAX, self.NORMAL_MAX],
            pen=pen
        )

    def _plot_impedance_line(self, timestamps: List[float], impedances: List[float]):
        """
        Plot impedance line with adaptive coloring.

        Args:
            timestamps: X-axis timestamps
            impedances: Impedance values
        """
        # Determine color based on current value
        current_imp = impedances[-1]

        if self.NORMAL_MIN <= current_imp <= self.NORMAL_MAX:
            color = (0, 150, 200)  # Blue - normal
        elif current_imp < self.NORMAL_MIN:
            color = (200, 100, 0)  # Orange - low (insulation failure)
        else:
            color = (200, 0, 0)  # Red - high (fracture)

        # Plot line
        pen = pg.mkPen(color=color, width=2)
        self.plot_widget.plot(
            timestamps,
            impedances,
            pen=pen,
            symbol='o',
            symbolSize=6,
            symbolBrush=color,
            name=f'{self.lead_name} Impedance'
        )

    def _analyze_anomalies(self, time_points: List[datetime], impedances: List[float]):
        """
        Analyze impedance for anomalies.

        Args:
            time_points: Datetime objects
            impedances: Impedance values
        """
        # Create mock trend object
        from openpace.database.models import LongitudinalTrend

        trend = LongitudinalTrend()
        trend.variable_name = f'lead_impedance_{self.lead_name.lower()}'
        trend.time_points = [dt.isoformat() for dt in time_points]
        trend.values = impedances

        try:
            # Detect anomalies
            self.anomalies = LeadImpedanceTrendAnalyzer.detect_anomalies(trend)

            # Calculate stability score
            self.stability_score = LeadImpedanceTrendAnalyzer.calculate_stability_score(trend)

            # Update info label
            current_imp = impedances[-1]
            info_parts = [f"Current: {current_imp:.0f} Ohms"]

            if self.stability_score is not None:
                info_parts.append(f"Stability: {self.stability_score:.0f}/100")

            if self.anomalies:
                info_parts.append(f"⚠ {len(self.anomalies)} anomalies detected")

            self.info_label.setText("  |  ".join(info_parts))

        except Exception as e:
            print(f"Error analyzing impedance: {e}")
            self.anomalies = []
            self.stability_score = None

    def _plot_anomalies(self, timestamps: List[float]):
        """
        Plot anomaly markers on the chart.

        Args:
            timestamps: X-axis timestamps
        """
        if not self.anomalies:
            return

        for anomaly in self.anomalies:
            try:
                # Parse anomaly timestamp
                anomaly_dt = datetime.fromisoformat(anomaly['timestamp'])
                anomaly_ts = anomaly_dt.timestamp()

                # Find closest data point
                closest_idx = min(range(len(timestamps)),
                                key=lambda i: abs(timestamps[i] - anomaly_ts))

                if closest_idx < len(self.impedances):
                    # Determine marker style based on type
                    if anomaly['type'] == 'possible_fracture':
                        symbol = 't'  # Triangle up
                        color = (200, 0, 0)  # Red
                        size = 12
                    else:  # insulation failure
                        symbol = 't1'  # Triangle down
                        color = (200, 100, 0)  # Orange
                        size = 12

                    # Plot marker
                    scatter = pg.ScatterPlotItem(
                        [anomaly_ts],
                        [self.impedances[closest_idx]],
                        symbol=symbol,
                        size=size,
                        brush=color,
                        pen=pg.mkPen(color=(255, 255, 255), width=2)
                    )
                    self.plot_widget.addItem(scatter)

            except Exception as e:
                print(f"Error plotting anomaly: {e}")

    def _configure_time_axis(self, timestamps: List[float]):
        """
        Configure X-axis to display dates properly.

        Args:
            timestamps: Unix timestamps
        """
        axis = pg.DateAxisItem(orientation='bottom')
        self.plot_widget.setAxisItems({'bottom': axis})

    def clear(self):
        """Clear all data and plots."""
        self.time_points = []
        self.impedances = []
        self.anomalies = []
        self.stability_score = None
        self.plot_widget.clear()
        self.info_label.setText("No data")
