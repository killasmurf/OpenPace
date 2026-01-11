"""
Battery Voltage Trend Widget

Displays battery voltage over time with ERI prediction overlay.
OSCAR-style timeline visualization.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import numpy as np

from openpace.processing.trend_calculator import BatteryTrendAnalyzer


class BatteryTrendWidget(QWidget):
    """
    Widget displaying battery voltage trend over time.

    Features:
    - Line plot of voltage vs time
    - ERI threshold line (2.2V)
    - Predicted ERI date marker
    - Color coding (green → yellow → red as approaches ERI)
    - Depletion rate annotation
    """

    ERI_THRESHOLD = 2.2  # Volts

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Battery Voltage Trend")

        # Data
        self.time_points = []
        self.voltages = []
        self.eri_prediction = None

        # Setup UI
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Title
        self.title_label = QLabel("Battery Voltage Trend")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.title_label)

        # Info label (depletion rate, ERI prediction)
        self.info_label = QLabel("No data")
        self.info_label.setStyleSheet("font-size: 11px; color: gray;")
        layout.addWidget(self.info_label)

        # Plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Axis labels
        self.plot_widget.setLabel('left', 'Battery Voltage', units='V')
        self.plot_widget.setLabel('bottom', 'Date')

        # Enable mouse interaction
        self.plot_widget.setMouseEnabled(x=True, y=False)

        layout.addWidget(self.plot_widget)

        # Legend
        self.plot_widget.addLegend()

        # Set default time range (2020 to current date)
        self._set_default_time_range()

    def set_data(self, time_points: List[datetime], voltages: List[float]):
        """
        Set battery voltage data.

        Args:
            time_points: List of datetime objects
            voltages: List of voltage values (Volts)
        """
        self.time_points = time_points
        self.voltages = voltages

        # Convert datetimes to timestamps for plotting
        timestamps = [dt.timestamp() for dt in time_points]

        # Clear previous plots
        self.plot_widget.clear()

        if len(timestamps) == 0:
            self.info_label.setText("No data")
            return

        # Create voltage line with color gradient
        self._plot_voltage_line(timestamps, voltages)

        # Add ERI threshold line
        self._plot_eri_threshold(timestamps)

        # Calculate and display ERI prediction
        if len(voltages) >= 3:
            self._calculate_eri_prediction(time_points, voltages)
            self._plot_eri_prediction(timestamps)

        # Configure time axis
        self._configure_time_axis(timestamps)

        # Set X-axis range with 10% extension on either side
        self._set_time_range_with_padding(timestamps)

    def _plot_voltage_line(self, timestamps: List[float], voltages: List[float]):
        """
        Plot battery voltage line with color coding.

        Green → Yellow → Red as voltage approaches ERI.
        """
        # Determine color based on current voltage
        current_voltage = voltages[-1]

        if current_voltage >= 2.5:
            color = (0, 200, 0)  # Green
        elif current_voltage >= 2.3:
            color = (200, 150, 0)  # Yellow/Orange
        else:
            color = (200, 0, 0)  # Red

        # Plot line
        pen = pg.mkPen(color=color, width=2)
        self.plot_widget.plot(
            timestamps,
            voltages,
            pen=pen,
            symbol='o',
            symbolSize=6,
            symbolBrush=color,
            name='Battery Voltage'
        )

    def _plot_eri_threshold(self, timestamps: List[float]):
        """
        Plot horizontal ERI threshold line.

        Args:
            timestamps: X-axis values for line extent
        """
        if len(timestamps) < 2:
            return

        # Horizontal line at ERI threshold
        pen = pg.mkPen(color=(200, 0, 0), width=2, style=Qt.PenStyle.DashLine)
        self.plot_widget.plot(
            [timestamps[0], timestamps[-1]],
            [self.ERI_THRESHOLD, self.ERI_THRESHOLD],
            pen=pen,
            name='ERI Threshold (2.2V)'
        )

    def _calculate_eri_prediction(self, time_points: List[datetime], voltages: List[float]):
        """
        Calculate ERI prediction using BatteryTrendAnalyzer.

        Args:
            time_points: Datetime objects
            voltages: Voltage values
        """
        # Create a mock trend object for analyzer
        from openpace.database.models import LongitudinalTrend

        trend = LongitudinalTrend()
        trend.variable_name = 'battery_voltage'
        trend.time_points = [dt.isoformat() for dt in time_points]
        trend.values = voltages

        try:
            self.eri_prediction = BatteryTrendAnalyzer.analyze_battery_depletion(trend)

            # Update info label
            if self.eri_prediction.get('predicted_eri_date'):
                years = self.eri_prediction.get('years_to_eri', 0)
                depletion_rate = self.eri_prediction.get('depletion_rate_v_per_year', 0)

                info_text = (
                    f"Current: {self.eri_prediction['current_voltage']:.2f}V  |  "
                    f"Depletion: {abs(depletion_rate):.3f}V/year  |  "
                    f"ERI in ~{years:.1f} years"
                )
                self.info_label.setText(info_text)
            else:
                self.info_label.setText(
                    f"Current: {self.eri_prediction['current_voltage']:.2f}V  |  "
                    f"Depletion rate: {self.eri_prediction.get('depletion_rate_v_per_year', 0):.3f}V/year"
                )

        except Exception as e:
            print(f"Error calculating ERI: {e}")
            self.eri_prediction = None

    def _plot_eri_prediction(self, timestamps: List[float]):
        """
        Plot predicted ERI date marker.

        Args:
            timestamps: Current data timestamps
        """
        if not self.eri_prediction or not self.eri_prediction.get('predicted_eri_date'):
            return

        try:
            # Parse ERI date
            eri_date_str = self.eri_prediction['predicted_eri_date']
            eri_date = datetime.fromisoformat(eri_date_str)
            eri_timestamp = eri_date.timestamp()

            # Plot vertical line at predicted ERI date
            pen = pg.mkPen(color=(200, 0, 0), width=2, style=Qt.PenStyle.DotLine)

            # Vertical line
            y_range = self.plot_widget.getPlotItem().viewRange()[1]
            line = pg.InfiniteLine(
                pos=eri_timestamp,
                angle=90,
                pen=pen,
                label='Predicted ERI',
                labelOpts={'position': 0.95, 'color': (200, 0, 0)}
            )
            self.plot_widget.addItem(line)

        except Exception as e:
            print(f"Error plotting ERI prediction: {e}")

    def _configure_time_axis(self, timestamps: List[float]):
        """
        Configure X-axis to display dates properly.

        Args:
            timestamps: Unix timestamps
        """
        # Create date axis
        axis = pg.DateAxisItem(orientation='bottom')
        self.plot_widget.setAxisItems({'bottom': axis})

    def _set_time_range_with_padding(self, timestamps: List[float]):
        """
        Set X-axis range with 10% padding on either side.

        Args:
            timestamps: Unix timestamps
        """
        if len(timestamps) == 0:
            return

        min_time = min(timestamps)
        max_time = max(timestamps)
        time_range = max_time - min_time

        # Add 10% padding on each side
        padding = time_range * 0.10 if time_range > 0 else 86400  # 1 day if single point

        self.plot_widget.setXRange(min_time - padding, max_time + padding, padding=0)

        # Auto-range Y-axis only
        self.plot_widget.enableAutoRange(axis='y')

    def _set_default_time_range(self):
        """Set default time range from 2020 to current date."""
        start_date = datetime(2020, 1, 1)
        end_date = datetime.now()

        start_timestamp = start_date.timestamp()
        end_timestamp = end_date.timestamp()

        self.plot_widget.setXRange(start_timestamp, end_timestamp, padding=0)

    def clear(self):
        """Clear all data and plots."""
        self.time_points = []
        self.voltages = []
        self.eri_prediction = None
        self.plot_widget.clear()
        self.info_label.setText("No data")
