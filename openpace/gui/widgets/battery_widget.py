"""
Battery Status Widget

Displays battery measurements over time (longevity or percentage).
OSCAR-style timeline visualization.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import numpy as np

from openpace.gui.widgets.table_chart_mixin import TableChartMixin


class BatteryTrendWidget(QWidget, TableChartMixin):
    """
    Widget displaying battery status trend over time.

    Features:
    - Line plot of battery longevity (months) or percentage vs time
    - Color coding (green → yellow → red as battery depletes)
    - Warning threshold lines
    - Statistics display
    """

    # Thresholds for longevity (months)
    LONGEVITY_GOOD = 24  # > 24 months = good
    LONGEVITY_WARNING = 6  # < 6 months = warning

    # Thresholds for percentage
    PERCENTAGE_GOOD = 50  # > 50% = good
    PERCENTAGE_WARNING = 20  # < 20% = warning

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Battery Status")

        # Data
        self.time_points: List[datetime] = []
        self.values: List[float] = []
        self.measurement_type: str = "longevity"  # "longevity" or "percentage"
        self.unit: str = "months"

        # Setup UI
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        # Create plot widget first
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # Axis labels (will be updated based on measurement type)
        self.plot_widget.setLabel('left', 'Battery Longevity', units='months')
        self.plot_widget.setLabel('bottom', 'Date')

        # Enable mouse interaction
        self.plot_widget.setMouseEnabled(x=True, y=False)

        # Legend
        self.plot_widget.addLegend()

        # Initialize the table/chart toggle (from mixin)
        self.init_table_chart_toggle(
            title="Battery Status",
            columns=["Date/Time", "Value", "Status"],
            chart_widget=self.plot_widget
        )

        # Set default time range (2020 to current date)
        self._set_default_time_range()

    def set_data(self, time_points: List[datetime], values: List[float],
                 measurement_type: str = "longevity", unit: str = None):
        """
        Set battery measurement data.

        Args:
            time_points: List of datetime objects
            values: List of measurement values
            measurement_type: "longevity" (months remaining) or "percentage"
            unit: Unit string (auto-detected if not provided)
        """
        self.time_points = time_points
        self.values = values
        self.measurement_type = measurement_type

        # Set unit based on measurement type
        if unit:
            self.unit = unit
        elif measurement_type == "longevity":
            self.unit = "months"
        else:
            self.unit = "%"

        # Update axis label
        if measurement_type == "longevity":
            self.plot_widget.setLabel('left', 'Battery Longevity', units='months')
            self.title_label.setText("Battery Longevity")
        else:
            self.plot_widget.setLabel('left', 'Battery Level', units='%')
            self.title_label.setText("Battery Level")

        # Convert datetimes to timestamps for plotting
        timestamps = [dt.timestamp() for dt in time_points]

        # Clear previous plots
        self.plot_widget.clear()

        if len(timestamps) == 0:
            self.info_label.setText("No data")
            return

        # Plot the data line with color coding
        self._plot_data_line(timestamps, values)

        # Add warning threshold lines
        self._plot_threshold_lines(timestamps)

        # Configure time axis
        self._configure_time_axis(timestamps)

        # Set X-axis range with 10% extension on either side
        self._set_time_range_with_padding(timestamps)

        # Update statistics
        self._update_statistics()

    def _plot_data_line(self, timestamps: List[float], values: List[float]):
        """
        Plot battery measurement line with color coding.
        """
        if not values:
            return

        # Determine color based on current value
        current_value = values[-1]
        color = self._get_value_color(current_value)

        # Plot line
        pen = pg.mkPen(color=color, width=2)
        label = 'Longevity' if self.measurement_type == "longevity" else 'Battery %'
        self.plot_widget.plot(
            timestamps,
            values,
            pen=pen,
            symbol='o',
            symbolSize=6,
            symbolBrush=color,
            name=label
        )

    def _get_value_color(self, value: float) -> tuple:
        """Get color based on value and measurement type."""
        if self.measurement_type == "longevity":
            if value > self.LONGEVITY_GOOD:
                return (0, 200, 0)  # Green
            elif value > self.LONGEVITY_WARNING:
                return (200, 150, 0)  # Yellow/Orange
            else:
                return (200, 0, 0)  # Red
        else:  # percentage
            if value > self.PERCENTAGE_GOOD:
                return (0, 200, 0)  # Green
            elif value > self.PERCENTAGE_WARNING:
                return (200, 150, 0)  # Yellow/Orange
            else:
                return (200, 0, 0)  # Red

    def _plot_threshold_lines(self, timestamps: List[float]):
        """
        Plot warning threshold lines.
        """
        if len(timestamps) < 2:
            return

        x_range = [timestamps[0], timestamps[-1]]

        if self.measurement_type == "longevity":
            # Warning threshold for longevity
            pen = pg.mkPen(color=(200, 150, 0), width=2, style=Qt.PenStyle.DashLine)
            self.plot_widget.plot(
                x_range,
                [self.LONGEVITY_WARNING, self.LONGEVITY_WARNING],
                pen=pen,
                name=f'Warning ({self.LONGEVITY_WARNING} months)'
            )
        else:
            # Warning threshold for percentage
            pen = pg.mkPen(color=(200, 150, 0), width=2, style=Qt.PenStyle.DashLine)
            self.plot_widget.plot(
                x_range,
                [self.PERCENTAGE_WARNING, self.PERCENTAGE_WARNING],
                pen=pen,
                name=f'Warning ({self.PERCENTAGE_WARNING}%)'
            )

    def _update_statistics(self):
        """Update the info label with current statistics."""
        if not self.values:
            self.info_label.setText("No data")
            return

        current = self.values[-1]
        status = self._get_status(current)

        if self.measurement_type == "longevity":
            years = current / 12
            info_text = f"Current: {current:.0f} months ({years:.1f} years)  |  Status: {status}"
        else:
            info_text = f"Current: {current:.0f}%  |  Status: {status}"

        # Add trend if we have multiple points
        if len(self.values) >= 2:
            change = self.values[-1] - self.values[0]
            if change < 0:
                info_text += f"  |  Change: {change:.1f}"

        self.info_label.setText(info_text)

    def _get_status(self, value: float) -> str:
        """Get status string based on value."""
        if self.measurement_type == "longevity":
            if value > self.LONGEVITY_GOOD:
                return "Good"
            elif value > self.LONGEVITY_WARNING:
                return "Monitor"
            else:
                return "Replace Soon"
        else:
            if value > self.PERCENTAGE_GOOD:
                return "Good"
            elif value > self.PERCENTAGE_WARNING:
                return "Monitor"
            else:
                return "Replace Soon"

    def _configure_time_axis(self, timestamps: List[float]):
        """
        Configure X-axis to display dates properly.
        """
        axis = pg.DateAxisItem(orientation='bottom')
        self.plot_widget.setAxisItems({'bottom': axis})

    def _set_time_range_with_padding(self, timestamps: List[float]):
        """
        Set X-axis range with 10% padding on either side.
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
        self.values = []
        self.plot_widget.clear()
        self.info_label.setText("No data")

    def get_table_row_data(self) -> List[List[Any]]:
        """
        Get data rows for the table view.

        Returns:
            List of rows: [Date/Time, Value, Status]
        """
        rows = []
        for dt, value in zip(self.time_points, self.values):
            # Format datetime
            date_str = dt.strftime("%Y-%m-%d %H:%M")

            # Format value
            if self.measurement_type == "longevity":
                value_str = f"{value:.0f} months"
            else:
                value_str = f"{value:.0f}%"

            # Determine status
            status = self._get_status(value)

            rows.append([date_str, value_str, status])

        return rows
